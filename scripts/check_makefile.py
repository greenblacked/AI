#!/usr/bin/env python3
"""Keep the `Makefile` and the CI steps that wrap the same commands in step.

`docs/ci.md` says the `make` targets wrap the same invocations the jobs run — down to the
flag, so a warning that fails CI fails locally too. Nothing enforced that, and two
concrete drifts had already happened: the Makefile's pin extraction used an unescaped `#`
inside `$(shell …)`, which GNU Make 3.81 (macOS's system `make`) reads as the start of a
comment, so every documented local command failed to parse on a Mac while CI, on a newer
`make`, stayed green; and `make lint` ran a bare `actionlint` while CI ran a pinned one.
A claim about equivalence that no gate reads is the shape `check_ci_docs.py` exists for,
one level down.

Two things are checked, both mechanical:

- **Portability.** No unescaped `#` inside a `$(…)` or `${…}` call. That is the construct
  that breaks the oldest `make` a contributor is likely to have, and the fix is one
  backslash.
- **Parity.** For each target that wraps a CI job, every `scripts/*.py` and `-m <module>`
  the target runs also appears in that job, and a flag both sides are meant to carry is
  present on both. The `catalogue` target is checked in both directions, because a check
  added to CI and not to the Makefile is exactly the drift that matters.

It also owns the number word in `docs/ci.md` and `AGENTS.md` that counts the catalogue
checks, so adding one is a fact the gate verifies rather than a number three files have
to be edited to keep true.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

# target -> (workflow file, job key) whose commands the target wraps.
PARITY: dict[str, tuple[str, str]] = {
    "validate": ("ci.yml", "validate-skills"),
    "catalogue": ("ci.yml", "catalogue"),
    "test": ("ci.yml", "test"),
    "coverage": ("ci.yml", "test"),
    "package": ("ci.yml", "package"),
    "portable": ("ci.yml", "package"),
    "attribution": ("ci.yml", "attribution"),
    "naming": ("ci.yml", "naming"),
}
# The target that must also be a superset of its job: a check CI runs and `make catalogue`
# does not is the drift worth failing on, so this one is compared both ways.
BIDIRECTIONAL = {"catalogue"}
# A flag that has to be present on both sides, or absent on both.
FLAGS = {"validate": "--strict", "attribution": "--range", "naming": "--range"}
# `python -m pip install` is not a check; ignoring it keeps parity about the things that
# are.
IGNORED_MODULES = frozenset({"pip"})

NUMBER_WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}
# The number word that counts the catalogue checks, and where each one lives. Each is
# anchored to the sentence it belongs to rather than a bare "N checks", which would match
# any table row that happened to read that way.
COUNT_CLAIMS = (
    (
        Path("docs/ci.md"),
        re.compile(r"the\s+(\w+)\s+checks\s+that\s+keep\s+the\s+repository's\s+claims"),
    ),
    (Path("AGENTS.md"), re.compile(r"the\s+(\w+)\s+catalogue\s+checks")),
    (
        Path("AGENTS.md"),
        re.compile(r"is\s+the\s+(\w+)\s+checks\s+on\s+what\s+the\s+repository\s+claims"),
    ),
)

TARGET_RE = re.compile(r"^([a-z][a-z0-9-]*):")
# `lint: LINT_STRICT := 0` matches TARGET_RE too, but it is a target-specific variable, not
# a rule: it must not be read as a fresh target whose recipe starts empty, or a recipe
# that sits above it is forgotten and a one-way parity check passes on nothing.
TARGET_VAR_RE = re.compile(
    r"^\s*(?:export\s+|override\s+|private\s+)*[A-Za-z_][A-Za-z0-9_.-]*\s*[:?+]?="
)
JOBS_RE = re.compile(r"^jobs:\s*(?:#.*)?$")
JOB_RE = re.compile(r"^ {2}([A-Za-z0-9_.-]+):\s*(?:#.*)?$")
TOP_LEVEL_RE = re.compile(r"^[^\s#]")
SCRIPT_RE = re.compile(r"scripts/([A-Za-z0-9_]+\.py)")
MODULE_RE = re.compile(r"-m\s+([A-Za-z0-9_]+)")
PYTEST_RE = re.compile(r"\bpytest\b")


def unescaped_hashes_in_call(text: str) -> list[int]:
    """Line numbers of a `#` that sits inside a `$(…)`/`${…}` call and is not escaped.

    A `#` at the top level is a comment and is left alone. One inside a function call is
    a comment too — to `make` 3.81, at least — which truncates the call and leaves it
    unterminated. The escape `\\#` is what tells the older parser to keep it.
    """
    problems: list[int] = []
    depth = 0
    line = 1
    for index, char in enumerate(text):
        if char == "\n":
            line += 1
        elif char == "$" and index + 1 < len(text) and text[index + 1] in "({":
            depth += 1
        elif depth > 0 and char in ")}":
            depth -= 1
        elif char == "#" and depth > 0 and (index == 0 or text[index - 1] != "\\"):
            problems.append(line)
    return problems


def make_targets(text: str) -> dict[str, str]:
    """Each target, mapped to its recipe text (the tab-indented lines under it)."""
    targets: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("\t"):
            if current is not None:
                targets[current] += line + "\n"
            continue
        match = TARGET_RE.match(line)
        if match:
            if TARGET_VAR_RE.match(line[match.end() :]):
                # A target-specific variable: keep the recipe an earlier rule line for
                # this target accumulated, and let any tab lines that follow still attach
                # to it, rather than treating the assignment as a new empty rule.
                current = match.group(1)
                targets.setdefault(current, "")
                continue
            current = match.group(1)
            targets[current] = ""
        else:
            current = None
    return targets


def job_blocks(text: str) -> dict[str, str]:
    """Each job in a workflow, mapped to the text of its block."""
    blocks: dict[str, str] = {}
    inside = False
    current: str | None = None
    for line in text.splitlines():
        if JOBS_RE.match(line):
            inside = True
            continue
        if not inside:
            continue
        if TOP_LEVEL_RE.match(line):
            break
        match = JOB_RE.match(line)
        if match:
            current = match.group(1)
            blocks[current] = ""
            continue
        if current is not None:
            blocks[current] += line + "\n"
    return blocks


def units(text: str) -> set[str]:
    """The checks a command runs: every `scripts/*.py`, every `-m <module>`, `pytest`."""
    found = {"scripts/" + match.group(1) for match in SCRIPT_RE.finditer(text)}
    for match in MODULE_RE.finditer(text):
        if match.group(1) not in IGNORED_MODULES:
            found.add(match.group(1))
    if PYTEST_RE.search(text):
        found.add("pytest")
    return found


def check(root: Path) -> int:
    makefile = root / MAKEFILE
    if not makefile.is_file():
        print(f"::error::{MAKEFILE} does not exist", file=sys.stderr)
        return 1

    text = makefile.read_text(encoding="utf-8")
    problems = 0

    for line in unescaped_hashes_in_call(text):
        print(
            f"::error file={MAKEFILE},line={line}::a `#` inside a `$(…)` call is read as "
            f"a comment by GNU Make 3.81 and truncates the call; escape it as `\\#`"
        )
        problems += 1

    targets = make_targets(text)
    workflows: dict[str, str] = {}
    for name, (workflow, job) in PARITY.items():
        recipe = targets.get(name)
        if recipe is None:
            print(
                f"::error file={MAKEFILE}::no `{name}` target, so the documented local "
                f"command the {job} job wraps cannot be checked"
            )
            problems += 1
            continue
        if workflow not in workflows:
            path = root / ".github" / "workflows" / workflow
            if not path.is_file():
                print(
                    f"::error::no workflow {workflow} to compare `{name}` against", file=sys.stderr
                )
                problems += 1
                continue
            workflows[workflow] = path.read_text(encoding="utf-8")
        blocks = job_blocks(workflows[workflow])
        if job not in blocks:
            print(f"::error::{workflow} has no job `{job}` for `make {name}`", file=sys.stderr)
            problems += 1
            continue
        local, ci = units(recipe), units(blocks[job])
        for unit in sorted(local - ci):
            print(
                f"::error file={MAKEFILE}::`make {name}` runs {unit}, which the {job} "
                f"job does not; the two have drifted apart"
            )
            problems += 1
        if name in BIDIRECTIONAL:
            for unit in sorted(ci - local):
                print(
                    f"::error file={MAKEFILE}::the {job} job runs {unit}, which `make "
                    f"{name}` does not; add it there so the local command stays the job"
                )
                problems += 1
        flag = FLAGS.get(name)
        if flag and ((flag in recipe) != (flag in blocks[job])):
            print(
                f"::error file={MAKEFILE}::`{flag}` is on one of `make {name}` and the "
                f"{job} job and not the other; the two are not the same command"
            )
            problems += 1

    catalogue = units(targets.get("catalogue", ""))
    word = NUMBER_WORDS.get(len(catalogue), str(len(catalogue)))
    for path, pattern in COUNT_CLAIMS:
        claim = root / path
        if not claim.is_file():
            print(f"::error::{path} does not exist", file=sys.stderr)
            problems += 1
            continue
        match = pattern.search(claim.read_text(encoding="utf-8"))
        if match is None:
            print(
                f"::error file={path}::no sentence stating how many catalogue checks "
                f"there are; the count has no home for this check to verify"
            )
            problems += 1
        elif match.group(1) != word:
            print(
                f"::error file={path}::says {match.group(1)} catalogue checks, but "
                f"`make catalogue` runs {len(catalogue)}; write {word!r}"
            )
            problems += 1

    if problems:
        print(f"\n{problems} Makefile problem(s)", file=sys.stderr)
        return 1
    print(
        f"{MAKEFILE} is in step with CI: {len(PARITY)} target(s) checked, "
        f"{len(catalogue)} catalogue check(s)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_makefile", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
