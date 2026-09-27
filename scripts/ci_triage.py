#!/usr/bin/env python3
"""Keep one self-updating PR comment naming why CI or Security failed.

Ported from `greenblacked/status-page`'s `.github/workflows/ci-triage.yml` and
`scripts/ci/ci-triage.cjs`, which do the same job in JavaScript through
`actions/github-script`. This repository has no JavaScript toolchain — no test
runner, no linter — so a `.cjs` file here would be untested and unlinted. Both
languages keep the same trust boundary: `urllib` with an `https` scheme check,
a token read from the environment, and an injectable transport so tests answer
from a fake rather than the network, the idiom `check_pin_freshness.py` uses.

Only ever reads run, job and step *metadata* through the API and never
downloads a log. It never checks out or executes anything from the pull
request; `.github/workflows/ci-triage.yml` checks out only the default
branch, sparsely, for this file. `workflow_run` — the trigger that wakes this
script — can hold a write token even when the run that triggered it came from
a fork, which is exactly why nothing here touches the fork's content: job and
step *names*, by contrast, come from a workflow file that lives in the pull
request, so a fork controls their text. `escape_name` is what keeps that text
inert before it goes anywhere near this comment's Markdown table.

`api()` raises `GitHubAPIError` for any response outside 200-299, the one
exception being a 404 on removing a label. A failed read is not "zero items"
and a failed write is not "done" — either one has to fail the job loudly
rather than be misread as a clean, empty result that then declares recovery
or removes the label on the strength of nothing.

Each run recomputes the whole picture from the API for the pull request's
*current* head commit rather than trusting the single `workflow_run` event
that woke it up: GitHub keeps at most one pending run per concurrency group
and cancels the rest, so an event can be dropped, and recomputing everything
makes any surviving run correct regardless of what it was told.

What it does, in order:

1. Find the open pull request for the triggering run — `pull_requests` on the
   event first, then the commit's associated pull requests, then a fork
   lookup by head branch — and skip if that pull request has since moved past
   the commit this run was for.
2. Recompute the latest run of each watched workflow (`CI`, `Security`) for
   the pull request's current head SHA, so a dropped event loses nothing.
3. For a failed run, find each failed job's first failed step and look up a
   likely cause in `CAUSES`, a table keyed on this repository's own job
   names and kept in step with `docs/ci.md`'s "Failing means" column —
   `tests/test_ci_triage.py` parses `.github/workflows/ci.yml` and
   `security.yml` and fails if a job exists with no entry here. A failure
   with no failed step (a timeout, a cancellation, lost infrastructure) is
   reported as such rather than guessed at.
4. Update a single marker comment (`MARKER`) in place — created once, edited
   after that, never duplicated and never deleted — and keep a `ci-failed`
   label in step with it. A pull request that has never failed gets no
   comment at all, and a red report is left standing while a re-run is still
   in flight rather than being cleared early.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

API = "https://api.github.com"
MARKER = "<!-- ai-ci-triage -->"
LABEL = "ci-failed"
WATCHED = ("CI", "Security")
# Only these count as a failure. `cancelled` says nothing about the code, so it holds
# whatever verdict already stood rather than declaring either failure or recovery.
FAILED_CONCLUSIONS = frozenset({"failure", "timed_out", "startup_failure"})
# Only these count as passing. `cancelled`, `action_required` (a fork run waiting on
# approval) and `stale` are neither, so they leave the previous state alone.
PASSED_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})

# The heading that opens each workflow's section in docs/ci.md, verbatim — checked
# against the file itself in tests/test_ci_triage.py so a renamed heading is caught
# rather than silently producing a dead anchor.
_CI_HEADING = "`.github/workflows/ci.yml` — CI"
_SECURITY_HEADING = "`.github/workflows/security.yml` — Security"


def slugify(heading: str) -> str:
    """Approximate GitHub's own Markdown-heading-to-anchor algorithm.

    Lowercase, drop anything that is not a word character, a space or a hyphen
    (which is what removes the backticks and the em dash in a heading like this
    file's own), then turn each remaining space into a hyphen. Verified against
    two anchors this repository already links to by hand in `docs/best-practices.md`
    and `AGENTS.md`: `#githubworkflowsciyml--ci` and `#why-the-aggregator-jobs-exist`.
    """
    lowered = heading.lower()
    kept = re.sub(r"[^\w\- ]+", "", lowered)
    return kept.replace(" ", "-")


WORKFLOW_ANCHORS = {
    "ci.yml": slugify(_CI_HEADING),
    "security.yml": slugify(_SECURITY_HEADING),
}

# Keyed on the job's *display name* — the API's `job.name`, which is a workflow's
# `name:` field for that job, not the `jobs:` key. A matrix leg's name carries its
# parameters ("test (3.13)"), so `cause_for` strips a trailing "(...)" before this
# lookup, the same way `docs/ci.md` describes the `test` row.
#
# tests/test_ci_triage.py parses both workflows and asserts every job's display name
# is a key here, so adding a job with no cause entry fails the test rather than
# rendering "unclassified" silently in a live PR comment.
CAUSES: dict[str, tuple[str, str]] = {
    "validate skills": ("make validate", "ci.yml"),
    "validate plugin manifest": (
        "npx --yes @anthropic-ai/claude-code plugin validate .",
        "ci.yml",
    ),
    "test": ("make test (`make coverage` for the 3.13 leg)", "ci.yml"),
    "check catalogue": ("make catalogue", "ci.yml"),
    "lint spelling": ("codespell (part of `make lint`)", "ci.yml"),
    "lint markdown": ("markdownlint-cli2 '**/*.md' (part of `make lint`)", "ci.yml"),
    "lint yaml": ("yamllint --strict . (part of `make lint`)", "ci.yml"),
    "lint workflows": ("actionlint (part of `make lint`)", "ci.yml"),
    "check links": ("lychee --offline './**/*.md'", "ci.yml"),
    "attribution": ("make attribution", "ci.yml"),
    "naming": ("make naming", "ci.yml"),
    "package": ("make package", "ci.yml"),
    "ci": (
        "no single command - this is the aggregate; open the run to see which "
        "dependency job failed",
        "ci.yml",
    ),
    "secret scan": ("gitleaks dir . --redact && gitleaks git . --redact", "security.yml"),
    "workflow audit": (
        "zizmor --persona=regular --min-severity=medium .",
        "security.yml",
    ),
    "python security lint": ("ruff check . && ruff format --check .", "security.yml"),
    "codeql": (
        "no local reproduction - read the alert under the repository's Security tab",
        "security.yml",
    ),
    "permissions audit": (
        "review docs/ci.md's four shell invariants by eye; no script reproduces this locally yet",
        "security.yml",
    ),
    "security": (
        "no single command - this is the aggregate; open the run to see which "
        "dependency job failed",
        "security.yml",
    ),
}

# A matrix leg's display name carries its parameters in a trailing "(...)".
_MATRIX_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")

# Untrusted names are stripped of backticks and newlines, capped, and have their
# backslashes and pipes escaped in one pass — escaping the pipe alone is not enough,
# because "\|" would then read as an escaped backslash followed by a bare pipe, which
# still ends a Markdown table cell.
_STRIP_RE = re.compile(r"[`\r\n]+")
_ESCAPE_RE = re.compile(r"[\\|]")


def escape_name(text: Any) -> str:
    """Make an untrusted job or step name safe inside one Markdown table cell.

    Never executed and never placed in a shell — this only ever ends up as text in
    a PR comment. Job and step names come from the workflow file at the pull
    request's head, so a fork fully controls their content.
    """
    safe = _STRIP_RE.sub(" ", str(text))
    safe = safe[:120]
    safe = _ESCAPE_RE.sub(lambda match: "\\" + match.group(0), safe)
    return f"`{safe}`"


def docs_link(owner: str, repo: str, workflow_file: str) -> str:
    """A link into this repository's own `docs/ci.md`, at the workflow's section."""
    return (
        f"https://github.com/{owner}/{repo}/blob/main/docs/ci.md#{WORKFLOW_ANCHORS[workflow_file]}"
    )


def cause_for(job_name: str, owner: str, repo: str) -> str:
    """The likely cause and local reproduction for one failed job's display name."""
    display = _MATRIX_SUFFIX_RE.sub("", job_name).strip()
    entry = CAUSES.get(display)
    if entry is None:
        return "unclassified - no cause entry for this job name; read its own log"
    command, workflow_file = entry
    return f"{command} · [docs]({docs_link(owner, repo, workflow_file)})"


# The transport this module actually needs: one call, one response. Real traffic goes
# through `http_transport`; tests supply a fake with the same shape, the way
# `check_pin_freshness.py`'s tests replace `fetch` with a table.
Transport = Callable[
    [str, str, dict[str, str], "bytes | None"], "tuple[int, dict[str, str], bytes]"
]


def resolve_url(path: str) -> str:
    """A full API URL from a relative path or an already-absolute one.

    `paginate` below follows a `Link` header, which GitHub already returns as a full
    URL; everything else calls in with a path. Either way the result must be
    `https://api.github.com/...` — never anything else, so a malformed or hostile
    pagination link cannot send this job's token somewhere unexpected.
    """
    url = path if path.startswith("https://") else f"{API}{path}"
    if not url.startswith("https://api.github.com/"):
        raise ValueError(f"refusing to call an unexpected URL: {url}")
    return url


class GitHubAPIError(RuntimeError):
    """A GitHub API call returned a status the caller did not ask to tolerate.

    Raised rather than swallowed: the JavaScript this file ports throws on any
    non-2xx Octokit response, and losing that on the way to Python is what let a
    503 on the runs listing read as "zero runs", a 403 on the jobs listing read as
    "no jobs", and a 5xx on the pull request itself read as "not open" — each one
    turning a failed API call into a false "Recovered" comment and a removed label
    instead of a red job.
    """

    def __init__(self, method: str, path: str, status: int) -> None:
        super().__init__(f"{method} {path} returned HTTP {status}")
        self.method = method
        self.path = path
        self.status = status


def api(
    transport: Transport,
    token: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    ok: tuple[int, ...] = (),
) -> tuple[int, Any, dict[str, str]]:
    """One authenticated GitHub API call.

    Raises `GitHubAPIError` for any status outside 200-299 that is not listed in
    `ok`. `ok` exists for exactly one caller — removing a label tolerates 404,
    because the label already being gone is the outcome being asked for. Every
    other call, read or write, gets no such tolerance: a failed read must stop the
    run rather than be read as "zero items", and a failed write must stop the run
    rather than be read as "done".
    """
    url = resolve_url(path)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ci-triage",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    status, response_headers, raw = transport(method, url, headers, data)
    parsed = json.loads(raw) if raw else None
    if status not in ok and not (200 <= status < 300):
        raise GitHubAPIError(method, path, status)
    return status, parsed, response_headers


_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _next_link(headers: dict[str, str]) -> str | None:
    link = headers.get("Link") or headers.get("link")
    if not link:
        return None
    match = _LINK_NEXT_RE.search(link)
    return match.group(1) if match else None


def paginate(transport: Transport, token: str, path: str) -> list[Any]:
    """Every item across a `Link: rel="next"` walk, hand-written rather than pulled
    in as a dependency for one loop."""
    items: list[Any] = []
    url: str | None = path
    while url:
        _, data, headers = api(transport, token, "GET", url)
        items.extend(data or [])
        url = _next_link(headers)
    return items


def find_pull_request(
    transport: Transport, token: str, owner: str, repo: str, trigger: dict[str, Any]
) -> int | None:
    """The open pull request a `workflow_run` event belongs to, forks included."""
    pull_requests = trigger.get("pull_requests") or []
    if pull_requests:
        return pull_requests[0]["number"]

    _, by_commit, _ = api(
        transport, token, "GET", f"/repos/{owner}/{repo}/commits/{trigger['head_sha']}/pulls"
    )
    for pr in by_commit or []:
        if pr.get("state") == "open":
            return pr["number"]

    # `workflow_run.pull_requests` is empty for a fork's pull request; match on the
    # head branch instead. Both come from the trigger event — a fork's own repository
    # owner and branch name — so each is percent-encoded on its own before it joins
    # the query string; only the literal `:` GitHub's `head` filter expects sits
    # unencoded between them.
    fork_owner = trigger.get("head_repository_owner")
    branch = trigger.get("head_branch")
    if fork_owner and branch:
        head = f"{quote(fork_owner, safe='')}:{quote(branch, safe='')}"
        _, by_branch, _ = api(
            transport, token, "GET", f"/repos/{owner}/{repo}/pulls?state=open&head={head}"
        )
        if by_branch:
            return by_branch[0]["number"]
    return None


def latest_runs(
    transport: Transport, token: str, owner: str, repo: str, head_sha: str
) -> dict[str, dict[str, Any]]:
    """The most recent run of each watched workflow for the pull request's current
    head SHA, so a dropped or superseded event loses nothing."""
    _, data, _ = api(
        transport,
        token,
        "GET",
        f"/repos/{owner}/{repo}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100",
    )
    latest: dict[str, dict[str, Any]] = {}
    for run in (data or {}).get("workflow_runs", []):
        name = run.get("name")
        if name not in WATCHED:
            continue
        previous = latest.get(name)
        if previous is None or run.get("run_number", 0) > previous.get("run_number", 0):
            latest[name] = run
    return latest


def describe_failures(
    transport: Transport, token: str, owner: str, repo: str, run: dict[str, Any]
) -> list[dict[str, str]]:
    """Each failed job in one run, with its first failed step and a likely cause."""
    _, data, _ = api(
        transport,
        token,
        "GET",
        f"/repos/{owner}/{repo}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100",
    )
    failures = []
    for job in (data or {}).get("jobs", []):
        if job.get("conclusion") not in FAILED_CONCLUSIONS:
            continue
        step = next(
            (s for s in job.get("steps") or [] if s.get("conclusion") in FAILED_CONCLUSIONS),
            None,
        )
        job_name = job.get("name", "")
        html_url = job.get("html_url", "")
        if step is None:
            cause = (
                "infrastructure: the job failed without a failing step "
                "(timeout, cancellation or runner loss)"
            )
            url = html_url
        else:
            cause = cause_for(job_name, owner, repo)
            url = f"{html_url}#step:{step.get('number')}:1"
        failures.append(
            {"job": job_name, "step": step.get("name") if step else "", "url": url, "cause": cause}
        )
    return failures


def render_comment(head_sha: str, rows: list[dict[str, str]], failing: bool) -> str:
    """The whole comment body, marker included."""
    short = head_sha[:7]
    lines = [MARKER]
    if failing:
        lines.append(f"### CI failing on `{short}`")
    else:
        lines.append(f"### Recovered: all watched workflows pass on `{short}`")
    lines += ["", "| Workflow | Result |", "| --- | --- |"]
    for row in rows:
        lines.append(f"| {row['workflow']} | {row['result']} |")
    lines += [
        "",
        "<sub>Updated in place by `.github/workflows/ci-triage.yml`. It reads the "
        "GitHub API only and never runs code from this pull request.</sub>",
    ]
    return "\n".join(lines)


def triage(transport: Transport, token: str, owner: str, repo: str, trigger: dict[str, Any]) -> str:
    """Recompute one pull request's CI state and bring its comment and label up to
    date. Returns a one-line summary for the job log."""
    number = find_pull_request(transport, token, owner, repo, trigger)
    if number is None:
        return f"No open pull request for {trigger['head_sha']}; nothing to do."

    _, pr, _ = api(transport, token, "GET", f"/repos/{owner}/{repo}/pulls/{number}")
    if pr is None or pr.get("state") != "open":
        return f"#{number} is not open; nothing to do."
    head_sha = pr["head"]["sha"]
    if head_sha != trigger["head_sha"]:
        return (
            f"#{number} has moved on to {head_sha}; ignoring the result for {trigger['head_sha']}."
        )

    runs = latest_runs(transport, token, owner, repo, head_sha)
    rows: list[dict[str, str]] = []
    failing = False
    pending = False
    for workflow in WATCHED:
        run = runs.get(workflow)
        if run is None:
            continue
        html_url = run.get("html_url", "")
        if run.get("status") != "completed":
            pending = True
            rows.append(
                {"workflow": workflow, "result": f"pending ({run['status']}) · [run]({html_url})"}
            )
            continue
        conclusion = run.get("conclusion")
        if conclusion in FAILED_CONCLUSIONS:
            failing = True
            failures = describe_failures(transport, token, owner, repo, run)
            if failures:
                detail = "<br>".join(
                    escape_name(f["job"])
                    + (f" → {escape_name(f['step'])}" if f["step"] else "")
                    + f": {f['cause']} · [logs]({f['url']})"
                    for f in failures
                )
            else:
                detail = f"{conclusion} · [run]({html_url})"
            rows.append({"workflow": workflow, "result": f"failing: {detail}"})
        elif conclusion in PASSED_CONCLUSIONS:
            rows.append(
                {"workflow": workflow, "result": f"passing ({conclusion}) · [run]({html_url})"}
            )
        else:
            pending = True
            rows.append(
                {"workflow": workflow, "result": f"no verdict ({conclusion}) · [run]({html_url})"}
            )

    comments = paginate(
        transport, token, f"/repos/{owner}/{repo}/issues/{number}/comments?per_page=100"
    )
    # `login`, not `type == "Bot"`: any bot can carry the marker in its own comment,
    # and matching on type alone would let this job edit or "own" someone else's.
    # `github-actions[bot]` is the login `GITHUB_TOKEN` posts as.
    existing = next(
        (
            c
            for c in comments
            if (c.get("user") or {}).get("login") == "github-actions[bot]"
            and (c.get("body") or "").startswith(MARKER)
        ),
        None,
    )

    if failing or existing is not None:
        if not failing and pending:
            pass  # A recovery run is still in flight; leave the red report standing.
        else:
            body = render_comment(head_sha, rows, failing)
            if existing is not None:
                api(
                    transport,
                    token,
                    "PATCH",
                    f"/repos/{owner}/{repo}/issues/comments/{existing['id']}",
                    {"body": body},
                )
            else:
                api(
                    transport,
                    token,
                    "POST",
                    f"/repos/{owner}/{repo}/issues/{number}/comments",
                    {"body": body},
                )

    labelled = any(label.get("name") == LABEL for label in pr.get("labels") or [])
    if failing and not labelled:
        api(
            transport,
            token,
            "POST",
            f"/repos/{owner}/{repo}/issues/{number}/labels",
            {"labels": [LABEL]},
        )
    elif not failing and not pending and labelled:
        # 404 is tolerated: the label already being gone is the outcome being asked
        # for. Anything else — a 403, a 5xx — still raises through `api`.
        api(
            transport,
            token,
            "DELETE",
            f"/repos/{owner}/{repo}/issues/{number}/labels/{LABEL}",
            ok=(404,),
        )

    return f"#{number}: {'failing' if failing else 'pending' if pending else 'green'}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow a redirect rather than silently resending the token to it.

    `Authorization` above carries this job's live token, scoped to
    `api.github.com` by `resolve_url` before any request is ever made. Nothing
    about a 3xx response re-validates where it points before urllib would
    otherwise follow it — and resend that same header, off this host, without
    `resolve_url` ever seeing the new one. Returning `None` here refuses every
    redirect outright: the 3xx falls through to the same non-2xx handling `api`
    gives every other status, rather than a hop this file never chose.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def http_transport(
    method: str, url: str, headers: dict[str, str], data: bytes | None
) -> tuple[int, dict[str, str], bytes]:
    """The one function in this file that reaches the network.

    Left uncovered on purpose rather than hidden behind a pragma, the same way
    `check_pin_freshness.py`'s `fetch` is: exercising it would put the suite on the
    network, and a suite that can make a request is one that fails when GitHub
    does. The coverage report naming these lines is the honest record that
    nothing in the suite sends a request, which is the property worth keeping.
    Everything that decides anything — the scheme and host in `resolve_url`,
    redirects being refused in `_NoRedirect` — is tested without ever reaching
    this function.
    """
    request = urllib.request.Request(  # noqa: S310 - resolve_url enforces https and the API host
        url, data=data, headers=headers, method=method
    )
    try:
        with _opener.open(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict((error.headers or {}).items()), error.read()


def main(argv: list[str] | None = None) -> int:
    """Read the triggering event out of `env:` and triage the pull request it names.

    No argument parsing: `.github/workflows/ci-triage.yml` passes every event value
    through `env:` rather than interpolating any of it into this command line, so
    nothing here is untrusted shell input.
    """
    del argv
    token = os.environ["GH_TOKEN"]
    owner, repo = os.environ["REPOSITORY"].split("/", 1)
    trigger = {
        "head_sha": os.environ["HEAD_SHA"],
        "head_branch": os.environ.get("HEAD_BRANCH", ""),
        "head_repository_owner": os.environ.get("HEAD_REPOSITORY_OWNER", ""),
        "pull_requests": json.loads(os.environ.get("PULL_REQUESTS_JSON") or "[]"),
    }
    print(triage(http_transport, token, owner, repo, trigger))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
