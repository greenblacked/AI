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

- the Python badge against the interpreter matrix CI actually runs
- the coverage badge against the floor `pyproject.toml` enforces
- a count spelled out in the prose, against the same totals

That last one was left out on purpose once, on the reasoning that parsing prose would
fail on a rewrite that was perfectly correct, and a gate that cries wolf is one people
learn to override. The exemption then produced exactly the failure this file exists to
prevent: the opening sentence claimed seven slash commands while six shipped, and it
survived several merges because the table and the badge were right and nothing read the
sentence. It was caught by a reviewer, which is the outcome named two paragraphs above.

The check is narrow enough to be safe rather than clever. It reads only lines outside
tables and fenced blocks, only a number immediately followed by one of six nouns, and
only where the number is a digit or a number word. Measured against this README it
matches six phrases and every one is a real count. `plugins` is deliberately not one of
the nouns: the prose uses it for two different true values, all eight of them in one
sentence and the five that ship a subagent in another, so a single expected total would
be wrong somewhere.

The two badges that state what CI enforces are floors, not live figures. A coverage
badge showing the real percentage would have to be typed by hand, and a typed number
in a README is exactly how the slash-command count went wrong. Stating the floor is
honest and checkable: the badge must match `fail_under`, and the Python badge must
match the test matrix, so neither drifts when its source of truth moves. The check runs
in both directions: a badge is required while its source exists, and a badge left
behind after the source is removed fails too, because that is a guarantee with nothing
enforcing it, which is the trigger-eval badge this file refused to add.

Standard library only, like the validator it imports.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.rules import find_agents, find_commands, find_plugins, find_skills  # noqa: E402

# `[`name`](plugins/<plugin>/skills/<name>/SKILL.md)` — the shape every skill row uses.
SKILL_ROW_RE = re.compile(r"\[`([a-z0-9-]+)`\]\((plugins/[^)]*?/skills/[^)]*?/SKILL\.md)\)")
# A table row's first cell: `name` for a subagent, `/name` for a command. Anchored to
# the start of the line — unlike `SKILL_ROW_RE` above, whose distinctive
# `[`name`](path)` link shape only ever occurs in a table row in practice, a bare
# backticked name has no such shape of its own and needs the anchor to tell a row apart
# from a mention in prose, e.g. "the `weekly` command reads pull requests". Before this
# was anchored, that prose mention alone made the check pass with no table row anywhere
# for the name it was actually about.
AGENT_OR_COMMAND_ROW_RE = re.compile(r"^\|\s*`(/?[a-z0-9-]+)`", re.M)
BADGE_RE = re.compile(r"img\.shields\.io/badge/skills-(\d+)-")
# The version list is URL-encoded in the badge ("3.10%20%7C%203.11") and is decoded
# before comparison. The trailing colour is what bounds the capture.
PYTHON_BADGE_RE = re.compile(r"img\.shields\.io/badge/python-(.+?)-[0-9a-f]{6}\)")
# "≥" arrives as %E2%89%A5 and "%" as %25; the number between them is the floor.
COVERAGE_BADGE_RE = re.compile(r"img\.shields\.io/badge/coverage-(?:%E2%89%A5)?(\d+)%25-")
CI_MATRIX_RE = re.compile(r"python-version:\s*\[([^\]]*)\]")
FAIL_UNDER_RE = re.compile(r"^fail_under\s*=\s*(\d+)", re.M)
# A row in the "What is included" table: | `coding` | focus | 12 skills, 1 subagent |,
# or with the name linked to that plugin's section: | [`coding`](#coding) | ... |
CONTENTS_ROW_RE = re.compile(
    r"^\|\s*\[?`([a-z0-9-]+)`(?:\]\(([^)\s]*)\))?\s*\|[^|]*\|([^|]*)\|", re.M
)
# The skills section a linked contents row points at, e.g. "### Coding" for #coding.
SECTION_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.M)
COUNT_RES = {
    "skills": re.compile(r"(\d+)\s+skills?\b"),
    "subagents": re.compile(r"(\d+)\s+subagents?\b"),
    "commands": re.compile(r"(\d+)\s+commands?\b"),
}

# Counts in the prose are written in words as often as in digits. Twenty is well above
# anything this repository will spell out rather than tabulate.
NUMBER_WORDS = {
    word: value
    for value, word in enumerate(
        [
            *("zero", "one", "two", "three", "four", "five", "six", "seven"),
            *("eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen"),
            *("fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"),
        ]
    )
}
# The qualified forms come first so the alternation prefers them: "agent skills" must not
# match as bare "skills" and leave "agent" as the number.
PROSE_NOUNS = {
    "agent skills": "skills",
    "read-only subagents": "subagents",
    "slash commands": "commands",
    "skills": "skills",
    "subagents": "subagents",
    "commands": "commands",
}
PROSE_COUNT_RE = re.compile(
    rf"\b([A-Za-z]+|\d+)\s+({'|'.join(PROSE_NOUNS)})\b",
    re.I,
)


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Every numbered line that is prose rather than a table row or fenced code.

    A table row states a per-plugin count and is checked against that plugin, not
    against the repository total, so reading one here would invent a failure.
    """
    out: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.lstrip().startswith("|"):
            continue
        out.append((number, line))
    return out


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


def ci_python_matrix(root: Path) -> list[str] | None:
    """The interpreter versions CI's test matrix runs, or None when there is no matrix."""
    workflow = root / ".github" / "workflows" / "ci.yml"
    if not workflow.is_file():
        return None
    match = CI_MATRIX_RE.search(workflow.read_text(encoding="utf-8"))
    if match is None:
        return None
    # Single quotes, double quotes or none: the workflow's style is not the contract.
    return re.findall(r"(\d+\.\d+)", match.group(1))


