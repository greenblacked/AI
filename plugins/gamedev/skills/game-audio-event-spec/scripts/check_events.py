#!/usr/bin/env python3
"""Compare an audio event table with the event ids a code tree uses.

Standard library only. Usage:

    check_events.py TABLE.csv CODE_DIR [--prefix P ...] [--ext .gd .cs ...]

TABLE.csv has a header row naming at least these columns:
    id, trigger, variants, bus, priority, max_instances, steal, duck_group, spatial

An id is a dotted lowercase name such as sfx.player.footstep. The first segment
is the prefix. A string literal in code counts as a use when it looks like an id
and its prefix is one the table uses (or one passed with --prefix), so ordinary
strings that merely contain a dot are ignored.

Prints one "id: code: reason" line per finding and exits 1 if there are any.
Codes: missing-from-table, unused-row, duplicate-id, empty-field, bad-value.
"""

import argparse
import csv
import os
import re
import sys

REQUIRED = (
    "id",
    "trigger",
    "variants",
    "bus",
    "priority",
    "max_instances",
    "steal",
    "duck_group",
    "spatial",
)
SPATIAL = {"2d", "3d"}
STEAL = {"oldest", "quietest", "lowest-priority", "none"}
ID = r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+"
LITERAL = re.compile(r"""["'](""" + ID + r""")["']""")
SKIP_DIRS = {".git", "node_modules", "Library", "Temp", "obj", "bin", "__pycache__"}
DEFAULT_EXT = (
    ".gd",
    ".cs",
    ".cpp",
    ".h",
    ".hpp",
    ".c",
    ".lua",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".tscn",
)


def read_table(path):
    findings, rows = [], {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"{path}: header lacks columns: {', '.join(missing)}")
        for row in reader:
            eid = (row["id"] or "").strip()
            if not eid:
                # A row with other fields filled in is an unfinished event, not a blank line.
                if any((v or "").strip() for k, v in row.items() if k != "id"):
                    label = f"(no id, line {reader.line_num})"
                    findings.append((label, "empty-field", "id is empty"))
                continue
            if eid in rows:
                findings.append((eid, "duplicate-id", "appears more than once in the table"))
                continue
            rows[eid] = row
            if not re.fullmatch(ID, eid):
                findings.append((eid, "bad-value", "id is not dotted lowercase"))
            for col in REQUIRED:
                if not (row[col] or "").strip():
                    findings.append((eid, "empty-field", f"{col} is empty"))
            for col in ("priority", "max_instances"):
                value = (row[col] or "").strip()
                # Empty is already an empty-field finding; do not report it twice.
                if value and not (value.isascii() and value.isdigit()):
                    findings.append((eid, "bad-value", f"{col} is not a whole number"))
            if (row["spatial"] or "").strip().lower() not in SPATIAL:
                findings.append((eid, "bad-value", "spatial must be 2d or 3d"))
            if (row["steal"] or "").strip().lower() not in STEAL:
                findings.append(
                    (eid, "bad-value", f"steal must be one of {', '.join(sorted(STEAL))}")
                )
    return rows, findings


def scan(root, exts, prefixes):
    used = {}
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(exts):
                continue
            path = os.path.join(here, name)
            # A named pipe or device opens by blocking, so only regular files are read.
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        for m in LITERAL.finditer(line):
                            if m.group(1).split(".")[0] in prefixes:
                                used.setdefault(m.group(1), f"{path}:{n}")
            except OSError as exc:
                print(f"{path}: unreadable: {exc}", file=sys.stderr)
    return used


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("table")
    ap.add_argument("code_dir")
    ap.add_argument(
        "--prefix", nargs="*", default=[], help="extra id prefixes to treat as event ids"
    )
    ap.add_argument("--ext", nargs="*", default=list(DEFAULT_EXT), help="file extensions to scan")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.code_dir):
        ap.error(f"{args.code_dir}: not a directory; every row would be reported unused")
    rows, findings = read_table(args.table)
    prefixes = {i.split(".")[0] for i in rows} | set(args.prefix)
    used = scan(args.code_dir, tuple(args.ext), prefixes)
    for eid, where in sorted(used.items()):
        if eid not in rows:
            findings.append((eid, "missing-from-table", f"used at {where}"))
    for eid in sorted(rows):
        if eid not in used:
            findings.append((eid, "unused-row", "no string literal in the code tree names it"))
    for eid, code, why in findings:
        print(f"{eid}: {code}: {why}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
