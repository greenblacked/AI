#!/usr/bin/env python3
"""Open the back-merge pull requests that follow a merged promotion.

This repository promotes `dev` into `stage` and `stage` into `main` with squash merges,
so each promotion leaves the branch it came from without the commit that landed on the
branch it went to. Left alone, the two drift: the next promotion re-resolves the same
changelog conflict, and `git log origin/dev..origin/stage` fills with commits that are
already released. `docs/ci.md#releasing-a-version` has always asked for a back-merge
after a release, by hand. This script is that step, run by `.github/workflows/back-merge.yml`
on a push to `stage` or `main`:

- a `release/promote-dev-to-stage` pull request merged into `stage` leaves one
  back-merge, `stage` into `dev`;
- a `release/promote-stage-to-main` pull request merged into `main` leaves two, `main`
  into `stage` and `main` into `dev`.

A push is not a promotion, so the script finds out what was pushed. It asks GitHub which
pull requests the pushed commit belongs to, reads each one, and acts only when one of
them satisfies all of: it is merged; it was merged into the branch that was pushed; its
head is in this repository; its head is `release/promote-dev-to-stage` or
`release/promote-stage-to-main` for that base, followed by the end of the name, `-` or
`/`; and its `merge_commit_sha` is the commit that was pushed. A direct push, a push of
anything a promotion did not merge, and a later push to a branch an earlier promotion
once reached all fail one of those and do nothing. So does the merge of a back-merge
pull request itself, whose head is `main` or `stage`, which is what stops a loop.

Each back-merge is a pull request whose head is the source long-lived branch itself
(`--head stage --base dev`). So the workflow needs no write access to repository contents:
it creates no branch, pushes no commit and moves no ref. It only reads, through the API,
and opens pull requests. GitHub makes the merge commit when a person merges the pull
request with the merge commit method, never a squash, because a squash would leave the
source's history unmerged and the two branches drifting again.

What it deliberately does not do:

- Resolve a conflict. When GitHub reports the pull request as not mergeable, the body
  says so and gives the commands for resolving it by hand on a separate branch.
- Open a duplicate. An open pull request for the same head and base is left exactly as
  it is, and so is a pair with nothing to merge (`ahead_by == 0`).
- Merge anything, enable auto-merge, or use a bypass.
- Take a branch name from the event. The branches come from the fixed table below; the
  push only says which row to look at.
- Act without a GitHub App token. Pull requests opened with the workflow token start no
  workflow, so the required checks would never report on them. The token arrives in
  `GH_TOKEN`, and `BACK_MERGE_TOKEN=app` says it is the App's; anything else is a
  notice and no action.

Every call goes through `gh api`. Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# (base the promotion merged into, head-branch prefix of a promotion, back-merges to open)
PROMOTIONS: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    ("stage", "release/promote-dev-to-stage", (("stage", "dev"),)),
    ("main", "release/promote-stage-to-main", (("main", "stage"), ("main", "dev"))),
)

MARKER = "<!-- back-merge -->"
DOCS_PATH = "docs/ci.md#back-merges-after-a-promotion"

# How long to wait for GitHub to compute whether a new pull request merges cleanly.
MERGEABLE_POLLS = 10
MERGEABLE_PAUSE = 3.0

Api = Callable[..., Any]


class ApiError(RuntimeError):
    """A GitHub API call that did not return 2xx."""

    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


def head_matches(head_ref: str, prefix: str) -> bool:
    """The prefix, then the end of the name, `-` or `/`: `release/promote-dev-to-stage-0.7`
    and `release/promote-dev-to-stage` match, `release/promote-dev-to-stagex` does not."""
    return head_ref == prefix or head_ref.startswith((prefix + "-", prefix + "/"))


def plan(pull: Any, repository: str, branch: str, sha: str) -> list[tuple[str, str]]:
    """The (source, destination) back-merges one pull request calls for, when it is the
    promotion that produced commit `sha` on `branch`; empty otherwise. `pull` is the
    pull request as GitHub returns it, never a value from the pushed event."""
    if not isinstance(pull, dict) or pull.get("merged") is not True:
        return []
    if pull.get("merge_commit_sha") != sha:
        return []
    head = pull.get("head") or {}
    base = pull.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name")
    head_ref = head.get("ref")
    if head_repo != repository or not isinstance(head_ref, str) or base.get("ref") != branch:
        return []
    for promoted_base, prefix, back_merges in PROMOTIONS:
        if branch == promoted_base and head_matches(head_ref, prefix):
            return list(back_merges)
    return []


def resolve(api: Api, repo: str, branch: str, sha: str) -> tuple[int, list[tuple[str, str]]] | None:
    """The promotion pull request that produced `sha` on `branch` and what it calls for,
    or None when the push is not the merge of one."""
    candidates = api("GET", f"repos/{repo}/commits/{sha}/pulls?per_page=100") or []
    for candidate in candidates:
        number = candidate.get("number") if isinstance(candidate, dict) else None
        if not isinstance(number, int):
            continue
        targets = plan(api("GET", f"repos/{repo}/pulls/{number}"), repo, branch, sha)
        if targets:
            return number, targets
    return None


def title_for(source: str, destination: str, number: int) -> str:
    return f"Merge {source} into {destination} after the promotion in #{number}"


def body_for(source: str, destination: str, number: int, *, conflict: bool = False) -> str:
    lines = [
        MARKER,
        f"This merges `{source}` back into `{destination}` after #{number} was promoted into "
        f"`{source}`, following the back-merge step in [docs/ci.md]({DOCS_PATH}).",
        "",
        f"- **What it carries:** everything on `{source}` that `{destination}` does not have "
        f"yet, and so the promotion commit itself. It makes `{source}`'s history an ancestor "
        f"of `{destination}`, so the next promotion starts from a common base.",
        f"- **Head:** `{source}` itself, so the branch is not copied and the workflow "
        "pushes nothing.",
        "- **Merge method:** merge with a merge commit, not squashed. A squash would leave "
        f"`{source}`'s history unmerged and the two branches drifting again.",
        "- **Conflicts:** never resolved automatically.",
    ]
    if conflict:
        branch = f"chore/back-merge-{source}-into-{destination}"
        lines += [
            "",
            "## Conflicts",
            "",
            f"GitHub reports that `{source}` does not merge cleanly into `{destination}`. "
            f"`{source}` is protected, so resolve it on a branch of your own, merge that "
            "branch with a merge commit, and close this pull request:",
            "",
            "```shell",
            "git fetch origin",
            f"git switch -c {branch} origin/{source}",
            f"git merge origin/{destination}",
            "# resolve the conflicts, keeping newer work on the destination",
            "git commit",
            f"git push origin {branch}",
            f"gh pr create --base {destination} --head {branch} \\",
            f"  --title 'Merge {source} into {destination} after the promotion in #{number}'",
            "```",
            "",
            f"Keep what `{destination}` has gained since the promotion; never drop one of its "
            "commits to make the trees match.",
        ]
    return "\n".join(lines) + "\n"


def gh_api(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """One `gh api` call, JSON in and out. Raises ApiError on a non-2xx response."""
    command = ["gh", "api", "--method", method, path]
    stdin = None
    if body is not None:
        command += ["--input", "-"]
        stdin = json.dumps(body)
    result = subprocess.run(  # noqa: S603 - fixed argv; gh resolves the host and token itself
        command,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        text = (result.stderr or result.stdout).strip()
        found = re.search(r"HTTP (\d{3})", text)
        status = int(found.group(1)) if found else None
        raise ApiError(status, text)
    return json.loads(result.stdout) if result.stdout.strip() else None


def annotate(level: str, message: str) -> None:
    safe = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level}::{safe}")


def open_pull(api: Api, repo: str, source: str, destination: str) -> dict[str, Any] | None:
    """The open pull request from `source` into `destination`, if there is one."""
    owner = repo.split("/", 1)[0]
    pulls = api(
        "GET", f"repos/{repo}/pulls?state=open&base={destination}&head={owner}:{source}&per_page=5"
    )
    return pulls[0] if pulls else None


def mergeable(api: Api, repo: str, number: int, sleep: Callable[[float], None]) -> bool | None:
    """GitHub computes mergeability lazily: `mergeable` is null until it has. Wait a
    little, and say None, not clean, when it never answers."""
    for attempt in range(MERGEABLE_POLLS):
        value = api("GET", f"repos/{repo}/pulls/{number}").get("mergeable")
        if value is not None:
            return bool(value)
        if attempt + 1 < MERGEABLE_POLLS:
            sleep(MERGEABLE_PAUSE)
    return None


def back_merge(
    api: Api,
    repo: str,
    source: str,
    destination: str,
    number: int,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, str]:
    """One back-merge. Returns what happened, for the summary."""
    pair = {"back_merge": f"{source} into {destination}"}
    existing = open_pull(api, repo, source, destination)
    if existing is not None:
        annotate("notice", f"#{existing['number']} already merges {source} into {destination}")
        return {**pair, "pull_request": f"#{existing['number']}", "result": "already open"}
    ahead = api("GET", f"repos/{repo}/compare/{destination}...{source}")["ahead_by"]
    if ahead == 0:
        annotate("notice", f"{destination} already has everything on {source}; nothing to merge")
        return {**pair, "result": "nothing to merge"}

    title = title_for(source, destination, number)
    try:
        created = api(
            "POST",
            f"repos/{repo}/pulls",
            {
                "title": title,
                "head": source,
                "base": destination,
                "body": body_for(source, destination, number),
                "maintainer_can_modify": False,
            },
        )
    except ApiError as error:
        annotate(
            "error",
            f"could not open {source} into {destination}: {error}. Check that the App is "
            f"installed on this repository with the permissions in {DOCS_PATH}.",
        )
        raise
    pull_number = created["number"]
    result = "opened"
    if mergeable(api, repo, pull_number, sleep) is False:
        api(
            "PATCH",
            f"repos/{repo}/pulls/{pull_number}",
            {"body": body_for(source, destination, number, conflict=True)},
        )
        annotate(
            "warning",
            f"#{pull_number} ({source} into {destination}) has conflicts; resolve them by "
            f"hand, see {DOCS_PATH}",
        )
        result = "opened, conflicts"
    return {**pair, "pull_request": f"#{pull_number}", "result": result}


def write_summary(rows: list[dict[str, str]]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["| Back-merge | Pull request | Result |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['back_merge']} | {row.get('pull_request', '')} | {row['result']} |")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def push_target(event: Any) -> tuple[str, str] | None:
    """(branch, sha) when the event is a push of a commit to `stage` or `main`."""
    if not isinstance(event, dict):
        return None
    ref, sha = event.get("ref"), event.get("after")
    if not isinstance(ref, str) or not isinstance(sha, str):
        return None
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or set(sha) == {"0"}:
        return None
    branch = ref.removeprefix("refs/heads/")
    if branch == ref or branch not in {promoted for promoted, _, _ in PROMOTIONS}:
        return None
    return branch, sha


def main(argv: list[str] | None = None, api: Api = gh_api) -> int:
    del argv
    repo = os.environ["GH_REPO"]
    event_path = os.environ["GITHUB_EVENT_PATH"]
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pushed = push_target(event)
    if pushed is None:
        annotate("notice", "not a push of a commit to stage or main; nothing to do")
        return 0
    if os.environ.get("BACK_MERGE_TOKEN") != "app":
        annotate(
            "notice",
            f"no GitHub App token, so nothing was opened; configure the App as described in "
            f"{DOCS_PATH}",
        )
        return 0
    branch, sha = pushed
    found = resolve(api, repo, branch, sha)
    if found is None:
        annotate("notice", f"{sha[:7]} on {branch} is not the merge of a promotion; nothing to do")
        return 0
    number, targets = found
    rows: list[dict[str, str]] = []
    failed = False
    for source, destination in targets:
        try:
            rows.append(back_merge(api, repo, source, destination, number))
        except ApiError as error:
            failed = True
            annotate("error", f"{source} into {destination}: {error}")
            rows.append({"back_merge": f"{source} into {destination}", "result": "failed"})
    write_summary(rows)
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
