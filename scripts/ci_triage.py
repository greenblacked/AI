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


def api(
    transport: Transport, token: str, method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, Any, dict[str, str]]:
    """One authenticated GitHub API call. Never raises on a non-2xx status.

    Every caller decides for itself what a given status means here - success,
    "already gone" on a 404 label removal, or something worth surfacing - rather
    than this function guessing which statuses are acceptable for every endpoint it
    is used for.
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
    # head branch instead.
    fork_owner = trigger.get("head_repository_owner")
    branch = trigger.get("head_branch")
    if fork_owner and branch:
        _, by_branch, _ = api(
            transport,
            token,
            "GET",
            f"/repos/{owner}/{repo}/pulls?state=open&head={fork_owner}:{branch}",
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
    existing = next(
        (
            c
            for c in comments
            if (c.get("user") or {}).get("type") == "Bot"
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
        status, _, _ = api(
            transport, token, "DELETE", f"/repos/{owner}/{repo}/issues/{number}/labels/{LABEL}"
        )
        if status not in (200, 204, 404):
            raise RuntimeError(f"could not remove the {LABEL} label from #{number}: HTTP {status}")

    return f"#{number}: {'failing' if failing else 'pending' if pending else 'green'}"


def http_transport(
    method: str, url: str, headers: dict[str, str], data: bytes | None
) -> tuple[int, dict[str, str], bytes]:  # pragma: no cover
    """The one function in this file that reaches the network.

    Left untested for the reason `check_pin_freshness.py`'s `fetch` gives: exercising
    it would put the suite on the network, and a suite that can make a request is one
    that fails when GitHub does. `resolve_url`, called from `api` before this is ever
    reached, is where the scheme and host are actually decided, and that is tested.
    """
    request = urllib.request.Request(  # noqa: S310 - resolve_url enforces https and the API host
        url, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
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
