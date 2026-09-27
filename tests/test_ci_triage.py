"""Tests for `scripts/ci_triage.py`, a port of status-page's `ci-triage.cjs`.

`FakeGitHub` plays the same role as `answers()` in `tests/test_workflows.py` and the
fake `claude` CLI in `conftest.py`: a table-driven stand-in for the network, so the
whole suite runs with no credential and no request ever leaving the machine. Unlike
those two it is stateful — a comment can be created and then edited, a label added
and then removed — because that is the shape the real API has here: `ci_triage.py`
reads and writes, it does not only read.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

from tests.conftest import load_script

ci_triage = load_script("ci_triage.py")
check_workflows = load_script("check_workflows.py")

REPO_ROOT = ci_triage.__file__.rsplit("/scripts/", 1)[0]

OWNER, REPO = "o", "r"
HEAD = "abc1234def0"
TOKEN = "tok"  # noqa: S105 - a fixture value, not a credential


class FakeGitHub:
    """A minimal, stateful stand-in for the four GitHub REST resources this script
    touches: pulls, actions runs/jobs, issue comments and issue labels."""

    def __init__(self):
        self.runs: list[dict] = []
        self.jobs: dict[int, list[dict]] = {}
        self.comments: list[dict] = []
        self.labels: list[str] = []
        self.pr_head = HEAD
        self.pr_state = "open"
        self.commit_prs: list[dict] = [{"number": 7, "state": "open"}]
        self.fork_prs: list[dict] = []

    def __call__(self, method: str, url: str, headers: dict, data: bytes | None):
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        parsed = urlparse(url)
        path = parsed.path
        body = json.loads(data) if data else None

        if re.match(rf"^/repos/{OWNER}/{REPO}/commits/[^/]+/pulls$", path):
            return 200, {}, json.dumps(self.commit_prs).encode()
        if path == f"/repos/{OWNER}/{REPO}/pulls":
            return 200, {}, json.dumps(self.fork_prs).encode()
        if path == f"/repos/{OWNER}/{REPO}/pulls/7":
            pr = {
                "number": 7,
                "state": self.pr_state,
                "head": {"sha": self.pr_head},
                "labels": [{"name": name} for name in self.labels],
            }
            return 200, {}, json.dumps(pr).encode()
        if path == f"/repos/{OWNER}/{REPO}/actions/runs":
            return 200, {}, json.dumps({"workflow_runs": self.runs}).encode()
        match = re.match(rf"^/repos/{OWNER}/{REPO}/actions/runs/(\d+)/jobs$", path)
        if match:
            run_id = int(match.group(1))
            return 200, {}, json.dumps({"jobs": self.jobs.get(run_id, [])}).encode()
        if path == f"/repos/{OWNER}/{REPO}/issues/7/comments":
            if method == "GET":
                return 200, {}, json.dumps(self.comments).encode()
            if method == "POST":
                comment = {
                    "id": len(self.comments) + 1,
                    "body": body["body"],
                    "user": {"type": "Bot", "login": "github-actions[bot]"},
                }
                self.comments.append(comment)
                return 201, {}, json.dumps(comment).encode()
        match = re.match(rf"^/repos/{OWNER}/{REPO}/issues/comments/(\d+)$", path)
        if match and method == "PATCH":
            comment_id = int(match.group(1))
            for comment in self.comments:
                if comment["id"] == comment_id:
                    comment["body"] = body["body"]
            return 200, {}, json.dumps({}).encode()
        if path == f"/repos/{OWNER}/{REPO}/issues/7/labels" and method == "POST":
            self.labels.extend(body["labels"])
            return 200, {}, json.dumps(self.labels).encode()
        match = re.match(rf"^/repos/{OWNER}/{REPO}/issues/7/labels/([^/]+)$", path)
        if match and method == "DELETE":
            name = match.group(1)
            if name in self.labels:
                self.labels.remove(name)
                return 204, {}, b""
            return 404, {}, b'{"message": "Not Found"}'
        raise AssertionError(f"unhandled {method} {url}")  # pragma: no cover


def green(run_id: int, name: str, run_number: int = 1) -> dict:
    return {
        "id": run_id,
        "name": name,
        "run_number": run_number,
        "status": "completed",
        "conclusion": "success",
        "html_url": f"https://gh/run/{run_id}",
    }


def make_trigger(**overrides) -> dict:
    base = {
        "head_sha": HEAD,
        "head_branch": "feature",
        "head_repository_owner": "someone",
        "pull_requests": [{"number": 7}],
    }
    base.update(overrides)
    return base


def run(fake: FakeGitHub, trigger: dict | None = None) -> str:
    return ci_triage.triage(fake, TOKEN, OWNER, REPO, trigger or make_trigger())


def test_stays_silent_on_a_pr_that_never_failed():
    fake = FakeGitHub()
    fake.runs = [green(1, "CI"), green(2, "Security")]
    assert run(fake).endswith(": green")
    assert fake.comments == []
    assert fake.labels == []


def test_reports_the_failing_job_step_and_cause_with_a_log_link_and_labels_the_pr():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}, green(2, "Security")]
    fake.jobs[1] = [
        {
            "name": "validate skills",
            "conclusion": "failure",
            "html_url": "https://gh/job/9",
            "steps": [
                {"name": "Checkout", "number": 1, "conclusion": "success"},
                {
                    "name": "Validate every skill, subagent and the marketplace manifest",
                    "number": 3,
                    "conclusion": "failure",
                },
            ],
        }
    ]
    result = run(fake)
    assert result == "#7: failing"
    assert len(fake.comments) == 1
    body = fake.comments[0]["body"]
    assert body.startswith(ci_triage.MARKER)
    assert "`validate skills`" in body
    assert "make validate" in body
    assert "https://gh/job/9#step:3:1" in body
    assert fake.labels == ["ci-failed"]


def test_edits_the_same_comment_on_recovery_and_removes_the_label():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}, green(2, "Security")]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [
                {
                    "name": "The README still describes what is in the repository",
                    "number": 2,
                    "conclusion": "failure",
                }
            ],
        }
    ]
    run(fake)
    fake.runs = [green(4, "CI", 2), green(2, "Security")]
    result = run(fake)
    assert result == "#7: green"
    assert len(fake.comments) == 1
    assert "Recovered" in fake.comments[0]["body"]
    assert fake.labels == []


def test_keeps_the_red_report_while_a_recovery_run_is_still_in_flight():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}, green(2, "Security")]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        }
    ]
    run(fake)
    fake.runs = [
        {**green(4, "CI", 2), "status": "in_progress", "conclusion": None},
        green(2, "Security"),
    ]
    result = run(fake)
    assert result == "#7: pending"
    assert "CI failing" in fake.comments[0]["body"]
    assert fake.labels == ["ci-failed"]


def test_a_stale_sha_is_ignored():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.pr_head = "newer0000000"
    result = run(fake)
    assert "has moved on" in result
    assert fake.comments == []
    assert fake.labels == []


def test_a_cancelled_run_is_not_a_failure():
    # cancelled says nothing about the code: it is neither a failure nor a pass, so
    # this run reports no verdict rather than declaring the PR either red or green.
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "cancelled"}]
    result = run(fake)
    assert not result.endswith(": failing")
    assert fake.comments == []
    assert fake.labels == []


def test_a_closed_pull_request_is_left_alone():
    fake = FakeGitHub()
    fake.pr_state = "closed"
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    result = run(fake)
    assert "is not open" in result
    assert fake.comments == []


def test_finds_a_fork_pull_request_by_head_branch():
    fake = FakeGitHub()
    fake.commit_prs = []
    fake.fork_prs = [{"number": 7}]
    fake.runs = [green(1, "CI"), green(2, "Security")]
    result = run(fake, make_trigger(pull_requests=[]))
    assert result == "#7: green"


def test_pagination_walks_a_link_header():
    fake = FakeGitHub()
    page_two = [{"id": 1, "body": "old", "user": {"type": "Bot"}}]

    real_call = fake.__call__

    def paged(method, url, headers, data):
        if url == f"https://api.github.com/repos/{OWNER}/{REPO}/issues/7/comments?per_page=100":
            next_url = f"https://api.github.com/repos/{OWNER}/{REPO}/issues/7/comments?page=2"
            return 200, {"Link": f'<{next_url}>; rel="next"'}, json.dumps([]).encode()
        if url == f"https://api.github.com/repos/{OWNER}/{REPO}/issues/7/comments?page=2":
            return 200, {}, json.dumps(page_two).encode()
        return real_call(method, url, headers, data)

    items = ci_triage.paginate(
        paged, TOKEN, f"/repos/{OWNER}/{REPO}/issues/7/comments?per_page=100"
    )
    assert items == page_two


# --- escaping: job and step names come from the PR head's workflow file ---


def test_backticks_and_newlines_are_stripped_before_rendering():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {
            "name": "x` @someone\n[click](http://evil)",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [],
        }
    ]
    run(fake)
    assert "`x  @someone [click](http://evil)`" in fake.comments[0]["body"]


def test_a_bare_pipe_is_escaped_so_it_cannot_leave_its_table_cell():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {
            "name": "x | @org/team [link](http://evil)",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [],
        }
    ]
    run(fake)
    assert "`x \\| @org/team [link](http://evil)`" in fake.comments[0]["body"]


def test_a_backslash_cannot_unescape_the_pipe_behind_it():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {"name": "a\\| @org/team", "conclusion": "failure", "html_url": "j", "steps": []}
    ]
    run(fake)
    row = next(line for line in fake.comments[0]["body"].splitlines() if line.startswith("| CI |"))
    # Split as GitHub does: a backslash escapes the next character, and an unescaped
    # pipe ends a cell. The row must still have exactly two cells either side of the
    # leading and trailing "|".
    cells = [""]
    i = 0
    while i < len(row):
        if row[i] == "\\" and i + 1 < len(row):
            cells[-1] += row[i] + row[i + 1]
            i += 2
            continue
        if row[i] == "|":
            cells.append("")
        else:
            cells[-1] += row[i]
        i += 1
    assert len(cells[1:-1]) == 2


def test_escape_name_caps_length_at_120_characters():
    long_name = "x" * 200
    escaped = ci_triage.escape_name(long_name)
    assert escaped == f"`{'x' * 120}`"


# --- transport safety ---


def test_resolve_url_refuses_a_non_github_host():
    with pytest.raises(ValueError, match="unexpected URL"):
        ci_triage.resolve_url("https://evil.example/repos/o/r/pulls/1")


def test_resolve_url_accepts_a_relative_path():
    assert ci_triage.resolve_url("/repos/o/r/pulls/1") == "https://api.github.com/repos/o/r/pulls/1"


# --- the anchor and cause table ---


def test_slugify_matches_anchors_already_linked_by_hand_elsewhere_in_this_repository():
    # docs/best-practices.md and AGENTS.md already link to these two anchors; if the
    # algorithm here disagreed with GitHub's own, those links would already be dead.
    assert ci_triage.slugify("`.github/workflows/ci.yml` — CI") == "githubworkflowsciyml--ci"
    assert ci_triage.slugify("Why the aggregator jobs exist") == "why-the-aggregator-jobs-exist"


def test_the_hardcoded_docs_headings_still_exist_verbatim():
    text = (Path(REPO_ROOT) / "docs" / "ci.md").read_text(encoding="utf-8")
    assert "## `.github/workflows/ci.yml` — CI" in text
    assert "## `.github/workflows/security.yml` — Security" in text


def _display_names(root, workflow_file: str) -> dict[str, str]:
    """Job id -> display name, parsed the same way `check_workflows.py` reads a
    workflow's own aggregate, reused here rather than re-implemented."""
    text = (root / ".github" / "workflows" / workflow_file).read_text(encoding="utf-8")
    jobs, _ = check_workflows.jobs_in(text)
    names = {}
    for job in jobs:
        body = check_workflows.job_body(text, jobs, job)
        match = check_workflows.DISPLAY_NAME_RE.search(body)
        assert match, f"job `{job.name}` in {workflow_file} declares no display name"
        names[job.name] = match.group(1).strip(" '\"")
    return names


