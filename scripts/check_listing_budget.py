#!/usr/bin/env python3
"""Fail when a plugin's listing, or a skill's description, grows past its record.

Every description a plugin ships is resident in context for the whole session, and the
runtime caps that listing at roughly 1% of the context window. Past the cap it drops the
descriptions of the least-used skills: they stay invocable by name and stop being chosen
on their own. Nothing raises an error, nothing appears in a log, and the skill simply
never fires again.

That is what the eight-plugin split was for, and nothing stopped it regressing. The
validator prints the per-plugin total and `--listing-budget` warns against one number,
but six plugins are already over the runtime default, so a single threshold can only be
set where it catches nothing. This is a ratchet instead, in the same shape as the
coverage floor: each plugin's ceiling is recorded in ``listing-budget.json`` with a few
hundred characters of slack, so rewording stays free and adding a skill does not. When it
fails, either trim a description, split the plugin, or raise the ceiling deliberately
with ``--update`` and say why in the commit.

The same file carries a per-skill ratchet, for the same reason one step down. A plugin's
total is the sum of its descriptions, so a ceiling with slack in it says nothing about any
one of them, and a description that drifts past the guidance costs every session it is
resident in. A flat rule cannot be the answer here either: a third of the descriptions in
this repository are already over the guidance, and they were written against measured
routing scores, so clearing a flat rule would mean editing descriptions to satisfy a
check. So what exists is recorded at what it measures and may not grow, and a skill with
no record is new and has to come in at or under DESCRIPTION_TARGET.

Standard library only, like the validator it imports: no dependency may stand between a
bare interpreter and a green build.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402
from skillcheck.rules import find_plugins, find_skills  # noqa: E402

BUDGET_FILE = "listing-budget.json"

# Claude Code's default listing budget is about 1% of the context window, which is
# roughly this for a 200k model. A plugin above it is not an error — a reader who
# installs one plugin is fine, and the split already did the work that could be done —
# but it is worth saying out loud on every run rather than discovering later.
RUNTIME_DEFAULT = 8000

# Characters per token, measured over every description in this repository with the
# 65,000-entry BPE vocabulary this runtime family publishes — the older published one,
# since the current model's is not released. It sat between 4.54 and 4.70 across the eight
# plugins, so it is a property of this library as a whole rather than of any one
# description; per skill the spread is wider and the report only ever applies it to plugin
# totals. It is recorded rather than computed on the fly: tokenizing needs a dependency and
# a megabyte of vocabulary, and this repository's validator is standard library only.
#
# To re-measure, encode each description exactly as measure() normalises it — whitespace
# collapsed — and divide total characters by total tokens. Change the constant and every
# figure below follows, including the comment written into listing-budget.json.
#
# It is here because RUNTIME_DEFAULT is a character figure standing in for a token one.
# One per cent of a 200k-token window is 2,000 tokens, which is about 9,250 characters at
# this ratio, so the 8,000 above is roughly 14% stricter than the sentence it encodes. A
# plugin a little over it has not necessarily spent one per cent of anything, and the
# report says so rather than leaving the reader with the alarming half of the pair.
CHARS_PER_TOKEN = 4.63
CONTEXT_WINDOW_TOKENS = 200_000
README = Path("README.md")
# Every file that tells a reader which fraction to set. The README was checked alone and
# `docs/using.md` was not, which is how it kept recommending 0.04 after the README stopped:
# the fix went to the page people read first and not to the one it links to for detail.
ADVICE_FILES = (README, Path("docs/using.md"))
# `{ "skillListingBudgetFraction": <n> }` in each advice file — the setting it tells a
# reader to raise when they install several plugins.
FRACTION_RE = re.compile(r'"skillListingBudgetFraction"\s*:\s*([0-9.]+)')

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

# The length a description that has no record yet has to come in at. AGENTS.md asks for
# 500-900 characters and the upper end of that was never enforced, so 34 of the 87
# descriptions here are above it, up to 971. That is why this is a ratchet and not a
# threshold: the only way to clear a flat rule would be to trim 34 descriptions that were
# written against measured routing scores, which is editing a description to satisfy a
# check. Recorded lengths grandfather those; this number gates everything new.
DESCRIPTION_TARGET = 900


class Recorded(NamedTuple):
    """What listing-budget.json records: a ceiling per plugin, a length per skill."""

    plugins: dict[str, int]
    skills: dict[str, int]


def walk(root: Path) -> list[tuple[str, str, int]]:
    """(plugin, skill, description length) for every skill that sits inside a plugin.

    One pass feeds both the per-plugin totals and the per-skill ratchet, so the two
    numbers are the same measurement of the same text and cannot disagree. A skill
    outside every plugin installs for nobody and the validator errors on it; it is left
    out here rather than counted against a plugin it is not in.
    """
    plugins = find_plugins(root)
    entries: list[tuple[str, str, int]] = []
    for skill in find_skills(root):
        try:
            description = parse((skill / "SKILL.md").read_text(encoding="utf-8")).get(
                "description", ""
            )
        except (OSError, FrontmatterError, UnicodeDecodeError):
            continue  # the validator reports a malformed skill; this is not its job
        for plugin in plugins:
            if skill.is_relative_to(plugin):
                # Whitespace is collapsed because a folded description carries newlines
                # the runtime never sees.
                entries.append(
                    (plugin.name, skill.name, len(" ".join((description or "").split())))
                )
                break
    return entries


def totals(root: Path, entries: list[tuple[str, str, int]]) -> dict[str, int]:
    """Sum a walk() into characters per plugin, including plugins that ship no skill."""
    sizes = {plugin.name: 0 for plugin in find_plugins(root)}
    for plugin, _skill, length in entries:
        sizes[plugin] += length
    return sizes


def measure(root: Path) -> dict[str, int]:
    """Characters of description each plugin puts into the listing, by plugin name."""
    return totals(root, walk(root))


def mute(entries: list[tuple[str, str, int]], plugin: str, budget: int = RUNTIME_DEFAULT) -> int:
    """How many of one plugin's skills lose their description, installed on their own.

    The character total says a plugin is over the budget; this says what that costs, in
    the unit the reader cares about. Past the budget the runtime drops whole descriptions
    rather than truncating them, so the skill stays invocable by name and stops being
    chosen on its own — a skill nobody can reach without already knowing it exists.

    Which particular skills go is not knowable here: the runtime drops the least-used,
    and on a fresh install nothing has been used. The count does depend on that order —
    dropping five short descriptions frees less room than dropping five long ones — so
    this packs the shortest first, which keeps the most and therefore reports the
    smallest honest number. Read it as "at least this many", not as the expected loss.
    """
    lengths = sorted(length for name, _skill, length in entries if name == plugin)
    used, kept = 0, 0
    for length in lengths:
        if used + length > budget:
            break
        used += length
        kept += 1
    return len(lengths) - kept


def ceiling_for(size: int) -> int:
    """The ceiling a measured total earns: rounded up to the next step, and at least
    HEADROOM above the total itself so a plugin sitting just under a boundary still has
    room to reword."""
    rounded = max(GRANULARITY, math.ceil(size / GRANULARITY) * GRANULARITY)
    while rounded - size < HEADROOM:
        rounded += GRANULARITY
    return rounded


def load(path: Path) -> Recorded:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), dict) for key in ("plugins", "skills")
    ):
        raise ValueError(
            f"{path.name} must be an object with 'plugins' and 'skills' objects in it; "
            "run --update to regenerate it"
        )
    return Recorded(
        {str(name): int(value) for name, value in data["plugins"].items()},
        {str(name): int(value) for name, value in data["skills"].items()},
    )


def write(path: Path, sizes: dict[str, int], lengths: dict[str, int] | None = None) -> None:
    body = {
        "_comment": (
            "Per-plugin ceilings for the skill listing, in characters, and the recorded "
            "length of each skill's description. Regenerate with "
            "scripts/check_listing_budget.py --update, and say in the commit why a "
            "ceiling or a length went up. The runtime default below is characters "
            f"standing in for tokens: this library measures {CHARS_PER_TOKEN} characters "
            f"per token, so {RUNTIME_DEFAULT:,} is about "
            f"{RUNTIME_DEFAULT / CHARS_PER_TOKEN:,.0f} "
            f"tokens against the {CONTEXT_WINDOW_TOKENS // 100:,} that one per cent of a "
            f"{CONTEXT_WINDOW_TOKENS // 1000}k window allows. A skill under 'skills' may "
            "not grow past the length recorded there; one that is absent is new and has "
            f"to come in at or under {DESCRIPTION_TARGET:,} characters."
        ),
        "runtime_default": RUNTIME_DEFAULT,
        "description_target": DESCRIPTION_TARGET,
        "plugins": {name: ceiling_for(sizes[name]) for name in sorted(sizes)},
        "skills": {name: (lengths or {})[name] for name in sorted(lengths or {})},
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def report_skills(lengths: dict[str, int], recorded: dict[str, int]) -> bool:
    """Gate each description against its record, print the summary, and say if it failed.

    A skill with no record is new: the target applies to it. A skill with one is
    grandfathered at whatever it measured when the record was written, and may shrink
    but not grow. A record with no skill is drift of the same kind a stale plugin entry
    is, and worse in one way: it would silently grandfather an over-length description
    added later under the same name.
    """
    failed = False
    for name in sorted(set(recorded) - set(lengths)):
        print(
            f"::error::{BUDGET_FILE} records a skill named {name}, "
            "which does not exist; run --update"
        )
        failed = True

    grandfathered = []
    for name in sorted(lengths):
        length, limit = lengths[name], recorded.get(name)
        if limit is None:
            if length > DESCRIPTION_TARGET:
                print(
                    f"::error::{name} is new and its description is {length:,} characters "
                    f"against a target of {DESCRIPTION_TARGET:,}; trim the description, or "
                    "record the length deliberately with --update and say why in the commit"
                )
                failed = True
        elif length > max(limit, DESCRIPTION_TARGET):
            # The record is a floor of DESCRIPTION_TARGET, not a hard ceiling. A skill
            # recorded under the target may be reworded freely up to it, the way the
            # per-plugin ceilings above carry slack so that rewording stays free. Only a
            # grandfathered description — one already over the target — is pinned where
            # it is, because that is the growth this ratchet exists to stop.
            print(
                f"::error::{name} description is {length:,} characters against a limit of "
                f"{max(limit, DESCRIPTION_TARGET):,}; trim the description, or raise the "
                "recorded length with --update and say why in the commit"
            )
            failed = True
        elif limit > DESCRIPTION_TARGET:
            grandfathered.append(name)

    note = ""
    if grandfathered:
        longest = max(grandfathered, key=lambda name: recorded[name])
        note = (
            f", {len(grandfathered)} grandfathered above it "
            f"(longest {longest} at {recorded[longest]:,})"
        )
    print(
        f"\n{len(lengths)} skill description(s) against the "
        f"{DESCRIPTION_TARGET:,}-character target{note}"
    )
    return failed


def check(root: Path, update: bool = False) -> int:
    path = root / BUDGET_FILE
    entries = walk(root)
    sizes = totals(root, entries)
    lengths = {skill: length for _plugin, skill, length in entries}
    if not sizes:
        print(f"no plugins found under {root}", file=sys.stderr)
        return 2

    if update:
        write(path, sizes, lengths)
        print(f"wrote {BUDGET_FILE} for {len(sizes)} plugin(s) and {len(lengths)} skill(s)")
        return 0

    if not path.is_file():
        print(f"{BUDGET_FILE} is missing; create it with --update", file=sys.stderr)
        return 1
    try:
        recorded = load(path)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"{BUDGET_FILE}: {error}", file=sys.stderr)
        return 1

    ceilings = recorded.plugins
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
        # Not a failure, and not harmless either. An earlier version of this comment said
        # someone who installs one plugin is unaffected; that is not true of a plugin
        # over the budget on its own, and the count below is what it costs them.
        print(
            f"above the ~{RUNTIME_DEFAULT:,} runtime default on their own: "
            f"{', '.join(over_runtime)}"
        )
        for name in over_runtime:
            tokens = sizes[name] / CHARS_PER_TOKEN
            silent = mute(entries, name)
            print(
                f"  {name}: about {tokens:,.0f} tokens, "
                f"{tokens / CONTEXT_WINDOW_TOKENS:.2%} of a "
                f"{CONTEXT_WINDOW_TOKENS // 1000}k window; installed alone, at least "
                f"{silent} of its skills lose their description entirely"
            )
        together = sum(sizes.values())
        needed = together / CHARS_PER_TOKEN / CONTEXT_WINDOW_TOKENS
        print(
            f"  all {len(sizes)} installed together: {together:,} characters against the "
            f"~{RUNTIME_DEFAULT:,} budget, so most descriptions are dropped and most "
            f"skills can only be reached by name"
        )
        print(
            f"  keeping every description at that size needs "
            f"skillListingBudgetFraction {needed:.3f}"
        )

    # Both files that tell a reader to raise `skillListingBudgetFraction` name a
    # number, and that number is a claim about this library's size, so it goes stale
    # the way any recorded measurement does: the README said 0.04 while the listing
    # needed 0.075, which covers a little over half and leaves the reader believing
    # they have fixed the problem. Checked here rather than in check_readme.py
    # because the measurement lives here, and two measurements of one thing
    # eventually disagree.
    needed = total / CHARS_PER_TOKEN / CONTEXT_WINDOW_TOKENS
    for advice in ADVICE_FILES:
        path = root / advice
        if not path.is_file():
            continue
        match = FRACTION_RE.search(path.read_text(encoding="utf-8"))
        if match is None:
            print(
                f"::error file={advice}::{advice} no longer names "
                f"skillListingBudgetFraction, so the install advice cannot be checked "
                f"against the listing it describes"
            )
            failed = True
            continue
        covers = float(match.group(1)) * CONTEXT_WINDOW_TOKENS * CHARS_PER_TOKEN
        if covers < total:
            print(
                f"::error file={advice}::the install advice recommends "
                f"skillListingBudgetFraction {match.group(1)}, which covers "
                f"{covers / total:.0%} of the {total:,} characters this marketplace "
                f"ships; it needs at least {needed:.3f}"
            )
            failed = True

    # Last, because it is the finer grain: the plugin block above is the one a reader
    # comes here for, and this says which single description moved.
    failed = report_skills(lengths, recorded.skills) or failed
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
