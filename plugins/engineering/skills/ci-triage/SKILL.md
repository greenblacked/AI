---
name: ci-triage
description: "Triage a red CI pipeline in a fixed order: check whether main is already broken before blaming the PR, locate the failing step from check-run annotations and --log-failed instead of whole logs, classify into exactly one of real / flake / infra / config-permission / dependency-drift, confirm with one cheap experiment, bisect only if that was inconclusive, then remediate under an explicit quarantine and retry policy. Use this skill whenever a build, pipeline, workflow, job or check is failing and someone wants to know why — including casual phrasings like \"CI is red\", \"the build broke\", \"this test keeps failing\", \"my PR is blocked\", \"is this a flake?\", \"the runner died\", or \"can we just re-run it\". Covers GitHub Actions and Jenkins. Do not use it for authoring a new pipeline, for debugging an application bug that CI is only reporting, or for running a production incident."
---

# CI Triage

Good triage ends with a named class, one piece of evidence for that class, and a remediation at the altitude of the cause. It does not end with green.

CI triage goes wrong in the same four ways every time. Someone reads a 40,000-line log looking for the word "error" when the platform already extracted the failure into an annotation. Someone hits "Re-run all jobs" first, which destroys both the evidence and the flake statistic that would have proved it was a flake. Someone debugs a PR for an hour before noticing that main was already red and the PR never had a chance. And someone "fixes" a nondeterministic test by retrying it, which converts a measurable defect into an untracked tax on every future run. The order below exists to make each of those impossible.

## Scope

Use for: a failing GitHub Actions or Jenkins run, a check blocking a PR, a suspected flake, a runner or registry failure, a dependency-drift break, a decision about whether to retry, quarantine, pin, or revert.

Do not use for: writing a new pipeline, tuning build speed on a green pipeline, application debugging where CI is only the messenger, or a live production incident.

## Hard gates

These are the rules that make the procedure durable. Breaking one invalidates the triage, not just slows it.

1. Check main before reading a single log line. Never triage a PR against a red baseline.
2. Read the check-run annotations before raw logs. They are the pre-extracted error surface.
3. Land on exactly one class. "Probably flaky but maybe the change" is not a classification, it is a decision you have not made.
4. Never bisect a nondeterministic failure. Quarantine first, bisect second — bisect assumes a deterministic predicate and will confidently return a wrong commit without one.
5. Never retry a non-idempotent step. Deploys, migrations, `terraform apply`, package publishes.
6. `continue-on-error: true` never goes on a required check. It converts a red signal into a silent one, which is strictly worse than red.
7. Every job carries `timeout-minutes:`. A hung job burns runner minutes until the 6-hour platform default and teaches the team that CI is slow rather than broken.

## Workflow

### 0. Is main red too?

Before anything else. This is the highest-value 60 seconds in the procedure:

```bash
gh run list --workflow=ci.yml --branch=main --limit=20 \
  --json conclusion,headSha,createdAt,displayTitle
```

If recent main runs are failing, this is not the PR's fault. Stop triaging the PR. Own it as a build-break: freeze merges, identify the first red SHA on main, and page the author of the change between the last green and the first red. A PR author debugging their own diff against a broken baseline is the single most expensive wasted hour in CI.

If main is green but only *sometimes*, you already have your answer for the PR too — see the flake path in step 2.

### 1. Locate the failing step

Never read the whole log. Work from most-structured to least:

```bash
# 1. Structured annotations first — the pre-extracted error surface.
gh api repos/{owner}/{repo}/commits/{sha}/check-runs --jq '.check_runs[] | select(.conclusion=="failure") | {id, name}'
gh api repos/{owner}/{repo}/check-runs/{check_run_id}/annotations

gh run view <run-id> --verbose           # 2. which step failed first, and step durations

# 3. Only the failed steps' logs.
gh run view <run-id> --log-failed
gh run view <run-id> --job <job-id> --log-failed
```

Read the last 50 lines of the failing step before the first 50. The proximate error is near the end; the cause is usually 200 lines above it in the same step, not in a different job.

Note the runner image and the step that failed *first* — a later step failing because an earlier one left no artifact is a symptom, not the failure.

### 2. Classify into exactly one bucket

**(A) real failure** — the change broke something. **(B) flake** — nondeterministic at a fixed SHA. **(C) infra/runner** — the machine, disk, network, or registry. **(D) config/permission** — the workflow definition or token scope. **(E) dependency drift** — an input moved without the diff moving.

Decode table. Match the log signal, take the class, do the action:

| Log signal | Class | Action |
| --- | --- | --- |
| `The runner has received a shutdown signal` / unexplained mid-step cancel | infra (spot preemption) | Retry once. Escalate to the runner owner if it repeats within a day — a preemption rate above a few percent is a capacity problem, not luck. |
| `No space left on device` | infra | Add a disk-reclaim step before the build; check for an artifact or Docker layer that grew. |
| `toomanyrequests` / HTTP 429 from a registry | infra (rate limit) | Authenticate the pull, or mirror the image into an internal registry. Anonymous Docker Hub pulls from shared runner IPs will keep doing this. |
| `Resource not accessible by integration` | permission | A scope is missing from the job's `permissions:` block. Add the one scope, not `write-all`. |
| `Input required and not supplied: token` | config | Fork PRs get no secrets. Move the secret-requiring work off `pull_request` or gate it on the same-repo condition. |
| `Permission to ... denied to github-actions[bot]` | permission | Needs `contents: write`; also check branch protection, which the token does not bypass. |
| `refusing to allow a GitHub App to create or update workflow` | permission | The token cannot touch `.github/workflows/`. Needs a PAT or App with `workflows` scope. |
| `npm ERR! ERESOLVE` / checksum or integrity mismatch / a new transitive major | dependency drift | Pin it. Use `npm ci`, never `npm install`, in CI — `npm install` rewrites the lockfile and makes the build a moving target. |
| Green at the same SHA yesterday, red today, no diff | dependency drift | Diff the lockfile, base image digest, and action tags against the last green run. |
| The same test fails on fewer than 100% of runs at an identical SHA | flake | Quarantine. Do not just retry — a retry hides the defect and deletes the evidence. |
| `Connection refused` to a `services:` container in the first seconds of a step | flake (readiness race) | Replace with a wait-for-health loop. `sleep 5` is the same race with a longer fuse. |
| `Timeout` / `Element not found` in a browser or E2E suite, intermittent | flake (timing) | Quarantine, then fix the wait condition. Raising the timeout postpones it. |
| A deterministic assertion diff that reproduces locally at the same SHA | real | Fix the code. |
| `OOMKilled` / exit 137 | infra or real | Both. Larger runner unblocks now; a memory regression in the diff is still a real failure. Check whether the last green run's peak was already near the limit. |

If two rows match, the more specific one wins and the other is a consequence. If none match, you are in step 3 without a hypothesis — say so rather than guessing.

### 3. Confirm with one cheap experiment

Exactly one, chosen by the class you picked. This is what separates a classification from a guess.

| Class | The experiment | Reads as confirmed when |
| --- | --- | --- |
| flake | Re-run the same job at the same SHA, 3-5 times. `gh run rerun <run-id> --failed` | It passes at least once with no code change. |
| infra | Re-run on a different runner label, or a different runner in the pool. | It passes elsewhere with the same SHA and same image. |
| config / permission | Diff the workflow file against the last green run: `git diff <last-green-sha>..HEAD -- .github/workflows/` | The diff contains the trigger, `permissions:`, or secret reference in question. |
| dependency drift | Diff the lockfile and pinned digests: `git diff <last-green-sha>..HEAD -- package-lock.json go.sum poetry.lock` — and if the lockfile is unchanged, that is itself the finding: the input moved outside the repo. | A version, digest, or floating tag moved. |
| real | Reproduce locally at the same SHA. | It fails locally, deterministically. |

Record the result before acting on it. "Passed 1 of 5 at the same SHA" is a datum with a quarantine policy attached; "seemed flaky" is not.

### 4. Bisect — only if step 3 was inconclusive

Bisect assumes a deterministic good/bad predicate. If step 3 showed nondeterminism, quarantine first and bisect afterwards against a stabilized test, or you will bisect noise and get a confident wrong answer.

```bash
git bisect start <known-bad-sha> <known-good-sha>
git bisect run ./scripts/bisect-probe.sh
```

The probe's exit code is the contract: `0` = good, `1`-`127` except `125` = bad, `125` = skip this commit as untestable (broken build, missing dependency). Anything else aborts the bisect. Guard against residual flakiness by requiring the test to fail on all three attempts before calling a commit bad:

```bash
#!/usr/bin/env bash
set -uo pipefail
npm ci --prefer-offline || exit 125   # can't build this commit -> skip, not bad
for _ in 1 2 3; do
  npx jest path/to/suspect.test.ts && exit 0   # any pass means good
done
exit 1
```

