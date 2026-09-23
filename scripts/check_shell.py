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
unclosed quote, a missing `fi`, a block tagged as shell that is actually JavaScript. It
cannot catch a flag that does not exist, and `bash -n` accepts an unterminated heredoc;
both still need a person to run the thing, which is what the skills themselves demand.

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

# The marker run is captured so the closing fence can be required to use the same
# character and be at least as long. Without that, a block quoting a bare ``` line
# closes early and the prose after it is parsed as shell, which fails for a reason
# that has nothing to do with the author.
FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})\s*(bash|sh|shell)\s*$", re.I)
FENCE_CLOSE_RE = re.compile(r"^(`{3,}|~{3,})\s*$")
# `<run-id>`, `<known-bad-sha>`, `<the exact failing commit>`. Deliberately narrow: it
# has to start with a letter and may not end on a space, so a real redirection, a
# here-string or `sort <in >` stays checkable rather than being rewritten away.
PLACEHOLDER_RE = re.compile(r"<[A-Za-z](?:[A-Za-z0-9 _.:/-]*[A-Za-z0-9_.:/-])?>")
SEARCH_DIRS = ("plugins", "docs", "scripts", ".claude", "template")
# A deliberately dumber test for the same thing, used only to notice that the scanner
# above has stopped finding anything. It shares no pattern with FENCE_OPEN_RE on
# purpose: two spellings of one regex fail together, which is no check at all.
LOOKS_LIKE_A_FENCE = ("bash", "sh", "shell")
# ripgrep uses the Rust regex crate, which has no lookaround at all: `(?=`, `(?!`, `(?<=`
# and `(?<!` are a parse error rather than a slow path, and `-P` is what switches it to
# PCRE2 where they work. `bash -n` cannot see this, because the command is valid shell
# and only fails when someone runs it — which is how `rg -n 'uses:\s*[^@]+@(?!\w{40})'`
# shipped in a skill whose own rule says every command it prints must run. This is the
# narrow, mechanical half of that rule: it proves nothing about a flag that does not
# exist, and a person still has to run the thing.
# `rg` as any whitespace-delimited token, with an optional path prefix, so `if rg -q`,
# `xargs rg` and `/usr/bin/rg` are seen. The false positive that buys — `echo rg` with a
# lookaround later on the same line — is far rarer than `if rg -q`.
RG_RE = re.compile(r"(?:^|[\s|;&(`]|\$\()(?:\S*/)?(?:rg|ripgrep)\s")
LOOKAROUND_RE = re.compile(r"\(\?(?:=|!|<=|<!)")
# Every spelling that reaches PCRE2: `--pcre2`, `--engine pcre2` or `auto` in either
# separator, `--auto-hybrid-regex` (the deprecated alias for `--engine auto`), and `P`
# anywhere in a bundled short-flag run — `-Pn` and `-nP` are the same flag.
PCRE2_RE = re.compile(
    r"(?:^|\s)(?:--pcre2|--auto-hybrid-regex|--engine[= ](?:pcre2|auto)"
    r"|-[A-Za-z]*P[A-Za-z]*)(?:\s|=|$)"
)
# A literal search switches the pattern off entirely, so `rg -F '(?!'` — the sweep you
# would write to find this very defect — is not a defect.
LITERAL_RE = re.compile(r"(?:^|\s)(?:--fixed-strings|-[A-Za-z]*F[A-Za-z]*)(?:\s|=|$)")


def fence_openers(text: str) -> int:
    """How many lines look like the start of a shell block, counted naively."""
    found = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("```", "~~~")):
            continue
        if stripped.lstrip("`~").strip().lower() in LOOKS_LIKE_A_FENCE:
            found += 1
    return found


def blocks(text: str):
    """Yield (line number of the first line of the block, block source)."""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        opening = FENCE_OPEN_RE.match(lines[index].lstrip())
        if opening is None:
            index += 1
            continue
        marker = opening.group(1)
        start = index + 1
        end = start
        while end < len(lines):
            closing = FENCE_CLOSE_RE.match(lines[end].lstrip())
            if closing is not None:
                run = closing.group(1)
                if run[0] == marker[0] and len(run) >= len(marker):
                    break
            end += 1
        yield start + 1, "\n".join(lines[start:end])
        index = end + 1


def logical_lines(source: str):
    """Yield (offset, command), joining lines a trailing backslash continues.

    A command split across lines is one command, and the flag that would make it legal
    is as likely to be on the second line as the first.
    """
    buffer = ""
    start = 0
    for offset, raw in enumerate(source.split("\n")):
        line = raw.rstrip()
        if not buffer:
            start = offset
        if line.endswith("\\") and not line.lstrip().startswith("#"):
            buffer += line[:-1] + " "
            continue
        yield start, buffer + line
        buffer = ""
    if buffer:
        yield start, buffer


def rg_without_pcre2(source: str) -> list[tuple[int, str]]:
    """Every ripgrep invocation using lookaround without asking for PCRE2."""
    found = []
    for offset, command in logical_lines(source):
        stripped = command.strip()
        if stripped.startswith("#") or not RG_RE.search(command):
            continue
        if PCRE2_RE.search(command) or LITERAL_RE.search(command):
            continue
        if LOOKAROUND_RE.search(command):
            found.append((offset, stripped))
    return found


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
            text = path.read_text(encoding="utf-8")
            problem = parses(text, executable)
            if problem is not None:
                rel = path.relative_to(root)
                print(f"::error file={rel},line=1::{rel} is not valid shell — {problem}")
                failures += 1
            for offset, command in rg_without_pcre2(text):
                rel = path.relative_to(root)
                print(
                    f"::error file={rel},line={offset + 1}::ripgrep cannot run this as "
                    f"written — lookaround needs -P. {command}"
                )
                failures += 1

    checked = 0
    apparent = 0
    seen = 0
    for directory in SEARCH_DIRS:
        for path in sorted((root / directory).rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            apparent += fence_openers(text)
            for line, source in blocks(text):
                seen += 1
                if not source.strip():
                    continue  # an empty block is nothing to parse, but it was found
                checked += 1
                for offset, command in rg_without_pcre2(source):
                    rel = path.relative_to(root)
                    print(
                        f"::error file={rel},line={line + offset}::ripgrep cannot run "
                        f"this as written — lookaround needs -P. {command}"
                    )
                    failures += 1
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

    # The same rule as the missing-bash branch above, for the other way this can report
    # success without having looked: if the tree plainly contains shell fences and the
    # scanner yielded none, the scanner is broken rather than the tree being clean. That
    # failure is otherwise a zero in a line nobody reads, with the build still green and
    # every block in the library unexamined.
    #
    # Measured against blocks found rather than blocks parsed, because an empty fence is
    # skipped before parsing and is still evidence the scanner is working.
    if apparent and not seen:
        print(
            f"::error::{apparent} fenced shell block(s) are visible in the Markdown and "
            f"the scanner matched none of them, so nothing was checked",
            file=sys.stderr,
        )
        return 2

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
