#!/usr/bin/env python3
"""Decide how much of CI a run needs: all of it, or only what its tree has not passed yet.

Every pull request used to run the whole of `ci.yml`, whatever its base and however many
times the same tree had already passed. A promotion into `main` re-ran the full suite on a
tree its stage pull request had just passed, the push to `main` ran it a third time, and
every edit to a pull request's description re-ran seventeen jobs to re-read a title and a
body. On a public repository's twenty concurrent jobs that queue is what held a release
for forty minutes.

The `scope` job runs this first and every other job in `ci.yml` reads its `mode`:

- ``full`` runs everything. It is the answer for every pull request into `dev` or `stage`,
  for `workflow_dispatch` and `merge_group`, and for anything below that cannot be proven.
- ``promotion`` is a pull request into `main`, or the push to `main` after one merges,
  whose tree has already passed a full run, apart from the changelog and the release
  benchmark patch a release prepares. The cheap checks and the deployment checks still
  run; the test matrix, the browser tests and the linters of files that did not change do
  not.
- ``text`` is an `edited` event on a pull request whose commit, against the same base, has
  already passed every check that reads the code. Only the two checks that read the title
  and description run again.

Every proof is read from the GitHub API and git, and any doubt, an API error, a missing
pull request, a run still in progress, a tree that differs, is `full`. A wrong answer here
can only cost time: the aggregate accepts a skipped job only when this script listed it,
and lists are fixed below rather than built from anything the API returns.

Standard library only, like the checks beside it; the API transport is injected so the
tests answer from a table and never reach the network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

API = "https://api.github.com"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CI_WORKFLOW = "ci.yml"

# Job ids in ci.yml. The two that read the pull request's title and body, and the two
# that are the machinery itself, always run.
TEXT_JOBS = ("attribution", "naming")
ALWAYS = ("scope", "ci")
# What a promotion skips: work whose result is a function of files the promoted tree
# shares, byte for byte, with the one that already passed.
PROMOTION_SKIPS = ("test", "site-browser", "validate-plugin", "lint-yaml", "lint-actions")
# What an edit skips: everything that reads the code rather than the description.
TEXT_SKIPS = (
    "validate-skills",
    "validate-plugin",
    "test",
    "catalogue",
    "spelling",
    "lint-markdown",
    "lint-yaml",
    "lint-actions",
    "links",
    "site-browser",
    "package",
)
# Check names (as the runs API reports jobs) that read only the description, or are the
# machinery; every other job in an earlier run must have succeeded for `text`.
TEXT_CHECK_NAMES = frozenset({"attribution", "naming", "ci", "scope"})
# The only paths a promotion may differ from stage in: a release moves the changelog's
# Unreleased section and repoints the one benchmark patch that applies to it.
MAY_DIFFER = frozenset(
    {
        "CHANGELOG.md",
        ".claude/agents/benchmarks/reviewer/unpublished-release-links/change.patch",
    }
)

Get = Callable[[str], Any]
Git = Callable[..., str]


class NotProvenError(Exception):
    """Whatever stopped a proof; the run falls back to `full` and says why."""


def resolve_url(path: str) -> str:
    """A full API URL; anything that is not `https://api.github.com/...` is refused."""
    url = path if path.startswith("https://") else f"{API}{path}"
    if not url.startswith(f"{API}/"):
        raise ValueError(f"refusing to call an unexpected URL: {url}")
    return url


def _sha(value: Any, what: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise NotProvenError(f"{what} is not a commit SHA")
    return value


def heads_passed(get: Get, repo: str, head_sha: str, base_sha: str | None, skip_run: str) -> str:
    """The id of the newest CI run on `head_sha` that ran the code checks, all green.

    Runs are read newest first. A run whose code checks were all skipped was itself a
    `text` run and is passed over; the first run that actually ran them decides, and any
    code check in it that did not succeed, or any newer run still in progress, is not a
    pass. With `base_sha`, only runs against that base count, because a pull request's
    run tests its merge with the base as it was then.
    """
    runs = get(
        f"/repos/{repo}/actions/workflows/{CI_WORKFLOW}/runs"
        f"?head_sha={head_sha}&event=pull_request&per_page=30"
    )
    if not isinstance(runs, dict) or not isinstance(runs.get("workflow_runs"), list):
        raise NotProvenError("the runs listing was not the expected shape")
    for run in runs["workflow_runs"]:
        if not isinstance(run, dict) or str(run.get("id")) == skip_run:
            continue
        if base_sha is not None:
            bases = {
                (pr.get("base") or {}).get("sha")
                for pr in run.get("pull_requests") or []
                if isinstance(pr, dict)
            }
            if base_sha not in bases:
                continue
        if run.get("status") != "completed":
            raise NotProvenError("an earlier run on this commit has not finished")
        jobs = get(f"/repos/{repo}/actions/runs/{run.get('id')}/jobs?per_page=100")
        code = [
            job
            for job in (jobs or {}).get("jobs") or []
            if isinstance(job, dict) and job.get("name") not in TEXT_CHECK_NAMES
        ]
        if code and all(job.get("conclusion") == "skipped" for job in code):
            continue
        if not code or any(job.get("conclusion") != "success" for job in code):
            raise NotProvenError("the newest run that checked the code did not pass it")
        # A number, so nothing else an API answer carries reaches the job summary.
        return str(int(run.get("id")))
    raise NotProvenError("no earlier run checked this commit's code")


def merged_pull(get: Get, repo: str, commit: str, base: str) -> dict[str, Any]:
    """The pull request into `base` whose merge produced `commit`."""
    pulls = get(f"/repos/{repo}/commits/{commit}/pulls")
    for pull in pulls if isinstance(pulls, list) else []:
        if (
            isinstance(pull, dict)
            and pull.get("merge_commit_sha") == commit
            and (pull.get("base") or {}).get("ref") == base
            and pull.get("merged_at")
        ):
            return pull
    raise NotProvenError(f"{commit[:7]} is not the merge of a pull request into {base}")


def tree_of(get: Get, repo: str, commit: str) -> str:
    data = get(f"/repos/{repo}/commits/{commit}")
    return _sha(((data or {}).get("commit") or {}).get("tree", {}).get("sha"), "a tree")


def promotion_from_stage(get: Get, git: Git, repo: str) -> str:
    """Prove this tree is stage's, which passed a full run, apart from the release files."""
    stage = _sha(git("rev-parse", "origin/stage").strip(), "origin/stage")
    differ = {line for line in git("diff", "--name-only", stage, "HEAD").splitlines() if line}
    if differ - MAY_DIFFER:
        raise NotProvenError(f"differs from stage in {len(differ - MAY_DIFFER)} file(s)")
    pull = merged_pull(get, repo, stage, "stage")
    head = _sha((pull.get("head") or {}).get("sha"), "the stage pull request's head")
    if tree_of(get, repo, head) != git("rev-parse", f"{stage}^{{tree}}").strip():
        raise NotProvenError("the stage pull request's head is not the tree stage holds")
    run = heads_passed(get, repo, head, None, "")
    number = int(pull.get("number"))
    return f"same tree as stage {stage[:7]}, whose pull request #{number} passed run {run}"


