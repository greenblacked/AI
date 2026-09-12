---
name: game-day
description: "Plan and run a deliberate reliability exercise — a chaos experiment, a failover or disaster-recovery drill, an unannounced on-call rehearsal — and convert what it finds into owned, dated work: a falsifiable hypothesis, a measured steady state, a blast radius with a tested abort, the right failure to inject, game master, responder, observer and comms roles, timings for the humans as well as the system, and a ticket per finding. Use this skill whenever someone wants to test resilience on purpose — \"let us run a game day\", \"can we kill an AZ and see what happens\", \"we should test the failover\", \"does our DR plan actually work\", \"chaos engineering experiment\", or \"fire drill for the on-call rota\". Do not use it for an incident happening now, load or performance testing, security red-teaming, or writing up a real outage."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(kubectl:*), Bash(aws:*), Bash(gh:*)
---

# Game Day

A game day is finished when you can name a thing you believed about the system that turned out to be false, and point at the ticket that fixes it. Nothing being broken is a valid result only if the hypothesis was specific enough to have been falsified.

The point is not to break things. Breaking things is trivially easy and teaches nothing on its own; the value comes from having written down, in advance, what you expected to happen, so that the gap between expectation and reality is measurable rather than anecdotal. Two failure modes dominate. The first is chaos as theatre — someone kills a few pods, everything survives, the team feels good, and the exercise proved only that the pods were replaceable, which nobody doubted. The second is the drill that turns into a genuine incident because the blast radius was larger than anyone modelled, or because there was no abort, or because the responders were never told it was a drill. Both are avoidable with the same discipline: a falsifiable hypothesis, a measured steady state, a scope chosen in advance, and an abort you have already tested.

The other half of the job is that most of what a game day finds is about people, not machines. The failover works and takes 40 seconds; the on-call takes 22 minutes to notice, because the alert fired into a channel nobody watches, and another 15 to find the runbook, which links to a wiki page that was archived. Those numbers are the deliverable.

## Scope

Use for: planning and running a chaos experiment, an AZ or region failover drill, a disaster-recovery or restore-from-backup test, a dependency-degradation experiment, an unannounced on-call rehearsal, or a comms and incident-command drill; and for turning the results of any of those into tickets.

Do not use for: a live incident (that is `k8s-triage`), load or performance testing, security red-teaming or penetration testing, writing the postmortem for a real outage (that is `postmortem`), or a planned production migration where the goal is for nothing to break (that is `cutover`).

## Hard gates

Skipping one of these is what turns a drill into an outage. Each has produced a real incident somewhere.

1. A falsifiable hypothesis exists in writing before the exercise is scheduled. No hypothesis, no game day.
2. Steady state is defined and measured for long enough beforehand to know its normal variance.
3. The blast radius is stated as a scope, not as an intention — the fraction of traffic, the number of instances, the specific tenant.
4. The abort mechanism has been executed successfully before the failure is injected. An untested rollback is a second experiment running inside the first.
5. One named person can call the abort, and their word ends the exercise with no debate.
6. Everyone who could plausibly be paged knows an exercise is running, even when the responders do not know what it is. Someone outside the drill can always answer "is this real?" in seconds.
7. No game day during a change freeze, a launch, a peak commercial window, or while the error budget is already exhausted.

## Workflow

### 1. Write the hypothesis

The shape, and every clause earns its place:

```text
When [X fails, precisely], [Y continues to serve within Z],
and the on-call learns about it within N minutes from the alert alone.
```

- **X** is one specific failure, not "the database has problems". "The primary RDS instance in eu-west-1a is rebooted."
- **Y and Z** are the user-visible commitment, in the SLI's own units. "Checkout success rate stays above 99% and p99 latency stays under 800ms."
- **N minutes, from the alert alone** is the clause people leave out, and it is the one that catches the most. It tests detection, not just resilience. If the responder only knows because they were watching the exercise, the system did not detect anything.

