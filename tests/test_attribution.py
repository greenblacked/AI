"""The check that a change carries no trace of the tool that wrote it.

Every literal in this file that a naive text search for a coding-assistant name would
find is built from two fragments joined at runtime, exactly as `check_attribution.py`
itself is written — a test suite proving a detector works is a strange place for the
detector's target text to sit whole.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

from tests.conftest import load_script

attribution = load_script("check_attribution.py")

# The six tool names and the phrases built around them, assembled here the same way the
# script under test assembles them, and nowhere written out whole.
CLAUDE = "cla" + "ude"
CODEX = "cod" + "ex"
COPILOT = "cop" + "ilot"
GENERATED = "gener" + "ated"
SESSION_DOMAIN = "clau" + "de.ai"
SESSION_PATH = "cod" + "e"


def git(repo, *args, env=None):
    result = subprocess.run(  # noqa: S603 - fixed argv, test fixture only
        ["git", *args],  # noqa: S607 - resolved against PATH like every other git call here
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result


@pytest.fixture
def repo(tmp_path):
    directory = tmp_path / "repo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Test User")
    git(directory, "config", "user.email", "test@example.com")
    git(directory, "commit", "-q", "--allow-empty", "-m", "initial")
    git(directory, "tag", "base")
    return directory


def commit(repo, message, *, author=None, committer=None):
    """One empty commit carrying `message`, written through -F so nothing about the
    message ever appears as a literal argument on a command line."""
    path = repo / "message.txt"
    path.write_text(message, encoding="utf-8")
    env = os.environ.copy()
    if author:
        env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = author
    if committer:
        env["GIT_COMMITTER_NAME"], env["GIT_COMMITTER_EMAIL"] = committer
    git(repo, "commit", "-q", "--allow-empty", "-F", str(path), env=env)
    path.unlink()


# --- a clean range ------------------------------------------------------------------


def test_a_clean_range_passes(repo, capsys):
    commit(repo, "an ordinary change")
    assert attribution.check(repo, "base..HEAD") == 0
    assert "carry no tool attribution" in capsys.readouterr().out


def test_an_empty_range_passes(repo, capsys):
    # No new commits at all is not a defect; there is nothing to have attributed wrong.
    assert attribution.check(repo, "base..HEAD") == 0
    assert "0 commit(s)" in capsys.readouterr().out


# --- each flagged pattern ------------------------------------------------------------


def test_a_co_authored_by_trailer_naming_a_tool_fails(repo, capsys):
    commit(repo, f"add a feature\n\nCo-authored-by: {CLAUDE.title()} <noreply@anthropic.com>\n")
    assert attribution.check(repo, "base..HEAD") == 1
    out = capsys.readouterr().out
    assert "Co-authored-by trailer names a coding tool" in out
    assert CLAUDE.title() in out


def test_a_human_co_authored_by_passes(repo, capsys):
    commit(repo, "add a feature\n\nCo-authored-by: greenblacked <greenblacked@example.com>\n")
    assert attribution.check(repo, "base..HEAD") == 0
    assert "carry no tool attribution" in capsys.readouterr().out


def test_a_generated_with_footer_fails(repo, capsys):
    commit(repo, f"add a feature\n\n{GENERATED.title()} with {CLAUDE.title()} Code\n")
    assert attribution.check(repo, "base..HEAD") == 1
    assert "generated-with/by footer" in capsys.readouterr().out


def test_a_generated_by_footer_fails(repo, capsys):
    commit(repo, f"add a feature\n\n{GENERATED.title()} by {CODEX.title()}\n")
    assert attribution.check(repo, "base..HEAD") == 1
    assert "generated-with/by footer" in capsys.readouterr().out


def test_attribution_in_the_commit_subject_line_is_caught(repo, capsys):
    # `commits_in` reads `%B`, the whole message including its subject line. Every other
    # fixture here puts the attribution after a blank line, in the body, which would not
    # have noticed a change to `%b` (body only, subject dropped) — this one only has a
    # subject line, so it is the one that would catch that mutation.
    commit(repo, f"{GENERATED.title()} with {CLAUDE.title()} Code")
    assert attribution.check(repo, "base..HEAD") == 1
    assert "generated-with/by footer" in capsys.readouterr().out


def test_an_assistant_session_url_fails(repo, capsys):
    url = f"https://{SESSION_DOMAIN}/{SESSION_PATH}/session-abc123"
    commit(repo, f"add a feature\n\nSee {url}\n")
    assert attribution.check(repo, "base..HEAD") == 1
    assert "assistant session link" in capsys.readouterr().out


def test_the_bare_session_footer_link_fails(repo, capsys):
    url = f"https://{SESSION_DOMAIN}/{SESSION_PATH}"
    commit(repo, f"add a feature\n\n{GENERATED.title()} with [{CLAUDE.title()} Code]({url})\n")
    out_check = attribution.check(repo, "base..HEAD")
    assert out_check == 1


def test_a_tool_session_trailer_fails(repo, capsys):
    commit(repo, f"add a feature\n\n{CODEX.title()}-Session: abc123\n")
    assert attribution.check(repo, "base..HEAD") == 1
    assert "tool session trailer" in capsys.readouterr().out


def test_an_author_naming_a_tool_fails(repo, capsys):
    commit(
        repo,
        "add a feature",
        author=(CLAUDE.title(), "noreply@anthropic.com"),
    )
    assert attribution.check(repo, "base..HEAD") == 1
    out = capsys.readouterr().out
    assert "author" in out and "names a coding tool" in out


def test_a_committer_naming_a_tool_fails(repo, capsys):
    commit(
        repo,
        "add a feature",
        committer=(COPILOT.title(), "copilot@example.com"),
    )
    assert attribution.check(repo, "base..HEAD") == 1
    out = capsys.readouterr().out
    assert "committer" in out and "names a coding tool" in out


# --- the bot allowlist -----------------------------------------------------------
#
# None of the three names below contain any of the six tool names, so `check` would
# accept them today even without `_ALLOWED_IDENTITY_NAMES` — TOOL_RE simply never
# matches "dependabot[bot]", "github-actions[bot]" or "GitHub". The tests immediately
# below show the identity is accepted; they do not show the allowlist is why, because
# nothing currently forces it to be. `test_the_bot_allowlist_holds_even_if_tool_re_widens`
# further down is the one that isolates the allowlist itself, by widening the pattern it
# is meant to guard against and checking the identity still passes.


def test_dependabot_bot_identity_passes(repo, capsys):
    identity = ("dependabot[bot]", "dependabot[bot]@users.noreply.github.com")
    commit(repo, "bump a dependency", author=identity, committer=identity)
    assert attribution.check(repo, "base..HEAD") == 0
    assert "carry no tool attribution" in capsys.readouterr().out


def test_github_actions_bot_identity_passes(repo, capsys):
    identity = ("github-actions[bot]", "github-actions[bot]@users.noreply.github.com")
    commit(repo, "automated commit", author=identity, committer=identity)
    assert attribution.check(repo, "base..HEAD") == 0
    assert "carry no tool attribution" in capsys.readouterr().out


def test_the_github_committer_identity_passes(repo, capsys):
    # The identity a squash merge made through the API carries as committer.
    commit(
        repo,
        "add a feature",
        committer=("GitHub", "noreply@github.com"),
    )
    assert attribution.check(repo, "base..HEAD") == 0
    assert "carry no tool attribution" in capsys.readouterr().out


def test_a_committer_named_github_with_a_different_email_is_still_checked(repo, capsys):
    # The allowance is for the exact identity GitHub's API uses, not for the display
    # name alone — otherwise anyone could claim it.
    commit(
        repo,
        "add a feature",
        committer=("GitHub", CLAUDE + "@example.com"),
    )
    assert attribution.check(repo, "base..HEAD") == 1


def test_the_bot_allowlist_holds_even_if_tool_re_widens(monkeypatch):
    # The allowlist check runs first and returns before `TOOL_RE` is ever consulted, so
    # it stays a real guard even against a pattern change that would otherwise have
    # caught these names. Widening TOOL_RE to something that plainly matches "bot" is
    # what makes that isolation visible: without the allowlist short-circuit, both
    # identities below would now read as naming a coding tool.
    monkeypatch.setattr(attribution, "TOOL_RE", re.compile(r"bot", re.IGNORECASE))
    assert attribution.TOOL_RE.search("dependabot[bot]") is not None  # the widened pattern
    assert attribution.identity_problem("author", "dependabot[bot]", "x@example.com") is None
    assert attribution.identity_problem("author", "github-actions[bot]", "x@example.com") is None


# --- branch names ------------------------------------------------------------------
#
# None of `_BRANCH_PREFIXES` below currently matches "dependabot/" either, so this next
# test shows the branch is accepted without yet showing the allowance is why.
# `test_the_dependabot_branch_allowance_holds_even_if_prefixes_widen`, after the other
# branch tests, is the one that isolates it.


def test_a_dependabot_branch_passes():
    assert attribution.branch_problem("dependabot/pip/foo-1.2.3") is None


@pytest.mark.parametrize(
    "branch",
    [CLAUDE + "/fix-thing", CODEX + "/fix-thing", COPILOT + "/fix-thing", "ai/fix", "bot/fix"],
)
def test_a_tool_named_branch_fails(branch):
    problem = attribution.branch_problem(branch)
    assert problem is not None
    assert branch in problem


def test_an_ordinary_branch_passes():
    assert attribution.branch_problem("ci/dependabot-auto-merge-and-attribution") is None


def test_no_branch_is_not_a_finding():
    assert attribution.branch_problem(None) is None
    assert attribution.branch_problem("") is None


def test_a_tool_named_branch_fails_the_whole_check(repo, capsys):
    commit(repo, "add a feature")
    assert attribution.check(repo, "base..HEAD", branch=f"{CLAUDE}/some-change") == 1
    assert "tool-named prefix" in capsys.readouterr().out


def test_a_dependabot_branch_passes_the_whole_check(repo, capsys):
    commit(repo, "bump a dependency")
    assert attribution.check(repo, "base..HEAD", branch="dependabot/pip/foo-1.2.3") == 0


def test_the_dependabot_branch_allowance_holds_even_if_prefixes_widen(monkeypatch):
    # `_ALLOWED_BRANCH_PREFIX` is checked before the loop over `_BRANCH_PREFIXES`, so it
    # stays a real exemption even against a prefix that would otherwise have caught this
    # branch. "depend" is that prefix: without the allowance short-circuiting first,
    # "dependabot/pip/foo" would now read as tool-named.
    monkeypatch.setattr(attribution, "_BRANCH_PREFIXES", ("depend",))
    assert "dependabot/pip/foo".startswith("depend")  # the widened prefix would now match
    assert attribution.branch_problem("dependabot/pip/foo") is None


# --- the pull request title and body ------------------------------------------------


def test_a_pull_request_body_footer_fails(repo, capsys):
    body = f"Some description of the change.\n\n{GENERATED.title()} with {CLAUDE.title()} Code\n"
    assert attribution.check(repo, "base..HEAD", pr_body=body) == 1
    out = capsys.readouterr().out
    assert "pull request body" in out
    assert "generated-with/by footer" in out


def test_a_pull_request_title_footer_fails(repo, capsys):
    title = f"{GENERATED.title()} with {CODEX.title()}: add a feature"
    assert attribution.check(repo, "base..HEAD", pr_title=title) == 1
    assert "pull request title" in capsys.readouterr().out


def test_an_ordinary_pull_request_title_and_body_pass(repo, capsys):
    assert (
        attribution.check(
            repo,
            "base..HEAD",
            pr_title="Add a feature",
            pr_body="Description of the change and why it matters.",
        )
        == 0
    )
    assert "carry no tool attribution" in capsys.readouterr().out


def test_no_pull_request_text_is_not_a_finding(repo):
    assert attribution.check(repo, "base..HEAD") == 0


# --- scan_text directly, including both findings on one line ------------------------


def test_scan_text_finds_nothing_in_empty_text():
    assert attribution.scan_text("source", "") == []
    assert attribution.scan_text("source", None) == []


def test_scan_text_reports_two_problems_on_one_line():
    url = f"https://{SESSION_DOMAIN}/{SESSION_PATH}"
    line = f"{GENERATED.title()} with [{CLAUDE.title()} Code]({url})"
    problems = attribution.scan_text("commit abc123", line)
    assert len(problems) == 2
    assert any("generated-with/by footer" in p for p in problems)
    assert any("assistant session link" in p for p in problems)


def test_scan_text_ignores_a_generated_line_with_no_tool_reference():
    # Narrowed after two measured false positives: this repository's own history has
    # "...block_scalars.json now, generated by a" (commit ec44c2d), and a real pull
    # request's body reads "generated by terraform-docs" — ordinary engineering prose,
    # not attribution. "generated by/with" only counts when one of the six tool names
    # follows it on the same line.
    assert (
        attribution.scan_text(
            "commit abc123", "This file was generated by terraform-docs; do not edit by hand."
        )
        == []
    )
    assert attribution.scan_text("commit abc123", "recording is generated by a script") == []


def test_scan_text_still_flags_generated_with_a_tool_name():
    problems = attribution.scan_text(
        "commit abc123", f"{GENERATED.title()} with {CLAUDE.title()} Code"
    )
    assert any("generated-with/by footer" in p for p in problems)


# --- identity_problem and TOOL_RE directly ------------------------------------------


def test_identity_problem_passes_an_ordinary_person():
    assert attribution.identity_problem("author", "Test User", "test@example.com") is None


def test_identity_problem_is_case_insensitive_in_the_tool_name():
    problem = attribution.identity_problem("author", CLAUDE.upper(), "noreply@anthropic.com")
    assert problem is not None


# --- git plumbing and error handling -------------------------------------------------


def test_git_binary_resolves_to_an_absolute_path():
    path = attribution.git_binary()
    assert path is not None
    assert os.path.isabs(path)


def test_git_binary_is_none_when_git_is_not_on_path(monkeypatch):
    monkeypatch.setattr(attribution.shutil, "which", lambda name: None)
    assert attribution.git_binary() is None


def test_check_reports_rather_than_raises_when_git_is_missing(repo, monkeypatch, capsys):
    monkeypatch.setattr(attribution, "git_binary", lambda: None)
    assert attribution.check(repo, "base..HEAD") == 2
    assert "git is not on PATH" in capsys.readouterr().err


def test_check_reports_an_unreadable_range_rather_than_raising(repo, capsys):
    assert attribution.check(repo, "not-a-real-ref..HEAD") == 2
    assert "could not read commits in range" in capsys.readouterr().out


def test_commits_in_skips_a_record_with_the_wrong_field_count(repo, monkeypatch):
    git_path = attribution.git_binary()

    class FakeResult:
        returncode = 0
        stdout = "only-one-field\x1e\n"
        stderr = ""

    monkeypatch.setattr(
        attribution.subprocess,
        "run",
        lambda *a, **k: FakeResult(),  # noqa: ARG005
    )
    assert attribution.commits_in(repo, "base..HEAD", git_path) == []


def test_commits_in_raises_on_a_nonzero_exit(repo):
    git_path = attribution.git_binary()
    with pytest.raises(ValueError, match="failed|not-a-ref"):
        attribution.commits_in(repo, "not-a-ref..HEAD", git_path)


# --- main() and its environment ------------------------------------------------------


def test_main_reads_the_range_flag(repo):
    assert attribution.main([str(repo), "--range", "base..HEAD"]) == 0


def test_main_reads_pull_request_and_branch_context_from_the_environment(repo, monkeypatch):
    monkeypatch.setenv("GITHUB_HEAD_REF", f"{CLAUDE}/change")
    monkeypatch.setenv("PR_TITLE", "Add a feature")
    monkeypatch.setenv("PR_BODY", "")
    assert attribution.main([str(repo), "--range", "base..HEAD"]) == 1


def test_main_with_clean_environment_passes(repo, monkeypatch):
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.delenv("PR_TITLE", raising=False)
    monkeypatch.delenv("PR_BODY", raising=False)
    assert attribution.main([str(repo), "--range", "base..HEAD"]) == 0


def test_main_defaults_the_range_to_origin_main_head(repo, monkeypatch):
    captured = {}

    def fake_check(root, commit_range, **kwargs):
        captured["range"] = commit_range
        return 0

    monkeypatch.setattr(attribution, "check", fake_check)
    assert attribution.main([str(repo)]) == 0
    assert captured["range"] == "origin/main..HEAD"
