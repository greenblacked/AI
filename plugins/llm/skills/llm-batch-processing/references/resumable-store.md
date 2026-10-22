# Resumable store

## Contents

- Schema
- Claim and write loop
- Tracking provider batches
- Dead-letter and repair
- Audit sample draw

## Schema

SQLite is enough for a single-host job; use the team's database where several hosts write.

```sql
CREATE TABLE IF NOT EXISTS results (
  item_id        TEXT NOT NULL,
  content_hash   TEXT NOT NULL,
  model_id       TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('pending','done','failed','dead')),
  attempts       INTEGER NOT NULL DEFAULT 0,
  output_json    TEXT,
  error          TEXT,
  input_tokens   INTEGER,
  output_tokens  INTEGER,
  updated_at     TEXT NOT NULL,
  PRIMARY KEY (item_id, model_id, prompt_version)
);
CREATE INDEX IF NOT EXISTS results_dedupe ON results (content_hash, model_id, prompt_version, status);
```

The manifest is a second table of every expected `item_id` and its `content_hash`, loaded once before the run. Remaining work is the manifest minus the rows already settled for the current model and prompt version, where settled means `done` or `dead` with the same `content_hash` as the manifest. A changed source text therefore comes back as remaining work, and a dead-lettered item is not paid for again on every restart:

```sql
SELECT m.item_id FROM manifest m
LEFT JOIN results r
  ON r.item_id = m.item_id AND r.model_id = :model AND r.prompt_version = :prompt
 AND r.content_hash = m.content_hash
 AND r.status IN ('done', 'dead')
WHERE r.item_id IS NULL;
```

## Claim and write loop

1. Select a page of remaining ids.
2. For each, look up an existing `done` row with the same `content_hash`, model and prompt version; if found, copy its output instead of calling the model.
3. Otherwise call the model, validate, and write the row in a single transaction with an upsert, so a retried or changed item updates its existing row instead of failing the primary key. Commit per item or per small group, never at the end.

```sql
INSERT INTO results (item_id, content_hash, model_id, prompt_version, status, attempts, output_json, error, input_tokens, output_tokens, updated_at)
VALUES (:item, :hash, :model, :prompt, :status, 1, :output, :error, :in_tok, :out_tok, :now)
ON CONFLICT (item_id, model_id, prompt_version) DO UPDATE SET
  content_hash = excluded.content_hash, status = excluded.status,
  attempts = results.attempts + 1, output_json = excluded.output_json,
  error = excluded.error, input_tokens = excluded.input_tokens,
  output_tokens = excluded.output_tokens, updated_at = excluded.updated_at;
```

This keeps one row per item, so the superseded output is overwritten. Add `content_hash` to the key instead if the earlier output must be kept.
4. On a validation failure, write `failed` with the error and the upsert increments `attempts`. After the attempt cap, write `dead`.

Run the writer in one process, or use a unique claim marker per worker, so two workers never pay for the same item.

## Tracking provider batches

Keep a separate table:

```sql
CREATE TABLE IF NOT EXISTS batches (
  batch_id     TEXT PRIMARY KEY,
  submitted_at TEXT NOT NULL,
  item_count   INTEGER NOT NULL,
  status       TEXT NOT NULL,
  collected_at TEXT
);
```

Insert the row immediately after submission returns. On restart, list batches that are not collected and resume polling them before submitting anything new. Results map back by custom id, which is your item id. Requests the provider reports as errored or expired go back to `pending` and are resubmitted in a later batch.

## Dead-letter and repair

```sql
SELECT error, COUNT(*) FROM results
WHERE status IN ('failed','dead') GROUP BY error ORDER BY 2 DESC;
```

Read twenty rows from the largest group before deciding on the repair. A bounded repair appends the validation error to the prompt and allows one extra attempt. If the group shares an input shape, change the prompt, bump the version and rerun that group instead.

## Audit sample draw

```sql
SELECT item_id, output_json FROM results
WHERE status = 'done' AND prompt_version = :prompt AND model_id = :model
ORDER BY random() LIMIT 300;
```

Stratify the draw when rare classes matter, so each has enough rows for its own interval. Hide the model output from the labeller, record their label beside it, and compute agreement per stratum.
