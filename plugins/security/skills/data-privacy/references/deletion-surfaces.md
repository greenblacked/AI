# Deletion surfaces

Read this at step 5, as a checklist. Deleting the primary row is the part everyone does.
These are the places the same record survives it, roughly in the order they are forgotten.

Work through every line and record the answer, including the ones that do not apply.
"Not applicable" written down is an answer; a line left blank is the one that fails later.

## The checklist

- [ ] **Primary store.** The row itself, hard-deleted rather than flagged.
- [ ] **Read replicas.** Usually follow automatically. Confirm rather than assume, and
      confirm the lag has passed before reporting completion.
- [ ] **Search index.** Elasticsearch, OpenSearch, Algolia, a database full-text index.
      Reindexing is asynchronous and often lags by hours, and the document persists in the
      index after the row has gone.
- [ ] **Caches.** Application cache, Redis, a CDN holding a personalised response. Each
      has its own expiry, and a long TTL outlives the deletion.
- [ ] **Analytics warehouse.** BigQuery, Snowflake, Redshift. This is usually a separate
      pipeline with a separate retention, and it is where deletion most often stops at the
      boundary because a different team owns it.
- [ ] **Event stream.** Kafka topics, an event log, an audit trail. Compacted or retained
      streams hold the payload independently of the database.
- [ ] **Object storage.** Uploads, exports, avatars, generated reports, and old backups of
      those buckets. Versioned buckets keep the previous version after a delete.
- [ ] **Logs.** Application logs, access logs, error trackers. Personal data arrives here
      through URLs, error messages and request bodies, and log retention is rarely aligned
      with data retention.
- [ ] **Third-party processors.** Anything you send data to — payment provider, email
      sender, support desk, analytics vendor. Deletion has to propagate, and each has its
      own mechanism and its own lag.
- [ ] **Local and derived copies.** Exports someone generated, a spreadsheet, a fixture in
      a test database seeded from production.
- [ ] **Backups and the restore path.** The one below.

## The restore path

A backup usually cannot be edited. Rewriting one to remove a record destroys its integrity
and often its restorability, so the answer is not to edit it.

The workable pattern is a suppression list: a record of every erasure, consulted by the
restore procedure and re-applied after any restore completes. Three things make it work:

- It is kept at least as long as the oldest backup that could still be restored. A
  suppression list shorter than backup retention has a window where restores undo
  erasures.
- It holds the minimum needed to re-apply the erasure, usually an identifier and a date.
  It is itself personal data and belongs in the inventory.
- The restore runbook names it as a step. A suppression list nobody consults during a
  restore is a list, not a control.

Test this the way you test the restore itself. An erasure that a restore silently undoes
is not an erasure, and the only time anyone finds out is during a restore, which is
already the worst moment to discover it.
