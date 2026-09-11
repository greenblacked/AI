"""Exit codes are the validator's contract with CI, so each one is pinned."""

from __future__ import annotations

import json

from skillcheck.cli import main
from tests.test_rules import write_skill


def test_a_tree_with_no_skills_exits_two(tmp_path, capsys):
    assert main([str(tmp_path)]) == 2
    assert "no SKILL.md found" in capsys.readouterr().err


def test_a_warning_only_fails_under_strict(tmp_path, monkeypatch):
    # No eval set is a warning, and the summary must show it as one, not as a pass.
    directory = write_skill(tmp_path, "demo", evals=False)
    assert main([str(tmp_path), "--skip-marketplace"]) == 0
    assert main([str(tmp_path), "--skip-marketplace", "--strict"]) == 1
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    main([str(tmp_path), "--skip-marketplace", "--github"])
    row = next(line for line in summary.read_text().splitlines() if directory.name in line)
    assert "⚠️ 1 warning(s)" in row


def _local_agent(root, name, stem=None):
    """Write a subagent into the repository's own `.claude/agents/`."""
    directory = root / ".claude" / "agents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem or name}.md"
    path.write_text(
        f"---\nname: {name}\ndescription: Do one narrow thing for work on this "
        "repository and return a conclusion. Use when the caller is changing something "
        f"here and wants {name} run over it.\ntools: Read, Grep\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return path


def test_a_repo_local_subagent_is_discovered_and_counted(mini_repo, capsys):
    # `.claude/agents/` holds the subagents that serve work on this repository rather
    # than shipping to installers, the same split `.claude/commands/` has. Before it was
    # scanned, a name that had drifted from its filename failed the way every other
    # unread file fails here: delegation silently never happens.
    _local_agent(mini_repo, "local-helper")
    assert main([str(mini_repo)]) == 0
    assert "2 subagent(s)" in capsys.readouterr().out


def test_a_broken_repo_local_subagent_fails_the_run(mini_repo, capsys):
    _local_agent(mini_repo, "local-helper", stem="helper")
    assert main([str(mini_repo)]) == 1
    out = capsys.readouterr().out
    assert "[name-mismatch]" in out
    assert ".claude/agents/helper.md" in out


def test_a_repo_local_subagent_without_evals_only_warns(mini_repo, capsys):
    # No eval set is a judgement call, not a rule, so it stays a warning here too —
    # and --strict is what makes the judgement call get made.
    _local_agent(mini_repo, "local-helper")
    assert main([str(mini_repo), "--strict"]) == 1
    assert "[no-evals]" in capsys.readouterr().out


def test_a_repo_local_subagent_may_not_steal_a_shipped_one_s_query(mini_repo, capsys):
    # The conflict check runs across both homes. Two positives on one query is a
    # contradiction no harness can satisfy, and it does not become less of one because
    # the pair straddles the plugin boundary.
    _local_agent(mini_repo, "local-helper")
    shared = "read the 40mb log and tell me which class of failure it is"
    (mini_repo / ".claude" / "agents" / "evals").mkdir(parents=True, exist_ok=True)
    (mini_repo / ".claude" / "agents" / "evals" / "local-helper.json").write_text(
        json.dumps(
            [{"query": shared, "should_trigger": True}]
            + [{"query": f"positive {i}", "should_trigger": True} for i in range(9)]
            + [{"query": f"negative {i}", "should_trigger": False} for i in range(10)]
        ),
        encoding="utf-8",
    )
    reader = mini_repo / "plugins" / "engineering" / "agents" / "evals" / "reader.json"
    entries = json.loads(reader.read_text())
    entries[0]["query"] = shared
    reader.write_text(json.dumps(entries), encoding="utf-8")
    assert main([str(mini_repo)]) == 1
    assert "[conflicting-eval-query]" in capsys.readouterr().out


def test_a_repo_local_eval_may_not_expect_a_name_that_does_not_exist(mini_repo, capsys):
    # `known` is built from both homes, so a repo-local set can legitimately name a
    # shipped skill — and a misspelling of one is still a permanent miss.
    _local_agent(mini_repo, "local-helper")
    (mini_repo / ".claude" / "agents" / "evals").mkdir(parents=True, exist_ok=True)
    (mini_repo / ".claude" / "agents" / "evals" / "local-helper.json").write_text(
        json.dumps(
            [{"query": f"positive {i}", "should_trigger": True} for i in range(10)]
            + [{"query": "negative 0", "should_trigger": False, "expected": "alpha"}]
            + [{"query": "negative 1", "should_trigger": False, "expected": "aplha"}]
            + [{"query": f"negative {i}", "should_trigger": False} for i in range(2, 10)]
        ),
        encoding="utf-8",
    )
    assert main([str(mini_repo)]) == 1
    out = capsys.readouterr().out
    assert "[unknown-expected]" in out
    assert "'aplha'" in out


def test_a_repo_local_subagent_may_not_register_hooks_either(mini_repo, capsys):
    # The key set is shared with plugin-shipped subagents on purpose, so one of these
    # can move into a plugin later without a surprise. The message says "plugin-shipped"
    # because that is the constraint being borrowed.
    path = _local_agent(mini_repo, "local-helper")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "tools: Read, Grep\n", "tools: Read, Grep\nhooks: something\n"
        ),
        encoding="utf-8",
    )
    assert main([str(mini_repo)]) == 1
    assert "[unknown-key]" in capsys.readouterr().out
