#!/usr/bin/env python3
"""Fail when a workflow contradicts itself in one of two ways that CI cannot notice.

Both claims here are about a workflow being internally consistent, and both have the
same shape of failure: the build stays green while the thing it was supposed to prove
stops being true.

**The aggregator must name every job.** `ci` and `security` exist so branch protection
has a stable name to require, because a matrix job's check name carries its parameters
and `test (3.13)` stops existing the day the matrix changes. They work by listing every
other job in `needs:` and failing when any of them failed. Nothing checked that the list
was complete. Add a job to `ci.yml` and forget the `needs:` entry and the required check
reports success while the new job is red — the pull request merges, and the only symptom
is a red job nobody is required to look at. That is worse than an unchecked convention:
an unchecked convention fails to notice a problem, and this actively certifies its
absence. Both aggregators are complete today, which is the right moment to gate it.

**A pinned version must mean one thing.** `CLAUDE_CODE_VERSION` is set in `ci.yml` and
again in `evals.yml`, because two workflows cannot share an `env` block. Bump one and
not the other and the eval harness scores descriptions against a different CLI than
`validate-plugin` validated the manifest with, which is a difference nobody would think
to look for when a score moves.

What is deliberately not checked:

- a workflow with no aggregator. `scheduled.yml` and `evals.yml` gate nothing and need
  no stable name for branch protection to point at, which `docs/ci.md` says in as many
  words. Demanding one would be inventing a rule rather than enforcing one.
- whether a job *should* be in the aggregate. Every job in a gating workflow is there to
  be passed, and a job deliberately excluded would be a decision to write down in the
  workflow rather than a shape to infer here.
- the digests. `*_SHA256` is compared across workflows like any other pin, but nothing
  here checks it against the artefact — the jobs that download something do that
  themselves, at the moment it matters, and fail before the binary runs.

There is deliberately no "found no pins" floor. The pin check is already belt and
braces — blinding the value pattern leaves PIN_KEY_RE reporting every pin as unreadable,
so a single pattern failure fails loudly — and a tree that legitimately pins nothing is
not a defect. A floor here fires on that tree and teaches people to ignore the check,
which costs more than the two-simultaneous-failures case it would cover. `check_shell.py`
takes the opposite decision for the opposite reason: there a single pattern failure does
pass silently, and the guard it uses cross-checks against a different scan rather than
asserting a count.

A `needs:` written in a shape this cannot parse is reported rather than read as empty,
and a workflow whose `jobs:` block yields nothing is reported rather than skipped. A
check that silently matches nothing passes every file it does not understand, which is
the failure `check_settings.py` documents at length and the one every check here is
written against.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"

# A job is a two-space key inside `jobs:`; a job's own keys sit at four. A trailing
# comment is allowed, because a key carrying one is still a job.
JOBS_RE = re.compile(r"^jobs:\s*(?:#.*)?$")
JOB_RE = re.compile(r"^ {2}([A-Za-z0-9_.-]+):\s*(?:#.*)?$")
TOP_LEVEL_RE = re.compile(r"^[^\s#]")
# The mark of the aggregator: a job-level `if:` that mentions `always()`, alongside a
# `needs:`. Matching the whole value exactly was this check's second silent hole —
# `if: ${{ always() }}` and `if: always() && !cancelled()` are both aggregates, and
# either spelling made the job invisible, the workflow read as gating nothing, and an
# incomplete `needs:` pass. Any `if:` carrying `always()` counts.
ALWAYS_RE = re.compile(r"^ {4}if:\s*.*always\(\)")
IF_RE = re.compile(r"^ {4}if:\s*(.*?)\s*(?:#.*)?$")
NEEDS_BLOCK_RE = re.compile(r"^ {4}needs:\s*(?:#.*)?$")
NEEDS_INLINE_RE = re.compile(r"^ {4}needs:\s*\[([^\]]*)\]\s*(?:#.*)?$")
NEEDS_ONE_RE = re.compile(r"^ {4}needs:\s*([A-Za-z0-9_.-]+)\s*(?:#.*)?$")
NEEDS_ITEM_RE = re.compile(r"^ {6}-\s*([A-Za-z0-9_.-]+)\s*(?:#.*)?$")
# Every pinned tool version or digest, at any indent so a step-level block is caught,
# and in any of YAML's three spellings. Requiring single quotes was a silent hole:
# nothing makes anyone use them — `.yamllint` extends `default`, where `quoted-strings`
# is off — so a pin re-typed bare or in double quotes dropped out of the comparison
# entirely and could not disagree with anything.
PIN_RE = re.compile(
    r"""^\s*([A-Z][A-Z0-9_]*_(?:VERSION|SHA256)):\s*"""
    # The bare form excludes the characters YAML gives a meaning to at the start of a
    # value — block scalars, anchors, aliases, tags, flow collections — so `>-` is
    # reported as unreadable rather than recorded as the version string ">-".
    r"""(?:'([^']*)'|"([^"]*)"|([^\s#'">|&*!{\[][^\s#]*))\s*(?:#.*)?$"""
)
# The same key with a value the pattern above cannot read. Reported rather than skipped,
# because a pin nobody parsed is a pin nobody is comparing.
PIN_KEY_RE = re.compile(r"^\s*[A-Z][A-Z0-9_]*_(?:VERSION|SHA256):")
DISPLAY_NAME_RE = re.compile(r"^ {4}name:\s*([^#]+?)\s*(?:#.*)?$", re.MULTILINE)
NEEDS_JSON_RE = re.compile(r"^\s+NEEDS_JSON:\s*\$\{\{\s*toJSON\(needs\)\s*}}\s*$", re.MULTILINE)
HELPER = "scripts/check_job_results.py"
KNOWN_GATES = {"ci.yml": "ci", "security.yml": "security"}


