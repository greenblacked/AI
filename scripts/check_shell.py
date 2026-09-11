#!/usr/bin/env python3
"""Syntax-check every piece of shell this repository ships or prints.

The product here is prose an agent follows as instructions, and the commands inside a
fenced block are the part it follows most literally. Until this existed they were the one
part of a skill nothing checked at all: the validator masks fenced blocks before scanning
for dangling pointers, which is right for that check and means nothing else ever looks
inside them. A skill that ships a command with an unbalanced quote reads fine, validates
clean, packages, and fails in someone else's terminal.

Two surfaces:

- `scripts/*.sh` bundled with a skill. The validator checks the shebang and the
  executable bit and stops there, so a syntax error in a script handed to `git bisect
  run` verbatim ships green. That one returns a confidently wrong answer during an
  incident rather than failing loudly, which is the worst shape a defect can have.
- every ```bash, ```sh and ```shell block in the Markdown.

`bash -n` parses without executing, so nothing here runs a command, touches a network or
needs a binary the block names. It catches the class that is purely mechanical — an
unclosed quote, a missing `fi`, a heredoc that never terminates, a block tagged as shell
that is actually JavaScript. It cannot catch a flag that does not exist; that still needs
a person to run it, which is what the skills themselves demand.

Placeholders are substituted before parsing. `git bisect start <bad-sha> <good-sha>` is
documentation convention, not a defect, and a gate that fails on it would be all noise:
before the substitution eleven of this repository's blocks "failed" and every one was a
placeholder.

Standard library only, like the validator it sits beside. It needs `bash` on PATH, which
CI has and every contributor's machine has; without one it says so and exits non-zero
rather than passing vacuously.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

FENCE_OPEN_RE = re.compile(r"^\s*(?:```|~~~)\s*(bash|sh|shell)\s*$", re.I)
FENCE_CLOSE_RE = re.compile(r"^\s*(?:```|~~~)\s*$")
# `<run-id>`, `<known-bad-sha>`, `<the exact failing commit>`. Deliberately narrow: it
# has to start with a letter, so a real redirection into a file or a here-string is not
# swallowed and stays checkable.
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][A-Za-z0-9 _.:/-]*>")
SEARCH_DIRS = ("plugins", "docs", "scripts", ".claude", "template")


def blocks(text: str):
    """Yield (line number of the first line of the block, block source)."""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        if not FENCE_OPEN_RE.match(lines[index]):
            index += 1
            continue
        start = index + 1
        end = start
        while end < len(lines) and not FENCE_CLOSE_RE.match(lines[end]):
            end += 1
        yield start + 1, "\n".join(lines[start:end])
        index = end + 1


def bash() -> str | None:
    """The absolute path to bash, or None. Resolved once, and never a bare name: a
    partial path is resolved against whatever PATH happens to hold at call time."""
    return shutil.which("bash")


def parses(source: str, shell: str | None = None) -> str | None:
    """None when the shell parses, otherwise the last line of bash's complaint."""
    executable = shell or bash()
    if executable is None:
        raise RuntimeError("bash is not on PATH")
    result = subprocess.run(  # noqa: S603 - absolute path, fixed argv, source only on stdin
        [executable, "-n"],
        input=PLACEHOLDER_RE.sub("PLACEHOLDER", source),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return None
    complaint = [line for line in result.stderr.strip().split("\n") if line.strip()]
    return complaint[-1] if complaint else f"bash -n exited {result.returncode}"


def check(root: Path) -> int:
    executable = bash()
    if executable is None:
        # Never pass vacuously. A check that reports success because it could not run is
        # worse than no check: it reads as evidence.
        print("bash is not on PATH, so nothing was checked", file=sys.stderr)
        return 2

    failures = 0
    scripts = 0
    for directory in SEARCH_DIRS:
        for path in sorted((root / directory).rglob("*.sh")):
            scripts += 1
            problem = parses(path.read_text(encoding="utf-8"), executable)
            if problem is not None:
                rel = path.relative_to(root)
                print(f"::error file={rel},line=1::{rel} is not valid shell — {problem}")
                failures += 1

    checked = 0
    for directory in SEARCH_DIRS:
        for path in sorted((root / directory).rglob("*.md")):
            for line, source in blocks(path.read_text(encoding="utf-8")):
                if not source.strip():
                    continue
                checked += 1
                problem = parses(source, executable)
                if problem is not None:
                    rel = path.relative_to(root)
                    print(
                        f"::error file={rel},line={line}::shell block does not parse — "
                        f"{problem}. If this is not shell, tag the fence with the right "
                        f"language; if it is, fix it or write the variable part as a "
                        f"<placeholder>"
                    )
                    failures += 1

    print(f"{scripts} shipped script(s) and {checked} shell block(s) parsed")
    if failures:
        print(f"{failures} did not", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_shell", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
