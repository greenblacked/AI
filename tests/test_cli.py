"""Exit codes are the validator's contract with CI, so each one is pinned."""

from __future__ import annotations

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
