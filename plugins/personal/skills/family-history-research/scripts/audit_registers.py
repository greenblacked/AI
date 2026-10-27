#!/usr/bin/env python3
"""Audit the five family-history registers for claims stronger than their evidence.

Reads sources.csv, statements.csv, conclusions.csv, people.csv and research-log.csv from
one directory and never writes. Every file and header is checked before anything is
printed, so a half-read register cannot produce a half-trusted report.

Exit codes: 0 clean, 1 errors (or warnings under --strict), 2 an input is unusable.
Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

COLUMNS: dict[str, tuple[str, ...]] = {
    "sources.csv": (
        "source_id",
        "citation",
        "kind",
        "locator",
        "how_obtained",
        "local_copy_path",
        "sha256",
    ),
    "statements.csv": (
        "statement_id",
        "source_id",
        "person_as_written",
        "event",
        "date_as_written",
        "place_as_written",
        "informant",
        "informant_closeness",
        "information",
    ),
    "conclusions.csv": (
        "conclusion_id",
        "conclusion",
        "kind",
        "person_a",
        "person_b",
        "evidence",
        "statements_for",
        "statements_against",
        "resolution",
        "proof_level",
    ),
    "people.csv": ("person_id", "name", "possibly_living", "inclusion_basis"),
    "research-log.csv": (
        "row_type",
        "date",
        "repository_kind",
        "terms",
        "scope_covered",
        "result",
        "follow_up",
        "coverage_item",
        "final_state",
        "reason",
    ),
}

SOURCE_KINDS = {"original", "derivative", "authored"}
INFORMATION = {"first-hand", "second-hand", "undetermined"}
CONCLUSION_KINDS = {"identity", "event", "relationship"}
EVIDENCE = {"direct", "indirect", "negative"}
PROOF_LEVELS = {"proved", "probable", "possible", "not proved", "disproved"}
ROW_TYPES = {"search", "coverage"}
FINAL_STATES = {"searched-found", "searched-not-found", "inaccessible", "out-of-scope"}
NEEDS_REASON = {"inaccessible", "out-of-scope"}

Table = list[dict[str, str]]


class UnusableError(Exception):
    """An input cannot be read as a register; nothing should be reported from it."""


@dataclass
class Finding:
    level: str  # "ERROR" or "WARNING"
    file: str
    row: int
    code: str
    message: str


def read_register(directory: Path, name: str) -> Table:
    path = directory / name
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header is None:
                raise UnusableError(f"{name}: the file is empty, not even a header row")
            header = [cell.strip() for cell in header]
            missing = [column for column in COLUMNS[name] if column not in header]
            if missing:
                raise UnusableError(f"{name}: missing columns {', '.join(missing)}")
            if len(set(header)) != len(header):
                raise UnusableError(f"{name}: the header repeats a column")
            rows: Table = []
            for number, raw in enumerate(reader, start=1):
                if not any(cell.strip() for cell in raw):
                    continue
                if len(raw) != len(header):
                    raise UnusableError(
                        f"{name}: data row {number} has {len(raw)} cells, header has {len(header)}"
                    )
                row = {column: cell.strip() for column, cell in zip(header, raw, strict=True)}
                row["_row"] = str(number)
                rows.append(row)
            return rows
    except FileNotFoundError:
        raise UnusableError(f"{name}: not found in {str(directory)!r}") from None
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise UnusableError(f"{name}: cannot be read ({type(error).__name__})") from None


def ids(cell: str) -> list[str]:
    return [part.strip() for part in cell.split(";") if part.strip()]


def audit(
    tables: dict[str, Table],
) -> list[Finding]:
    found: list[Finding] = []

    def add(level: str, file: str, row: dict[str, str], code: str, message: str) -> None:
        found.append(Finding(level, file, int(row["_row"]), code, message))

    sources: dict[str, dict[str, str]] = {}
    for row in tables["sources.csv"]:
        key = row["source_id"]
        if not key or key in sources:
            add("ERROR", "sources.csv", row, "source-id", f"missing or repeated id {key!r}")
            continue
        sources[key] = row
        if row["kind"] not in SOURCE_KINDS:
            add("ERROR", "sources.csv", row, "source-kind", f"{key!r} has kind {row['kind']!r}")
        if row["local_copy_path"] and not row["sha256"]:
            add(
                "WARNING",
                "sources.csv",
                row,
                "no-sha256",
                f"{key!r} has a local copy {row['local_copy_path']!r} but no sha256",
            )

    statements: dict[str, dict[str, str]] = {}
    for row in tables["statements.csv"]:
        key = row["statement_id"]
        if not key or key in statements:
            add("ERROR", "statements.csv", row, "statement-id", f"missing or repeated id {key!r}")
            continue
        statements[key] = row
        if row["source_id"] not in sources:
            add(
                "ERROR",
                "statements.csv",
                row,
                "missing-source",
                f"{key!r} cites source {row['source_id']!r}, which sources.csv does not hold",
            )
        if row["information"] not in INFORMATION:
            add(
                "ERROR",
                "statements.csv",
                row,
                "information",
                f"{key!r} has information {row['information']!r}",
            )

    people: dict[str, dict[str, str]] = {}
    for row in tables["people.csv"]:
        key = row["person_id"]
        if not key or key in people:
            add("ERROR", "people.csv", row, "person-id", f"missing or repeated id {key!r}")
            continue
        people[key] = row
        living = row["possibly_living"].lower()
        if living not in {"yes", "no"}:
            add(
                "ERROR",
                "people.csv",
                row,
                "living-flag",
                f"{key!r} has possibly_living {row['possibly_living']!r}, expected yes or no",
            )
        elif living == "yes" and not row["inclusion_basis"]:
            add(
                "ERROR",
                "people.csv",
                row,
                "living-no-basis",
                f"{key!r} is possibly living and has no inclusion basis",
            )

    seen_conclusions: set[str] = set()
    for row in tables["conclusions.csv"]:
        key = row["conclusion_id"]
        where = "conclusions.csv"
        if not key or key in seen_conclusions:
            add("ERROR", where, row, "conclusion-id", f"missing or repeated id {key!r}")
            continue
        seen_conclusions.add(key)
        level = row["proof_level"]
        if level not in PROOF_LEVELS:
            add("ERROR", where, row, "proof-level", f"{key!r} has proof level {level!r}")
        if row["kind"] not in CONCLUSION_KINDS:
            add("ERROR", where, row, "conclusion-kind", f"{key!r} has kind {row['kind']!r}")
        evidence = set(ids(row["evidence"]))
        if not evidence or not evidence <= EVIDENCE:
            add("ERROR", where, row, "evidence", f"{key!r} has evidence {row['evidence']!r}")

        for column in ("person_a", "person_b"):
            if row[column] and row[column] not in people:
                add(
                    "ERROR",
                    where,
                    row,
                    "missing-person",
                    f"{key!r} cites {column} {row[column]!r}, which people.csv does not hold",
                )
        if row["kind"] == "relationship" and not (row["person_a"] and row["person_b"]):
            add(
                "ERROR",
                where,
                row,
                "relationship-people",
                f"{key!r} is a relationship but names person_a {row['person_a']!r} "
                f"and person_b {row['person_b']!r}",
            )

        if row["kind"] == "relationship" and row["person_a"] and row["person_a"] == row["person_b"]:
            add(
                "ERROR",
                where,
                row,
                "relationship-same-person",
                f"{key!r} is a relationship between {row['person_a']!r} and itself",
            )

        support = ids(row["statements_for"])
        against = ids(row["statements_against"])
        for column, group in (("statements_for", support), ("statements_against", against)):
            for statement in group:
                if statement not in statements:
                    add(
                        "ERROR",
                        where,
                        row,
                        "missing-statement",
                        f"{key!r} cites {statement!r} in {column}, which statements.csv "
                        "does not hold",
                    )

        known = [statements[s] for s in support if s in statements]
        support_sources = {s["source_id"] for s in known if s["source_id"] in sources}
        original = {s for s in support_sources if sources[s]["kind"] == "original"}

        if level in {"proved", "probable"}:
            if not original:
                add(
                    "ERROR",
                    where,
                    row,
                    "no-original-support",
                    f"{key!r} is {level} but no supporting statement comes from an original "
                    f"source (sources behind it: {sorted(support_sources)!r})",
                )
            if level == "proved" and len(original) == 1:
                add(
                    "ERROR",
                    where,
                    row,
                    "one-original",
                    f"{key!r} is proved on one original source {sorted(original)!r}; "
                    "proved needs at least two",
                )
            # Only distinct originals count: a derivative or authored copy of the same
            # record is not a second witness, so adding one must not silence this.
            if level == "probable" and len(original) == 1:
                add(
                    "WARNING",
                    where,
                    row,
                    "single-source",
                    f"{key!r} is probable and rests on one original source {sorted(original)!r}",
                )
        if level == "proved" and evidence == {"negative"}:
            add(
                "ERROR",
                where,
                row,
                "negative-only",
                f"{key!r} is proved on negative evidence alone",
            )
        if level in {"proved", "probable"} and against and not row["resolution"]:
            add(
                "ERROR",
                where,
                row,
                "unresolved-conflict",
                f"{key!r} is {level}, cites {against!r} against it and gives no resolution",
            )

    for row in tables["research-log.csv"]:
        where = "research-log.csv"
        if row["row_type"] not in ROW_TYPES:
            add("ERROR", where, row, "row-type", f"row_type {row['row_type']!r} is not known")
            continue
        if row["row_type"] != "coverage":
            continue
        item = row["coverage_item"]
        state = row["final_state"]
        if state not in FINAL_STATES:
            add(
                "ERROR",
                where,
                row,
                "coverage-state",
                f"coverage item {item!r} ends as {state!r}, which is not a final state",
            )
        elif state in NEEDS_REASON and not row["reason"]:
            add(
                "ERROR",
                where,
                row,
                "coverage-reason",
                f"coverage item {item!r} is {state} and gives no reason",
            )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit family-history registers (read-only).")
    parser.add_argument("directory", type=Path, help="directory holding the five registers")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args(argv)

    try:
        tables = {name: read_register(args.directory, name) for name in COLUMNS}
    except UnusableError as error:
        print(f"unusable input: {error}", file=sys.stderr)
        return 2

    findings = audit(tables)
    for item in findings:
        print(f"{item.level} {item.file} row {item.row} [{item.code}] {item.message}")
    errors = sum(1 for f in findings if f.level == "ERROR")
    warnings = len(findings) - errors
    print(f"{errors} errors, {warnings} warnings")
    if errors or (warnings and args.strict):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