def test_every_real_job_has_a_cause_entry():
    root = Path(REPO_ROOT)
    names = {
        **_display_names(root, "ci.yml"),
        **_display_names(root, "security.yml"),
    }
    missing = sorted(display for display in names.values() if display not in ci_triage.CAUSES)
    assert missing == [], (
        f"{missing} have no entry in ci_triage.CAUSES; a job with no cause entry "
        "renders 'unclassified' in a live PR comment instead of a local command"
    )
    # And nothing in CAUSES claims a job name this repository no longer has.
    stale = sorted(set(ci_triage.CAUSES) - set(names.values()))
    assert stale == [], f"{stale} in ci_triage.CAUSES no longer name a real job"


def test_a_matrix_legs_parameters_are_stripped_before_the_cause_lookup():
    assert ci_triage.cause_for("test (3.13)", OWNER, REPO) == ci_triage.cause_for(
        "test", OWNER, REPO
    )


def test_an_unknown_job_name_is_reported_rather_than_guessed_at():
    assert ci_triage.cause_for("some future job", OWNER, REPO).startswith("unclassified")


# --- the remaining branches: no PR anywhere, a commit-associated PR, an unwatched
# workflow run, two runs racing for the same workflow, a job list with nothing failed
# in it, and the label-removal error path ---


