# GitHub Actions: reading a failure

Everything here is for locating and explaining a failure on GitHub-hosted or self-hosted
Actions runners. Load it during steps 1-3 of the triage workflow.

## Contents

- [Finding the run and the failing job](#finding-the-run-and-the-failing-job)
- [Check-run annotations: the structured error surface](#check-run-annotations-the-structured-error-surface)
- [Reading logs without reading all of them](#reading-logs-without-reading-all-of-them)
- [Debug logging](#debug-logging)
- [Emitting your own annotations](#emitting-your-own-annotations)
- [The permissions block](#the-permissions-block)
- [Fork PRs, secrets, and pull_request_target](#fork-prs-secrets-and-pull_request_target)
- [Comparing a red run to the last green one](#comparing-a-red-run-to-the-last-green-one)
- [Timeouts, concurrency, and cancellation](#timeouts-concurrency-and-cancellation)

## Finding the run and the failing job

```bash
# Recent runs of one workflow on one branch.
gh run list --workflow=ci.yml --branch=main --limit=20 \
  --json databaseId,conclusion,headSha,createdAt,displayTitle

# Runs for a PR's head branch.
gh run list --branch "$(gh pr view 1234 --json headRefName --jq .headRefName)" --limit 10

# Only failures, with the run id you need for everything else.
gh run list --status failure --limit 20 --json databaseId,workflowName,headSha
```

`gh run view <run-id> --verbose` prints per-job, per-step status and duration. Use it to
find which step failed **first** — a later step failing for lack of an artifact is a
symptom of the earlier one.

`gh run view <run-id> --exit-status` exits non-zero if the run failed, which is what you
want inside a bisect probe or a polling script.

`gh run view <run-id> --attempt 1` reads a specific attempt. After someone has already
clicked re-run, attempt 1 is where the original evidence still lives.

## Check-run annotations: the structured error surface

Annotations are what the platform (or an action such as a test reporter or a linter)
extracted from the run: file, line, level, title, message. Reading them first is the
single largest time saving in triage, because a good annotation is the whole answer.

```bash
# 1. Failing check runs for a commit.
gh api repos/{owner}/{repo}/commits/{sha}/check-runs \
  --jq '.check_runs[] | select(.conclusion=="failure") | {id, name, details_url}'

# 2. Annotations for one of them.
gh api repos/{owner}/{repo}/check-runs/{check_run_id}/annotations \
  --jq '.[] | {path, start_line, annotation_level, title, message}'
```

The endpoint is `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations`. It
needs `checks: read`. It paginates — add `--paginate` when a linter has produced many.

Annotation quality varies by tooling. A repo with no annotations at all is usually a repo
that has not wired a test reporter, which is worth fixing once and benefiting from forever.

## Reading logs without reading all of them

```bash
gh run view <run-id> --log-failed              # only failed steps, all jobs
gh run view <run-id> --job <job-id> --log-failed
gh run view <run-id> --log | grep -n -i -E 'error|fail' | tail -40   # last resort
```

`--log-failed` is the default move. `--log` downloads the whole archive and is only
justified when you need the sequence of a *successful* step that set up the failure.

Log-reading order that actually works:

1. The last 50 lines of the failing step — the proximate error.
2. The first 30 lines of the failing step — what it was configured to do.
3. The **"Set up job"** block — runner image and version, the labels that matched, the
   token permissions granted to this job. Reproducing on a different image is not
   reproducing.
4. Only then, the 200 lines above the proximate error.

Timestamps in the raw log are UTC ISO-8601 at the start of each line. A step that failed
0.2s after it started is a config or permission failure; a step that failed at minute 59
of a 60-minute timeout is an infra or hang failure. Duration is a classification signal.

## Debug logging

Two levels, both off by default:

| Variable | Effect |
| --- | --- |
| `ACTIONS_STEP_DEBUG` = `true` | Verbose logging from steps and actions (`core.debug` output). |
| `ACTIONS_RUNNER_DEBUG` = `true` | Runner and worker diagnostic logs, added to the log archive. |

Set them as repository/environment **variables** (or secrets) to enable persistently, or
enable them for one re-run only:

```bash
gh run rerun <run-id> --failed --debug
```

Prefer the per-run form. Leaving step debug on repo-wide inflates every log archive and
raises the chance of a secret-adjacent value being printed by a third-party action.

## Emitting your own annotations

When a tool fails without producing annotations, make it produce them. Workflow commands
written to stdout are parsed by the runner:

```bash
echo "::error file=src/app.ts,line=42,col=5,endColumn=12,title=Type error::Expected string, got number"
echo "::warning file=Dockerfile,line=3::Base image tag is not pinned to a digest"
echo "::notice::Cache miss; full rebuild"
```

Parameters: `file`, `line`, `col`, `endLine`, `endColumn`, `title`. All optional; the text
after `::` is the message. Related commands worth knowing during triage:

```bash
echo "::group::Dependency tree"   # collapsible section
echo "::endgroup::"
echo "::add-mask::$SOME_VALUE"    # redact a value from all subsequent log output
```

`add-mask` is the fix when triage requires printing something that is adjacent to a
secret. Note that masking only applies after the command runs.

## The permissions block

`GITHUB_TOKEN` permissions are per-job. Specifying any scope sets every unspecified scope
to `none`, which is the behavior you want: declare a `permissions: {}` default at
workflow level and grant the minimum per job.

| Scope | Grant it when the job needs to |
| --- | --- |
| `actions` | Read/cancel workflow runs, download artifacts from other runs |
| `attestations` | Generate build provenance attestations |
| `checks` | Read or write check runs, including reading annotations |
| `contents` | Read the repo (`read`); push commits, tags, releases (`write`) |
| `deployments` | Create or update deployments |
| `id-token` | Request an OIDC token for keyless cloud auth — required for OIDC, and `write` |
| `issues` | Comment on or label issues |
| `packages` | Pull or publish to GitHub Packages / GHCR |
| `pages` | Deploy GitHub Pages |
| `pull-requests` | Comment on, label, or update PRs |
| `security-events` | Upload SARIF / code-scanning results |
| `statuses` | Set commit statuses |

Decoding failures:

- `Resource not accessible by integration` — a scope is missing. Identify the API call in
  the log and grant that one scope. `write-all` makes the message go away and makes every
  future compromise worse.
- `Permission to <repo> denied to github-actions[bot]` — needs `contents: write`. If it is
  already set, the block is branch protection, which `GITHUB_TOKEN` does not bypass.
- `refusing to allow a GitHub App to create or update workflow ... without workflows permission`
  — nothing scoped by `permissions:` can write `.github/workflows/`. Needs a PAT or a
  GitHub App installation token with the `workflows` scope.
- OIDC failures (`Unable to get ACTIONS_ID_TOKEN_REQUEST_URL`) — `id-token: write` missing.

## Fork PRs, secrets, and pull_request_target

A `pull_request` run from a fork gets a read-only token and **no secrets**. This is the
cause of `Input required and not supplied: token` and of "works on branch, fails on the
contributor's PR". It is a security boundary, not a bug.

Correct handling, in order of preference:

1. Make the job not need the secret (run the linter, skip the upload).
2. Gate the secret-requiring step on the PR being same-repo:
   `if: github.event.pull_request.head.repo.full_name == github.repository`
3. Split the privileged work into a separate `workflow_run`-triggered workflow that
   consumes artifacts from the untrusted run and never checks out fork code.

`pull_request_target` runs with a write-scoped token and full secret access in the context
of the base repo. Combining it with `actions/checkout` at `github.event.pull_request.head.sha`
executes attacker-controlled code with those credentials. That is the standard Actions
repo-takeover path. If a workflow you are triaging does this, the finding is a security
issue and outranks the CI failure you came for.

## Comparing a red run to the last green one

Most config and drift failures are visible in a diff against the last green run:

```bash
GREEN=$(gh run list --workflow=ci.yml --branch=main --status=success --limit=1 --json headSha --jq '.[0].headSha')
git diff "$GREEN"..HEAD -- .github/workflows/       # config drift
git diff "$GREEN"..HEAD -- package-lock.json go.sum poetry.lock Cargo.lock
git diff "$GREEN"..HEAD -- Dockerfile               # base image moved
```

If all of those are empty and the run still went from green to red, the input that moved
is outside the repo: a floating action tag (`@v3`), a mutable base image tag (`:latest`,
`:20`), a registry, a hosted-runner image update, or an upstream service. Runner images
are versioned in the "Set up job" block — comparing that line between the green and red
runs identifies a runner-image rollout in about ten seconds.

## Timeouts, concurrency, and cancellation

- `timeout-minutes:` belongs on every job, and on any step that talks to the network. The
  platform default is 360 minutes, which is a billing incident rather than a timeout.
- An unexplained cancellation is usually one of three things: a `concurrency` group with
  `cancel-in-progress: true` (a newer push superseded this run), a manual cancel, or spot
  preemption (`The runner has received a shutdown signal`). The first two are not failures
  and should not be triaged as such — check the run's `conclusion` field, which reads
  `cancelled`, not `failure`.
- `if: ${{ failure() }}` runs a step only when a previous step failed; `always()` runs it
  even on cancellation. Diagnostic steps want `failure()`. Cleanup steps want `always()`.
  Using `always()` for a debug shell means it also fires on cancelled runs and holds a
  runner hostage.