A hypothesis you are certain about is not worth the exercise; one you cannot state is not an exercise at all, it is an outage you scheduled. Aim for the ones where the honest answer is "probably, but I would not bet the quarter on it".

### 2. Measure the steady state

Pick two to four metrics that describe the system as users experience it — the SLIs you already alert on are the right candidates — and record them for long enough to know their ordinary variance. A day if the system has a daily cycle, a week if it has a weekly one.

Write down the normal band, not a single number. "Checkout success 99.94-99.99%, p99 620-780ms, 1,100-1,400 rps at this hour on a Tuesday." Without the band you cannot distinguish degradation from the noise the system makes anyway, and every argument during the exercise becomes about whether the graph moved.

If you cannot measure the steady state, stop. That is the finding: you have no way to tell whether the system is healthy, which makes both the exercise and your incident response guesswork. Fix the observability gap and reschedule — and see `alert-design` for how to build the SLI.

### 3. Choose the blast radius and the abort

The smallest scope that can still falsify the hypothesis. Not the smallest scope that feels safe — an experiment too small to fail teaches nothing and costs a morning.

- **Scope:** name it in numbers. One AZ of three. 5% of sessions, selected by a header. One shard. One non-critical tenant with a support ticket already raised for them.
- **Abort condition:** decided before, in the steady-state metrics. "Abort if checkout success drops below 99% for 2 minutes, or if any alert not on the expected list fires." Not "abort if it looks bad".
- **Abort mechanism:** a specific command or button. Run it before the injection to prove it works — restore the instance you have not yet killed, flip the traffic weight back and forth, revert the feature flag. An abort you have not exercised is a hypothesis of its own.
- **Time to abort:** know how long the abort takes. A rollback that takes eleven minutes cannot protect a two-minute abort condition, and you need to know that before you learn it live.
- **Named owner of the abort:** one person, usually the game master. Their call is final and is never second-guessed during the exercise. Debate belongs in the debrief.

Staging has exactly one legitimate use here: debugging the mechanics of the exercise itself — does the injection tool work, does the abort work, does the observer's timestamp sheet make sense. Then run it for real. A DR plan proven only in staging is untested, because staging has different data volumes, different traffic, different IAM, different DNS, and no real users to be wrong about. The confidence you take from a staging-only drill is the expensive kind.

### 4. Pick the failure worth injecting

Choose the one that tests the belief you are least sure about. The table below maps common injections to what each actually tests — note that several of them test a human process rather than a machine.

| Failure to inject | What it actually tests |
| --- | --- |
| Kill one instance or pod | Replacement speed and whether anything held local state. The easiest and least informative one; do not stop here. |
| Kill every replica of one service | Whether dependents degrade or cascade, and whether the alert names the failed service or forty of its neighbours. |
| Remove an availability zone (block traffic, drain nodes) | Real capacity headroom in the survivors, zone-aware routing, and whether quorum systems survive losing a third of themselves. |
| Fail over the primary database | The failover mechanism, connection-pool recovery, and how much write-path downtime is actually incurred against what the RPO/RTO claims. |
| Restore a database from backup into a scratch environment | Whether the backups are restorable at all, and how long it takes. Frequently the single highest-value exercise available. |
| Add 500ms latency to a downstream dependency | Timeouts, retry budgets, and whether a slow dependency becomes an outage through pool exhaustion. Slow is harder than dead. |
| Return errors from a dependency at 20% | Retry storms, circuit breakers, and whether partial degradation is visible in the SLI at all. |
| Break DNS resolution for one dependency | Resolver caching, timeout behaviour, and the class of failure that hits everything simultaneously. |
| Fill a disk to 95% | Log rotation, back-pressure, and whether the disk alert fires before the service does. |
| Expire or revoke a certificate in a non-critical path | Renewal automation, and the alert that should have warned weeks earlier. |
| Revoke a service account's permission | Whether the failure is legible or arrives as a generic 500 nobody can attribute. |
| Page the real on-call, unannounced, with a synthetic but realistic alert | Detection, acknowledgement, escalation, and whether the runbook is usable at 3am. |
| Hide the runbook, or the primary responder | Bus factor and documentation. Uncomfortable and disproportionately informative. |
| Simulate the incident channel and status page under a comms drill | Whether anyone can write a customer-facing update in under ten minutes, which is the part that is always improvised. |

