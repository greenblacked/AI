#!/usr/bin/env python3
"""Cut a release: a `CHANGELOG.md` section and an annotated git tag, nothing else.

Releases are git tags matching ``vX.Y.Z`` plus a changelog entry. The plugin manifests
carry no ``version`` field on purpose — ``validate-plugin`` in `ci.yml` treats the
per-plugin "No version specified" warning as a control, because a git-sourced
marketplace derives its version from the commit, and a tag is what lets an installer
pin to one anyway.

`main` requires a pull request, so cutting a release is two steps, each its own
subcommand here:

``prepare`` runs on a branch. It moves the body of ``## [Unreleased]`` into a new
``## [x.y.z] - YYYY-MM-DD`` section dated today (UTC), leaves an empty ``Unreleased``
above it, and updates the compare-link footer at the bottom of the file if one is
there. It refuses an empty ``Unreleased`` section, a malformed version, and a version
that is not greater than every existing changelog section and git tag — local tags and,
when an ``origin`` remote is configured, tags already pushed there too, since a branch
may not have fetched a tag another release just pushed. Commit the result, open a pull
request, and merge it.

``tag`` runs on `main` after that pull request has merged. It verifies the branch,
a clean working tree, that `HEAD` matches `origin/main`, that the changelog carries a
non-empty section for the version, and that the tag does not already exist locally or
on the remote — then creates an annotated tag whose message is that section's body. It
does not push; it prints the command that does.

``notes`` prints one version's section body with nothing else, which is what
`release.yml` writes into a file for `gh release create --notes-file`.

Standard library only, like every script here. Git is run as a subprocess with argument
lists, never a shell, resolved to an absolute path the way `check_attribution.py`
resolves it.
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHANGELOG = Path("CHANGELOG.md")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# "## [1.2.3] - 2026-09-24" or "## [Unreleased]" — the date suffix is optional so an
# unreleased heading is read by the same pattern as a released one.
HEADING_RE = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$")
# A Keep a Changelog compare-link footer line, e.g. "[1.2.3]: https://.../compare/...".
# Anything shaped like it is skipped when looking for the end of a section, so a section
# with no heading after it (the newest one) does not swallow the footer as its own body.
FOOTER_LINK_RE = re.compile(r"^\[[^\]]+\]:\s")
# "[Unreleased]: https://github.com/x/y/compare/v1.0.0...HEAD" — the one footer line
# `prepare` rewrites, and the one it reads the previous version and the base URL from.
UNRELEASED_LINK_RE = re.compile(
    r"^\[Unreleased\]:\s*(?P<base>.+)/compare/v(?P<from>\d+\.\d+\.\d+)\.\.\.HEAD\s*$"
)


def git_binary() -> str | None:
    """The absolute path to git, never a bare name a stale PATH entry could shadow."""
    return shutil.which("git")


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    git = git_binary()
    if git is None:
        raise SystemExit("git is not on PATH")
    result = subprocess.run(  # noqa: S603 - absolute path, fixed argv, no shell
        [git, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or f"git {' '.join(args)} failed").strip())
    return result


def normalize_version(version: str) -> str:
    """Accept "1.2.3" or "v1.2.3" alike; validation happens on the stripped form."""
    return version[1:] if version[:1] in ("v", "V") else version


def version_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


# --- reading and editing the changelog ------------------------------------------------


def heading_indices(lines: list[str]) -> list[tuple[int, str, str | None]]:
    """Every `## [name]` or `## [name] - date` heading, as (line index, name, date)."""
    found = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            found.append((index, match.group(1), match.group(2)))
    return found


def find_heading(headings: list[tuple[int, str, str | None]], name: str) -> int | None:
    for index, heading_name, _ in headings:
        if heading_name == name:
            return index
    return None


def section_end(lines: list[str], headings: list[tuple[int, str, str | None]], start: int) -> int:
    """Where a section's body stops: the next heading, the compare-link footer if
    there is no heading after it (the newest section otherwise swallows the footer as
    its own body), or the end of the file."""
    later_headings = [index for index, _, _ in headings if index > start]
    if later_headings:
        return min(later_headings)
    for index in range(start + 1, len(lines)):
        if FOOTER_LINK_RE.match(lines[index]):
            return index
    return len(lines)


def section_body(
    lines: list[str], headings: list[tuple[int, str, str | None]], name: str
) -> str | None:
    """The trimmed body of one section, or None when there is no such heading."""
    start = find_heading(headings, name)
    if start is None:
        return None
    end = section_end(lines, headings, start)
    body = lines[start + 1 : end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body)


def changelog_versions(headings: list[tuple[int, str, str | None]]) -> list[str]:
    """Every released version already in the changelog, "Unreleased" excluded."""
    return [name for _, name, _ in headings if name != "Unreleased" and VERSION_RE.match(name)]


def existing_tag_versions(root: Path) -> list[str]:
    """Every `vX.Y.Z` tag already in the local repository, or [] with no git or no repo."""
    if git_binary() is None:
        return []
    result = run_git(root, "tag", "--list", "v*", check=False)
    if result.returncode != 0:
        return []
    versions = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("v") and VERSION_RE.match(line[1:]):
            versions.append(line[1:])
    return versions


def has_remote(root: Path, name: str) -> bool:
    """Whether `name` is configured as a remote at all."""
    if git_binary() is None:
        return False
    result = run_git(root, "remote", check=False)
    if result.returncode != 0:
        return False
    return name in result.stdout.split()


def existing_remote_tag_versions(root: Path) -> list[str]:
    """Every `vX.Y.Z` tag already pushed to `origin`, or [] with no such remote.

    `prepare` runs on a branch, which may not have fetched every tag a release already
    pushed — a fresh clone, or one that simply has not fetched lately. Local tags alone
    would miss that case; asking `origin` directly does not. Skipped with a notice
    rather than failing when there is no `origin` remote or it cannot be reached,
    because `prepare` still has to work on a branch with neither.
    """
    if not has_remote(root, "origin"):
        print("no origin remote configured; not checking it for an existing tag")
        return []
    result = run_git(root, "ls-remote", "--tags", "origin", check=False)
    if result.returncode != 0:
        print(f"could not reach origin to check for an existing tag: {result.stderr.strip()}")
        return []
    versions = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.endswith("^{}"):
            continue  # a peeled annotated-tag ref, not a tag name of its own
        prefix = "refs/tags/v"
        if ref.startswith(prefix) and VERSION_RE.match(ref[len(prefix) :]):
            versions.append(ref[len(prefix) :])
    return versions


def rewrite_footer(lines: list[str], new_version: str) -> None:
    """Update the compare-link footer in place, if the changelog carries one.

    Not every changelog does — Keep a Changelog treats the footer as optional — so this
    is a no-op rather than an error when `[Unreleased]:` is not written as a compare
    link against a previous tag.
    """
    for index, line in enumerate(lines):
        match = UNRELEASED_LINK_RE.match(line)
        if match:
            base = match.group("base")
            previous = match.group("from")
            lines[index] = f"[Unreleased]: {base}/compare/v{new_version}...HEAD"
            lines.insert(index + 1, f"[{new_version}]: {base}/compare/v{previous}...v{new_version}")
            return


def build_release_section(lines: list[str], version: str, date: str) -> list[str]:
    """`lines` with `## [Unreleased]`'s body moved into a new dated section above it,
    and the compare-link footer updated if there is one."""
    headings = heading_indices(lines)
    unreleased_index = find_heading(headings, "Unreleased")
    if unreleased_index is None:
        raise SystemExit(f"{CHANGELOG} has no ## [Unreleased] section")
    end = section_end(lines, headings, unreleased_index)

    body = lines[unreleased_index + 1 : end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()

    before = lines[: unreleased_index + 1]
    after = lines[end:]
    new_section = ["", f"## [{version}] - {date}"]
    if body:
        new_section += [""] + body
    new_section += [""]

    result = before + new_section + after
    rewrite_footer(result, version)
    return result


# --- prepare ----------------------------------------------------------------------


def prepare(root: Path, version: str) -> int:
    version = normalize_version(version)
    if not VERSION_RE.match(version):
        print(f"::error::{version!r} is not a valid x.y.z version", file=sys.stderr)
        return 1

    path = root / CHANGELOG
    if not path.is_file():
        print(f"::error::{CHANGELOG} does not exist", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = heading_indices(lines)

    unreleased = section_body(lines, headings, "Unreleased")
    if unreleased is None:
        print(f"::error::{CHANGELOG} has no ## [Unreleased] section", file=sys.stderr)
        return 1
    if not unreleased.strip():
        print("::error::the Unreleased section is empty; nothing to release", file=sys.stderr)
        return 1

    known = (
        set(changelog_versions(headings))
        | set(existing_tag_versions(root))
        | set(existing_remote_tag_versions(root))
    )
    if version in known:
        print(
            f"::error::version {version} already exists as a changelog section or a git tag",
            file=sys.stderr,
        )
        return 1
    if known:
        newest = max(known, key=version_key)
        if version_key(version) <= version_key(newest):
            print(
                f"::error::version {version} is not greater than the newest existing "
                f"version {newest}",
                file=sys.stderr,
            )
            return 1

    date = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    new_lines = build_release_section(lines, version, date)
    trailing_newline = "\n" if text.endswith("\n") else ""
    path.write_text("\n".join(new_lines) + trailing_newline, encoding="utf-8")

    print(f"moved Unreleased into [{version}] - {date} in {CHANGELOG}")
    print("next steps:")
    print(f"  git add {CHANGELOG}")
    print(f'  git commit -m "Prepare the {version} release"')
    print("  open a pull request and merge it")
    print(f"  then, on main: make release VERSION={version}")
    return 0


# --- tag ----------------------------------------------------------------------------


def current_branch(root: Path) -> str:
    return run_git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def working_tree_clean(root: Path) -> bool:
    # `--porcelain` lists untracked files too, unless told not to; that is what makes
    # this cover "including untracked files" rather than only tracked changes.
    return run_git(root, "status", "--porcelain").stdout.strip() == ""


def rev_parse(root: Path, ref: str) -> str | None:
    result = run_git(root, "rev-parse", ref, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def tag_exists_locally(root: Path, tag_name: str) -> bool:
    result = run_git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}", check=False)
    return result.returncode == 0


def tag_exists_on_remote(root: Path, tag_name: str) -> bool:
    result = run_git(root, "ls-remote", "--tags", "origin", check=False)
    if result.returncode != 0:
        raise SystemExit((result.stderr or "git ls-remote --tags origin failed").strip())
    ref = f"refs/tags/{tag_name}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return True
    return False


def tag(root: Path, version: str) -> int:
    version = normalize_version(version)
    if not VERSION_RE.match(version):
        print(f"::error::{version!r} is not a valid x.y.z version", file=sys.stderr)
        return 1

    branch = current_branch(root)
    if branch != "main":
        print(f"::error::release must run on main, not {branch}", file=sys.stderr)
        return 1

    if not working_tree_clean(root):
        print(
            "::error::the working tree is not clean (tracked or untracked changes)", file=sys.stderr
        )
        return 1

    path = root / CHANGELOG
    if not path.is_file():
        print(f"::error::{CHANGELOG} does not exist", file=sys.stderr)
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()
    headings = heading_indices(lines)
    body = section_body(lines, headings, version)
    if body is None:
        print(f"::error::{CHANGELOG} has no [{version}] section", file=sys.stderr)
        return 1
    if not body.strip():
        print(f"::error::the [{version}] section in {CHANGELOG} is empty", file=sys.stderr)
        return 1

    # Checked before the fetch below: fetching `--tags` would otherwise pull an
    # already-pushed tag into a local ref of its own, which would then make
    # `tag_exists_locally` true for a tag this run never created and hide the
    # "already exists on origin" case behind a misleading "already exists locally".
    tag_name = f"v{version}"
    if tag_exists_locally(root, tag_name):
        print(f"::error::tag {tag_name} already exists locally", file=sys.stderr)
        return 1
    if tag_exists_on_remote(root, tag_name):
        print(f"::error::tag {tag_name} already exists on origin", file=sys.stderr)
        return 1

    run_git(root, "fetch", "origin", "main:refs/remotes/origin/main", "--tags")
    head = rev_parse(root, "HEAD")
    origin_main = rev_parse(root, "refs/remotes/origin/main")
    if head is None or origin_main is None or head != origin_main:
        print("::error::HEAD is not up to date with origin/main; pull first", file=sys.stderr)
        return 1

    git = git_binary()
    if git is None:
        raise SystemExit("git is not on PATH")
    result = subprocess.run(  # noqa: S603 - absolute path, fixed argv, message via stdin
        # `--cleanup=verbatim` is load-bearing: git's default `strip` cleanup for a
        # tag message drops every line starting with `#`, and a changelog section
        # commonly has `### Added` / `### Fixed` subheadings that would otherwise
        # vanish from the tag silently.
        [git, "tag", "-a", tag_name, "--cleanup=verbatim", "-F", "-"],
        cwd=root,
        input=body + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit((result.stderr or "git tag failed").strip())

    print(f"created annotated tag {tag_name}")
    print("next step:")
    print(f"  git push origin {tag_name}")
    return 0


# --- notes ----------------------------------------------------------------------------


def notes(root: Path, version: str) -> int:
    version = normalize_version(version)
    path = root / CHANGELOG
    if not path.is_file():
        print(f"::error::{CHANGELOG} does not exist", file=sys.stderr)
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()
    headings = heading_indices(lines)
    body = section_body(lines, headings, version)
    if body is None or not body.strip():
        print(f"::error::no non-empty [{version}] section in {CHANGELOG}", file=sys.stderr)
        return 1
    print(body)
    return 0


# --- CLI --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", default=".", type=Path, help="repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare", help="move Unreleased into a new dated section on a branch"
    )
    prepare_parser.add_argument("version", help="the version to release, e.g. 1.2.3")

    tag_parser = subparsers.add_parser(
        "tag", help="tag the release on main after the prepare pull request has merged"
    )
    tag_parser.add_argument("version", help="the version to release, e.g. 1.2.3")

    notes_parser = subparsers.add_parser(
        "notes", help="print one version's changelog section body and nothing else"
    )
    notes_parser.add_argument("version", help="the version whose notes to print, e.g. 1.2.3")

    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "prepare":
        return prepare(root, args.version)
    if args.command == "tag":
        return tag(root, args.version)
    return notes(root, args.version)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
