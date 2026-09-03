"""The check that makes CI the source of truth: this repository validates clean.

Without this, the validator is a tool that has never been pointed at anything real.
"""

from __future__ import annotations

from pathlib import Path

from skillcheck.cli import main
from skillcheck.rules import check_marketplace, check_skill, find_skills

ROOT = Path(__file__).resolve().parent.parent


def test_every_skill_in_this_repository_is_valid():
    findings = []
    for skill in find_skills(ROOT):
        findings.extend(check_skill(skill, ROOT))
    findings.extend(check_marketplace(ROOT))
    errors = [f"{f.path}:{f.line} [{f.code}] {f.message}" for f in findings if f.failed]
    assert errors == []


def test_the_cli_exits_zero_on_this_repository(capsys):
    assert main([str(ROOT)]) == 0
    capsys.readouterr()


def test_the_cli_exits_one_when_a_skill_is_broken(tmp_path, capsys):
    directory = tmp_path / "plugins" / "engineering" / "skills" / "demo"
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text("---\nname: wrong-name\n---\n", encoding="utf-8")
    assert main([str(tmp_path), "--skip-marketplace"]) == 1
    output = capsys.readouterr().out
    assert "name-mismatch" in output
    assert "missing-description" in output


def test_github_mode_emits_annotations(tmp_path, capsys):
    directory = tmp_path / "plugins" / "engineering" / "skills" / "demo"
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    main([str(tmp_path), "--github", "--skip-marketplace"])
    output = capsys.readouterr().out
    assert "::error file=plugins/engineering/skills/demo/SKILL.md,line=1" in output