def test_no_open_pull_request_is_a_noop():
    fake = FakeGitHub()
    fake.commit_prs = []
    result = run(fake, make_trigger(pull_requests=[], head_repository_owner="", head_branch=""))
    assert result == f"No open pull request for {HEAD}; nothing to do."
    assert fake.comments == []


def test_a_commit_associated_pull_request_is_used_when_the_event_names_none():
    fake = FakeGitHub()
    fake.commit_prs = [{"number": 7, "state": "open"}]
    fake.runs = [green(1, "CI"), green(2, "Security")]
    result = run(fake, make_trigger(pull_requests=[], head_repository_owner="", head_branch=""))
    assert result == "#7: green"


def test_an_unwatched_workflow_run_is_ignored():
    fake = FakeGitHub()
    fake.runs = [
        green(1, "CI"),
        green(2, "Security"),
        {**green(3, "CodeQL"), "conclusion": "failure"},
    ]
    result = run(fake)
    assert result == "#7: green"
    assert fake.comments == []


def test_the_higher_run_number_wins_when_two_runs_share_a_workflow_name():
    fake = FakeGitHub()
    fake.runs = [
        {**green(1, "CI", 1), "conclusion": "failure"},
        green(2, "CI", 2),
        green(3, "Security"),
    ]
    result = run(fake)
    assert result == "#7: green"
    assert fake.comments == []


