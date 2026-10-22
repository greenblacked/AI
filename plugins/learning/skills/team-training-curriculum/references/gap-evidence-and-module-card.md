# Gap evidence and module card

## Contents

- Evidence tally
- Module card
- Worked example: a new SRE path
- The 30-day application check

## Evidence tally

One row per task from the performance task list. Fill it from artefacts, not opinion.

| Task | Where to look | What counts as a gap signal | Learners affected | Verdict |
| --- | --- | --- | --- | --- |
| Roll back a release alone | Release channel, incident timelines | Rollback done by someone else, or delayed waiting for help | 4 of 6 | Teach |
| Triage a failing pod | Pager history, escalation notes | Escalated without logs or events attached | 3 of 6 | Teach |
| Read a dashboard | Review comments, channel questions | Few questions asked | 1 of 6 | Skip |
| Write a runbook step | Runbook pull requests | Reviews requiring a rewrite | 5 of 6 | Practise only |

Sources by kind of work: review comments on pull requests; incident timelines and the paged-for-escalation list; support tickets reopened or bounced between teams; questions in the team channel; time from assignment to first commit on similar tickets. Read a sample of at least ten items per task before giving a verdict, and write down the ten so someone else can check.

Verdicts: teach (a module with practice and assessment), practise only (the knowledge is there, give a sandbox exercise), skip (no evidence of a gap).

## Module card

```text
Module:           (name, one line)
Serves task:      (id from the performance task list)
Objective:        (the task, phrased as what the learner does)
Needed by:        (date or event) ; taught: (within the two weeks before the need date)
Prerequisites:    (modules or existing abilities)
Practice task:    (what they do, on which system, in the sandbox)
Assessment:       (the same task unaided; who or what checks it; pass condition)
Hours:            (preparation by learner + session + practice)
Owner:            (name)
Review date:      (no later than six months out)
Applied by:       (the real work that should use it, so day 30 can be checked)
```

## Worked example: a new SRE path

Performance tasks, ranked: roll back a release; triage a failing pod; acknowledge and hand off a page; write a runbook step; run a controlled restart of a stateful service.

| Week | Hours | Module | Needed by | Assessment |
| --- | --- | --- | --- | --- |
| 1 | 3 | Release and rollback | First shadow release, week 2 | Roll back a seeded bad release in the sandbox unaided |
| 2 | 4 | Pod triage | First on-call shadow, week 3 | Diagnose three seeded failures; escalate with evidence attached |
| 3 | 3 | Pages and handoffs | On-call shadow, week 3 | Run a mock page start to handoff |
| 5 | 3 | Runbook writing | First runbook ticket, week 6 | A runbook step passes review without a rewrite |
| 7-8 | 4 | Capstone | A real backlog ticket | Ticket merged, reviewed, no pairing |

Total over eight weeks is at most four hours in any week. Nothing on stateful restarts: the evidence showed no gap, so it was skipped.

## The 30-day application check

Thirty days after each module, ask for each learner one question: where did you use this in real work? Evidence beats recollection, so name the pull request, ticket or incident. Count only learners who had a chance to use it (the "Applied by" work happened). Record the count applied out of that number.

- Applied by most: keep, and review on the date.
- Applied by few: the timing or the target task was wrong; move it closer to the need or rewrite it.
- Applied by nobody who had the chance, within 30 days: delete the module, and write a line saying why, so it is not rebuilt from habit.
- Nobody had the chance (the rare event did not occur): defer the check to the next real occurrence; do not delete.
