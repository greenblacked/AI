"""install.sh is the local-development install path, and its failure modes are exactly
the ones a convenience script must not have: nesting a link inside a real directory while
reporting success, or replacing someone's deliberate symlink without being asked.

These run the real script against a temporary target directory. Most of them run a copy of
it inside a small repository built per test, because the script links from whichever tree
it sits in: linking five skills proves the same behaviour as linking every one of them, at
a fraction of the time. One test still links this repository's whole tree, so a shipped
skill the script cannot reach still fails here.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO

SCRIPT = REPO / "scripts" / "install.sh"
# Three plugins, so a selection has something to leave out, and more than one skill in
# a plugin, so "exactly its skills" is a set rather than a single name.
LAYOUT = {
    "coding": ("code-review", "debugging"),
    "personal": ("budget", "travel"),
    "design": ("ui-ux-review",),
}
SKILLS = sorted(name for names in LAYOUT.values() for name in names)

pytestmark = pytest.mark.skipif(os.name == "nt", reason="a bash script with symlinks")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A plugin tree with the real install.sh copied into its scripts/ directory."""
    root = tmp_path / "repo"
    for plugin, names in LAYOUT.items():
        for name in names:
            skill = root / "plugins" / plugin / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    (root / "scripts").mkdir()
    shutil.copy2(SCRIPT, root / "scripts" / "install.sh")
    return root


def run(repo: Path, target: Path, *flags: str) -> subprocess.CompletedProcess:
    # bash comes from PATH on purpose: the script is run the way a person runs it.
    return subprocess.run(  # noqa: S603
        ["bash", str(repo / "scripts" / "install.sh"), *flags],  # noqa: S607
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_SKILLS_DIR": str(target)},
        check=False,
    )


def test_links_every_shipped_skill_into_an_empty_target(tmp_path):
    # The one run against this repository itself: every skill that ships has to be
    # reachable by the script, whatever the small tree below proves about its logic.
    shipped = sorted(p.parent.name for p in REPO.glob("plugins/*/skills/*/SKILL.md"))
    target = tmp_path / "skills"
    result = run(REPO, target)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in target.iterdir()) == shipped
    assert all(p.is_symlink() and (p / "SKILL.md").is_file() for p in target.iterdir())
    assert f"done: {len(shipped)} linked, 0 unchanged" in result.stderr


def test_links_every_skill_into_an_empty_target(repo, tmp_path):
    target = tmp_path / "skills"
    result = run(repo, target)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in target.iterdir()) == SKILLS
    assert all(p.is_symlink() and (p / "SKILL.md").is_file() for p in target.iterdir())
    assert f"done: {len(SKILLS)} linked, 0 unchanged" in result.stderr


def test_a_second_run_changes_nothing_and_still_exits_zero(repo, tmp_path):
    target = tmp_path / "skills"
    run(repo, target)
    result = run(repo, target)
    assert result.returncode == 0
    assert f"done: 0 linked, {len(SKILLS)} unchanged" in result.stderr


def test_dry_run_writes_nothing(repo, tmp_path):
    target = tmp_path / "skills"
    result = run(repo, target, "--dry-run")
    assert result.returncode == 0
    assert not target.exists()
    assert "would link" in result.stderr and "dry run" in result.stderr


def test_bad_usage_exits_two(repo, tmp_path):
    result = run(repo, tmp_path / "skills", "--bogus")
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_help_exits_zero(repo, tmp_path):
    result = run(repo, tmp_path / "skills", "--help")
    assert result.returncode == 0 and "Exit codes" in result.stdout


def test_a_real_directory_in_the_way_is_never_removed_even_with_force(repo, tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).mkdir()
    (target / SKILLS[0] / "keep.txt").write_text("mine", encoding="utf-8")
    for flags in ((), ("--force",)):
        result = run(repo, target, *flags)
        assert result.returncode == 3, result.stderr
        assert "is a directory; remove it yourself" in result.stderr
        assert (target / SKILLS[0] / "keep.txt").read_text() == "mine"
        assert not (target / SKILLS[0]).is_symlink()
        # The other skills were still linked; the conflict did not abort the run.
        assert (target / SKILLS[1]).is_symlink()


