"""install.sh is the local-development install path, and its failure modes are exactly
the ones a convenience script must not have: nesting a link inside a real directory while
reporting success, or replacing someone's deliberate symlink without being asked.

These run the real script against a temporary target directory. The repository it links
from is this one, so the count of links is whatever the tree holds.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO

SCRIPT = REPO / "scripts" / "install.sh"
SKILLS = sorted(p.name for p in REPO.glob("plugins/*/skills/*") if (p / "SKILL.md").is_file())

pytestmark = pytest.mark.skipif(os.name == "nt", reason="a bash script with symlinks")


def run(target: Path, *flags: str) -> subprocess.CompletedProcess:
    # bash comes from PATH on purpose: the script is run the way a person runs it.
    return subprocess.run(  # noqa: S603
        ["bash", str(SCRIPT), *flags],  # noqa: S607
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_SKILLS_DIR": str(target)},
        check=False,
    )


def test_links_every_skill_into_an_empty_target(tmp_path):
    target = tmp_path / "skills"
    result = run(target)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in target.iterdir()) == SKILLS
    assert all(p.is_symlink() and (p / "SKILL.md").is_file() for p in target.iterdir())
    assert f"done: {len(SKILLS)} linked, 0 unchanged" in result.stderr


def test_a_second_run_changes_nothing_and_still_exits_zero(tmp_path):
    target = tmp_path / "skills"
    run(target)
    result = run(target)
    assert result.returncode == 0
    assert f"done: 0 linked, {len(SKILLS)} unchanged" in result.stderr


def test_dry_run_writes_nothing(tmp_path):
    target = tmp_path / "skills"
    result = run(target, "--dry-run")
    assert result.returncode == 0
    assert not target.exists()
    assert "would link" in result.stderr and "dry run" in result.stderr


def test_bad_usage_exits_two(tmp_path):
    result = run(tmp_path / "skills", "--bogus")
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_help_exits_zero(tmp_path):
    result = run(tmp_path / "skills", "--help")
    assert result.returncode == 0 and "Exit codes" in result.stdout


def test_a_real_directory_in_the_way_is_never_removed_even_with_force(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).mkdir()
    (target / SKILLS[0] / "keep.txt").write_text("mine", encoding="utf-8")
    for flags in ((), ("--force",)):
        result = run(target, *flags)
        assert result.returncode == 3, result.stderr
        assert "is a directory; remove it yourself" in result.stderr
        assert (target / SKILLS[0] / "keep.txt").read_text() == "mine"
        assert not (target / SKILLS[0]).is_symlink()
        # The other skills were still linked; the conflict did not abort the run.
        assert (target / SKILLS[1]).is_symlink()


def test_a_foreign_symlink_is_kept_without_force_and_replaced_with_it(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (target / SKILLS[0]).symlink_to(elsewhere)

    result = run(target)
    assert result.returncode == 3
    assert f"points at {elsewhere} (use --force)" in result.stderr
    assert os.readlink(target / SKILLS[0]) == str(elsewhere)

    result = run(target, "--force")
    assert result.returncode == 0, result.stderr
    assert (target / SKILLS[0] / "SKILL.md").is_file()


def test_a_regular_file_in_the_way_is_kept_without_force_and_replaced_with_it(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).write_text("a file", encoding="utf-8")
    result = run(target)
    assert result.returncode == 3 and "exists and is not a symlink" in result.stderr
    assert (target / SKILLS[0]).is_file() and not (target / SKILLS[0]).is_symlink()
    result = run(target, "--force")
    assert result.returncode == 0 and (target / SKILLS[0]).is_symlink()


def test_a_stale_symlink_into_this_repository_still_needs_force(tmp_path):
    # The script recognises exactly one target per link: the skill directory itself.
    # A link into the repository but at the wrong place is somebody's deliberate
    # arrangement as far as it can tell, so it is left alone until asked.
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).symlink_to(REPO / "plugins" / "nowhere")
    result = run(target)
    assert result.returncode == 3
    assert "use --force" in result.stderr
    assert os.readlink(target / SKILLS[0]) == str(REPO / "plugins" / "nowhere")
