"""Packaging is the cheapest proof the repository is distributable, so it gets tested.

A skill that validates but cannot be packaged is a skill nobody can install, and the
two defects the packager guards against — a symlink baked into the archive, and a stale
archive uploaded as if it were still shipped — are both silent.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from tests.conftest import load_script, write_skill

packager = load_script("package_skills.py")


def names_in(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as bundle:
        return sorted(bundle.namelist())


def test_the_archive_has_one_top_level_directory_named_after_the_skill(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references").mkdir()
    (skill / "references" / "depth.md").write_text("# Depth\n", encoding="utf-8")
    archive = packager.package(skill, tmp_path / "dist", mini_repo)
    assert archive.name == "alpha.skill"
    names = names_in(archive)
    assert names == [
        "alpha/LICENSE.txt",
        "alpha/NOTICE.txt",
        "alpha/SKILL.md",
        "alpha/references/depth.md",
    ]


def test_evals_pycache_and_ds_store_are_excluded(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "__pycache__").mkdir()
    (skill / "__pycache__" / "x.pyc").write_bytes(b"")
    (skill / ".DS_Store").write_bytes(b"")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "helper.py").write_text("print()\n", encoding="utf-8")
    archive = packager.package(skill, tmp_path / "dist", mini_repo)
    assert names_in(archive) == [
        "alpha/LICENSE.txt",
        "alpha/NOTICE.txt",
        "alpha/SKILL.md",
        "alpha/scripts/helper.py",
    ]


def test_license_and_notice_are_copies_of_the_repository_root_files(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    archive = packager.package(skill, tmp_path / "dist", mini_repo)
    with zipfile.ZipFile(archive) as bundle:
        license_text = bundle.read("alpha/LICENSE.txt").decode("utf-8")
        notice_text = bundle.read("alpha/NOTICE.txt").decode("utf-8")
    assert license_text == (mini_repo / "LICENSE").read_text(encoding="utf-8")
    assert notice_text == (mini_repo / "NOTICE").read_text(encoding="utf-8")


def test_a_skill_with_its_own_license_txt_is_refused(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "LICENSE.txt").write_text("a different licence\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="already has a LICENSE.txt"):
        packager.package(skill, tmp_path / "dist", mini_repo)


def test_a_skill_with_its_own_notice_txt_is_refused(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "NOTICE.txt").write_text("a different notice\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="already has a NOTICE.txt"):
        packager.package(skill, tmp_path / "dist", mini_repo)


def test_no_repository_license_fails_loudly(mini_repo, tmp_path):
    (mini_repo / "LICENSE").unlink()
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    with pytest.raises(SystemExit, match="no LICENSE at the repository root"):
        packager.package(skill, tmp_path / "dist", mini_repo)
    # The check has to run before anything is written, or a missing LICENSE leaves a
    # valid-looking but incomplete archive behind — every skill file present, the
    # licence missing, and nothing about the failed run visible from dist/ itself.
    assert not (tmp_path / "dist" / "alpha.skill").exists()


def test_a_skill_that_does_not_validate_is_refused(mini_repo, tmp_path):
    broken = write_skill(mini_repo, "engineering", "broken", evals=None)
    (broken / "SKILL.md").write_text("---\nname: wrong\n---\n\nBody.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not validate"):
        packager.package(broken, tmp_path / "dist", mini_repo)


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_a_symlink_inside_the_skill_is_refused(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the tree\n", encoding="utf-8")
    (skill / "references").mkdir()
    (skill / "references" / "leak.md").symlink_to(outside)
    with pytest.raises(SystemExit, match="is a symlink"):
        packager.package(skill, tmp_path / "dist", mini_repo)
    assert not (tmp_path / "dist" / "alpha.skill").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_included_never_follows_a_link(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    real = skill / "real.md"
    real.write_text("x", encoding="utf-8")
    (skill / "link.md").symlink_to(real)
    assert packager._included(real, skill)
    assert not packager._included(skill / "link.md", skill)


def test_main_clears_stale_archives_and_packages_every_skill(mini_repo, capsys):
    # Against the fixture, not this repository: a test that rebuilds the developer's
    # own dist/ deletes whatever `make package` just produced and races with it.
    dist = mini_repo / "dist"
    dist.mkdir()
    stale = dist / "renamed-long-ago.skill"
    stale.write_bytes(b"stale")
    assert packager.main(mini_repo) == 0
    out = capsys.readouterr().out
    assert not stale.exists()
    assert [a.stem for a in sorted(dist.glob("*.skill"))] == ["alpha", "beta"]
    assert "packaged 2 skill(s)" in out


def test_a_tree_with_no_skills_exits_two(tmp_path, capsys):
    assert packager.main(tmp_path) == 2
    assert "no skills found" in capsys.readouterr().err


def test_a_cache_directory_nested_below_the_top_level_is_excluded(mini_repo, tmp_path):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references" / "__pycache__").mkdir(parents=True)
    (skill / "references" / "__pycache__" / "x.txt").write_text("x", encoding="utf-8")
    archive = packager.package(skill, tmp_path / "dist", mini_repo)
    assert names_in(archive) == ["alpha/LICENSE.txt", "alpha/NOTICE.txt", "alpha/SKILL.md"]
