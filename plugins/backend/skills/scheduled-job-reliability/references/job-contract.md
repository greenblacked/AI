# Job contract template

Keep one block per job in the repository next to the code, so a change to the job changes its contract in the same review.

```text
Job:               nightly-usage-rollup
Schedule:          17 2 * * *  (UTC, offset chosen to avoid the top of the hour)
Window:            previous UTC day, [00:00, 24:00), supplied by the scheduler as --window-start/--window-end
Idempotent:        yes; output replaced per (window, account) inside one transaction
Max runtime:       40 min (slowest healthy run 22 min); activeDeadlineSeconds 2700
Overlap policy:    skip; concurrencyPolicy Forbid, startingDeadlineSeconds 1800
Missed-run policy: catch up per day, at most 3 windows per pass, oldest first
Run record:        job_run table, one row per (job, window)
Alert:             no success for 36 h -> ticket; no success for 60 h -> page
Owner:             billing platform team
Rerun procedure:   run with the explicit window; safe to repeat
```

## Worked example

A rollup read `now() - interval '1 day'` and appended rows to a totals table. A deploy during the run killed it half-way; the retry ran the next morning, covered a different day, and left the first day with half its rows.

Changes: the window became a parameter derived from the scheduled time; totals were written with `INSERT ... ON CONFLICT (window_start, account_id) DO UPDATE`; a `job_run` row per window recorded status; the catch-up pass selected days in the last 14 with no `succeeded` row. Killing the process mid-run and rerunning the same window then produced the same table as an undisturbed run.

## Questions that expose a hole

- What happens if the previous run is still going when the next is due?
- What happens if the scheduler is down for two periods?
- What does a rerun for an already finished window do?
- Who finds out if nothing runs, and how long does that take?
- Which cell of the contract would change if the data grew tenfold?