def coverage_floor(root: Path) -> int | None:
    """The coverage percentage `make coverage` fails below, or None when none is set."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    match = FAIL_UNDER_RE.search(pyproject.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else None


def check(root: Path) -> int:
    readme = root / "README.md"
    if not readme.is_file():
        print(f"no README.md under {root}", file=sys.stderr)
        return 2
    text = readme.read_text(encoding="utf-8")
    contents = on_disk(root)
    problems: list[str] = []
    row_names = set(AGENT_OR_COMMAND_ROW_RE.findall(text))

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

    # --- badges that state what CI enforces ------------------------------------------
    matrix = ci_python_matrix(root)
    python_badge = PYTHON_BADGE_RE.search(text)
    if matrix is None and python_badge is not None:
        fail("the README has a python badge and CI runs no interpreter matrix to back it")
    elif matrix is not None:
        if python_badge is None:
            fail("CI runs a Python matrix and the README has no python badge stating it")
        else:
            stated = [v.strip() for v in unquote(python_badge.group(1)).split("|")]
            if sorted(stated) != sorted(matrix):
                fail(f"the python badge says {', '.join(stated)}, and CI tests {', '.join(matrix)}")
    floor = coverage_floor(root)
    coverage_badge = COVERAGE_BADGE_RE.search(text)
    if floor is None and coverage_badge is not None:
        fail("the README states a coverage floor and pyproject.toml sets none")
    elif floor is not None:
        if coverage_badge is None:
            fail(
                f"pyproject.toml fails coverage below {floor} and the README has no "
                "badge stating it"
            )
        elif int(coverage_badge.group(1)) != floor:
            fail(
                f"the coverage badge says {coverage_badge.group(1)}, and pyproject.toml "
                f"fails below {floor}"
            )

    # --- subagents and commands: every shipped one has a row --------------------------
    # A row is the first cell of a table line, not a backticked name anywhere in the
    # document: a mention in prose used to satisfy this check with no table row for the
    # name it was actually about, the same gap `SKILL_ROW_RE` never had for a skill.
    for kind, key, mark in (("subagent", "subagents", ""), ("command", "commands", "/")):
        for plugin in sorted(contents):
            for name in sorted(contents[plugin][key]):
                if f"{mark}{name}" not in row_names:
                    fail(f"{kind} {name} ships with {plugin} and has no row in the README")

    # --- the repository's own agents and commands -------------------------------------
    # The loop above covers anything a plugin ships. Nothing covered `.claude/`, so a
    # subagent or command written for work on this repository could exist with no row
    # and no gate would say so — which is how the three-stage loop's own documentation
    # went stale. These ship to nobody but they are listed in the README all the same.
    for directory, kind, mark in (
        (root / ".claude" / "agents", "subagent", ""),
        (root / ".claude" / "commands", "command", "/"),
    ):
        finder = find_agents if kind == "subagent" else find_commands
        for path in finder(directory):
            if f"{mark}{path.stem}" not in row_names:
                fail(f"{kind} {mark}{path.stem} is in .claude/ and has no row in the README")

    # --- counts spelled out in the prose ----------------------------------------------
    totals = {
        "skills": len(every_skill),
        "subagents": len({n for p in contents.values() for n in p["subagents"]}),
        "commands": len({n for p in contents.values() for n in p["commands"]}),
    }
    for number, line in prose_lines(text):
        for stated, noun in PROSE_COUNT_RE.findall(line):
            if stated.isdigit():
                value = int(stated)
            elif stated.lower() in NUMBER_WORDS:
                value = NUMBER_WORDS[stated.lower()]
            else:
                continue  # ordinary prose — "the skills", "installed subagents"
            kind = PROSE_NOUNS[noun.lower()]
            if value != totals[kind]:
                fail(
                    f"line {number} says {stated} {noun}, and there are "
                    f"{totals[kind]}; if that sentence counts something narrower than "
                    f"the whole repository, say so in words the count cannot be read from"
                )

    # --- the per-plugin contents table ------------------------------------------------
    seen_in_table = set()
    # A linked name has to land on that plugin's own section: the link renders and
    # resolves whatever it points at, so a row copied from its neighbour would send the
    # reader to the wrong plugin with nothing else to notice.
    headings = {h.strip().lower() for h in SECTION_HEADING_RE.findall(text)}
    for plugin, target, cell in CONTENTS_ROW_RE.findall(text):
        if plugin not in contents:
            continue  # a backticked name in some other table; the checks above own those
        seen_in_table.add(plugin)
        # Only an in-page link is a contents-table link; a skill or command row that
        # happens to share a plugin's name links to a file path and is not this check's.
        in_page = target.startswith("#")
        if in_page and target != f"#{plugin}":
            fail(f"the contents table links {plugin} to {target}; its section is #{plugin}")
        elif in_page and plugin not in headings:
            fail(f"the contents table links {plugin} to #{plugin}, and no heading makes it")
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
