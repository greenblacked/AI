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
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"

# A job is a two-space key inside `jobs:`; a job's own keys sit at four. A trailing
# comment is allowed, because a key carrying one is still a job.
JOBS_RE = re.compile(r"^jobs:\s*(?:#.*)?$")
JOB_RE = re.compile(r"^ {2}([A-Za-z0-9_.-]+):\s*(?:#.*)?$")
TOP_LEVEL_RE = re.compile(r"^[^\s#]")
# `    if: always()`, the mark of the aggregator, alongside its `needs:`.
ALWAYS_RE = re.compile(r"^ {4}if:\s*always\(\)\s*(?:#.*)?$")
NEEDS_BLOCK_RE = re.compile(r"^ {4}needs:\s*(?:#.*)?$")
NEEDS_INLINE_RE = re.compile(r"^ {4}needs:\s*\[([^\]]*)\]\s*(?:#.*)?$")
NEEDS_ONE_RE = re.compile(r"^ {4}needs:\s*([A-Za-z0-9_.-]+)\s*(?:#.*)?$")
NEEDS_ITEM_RE = re.compile(r"^ {6}-\s*([A-Za-z0-9_.-]+)\s*(?:#.*)?$")
# Every pinned tool version or digest, at any indent, so a step-level block is caught.
PIN_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*_(?:VERSION|SHA256)):\s*'([^']*)'\s*(?:#.*)?$")


class Job:
    """One job: where its key sits, and the aggregate it declares if it is one."""

    def __init__(self, name: str, line: int) -> None:
        self.name = name
        self.line = line
        self.always = False
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

        if ALWAYS_RE.match(line):
            current.always = True
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
            found.append((match.group(1), match.group(2), number))
    return found


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

        for name, value, number in pins_in(text):
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
