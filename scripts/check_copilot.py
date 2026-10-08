#!/usr/bin/env python3
"""Fail when a Copilot wrapper has drifted from the Claude Code file it mirrors.

`.github/instructions/`, `.github/agents/` and `.github/prompts/` hold short wrappers
around the files Claude Code reads from `.claude/` and `REVIEW.md`. A wrapper restates the
key rules inline, because Copilot's reviewer may not follow a link, so it is a copy that
can go stale: edit `.claude/rules/skills.md` and the Copilot rules for skills keep saying
the old thing, with no error anywhere. This check pins each wrapper to the exact bytes of
the file it was written from, so a source edit that nobody carried across fails the build.

Each source maps to one wrapper by name:

- `.claude/rules/<name>.md` to `.github/instructions/<name>.instructions.md`
- a nested `.claude/rules/<dir>/<name>.md` to `.github/instructions/<dir>-<name>.instructions.md`
- `REVIEW.md` to `.github/instructions/review.instructions.md`
- `.claude/agents/<name>.md` to `.github/agents/<name>.agent.md`
- `.claude/commands/<name>.md` to `.github/prompts/<name>.prompt.md`, nested the same way
  (`.claude/commands/<dir>/<name>.md` to `.github/prompts/<dir>-<name>.prompt.md`)

Rules and commands are found recursively, because Claude Code discovers both in
subdirectories; a nested file skipped here would be a source with no wrapper and no error.
Two sources that map to the same wrapper name (`a/b-c.md` and `a-b/c.md`, or a rule named
`review.md` beside `REVIEW.md`) fail rather than share a wrapper. `.claude/agents/` is not
recursive: its subfolders hold benchmark cases and eval sets, not agents.

The first line of a wrapper's body, right after its front matter, is a comment naming
the source and the SHA-256 of the source's bytes:

    <!-- source: .claude/rules/skills.md sha256: <64 hex characters> -->

Three things fail, all mechanical:

- a source with no wrapper, or a wrapper with no such comment
- a wrapper whose recorded hash differs from its source's
- a wrapper whose comment points at a source that does not exist, or at a different one
  than its own name maps to

What is not checked is whether the wrapper says the same thing as its source. A hash proves
the source has not changed since a person last read it, not that the person read it well,
and a check that guessed at meaning would fail a correct wrapper. A wrapper under these
folders with no comment and no source of that name is hand-written and left alone.

To update a wrapper after its source changed:

1. Read the diff of the source (`git diff -- <source>`) and carry the change into the
   wrapper's text.
2. Take the new hash with `sha256sum <source>` (or `shasum -a 256 <source>` on macOS),
   which hashes the file's bytes, as this check does.
3. Put that hash in the wrapper's first comment line. Re-run `make catalogue`.

This is check-only on purpose: a command that rewrote the hash by itself would turn the
check into a formality, because the hash is what records that a person re-read the source.
The skills under `plugins/` are not mirrored here at all; they are not duplicated for Copilot.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# (source folder, source suffix, wrapper folder, wrapper suffix, discovered recursively)
RULES = (
    (Path(".claude/rules"), ".md", Path(".github/instructions"), ".instructions.md", True),
    (Path(".claude/agents"), ".md", Path(".github/agents"), ".agent.md", False),
    (Path(".claude/commands"), ".md", Path(".github/prompts"), ".prompt.md", True),
)
# One source that is a single file rather than a folder of them.
REVIEW_SOURCE = Path("REVIEW.md")
REVIEW_WRAPPER = Path(".github/instructions/review.instructions.md")

MARKER_RE = re.compile(r"^<!--\s*source:\s*(\S+)\s+sha256:\s*([0-9A-Fa-f]+)\s*-->\s*$")
FRONT_MATTER_FENCE = "---"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_pairs(
    root: Path, collisions: list[tuple[Path, str]] | None = None
) -> dict[Path, Path]:
    """Every source that must have a wrapper, mapped to the wrapper it must have.

    A nested source joins its relative path parts with "-" for the wrapper name. Sources
    that land on one wrapper are reported in `collisions` as (skipped source, message) when
    given, and only the first is kept, so the report names the clash instead of one
    wrapper silently serving two.
    """
    pairs: dict[Path, Path] = {}
    claimed: dict[Path, Path] = {}

    def claim(source: Path, wrapper: Path) -> None:
        if wrapper in claimed:
            if collisions is not None:
                collisions.append(
                    (
                        source,
                        f"{source.as_posix()} and {claimed[wrapper].as_posix()} both map to "
                        f"{wrapper.as_posix()}; rename one so each source has its own wrapper",
                    )
                )
            return
        claimed[wrapper] = source
        pairs[source] = wrapper

    for source_dir, suffix, wrapper_dir, wrapper_suffix, recursive in RULES:
        folder = root / source_dir
        if not folder.is_dir():
            continue
        found = folder.rglob(f"*{suffix}") if recursive else folder.glob(f"*{suffix}")
        for source in sorted(path for path in found if path.is_file()):
            relative = source.relative_to(folder).with_suffix("")
            claim(
                source_dir / source.relative_to(folder),
                wrapper_dir / ("-".join(relative.parts) + wrapper_suffix),
            )
    if (root / REVIEW_SOURCE).is_file():
        claim(REVIEW_SOURCE, REVIEW_WRAPPER)
    return pairs


def read_marker(path: Path) -> tuple[str, str] | None:
    """The (source, hash) a wrapper records, or None when its body has no such first line.

    The body starts after the front matter, which Copilot needs to be the very first
    thing in the file. A wrapper without front matter starts its body at line one.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    if lines and lines[0].strip() == FRONT_MATTER_FENCE:
        for end in range(1, len(lines)):
            if lines[end].strip() == FRONT_MATTER_FENCE:
                index = end + 1
                break
        else:
            return None
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return None
    match = MARKER_RE.match(lines[index])
    if not match:
        return None
    return match.group(1), match.group(2).lower()


