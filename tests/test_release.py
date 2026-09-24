"""`scripts/release.py`: moving CHANGELOG's Unreleased section into a dated one on a
branch, and tagging it on `main` once that pull request has merged.

Every git operation runs against a real temporary repository with a real bare repo as
its `origin`, the same way `test_attribution.py` builds one, rather than against a
mocked subprocess — the checks here are precisely about what git reports.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from tests.conftest import load_script

release = load_script("release.py")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def git(repo, *args, env=None, check=True):
    return subprocess.run(  # noqa: S603 - fixed argv, test fixture only
        ["git", *args],  # noqa: S607 - resolved against PATH like every other git call here
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


CHANGELOG_WITH_UNRELEASED_BODY = """# Changelog

## [Unreleased]

- Added a new thing.

## [1.0.0] - 2026-01-01

- Initial release.

[Unreleased]: https://example.com/owner/repo/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/owner/repo/releases/tag/v1.0.0
"""

CHANGELOG_EMPTY_UNRELEASED = """# Changelog

## [Unreleased]

## [1.0.0] - 2026-01-01

- Initial release.
"""

CHANGELOG_EMPTY_VERSION_SECTION = """# Changelog

## [Unreleased]

- Something changed.

## [1.0.0] - 2026-01-01
"""

CHANGELOG_NO_FOOTER = """# Changelog

## [Unreleased]

- Something changed.

## [1.0.0] - 2026-01-01

