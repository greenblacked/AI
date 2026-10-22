---
name: audit-trail-design
description: "Design the audit log for user and admin actions: start from the investigation questions (who did what to which record, when, from where, allowed or denied), log denials as well as successes, write state changes in the same transaction as the change, keep the trail in an append-only store separate from application logs with tamper evidence from a hash chain or write-once storage, keep secrets and full personal data out of entries, fix retention and reviewer access, and accept it only when a staged incident can be reconstructed from the trail alone. Use when someone says \"we need an audit log\", \"customers want an activity history\", \"who changed this setting\", or is adding admin, impersonation or export features. Not for operational metrics and traces (instrumentation), deciding who may act (authorization-design), or what should page someone (alert-design)."
allowed-tools: "Read, Grep, Glob, Write"
---

# Audit Trail Design

Done means someone who did not stage an incident can reconstruct it — which account did what, to which records, in which order, from where, and what they tried and were refused — using the audit trail alone, and can show that no entry was altered or removed after it was written.

The usual failure is treating the audit log as application logging with a different level. Entries go through the same pipeline, land in the same index with the same short retention, carry free-text messages nobody can query by record id, record successes but not the denied attempts that show what someone was trying, and can be deleted by the same administrators whose actions they record. The trail exists, and the first time it is needed it cannot answer the question.

## Scope

Use for: designing or reviewing an audit trail for user, administrator, support-staff and service actions in an application or platform; a customer-facing activity history; making an existing trail tamper-evident; choosing what to log for impersonation, data export, permission changes and configuration changes.

Do not use for: operational telemetry — metrics, traces and debug logs (`instrumentation`); deciding which actions a user may perform (`authorization-design`; this skill records the decision it makes); choosing what should page someone (`alert-design`); collecting audit evidence for SOC 2 or ISO 27001 (`control-evidence`, which may cite this trail).

## Hard gates

1. **Questions first.** No event is added because it is easy to emit. Each one answers a question in the investigation list.
2. **Denials are logged.** An attempt that was refused is often the earliest sign of compromise or abuse, and the trail is the only place it is recorded.
3. **No change without its entry.** A state change and its audit entry commit together, or neither does.
4. **Separate store, append-only, tamper-evident.** The people and services whose actions are recorded cannot alter or delete the record.
5. **No secrets in entries, and personal data minimised.** The audit store is retained longer and read by more people than the data it describes.
6. **Accepted by reconstruction.** The design passes when a staged incident is reconstructed from the trail, not when the schema is approved.

## Workflow

### 1. Write the investigation questions

With security, support and whoever answers customer or regulator enquiries, list the questions the trail must answer. Typical ones:

- Who changed this record or setting, when, and what was it before?
- Everything this account did between two times, including what it was refused.
- Everyone who read or exported this customer's data in a period.
- Who granted this person administrator access, and who approved it?
- What did support staff do while impersonating this user?
- Was this action taken by the user, by an administrator on their behalf, or by an automated job?

Each question names its query keys (actor, target record, tenant, time range, action type). Those keys become indexed fields, which is why this step comes before the schema.

### 2. Build the event catalogue

From the questions, list the events. The categories that nearly every system needs:

| Category | Examples |
| --- | --- |
| Authentication | Sign-in success and failure, multi-factor enrolment and reset, session revocation, password and recovery changes |
| Authorisation decisions | Denied actions at every enforcement point; allowed actions for sensitive operations |
| Privilege and membership | Role grants and removals, group changes, invitations, ownership transfers |
| Administrative and support actions | Impersonation start and end, actions taken while impersonating, account suspension, manual overrides |
| Data access | Exports, bulk downloads, report generation, API key use on sensitive scopes; individual record reads where the regime requires it (health records, for instance) |
| Configuration | Security settings, retention settings, single sign-on and integration configuration, webhook targets |
| Keys and credentials | API key creation, rotation and revocation (never the key itself) |
| The trail itself | Searches and exports of the audit log, retention changes, any access by its administrators |

The OWASP Logging Cheat Sheet's list of events to record is a useful cross-check. Do not log every read of every record by default: the volume buries the events that matter and multiplies the personal data held. Log reads where a question or a regulation needs them.

### 3. Fix the schema

Every entry carries structured fields, never a free-text sentence as its only content:

- **Actor**: stable user or service id, actor type (user, admin, support, service, job), the real actor and the on-behalf-of subject when impersonating, session or token id, authentication method.
- **Action**: a stable verb from the catalogue (`role.grant`, `export.create`), not a message string.
- **Target**: resource type, resource id, tenant.
- **Outcome**: allowed, denied or failed, with the policy or rule that decided and the reason code.
- **Context**: server timestamp in UTC from a synchronised clock, source address, user agent, request or correlation id.
- **Change**: for updates, the field names changed, with before and after values only for fields that are safe to keep.