def promotion_from_merge(get: Get, git: Git, repo: str, sha: str) -> str:
    """Prove the pushed commit is the tree of a pull request into main that passed."""
    pull = merged_pull(get, repo, sha, "main")
    head = _sha((pull.get("head") or {}).get("sha"), "the merged pull request's head")
    if tree_of(get, repo, head) != git("rev-parse", "HEAD^{tree}").strip():
        raise NotProvenError("the merge changed the tree its pull request was checked on")
    run = heads_passed(get, repo, head, None, "")
    return f"the tree pull request #{int(pull.get('number'))} passed in run {run}"


def decide(env: dict[str, str], get: Get, git: Git) -> tuple[str, str]:
    """`(mode, reason)` for this run; anything not proven is `full`."""
    event = env.get("EVENT_NAME", "")
    repo = env.get("REPOSITORY", "")
    try:
        if event == "pull_request":
            if env.get("EVENT_ACTION") == "edited":
                head = _sha(env.get("HEAD_SHA"), "the head")
                base = _sha(env.get("BASE_SHA"), "the base")
                run = heads_passed(get, repo, head, base, env.get("RUN_ID", ""))
                return "text", f"only the description changed; run {run} passed the code"
            if env.get("BASE_REF") == "main":
                return "promotion", promotion_from_stage(get, git, repo)
            return "full", f"a pull request into {env.get('BASE_REF') or 'an unknown base'}"
        if event == "push" and env.get("REF") == "refs/heads/main":
            sha = _sha(env.get("SHA"), "the pushed commit")
            return "promotion", promotion_from_merge(get, git, repo, sha)
    except NotProvenError as reason:
        return "full", f"not proven: {reason}"
    except Exception as error:  # noqa: BLE001 - any failure to prove is a full run, never a skip
        return "full", f"not proven: {type(error).__name__}"
    return "full", f"a {event or 'unknown'} event"


def skippable(mode: str) -> tuple[str, ...]:
    return {"promotion": PROMOTION_SKIPS, "text": TEXT_SKIPS}.get(mode, ())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects, so the token is never resent to a host `resolve_url` did not see."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(token: str) -> Get:
    """The only function that reaches the network; `decide` takes it as a parameter.

    Its inner request is left uncovered on purpose, as in `ci_triage.py`: a suite that
    can make a request is one that fails when GitHub does.
    """
    opener = urllib.request.build_opener(_NoRedirect)

    def get(path: str) -> Any:
        request = urllib.request.Request(  # noqa: S310 - resolve_url enforces the API host
            resolve_url(path),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ci-scope",
            },
        )
        try:
            with opener.open(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise NotProvenError(f"the API answered HTTP {error.code}") from error

    return get


def run_git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def main() -> int:
    mode, reason = decide(dict(os.environ), http_get(os.environ.get("GH_TOKEN", "")), run_git)
    skip = " ".join(skippable(mode))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"mode={mode}\nskippable={skip}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"**CI scope: `{mode}`.** {reason}\n")
    print(f"mode={mode}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
