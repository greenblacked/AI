#!/usr/bin/env python3
"""PostToolUse hook: validate what was just written, not in CI.

Claude Code passes the tool call as JSON on stdin. If the file just written is one the
validator covers — a skill, a subagent, a slash command or a rule — run the validator
and report only the errors belonging to it. Exiting 2 is what puts the message in
front of the agent that made the edit, which is the whole point: a dangling
`references/` pointer costs nothing to fix now and is invisible until someone reads
the CI log twenty minutes later.

Warnings are deliberately not reported here. They are judgement calls, and a hook that
interrupts on a judgement call teaches people to remove the hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# The three directory names that hold a single-file target, under `.claude/` or inside
# a plugin. This deliberately does not list which files the validator accepts: a path it
# never reads produces no findings, so the filter in `main` matches nothing and the hook
# stays silent. Keeping that knowledge in the validator alone is what stops the two
# drifting apart.
FILE_TARGET_DIRS = ("agents", "commands", "rules")


def _is_file_target(path: Path) -> bool:
    """Is this a subagent, command or rule — something that owns only its own findings?"""
    if path.suffix != ".md":
        return False
    parts = path.parts
    for index, part in enumerate(parts[:-1]):
        if part not in FILE_TARGET_DIRS:
            continue
        if index == 1 and parts[0] == ".claude":
            return True
        if index == 2 and parts[0] == "plugins":
            return True
    return False


def edited_target(payload: object) -> tuple[str, str] | None:
    """Return what the edit belongs to, and the prefix its findings start with.

    A skill owns a directory: editing a reference file under it should surface the
    `SKILL.md` error that edit just created, so every path beneath the directory
    counts. A subagent, command or rule is one file and owns only itself, which is why
    the two cases end in `/` and `:` respectively — the validator prints
    `<path>:<line>`, so those two prefixes are what separate a directory's findings
    from one file's.
    """
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    try:
        path = Path(raw).resolve().relative_to(ROOT)
    except ValueError:
        return None  # outside the repository
    for parent in [path, *path.parents]:
        if (ROOT / parent / "SKILL.md").is_file():
            return str(parent), f"{parent}/"
    if _is_file_target(path):
        return str(path), f"{path}:"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    target = edited_target(payload)
    if target is None:
        return 0
    name, key = target

    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "skillcheck", str(ROOT), "--skip-marketplace"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )

    prefix = f"ERROR   {key}"
    errors = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
    if not errors:
        return 0

    print(f"skillcheck found {len(errors)} error(s) in {name}:", file=sys.stderr)
    for line in errors:
        print(line.removeprefix("ERROR   "), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