`references/event-schema.md` has the field table, a JSON example and the content rules. Read it when writing the schema.

### 4. Design the write path

- **State changes**: write the audit entry in the same database transaction as the change, into an outbox table, and ship it from there to the audit store. That guarantees no change exists without its entry; emitting after commit loses the entry whenever the process dies between the commit and the emit.
- **Denials**: emit from the enforcement point itself, at the moment of the decision. There is no transaction to join.
- **Failure behaviour**: decide per action category. For high-risk administrative actions, refuse the action when the entry cannot be written. For low-risk user actions, buffer durably and alert on the backlog.
- **Clock**: server time only. Client-supplied timestamps go in a separate field if kept at all.

### 5. Choose the store and its tamper evidence

Keep the trail out of the application log pipeline: different store, different retention, different access. Then make it append-only and tamper-evident with at least one of:

- **Write-once storage**: S3 Object Lock in compliance mode, Azure immutable blob storage with a locked time-based retention policy, or a Google Cloud Storage bucket with a locked retention policy — in an account or project the application's administrators do not control.
- **Hash chain**: each entry stores a hash over its canonical form and the previous entry's hash, and the chain head is anchored periodically to a separate trust domain. A chain alone stops nobody who can rewrite the whole chain; the anchor is what makes rewriting detectable.
- **Database privileges**: if the trail lives in a relational table, the application role has insert only, with update, delete and truncate revoked and the table owned by a different role.

`references/tamper-evidence.md` covers each option, how to verify a chain, and the trade-offs. Read it when choosing the store.

### 6. Keep secrets and personal data out

No passwords, tokens, keys, session cookies, full card numbers or authentication secrets, ever, including inside request bodies copied into an entry. Refer to people by stable pseudonymous id, not by email or name, and resolve names at read time from the identity system. For changed fields holding personal or sensitive data, record that the field changed, not the values.

Pseudonymous ids also help with erasure: the trail can be kept for its retention period while the mapping from id to person is handled by the privacy process. That interaction is `data-privacy`'s to settle; record the decision in the design.

### 7. Set retention and reviewer access

Set one retention per category, from the strictest obligation that applies and the longest investigation you expect to run. PCI DSS v4.0 requirement 10.5.1, for example, asks for at least twelve months of audit log history with the most recent three months immediately available. Write the retention into the storage configuration, not only the policy.

Reading the trail is restricted to named roles (security, compliance, designated support leads), every search and export of the trail is itself audited, and nobody whose actions are recorded can change retention or delete entries. Customer-facing activity history is a filtered, tenant-scoped view over the same store, never a second copy that can drift.

### 8. Accept by reconstructing a staged incident

Before calling the design done, stage an incident in a test environment: one person signs in, is denied an action, gains a role through an administrator, exports data, impersonates a user through support tooling, changes a setting and reverts it. Give a second person, who was not told the script, only the audit trail and the investigation questions. They write the timeline; compare it with the script.

Every gap is a design defect: an event missing from the catalogue, a field that cannot be queried, an impersonated action attributed to the wrong actor, a denial that never arrived. Fix and repeat until the timeline matches, then verify the chain or the retention lock as part of the same test.

## What to hand back

- The investigation questions and the query keys each needs.
- The event catalogue with the categories covered and the reads deliberately not logged.
- The schema, the write path per category, and the failure behaviour chosen.
- The store, its tamper-evidence mechanism, retention per category and reviewer roles.
- The staged-incident result: the script, the reconstructed timeline and every gap closed.

## Anti-patterns

**The audit log is a log level.** It inherits the application logs' retention, access and sampling, and an operator can delete it while cleaning up disk.

**Successes only.** The trail shows the account that finally succeeded and not the four hundred refusals before it.

**Free-text entries.** "Admin updated user settings" cannot be queried by target id, and nobody can answer "who touched this record".

**Impersonation logged as the user.** Every action support staff took appears as the customer's own, which is wrong in the investigation and wrong in the customer's activity history.

**Copying the request body.** It is convenient and it puts passwords, tokens and personal data into the longest-retained store in the system.

## Reference files

- `references/event-schema.md` — read when writing the schema: field table, a JSON example, action naming, and the content rules for secrets and personal data.
- `references/tamper-evidence.md` — read when choosing the store: write-once storage options, the hash chain and its verification, database privileges, and what each does and does not protect against.
