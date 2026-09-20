#!/usr/bin/env python3
"""Fail when `docs/ci.md` stops describing the jobs CI actually runs.

CI is the source of truth for whether this repository is correct, and `docs/ci.md` is the
only place a reader learns what a check name means. When a red `check catalogue` arrives
on a pull request, the table in that file is what turns it into something actionable; a
job with no row is a failure someone has to reverse-engineer from a workflow file, and a
row for a job that no longer exists sends them looking for a step that was deleted.

The README had exactly this problem and drifted twice, both times after the plugins were
re-cut, and both times it was caught by a person reading rather than by a gate.
`check_readme.py` is the answer to that; this is the same answer for the file that
documents the gates themselves. It is the more embarrassing of the two to get wrong,
because a repository whose whole argument is that a convention needs a check should not
document its checks on the honour system.

What is checked, all of it mechanical:

- every workflow in `.github/workflows/` has a section in `docs/ci.md`
- every job in every workflow has a row in that workflow's section
- every job named by a row exists in that workflow
- no section for a workflow file that is gone

What is deliberately not checked is the second column, the check name. `test` appears
there as `test (3.10)` … `test (3.13)`, because a matrix job's check name carries its
parameters, and `catalogue` has a second row labelled `(portable step)` that documents a
step rather than a job. A gate that insisted those matched would fail on documentation
that is correct, and a gate that cries wolf is one people learn to override — the same
reasoning `check_readme.py` applies to counts written in prose. The job column is
mechanical; the check-name column is prose, and it is left to the reader.

Rows are read from a workflow's heading up to the next heading of any level, which is
what keeps the dispatch-input and credential tables further down the evals section from
being mistaken for job rows: they sit under their own subheadings. A second job table
placed under the same heading would be read as part of the first, which is the right
trade — the alternative is guessing which of two adjacent tables is the real one. Job names
are the two-space keys inside a workflow's `jobs:` block, which is how `permissions-audit`
finds them in shell. Parsing the workflows twice, once here and once there, is deliberate:
that audit is a required part of the `security` gate, and a security check that could only
fail inside the other workflow's catalogue job would be one indirection away from being
switched off by accident.

A workflow whose `jobs:` block yields nothing is reported rather than skipped. A parse
that silently matches nothing would pass this file vacuously, which is the failure shape
`check_settings.py` documents at length and the one every check here is written against.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"
DOC = Path("docs") / "ci.md"

# "## `.github/workflows/ci.yml` — CI" — the heading that opens a workflow's section.
SECTION_RE = re.compile(r"^#{2,}\s+`\.github/workflows/([^`]+)`")
# Any heading, which is what bounds a section's table.
HEADING_RE = re.compile(r"^#{1,6}\s")
# "| `validate-skills` | `validate skills` | … |" — the job is the first backticked
# token of the first cell. Anything after it, such as "(portable step)", is prose.
ROW_RE = re.compile(r"^\|\s*`([^`]+)`")
# A job is a two-space key inside `jobs:`; a job's own keys sit at four. A trailing
# comment is allowed, because a key that carries one is still a job, and a walk that
# skipped it would leave that job unchecked while still reporting a clean run.
JOBS_RE = re.compile(r"^jobs:\s*(?:#.*)?$")
JOB_RE = re.compile(r"^ {2}([A-Za-z0-9_.-]+):\s*(?:#.*)?$")
TOP_LEVEL_RE = re.compile(r"^[^\s#]")


def jobs_in(text: str) -> dict[str, int]:
    """Every job in a workflow, mapped to the line its key sits on."""
    jobs: dict[str, int] = {}
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if JOBS_RE.match(line):
            inside = True
            continue
        if not inside:
            continue
        if TOP_LEVEL_RE.match(line):
            break  # another top-level key; the jobs block is over
        match = JOB_RE.match(line)
        if match:
            jobs[match.group(1)] = number
    return jobs


def documented(text: str) -> dict[str, dict[str, int]]:
    """Each workflow section in the document, mapped to the jobs its table names.

    The table is the rows between the section heading and the next heading of any level,
    which is what keeps the dispatch-input and credential tables further down the evals
    section from being read as job rows.
    """
    sections: dict[str, dict[str, int]] = {}
    current: dict[str, int] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = SECTION_RE.match(line)
        if match:
            current = sections.setdefault(match.group(1), {})
            continue
        if HEADING_RE.match(line):
            current = None
            continue
        if current is None:
            continue
        row = ROW_RE.match(line)
        if row:
            current.setdefault(row.group(1), number)
    return sections


def check(root: Path) -> int:
    doc = root / DOC
    if not doc.is_file():
        print(f"::error::{DOC} does not exist", file=sys.stderr)
        return 1

    workflows = sorted(
        path for pattern in ("*.yml", "*.yaml") for path in (root / WORKFLOW_DIR).glob(pattern)
    )
    if not workflows:
        print(f"::error::no workflows in {WORKFLOW_DIR}", file=sys.stderr)
        return 1

    sections = documented(doc.read_text(encoding="utf-8"))
    problems = 0
    counted = 0

    for path in workflows:
        name = path.name
        jobs = jobs_in(path.read_text(encoding="utf-8"))
        rel = path.relative_to(root)
        if not jobs:
            print(
                f"::error file={rel}::found no job in this workflow, so its "
                f"documentation cannot be checked; if the `jobs:` block moved, this "
                f"check has to move with it"
            )
            problems += 1
            continue
        counted += len(jobs)

        if name not in sections:
            print(
                f"::error file={DOC}::{name} has no section; add a heading reading "
                f"'## .github/workflows/{name}' in backticks, with a table of its "
                f"{len(jobs)} job(s)"
            )
            problems += 1
            continue

        rows = sections[name]
        for job, line in sorted(jobs.items(), key=lambda item: item[1]):
            if job not in rows:
                print(
                    f"::error file={rel},line={line}::job `{job}` has no row in the "
                    f"{name} table in {DOC}; a job nobody documented is a red check "
                    f"somebody has to reverse-engineer"
                )
                problems += 1
        for job, line in sorted(rows.items(), key=lambda item: item[1]):
            if job not in jobs:
                print(
                    f"::error file={DOC},line={line}::the {name} table has a row for "
                    f"`{job}`, which is not a job in that workflow"
                )
                problems += 1

    present = {path.name for path in workflows}
    for name in sorted(set(sections) - present):
        print(f"::error file={DOC}::there is a section for {name}, which does not exist")
        problems += 1

    if problems:
        print(f"\n{problems} CI documentation problem(s)", file=sys.stderr)
        return 1
    print(
        f"{DOC} is current: {counted} job(s) across {len(workflows)} workflow(s), each with a row"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_ci_docs", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