def test_describe_failures_skips_a_job_that_did_not_fail():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {"name": "test", "conclusion": "success", "html_url": "j1", "steps": []},
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j2",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        },
    ]
    run(fake)
    body = fake.comments[0]["body"]
    assert "`test`" not in body
    assert "`check catalogue`" in body


def test_a_failed_job_with_no_failed_step_is_reported_as_infrastructure():
    # A timeout, a cancelled step or a runner lost mid-job can fail the job with no
    # step ever recorded as the cause; that is reported as such rather than guessed.
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {"name": "check catalogue", "conclusion": "timed_out", "html_url": "j", "steps": []}
    ]
    run(fake)
    body = fake.comments[0]["body"]
    assert "infrastructure: the job failed without a failing step" in body
    assert "make catalogue" not in body


def test_a_failed_run_with_no_reported_jobs_falls_back_to_the_runs_own_conclusion():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = []
    run(fake)
    assert "failure · [run](https://gh/run/1)" in fake.comments[0]["body"]


def test_removing_the_label_raises_on_an_unexpected_status():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        }
    ]
    run(fake)  # labels the PR
    fake.runs = [green(4, "CI", 2)]  # recovers

    real_call = fake.__call__

    def flaky(method, url, headers, data):
        if method == "DELETE":
            return 500, {}, b'{"message": "server error"}'
        return real_call(method, url, headers, data)

    with pytest.raises(ci_triage.GitHubAPIError, match="returned HTTP 500"):
        ci_triage.triage(flaky, TOKEN, OWNER, REPO, make_trigger())


