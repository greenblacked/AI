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
    # instructions in any session opened there. Codex prefers `AGENTS.override.md` over
    # `AGENTS.md` in the same directory (openai/codex, codex-rs/core/src/agents_md.rs), so
    # that name is an instruction file too, and so is any name its user lists in
    # `project_doc_fallback_filenames`, which the loader reads after `AGENTS.md`.
    text = flat(path)
    assert anchor in text, (path, anchor)
    clause = text.split(anchor, 1)[1][:260]
    for name in (
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "AGENTS.override.md",
        "project_doc_fallback_filenames",
        ".claude/",
    ):
        assert name in clause, (path, name, clause)


def test_a_contributor_instruction_file_is_a_blocking_finding():
    text = flat(".claude/agents/reviewer.md")
    assert re.search(
        r"adds, edits or deletes an instruction file .{0,230}is a blocking finding", text
    )


def test_the_blocking_rule_names_every_instruction_file():
    # The blocking rule has its own list, separate from the inert allowlist's, and a name
    # missing from it lets that file through as an ordinary change.
    text = flat(".claude/agents/reviewer.md")
    clause = text.split("adds, edits or deletes an instruction file", 1)[1][:240]
    for name in (
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "AGENTS.override.md",
        "project_doc_fallback_filenames",
        ".claude/",
    ):
        assert name in clause, (name, clause)


def test_the_blocking_rule_covers_deleting_or_renaming_away_an_instruction_file():
    # Removing a trusted instruction file changes what a session is told as surely as
    # adding one. `--no-renames` shows a rename as a deletion plus an addition, so a
    # rename whose source is an instruction path is a deletion of it.
    text = flat(".claude/agents/reviewer.md")
    clause = text.split("adds, edits or deletes an instruction file", 1)[1][:380]
    assert "rename" in clause and "--no-renames" in clause and "deletion" in clause, clause


@pytest.mark.parametrize(
    ("path", "occurrences"), [("docs/chatgpt-agents.md", 2), ("docs/using.md", 1)]
)
def test_the_restated_blocking_rule_covers_deletion_and_renames(path, occurrences):
    # chatgpt-agents.md states the rule twice, in the long-form section and again in the
    # standalone reviewer role card, which is pasted on its own; every restatement has to
    # carry the deletion and rename clauses, not only the first one a split finds.
    text = flat(path)
    marker = "is a blocking finding on a contributor change"
    assert text.count(marker) == occurrences, (path, text.count(marker))
    for part in text.split(marker)[1:]:
        clause = part[:140]
        assert "adds, edits or deletes it" in clause and "rename" in clause, (path, clause)


def test_the_reviewer_role_card_states_the_blocking_rule_itself():
    # The role card's own inert-paths list excludes instruction files; without the rule
    # beside it, a card read alone falls back to the owner-must-run flow for them.
    text = flat("docs/chatgpt-agents.md")
    anchor = "and no gate runs): a *.md file under plugins/ or docs/"
    assert anchor in text
    clause = text.split(anchor, 1)[1][:450]
    rule = "is a blocking finding on a contributor change that adds, edits or deletes it"
    assert rule in clause and "a rename counts through its deleted source path" in clause, clause


@pytest.mark.parametrize(
    ("path", "occurrences"),
    [
        (".claude/agents/reviewer.md", 1),
        ("docs/chatgpt-agents.md", 2),
        ("docs/using.md", 1),
    ],
)
def test_dot_prefixed_claude_paths_are_blocking_not_owner_must_run(path, occurrences):
    # `.claude/` is canonical, so never a rename finding, but it is instruction
    # configuration and blocks; only other dot-prefixed paths such as `.github/` are
    # non-inert and go to the owner-must-run flow.
    text = flat(path).replace("`", "")
    assert "canonical but non-inert" not in text, path
    parts = re.split(r"[Dd]ot-prefixed paths", text)[1:]
    assert len(parts) == occurrences, (path, len(parts))
    for part in parts:
        clause = part[:260]
        assert re.search(
            r"\.claude/ path is a blocking finding as instruction configuration, and any"
            r" other, such as \.github/, is non-inert and goes to the owner-must-run flow",
            clause,
        ), (path, clause)


# The setting's name is not its values: `project_doc_fallback_filenames` is configured in the
# reviewing user's own Codex configuration, outside this repository, so the trusted caller has
# to state the resolved list (`[]` when empty) and the reviewer stops rather than assume it empty.
FALLBACK_SENTENCE = (
    "The fallback names are the list the owner resolved from their trusted Codex"
    " configuration and states in the"
)