def test_a_foreign_symlink_is_kept_without_force_and_replaced_with_it(repo, tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (target / SKILLS[0]).symlink_to(elsewhere)

    result = run(repo, target)
    assert result.returncode == 3
    assert f"points at {elsewhere} (use --force)" in result.stderr
    assert os.readlink(target / SKILLS[0]) == str(elsewhere)

    result = run(repo, target, "--force")
    assert result.returncode == 0, result.stderr
    assert (target / SKILLS[0] / "SKILL.md").is_file()


def test_a_regular_file_in_the_way_is_kept_without_force_and_replaced_with_it(repo, tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).write_text("a file", encoding="utf-8")
    result = run(repo, target)
    assert result.returncode == 3 and "exists and is not a symlink" in result.stderr
    assert (target / SKILLS[0]).is_file() and not (target / SKILLS[0]).is_symlink()
    result = run(repo, target, "--force")
    assert result.returncode == 0 and (target / SKILLS[0]).is_symlink()


def test_a_stale_symlink_into_this_repository_still_needs_force(repo, tmp_path):
    # The script recognises exactly one target per link: the skill directory itself.
    # A link into the repository but at the wrong place is somebody's deliberate
    # arrangement as far as it can tell, so it is left alone until asked.
    target = tmp_path / "skills"
    target.mkdir()
    (target / SKILLS[0]).symlink_to(repo / "plugins" / "nowhere")
    result = run(repo, target)
    assert result.returncode == 3
    assert "use --force" in result.stderr
    assert os.readlink(target / SKILLS[0]) == str(repo / "plugins" / "nowhere")


def test_a_link_reached_through_a_symlinked_alias_is_still_recognised(repo, tmp_path):
    # REPO_ROOT is computed from the running script's own path, so invoking install.sh
    # through a symlinked alias of this repository builds a skill_dir that is spelled
    # differently but is physically the same directory. A later run through the
    # canonical path used to compare the two spellings as strings and report every
    # already-linked skill as a conflict.
    target = tmp_path / "skills"
    alias = tmp_path / "alias-repo"
    alias.symlink_to(repo)

    first = subprocess.run(  # noqa: S603
        ["bash", str(alias / "scripts" / "install.sh")],  # noqa: S607
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_SKILLS_DIR": str(target)},
        check=False,
    )
    assert first.returncode == 0, first.stderr

    second = run(repo, target)  # the canonical, non-aliased path this time
    assert second.returncode == 0, second.stderr
    assert f"done: 0 linked, {len(SKILLS)} unchanged" in second.stderr


def plugin_skills(repo: Path, *plugins: str) -> dict[str, Path]:
    return {
        path.parent.name: path.parent.resolve()
        for plugin in plugins
        for path in (repo / "plugins" / plugin / "skills").glob("*/SKILL.md")
    }


@pytest.mark.parametrize("flags", [("--plugin",), ("--plugin", ""), ("--plugin", "--force")])
def test_plugin_requires_a_name_before_writes(repo, tmp_path, flags):
    target = tmp_path / "skills"
    result = run(repo, target, *flags)
    assert result.returncode == 2
    assert "--plugin requires a plugin name" in result.stderr
    assert not target.exists()


@pytest.mark.parametrize("name", ["unknown", "../coding", "coding/skills", "/coding"])
def test_unknown_plugin_rejects_entire_selection_before_writes(repo, tmp_path, name):
    target = tmp_path / "skills"
    result = run(repo, target, "--plugin", "coding", "--plugin", name, "--force")
    assert result.returncode == 2
    assert "unknown plugin" in result.stderr
    assert not target.exists()


def test_selected_plugin_links_exactly_its_skills_and_is_idempotent(repo, tmp_path):
    target = tmp_path / "skills"
    expected = plugin_skills(repo, "coding")
    result = run(repo, target, "--plugin", "coding")
    assert result.returncode == 0, result.stderr
    assert {p.name: p.resolve() for p in target.iterdir()} == expected
    second = run(repo, target, "--plugin", "coding")
    assert second.returncode == 0, second.stderr
    assert f"done: 0 linked, {len(expected)} unchanged" in second.stderr


def test_multiple_plugins_and_duplicates_install_the_union_once(repo, tmp_path):
    target = tmp_path / "skills"
    expected = plugin_skills(repo, "coding", "personal")
    result = run(repo, target, "--plugin", "coding", "--plugin", "personal", "--plugin", "coding")
    assert result.returncode == 0, result.stderr
    assert {p.name: p.resolve() for p in target.iterdir()} == expected
    assert f"done: {len(expected)} linked, 0 unchanged" in result.stderr


def test_selected_plugin_dry_run_lists_only_selected_skills(repo, tmp_path):
    target = tmp_path / "skills"
    result = run(repo, target, "--dry-run", "--plugin", "personal")
    assert result.returncode == 0, result.stderr
    assert not target.exists()
    names = {
        line.split("would link ", 1)[1].split(" -> ", 1)[0]
        for line in result.stderr.splitlines()
        if "would link " in line
    }
    assert names == set(plugin_skills(repo, "personal"))


def test_selected_plugin_preserves_conflicts_and_unselected_entries(repo, tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    name = next(iter(plugin_skills(repo, "personal")))
    (target / name).mkdir()
    marker = target / name / "keep.txt"
    marker.write_text("mine", encoding="utf-8")
    unselected = target / "codebase-orientation"
    unselected.write_text("unselected", encoding="utf-8")
    for flags in ((), ("--force",)):
        result = run(repo, target, "--plugin", "personal", *flags)
        assert result.returncode == 3, result.stderr
        assert marker.read_text() == "mine"
        assert unselected.read_text() == "unselected"


def test_the_selection_array_is_never_expanded_bare():
    # Before bash 4.4 (stock macOS is 3.2) expanding an empty array under `set -u` is fatal,
    # and the default run has no --plugin; the suite runs on bash 5, so it cannot see that.
    guarded = '${PLUGINS[@]+"${PLUGINS[@]}"}'
    script = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(r"\$\{PLUGINS\[@\]", script.replace(guarded, ""))
