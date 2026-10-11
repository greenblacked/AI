"""The contributor-review contract is prose spread over six files, and no gate executes it.

These cases pin the invariants a review has already found broken once, so a later edit
that reverts one fails here rather than waiting for the next review to notice. The
reviewer benchmark cannot carry them: it always briefs `reviewer` as the repository
owner, and every rule below is about a contributor's change.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import REPO

CONTRACT_FILES = (
    ".claude/agents/reviewer.md",
    ".claude/agents/investigator.md",
    ".claude/commands/ship.md",
    ".claude/commands/verify.md",
    "docs/chatgpt-agents.md",
    "docs/using.md",
)


def read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def flat(path: str) -> str:
    """The file with line breaks folded, so a command wrapped across lines still matches."""
    return re.sub(r"\s+", " ", read(path))


@pytest.mark.parametrize("path", CONTRACT_FILES)
def test_every_contributor_path_listing_turns_rename_detection_off(path):
    # With renames on, `git mv tests/test_a.py docs/test_a.md` lists only the new path,
    # which passes the inert allowlist while the test is gone.
    commands = re.findall(r"git diff(?: -[-\w]+)*", flat(path))
    listings = [c for c in commands if re.search(r" (?:-z|--name-only|--raw)\b", c)]
    assert listings, path
    for command in listings:
        assert "--no-renames" in command, (path, command)


def test_a_contributor_change_missing_its_live_check_is_fix_not_stop():
    text = flat(".claude/agents/reviewer.md")
    rule = text.split("only the absence of all three is `STOP`.", 1)[1][:600]
    assert "contributor" in rule and "owner-must-run" in rule and "`FIX`" in rule, rule