Two flavours, different value, both needed. Technical injection tells you about the system; human and process drills tell you about the response. Most organisations run only the first and are surprised by the second during a real incident.

### 5. Schedule it

- **Business hours**, with the team at full strength. A game day at 2am to "be realistic" gives you a real outage with a tired team and no one to help.
- **Announced to stakeholders**: support, the incident-command rota, anyone who owns a dependency, and anyone who would otherwise escalate. Post in the incident channel that a drill is running, with the game master's name, the abort owner, and the expected end time.
- **Unannounced to responders**, when the team's culture supports it and only for the human drills. It is the only way to measure real detection time. Where trust is not there yet, announce it and measure the rest — an announced drill still measures the failover, the runbook and the comms. Escalate to unannounced once people have seen that findings are treated as system defects rather than performance issues.
- **Not** during a freeze, a launch week, a peak commercial period, an ongoing incident, or when the error budget is already spent.
- Budget the debrief in the same calendar block. A game day with no debrief slot loses most of its value in the two days it takes to schedule one.

### 6. Assign the roles

| Role | Responsibility |
| --- | --- |
| **Game master** | Owns the script, executes the injection, holds the abort, keeps time. Does not respond to the incident. |
| **Responders** | The real on-call, working the problem with no knowledge of the script. If they know what was injected, you are measuring their acting, not the system. |
| **Observer** | Takes timestamped notes and nothing else. Every event, every question asked out loud, every tab opened, every moment someone had to guess. This is the role people skip and the one that produces the findings. |
| **Comms** | Tells stakeholders this is a drill, keeps the "is this real?" answer available in seconds, and handles anyone who escalates from outside. |

For a small team, game master and comms can be one person. Observer cannot be merged into anything: someone participating cannot take reliable timestamps, and reconstructing them afterwards from memory produces the round numbers that make the whole record untrustworthy.

### 7. Run it, and measure the humans

Inject the failure. Then stop talking and watch. The strongest instinct in the room is to help the responders, and it destroys the measurement — every hint you give is a minute you can no longer count.

The observer records, with wall-clock timestamps:

| Measure | Definition |
| --- | --- |
| Time to detect | Injection to the first automated signal reaching a human — the page, not the graph. |
| Time to acknowledge | First signal to a human actively working it. |
| Time to correct action | Acknowledgement to the first action that actually helped, plus every action taken before it that did not. |
| Time to recover | Injection to steady state restored. |
| Guesses | Every moment someone said "I think", "does anyone know", or opened a dashboard hoping. Each one is a documentation or observability finding. |
| Wrong turns | Actions taken from a mistaken model of the system. These are the most valuable notes in the file. |

Abort the moment the abort condition trips, without discussion. An aborted game day is a successful game day: it found the boundary, which is what you came for.

### 8. Debrief within 24 hours, and turn findings into tickets

Same day if you can, next morning at the latest. Memory of the wrong turns decays fastest, and those are the findings worth having.

Run it blameless, in the `postmortem` style — every wrong turn is a defect in documentation, tooling, alerting or system design, and never a defect in the person. Someone who took a wrong turn during a drill just found a trap before it caught a real incident at 3am.

Then: **every finding becomes a ticket with an owner and a date, or it did not happen.** A game day whose findings live in a document is a game day you will run again next year for exactly the same reasons, and the second run is much harder to justify. Write the tickets during the debrief, in the room, with names attached. Anything that cannot find an owner is a finding the team has decided not to fix — record that decision explicitly rather than letting it decay into a backlog item.