def wrapper_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for _, _, wrapper_dir, wrapper_suffix, _ in RULES:
        folder = root / wrapper_dir
        if folder.is_dir():
            found.extend(
                wrapper_dir / path.name for path in sorted(folder.glob(f"*{wrapper_suffix}"))
            )
    return sorted(set(found))


def check(root: Path) -> int:
    if not root.is_dir() or not ((root / ".claude").is_dir() or (root / REVIEW_SOURCE).is_file()):
        print(
            f"::error::{root} is not a repository root: it has no .claude/ and no REVIEW.md",
            file=sys.stderr,
        )
        return 1
    problems: list[str] = []

    def fail(path: Path, message: str) -> None:
        problems.append(message)
        print(f"::error file={path.as_posix()}::{message}")

    collisions: list[tuple[Path, str]] = []
    pairs = expected_pairs(root, collisions)
    for skipped, message in collisions:
        fail(skipped, message)
    by_wrapper = {wrapper: source for source, wrapper in pairs.items()}

    for source, wrapper in sorted(pairs.items()):
        if not (root / wrapper).is_file():
            fail(
                source,
                f"{source.as_posix()} has no Copilot wrapper; write {wrapper.as_posix()} "
                f"starting with `<!-- source: {source.as_posix()} sha256: <hash> -->`",
            )

    checked = 0
    for wrapper in sorted(set(wrapper_files(root)) | set(by_wrapper)):
        path = root / wrapper
        if not path.is_file():
            continue
        own = by_wrapper.get(wrapper)
        marker = read_marker(path)
        if marker is None:
            if own is not None:
                fail(
                    wrapper,
                    f"{wrapper.as_posix()} mirrors {own.as_posix()} but its body does not start "
                    f"with `<!-- source: {own.as_posix()} sha256: <hash> -->`",
                )
            continue
        named, recorded = marker
        checked += 1
        target = (root / named).resolve()
        if not target.is_relative_to(root):
            fail(
                wrapper, f"{wrapper.as_posix()} points to {named}, which is outside the repository"
            )
            continue
        if not target.is_file():
            fail(wrapper, f"{wrapper.as_posix()} points to {named}, which does not exist")
            continue
        if own is None and Path(named) not in pairs:
            fail(
                wrapper,
                f"{wrapper.as_posix()} points to {named}, which is not a source that is mirrored "
                "(.claude/rules, .claude/agents, .claude/commands or REVIEW.md)",
            )
            continue
        if own is not None and Path(named) != own:
            fail(
                wrapper,
                f"{wrapper.as_posix()} points to {named}, but its name maps to {own.as_posix()}",
            )
            continue
        actual = sha256_of(target)
        if recorded != actual:
            fail(
                wrapper,
                f"{wrapper.as_posix()} was written from an older {named}: update the wrapper "
                f"to match the source, then record {actual} as its hash",
            )

    if problems:
        print(f"\n{len(problems)} Copilot wrapper problem(s)", file=sys.stderr)
        return 1
    print(f"{checked} Copilot wrapper(s) match their sources; {len(pairs)} source(s) covered")
    return 0


def main(argv: list[str] | None = None) -> int:
    summary = __doc__.split("\n", 1)[0]
    update_steps = "To update a wrapper" + __doc__.split("To update a wrapper", 1)[1]
    parser = argparse.ArgumentParser(
        prog="check_copilot",
        description=summary,
        epilog=update_steps.split("Standard library only")[0].rstrip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
