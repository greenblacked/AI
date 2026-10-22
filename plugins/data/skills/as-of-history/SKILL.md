---
name: as-of-history
description: "Answer what was true, or what we believed, on a past date, and keep the history to answer it: classify the question as state, validity or arrival, pick a periodic snapshot, type-2 dimension or append-only change log to match, add recorded time beside valid time for anything restated or backdated, join facts on half-open intervals, accept the design only when a known past report reproduces to the unit, and when history was never captured, rebuild it from audit logs, backups or exports and mark the span inferred. Use when asked \"what did the dashboard say on 1 March\", \"what plan was this customer on at the time\", \"we overwrote the old values\", \"SCD type 2 or snapshots\", \"bitemporal\" or \"reproduce last quarter's board numbers\". Not for modelling a new application table (schema-design), changing a live schema (db-migration), or when a figure is final (late-data-maturity)."
allowed-tools: Read, Glob, Grep
---

# As-Of History

Done means a question of the form "as known on date K, what was true at date V" has one query that answers it, the history behind that query has passed its integrity checks, and a report someone actually published in the past comes back from it unchanged. Any span of history that was rebuilt rather than captured is labelled as inferred, row by row.

The usual failure is a dimension that is overwritten in place. Last quarter's revenue by customer segment is recomputed with today's segments, the board pack no longer reproduces, and nobody can say whether the old number was wrong or the customers moved. The second failure is a type-2 dimension used to answer a "what did we know" question: it records when something was true, not when the warehouse learned it, so a backdated correction rewrites the past silently.

## Workflow

### 1. Write the question with both dates

Rewrite each question as one sentence naming the entity, the valid date (when the thing was true in the world) and the knowledge date (when someone would have looked). "As of the 3 April board pack, what was Acme's plan on 31 March?" has both. Then classify it:

- **State**: what did the table hold at a moment, as the warehouse saw it then. Answered by a snapshot or by recorded time.
- **Validity**: over what interval was a fact true in the world, including corrections learned later. Answered by valid time.
- **Arrival**: when did we learn it, in what order did changes come. Answered by an append-only change log.

Most disputes about "the number changed" are a state question being answered with validity data, or the reverse.

### 2. Choose the storage that matches the question

| Question | Store | Why |
| --- | --- | --- |
| State at daily or monthly grain | Periodic snapshot table, one copy per period | Simple to query and to explain; misses changes between snapshots |
| Validity of a slowly changing attribute | Type-2 dimension with `valid_from`, `valid_to` | Compact; joins facts to the attribute in force when they happened |
| Arrival and order of changes | Append-only change log (CDC stream, audit table) | Rebuilds either of the above; nothing else rebuilds it |
| Validity of something that gets restated or backdated | Bitemporal: valid time and recorded time | The only form that answers both "what was true" and "what did we think was true" |

Capture the change log whenever the source can supply one, even if you also build a snapshot or a dimension from it: it is the one form the others can be rebuilt from. Warehouse time travel (Snowflake `AT`, BigQuery `FOR SYSTEM_TIME AS OF`) is a recovery window of days, not a history store; use it to seed a snapshot, not to answer next year's question. Read `references/history-patterns.md` for each layout, the dbt snapshot behaviour that matters, and the queries.

### 3. Add recorded time to anything that is restated

If a value can be corrected after the fact (a backdated plan change, a revised invoice, a reclassified account), a single time axis is not enough. Give the table `valid_from`, `valid_to`, `recorded_from` and `recorded_to`. A correction never edits a row: it closes the current rows' `recorded_to` at the correction time and inserts new rows with `recorded_from` set to that time, covering the corrected valid interval. The past belief survives, so a report run at an earlier knowledge date still sees what it saw.

### 4. Fix the interval conventions once

Use half-open intervals (`valid_from <= t and t < valid_to`) so adjacent versions never both match a boundary instant. Use a far-future sentinel for the open end rather than null, so every join is the same two comparisons. Store timestamps in UTC and convert to the reporting time zone only when assigning a day. Write these down in the model's documentation; a second convention in one warehouse is how a fact joins to two versions or to none.

### 5. Check the history before trusting it

Run the integrity checks on every history table: no overlapping intervals per key, no gaps unless the entity genuinely did not exist, exactly one open row per live key, `valid_from` before `valid_to`, and for bitemporal tables the same checks within each recorded interval. Then join the main fact table to the history and count facts that match zero or two versions. Each check is in `references/history-patterns.md`; a non-zero result is a defect to fix before step 6, not a tolerance.

### 6. Reproduce a known past report

Pick a report someone actually published, with its figures and the date it was produced: a month-end pack, a board deck, a regulator submission. Recompute it with the knowledge date set to when it was produced and the transformation code checked out at the commit that was live then. Expect a match to the unit.

When it does not match, classify the gap before changing anything: history not captured for that span, a metric definition that changed since (the code version is part of history), late rows that arrived after the report (a `late-data-maturity` question), or a defect in the history itself. Only the last is fixed in the history tables.

### 7. Rebuild history that was never captured, and say so

When the past was overwritten, rebuild what you can from the sources in `references/reconstruction.md`: application audit tables, CDC or binlog retention, restored backups, object-store versions, exported reports, SaaS field history. Load the result into the same table with a `history_source` column (`captured`, or `inferred:` and the method) and the date capture began. Never blend inferred rows into captured ones without the label; a reader comparing two quarters must be able to see that one was reconstructed.

Start capturing immediately, before the reconstruction is finished. Every day without capture is another day that has to be inferred.

## What to hand back

```markdown
## Question
[Entity, valid date, knowledge date; state, validity or arrival.]

## Storage chosen
[Snapshot, type-2, change log or bitemporal, and why; interval conventions.]

## Integrity results
[Overlaps, gaps, open rows, facts matching zero or two versions.]

## Reproduction test
[Report reproduced, knowledge date, code commit, result, any gap and its class.]

## Inferred spans
[Entity, date range, method, capture start date.]
```

## Anti-patterns

**Overwriting a dimension and recomputing the past.** Every historical report changes with today's attributes, and the change looks like a correction rather than a loss.

**Type-2 answering a "what did we know" question.** Backdated corrections move `valid_from` into the past and the old belief disappears. Add recorded time.

**Closed intervals.** `between valid_from and valid_to` matches two versions at every boundary, and the join doubles a fact once per change.

**Time travel as the history store.** It expires in days; the question about last year arrives next year.

**Unlabelled reconstruction.** A rebuilt span that looks captured gets cited with the same confidence, and the first mismatch discredits the whole table.

## Reference files

- `references/history-patterns.md` — read at steps 2 to 5: snapshot, type-2, change log and bitemporal layouts, dbt snapshot behaviour, as-of joins and the integrity checks.
- `references/reconstruction.md` — read at step 7: where uncaptured history can still be found, how far back each source usually goes, and how to mark inferred spans.
