"""Rule-level tests.

Each case builds a throwaway skill directory containing exactly one defect, so a
failure names the rule that broke rather than "something is wrong with validation".
"""

from __future__ import annotations

import json

import pytest

from skillcheck.rules import ERROR, WARNING, check_marketplace, check_skill, find_skills

GOOD_DESCRIPTION = (
    "Do a specific, useful thing end to end. Use this skill whenever the user asks "
    "for that thing, including casual phrasings."
)


def write_skill(
    root, name, *, description=GOOD_DESCRIPTION, front=None, body="# Demo\n", evals=True
):
    directory = root / "skills" / "engineering" / name
    directory.mkdir(parents=True, exist_ok=True)
    if front is None:
        front = f"name: {name}\ndescription: {description}"
    (directory / "SKILL.md").write_text(f"---\n{front}\n---\n\n{body}", encoding="utf-8")
    if evals:
        # A fixture skill is otherwise incomplete, and every assertion of "produces
        # nothing" would trip over the missing-eval-set warning instead.
        (directory / "evals").mkdir(exist_ok=True)
        cases = [{"query": f"positive {i}", "should_trigger": True} for i in range(10)]
        cases += [{"query": f"negative {i}", "should_trigger": False} for i in range(10)]
        (directory / "evals" / "trigger-eval.json").write_text(json.dumps(cases), encoding="utf-8")
    return directory


def codes(findings, level=None):
    return {f.code for f in findings if level is None or f.level == level}


def test_a_well_formed_skill_produces_nothing(tmp_path):
    directory = write_skill(tmp_path, "demo")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize(
    ("front", "expected"),
    [
        ("name: demo", "missing-description"),
        (f"description: {GOOD_DESCRIPTION}", "missing-name"),
        (f"name: \ndescription: {GOOD_DESCRIPTION}", "empty-name"),
        ("name: demo\ndescription: ''", "empty-description"),
        (f"name: Demo\ndescription: {GOOD_DESCRIPTION}", "bad-name"),
        (f"name: de--mo\ndescription: {GOOD_DESCRIPTION}", "bad-name"),
        (f"name: other\ndescription: {GOOD_DESCRIPTION}", "name-mismatch"),
        (f"name: demo\ndescription: {GOOD_DESCRIPTION} Use for <html>.", "angle-brackets"),
        (f"name: demo\ndescription: {GOOD_DESCRIPTION}\nallowed_tools: Read", "unknown-key"),
        (
            f"name: demo\ndescription: {GOOD_DESCRIPTION}\ncompatibility: {'x' * 501}",
            "long-compatibility",
        ),
    ],
)
def test_frontmatter_defects_are_errors(tmp_path, front, expected):
    directory = write_skill(tmp_path, "demo", front=front)
    assert expected in codes(check_skill(directory, tmp_path), ERROR)


def test_over_long_name_and_description_are_errors(tmp_path):
    long_name = "a" * 65
    directory = write_skill(
        tmp_path, long_name, front=f"name: {long_name}\ndescription: {'d' * 1025}"
    )
    found = codes(check_skill(directory, tmp_path), ERROR)
    assert {"long-name", "long-description"} <= found


def test_a_dangling_reference_is_an_error(tmp_path):
    directory = write_skill(
        tmp_path, "demo", body="Read `references/deep-dive.md` before starting.\n"
    )
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_reference_that_exists_is_fine(tmp_path):
    directory = write_skill(
        tmp_path, "demo", body="Read `references/deep-dive.md` before starting.\n"
    )
    (directory / "references").mkdir()
    (directory / "references" / "deep-dive.md").write_text("# Deep dive\n", encoding="utf-8")
    assert check_skill(directory, tmp_path) == []


def test_a_bare_directory_mention_is_not_a_reference(tmp_path):
    directory = write_skill(tmp_path, "demo", body="Put helper code in scripts/ if it repeats.\n")
    assert check_skill(directory, tmp_path) == []


def test_a_nested_skill_is_an_error(tmp_path):
    directory = write_skill(tmp_path, "demo")
    nested = directory / "references" / "inner"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("---\nname: inner\n---\n", encoding="utf-8")
    assert "nested-skill" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_shell_script_needs_a_shebang_and_the_executable_bit(tmp_path):
    directory = write_skill(tmp_path, "demo")
    scripts = directory / "scripts"
    scripts.mkdir()
    (scripts / "run.sh").write_text("echo hi\n", encoding="utf-8")
    found = codes(check_skill(directory, tmp_path), ERROR)
    assert {"no-shebang", "not-executable"} <= found


