---
name: upstream-change-defense
description: "Protect warehouse pipelines from source teams changing a field's schema or meaning: classify each surprise as structural (column dropped, renamed, retyped) or semantic (same column, new meaning: a new status code, pence to pounds, a time zone switch, re-keyed ids), land raw untouched, diff the schema at ingest, catch semantic drift with enum, range and match-rate checks, quarantine failing rows and replay from raw after the fix, then give the producer a CI compatibility check and a named contact. Use when \"they renamed a column and the pipeline broke\", \"amounts are suddenly 100x\", \"a new status value appeared\", \"we need a data contract\" or \"upstream keeps breaking our models\". Not for designing the producer's API (api-design), shipping their schema change (db-migration), a table's general check suite (data-quality-checks), or who reads your table (consumer-discovery)."
allowed-tools: Read, Glob, Grep
---

# Upstream Change Defence

Done means a change in a source arrives as a named, quarantined event with a replay path, not as a wrong number on a dashboard a week later: raw data is landed as received, structural changes are caught by a schema diff at ingest, semantic changes by distribution checks on the fields that carry meaning, failing rows wait in quarantine, and the producer has a check in their own pipeline and a person to call.

The usual failure is defending only against the change that breaks loudly. A dropped column fails the load and gets fixed the same morning. A status code reused for a new meaning, or an amount that switched from minor to major units, loads cleanly and is reported for weeks. Semantic change is the expensive half, and no schema check sees it.

## Workflow

### 1. Inventory the sources and their past surprises

List each upstream source with its owner, delivery mechanism (replication, files, events, API pulls) and the tables downstream of it. For each, collect the incidents of the last year caused by an upstream change and classify them:

| Class | Examples | Detected by |
| --- | --- | --- |
| Structural | Column added, dropped, renamed; type widened or narrowed; nullability changed; nested field moved | Schema diff at ingest |
| Semantic | New or reused enum value; unit or currency change; time zone change; id re-keyed or recycled; null now means something; event fired at a different moment | Distribution checks against a baseline |

Rank sources by blast radius (the money and decisions downstream of them) times surprise frequency, and work down that list. The first two or three sources usually carry most of the risk.

### 2. Land raw, untouched, before parsing

Load each delivery as received into a raw landing table: the payload in a semi-structured column (`VARIANT` in Snowflake, `JSON` in BigQuery, the file as-is in object storage) plus load metadata: source, file or batch id, load time, and the schema version if the producer sends one. Parse into typed staging models downstream.

This ordering is the defence. A structural change no longer fails the load, so nothing is lost while it is investigated, and every fix can be replayed from the original bytes. Never edit raw; a correction is a change to the parsing model, applied by replay.

### 3. Diff the schema at ingest

For each batch, compare the observed schema (keys and types in the payload, or `INFORMATION_SCHEMA.COLUMNS` for replicated tables) with the expected schema recorded for that source. Classify the diff:

- **Additive** (new nullable column or key): load, warn the owning team, review whether it changes meaning of an existing field.
- **Breaking** (dropped or renamed field, narrowed or changed type, a reliably filled field now nullable, changed key): stop the parse for that source and alert, leaving the raw batch in place.

Keep the expected schema in version control beside the parsing model, so accepting a change is a reviewed commit, not a silent drift. The queries are in `references/detection-checks.md`.

### 4. Check meaning with distributions

For each field that carries meaning, compare every batch with a trailing baseline (30 days is a reasonable start; long enough to include a month end):

- Enum fields: values never seen before, values that vanished, and each value's share moving beyond its historical range.
- Amounts and quantities: median and high percentiles; a factor of 100 or 1000 is a unit change, not growth.
- Timestamps: hour-of-day distribution; a whole-hour shift is a time zone change.
- Foreign keys: match rate against the dimension; a sudden drop is a re-keyed or recycled id.
- Null rates on fields that were reliably filled.

Run these on staging before anything is published, because after publish the wrong figure is already in someone's report. Queries for each are in `references/detection-checks.md`.

### 5. Quarantine and replay

Route rows that fail a breaking check to a quarantine table with the batch id, the check that failed and the time. Decide per table whether the rest of the batch may publish: for counts where a missing slice is visible and tolerable, publish and show the quarantined count beside the figure; for money and anything summed, block the publish, because a total missing one segment looks plausible and is wrong.

After the fix (a new mapping for the status code, a unit conversion keyed on the change date, an updated expected schema), replay the affected batches from raw through the same models. Make the parse idempotent by batch id, so a replay replaces rather than appends. Confirm the replay with the same checks, then release.

### 6. Move detection to the producer

Every check above fires after the change has shipped. Ask the producing team for three things, in this order:

1. **A named contact** on each side and a channel for change notices, with the notice period agreed.
2. **A contract file** in their repository: field names, types, nullability, and for semantic fields the allowed values, units, time zone and what null means.
3. **A compatibility check in their CI** that fails a breaking change to the contract before it merges: `buf breaking` for Protobuf, a schema registry compatibility check for Avro or JSON Schema, or a diff of the contract file for tables and files.

Schema checks in their CI will not catch semantic change. That is what the contract's semantic section and the notice are for; a new enum value should be a contract change reviewed by both sides. A template and the registry compatibility modes are in `references/producer-contract.md`.

### 7. Review each surprise that still gets through

When a change escapes, add the check that would have caught it, at the earliest point it could run (producer CI before ingest, ingest before publish). Track escapes per source; a source that keeps escaping needs a stricter contract or a conversation with its owner, not more downstream checks.

## What to hand back

```markdown
## Sources ranked
[Source, owner, delivery, blast radius, past surprises by class.]

## Raw landing
[Per source: landing table or location, load metadata, replay command.]

## Structural detection
[Expected schema location, diff rule, additive vs breaking action.]

## Semantic detection
[Per field: check, baseline window, threshold, action.]

## Quarantine and publish rule
[Per table: partial publish allowed or blocked, where quarantine counts are shown.]

## Producer agreement
[Contacts, notice period, contract file, CI check, status.]
```

## Anti-patterns

**Parsing on load.** A typed load fails on the first structural change and the batch is gone or half-written; land raw and parse after.

**Only checking schemas.** The schema stays identical when cents become pounds. Check the values of fields that carry meaning.

**Silent quarantine.** Rows set aside without a visible count bias every total that includes them. Show the count, or block.

**Editing raw to fix a change.** The original record of what the producer sent is lost, and the next replay reintroduces the error.

**Downstream checks as the only defence.** Each check fires after the change has shipped. The cheapest catch is a failed check in the producer's pull request.

## Reference files

- `references/detection-checks.md` — read at steps 3 and 4: the schema diff, enum drift, unit shift, time zone shift, match rate and null rate queries.
- `references/producer-contract.md` — read at step 6: the contract template, what goes in its semantic section, and the compatibility checks producers can run in CI.
