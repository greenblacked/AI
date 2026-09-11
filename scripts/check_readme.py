#!/usr/bin/env python3
"""Fail when the README stops describing what is actually in the repository.

The README is a catalogue: a badge counting the skills, a table of per-plugin contents,
and one row per skill, subagent and command. Every one of those is a number or a name
that goes stale when something is added, removed or moved, and nothing notices — a
reader is told the library contains something it does not, or is not told about the skill
they wanted. This repository has drifted that way twice, both times after plugins were
re-cut, and both times it was caught by someone reading rather than by a gate.

What is checked, all of it mechanical:

- the skills badge count against the skills on disk
- one row per skill, linking to a `SKILL.md` that exists
- no row for a skill that is gone
- the per-plugin contents table against what each plugin actually ships
- one row per shipped subagent and per shipped command

What is not checked is the prose, including the sentence that spells the counts in
words. A check that tried to parse that would fail on a rewrite that was perfectly
correct, and a gate that cries wolf is one people learn to override.

Standard library only, like the validator it imports.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.rules import find_agents, find_commands, find_plugins, find_skills  # noqa: E402

# `[`name`](plugins/<plugin>/skills/<name>/SKILL.md)` — the shape every skill row uses.
SKILL_ROW_RE = re.compile(r"\[`([a-z0-9-]+)`\]\((plugins/[^)]*?/skills/[^)]*?/SKILL\.md)\)")
BADGE_RE = re.compile(r"img\.shields\.io/badge/skills-(\d+)-")
# A row in the "What is included" table: | `coding` | focus | 12 skills, 1 subagent |
CONTENTS_ROW_RE = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|[^|]*\|([^|]*)\|", re.M)
COUNT_RES = {
    "skills": re.compile(r"(\d+)\s+skills?\b"),
    "subagents": re.compile(r"(\d+)\s+subagents?\b"),
    "commands": re.compile(r"(\d+)\s+commands?\b"),
}


def on_disk(root: Path) -> dict[str, dict[str, set[str]]]:
    """What each plugin actually ships, by plugin name."""
    contents = {}
    for plugin in find_plugins(root):
        skills = {d.name for d in find_skills(plugin / "skills")}
        contents[plugin.name] = {
            "skills": skills,
            "subagents": {a.stem for a in find_agents(plugin / "agents")},
            "commands": {c.stem for c in find_commands(plugin / "commands")},
        }
    return contents


def check(root: Path) -> int:
    readme = root / "README.md"
    if not readme.is_file():
        print(f"no README.md under {root}", file=sys.stderr)
        return 2
    text = readme.read_text(encoding="utf-8")
    contents = on_disk(root)
    problems: list[str] = []

    def fail(message: str) -> None:
        problems.append(message)
        print(f"::error file=README.md::{message}")

    # --- skills: every one listed once, every listed one real -------------------------
    every_skill = {name for plugin in contents.values() for name in plugin["skills"]}
    listed: dict[str, int] = {}
    for name, path in SKILL_ROW_RE.findall(text):
        listed[name] = listed.get(name, 0) + 1
        if not (root / path).is_file():
            fail(f"the row for {name!r} links to {path}, which does not exist")
        elif (root / path).parent.name != name:
            fail(f"the row for {name!r} links to {path}, which is a different skill")

    for name in sorted(every_skill - set(listed)):
        fail(f"{name} is in the repository and has no row in the README")
    for name in sorted(set(listed) - every_skill):
        fail(f"the README has a row for {name}, which is not a skill in any plugin")
    for name in sorted(n for n, count in listed.items() if count > 1):
        fail(f"{name} has {listed[name]} rows in the README; it should have one")

    badge = BADGE_RE.search(text)
    if badge is None:
        fail("no skills badge found, so nothing states the count")
    elif int(badge.group(1)) != len(every_skill):
        fail(f"the skills badge says {badge.group(1)}, and there are {len(every_skill)}")

    # --- subagents and commands: every shipped one has a row --------------------------
    for kind, key in (("subagent", "subagents"), ("command", "commands")):
        for plugin in sorted(contents):
            for name in sorted(contents[plugin][key]):
                # A command is written `/name` in its table and a subagent as `name`;
                # matching the backticked name covers both without parsing the table.
                if f"`{name}`" not in text and f"`/{name}`" not in text:
                    fail(f"{kind} {name} ships with {plugin} and has no row in the README")

    # --- the per-plugin contents table ------------------------------------------------
    seen_in_table = set()
    for plugin, cell in CONTENTS_ROW_RE.findall(text):
        if plugin not in contents:
            continue  # a backticked name in some other table; the checks above own those
        seen_in_table.add(plugin)
        for key, pattern in COUNT_RES.items():
            match = pattern.search(cell)
            stated = int(match.group(1)) if match else 0
            actual = len(contents[plugin][key])
            if stated != actual:
                fail(f"the contents table says {plugin} has {stated} {key}, and it has {actual}")
    for plugin in sorted(set(contents) - seen_in_table):
        fail(f"{plugin} is a plugin and has no row in the contents table")

    if problems:
        print(f"\n{len(problems)} README problem(s)", file=sys.stderr)
        return 1
    print(
        f"README is current: {len(every_skill)} skill(s) across {len(contents)} plugin(s), "
        "contents table and badge agree with the tree"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_readme", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