Finally, decide the next exercise. The best candidate is usually the thing you were too nervous to inject this time.

## Experiment record

Fill this in before the exercise and complete it during. It is the artefact — the hypothesis and the timeline are what make the numbers arguable later.

```markdown
# Game day: [name] — [date]

## Hypothesis
When [X fails], [Y continues within Z], and on-call learns within [N] minutes from the alert alone.

## Steady state
[Metric: normal band, measured over what period.]

## Blast radius
[Scope in numbers. Environment. Duration cap.]

## Abort
Condition: [metric threshold, or unexpected alert]
Mechanism: [exact command] — tested at [time], took [duration]
Owner: [name]

## Roles
Game master / Responders / Observer / Comms

## Timeline
| Wall clock | Elapsed | Event |
| --- | --- | --- |
| 10:00 | 00:00 | Injection: [command run] |
| 10:0? | | First alert fired: [alertname] to [destination] |
| 10:0? | | Responder acknowledged |
| 10:1? | | First correct action |
| 10:2? | | Steady state restored |

## Result
Hypothesis: confirmed / falsified. [Which clause failed, and by how much.]
Detect [m] / acknowledge [m] / correct action [m] / recover [m].

## Findings
| # | Finding | Evidence from the timeline | Owner | Due | Ticket |
| --- | --- | --- | --- | --- | --- |

## What we did not test
[The scope you deliberately excluded, so nobody reads this as broader assurance than it is.]
```

## Anti-patterns

**Chaos without a hypothesis.** Killing things at random produces war stories, not fixes. Nothing is falsifiable, so nothing is learned, and the exercise cannot fail — which is exactly why it keeps getting repeated and never changes anything. Write the sentence first.

**Testing in staging only.** Staging has different data volume, traffic, IAM, DNS and capacity, and no real users to be wrong about. A failover that works there tells you the code path exists, not that the system survives. Use staging to debug the exercise mechanics, then run it for real or admit the plan is untested.

**No abort button.** Without a pre-tested abort, the exercise's exit path is improvised under pressure, which is the definition of an incident. The abort must be a specific command, run successfully before injection, owned by one named person, with a known duration.

**Announcing to the responders.** Warned responders sit on the dashboard and the detection time you measure is fiction — usually by a factor of ten. It is the number most worth having and the easiest to destroy. Announce to stakeholders, not to the rota, once the team trusts that findings are treated as system defects.

**Findings with no owner.** A document full of insight funds nothing. Within a month the tickets are unwritten, the fixes are unmade, and the next drill rediscovers the same gaps at the same cost. Write tickets in the debrief, with names and dates, or record explicitly that the team chose not to fix it.

**The drill that becomes an incident because nobody said it was a drill.** Someone outside the loop sees the alert, escalates, wakes an executive, and posts to the status page. Now you are running a real incident response about a fake incident, with real customer communication to retract. Comms is a role, announced before the injection, with an answer to "is this real?" available in seconds.

**Only injecting instance kills.** The cheapest failure to inject is also the one modern platforms already handle. If every exercise is a pod kill, the exercise is measuring the orchestrator. Latency, partial errors, DNS, certificate expiry, permission loss and database failover are where the untested assumptions live.

**Skipping the observer.** Participants cannot take reliable timestamps. Reconstructed afterwards, the timeline is round numbers and charitable recollection, and the human-response measurements — the actual deliverable — become unarguable in the wrong direction.

## Reference files

- `references/experiment-catalogue.md` — read when choosing and executing the injection: concrete failure injections with the commands and tooling for Kubernetes, AWS and network-level faults, the safety controls each needs, and what to watch while it runs.
- `references/drill-facilitation.md` — read when running a human or process drill: unannounced on-call rehearsals, the observer's note-taking sheet, DR and restore-test specifics against stated RPO and RTO, and how to run the debrief so findings leave the room as tickets.
