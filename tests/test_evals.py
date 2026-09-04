"""The eval-set schema is checked on every run because it is free and deterministic.

Scoring the queries needs a model and costs money, so that lives in a manual workflow.
Validating the shape does not, and a malformed eval set is worse than none: it looks
like measurement while measuring nothing.
"""

from __future__ import annotations

import json

from skillcheck.rules import ERROR, WARNING, check_evals


def write_evals(root, entries, raw=None):
    directory = root / "plugins" / "engineering" / "skills" / "demo"
    (directory / "evals").mkdir(parents=True, exist_ok=True)
    path = directory / "evals" / "trigger-eval.json"
    path.write_text(raw if raw is not None else json.dumps(entries), encoding="utf-8")
    return directory


def balanced(positives=10, negatives=10):
    return [{"query": f"positive {i}", "should_trigger": True} for i in range(positives)] + [
        {"query": f"negative {i}", "should_trigger": False} for i in range(negatives)
    ]


def codes(findings, level=ERROR):
    return {f.code for f in findings if f.level == level}


def test_a_balanced_set_produces_nothing(tmp_path):
    assert check_evals(write_evals(tmp_path, balanced()), tmp_path) == []


def test_a_missing_eval_set_warns_but_does_not_fail(tmp_path):
    directory = tmp_path / "skills" / "engineering" / "demo"
    directory.mkdir(parents=True)
    findings = check_evals(directory, tmp_path)
    assert codes(findings, WARNING) == {"no-evals"}
    assert not any(f.failed for f in findings)


def test_too_few_queries_is_an_error(tmp_path):
    assert "thin-eval-set" in codes(check_evals(write_evals(tmp_path, balanced(4, 4)), tmp_path))


def test_a_set_with_no_real_negatives_is_an_error(tmp_path):
    # The negatives are the whole point: they are what catches a description that
    # fires on everything.
    assert "unbalanced-eval-set" in codes(
        check_evals(write_evals(tmp_path, balanced(18, 2)), tmp_path)
    )


def test_duplicate_queries_are_an_error(tmp_path):
    entries = balanced()
    entries[1]["query"] = entries[0]["query"]
    assert "duplicate-eval-query" in codes(check_evals(write_evals(tmp_path, entries), tmp_path))


def test_malformed_entries_are_reported(tmp_path):
    entries = balanced()
    entries[0] = {"query": "", "should_trigger": True}
    entries[1] = {"query": "x", "should_trigger": "yes"}
    entries[2] = {"query": "y", "should_trigger": True, "note": "extra"}
    assert "bad-eval-entry" in codes(check_evals(write_evals(tmp_path, entries), tmp_path))


def test_invalid_json_is_an_error(tmp_path):
    assert "bad-eval-json" in codes(
        check_evals(write_evals(tmp_path, None, raw="{ nope"), tmp_path)
    )


def test_a_json_object_instead_of_an_array_is_an_error(tmp_path):
    assert "bad-eval-shape" in codes(
        check_evals(write_evals(tmp_path, None, raw='{"queries": []}'), tmp_path)
    )


def test_an_eval_finding_lands_on_the_skill_row_in_the_summary(tmp_path, monkeypatch):
    # The summary grouped by trimming a "/SKILL.md" suffix, so a finding reported
    # against <skill>/evals/trigger-eval.json matched no row: the table printed a green
    # tick for a skill while the build failed on it.
    from skillcheck.cli import main

    directory = write_evals(tmp_path, [{"query": "only one", "should_trigger": True}])
    (directory / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A thing. Use this skill when asked.\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert main([str(tmp_path), "--github", "--skip-marketplace"]) == 1
    row = next(line for line in summary.read_text().splitlines() if str(directory.name) in line)
    assert "❌" in row


POSITIVE = {"query": "ship it", "should_trigger": True}


def write_eval_set(root, plugin, skill, queries):
    directory = root / "plugins" / plugin / "skills" / skill / "evals"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "trigger-eval.json").write_text(json.dumps(queries), encoding="utf-8")
    return directory.parent


def test_the_same_positive_in_two_skills_is_an_error(tmp_path):
    from skillcheck.rules import check_eval_conflicts

    # Whitespace and case differ, because a conflict people actually create is a
    # near-copy rather than an exact one.
    a = write_eval_set(tmp_path, "engineering", "alpha", [POSITIVE])
    b = write_eval_set(
        tmp_path, "engineering", "beta", [{"query": "Ship  It", "should_trigger": True}]
    )
    findings = check_eval_conflicts([a, b], tmp_path)
    assert [f.code for f in findings] == ["conflicting-eval-query"]
    assert "alpha" in findings[0].message


def test_a_positive_in_one_skill_and_a_negative_in_another_is_allowed(tmp_path):
    from skillcheck.rules import check_eval_conflicts

    a = write_eval_set(tmp_path, "engineering", "alpha", [POSITIVE])
    b = write_eval_set(
        tmp_path, "engineering", "beta", [{"query": "ship it", "should_trigger": False}]
    )
    assert check_eval_conflicts([a, b], tmp_path) == []


def test_a_missing_or_malformed_eval_set_is_not_reported_twice(tmp_path):
    from skillcheck.rules import check_eval_conflicts

    a = tmp_path / "plugins" / "engineering" / "skills" / "alpha"
    a.mkdir(parents=True)
    b = write_eval_set(tmp_path, "engineering", "beta", [POSITIVE])
    (b / "evals" / "trigger-eval.json").write_text("{not json", encoding="utf-8")
    assert check_eval_conflicts([a, b], tmp_path) == []
