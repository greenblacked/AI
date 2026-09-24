"""The check that a `.skill` archive is actually loadable, not just a zip that wrote.

ci.yml's `package` job and release.yml's `release` job both build archives with
`package_skills.py` and then run this against the same `dist/`, which is the point: one
script rather than two copies that can drift.
"""

from __future__ import annotations

import zipfile

from tests.conftest import load_script

verify_archives = load_script("verify_archives.py")
packager = load_script("package_skills.py")


def test_every_archive_built_by_the_packager_verifies(mini_repo, capsys):
    assert packager.main(mini_repo) == 0
    assert verify_archives.verify(mini_repo) == 0
    assert "2 archive(s) verified" in capsys.readouterr().out


def test_no_archives_fails(tmp_path, capsys):
    (tmp_path / "dist").mkdir()
    assert verify_archives.verify(tmp_path) == 1
    assert "no archives" in capsys.readouterr().out


def test_a_dist_directory_that_does_not_exist_fails(tmp_path, capsys):
    assert verify_archives.verify(tmp_path) == 1
    assert "no archives" in capsys.readouterr().out


def test_an_archive_with_no_skill_md_at_its_root_fails(mini_repo, capsys):
    packager.main(mini_repo)
    archive = mini_repo / "dist" / "alpha.skill"
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    assert "alpha/SKILL.md" in names
    # Rewrite the archive with the member moved somewhere else, so it still opens and
    # still has content, but not where the upload route looks for it.
    with zipfile.ZipFile(archive) as bundle:
        content = bundle.read("alpha/SKILL.md")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("alpha/nested/SKILL.md", content)
    assert verify_archives.verify(mini_repo) == 1
    assert "no alpha/SKILL.md" in capsys.readouterr().out


def test_an_archive_whose_skill_md_declares_a_different_name_fails(mini_repo, capsys):
    packager.main(mini_repo)
    archive = mini_repo / "dist" / "alpha.skill"
    with zipfile.ZipFile(archive) as bundle:
        content = bundle.read("alpha/SKILL.md").decode("utf-8")
    renamed = content.replace("name: alpha", "name: renamed")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("alpha/SKILL.md", renamed)
    assert verify_archives.verify(mini_repo) == 1
    assert "declares name" in capsys.readouterr().out


def test_a_corrupt_member_fails(mini_repo, monkeypatch, capsys):
    packager.main(mini_repo)
    archive = mini_repo / "dist" / "alpha.skill"
    with zipfile.ZipFile(archive) as bundle:
        content = bundle.read("alpha/SKILL.md")
    with zipfile.ZipFile(archive, "w") as bundle:
        info = zipfile.ZipInfo("alpha/SKILL.md")
        bundle.writestr(info, content)
    # testzip() only ever reports a CRC mismatch, which the write above did not
    # introduce; instead prove the corrupt-member branch by monkeypatching testzip.
    # monkeypatch restores the original automatically at teardown, unlike a manual
    # try/finally, which leaves the patch in place for every later test if the
    # assertion between save and restore ever raises.
    monkeypatch.setattr(zipfile.ZipFile, "testzip", lambda self: "alpha/SKILL.md")
    assert verify_archives.verify(mini_repo) == 1
    assert "corrupt member" in capsys.readouterr().out


def test_main_reads_the_root_argument(mini_repo, capsys):
    packager.main(mini_repo)
    assert verify_archives.main([str(mini_repo)]) == 0
    assert "2 archive(s) verified" in capsys.readouterr().out
