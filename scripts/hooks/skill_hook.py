#!/usr/bin/env python3
"""PostToolUse hook: validate a skill the moment it is written, not in CI.

Claude Code passes the tool call as JSON on stdin. If the file just written was part
of a skill, run the repository's validator and report only the errors that belong to
that skill. Exiting 2 is what puts the message in front of the agent that made the
edit, which is the whole point: a dangling `references/` pointer costs nothing to fix
now and is invisible until someone reads the CI log.

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


def edited_skill(payload: dict) -> Path | None:
    """Return the skill directory the edited file belongs to, if any."""
    raw = payload.get("tool_input", {}).get("file_path")
    if not raw:
        return None
    try:
        path = Path(raw).resolve().relative_to(ROOT)
    except ValueError:
        return None  # outside the repository
    for parent in [path, *path.parents]:
        if (ROOT / parent / "SKILL.md").is_file():
            return parent
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    skill = edited_skill(payload)
    if skill is None:
        return 0

    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "skillcheck", str(ROOT), "--skip-marketplace"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )

    prefix = f"ERROR   {skill}/"
    errors = [line for line in result.stdout.splitlines() if line.startswith(prefix)]
    if not errors:
        return 0

    print(f"skillcheck found {len(errors)} error(s) in {skill}:", file=sys.stderr)
    for line in errors:
        print(line.removeprefix("ERROR   "), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
