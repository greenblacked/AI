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
