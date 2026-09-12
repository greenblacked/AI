#!/usr/bin/env python3
"""Fail when a plugin's skill listing grows past its recorded ceiling.

Every description a plugin ships is resident in context for the whole session, and the
runtime caps that listing at roughly 1% of the context window. Past the cap it drops the
descriptions of the least-used skills: they stay invocable by name and stop being chosen
on their own. Nothing raises an error, nothing appears in a log, and the skill simply
never fires again.

That is what the seven-plugin split was for, and nothing stopped it regressing. The
validator prints the per-plugin total and `--listing-budget` warns against one number,
but two plugins are already over the runtime default, so a single threshold can only be
set where it catches nothing. This is a ratchet instead, in the same shape as the
coverage floor: each plugin's ceiling is recorded in ``listing-budget.json`` with a few
hundred characters of slack, so rewording stays free and adding a skill does not. When it
fails, either trim a description, split the plugin, or raise the ceiling deliberately
with ``--update`` and say why in the commit.

Standard library only, like the validator it imports: no dependency may stand between a
bare interpreter and a green build.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402
from skillcheck.rules import find_plugins, find_skills  # noqa: E402

BUDGET_FILE = "listing-budget.json"

# Claude Code's default listing budget is about 1% of the context window, which is
# roughly this for a 200k model. A plugin above it is not an error — a reader who
# installs one plugin is fine, and the split already did the work that could be done —
# but it is worth saying out loud on every run rather than discovering later.
RUNTIME_DEFAULT = 8000

# How much slack a recorded ceiling carries over the measured total. A description is
# 500-900 characters, so this lets prose be reworded and refuses to let a skill be added
# without someone deciding to raise the ceiling.
#
# HEADROOM is a floor on that slack, not decoration. Rounding alone gave a plugin
# measuring 4,499 exactly one character before the gate failed, which makes "rewording
# stays free" untrue for whichever plugins happen to land near a boundary — and a gate
# that fails on a two-character edit is one people route around.
GRANULARITY = 500
HEADROOM = 150


def measure(root: Path) -> dict[str, int]:
    """Characters of description each plugin puts into the listing, by plugin name."""
    plugins = find_plugins(root)
    sizes = {plugin.name: 0 for plugin in plugins}
    for skill in find_skills(root):
        try:
            description = parse((skill / "SKILL.md").read_text(encoding="utf-8")).get(
                "description", ""
            )
        except (OSError, FrontmatterError, UnicodeDecodeError):
            continue  # the validator reports a malformed skill; this is not its job
        for plugin in plugins:
            if skill.is_relative_to(plugin):
                sizes[plugin.name] += len(" ".join((description or "").split()))
                break
    return sizes


def ceiling_for(size: int) -> int:
    """The ceiling a measured total earns: rounded up to the next step, and at least
    HEADROOM above the total itself so a plugin sitting just under a boundary still has
    room to reword."""
    rounded = max(GRANULARITY, math.ceil(size / GRANULARITY) * GRANULARITY)
    while rounded - size < HEADROOM:
        rounded += GRANULARITY
    return rounded


def load(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), dict):
        raise ValueError(f"{path.name} must be an object with a 'plugins' object in it")
    return {str(name): int(value) for name, value in data["plugins"].items()}


def write(path: Path, sizes: dict[str, int]) -> None:
    body = {
        "_comment": (
            "Per-plugin ceilings for the skill listing, in characters. Regenerate with "
            "scripts/check_listing_budget.py --update, and say in the commit why a "
            "ceiling went up."
        ),
        "runtime_default": RUNTIME_DEFAULT,
        "plugins": {name: ceiling_for(sizes[name]) for name in sorted(sizes)},
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def check(root: Path, update: bool = False) -> int:
    path = root / BUDGET_FILE
    sizes = measure(root)
    if not sizes:
        print(f"no plugins found under {root}", file=sys.stderr)
        return 2

    if update:
        write(path, sizes)
        print(f"wrote {BUDGET_FILE} for {len(sizes)} plugin(s)")
        return 0

    if not path.is_file():
        print(f"{BUDGET_FILE} is missing; create it with --update", file=sys.stderr)
        return 1
    try:
        ceilings = load(path)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"{BUDGET_FILE}: {error}", file=sys.stderr)
        return 1

    failed = False
    # A plugin that appears in one place and not the other is drift in its own right:
    # a new plugin with no ceiling is unmeasured, and a stale entry means the file was
    # not regenerated when a plugin was renamed or removed.
    for name in sorted(set(sizes) - set(ceilings)):
        print(f"::error::{name} has no ceiling in {BUDGET_FILE}; run --update")
        failed = True
    for name in sorted(set(ceilings) - set(sizes)):
        print(f"::error::{BUDGET_FILE} records {name}, which is not a plugin; run --update")
        failed = True

    total = sum(sizes.values())
    over_runtime = []
    for name in sorted(sizes):
        size, ceiling = sizes[name], ceilings.get(name)
        if ceiling is not None and size > ceiling:
            print(
                f"::error::{name} listing is {size:,} characters against a ceiling of "
                f"{ceiling:,}; trim a description, split the plugin, or raise the ceiling "
                "with --update and say why"
            )
            failed = True
        marker = " (over the runtime default)" if size > RUNTIME_DEFAULT else ""
        if marker:
            over_runtime.append(name)
        headroom = "" if ceiling is None else f", ceiling {ceiling:,}"
        print(f"{name}: {size:,}{headroom}{marker}")

    print(f"\ntotal across {len(sizes)} plugin(s): {total:,} characters")
    if over_runtime:
        # Not a failure. Someone who installs one plugin is unaffected, and the split
        # has already done what a split can do; the number is here so it stays visible.
        print(
            f"above the ~{RUNTIME_DEFAULT:,} runtime default on their own: "
            f"{', '.join(over_runtime)}"
        )
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_listing_budget", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    parser.add_argument(
        "--update",
        action="store_true",
        help=f"rewrite {BUDGET_FILE} from the current totals instead of checking against it",
    )
    args = parser.parse_args(argv)
    return check(args.root.resolve(), args.update)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