Bisecting CI-only failures that do not reproduce locally is possible but expensive — push each candidate SHA to a branch and let the workflow run. Budget it deliberately; often the workflow diff in step 3 is cheaper.

### 5. Remediate at the right altitude

| Class | Remediation | Not this |
| --- | --- | --- |
| real | Fix the code, or revert the PR if it already merged. | Retry, or lower the assertion. |
| flake | Quarantine under the policy below, with an owner and an SLA. | `retries: 3`, or deleting the assertion. |
| infra | Fix the step (disk reclaim, authenticated pull, health-check wait) and file the capacity or image issue upstream. | Blanket runner-level retry, which hides the capacity problem you are being billed for. |
| config/permission | Add the one missing scope or fix the trigger, and check whether other workflows share the defect. | `permissions: write-all`. |
| dependency drift | Pin the version or digest, and add the pin to whatever renovates dependencies so it is upgraded deliberately. | Deleting the lockfile. |

If the fix is not yours to make, say who owns it and what unblocks the queue in the meantime. Reverting a merged PR to unblock everyone is a normal, cheap, non-punitive action — treat it as the default when main is red and the fix is not obvious inside ten minutes.

### 6. Record what it was

One line per triage, into whatever tracks CI health:

```text
run: <url>  class: A|B|C|D|E  evidence: <the step-3 result>  action: fix|quarantine|pin|revert  change-failure: yes|no
```

Get the last field right. CI redness is **not** change failure rate. Change failure rate counts deployments to production that caused degraded service requiring a hotfix, rollback, or patch — a red pre-merge check is CI-only and does not count. Reporting CI redness as change failure rate inflates the metric and makes the team look worse the more they test.

DORA renamed the recovery metric in the 2024 report: mean time to restore / MTTR is now **failed deployment recovery time**, deliberately narrowed to service impairment caused by a change rather than by any outage. 2024 benchmarks for change failure rate: elite around 5%, low around 40%. See `references/flake-policy.md` for the full metric definitions.

## Quarantine policy

Flakes need a policy, not a judgment call per test, because the per-test judgment always resolves to "retry it for now."

**Entry.** A test qualifies when either: it produced two different outcomes at the same SHA within 14 days, or its failure rate exceeds 1% over its last 100 runs. One weird failure is not enough; a second one at the same SHA is.

**Effect.** A quarantined test still runs and its result is still recorded — it just does not block the merge. A quarantine that stops executing the test is a deletion with extra steps, and you lose the signal that would tell you it is fixed.

**Owner.** Auto-assign from CODEOWNERS on the test's path at quarantine time. An unowned quarantined test is a permanent one.

**Exit.** 50 consecutive green runs returns it to blocking. Fewer than that and you re-quarantine it next week.

**SLA.** 14 days. At day 14 the test is deleted, not extended. This is the load-bearing clause: without a deletion deadline the quarantine list is an append-only log of tests nobody trusts and nobody removes. A deleted flaky test and a permanently-quarantined flaky test provide identical coverage; only one of them is honest about it.

**Cap.** Cap the quarantine list — 1% of the suite, or a flat number the team picks once. Hitting the cap is a stop-the-line event: no new quarantines until the list drains. The cap is what stops quarantine from becoming the default response to every red run.

Grounding: Google reported flaky tests as roughly 16% of all test failures, taking about 1.5x longer to fix than ordinary failures. Flakes are not a rounding error, and they are more expensive per unit than real bugs.

## Retry hygiene

Retries are legitimate for exactly three things: network and registry fetches, infra-class steps, and tests explicitly marked as known flakes. Everything else is off-limits.

- Never retry a non-idempotent step — deploys, database migrations, `terraform apply`, package publishes. A retried publish is a duplicate artifact; a retried migration is a corrupted schema.
- Cap attempts, always. Two or three. An uncapped retry loop turns a hard failure into a timeout, and a timeout is harder to diagnose than the original error.
- Emit a metric per attempt, tagged with job and step. A retry that is not counted is a bug you have agreed never to fix — the whole point of counting is that the aggregate becomes visible when no individual run is annoying enough to investigate.
- No `continue-on-error: true` on a required check, ever. It makes a broken check report success.
- Retry the narrowest thing that failed. Retrying the whole job to work around one flaky `curl` costs the full build every time and buries the signal.

## Local reproduction

Read the **"Set up job"** block at the top of the log first. It names the runner image and version (`Runner Image: ubuntu-24.04`, plus an image version). Reproducing on a different image is not reproducing.

```bash
gh run rerun <run-id> --failed --debug   # re-run failed jobs with runner debug logging on
gh run download <run-id>                 # pull artifacts down
```

