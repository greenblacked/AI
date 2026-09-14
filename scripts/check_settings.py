#!/usr/bin/env python3
"""Fail when the hook registration in `.claude/settings.json` points at nothing.

`.claude/settings.json` is the only file in this repository that nothing else reads.
The validator does not know it exists, `make package` does not ship it, and
`tests/test_skill_hook.py` feeds the hook script on stdin without ever looking at how it
is registered. So the one line that decides whether the hook runs at all — the path in
`command` — is the one line no gate covers. A typo in it, or a stale path left behind
when the script moves, disables the hook with no error anywhere: sessions carry on, skills
are written unvalidated, and the first symptom is a bad skill reaching CI weeks later.

What is checked, all of it mechanical:

- the file parses as JSON, and has the shape the runtime expects
- every hook `command` names a file that exists, after `$CLAUDE_PROJECT_DIR` is
  substituted for the repository root
- that file is executable, since the runtime executes it rather than interpreting it
- `matcher` is present and non-empty

What is not checked is what the matcher means. How the runtime anchors that pattern and
which events take a matcher at all are not settled here, and a check that guessed would
fail a correct registration — worse than no check, because it is the kind people learn to
override.

A command that names no file at all — a bare binary like `jq`, an inline one-liner — is
reported rather than skipped. Every hook registered here runs a script in the tree, and
the alternative is a check with a hole in it exactly where a typo lands: a mistyped path
with no separator left in it would read as a system binary and pass. Registering
something other than a script is then a deliberate change to this file rather than a
silent one.

A repository with no `.claude/settings.json` has no hooks, which is not a defect. This
sits in `scripts/` rather than `src/skillcheck/` because it is a claim the repository
makes about itself, like the README check beside it, and not part of the skill contract
every installer's tree has to satisfy.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

SETTINGS_FILE = Path(".claude") / "settings.json"
PROJECT_DIR_VARS = ("${CLAUDE_PROJECT_DIR}", "$CLAUDE_PROJECT_DIR")


def executable_path(command: str, root: Path) -> Path | None:
    """The file a hook `command` runs, or None when it names no file at all.

    The command is a shell line, so the file is the first word of it; anything after
    that is arguments. A first word with no path separator is a binary from PATH rather
    than a script in the tree, which is not the shape any registration here uses.
    """
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    if not words:
        return None
    first = words[0]
    for variable in PROJECT_DIR_VARS:
        first = first.replace(variable, str(root))
    if os.sep not in first and (os.altsep is None or os.altsep not in first):
        return None
    return Path(first) if Path(first).is_absolute() else (root / first)


def check(root: Path) -> int:
    path = root / SETTINGS_FILE
    if not path.is_file():
        print(f"no {SETTINGS_FILE} under {root}, so there are no hooks to check")
        return 0

    problems: list[str] = []

    def fail(message: str) -> None:
        problems.append(message)
        print(f"::error file={SETTINGS_FILE.as_posix()}::{message}")

    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"does not parse as JSON: {error}")
        return 1
    if not isinstance(settings, dict):
        fail(f"holds a {type(settings).__name__}, and the runtime expects an object")
        return 1

    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        fail("`hooks` is not an object, so no registration in it can load")
        return 1

    commands = 0
    for event in sorted(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            fail(f"the {event} registration is not a list of matcher groups")
            continue
        for index, group in enumerate(groups):
            where = f"{event}[{index}]"
            if not isinstance(group, dict):
                fail(f"{where} is not an object")
                continue

            matcher = group.get("matcher")
            if matcher is None:
                fail(f"{where} has no matcher, so nothing says which tools it runs on")
            elif not isinstance(matcher, str) or not matcher.strip():
                fail(f"{where} has an empty matcher, so nothing says which tools it runs on")

            entries = group.get("hooks")
            if not isinstance(entries, list) or not entries:
                fail(f"{where} registers no hooks, so the matcher runs nothing")
                continue

            for position, entry in enumerate(entries):
                seat = f"{where}.hooks[{position}]"
                if not isinstance(entry, dict):
                    fail(f"{seat} is not an object")
                    continue
                command = entry.get("command")
                if not isinstance(command, str) or not command.strip():
                    fail(f"{seat} has no command, so the registration does nothing")
                    continue
                commands += 1

                target = executable_path(command, root)
                if target is None:
                    fail(
                        f"{seat} runs {command!r}, which names no file — a hook here runs a "
                        f"script in the tree, named from $CLAUDE_PROJECT_DIR"
                    )
                    continue
                try:
                    inside = target.resolve().relative_to(root.resolve())
                except ValueError:
                    fail(
                        f"{seat} runs {target}, which is outside the repository and will not "
                        f"exist in anyone else's clone"
                    )
                    continue
                if not target.is_file():
                    fail(f"{seat} runs {inside}, which does not exist")
                elif not os.access(target, os.X_OK):
                    fail(f"{seat} runs {inside}, which is not executable")

    if problems:
        print(f"\n{len(problems)} settings problem(s)", file=sys.stderr)
        return 1
    print(
        f"{SETTINGS_FILE.as_posix()} is wired: {commands} hook command(s) across "
        f"{len(hooks)} event(s), each present, executable and matched"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_settings", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
