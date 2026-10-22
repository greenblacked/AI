# Gates and templates

## Contents

- Failure conditions and rollback
- Gate template
- Worked gates: on-call and a monthly close
- Intervention log
- Sign-off record

## Failure conditions and rollback

Fill this in before rung 1. One row per way the duty can go wrong.

| Failure condition (observable) | Detected by | Stop or rollback | Who is told, and when |
| --- | --- | --- | --- |
| A step skipped from the written procedure | Owner, from the log | Stop, repeat the step, record it | Owner, immediately |
| Action taken outside the stated scope | Owner or system audit trail | Revert the action using the documented undo | Owner and the system's stakeholders |
| Customer-visible error | Monitoring or a report | The documented rollback; escalate if it does not complete | Escalation contact, within the agreed time |
| Wrong figure or record posted | Reconciliation check | Reverse the entry, repost, note the cause | Finance owner or approver |
| Escalation raised after the agreed threshold | Timeline in the log | Count as a failed run | Owner |

A near-miss that the learner caught and corrected is recorded, and does not count as a failure if the written rollback was followed. The point is to separate "wrong and unnoticed" from "wrong and handled".

## Gate template

```text
Rung:            (watch | assist | do-with-watcher | solo)
Date window:     from ... to ...
Actions to demonstrate (3 to 5, each observable):
  1.
  2.
  3.
Count required:  (for example 2 runs, consecutive)
Failure conditions that reset the count: (refer to the table above)
Evidence kept:   (run log, ticket links, screenshots)
Decided by:      (owner)
```

## Worked gates

### On-call rotation, rung 3

- Acknowledges the page inside the agreed response time.
- States the first three things they check, in order, before touching anything.
- Chooses between mitigation and diagnosis and says why.
- Writes the timeline entry as they go.
- Hands over or escalates using the written criteria.

Count: two consecutive shifts or two drills with no owner intervention. Drills on a staging copy count only for the rungs the plan says they may stand in for.

### Monthly close, rung 3

- Completes the pre-close checklist and attaches the evidence.
- Runs the reconciliation and explains each variance over the threshold.
- Posts the adjusting entries without reviewer correction.
- Produces the report pack on the due date.
- Names the three items the approver will ask about.

Count: two closes. With only three closes in the runway the full count cannot be met on live runs, so write the substitution into the plan. Rung 1 is a rehearsal on a copy: the learner watches the owner rework the previous month's close on a copy of its data, with narration. Rung 2 is close one. Rung 3 is close two, and its second count is a rehearsal on a copy of an earlier month with the owner only observing. Rung 4 is close three. Alternatively lower the rung-3 count to one for this monthly duty and record that in the plan; either way the gate states which runs are rehearsals.

## Intervention log

| Time | Run | Signal used (pause or take over) | What the learner was doing | What the owner saw | Fix or follow-up |
| --- | --- | --- | --- | --- | --- |

Review the log at the end of each run. A repeat in the same column means the runbook is missing something.

## Sign-off record

```text
Duty:
Learner:                Owner:                Escalation contact:
Rung gates met (dates): 1 ...  2 ...  3 ...  4 ...
Runs completed:         ...
Interventions in rung 3: ...
Runbook changes made by the learner: (link or diff)
Open risks accepted:
Owner signature and date:
Told: (who now knows the duty has moved)
```