`act` runs workflows locally in Docker and is genuinely useful for step ordering and expression evaluation. Its limits are not cosmetic: no `services:` parity, no OIDC, different images than the hosted runners, and partial support for some contexts. **A green `act` run does not clear a red CI.** Use it to shorten the edit loop, then confirm on the real runner.

For a failure that only exists on the runner, add a temporary interactive shell gated so it can never fire on a green run:

```yaml
- name: Debug shell on failure
  if: ${{ failure() }}
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 15
  with:
    limit-access-to-actor: true
```

Remove it in the same PR that fixes the bug. An ungated or unlimited tmate step is a remote shell on a machine holding your secrets.

## Jenkins equivalents

The classification is identical; only the surfaces change.

- **Failing stage:** Blue Ocean's pipeline view, or the classic **Pipeline Steps** page (`/job/<name>/<build>/flowGraphTable/`), which shows per-step status and links straight to that step's log fragment. This is the `--log-failed` equivalent — do not open Console Output and scroll.
- **Fast iteration:** the **Replay** link on a build re-runs it with an editable copy of the Jenkinsfile, without a commit. It is the fastest way to test a pipeline-config hypothesis, and it is also why pipeline fixes go untracked — land the change in the Jenkinsfile once Replay confirms it.
- **Infra class:** check the agent/node the build ran on, executor availability, and workspace disk. `No space left on device` on a long-lived agent usually means stale workspaces, not a big build.
- **Config class:** diff the Jenkinsfile against the last green build; check credential bindings and folder-level credential scope, which is where the `Input required` equivalent lives.
- **Flake class:** the JUnit plugin's per-test history graph gives you the same "fails on fewer than 100% of runs at the same SHA" evidence. The quarantine policy above applies unchanged.

## Output format

Report triage in this shape. It front-loads the answer and makes the evidence auditable:

```markdown
## Verdict
[Class A-E, one sentence. Whether main is healthy.]

## Evidence
[The annotation or log line that decided it, quoted. The step-3 experiment and its result.]

## Cause
[What actually happened, one paragraph.]

## Action
[fix / quarantine / pin / revert — with the exact change or command. Owner if not you.]

## Unblocking now
[What the PR author or the team does in the next five minutes. Omit if the action above already does it.]

## Follow-up
[Quarantine entry with owner and SLA date, capacity ticket, pin to renovate. Omit if none.]
```

## Anti-patterns

**Reading the whole log.** Costs 10-20 minutes and finds the wrong "error" — build logs are full of the word. `--log-failed` and annotations get you there in under a minute.

**Hitting "Re-run all jobs" first.** The most expensive click in CI. It destroys the evidence *and* the flake statistic: you can no longer tell whether the same SHA produced two different outcomes, which is the exact datum the quarantine policy needs. Classify first, re-run as the step-3 experiment.

**Triaging a PR without checking main.** An hour of debugging a diff that was never the problem, and the real build-break stays unowned that whole hour.

**`continue-on-error: true` to unblock the team.** Converts a red signal into a silent one. The check now reports success while testing nothing, and it stays that way for months because nothing surfaces it.

**Blanket runner-level retries.** Hides both flake rate and infra failure rate, the two numbers that would justify fixing either. Costs runner minutes proportional to the problem you can no longer see.

**Bisecting a nondeterministic failure.** Returns a confidently wrong commit, which is worse than no answer because someone will act on it. Quarantine, stabilize, then bisect.

**`pull_request_target` with a checkout of the PR head.** Executes untrusted fork code with a write-scoped token and access to secrets. This is the standard Actions repo-takeover path, not a theoretical one. Use `pull_request`, and if you truly need the token, split the privileged work into a separate `workflow_run` job that never checks out fork code.

**Unpinned action tags.** `@v3` is a mutable ref pointing at whatever the maintainer moved it to. It makes builds non-reproducible and puts a supply-chain compromise one force-push away. Pin to a full commit SHA with the version in a trailing comment.

**No `permissions:` block.** The job inherits the repository default, which may be write-all. Set a `permissions: {}` default at workflow level and grant per-job.

## Reference files

- `references/github-actions.md` — read when working a GitHub Actions failure: annotation and log APIs, debug logging, workflow-command annotation syntax, the `permissions:` scope table, and the fork-PR secrets rules.
- `references/flake-policy.md` — read when classifying a flake, writing the quarantine entry, or reporting CI health: quarantine mechanics, flake-rate and retry metric definitions, and the DORA framing for what does and does not count as a change failure.
