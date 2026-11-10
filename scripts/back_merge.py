#!/usr/bin/env python3
"""Open the back-merge pull requests that follow a merged promotion.

This repository promotes `dev` into `stage` and `stage` into `main` with squash merges,
so each promotion leaves the branch it came from without the commit that landed on the
branch it went to. Left alone, the two drift: the next promotion re-resolves the same
changelog conflict, and `git log origin/dev..origin/stage` fills with commits that are
already released. `docs/ci.md#releasing-a-version` has always asked for a back-merge
after a release, by hand. This script is that step, run by `.github/workflows/back-merge.yml`
once a promotion pull request has actually merged:

- `release/promote-dev-to-stage*` into `stage` leaves one back-merge, `stage` into `dev`;
- `release/promote-stage-to-main*` into `main` leaves two, `main` into `stage` and
  `main` into `dev`.

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
  event only decides whether a table row applies, and `plan` re-checks what the
  workflow's `if:` already filtered, so a mistake in one is not a hole in the other.

Every call goes through `gh api`; the token arrives in `GH_TOKEN`. A token minted from a
GitHub App is the one that makes the pull request start the required checks; the workflow
token cannot, because GitHub starts no workflow from an event that token caused. The
script is told which it has through `BACK_MERGE_TOKEN`, and says so in the pull request
body when it is the second.

Standard library only, like the checks it sits beside.
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


def plan(event: dict[str, Any], repository: str) -> list[tuple[str, str]]:
    """The (source, destination) back-merges a pull request event calls for; empty unless
    it is a pull request that was merged, from this repository, as a promotion."""
    if event.get("action") != "closed":
        return []
    pull = event.get("pull_request")
    if not isinstance(pull, dict) or pull.get("merged") is not True:
        return []
    head = pull.get("head") or {}
    base = pull.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name")
    head_ref = head.get("ref")
    base_ref = base.get("ref")
    if head_repo != repository or not isinstance(head_ref, str) or not isinstance(base_ref, str):
        return []
    for promoted_base, prefix, back_merges in PROMOTIONS:
        if base_ref == promoted_base and head_ref.startswith(prefix):
            return list(back_merges)
    return []


def title_for(source: str, destination: str, number: int) -> str:
    return f"Merge {source} into {destination} after the promotion in #{number}"


def body_for(
    source: str, destination: str, number: int, *, app_token: bool, conflict: bool = False
) -> str:
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
    if not app_token:
        lines += [
            "",
            "> This pull request was opened with the workflow token, so GitHub did not start "
            "the required checks. Close and reopen it to start them, or set up the App token "
            f"described in [docs/ci.md]({DOCS_PATH}).",
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
    app_token: bool,
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
                "body": body_for(source, destination, number, app_token=app_token),
                "maintainer_can_modify": False,
            },
        )
    except ApiError as error:
        annotate(
            "error",
            f"could not open {source} into {destination}: {error}. If the message says Actions "
            "may not create pull requests, allow it under Settings > Actions > General, or set "
            f"up the App token described in {DOCS_PATH}.",
        )
        raise
    pull_number = created["number"]
    result = "opened"
    if mergeable(api, repo, pull_number, sleep) is False:
        api(
            "PATCH",
            f"repos/{repo}/pulls/{pull_number}",
            {"body": body_for(source, destination, number, app_token=app_token, conflict=True)},
        )
        annotate(
            "warning",
            f"#{pull_number} ({source} into {destination}) has conflicts; resolve them by "
            f"hand, see {DOCS_PATH}",
        )
        result = "opened, conflicts"
    if not app_token:
        annotate(
            "warning",
            f"#{pull_number} was opened with the workflow token, so its required checks did "
            "not start; close and reopen it, or set up the App token",
        )
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


def main(argv: list[str] | None = None, api: Api = gh_api) -> int:
    del argv
    repo = os.environ["GH_REPO"]
    event_path = os.environ["GITHUB_EVENT_PATH"]
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    targets = plan(event, repo)
    if not targets:
        annotate("notice", "not a merged promotion pull request; nothing to do")
        return 0
    number = event["pull_request"]["number"]
    app_token = os.environ.get("BACK_MERGE_TOKEN") == "app"
    rows: list[dict[str, str]] = []
    failed = False
    for source, destination in targets:
        try:
            rows.append(back_merge(api, repo, source, destination, number, app_token=app_token))
        except ApiError as error:
            failed = True
            annotate("error", f"{source} into {destination}: {error}")
            rows.append({"back_merge": f"{source} into {destination}", "result": "failed"})
    write_summary(rows)
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