- Initial release.
"""


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))

    directory = tmp_path / "repo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Test User")
    git(directory, "config", "user.email", "test@example.com")
    (directory / "CHANGELOG.md").write_text(CHANGELOG_WITH_UNRELEASED_BODY, encoding="utf-8")
    git(directory, "add", "CHANGELOG.md")
    git(directory, "commit", "-q", "-m", "initial")
    git(directory, "remote", "add", "origin", str(origin))
    git(directory, "push", "-q", "-u", "origin", "main")
    return directory


def write_changelog(repo, text):
    (repo / "CHANGELOG.md").write_text(text, encoding="utf-8")


def commit_all(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


# --- normalize_version and version_key -------------------------------------------


def test_normalize_version_strips_a_leading_v():
    assert release.normalize_version("v1.2.3") == "1.2.3"
    assert release.normalize_version("V1.2.3") == "1.2.3"
    assert release.normalize_version("1.2.3") == "1.2.3"


def test_version_key_orders_numerically_not_lexically():
    assert release.version_key("1.9.0") < release.version_key("1.10.0")


# --- prepare ------------------------------------------------------------------------


def test_prepare_moves_unreleased_into_a_new_dated_section(repo, capsys):
    assert release.prepare(repo, "1.1.0") == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## [Unreleased]\n\n## [1.1.0] - " in text
    assert "- Added a new thing." in text
    match = re.search(r"## \[1\.1\.0\] - (\d{4}-\d{2}-\d{2})", text)
    assert match and DATE_RE.match(match.group(1))
    # The old section is untouched and still below the new one.
    assert text.index("## [1.1.0]") < text.index("## [1.0.0]")
    # The compare-link footer follows the new version along.
    assert "[Unreleased]: https://example.com/owner/repo/compare/v1.1.0...HEAD" in text
    assert "[1.1.0]: https://example.com/owner/repo/compare/v1.0.0...v1.1.0" in text
    assert "[1.0.0]: https://example.com/owner/repo/releases/tag/v1.0.0" in text

    out = capsys.readouterr().out
    assert "moved Unreleased into [1.1.0]" in out
    assert "make release VERSION=1.1.0" in out


def test_prepare_accepts_a_leading_v(repo):
    assert release.prepare(repo, "v1.1.0") == 0
    assert "## [1.1.0] - " in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_prepare_leaves_the_changelog_untouched_with_no_footer(repo):
    write_changelog(repo, CHANGELOG_NO_FOOTER)
    assert release.prepare(repo, "1.1.0") == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.1.0] - " in text
    assert "Something changed." in text
    assert "compare" not in text  # no footer to rewrite, and none invented


def test_prepare_refuses_an_empty_unreleased_section(repo, capsys):
    write_changelog(repo, CHANGELOG_EMPTY_UNRELEASED)
    assert release.prepare(repo, "1.1.0") == 1
    assert "empty" in capsys.readouterr().err


def test_prepare_refuses_a_malformed_version(repo, capsys):
    assert release.prepare(repo, "1.2") == 1
    assert "not a valid" in capsys.readouterr().err


def test_prepare_refuses_a_version_that_already_exists_as_a_section(repo, capsys):
    assert release.prepare(repo, "1.0.0") == 1
    assert "already exists" in capsys.readouterr().err


def test_prepare_refuses_a_version_not_greater_than_the_newest_section(repo, capsys):
    assert release.prepare(repo, "0.9.0") == 1
    assert "not greater than the newest existing version 1.0.0" in capsys.readouterr().err


def test_prepare_refuses_a_version_that_already_exists_as_a_tag(repo, capsys):
    git(repo, "tag", "v2.0.0")
    assert release.prepare(repo, "2.0.0") == 1
    assert "already exists" in capsys.readouterr().err


def test_prepare_refuses_a_version_not_greater_than_an_existing_tag(repo, capsys):
    git(repo, "tag", "v1.5.0")
    assert release.prepare(repo, "1.2.0") == 1
    assert "not greater than the newest existing version 1.5.0" in capsys.readouterr().err


def test_prepare_refuses_a_version_that_exists_only_as_a_remote_tag(repo, capsys):
    # Pushed to origin but never fetched down locally — the case a branch that has not
    # fetched lately, or a fresh clone, would otherwise miss entirely.
    git(repo, "tag", "v3.0.0")
    git(repo, "push", "-q", "origin", "v3.0.0")
    git(repo, "tag", "-d", "v3.0.0")
    assert release.existing_tag_versions(repo) == []
    assert release.prepare(repo, "3.0.0") == 1
    assert "already exists" in capsys.readouterr().err


def test_prepare_refuses_a_version_not_greater_than_a_remote_only_tag(repo, capsys):
    git(repo, "tag", "v1.8.0")
    git(repo, "push", "-q", "origin", "v1.8.0")
    git(repo, "tag", "-d", "v1.8.0")
    assert release.prepare(repo, "1.3.0") == 1
    assert "not greater than the newest existing version 1.8.0" in capsys.readouterr().err


def test_prepare_skips_the_remote_tag_check_with_no_origin_configured(tmp_path, capsys):
    directory = tmp_path / "solo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Test User")
    git(directory, "config", "user.email", "test@example.com")
    write_changelog(directory, CHANGELOG_WITH_UNRELEASED_BODY)
    commit_all(directory, "initial")
    assert release.prepare(directory, "1.1.0") == 0
    assert "no origin remote configured" in capsys.readouterr().out


def test_prepare_refuses_when_the_changelog_is_missing(tmp_path, capsys):
    assert release.prepare(tmp_path, "1.0.0") == 1
    assert "does not exist" in capsys.readouterr().err


def test_prepare_refuses_when_there_is_no_unreleased_heading(repo, capsys):
    write_changelog(repo, "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n- Initial release.\n")
    assert release.prepare(repo, "1.1.0") == 1
    assert "Unreleased" in capsys.readouterr().err


def test_prepare_succeeds_as_the_first_release_ever(repo):
    # No prior version section and no tag: `known` is empty, so there is nothing to
    # compare the new version against.
    write_changelog(repo, "# Changelog\n\n## [Unreleased]\n\n- First feature.\n")
    assert release.prepare(repo, "0.1.0") == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0] - " in text
    assert "First feature." in text


def test_build_release_section_raises_without_an_unreleased_heading():
    with pytest.raises(SystemExit, match="Unreleased"):
        release.build_release_section(
            ["# Changelog", "", "## [1.0.0] - 2026-01-01"], "1.1.0", "2026-02-02"
        )


# --- tag ------------------------------------------------------------------------------


def prepare_and_land(repo, version):
    """`prepare`, commit and push, as the maintainer does between the two steps."""
    assert release.prepare(repo, version) == 0
    commit_all(repo, f"Prepare the {version} release")
    git(repo, "push", "-q", "origin", "main")


def test_tag_refuses_off_main(repo, capsys):
    git(repo, "checkout", "-q", "-b", "feature")
    assert release.tag(repo, "1.0.0") == 1
    assert "must run on main" in capsys.readouterr().err


def test_tag_refuses_a_dirty_working_tree(repo, capsys):
    (repo / "untracked.txt").write_text("x", encoding="utf-8")
    assert release.tag(repo, "1.0.0") == 1
    assert "not clean" in capsys.readouterr().err


def test_tag_refuses_when_head_is_behind_origin_main(repo, capsys):
    git(repo, "commit", "-q", "--allow-empty", "-m", "a local commit not yet pushed")
    assert release.tag(repo, "1.0.0") == 1
    assert "not up to date with origin/main" in capsys.readouterr().err


def test_tag_refuses_a_missing_section(repo, capsys):
    assert release.tag(repo, "9.9.9") == 1
    assert "has no [9.9.9] section" in capsys.readouterr().err


def test_tag_refuses_an_empty_section(repo, capsys):
    write_changelog(
        repo,
        CHANGELOG_WITH_UNRELEASED_BODY.replace(
            "## [1.0.0] - 2026-01-01\n\n- Initial release.",
            "## [1.0.0] - 2026-01-01\n",
        ),
    )
    commit_all(repo, "empty the 1.0.0 section")
    git(repo, "push", "-q", "origin", "main")
    assert release.tag(repo, "1.0.0") == 1
    assert "is empty" in capsys.readouterr().err


def test_tag_refuses_when_the_tag_exists_locally(repo, capsys):
    git(repo, "tag", "v1.0.0")
    assert release.tag(repo, "1.0.0") == 1
    assert "already exists locally" in capsys.readouterr().err


def test_tag_refuses_when_the_tag_exists_on_the_remote(repo, capsys):
    git(repo, "tag", "v1.0.0")
    git(repo, "push", "-q", "origin", "v1.0.0")
    git(repo, "tag", "-d", "v1.0.0")
    assert release.tag(repo, "1.0.0") == 1
    assert "already exists on origin" in capsys.readouterr().err


def test_tag_creates_an_annotated_tag_with_the_section_as_its_message(repo, capsys):
    # git's default tag-message cleanup ("strip") drops any line starting with "#",
    # which is exactly the shape of a Keep a Changelog subheading. This is what
    # proves `--cleanup=verbatim` is doing its job rather than silently eating them.
    write_changelog(
        repo,
        CHANGELOG_WITH_UNRELEASED_BODY.replace(
            "## [1.0.0] - 2026-01-01\n\n- Initial release.",
            "## [1.0.0] - 2026-01-01\n\n"
            "### Added\n\n- Initial release.\n\n"
            "### Fixed\n\n- Nothing yet.",
        ),
    )
    commit_all(repo, "give the 1.0.0 section subheadings")
    git(repo, "push", "-q", "origin", "main")

    assert release.tag(repo, "1.0.0") == 0
    out = capsys.readouterr().out
    assert "created annotated tag v1.0.0" in out
    assert "git push origin v1.0.0" in out

    show = git(repo, "for-each-ref", "refs/tags/v1.0.0", "--format=%(contents)")
    assert "### Added" in show.stdout
    assert "### Fixed" in show.stdout
    assert "Initial release." in show.stdout
    assert "Nothing yet." in show.stdout
    kind = git(repo, "cat-file", "-t", "refs/tags/v1.0.0")
    assert kind.stdout.strip() == "tag"  # annotated, not lightweight

    # tag does not push on its own.
    remote_tags = git(repo, "ls-remote", "--tags", "origin")
    assert "refs/tags/v1.0.0" not in remote_tags.stdout


def test_tag_refuses_a_malformed_version(repo, capsys):
    assert release.tag(repo, "1.0") == 1
    assert "not a valid" in capsys.readouterr().err


def test_prepare_then_land_then_tag_end_to_end(repo):
    assert release.prepare(repo, "1.1.0") == 0
    prepare_and_land_note = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.1.0]" in prepare_and_land_note
    commit_all(repo, "Prepare the 1.1.0 release")
    git(repo, "push", "-q", "origin", "main")

    assert release.tag(repo, "1.1.0") == 0
    show = git(repo, "for-each-ref", "refs/tags/v1.1.0", "--format=%(contents)")
    assert "Added a new thing." in show.stdout


# --- notes ----------------------------------------------------------------------------


def test_notes_prints_the_section_body_and_nothing_else(repo, capsys):
    assert release.notes(repo, "1.0.0") == 0
    assert capsys.readouterr().out.strip() == "- Initial release."


def test_notes_accepts_a_leading_v(repo, capsys):
    assert release.notes(repo, "v1.0.0") == 0
    assert "Initial release." in capsys.readouterr().out


def test_notes_refuses_a_missing_version(repo, capsys):
    assert release.notes(repo, "9.9.9") == 1
    assert "no non-empty" in capsys.readouterr().err


def test_notes_refuses_an_empty_section(repo, capsys):
    write_changelog(repo, CHANGELOG_EMPTY_VERSION_SECTION)
    assert release.notes(repo, "1.0.0") == 1
    assert "no non-empty" in capsys.readouterr().err


def test_notes_refuses_when_the_changelog_is_missing(tmp_path, capsys):
    assert release.notes(tmp_path, "1.0.0") == 1
    assert "does not exist" in capsys.readouterr().err


# --- git plumbing and error handling -------------------------------------------------


def test_git_binary_resolves_to_an_absolute_path():
    import os

    path = release.git_binary()
    assert path is not None
    assert os.path.isabs(path)


def test_run_git_raises_when_git_is_not_on_path(monkeypatch, repo):
    monkeypatch.setattr(release.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="git is not on PATH"):
        release.run_git(repo, "status")


def test_run_git_raises_on_a_failed_command(repo):
    with pytest.raises(SystemExit):
        release.run_git(repo, "not-a-real-git-command")


def test_tag_exists_on_remote_raises_when_there_is_no_origin(tmp_path):
    directory = tmp_path / "solo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Test User")
    git(directory, "config", "user.email", "test@example.com")
    git(directory, "commit", "-q", "--allow-empty", "-m", "initial")
    with pytest.raises(SystemExit):
        release.tag_exists_on_remote(directory, "v1.0.0")


def test_existing_tag_versions_is_empty_with_no_matching_tags(repo):
    assert release.existing_tag_versions(repo) == []


def test_existing_tag_versions_is_empty_outside_a_git_repository(tmp_path):
    directory = tmp_path / "not-a-repo"
    directory.mkdir()
    assert release.existing_tag_versions(directory) == []


def test_tag_exists_on_remote_ignores_other_refs(repo):
    git(repo, "tag", "v9.0.0")
    git(repo, "push", "-q", "origin", "v9.0.0")
    assert release.tag_exists_on_remote(repo, "v1.0.0") is False


def test_tag_refuses_when_the_changelog_is_missing(repo, capsys):
    (repo / "CHANGELOG.md").unlink()
    commit_all(repo, "remove the changelog")
    git(repo, "push", "-q", "origin", "main")
    assert release.tag(repo, "1.0.0") == 1
    assert "does not exist" in capsys.readouterr().err


def test_tag_raises_when_git_disappears_right_before_creating_the_tag(repo, monkeypatch):
    # Every check up to this point goes through `run_git`, which resolves its own path;
    # only the final, direct `git_binary()` call in `tag()` is under test here, so every
    # earlier step is stubbed to succeed without needing git at all.
    monkeypatch.setattr(release, "current_branch", lambda root: "main")
    monkeypatch.setattr(release, "working_tree_clean", lambda root: True)
    monkeypatch.setattr(release, "tag_exists_locally", lambda root, name: False)
    monkeypatch.setattr(release, "tag_exists_on_remote", lambda root, name: False)
    monkeypatch.setattr(release, "run_git", lambda *a, **k: None)
    monkeypatch.setattr(release, "rev_parse", lambda root, ref: "same-sha")
    monkeypatch.setattr(release, "git_binary", lambda: None)
    with pytest.raises(SystemExit, match="git is not on PATH"):
        release.tag(repo, "1.0.0")


def test_tag_raises_when_git_tag_itself_fails(repo, monkeypatch):
    real_run = release.subprocess.run

    def fake_run(argv, **kwargs):
        if len(argv) > 1 and argv[1] == "tag":
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="git tag exploded")
        return real_run(argv, **kwargs)

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    with pytest.raises(SystemExit, match="git tag exploded"):
        release.tag(repo, "1.0.0")


def test_existing_tag_versions_lists_only_valid_semver_tags(repo):
    git(repo, "tag", "v1.2.3")
    git(repo, "tag", "not-a-version")
    git(repo, "tag", "v2.0")  # not x.y.z, ignored
    assert release.existing_tag_versions(repo) == ["1.2.3"]


def test_has_remote_true_for_a_configured_remote(repo):
    assert release.has_remote(repo, "origin") is True
    assert release.has_remote(repo, "upstream") is False


def test_has_remote_false_with_no_remotes_at_all(tmp_path):
    directory = tmp_path / "solo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    assert release.has_remote(directory, "origin") is False


def test_existing_remote_tag_versions_is_empty_with_no_origin(tmp_path, capsys):
    directory = tmp_path / "solo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    assert release.existing_remote_tag_versions(directory) == []
    assert "no origin remote configured" in capsys.readouterr().out


def test_existing_remote_tag_versions_lists_only_valid_semver_tags_from_origin(repo):
    git(repo, "tag", "v1.2.3")
    git(repo, "tag", "not-a-version")
    for name in ("v1.2.3", "not-a-version"):
        git(repo, "push", "-q", "origin", name)
    assert release.existing_remote_tag_versions(repo) == ["1.2.3"]


def test_existing_remote_tag_versions_ignores_a_peeled_ref(repo):
    # An annotated tag's peeled object shows up in `ls-remote` as a second line for
    # the same ref, suffixed `^{}`; it must not be read as a second tag named that.
    git(repo, "tag", "-a", "v4.0.0", "-m", "annotated")
    git(repo, "push", "-q", "origin", "v4.0.0")
    assert release.existing_remote_tag_versions(repo) == ["4.0.0"]


def test_existing_remote_tag_versions_reports_and_skips_an_unreachable_origin(
    repo, monkeypatch, capsys
):
    monkeypatch.setattr(release, "has_remote", lambda root, name: True)
    real_run = release.run_git

    def fake_run_git(root, *args, **kwargs):
        if args[:1] == ("ls-remote",):
            result = subprocess.CompletedProcess(
                args, 1, stdout="", stderr="could not resolve host"
            )
            return result
        return real_run(root, *args, **kwargs)

    monkeypatch.setattr(release, "run_git", fake_run_git)
    assert release.existing_remote_tag_versions(repo) == []
    assert "could not reach origin" in capsys.readouterr().out


# --- the CLI --------------------------------------------------------------------------


def test_main_prepare_via_argv(repo):
    assert release.main(["--root", str(repo), "prepare", "1.1.0"]) == 0
    assert "## [1.1.0]" in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_main_tag_via_argv(repo):
    assert release.main(["--root", str(repo), "tag", "1.0.0"]) == 0


def test_main_notes_via_argv(repo, capsys):
    assert release.main(["--root", str(repo), "notes", "1.0.0"]) == 0
    assert "Initial release." in capsys.readouterr().out


def test_main_requires_a_version_argument(repo):
    with pytest.raises(SystemExit):
        release.main(["--root", str(repo), "prepare"])


def test_main_requires_a_command():
    with pytest.raises(SystemExit):
        release.main([])
