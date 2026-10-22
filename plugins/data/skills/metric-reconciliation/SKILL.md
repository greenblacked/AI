---
name: metric-reconciliation
description: "Settle why two dashboards, teams or systems report different values for the same metric, and end with one definition instead of an explanation: freeze one metric, one day and one segment, reproduce each figure from raw data, diff the two row sets by key with a full outer join, and assign the gap to causes tested in a fixed order — time zone and day boundary, snapshot time, filters and inclusion, dedupe rule, join grain, currency and units — until the residual is zero. Close with one owned, versioned definition and the duplicate retired or renamed. Use when finance and product disagree on revenue, Looker says 41,200 and the board deck 39,850, or two reports never tie out. Not for a total inflated by a join (join-fanout-hunt), why a metric moved over time (metric-movement-decomposition) or a figure still changing as data lands (late-data-maturity)."
allowed-tools: Read, Grep, Glob
---

# Metric Reconciliation

This is finished when the gap between the two figures is broken into named causes that sum to the whole difference, each cause backed by the rows it moved, and the organisation has one owned definition of the metric with the other version retired or renamed so the two can no longer be confused.

The usual failure is an explanation that nobody acts on. Someone spends two days establishing that marketing counts signups in UTC and finance in local time, writes it up, and both dashboards carry on under the same name until the question comes back next quarter from someone more senior. The second failure is diffing totals over a month and every segment at once: six causes overlap, none sums cleanly, and the residual is waved away as "timing". Narrow the comparison until it can be explained row by row, then change the definitions, not the write-up.

## Scope

Use for: two dashboards, reports, teams or systems that disagree on a metric they both call the same name; a warehouse figure that does not tie to the source system or to finance; a migrated report that does not match the old one for a metric with an existing definition; deciding which definition survives.

Do not use for: a single query whose total is inflated by a join, which is `join-fanout-hunt` (this skill hands a join-grain gap there); explaining why one metric changed between two periods, which is `metric-movement-decomposition`; yesterday's figure that keeps rising as late rows arrive, which is `late-data-maturity`; replacing a spreadsheet with a pipeline, where the old sheet is the reference to match, which is `spreadsheet-retirement`.

## Workflow

### 1. Freeze one metric, one day, one segment

Pick a single day that is complete on both sides (old enough that late data has landed), a single segment small enough to inspect row by row (one country, one product line), and the one metric. Write down both reported figures for that slice, where each was read, and when. The read time matters: a figure read at 09:00 and one read at 15:00 can differ by data that arrived in between.

If the two sides disagree only over long ranges, pick the day with the largest gap. A difference that exists in the monthly total but in no single day is almost always a day-boundary cause.

### 2. Get each definition as the query that actually runs

Take the SQL the dashboard or report executes — from the BI tool's generated-SQL view, the semantic layer's compiled query, or the warehouse query log — not the definition in the wiki. Note everything outside the SQL that changes the number: dashboard-level filters, row-level security on the viewer, an extract refreshed at a fixed time, a cached tile, a manual adjustment in a spreadsheet downstream.

### 3. Reproduce both figures from raw

Run each side's logic yourself against the warehouse for the frozen slice and match its reported figure exactly. If a side does not reproduce, stop and find out what it is reading — usually an extract or cache from a different time, or a filter applied in the tool. Diffing a number you cannot reproduce explains a number nobody is looking at.

### 4. Diff the row sets by key

Rewrite each side to emit one row per entity key (order, user, account) with that key's contribution to the metric. Check each side is unique on the key; if it is not, that side has a join-grain problem, so hand it to `join-fanout-hunt` before going on. Full outer join the two keyed sets and put every key in one bucket: only in A, only in B, in both with different values, or matching. The difference between the figures equals the only-A total, minus the only-B total, plus the value differences — check that it does before moving on, because a diff that does not add up is comparing the wrong things.

Read `references/row-diff.md` for the diff query and the per-cause tests.

### 5. Assign the gap to causes in a fixed order

For each cause, apply one side's rule for that cause to the other side only, rerun the diff, and record how much of the gap closed. Test in this order:

| Order | Cause | What it looks like in the diff |
| --- | --- | --- |
| 1 | Time zone and day boundary | Only-A and only-B keys clustered in the hours either side of midnight |
| 2 | Snapshot time | Only-A keys loaded after side B was computed; recent updates to the value |
| 3 | Filter and inclusion | Only-one-side keys sharing an attribute: test accounts, internal users, refunds, cancelled status, bots, a product excluded |
| 4 | Dedupe rule | Same keys, different counts: one side counts events, the other users or sessions; one side keeps retries |
| 5 | Join grain | Value differences in integer multiples on some keys |
| 6 | Currency and units | Value differences by a near-constant ratio: an exchange rate, cents against units, gross against net of tax |

The order is fixed because the causes masquerade as each other. A time zone shift moves keys into and out of the day and looks exactly like an inclusion filter; late data looks like a filter too. Removing the boundary and timing causes first leaves the later buckets clean enough to read. Keep the running total: each cause's amount, and the residual after it.

Stop when the residual is zero, or inside a tolerance agreed before you started (rounding at the cent, for instance). A residual you cannot explain is reported as unexplained, with its keys — never spread across the causes you did find.

### 6. Widen once, to check the causes hold

Apply the causes you found to a full week or month across all segments. If the reconciled figures now agree everywhere, the cause list is complete. If another segment or day leaves a residual, freeze that slice and return to step 3: it has a cause the first slice did not exercise.

### 7. End with one definition and a retired duplicate

With the people who use the metric, decide for each cause which rule serves the decision the metric exists for, and write the definition once — in the semantic layer or the metrics definitions under version control — with a named owner. Repoint both dashboards at it. Then retire the other version: delete it, or, if it genuinely answers a different question, rename it so the two no longer share a name ("signups (attributed)" beside "signups"). Read `references/definition-record.md` for the record to write and the retirement steps.

## Output format

```markdown
## Slice
Metric: [name]. Day: [date, time zone]. Segment: [value]. A: [figure, source, read at]. B: [figure, source, read at].

## Reproduction
[Both figures reproduced from raw: yes or no, and what was found if not.]

## Reconciliation
| Step | Cause | Amount | Running figure | Keys moved |
| --- | --- | --- | --- | --- |
| | A as reported | | 12,480 | |
| 1 | Time zone | -298 | 12,182 | 298 |
| ... | | | | |
| | Residual | 0 | B: 12,115 | |

## Holds over the wider range
[Week or month, all segments: agrees, or the slice that did not.]

## Definition
[The owned definition, its location, the owner, and what happened to the other version.]
```

## Anti-patterns

**Diffing the monthly total.** Several causes overlap and offset; the residual becomes "timing". One day, one segment, row by row.

**Reconciling a number you did not reproduce.** If the dashboard reads a stale extract, the diff explains the extract, not the dashboard.

**Testing causes in whatever order they occur to you.** An inclusion filter "found" before the time zone check absorbs keys that only moved across midnight, and the definition you write encodes the wrong rule.

**Spreading the residual.** A gap of 37 assigned "probably to late data" hides a seventh cause. Report it with its keys.

**A write-up instead of a change.** Two dashboards with the same metric name and different rules will be compared again. One definition, one owner, and the other renamed or gone.

## Reference files

- `references/row-diff.md` — read at steps 4 and 5: the keyed full outer join, the bucket summary, and a test query for each cause, including time zone conversion per dialect.
- `references/definition-record.md` — read at step 7: the definition record, choosing the rule per cause, and retiring or renaming the duplicate without breaking its readers.
