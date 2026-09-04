# Runbook, rollback and comms templates

The documents a cutover needs, in the shape they need to be in at 03:00 when the person
reading them is not the person who wrote them. Load this while writing the plan.

## Contents

- [What makes a runbook usable under pressure](#what-makes-a-runbook-usable-under-pressure)
- [Runbook header](#runbook-header)
- [Step template](#step-template)
- [Rollback runbook](#rollback-runbook)
- [The rollback deadline, calculated](#the-rollback-deadline-calculated)
- [T-minus schedule](#t-minus-schedule)
- [Comms templates](#comms-templates)
- [Worked example: hosting provider migration](#worked-example-hosting-provider-migration)
- [After the window](#after-the-window)

## What makes a runbook usable under pressure

- **Numbered steps, executed in order.** Not a checklist of things that need to happen.
- **One action per step.** If a step contains "and", it is two steps, and the second one is
  the one that gets skipped.
- **Real commands, filled in.** No placeholders except in one marked variables block at the
  top. A runbook containing `--cluster your-cluster-name` was never rehearsed.
- **An expected observation per step.** "Done" means someone saw the thing, not that a
  command exited zero.
- **An abort condition per step**, naming the rollback step to jump to.
- **UTC everywhere.** Participants are in several timezones and "2pm" is how two people
  join an hour apart.
- **Rehearsed durations, not estimates**, so elapsed time can be compared to plan mid-window.

## Runbook header

Everything environment-specific lives here and nowhere else, so a change of target is one
edit rather than a hunt through forty steps.

```markdown
# Cutover runbook: [old system] → [new system]
Window:              2026-04-18 01:00 – 05:00 UTC
Rollback deadline:   03:30 UTC (see calculation below)
Point of no return:  step 12 — first write accepted only by the new system

Keyboard:  @name          Clock and comms: @name          Decider: @name
Escalation: @name (owner, [system]), @name (DBA), vendor support [contract ID]
Channel:   #cutover-2026-04-18 (single channel; no DMs)

## Variables
OLD_HOST=api-old.internal.example.com
NEW_HOST=api-new.internal.example.com
LB_LISTENER_ARN=arn:aws:elasticloadbalancing:eu-west-1:1234:listener/app/prod/abc/def
DB_PRIMARY=pg-prod-01.internal
ZONE_ID=Z0123456789ABCDEFGHIJ
```

## Step template

```markdown
### Step N — [imperative, one action]
Owner:     @name
Duration:  [rehearsed measurement]  (plan cumulative: T+MM)
Command:   [exact, copy-pasteable]
Expect:    [the observation that means it worked, with numbers]
Abort if:  [condition] → go to rollback step R[n]
Notes:     [anything the operator needs that is not obvious from the command]
```

Two step types deserve extra care:

**Verification steps.** Give them their own number. A verification folded into the previous
step's "Expect" line is skipped when the previous step feels obviously fine.

```markdown
### Step 9 — Verify reconciliation before releasing writes
Owner:     @name (DBA)
Duration:  6 min (rehearsed: 5m20s)
Command:   ./scripts/reconcile.sh --old $DB_PRIMARY --new $NEW_DB --tables orders,payments,users
Expect:    counts equal on all three tables; checksum equal; sampled diff 0 rows
Abort if:  any difference in orders or payments → go to rollback step R2, do not release writes
```

**The point-of-no-return step.** Mark it, and require the decider to confirm in the channel
before the keyboard runs it.

```markdown
### Step 12 — POINT OF NO RETURN: accept writes on the new system
Owner:     @name (keyboard) — requires explicit "GO" from @decider in channel
Duration:  1 min
Expect:    write success rate on new stack above 99.9% within 60s
Abort if:  cannot be aborted after this step; rollback from here costs [duration] and
           requires replaying writes made since. Confirm the clock against the rollback
           deadline before running.
```

## Rollback runbook

A separate document with the same structure. It is not "the steps above in reverse": the
inverse of a step is often a different operation with different risks, and any data written
since the switch has to be dealt with explicitly.

```markdown
# Rollback runbook: [new system] → [old system]
Total rehearsed duration: 38 min
Valid until: the rollback deadline, 03:30 UTC

### R1 — Announce rollback
Owner: @clock. Post decision, time, and expected completion. Update the status page.

### R2 — Return traffic to the old stack
Owner: @keyboard
Command: aws elbv2 modify-listener --listener-arn $LB_LISTENER_ARN \
           --default-actions file://weights-100-0.json
Expect:  old-stack RPS back to baseline within 60s; new-stack RPS to zero
Duration: 3 min (rehearsed: 2m10s)

### R3 — Freeze writes on the new system
...

### R4 — Replay writes made on the new system since step 12 back to the old one
Owner: @dba
Command: ./scripts/replay.sh --from '2026-04-18T02:41:00Z' --into $DB_PRIMARY
Expect:  replay report shows 0 conflicts; reconciliation green in both directions
Duration: 20 min (rehearsed: 17m, with 4.2k rows)
Notes:   this is the step that makes the rollback expensive and it is why the deadline exists.

### R5 — Verify and stand down
...
```

Rehearse the rollback from the far side of the point of no return, with data written on the
new system. A rollback that has only been rehearsed from before the point of no return has
not exercised the step that actually matters.

## The rollback deadline, calculated

```text
rollback deadline = window end
                  − rollback duration (rehearsed)
                  − margin for the rollback going badly (50–100% of its duration)
                  − time needed to verify the old system afterwards
```

Worked: window ends 05:00; rollback is 38 minutes rehearsed; margin 40 minutes; verification
15 minutes. Deadline = 05:00 − 1h33 ≈ 03:30 UTC.

Announce it at the start of the window, restate it at each update within 30 minutes of it,
and do not reopen it during the window. Its whole function is to move the decision to a
time when nobody was invested in the outcome.

## T-minus schedule

| When | What | Owner |
| --- | --- | --- |
| T-14d | Runbook drafted, roles named, window proposed, stakeholders informed | Lead |
| T-10d | Go/no-go criteria written and agreed | Decider |
| T-7d | Full rehearsal against staging or a restored copy, timed | Keyboard |
| T-7d | DNS TTLs lowered (48h+ before the window, longer if the old TTL was long) | Networking |
| T-5d | Rollback rehearsed from past the point of no return | Keyboard, DBA |
| T-3d | Runbook updated with rehearsed timings; window confirmed or moved | Lead |
| T-2d | Customer notice sent; support briefed; status page draft prepared | Comms |
| T-1d | Change freeze begins on both systems; backups taken and a restore verified | Ops |
| T-2h | Go/no-go call; decision recorded with a UTC timestamp | Decider |
| T-0 | Window opens; clock owner posts the opening message | Clock |
| T+window | Bake period begins; old system stays warm and reversible | Ops |
| T+bake | Decommission, as a separate scheduled change | Owner |

Moving the window is a normal outcome of the T-2h call. A no-go that costs a rescheduled
Saturday is cheaper than a go that overruns into Monday.

## Comms templates

**Customer notice, T-2d.** What, when in their local terms, expected impact, what to do if
affected, where to watch.

```text
Scheduled maintenance: Saturday 18 April, 01:00–05:00 UTC.
[Product] will be read-only for approximately 40 minutes within that window.
No action is needed. Live status: status.example.com
```

**Window opening.**

```text
[UTC 01:00] Cutover starting: [old] → [new]. Window closes 05:00 UTC.
            Rollback deadline 03:30 UTC. Point of no return is step 12.
            Keyboard @name · Clock @name · Decider @name
            Updates here every 15 minutes, including when nothing has changed.
```

**Periodic update — post it even when nothing has changed.**

```text
[UTC 02:15] Step 7 of 19. On plan (+4 min). 10% traffic on new stack, error rate nominal.
            Point of no return not yet passed. Next update 02:30.
```

**Decision.**

```text
[UTC 03:28] DECISION (@decider): ROLL BACK. Step 14 incomplete at the 03:30 deadline.
            Executing rollback runbook, rehearsed 38 min, expected complete by 04:10.
```

**Close.**

```text
[UTC 04:05] Cutover complete. Traffic 100% on new stack since 03:40.
            Reconciliation green. Bake period runs to 25 April; old stack stays warm.
            Decommission scheduled 28 April as change CHG-1234.
```

## Worked example: hosting provider migration

Nineteen steps, four hours, one freeze. The shape rather than the detail:

1-3. Announce; enable read-only mode on the old system; confirm write rate is zero.
4-6. Final delta sync; verify sync completion; run reconciliation (counts, checksums, sample).
7-8. Bring the new stack to full capacity; run synthetic checks against it directly.
9-11. Shift 1%, then 10%, then 50% of read traffic; hold and observe between each.
12. **Point of no return** — release writes on the new system only.
13-15. Shift remaining traffic; verify end-to-end journeys; confirm background jobs and
webhooks are running on the new side and stopped on the old.
16-17. Re-enable write paths for batch and integration clients; verify third-party callbacks.
18. Reconcile again, an hour after release.
19. Announce complete; start the bake; leave the old stack running and reversible.

The steps most often missing from a first draft: background jobs and cron, webhook and
callback URLs registered with third parties, outbound IP allowlists held by partners,
scheduled reports, and anything with its own cached copy of the old endpoint.

## After the window

Write it up while it is fresh, whether it went well or badly — a cutover that succeeded
still has the two steps that ran long and the one thing the rehearsal missed, and those are
what the next one needs. The `postmortem` skill covers the writeup; the status channel
transcript is most of the raw material, which is the other reason to post everything into it
at the time.