def test_main_reads_the_triggering_event_from_env_and_triages_it(monkeypatch, capsys):
    fake = FakeGitHub()
    fake.runs = [green(1, "CI"), green(2, "Security")]
    monkeypatch.setattr(ci_triage, "http_transport", fake)
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    monkeypatch.setenv("REPOSITORY", f"{OWNER}/{REPO}")
    monkeypatch.setenv("HEAD_SHA", HEAD)
    monkeypatch.setenv("HEAD_BRANCH", "feature")
    monkeypatch.setenv("HEAD_REPOSITORY_OWNER", "someone")
    monkeypatch.setenv("PULL_REQUESTS_JSON", json.dumps([{"number": 7}]))
    assert ci_triage.main() == 0
    assert capsys.readouterr().out.strip() == "#7: green"


def test_main_defaults_the_optional_env_vars(monkeypatch, capsys):
    # HEAD_BRANCH, HEAD_REPOSITORY_OWNER and PULL_REQUESTS_JSON are absent whenever the
    # workflow's own step never set them; main() must still run rather than raise.
    monkeypatch.delenv("HEAD_BRANCH", raising=False)
    monkeypatch.delenv("HEAD_REPOSITORY_OWNER", raising=False)
    monkeypatch.delenv("PULL_REQUESTS_JSON", raising=False)
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    monkeypatch.setenv("REPOSITORY", f"{OWNER}/{REPO}")
    monkeypatch.setenv("HEAD_SHA", HEAD)
    fake = FakeGitHub()
    fake.commit_prs = []
    monkeypatch.setattr(ci_triage, "http_transport", fake)
    assert ci_triage.main() == 0
    assert capsys.readouterr().out.strip() == f"No open pull request for {HEAD}; nothing to do."


# --- an API error must fail the run, never read as an empty, successful result ---


def _labelled_red_report(fake: FakeGitHub) -> str:
    """A standing red report and label, the state each error test starts from."""
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}, green(2, "Security")]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        }
    ]
    run(fake)
    assert fake.labels == ["ci-failed"]
    return fake.comments[0]["body"]


def test_a_503_on_the_runs_listing_raises_and_leaves_the_red_report_in_place():
    fake = FakeGitHub()
    body_before = _labelled_red_report(fake)

    real_call = fake.__call__

    def flaky(method, url, headers, data):
        if method == "GET" and "/actions/runs?" in url:
            return 503, {}, b'{"message": "server error"}'
        return real_call(method, url, headers, data)

    with pytest.raises(ci_triage.GitHubAPIError, match="returned HTTP 503"):
        ci_triage.triage(flaky, TOKEN, OWNER, REPO, make_trigger())
    # Neither the standing comment nor the label moved: the run stopped before either
    # was touched, rather than the missing runs being read as a recovery.
    assert fake.comments[0]["body"] == body_before
    assert fake.labels == ["ci-failed"]


def test_a_403_on_the_jobs_listing_raises_rather_than_rendering_a_placeholder():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]

    real_call = fake.__call__

    def flaky(method, url, headers, data):
        if method == "GET" and re.search(r"/actions/runs/\d+/jobs", url):
            return 403, {}, b'{"message": "forbidden"}'
        return real_call(method, url, headers, data)

    with pytest.raises(ci_triage.GitHubAPIError, match="returned HTTP 403"):
        ci_triage.triage(flaky, TOKEN, OWNER, REPO, make_trigger())
    # No comment was ever posted claiming "failure · [run](...)" off the back of a
    # jobs listing that actually failed to load.
    assert fake.comments == []


