# Flake policy, CI metrics, and DORA framing

The operating rules for nondeterministic tests, the numbers that make CI health visible,
and the definitions that stop CI redness being misreported as a delivery metric. Load this
when classifying a flake, writing a quarantine entry, or reporting on CI health.

## Contents

- [Why flakes need a policy rather than judgment](#why-flakes-need-a-policy-rather-than-judgment)
- [Detecting a flake](#detecting-a-flake)
- [Quarantine policy](#quarantine-policy)
- [The quarantine record](#the-quarantine-record)
- [Common flake causes and their real fixes](#common-flake-causes-and-their-real-fixes)
- [Metric definitions](#metric-definitions)
- [DORA framing: what CI redness is and is not](#dora-framing-what-ci-redness-is-and-is-not)
- [Reporting template](#reporting-template)

## Why flakes need a policy rather than judgment

Judged case by case, every flake resolves to "retry it for now," because at the moment of
the decision the retry is cheap and the fix is not. The cost lands later and is paid by
everyone: a suite with a 1% per-test flake rate and 300 tests fails a clean run roughly
95% of the time, at which point the team stops reading CI results at all. That is the real
failure mode — not the wasted minutes, but the loss of the signal.

Google reported flaky tests as about 16% of all test failures, taking roughly 1.5x longer
to fix than ordinary failures, and found that when a test flips from pass to fail in their
post-submit CI it is a flake far more often than a genuine regression. A policy with a
deletion deadline is what converts that from a permanent tax into a bounded queue.

## Detecting a flake

The defining evidence is **two different outcomes at the same commit SHA**. Everything else
is inference.

```bash
# Same job, same SHA, five times. Any pass means nondeterministic.
for i in 1 2 3 4 5; do gh run rerun <run-id> --failed; sleep 90; done

# Outcome history for one workflow, to eyeball the pass/fail pattern.
gh run list --workflow=ci.yml --branch=main --limit=100 \
  --json headSha,conclusion,createdAt --jq '.[] | [.createdAt,.headSha[0:8],.conclusion] | @tsv'
```

Signals that point at a flake before you have run the experiment:

- Failure text mentions timing: `Timeout`, `Element not found`, `Connection refused`,
  `deadline exceeded`, `context canceled`.
- The failure moves between tests or between runs at the same SHA.
- The failure rate correlates with parallelism, runner load, or time of day.
- The test passes in isolation and fails in the suite (shared state or ordering).
- It fails only in CI, never locally (concurrency, clock, DNS, or a `services:` race).

Signals that point away from a flake: a deterministic assertion diff, a compile error, a
failure that reproduces locally on the first attempt every time.

## Quarantine policy

**Entry criterion.** Either of:

- two different outcomes recorded at the same SHA within the last 14 days, or
- a failure rate above 1% over the test's last 100 runs.

One odd failure does not qualify. Requiring the second occurrence prevents quarantine from
becoming the reflex response to any red run.

**Effect.** A quarantined test *still runs* and its result is *still recorded* — it simply
does not block the merge. Skipping it instead is a deletion with extra bookkeeping, and it
destroys the only data that could later prove it is fixed.

**Owner.** Auto-assigned from CODEOWNERS on the test's path at the moment of quarantine.
An unowned quarantined test is a permanent one; assignment is what makes the SLA mean
something.

**Exit criterion.** 50 consecutive green runs returns the test to blocking. A lower
threshold re-admits a 1%-flake test that got lucky.

**SLA.** 14 days from quarantine. At day 14 the test is **deleted**, not extended. This is
the load-bearing clause. Without it the quarantine list becomes an append-only record of
tests nobody trusts and nobody removes. A deleted flaky test and an indefinitely
quarantined flaky test give identical coverage; only one of them is honest about it, and
the honest one creates pressure to write a deterministic replacement.

**Cap.** Cap the list at roughly 1% of the suite, or a flat number the team agrees once.
Hitting the cap is a **stop-the-line event**: no new quarantines are accepted until the
list drains below the cap. The cap is the mechanism that stops quarantine from becoming
the default answer to every red run, and it forces the trade-off to be made explicitly by
a team rather than implicitly by whoever is on triage that day.

**Escalation.** A test that is quarantined a second time within 90 days of exiting
quarantine does not get another 14 days. Delete it and open a ticket for a deterministic
replacement — the second quarantine is evidence that the first fix addressed a symptom.

## The quarantine record

Keep it in the repo, next to the tests, in a format a script can read:

```yaml
# .ci/quarantine.yml  — cap: 1% of suite (currently 12 of 1,430)
- test: tests/e2e/checkout.spec.ts::applies promo code
  reason: readiness race against the payments stub container
  evidence: 3 of 10 runs failed at a1b2c3d on 2026-07-22
  owner: "@payments-team"          # from CODEOWNERS
  quarantined: 2026-07-22
  delete_after: 2026-08-05         # entry + 14 days, not negotiable
  issue: PLAT-4471
```

Enforce it in CI: a scheduled job that fails when any entry is past `delete_after`, or
when the list exceeds the cap. A policy nothing enforces is a comment.

## Common flake causes and their real fixes

| Cause | Symptom | Fix that holds | Fix that does not |
| --- | --- | --- | --- |
| Service readiness race | `Connection refused` in the first seconds of a step | Poll the health endpoint until ready, with a bounded deadline; use container health checks and `depends_on` conditions where available | `sleep 5` |
| Fixed waits in E2E | Intermittent `Element not found` | Wait on the condition (element state, network idle, explicit event) | Raising the timeout |
| Shared mutable state | Fails in the suite, passes alone | Isolate per test: fresh schema, unique namespace or prefix, no shared globals | Forcing serial execution |
| Test-order dependence | Fails only under a particular shard or seed | Fix the dependency; randomize order in CI so it stays fixed | Pinning the seed |
| Clock and timezone | Fails near midnight, month end, or a DST boundary | Inject a clock; freeze time in the test | Retrying until the hour changes |
| Real network calls | Fails when an upstream is slow | Stub at the boundary; keep real calls in a separate, non-blocking contract suite | A retry wrapper |
| Unordered collections | Assertion diff that varies between runs | Assert on sets, or sort before comparing | Re-running |
| Resource exhaustion under parallelism | Fails only at high concurrency, often `OOMKilled` / exit 137 | Bound concurrency, raise the limit deliberately, fix the leak | Reducing parallelism silently |

## Metric definitions

Define these once so the numbers mean the same thing in every conversation:

- **Flake rate (per test)** — distinct-SHA runs where the test produced both outcomes,
  divided by total runs of that test, over a rolling 100 runs.
- **Flake rate (per pipeline)** — runs that failed and then passed on re-run at the same
  SHA with no code change, divided by total runs. This is the number that predicts whether
  people trust CI.
- **Retry count** — attempts per job per run, emitted as a metric tagged with job and step.
  A retry that is not counted is a bug you have agreed never to fix: no single run is
  annoying enough to investigate, and without the aggregate nothing ever surfaces it.
- **Time to red-to-green on main** — first red run to next green run on the default branch.
  This is the build-break metric and it is the one that justifies a merge freeze.
- **Quarantine list size and age** — count, plus oldest entry's days-since-quarantine.
  Rising size with rising age means the SLA is not being enforced.
- **Mean time to triage** — failure to classification, not failure to fix. If this is
  above ten minutes, the problem is usually log-reading habits rather than difficulty.

## DORA framing: what CI redness is and is not

**Change failure rate** is the share of *deployments to production* that cause degraded
service requiring a hotfix, rollback, or patch. A red pre-merge check is CI-only. It never
reached production, so it does not count. Reporting CI redness as change failure rate
inflates the metric and produces the perverse result that a team looks worse the more
thoroughly it tests before merging.

In the **2024 DORA report** the recovery metric was renamed from mean time to restore /
MTTR to **failed deployment recovery time**, and narrowed deliberately: the old definition
did not distinguish a failure caused by a change from one caused by something external
such as a data-center outage. The new one measures only the time to restore service after
a change to production caused the impairment.

2024 benchmarks worth knowing when someone asks whether a number is good:

| Metric | Elite | Low |
| --- | --- | --- |
| Change failure rate | ~5% | ~40% |
| Failed deployment recovery time | under an hour | a week to a month |

So: track CI health with the CI metrics above, and track delivery with the DORA four. A
build-break on main belongs in "time to red-to-green on main". A bad deploy belongs in
change failure rate. Keeping them separate is what makes either of them actionable.

## Reporting template

For a weekly or per-incident CI health note:

```markdown
## CI health, week of YYYY-MM-DD
- Pipeline flake rate: X% (prev Y%)
- Main red-to-green: N incidents, median M minutes
- Quarantine: A tests (cap B), oldest C days, D past SLA
- Retries: E total attempts across F jobs; top offender: <job/step>

### Actions
- [ ] <the one thing that most reduces the number above>
```

Report the trend, not the absolute number alone. A 3% flake rate falling from 8% and a 3%
rate rising from 1% call for opposite responses.