class Job:
    """One job: where its key sits, and the aggregate it declares if it is one."""

    def __init__(self, name: str, line: int) -> None:
        self.name = name
        self.line = line
        self.always = False
        self.condition: str | None = None
        self.needs: list[str] | None = None
        self.unparsed: int | None = None


def jobs_in(text: str) -> tuple[list[Job], list[str]]:
    """Every job in a workflow, and any line whose `needs:` could not be read."""
    jobs: list[Job] = []
    problems: list[str] = []
    inside = False
    current: Job | None = None
    collecting = False

    for number, line in enumerate(text.splitlines(), start=1):
        if JOBS_RE.match(line):
            inside = True
            continue
        if not inside:
            continue
        if TOP_LEVEL_RE.match(line):
            break

        match = JOB_RE.match(line)
        if match:
            current = Job(match.group(1), number)
            jobs.append(current)
            collecting = False
            continue
        if current is None:
            continue

        if collecting:
            item = NEEDS_ITEM_RE.match(line)
            if item:
                current.needs.append(item.group(1))
                continue
            if line.strip() and not line.startswith(" " * 6):
                collecting = False
            elif line.strip():
                # Indented under `needs:` and not a plain list item — a shape this
                # does not understand, and reading it as the end of the list would
                # quietly drop a dependency.
                problems.append(f"{number}: {line.strip()}")
                collecting = False
                continue

        condition = IF_RE.match(line)
        if condition:
            current.condition = condition.group(1)
            current.always = ALWAYS_RE.match(line) is not None
            continue
        inline = NEEDS_INLINE_RE.match(line)
        if inline:
            current.needs = [n.strip() for n in inline.group(1).split(",") if n.strip()]
            continue
        if NEEDS_BLOCK_RE.match(line):
            current.needs = []
            collecting = True
            continue
        one = NEEDS_ONE_RE.match(line)
        if one:
            current.needs = [one.group(1)]
            continue
        if line.startswith("    needs:"):
            problems.append(f"{number}: {line.strip()}")

    return jobs, problems


