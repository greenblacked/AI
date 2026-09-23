#!/usr/bin/env python3
"""Render the README's table of AI tools from providers.json, and fail when they differ.

The table says, per tool, whether it reads `AGENTS.md`, whether it loads skills, and how
to use this library with it. Every cell is a claim about someone else's product, and
those go stale on a schedule nobody here controls: a vendor adds `AGENTS.md` support, or
moves the page that said it had none. So the claims live as data in ``providers.json``,
each row with the sources it was checked against and the date it was checked, and the
README carries only a rendering of that file.

Three things are checked. The data itself — a row with no source is an assertion nobody
can re-verify, and a `|` in a cell silently splits the Markdown table. The README block
against what the data renders to, so a hand edit to the table, or a data edit nobody
re-rendered, fails rather than leaving the two to disagree. And the age of each row,
which is a warning and never a failure: CI should not go red because the calendar moved,
but a claim about a third-party tool that nobody has looked at in half a year should say
so on every run until someone does.

Standard library only, like the validator: no dependency may stand between a bare
interpreter and a green build.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

PROVIDERS_FILE = "providers.json"
README = "README.md"
START = "<!-- providers-table:start -->"
END = "<!-- providers-table:end -->"
WRITE_COMMAND = "python scripts/providers_table.py --write ."
NOTE = (
    f"<!-- Generated from {PROVIDERS_FILE} by `{WRITE_COMMAND}`. "
    "Do not edit this table by hand: edit that file and regenerate. -->"
)

# The text cells in column order, with their headers. `sources` and `verified` render
# together as the last column, so they are not here.
COLUMNS = (
    ("provider", "Provider"),
    ("tool", "Tool"),
    ("agents_md", "Reads `AGENTS.md`"),
    ("skills", "Loads skills"),
    ("use", "How to use this library"),
)
CHECKED_HEADER = "Checked"
ROW_KEYS = {key for key, _header in COLUMNS} | {"sources", "verified"}
TOP_KEYS = {"stale_after_days", "tools"}

# `date.fromisoformat` accepts more than this on 3.11 and later ("20260923", week dates),
# so the shape is pinned separately: the file should read the same on every interpreter
# CI runs.
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Characters that end a Markdown link target or split a table cell. A URL carrying one
# renders as a broken link or a broken row, and neither raises an error anywhere.
URL_BREAKERS = re.compile(r"[\s|()<>]")


def row_label(index: int, row: object) -> str:
    """How an error names a row: its position, plus provider and tool when it has them."""
    if isinstance(row, dict):
        name = " ".join(
            str(row[key]) for key in ("provider", "tool") if isinstance(row.get(key), str)
        )
        if name.strip():
            return f"tools[{index}] ({name})"
    return f"tools[{index}]"


def validate(data: object) -> list[str]:
    """Every problem with the parsed providers file, as messages; empty when it is sound."""
    if not isinstance(data, dict):
        return [f"{PROVIDERS_FILE} must be an object with 'stale_after_days' and 'tools'"]
    problems: list[str] = []
    for key in sorted(set(data) - TOP_KEYS):
        problems.append(f"unknown top-level key {key!r}; expected only {sorted(TOP_KEYS)}")
    stale = data.get("stale_after_days")
    # bool is an int subclass, and `true` days is a typo rather than a threshold.
    if isinstance(stale, bool) or not isinstance(stale, int) or stale <= 0:
        problems.append("'stale_after_days' must be a positive whole number of days")
    tools = data.get("tools")
    if not isinstance(tools, list) or not tools:
        problems.append("'tools' must be a non-empty list of rows")
        return problems

    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(tools):
        label = row_label(index, row)
        if not isinstance(row, dict):
            problems.append(f"{label} must be an object")
            continue
        for key in sorted(ROW_KEYS - set(row)):
            problems.append(f"{label} is missing {key!r}")
        for key in sorted(set(row) - ROW_KEYS):
            # A key the renderer does not know is data that goes nowhere, and most often
            # a misspelling of one it does.
            problems.append(f"{label} has unknown key {key!r}")
        for key, _header in COLUMNS:
            if key not in row:
                continue
            value = row[key]
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{label} {key!r} must be a non-empty string")
            elif "|" in value or "\n" in value or "\r" in value:
                problems.append(
                    f"{label} {key!r} contains a '|' or a line break, which would break "
                    "the Markdown table"
                )
        if "sources" in row:
            sources = row["sources"]
            if not isinstance(sources, list) or not sources:
                problems.append(f"{label} 'sources' must be a non-empty list of https URLs")
            else:
                for url in sources:
                    if not isinstance(url, str):
                        problems.append(f"{label} source {url!r} is not a string")
                        continue
                    parts = urlsplit(url)
                    if parts.scheme != "https" or not parts.netloc:
                        problems.append(f"{label} source {url!r} is not an https URL")
                    elif URL_BREAKERS.search(url):
                        problems.append(
                            f"{label} source {url!r} contains whitespace, '|', a "
                            "parenthesis or an angle bracket, which would break the link"
                        )
        if "verified" in row and parse_date(row["verified"]) is None:
            problems.append(
                f"{label} 'verified' must be a date in YYYY-MM-DD form, got {row['verified']!r}"
            )
        provider, tool = row.get("provider"), row.get("tool")
        if isinstance(provider, str) and isinstance(tool, str):
            if (provider, tool) in seen:
                problems.append(f"{label} duplicates an earlier row for {provider} {tool}")
            seen.add((provider, tool))
    return problems


def parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def ordered(tools: list[dict]) -> list[dict]:
    """Rows by provider, then tool, ignoring case so "deepseek" does not sort after "Z"."""
    return sorted(
        tools,
        key=lambda row: (
            row["provider"].casefold(),
            row["tool"].casefold(),
            row["provider"],
            row["tool"],
        ),
    )


def render(data: dict) -> str:
    """The whole README block, markers included, for a providers file that validated."""
    headers = [header for _key, header in COLUMNS] + [CHECKED_HEADER]
    lines = [
        START,
        NOTE,
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in ordered(data["tools"]):
        first, *rest = row["sources"]
        checked = ", ".join(
            [f"[{row['verified']}]({first})"]
            + [f"[{number}]({url})" for number, url in enumerate(rest, 2)]
        )
        cells = [row[key].strip() for key, _header in COLUMNS] + [checked]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", END]
    return "\n".join(lines)


def find_block(text: str) -> tuple[int, int] | str:
    """(start, end) offsets of the block in the README, or why it cannot be found."""
    starts, ends = text.count(START), text.count(END)
    if starts != 1 or ends != 1:
        return (
            f"expected one {START} and one {END} marker, found {starts} and {ends}; the "
            f"generated table needs both, around the place it belongs"
        )
    start, end = text.index(START), text.index(END)
    if end < start:
        return f"the {END} marker comes before {START}"
    return start, end + len(END)


def stale_rows(data: dict, today: date) -> list[str]:
    """A warning per row not checked within stale_after_days of today."""
    warnings = []
    for row in ordered(data["tools"]):
        verified = parse_date(row["verified"])
        days = (today - verified).days
        if days > data["stale_after_days"]:
            warnings.append(
                f"{row['provider']} {row['tool']} last checked {row['verified']}, "
                f"{days} days ago; re-verify against its sources and update the date"
            )
    return warnings


def run(root: Path, write: bool = False, today: date | None = None) -> int:
    today = today or date.today()
    providers = root / PROVIDERS_FILE
    readme = root / README
    if not providers.is_file():
        print(f"::error file={PROVIDERS_FILE}::{PROVIDERS_FILE} is missing under {root}")
        return 1
    try:
        data = json.loads(providers.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"::error file={PROVIDERS_FILE}::{PROVIDERS_FILE} is not valid JSON: {error}")
        return 1
    problems = validate(data)
    for problem in problems:
        print(f"::error file={PROVIDERS_FILE}::{problem}")
    if problems:
        print(f"\n{len(problems)} problem(s) in {PROVIDERS_FILE}", file=sys.stderr)
        return 1

    # Before the README is looked at, so a stale row is reported even on a run that
    # fails for another reason, and never changes the exit status.
    for warning in stale_rows(data, today):
        print(f"::warning file={PROVIDERS_FILE}::{warning}")

    if not readme.is_file():
        print(f"::error file={README}::{README} is missing under {root}")
        return 1
    text = readme.read_text(encoding="utf-8")
    span = find_block(text)
    if isinstance(span, str):
        print(f"::error file={README}::{span}")
        return 1
    block = render(data)
    current = text[span[0] : span[1]]

    if write:
        if current != block:
            readme.write_text(text[: span[0]] + block + text[span[1] :], encoding="utf-8")
            print(f"wrote the providers table to {README}: {len(data['tools'])} tool(s)")
        else:
            print(f"the providers table in {README} is already current")
        return 0

    if current != block:
        print(
            f"::error file={README}::the providers table in {README} does not match "
            f"{PROVIDERS_FILE}; run `{WRITE_COMMAND}` (or `make providers`) and commit "
            "the result"
        )
        return 1
    print(f"providers table is current: {len(data['tools'])} tool(s) from {PROVIDERS_FILE}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="providers_table", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    parser.add_argument(
        "--write",
        action="store_true",
        help=f"rewrite the table in {README} from {PROVIDERS_FILE} instead of checking it",
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="the date staleness is measured from, as YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)
    return run(args.root.resolve(), args.write, args.today)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
