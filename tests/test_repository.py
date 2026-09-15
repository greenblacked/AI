"""The check that makes CI the source of truth: this repository validates clean.

Without this, the validator is a tool that has never been pointed at anything real.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from skillcheck.cli import _listing_sizes, main
from skillcheck.rules import check_marketplace, check_skill, find_plugins, find_skills

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


def test_listing_budget_warns_per_plugin_and_is_off_by_default(capsys):
    # This repository's descriptions exceed the runtime's default budget; the point of
    # the flag is to make that visible on demand without turning it into a gate.
    assert main([str(ROOT), "--skip-marketplace"]) == 0
    out = capsys.readouterr().out
    assert "description characters in the listing:" in out
    assert "listing-over-budget" not in out
    main([str(ROOT), "--skip-marketplace", "--listing-budget", "1000"])
    out = capsys.readouterr().out
    # Measure which plugins are actually over rather than assuming all of them are. A
    # literal count broke when the library was re-split, and "every plugin" broke the
    # first time a small plugin was added — both times the test failed on a change that
    # was correct, which is the fastest way to teach someone to stop reading it.
    over = sum(
        1 for size in _listing_sizes(find_plugins(ROOT), find_skills(ROOT)).values() if size > 1000
    )
    assert over, "no plugin exceeds 1000 characters, so this asserts nothing"
    assert out.count("[listing-over-budget]") == over


def test_the_fixture_repository_validates_clean(mini_repo):
    # Every script test builds on this fixture, and a fixture the validator rejects
    # proves nothing about the hook or the packager: an error attributed to another
    # skill hides in the noise. The first version of it shipped with colliding eval
    # queries and only the tests that happened not to look at the total passed.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "skillcheck", str(mini_repo), "--strict"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(mini_repo / "src")},
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_this_repository_s_budget_comment_is_what_the_writer_emits():
    """The note in listing-budget.json is regenerated, so it must not be hand-edited.

    ``write()`` rebuilds the whole file, and it now derives the token figures from
    CHARS_PER_TOKEN. A comment typed in by hand survives until the next ``--update`` and
    then vanishes, and in the meantime it can state a ratio the report has stopped using.
    Writing this file by hand once already produced "1,730 tokens" where the constant
    gives 1,728.
    """
    import importlib.util
    import json
    import tempfile

    spec = importlib.util.spec_from_file_location(
        "clb", ROOT / "scripts" / "check_listing_budget.py"
    )
    budget = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(budget)

    committed = json.loads((ROOT / budget.BUDGET_FILE).read_text(encoding="utf-8"))["_comment"]
    scratch = Path(tempfile.mkdtemp()) / budget.BUDGET_FILE
    budget.write(scratch, {"any": 0})
    emitted = json.loads(scratch.read_text(encoding="utf-8"))["_comment"]
    assert committed == emitted