def test_a_5xx_on_get_pull_request_raises_rather_than_reading_as_not_open():
    fake = FakeGitHub()

    real_call = fake.__call__

    def flaky(method, url, headers, data):
        if method == "GET" and url.endswith("/pulls/7"):
            return 500, {}, b'{"message": "server error"}'
        return real_call(method, url, headers, data)

    with pytest.raises(ci_triage.GitHubAPIError, match="returned HTTP 500"):
        ci_triage.triage(flaky, TOKEN, OWNER, REPO, make_trigger())


# --- redirects must never carry the token off api.github.com ---


def test_the_redirect_handler_refuses_every_redirect():
    handler = ci_triage._NoRedirect()
    refused = handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example/steal")
    assert refused is None


def test_the_opener_uses_the_refusing_handler_in_place_of_the_default():
    handlers = ci_triage._opener.handlers
    assert any(isinstance(h, ci_triage._NoRedirect) for h in handlers)
    assert not any(type(h) is urllib.request.HTTPRedirectHandler for h in handlers)


# --- untrusted values reach a query string only percent-encoded ---


def test_the_fork_lookup_percent_encodes_owner_and_branch():
    fake = FakeGitHub()
    fake.commit_prs = []
    fake.fork_prs = [{"number": 7}]
    fake.runs = [green(1, "CI"), green(2, "Security")]
    captured = {}

    real_call = fake.__call__

    def capturing(method, url, headers, data):
        if urlparse(url).path == f"/repos/{OWNER}/{REPO}/pulls":
            captured["url"] = url
        return real_call(method, url, headers, data)

    result = ci_triage.triage(
        capturing,
        TOKEN,
        OWNER,
        REPO,
        make_trigger(pull_requests=[], head_repository_owner="some&one", head_branch="feature#1=x"),
    )
    assert result == "#7: green"
    assert "some%26one" in captured["url"]
    assert "feature%231%3Dx" in captured["url"]
    # And the colon `head=owner:branch` needs stays literal, since that is the
    # separator GitHub's own filter expects, not something being encoded away.
    assert "some%26one:feature%231%3Dx" in captured["url"]


# --- comment ownership is the bot's login, not merely "some bot or other" ---


def test_a_bot_comment_from_another_login_carrying_the_marker_is_ignored():
    fake = FakeGitHub()
    fake.comments = [
        {
            "id": 99,
            "body": f"{ci_triage.MARKER}\nsomeone else's bot comment",
            "user": {"type": "Bot", "login": "some-other-bot"},
        }
    ]
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        }
    ]
    run(fake)
    # The foreign comment was left alone, and a new one was created rather than this
    # job mistaking someone else's bot comment for its own.
    assert len(fake.comments) == 2
    assert fake.comments[0]["body"].startswith(f"{ci_triage.MARKER}\nsomeone else's bot")
    assert fake.comments[1]["body"].startswith(ci_triage.MARKER)
    assert "CI failing" in fake.comments[1]["body"]


# --- cancelled is not a verdict either way ---


def test_does_not_declare_recovery_when_the_rerun_was_cancelled():
    fake = FakeGitHub()
    fake.runs = [{**green(1, "CI"), "conclusion": "failure"}]
    fake.jobs[1] = [
        {
            "name": "check catalogue",
            "conclusion": "failure",
            "html_url": "j",
            "steps": [{"name": "step", "number": 1, "conclusion": "failure"}],
        }
    ]
    run(fake)
    fake.runs = [{**green(4, "CI", 2), "conclusion": "cancelled"}]
    result = run(fake)
    assert result == "#7: pending"
    assert "CI failing" in fake.comments[0]["body"]
    assert fake.labels == ["ci-failed"]
