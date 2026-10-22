# Tamper evidence

What each option protects against, and what it does not. Most designs combine two: a database or stream the application writes to, and write-once storage in a separate account that the trail is shipped to and verified against.

## Contents

- [Threat to design against](#threat-to-design-against)
- [Write-once object storage](#write-once-object-storage)
- [Hash chain](#hash-chain)
- [Database privileges](#database-privileges)
- [Verifying the trail](#verifying-the-trail)
- [Choosing](#choosing)

## Threat to design against

The realistic adversaries are an administrator of the application covering their own actions, an attacker who has compromised an administrator or the application's credentials, and an operator deleting data by mistake. The design goal is that any of them can stop new entries being written (which is itself detectable as a gap) but cannot change or remove entries already written without that being detected.

## Write-once object storage

| Platform | Mechanism | Notes |
| --- | --- | --- |
| AWS | S3 Object Lock, compliance mode, with a default retention period on the bucket | In compliance mode no user, including the account root user, can delete a locked object version or shorten its retention. Governance mode can be bypassed by principals holding `s3:BypassGovernanceRetention`, so it does not meet this goal. Requires bucket versioning. |
| Azure | Immutable storage for Blob Storage with a time-based retention policy, locked | An unlocked policy can be changed or deleted; locking it is what makes it immutable. |
| Google Cloud | Cloud Storage bucket retention policy, locked with Bucket Lock | A locked retention policy cannot be removed or reduced; locking is irreversible. |

Put the bucket in a separate account, subscription or project whose administrators are not the application's administrators. Write-once storage in the same account as the application still stops deletion, but the shipping path and the bucket's configuration remain in reach of the people being audited.

Write in batches (for example one object per minute per writer) with a manifest per batch; individual objects per event are expensive and slow to list.

Retention locks are hard to undo by design. Set the retention period from the agreed policy before locking, and test in a non-production bucket first.

## Hash chain

Each entry stores:

- `hash = SHA-256(prev_hash || canonical(entry_without_hash_fields))`
- `prev_hash` = the previous entry's `hash`, or a fixed genesis value for the first entry.

Canonical serialisation matters: two serialisations of the same JSON object must hash the same, so use a defined scheme such as the JSON Canonicalization Scheme (RFC 8785) rather than whatever the library emits.

A chain detects an edited or removed entry in the middle, but someone who can rewrite the store can recompute the whole chain. The fix is anchoring: periodically (every few minutes, and at every batch boundary) write the current chain head and its sequence number to a separate trust domain — the write-once bucket above, or a different organisation's system. Rewriting the chain then disagrees with an anchor the attacker cannot change.

With several writers, keep one chain per writer or per partition, each with its own sequence number. A single global chain serialises every write.

AWS CloudTrail's log file integrity validation is a working example of the pattern: hourly digest files hold hashes of the log files delivered and the previous digest file's signature, and `aws cloudtrail validate-logs` verifies them.

## Database privileges

When the trail lives in a relational table:

```sql
-- the application connects as app_rw; the table is owned by audit_owner
REVOKE UPDATE, DELETE, TRUNCATE ON audit_event FROM app_rw;
GRANT INSERT, SELECT ON audit_event TO app_rw;
```

A revoke from `app_rw` removes only privileges granted to that role directly. Privileges it holds through `PUBLIC`, a group role it is a member of, or default privileges on the schema stay in force, so list the effective privileges (`\dp audit_event` in psql, or `has_table_privilege('app_rw', 'audit_event', 'UPDATE')`) and expect `false` for update, delete and truncate before relying on it.

This stops the application, and anyone holding its credentials, from changing history. It does not stop the table owner or a database superuser, so treat it as one layer: ship entries onwards to write-once storage and verify against it.

A trigger that raises an exception on update or delete adds a guard against mistakes by other roles, but the owner can disable triggers, so it is not tamper evidence on its own.

## Verifying the trail

Verification that never runs is not a control. Schedule it:

1. Recompute each chain from its last verified anchor and compare with the stored hashes.
2. Compare the recomputed head with the anchors in the separate trust domain.
3. Check sequence numbers for gaps per writer; a gap is a lost or removed entry.
4. Compare entry counts per period between the primary store and the write-once copy.
5. Alert the security team, not the application team, on any mismatch.

Run the same verification as part of the staged-incident acceptance test, and include a deliberate tampering step in a test environment to prove the check fails when it should.

## Choosing

| Need | Minimum |
| --- | --- |
| Small internal tool, one regime with modest requirements | Separate table with insert-only privileges, shipped daily to write-once storage in another account |
| Customer-facing product with administrator and support access | Outbox to a stream, hash chain per writer, anchors and batches in write-once storage in a separate account, scheduled verification |
| Regulated data with long retention | As above, with retention locked per category and verification evidence kept for the auditor |