@pytest.mark.parametrize(
    ("path", "occurrences"),
    [
        (".claude/agents/reviewer.md", 2),
        ("docs/chatgpt-agents.md", 2),
        ("docs/using.md", 1),
    ],
)
def test_each_statement_of_the_rule_requires_the_caller_supplied_fallback_list(path, occurrences):
    # Five statements restate the instruction-file rule (the gates paragraph and the
    # blocking rule in reviewer.md, the long form and the role card in chatgpt-agents.md,
    # using.md); each has to carry the whole requirement, since the role card is pasted alone.
    text = flat(path).replace("`", "")
    assert text.count(FALLBACK_SENTENCE) == occurrences, (path, text.count(FALLBACK_SENTENCE))
    for part in text.split(FALLBACK_SENTENCE)[1:]:
        clause = part[:520]
        assert re.match(r" (?:brief|packet) as a list, \[\] when empty;", clause), (path, clause)
        for needle in (
            "whose basename matches one, at any depth, is an instruction file",
            "a config file in the diff is never a source for the list",
            "states no list is not an empty one",
            "STOP, asking the caller for it before any Markdown path is classified as inert",
        ):
            assert needle in clause, (path, needle, clause)


# Codex and Claude Code open an instruction file by name and trust the filesystem, so on a
# case-insensitive one (default macOS and Windows) `docs/team_guide.md` loads where
# `TEAM_GUIDE.md` is configured and `claude.md` loads as `CLAUDE.md`. The reviewer cannot know
# the reader's filesystem, so every name comparison is case-insensitive, fixed names included.
CASE_SENTENCE = (
    "Instruction-file names, and a .claude/ segment, compare case-insensitively,"
    " the fixed names and the fallback names alike, on any filesystem:"
    " a case-insensitive checkout loads claude.md or .Claude/,"
    " or docs/team_guide.md where TEAM_GUIDE.md is configured, as an instruction file."
)


@pytest.mark.parametrize(
    ("path", "occurrences"),
    [
        (".claude/agents/reviewer.md", 2),
        ("docs/chatgpt-agents.md", 2),
        ("docs/using.md", 1),
    ],
)
def test_each_statement_of_the_rule_compares_names_case_insensitively(path, occurrences):
    # Same five statements as above; a statement that omits the clause reads a changed
    # `docs/team_guide.md` as inert prose on a checkout that loads it as instructions.
    text = flat(path).replace("`", "")
    assert text.count(CASE_SENTENCE) == occurrences, (path, text.count(CASE_SENTENCE))
    # The clause sits directly before the fallback-list sentence, inside the same statement.
    assert text.count(CASE_SENTENCE + " " + FALLBACK_SENTENCE) == occurrences, path


@pytest.mark.parametrize("path", CONTRACT_FILES)
def test_no_statement_matches_instruction_file_names_by_exact_case(path):
    # Negative check: an "exact" or "case-sensitive" basename match is the defect itself.
    text = flat(path).replace("`", "")
    assert not re.search(r"\bcase-sensitiv", text, re.IGNORECASE), path
    assert not re.search(r"\b(?:exact|exactly)[- ](?:case|basename|name)", text, re.IGNORECASE), (
        path
    )


@pytest.mark.parametrize(
    ("path", "anchor"),
    [
        (".claude/agents/reviewer.md", "file under plugins/ or docs/"),
        (".claude/agents/reviewer.md", "adds, edits or deletes an instruction file"),
        ("docs/chatgpt-agents.md", "The inert paths are: a *.md file under plugins/ or docs/"),
        ("docs/chatgpt-agents.md", "and no gate runs): a *.md file under plugins/ or docs/"),
        ("docs/using.md", "(Markdown under plugins/ or docs/"),
    ],
)
def test_the_fallback_clause_in_each_list_names_the_caller_as_the_source(path, anchor):
    # The inline clause sits in the instruction-file list itself, so a reader who stops at the
    # list still sees that the names come from the caller and not from the setting's key.
    text = flat(path).replace("`", "")
    assert anchor in text, (path, anchor)
    clause = text.split(anchor, 1)[1][:320]
    assert re.search(
        r"project_doc_fallback_filenames lists, as the caller's (?:brief|packet) states them",
        clause,
    ), (path, clause)