def pins_in(text: str) -> list[tuple[str, str, int]]:
    """Every pinned version or digest in a workflow, as (name, value, line).

    A list rather than a mapping, because the same name can appear twice in one file —
    `evals.yml` set `CLAUDE_CODE_VERSION` in two step-level blocks — and a mapping keeps
    whichever came last. That is the bug this function had first: two different values in
    one workflow collapsed into one and the check passed.
    """
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = PIN_RE.match(line)
        if match:
            value = next(g for g in match.groups()[1:] if g is not None)
            found.append((match.group(1), value, number))
        elif PIN_KEY_RE.match(line):
            found.append((line.split(":", 1)[0].strip(), None, number))
    return found


def job_body(text: str, jobs: list[Job], target: Job) -> str:
    """The source belonging to one already-parsed job."""
    lines = text.splitlines()
    later = [job.line for job in jobs if job.line > target.line]
    end = min(later) - 1 if later else len(lines)
    return "\n".join(lines[target.line - 1 : end])


def helper_step(body: str) -> tuple[list[str], str] | None:
    """Static helper arguments and its containing step, if canonical and unambiguous."""
    lines = body.splitlines()
    command_lines = [index for index, line in enumerate(lines) if HELPER in line]
    if len(command_lines) != 1:
        return None
    command_line = command_lines[0]
    starts = [index for index in range(command_line + 1) if lines[index].startswith("      - ")]
    if not starts:
        return None
    start = starts[-1]
    ends = [index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")]
    end = ends[0] if ends else len(lines)
    step = "\n".join(lines[start:end])
    joined = re.sub(r"\\\n\s*", " ", step)
    calls = [line.strip() for line in joined.splitlines() if HELPER in line]
    if len(calls) != 1:
        return None
    try:
        words = shlex.split(calls[0])
    except ValueError:
        return None
    try:
        helper = words.index(HELPER)
    except ValueError:
        return None
    if helper == 0 or words[:helper] not in (["python"], ["python3"]):
        return None
    return words[helper + 1 :], step


def canonical_helper_run(step: str) -> bool:
    """The helper step runs strict shell setup and then only the helper command."""
    lines = step.splitlines()
    run_lines = [index for index, line in enumerate(lines) if line == "        run: |"]
    if len(run_lines) != 1:
        return False
    commands = []
    for line in lines[run_lines[0] + 1 :]:
        if line.strip() and not line.startswith(" " * 10):
            break
        if line.strip():
            commands.append(line[10:])
    joined = re.sub(r"\\\n\s*", " ", "\n".join(commands))
    command_lines = [line.strip() for line in joined.splitlines() if line.strip()]
    return (
        len(command_lines) == 2
        and command_lines[0] == "set -Eeuo pipefail"
        and command_lines[1].startswith(f"python3 {HELPER} ")
    )


def check_known_gate(rel: Path, text: str, jobs: list[Job]) -> int:
    """Enforce the shared fail-closed implementation for branch-protection gates."""
    expected_name = KNOWN_GATES.get(rel.name)
    if expected_name is None:
        return 0
    matches = [job for job in jobs if job.name == expected_name]
    if len(matches) != 1:
        print(f"::error file={rel}::expected one `{expected_name}` aggregate job")
        return 1
    aggregate = matches[0]
    body = job_body(text, jobs, aggregate)
    problems = 0
    display = DISPLAY_NAME_RE.search(body)
    if display is None or display.group(1).strip(" '\"") != expected_name:
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` must have "
            f"display name `{expected_name}`"
        )
        problems += 1
    if aggregate.condition not in ("always()", "${{ always() }}"):
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` must use exactly always()"
        )
        problems += 1
    if re.search(r"^ {4}continue-on-error:", body, re.MULTILINE):
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` may not continue on error"
        )
        problems += 1
    helper = helper_step(body)
    step = helper[1] if helper is not None else ""
    if not NEEDS_JSON_RE.search(step):
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` must pass "
            "`${{ toJSON(needs) }}` as NEEDS_JSON"
        )
        problems += 1
    if re.search(r"^(?: {6}- | {8})(?:if|continue-on-error):", step, re.MULTILINE):
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` helper step "
            "must be unconditional and may not continue on error"
        )
        problems += 1
    if helper is not None and not canonical_helper_run(step):
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` helper step must "
            "run strict shell setup followed by only the shared helper"
        )
        problems += 1
    if helper is None:
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` must call "
            f"`python3 {HELPER}` with static job IDs"
        )
        problems += 1
    elif aggregate.needs is None or helper[0] != aggregate.needs:
        print(
            f"::error file={rel},line={aggregate.line}::`{expected_name}` helper job IDs "
            "must exactly match its needs list"
        )
        problems += 1
    return problems


def check(root: Path) -> int:
    workflows = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in (root / WORKFLOW_DIR).glob(pattern)
    )
    if not workflows:
        print(f"::error::no workflows in {WORKFLOW_DIR}", file=sys.stderr)
        return 1

    problems = 0
    gated = 0
    seen_pins: dict[str, list[tuple[str, str, int]]] = {}

    for path in workflows:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        jobs, unreadable = jobs_in(text)

        for where in unreadable:
            line, shape = where.split(": ", 1)
            print(
                f"::error file={rel},line={line}::could not read this `needs:` — "
                f"{shape}. Write it as a list of job names; a shape this check cannot "
                f"read is one it cannot vouch for"
            )
            problems += 1

        if not jobs:
            print(
                f"::error file={rel}::found no job in this workflow, so its aggregate "
                f"cannot be checked; if the `jobs:` block moved, this check has to "
                f"move with it"
            )
            problems += 1
            continue

        problems += check_known_gate(rel, text, jobs)

        for name, value, number in pins_in(text):
            if value is None:
                print(
                    f"::error file={rel},line={number}::could not read the value of "
                    f"`{name}`; write it as a plain, single-quoted or double-quoted "
                    f"scalar, because a pin nobody can parse is one nobody is comparing"
                )
                problems += 1
                continue
            seen_pins.setdefault(name, []).append((str(rel), value, number))

        aggregators = [job for job in jobs if job.always and job.needs is not None]
        if not aggregators:
            continue  # gates nothing, so it needs no stable name to require
        if len(aggregators) > 1:
            names = ", ".join(job.name for job in aggregators)
            print(
                f"::error file={rel}::more than one job looks like the aggregate "
                f"({names}); this check will not guess which one branch protection "
                f"requires"
            )
            problems += 1
            continue

        aggregate = aggregators[0]
        gated += 1
        listed = set(aggregate.needs)
        for job in jobs:
            if job.name == aggregate.name or job.name in listed:
                continue
            print(
                f"::error file={rel},line={job.line}::job `{job.name}` is missing from "
                f"`{aggregate.name}`'s needs, so a failure in it would not fail the "
                f"required check"
            )
            problems += 1
        known = {job.name for job in jobs}
        for name in sorted(listed - known):
            print(
                f"::error file={rel},line={aggregate.line}::`{aggregate.name}` needs "
                f"`{name}`, which is not a job in this workflow"
            )
            problems += 1

    for name, places in sorted(seen_pins.items()):
        if len({value for _, value, _ in places}) > 1:
            spread = "; ".join(f"{where}:{line} has {value}" for where, value, line in places)
            print(
                f"::error::{name} is pinned to more than one value — {spread}. A pin "
                f"that means two things is one that was bumped in one place"
            )
            problems += 1

    if problems:
        print(f"\n{problems} workflow problem(s)", file=sys.stderr)
        return 1
    print(
        f"workflows are consistent: {gated} aggregate(s) name every job, "
        f"{len(seen_pins)} pin(s) agree across {len(workflows)} workflow(s)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_workflows", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