def test_a_description_with_no_trigger_clause_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", description="Does a thing competently.")
    assert "no-trigger" in codes(check_skill(directory, tmp_path), WARNING)


def test_a_description_near_the_cap_warns(tmp_path):
    description = "Use this skill when asked. " + "x" * 990
    directory = write_skill(tmp_path, "demo", description=description)
    assert "description-headroom" in codes(check_skill(directory, tmp_path), WARNING)


def test_shouting_warns_but_does_not_fail(tmp_path):
    directory = write_skill(tmp_path, "demo", body="You must ALWAYS check the exit code.\n")
    findings = check_skill(directory, tmp_path)
    assert "shouting" in codes(findings, WARNING)
    assert not any(f.failed for f in findings)


def test_an_over_long_skill_body_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", body="line\n" * 520)
    assert "long-skill" in codes(check_skill(directory, tmp_path), WARNING)


def test_find_skills_returns_every_skill_directory(tmp_path):
    write_skill(tmp_path, "one")
    write_skill(tmp_path, "two")
    assert [p.name for p in find_skills(tmp_path / "skills")] == ["one", "two"]


def test_marketplace_must_list_every_skill(tmp_path):
    write_skill(tmp_path, "demo")
    manifest = tmp_path / ".claude-plugin"
    manifest.mkdir()
    (manifest / "marketplace.json").write_text(
        '{"name": "x", "owner": {"name": "y"}, "plugins": []}', encoding="utf-8"
    )
    assert "unlisted-skill" in codes(check_marketplace(tmp_path), ERROR)


def test_marketplace_entries_must_resolve(tmp_path):
    directory = write_skill(tmp_path, "demo")
    manifest = tmp_path / ".claude-plugin"
    manifest.mkdir()
    (manifest / "marketplace.json").write_text(
        '{"name": "x", "owner": {"name": "y"}, "plugins": [{"name": "p", "skills": '
        '["./skills/engineering/demo", "./skills/engineering/ghost"]}]}',
        encoding="utf-8",
    )
    found = codes(check_marketplace(tmp_path), ERROR)
    assert "missing-listed-skill" in found
    assert "unlisted-skill" not in found
    assert directory.exists()


def test_invalid_marketplace_json_is_an_error(tmp_path):
    write_skill(tmp_path, "demo")
    manifest = tmp_path / ".claude-plugin"
    manifest.mkdir()
    (manifest / "marketplace.json").write_text("{ not json", encoding="utf-8")
    assert "bad-json" in codes(check_marketplace(tmp_path), ERROR)


def test_a_path_inside_a_fenced_block_is_not_a_pointer(tmp_path):
    # Skills document layouts. Treating an illustrative path as a dangling pointer made
    # it impossible to show one without failing the build.
    body = (
        "Another project lays itself out like this:\n\n"
        "```text\ntheirs/\n  references/other.md\n```\n"
    )
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_tilde_fence_is_masked_too(tmp_path):
    body = "Example:\n\n~~~text\nreferences/other.md\n~~~\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_pointer_after_a_fence_is_still_checked(tmp_path):
    body = "```text\nsome/example\n```\n\nNow read `references/deep.md`.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_the_reported_line_points_at_the_pointer(tmp_path):
    body = "one\ntwo\n\nRead `references/deep.md` now.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    finding = next(f for f in check_skill(directory, tmp_path) if f.code == "dangling-reference")
    lines = (directory / "SKILL.md").read_text().split("\n")
    assert "references/deep.md" in lines[finding.line - 1]


def test_an_unterminated_fence_does_not_switch_the_check_off(tmp_path):
    # Masking to end-of-file would silently stop checking every pointer after it, which
    # is the failure this validator exists to prevent rather than to have.
    body = "```text\nnever closed\n\nRead `references/deep.md`.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_longer_fence_survives_a_nested_shorter_one(tmp_path):
    body = "````text\nouter\n```\ninner\n```\nreferences/inside.md\n````\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_readme_in_the_agents_directory_is_not_a_subagent(tmp_path):
    from skillcheck.rules import find_agents

    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "README.md").write_text("# Subagents\n", encoding="utf-8")
    (agents / "real-agent.md").write_text("---\nname: real-agent\n---\n", encoding="utf-8")
    assert [p.name for p in find_agents(agents)] == ["real-agent.md"]