@pytest.mark.parametrize(
    ("path", "needle"),
    [
        (".claude/agents/reviewer.md", "- **Fallback names** — for a contributor change"),
        (
            ".claude/agents/reviewer.md",
            "Also require the caller's fallback names, stated as a list",
        ),
        ("docs/chatgpt-agents.md", "- Fallback names, for a contributor change:"),
        ("docs/chatgpt-agents.md", "Fallback names (contributor only):"),
        (
            "docs/chatgpt-agents.md",
            "the candidate ref and the fallback names (a list, [] when empty) instead",
        ),
        ("docs/using.md", "the pinned `<base>`, the fallback names ("),
        ("docs/using.md", "and the fallback names;"),
        (".claude/commands/ship.md", "the pinned `<base>`, the fallback names ("),
        (
            ".claude/commands/ship.md",
            "the pinned `<base>`, the fallback names and the candidate ref",
        ),
        (".claude/commands/verify.md", "the pinned `<base>`, the fallback names ("),
        (
            ".claude/commands/verify.md",
            "the pinned `<base>`, the fallback names and the candidate ref",
        ),
    ],
)
def test_wherever_the_caller_lists_what_it_passes_the_fallback_names_are_listed(path, needle):
    assert needle in flat(path), (path, needle)


def test_the_reviewers_fallback_input_says_where_the_list_comes_from_and_stops_without_it():
    text = flat(".claude/agents/reviewer.md")
    bullet = text.split("**Fallback names**", 1)[1][:700]
    for needle in (
        "trusted Codex configuration",
        "stated as a list in the configuration's own form",
        "with `[]` for no fallback names",
        "neither the diff nor the contributor's branch can supply them",
        "not an empty one",
    ):
        assert needle in bullet, (needle, bullet)
    stop = text.split("Also require the caller's fallback names", 1)[1][:330]
    assert "`Verdict: STOP`" in stop and "never assumed empty" in stop, stop
    assert "never read from the candidate" in stop, stop
    assert "`[]` when empty" in stop, stop


@pytest.mark.parametrize("path", CONTRACT_FILES)
def test_no_statement_assumes_an_unstated_list_is_empty_or_reads_it_from_the_branch(path):
    # Negative check: the failure this guards is a reviewer that defaults to "no fallback
    # names" or takes them from the contributor's own config file in the diff.
    # It also forbids the word `none` as the empty list.
    text = flat(path).replace("`", "")
    assert not re.search(
        r"(?<!never )(?<!not )\b(?:defaults? to|assumed?|treated as|read as) (?:to be )?"
        r"(?:an? )?(?:none|empty)\b",
        text,
    ), path
    assert not re.search(r"fallback names? (?:from|in) the (?:diff|candidate|contributor)", text), (
        path
    )
    assert not re.search(r"(?:from|in) the contributor's (?:config|\.codex)", text), path
    # Codex accepts `none` as a fallback filename (its loader rejects only empty strings, `.`,
    # `..` and path separators), so the word cannot also mean "no fallbacks": a configuration
    # listing "none" would read as empty and a contributor's `docs/none` could be misclassified.
    # The empty list is `[]`, in the configuration's own form.
    sentinel = re.compile(
        r"(?:\bor|\bgiven as|\bstated as names or|\bthe word|\bwords?|\(or)\s+[\"“]?none\b[\"”]?",
        re.IGNORECASE,
    )
    for anchor in re.finditer(r"fallback[ _]name|fallback_filenames", text):
        window = text[anchor.start() : anchor.start() + 400]
        assert not sentinel.search(window), (path, window)


@pytest.mark.parametrize(
    "path", [".claude/commands/ship.md", ".claude/agents/reviewer.md", "CONTRIBUTING.md"]
)
def test_the_build_loop_branches_from_and_measures_against_dev(path):
    # Feature work lands on dev; main's first-parent history is promotions and release
    # preparation, so a branch cut from main misses everything dev has not promoted yet.
    text = flat(path)
    # CONTRIBUTING still names origin/main, as the base a promotion passes to
    # `make naming`; only the build loop's own base is checked there.
    if path != "CONTRIBUTING.md":
        assert "origin/main" not in text, path
    assert re.search(r"(?:origin/dev|[Bb]ranch from `dev`)", text), path


def test_ship_opens_and_merges_its_pull_request_into_dev():
    text = flat(".claude/commands/ship.md")
    assert "open the pull request into `dev`" in text
    assert "the merge into `dev`" in text


def test_the_reviewer_reads_the_candidate_by_one_resolved_sha():
    # A forced re-fetch of refs/review/<n> mid-review would move a ref-named read; the
    # pinned SHA cannot move.
    text = flat(".claude/agents/reviewer.md")
    assert "git rev-parse --verify 'refs/review/<n>^{commit}'" in text
    for verb in ("diff", "show", "ls-tree", "merge-base", "merge"):
        for command in re.findall(rf"git (?:-C \S+ )?(?:-c \S+ )*{verb}\b[^`\n]*", text):
            assert "refs/review/<n>" not in command or "rev-parse" in command, command


def test_ship_names_a_trusted_checkout_pinned_at_the_base():
    text = flat(".claude/commands/ship.md")
    assert "checked out exactly at `<base>`" in text
    assert "git worktree add --detach <dir> '<base>'" in text
