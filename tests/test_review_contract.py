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


@pytest.mark.parametrize(
    ("path", "anchor"),
    [
        (".claude/agents/reviewer.md", "file under `plugins/` or `docs/`"),
        ("docs/chatgpt-agents.md", "The inert paths are: a *.md file under plugins/ or docs/"),
        ("docs/chatgpt-agents.md", "and no gate runs): a *.md file under plugins/ or docs/"),
        ("docs/using.md", "(Markdown under `plugins/` or `docs/`"),
    ],
)
def test_the_inert_allowlist_excludes_instruction_files(path, anchor):
    # A contributor's nested `docs/CLAUDE.md` is Markdown under `docs/`, and loads as
    # instructions in any session opened there.
    text = flat(path)
    assert anchor in text, (path, anchor)
    clause = text.split(anchor, 1)[1][:260]
    for name in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude/"):
        assert name in clause, (path, name, clause)


def test_a_contributor_instruction_file_is_a_blocking_finding():
    text = flat(".claude/agents/reviewer.md")
    assert re.search(r"adds or edits an instruction file .{0,120}is a blocking finding", text)


@pytest.mark.parametrize(
    "path", [".claude/commands/ship.md", ".claude/agents/reviewer.md", "CONTRIBUTING.md"]
)
def test_the_build_loop_branches_from_and_measures_against_dev(path):
    # Feature work lands on dev; main's first-parent history is promotions and release
    # preparation, so a branch cut from main misses everything dev has not promoted yet.
    text = flat(path)
    # CONTRIBUTING still names origin/main for `make naming` and `make attribution`,
    # which diff against it; only the build loop's own base is checked there.
    if path != "CONTRIBUTING.md":
        assert "origin/main" not in text, path
    assert re.search(r"(?:origin/dev|[Bb]ranch from `dev`)", text), path


def test_ship_opens_and_merges_its_pull_request_into_dev():
    text = flat(".claude/commands/ship.md")
    assert "open the pull request into `dev`" in text
    assert "the merge into `dev`" in text
