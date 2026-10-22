---
name: srm-diagnosis
description: "Find why an experiment's traffic split differs from its design (sample ratio mismatch) and decide what to do with the result: confirm with a chi-square test at p below 0.001 on randomisation units, locate the stage where the arms diverge by counting at assignment, exposure, first event and the analysis table, slice by day, platform and browser, then test causes in a fixed order — bot filtering by arm, redirects or load time, cache or CDN serving, triggering logic, logging loss on one arm — and discard the result until fixed rather than reweighting. Use when someone says the split came out 51/49, the SRM check failed, treatment has fewer users than control, or asks whether an uneven split matters. Not for reading out a healthy test (experiment-readout), planning one (experiment-design) or a time-window marketplace test (switchback-test-design)."
allowed-tools: Read, Glob, Grep
---

# SRM Diagnosis

The diagnosis is done when you can name the mechanism that removed or added units in one arm, show the stage where the counts first diverge, point to the fix, and have stated that the affected result is not to be used — with a rerun planned on a fresh randomisation.

The usual failure is treating a 50.6/49.4 split as a rounding curiosity, or "correcting" it by reweighting the arms back to 50/50. A sample ratio mismatch means the arms no longer hold the populations randomisation created. The units that went missing are almost never missing at random — they are the slow-loading, the bot-flagged, the ones who bounced before a beacon fired — so reweighting restores the counts and keeps the bias. The effect estimate from such a test can be wrong in either direction and by more than the effect itself.

## Scope

Use for: a failed sample ratio check; a split visibly off its design; deciding whether a small imbalance matters; finding which pipeline stage loses units; setting up a daily ratio monitor so the next one is caught in days.

Do not use for: reading out a test whose split is healthy, which is `experiment-readout`; designing the next test, which is `experiment-design`; a switchback or geo test, where the units are windows or regions and the check is against the schedule, which is `switchback-test-design`.

This skill pre-approves no shell command. It reads change logs, experiment configs and query output, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Confirm it is a mismatch, on the right units

Count distinct randomisation units per arm — users if users were randomised, never events or sessions, which vary with behaviour the treatment changes. Run a chi-square goodness-of-fit test against the designed shares (0.9/0.1 for a 90/10 test, not 0.5/0.5). Flag at p < 0.001. A small relative imbalance is significant at scale: 50.3/49.7 on two million users gives a chi-square of 72, and is a real defect, not noise.

Read `references/srm-queries.md` for the test in standard-library Python and the counting queries.

### 2. Stop the readout

Tell the experiment's owner now that the result is blocked, before anyone quotes it. Do not report the effect "with a caveat" or analyse the arms as they stand. The decision the test was meant to inform waits for a clean rerun.

### 3. Find the stage where the arms diverge

Count units per arm at each stage the data passes through, from the same time window:

| Stage | Source | What a break here means |
| --- | --- | --- |
| Assignment | Bucketing service or assignment log | The hash, allocation or eligibility is wrong |
| Exposure | Server-side render or serve log | Assigned units did not receive their arm: redirects, errors, caching |
| First client event | Analytics or beacon pipeline | Client logging lost units in one arm |
| Analysis table | The table the readout reads | Bot filters, joins, deduplication or the trigger condition removed units |

The first stage where the ratio departs from the design is where the cause lives. If assignment is already off, no downstream investigation helps.

### 4. Slice the mismatch

Within the stage that breaks, compute the ratio and chi-square by day, platform, app version, browser, country, new or returning, logged-in or anonymous. A mismatch concentrated in one slice — one browser, one app version, the first two days — names the mechanism far faster than reasoning about the whole. A ratio that broke on a particular day usually matches a deploy, an allocation change or a filter change on that day; check the change log.

### 5. Test the causes in order

Work down this list, because it runs roughly from most common and cheapest to check to least:

1. **Bot filtering by arm.** Treatment changes behaviour — more clicks, faster navigation, a new endpoint — that the bot heuristic reads as automated, so one arm loses more units to filtering. Compare unit counts before and after the bot filter per arm.
2. **Redirects or load-time differences.** A treatment served through a redirect, or that loads slower, loses users who leave before the page renders and before the exposure event fires. Look at exposure-to-first-event drop-off per arm and by connection speed or device class.
3. **Cache or CDN serving.** A cached page serves one arm's variant to users assigned to the other, or a cache key that omits the arm makes one variant dominate. Check whether the served variant matches the assigned arm per request.
4. **Triggering logic.** The trigger condition depends on something the treatment changes (a component only treatment renders, a later page treatment users reach more often), so the triggered populations differ by construction. Recompute the trigger as it would fire in control.
5. **Logging loss on one arm.** The new code path drops or delays the event the readout keys on: a missing beacon, a renamed event, a client crash before flush. Compare server-side exposure counts with client-side event counts per arm.

Also rule out the less common: overlapping experiments that share a hash salt, an allocation changed mid-run while assignment stayed sticky, and identity merging (anonymous to logged-in) that moves units between arms. Read `references/cause-catalogue.md` for the signal, test and fix for each.

### 6. Fix, then rerun on a fresh randomisation

Fix the mechanism, then restart the test with a new salt so units do not carry the broken arm's experience into the rerun. Do not reweight the arms, impute the missing units, or analyse the healthy slices and call it a result: each assumes the missing units resemble the ones that stayed, which is exactly what a mismatch says is false. A slice analysis can suggest a hypothesis; it cannot support the decision.

After the fix, confirm on the rerun that every stage in step 3 keeps the designed ratio within the first days.

### 7. Make the next one loud

If the platform does not already do it, add a daily sample ratio check at p < 0.001 for every running test, computed on randomisation units at the analysis-table stage, with an alert to the experiment owner. Most mismatches are visible within the first days; one found at the readout date has cost the whole run.

## Output format

```markdown
## Mismatch
[Counts per arm, designed shares, chi-square, p.]

## Where it breaks
[Counts per arm at each stage; first stage that departs from the design.]

## Slice
[The slice(s) where the mismatch concentrates, with counts.]

## Cause
[Mechanism, the evidence for it, and the causes ruled out.]

## Fix and rerun
[The fix, who owns it, the new salt, and the rerun's start date.]

## Status of the original result
[Blocked; not to be quoted. Any slice analysis labelled as a hypothesis only.]
```

## Anti-patterns

**Reweighting to the designed split.** It fixes the counts and keeps the composition the mismatch created.

**Counting events instead of units.** Events per user vary with treatment, so an event-count imbalance is expected and a unit-count balance can hide behind it.

**Testing against 50/50 when the design was not.** A 90/10 test checked against equal shares flags every run and teaches people to ignore the check.

**Rerunning on the same salt.** Units that had the broken experience carry it into the rerun.

**Finding it at the readout.** A daily check catches most mismatches in the first days instead of after the full run.

## Reference files

- `references/srm-queries.md` — read at steps 1, 3 and 4: the chi-square test in standard-library Python, stage-by-stage counting SQL and the slice query.
- `references/cause-catalogue.md` — read at step 5: for each cause, the signal that points at it, the query or check that confirms it, and the fix.
