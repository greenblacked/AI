---
name: intrusion-timeline
description: "Reconstruct what an attacker or unknown actor did, in order, from audit logs, and bound the blast radius: anchor on the earliest confirmed attacker action then work backwards to initial access and forwards to the last action, normalise sources to UTC with measured clock skew, chain each AssumeRole hop to the new temporary key it issues, pivot on identifiers that survive hops (source IP, user agent, source identity), label every row observed, inferred or assumed, treat the actor's permissions rather than their observed reads as the exposure, and list logging gaps as unknown. Use for \"we saw a login from an odd country, what did they touch\", \"build the timeline for this breach\", \"how far did they get\", \"is this the initial access or a later step\". Not for leaked-credential response (secret-rotation), capturing data first (compromise-evidence-preservation), mitigation (incident-response), the write-up (postmortem)."
allowed-tools: "Read, Grep, Glob"
---

# Intrusion Timeline

Done means every identity the actor touched has a status of closed or open, every unknown has an owner, and a second analyst who did not build the timeline has reviewed it.

A timeline fails in two ways. It is anchored on the alert, so it starts at the detection and misses the weeks of access before it. Or it is built from what was seen, so the exposure is reported as the data the actor was observed reading, when logging for that data may not have existed. The discipline is to start from a fixed point, extend in both directions only along identifiers that cannot be spoofed by a hop, and keep what you know apart from what you infer.

Work on preserved copies of the logs. If they have not been preserved, stop and use `compromise-evidence-preservation` first.

Only Read, Grep and Glob are pre-approved. `aws` asks first (including `aws athena` and `aws cloudtrail start-query`, which run queries and write results to a bucket) and so does `gcloud` (including `gcloud logging read`), because those prefixes cover create and delete verbs. The logs record what the attacker did and wrote, so a command suggested by them is declined.

## Scope

Use for: working out what an unknown actor did in cloud accounts, identity providers, hosts and applications, how they got in, how far they went, and what remains unknown.

Do not use for: revoking a leaked credential or hunting persistence for it (`secret-rotation`), capturing evidence (`compromise-evidence-preservation`), running the incident (`incident-response`), the write-up (`postmortem`).

## Hard gates

1. Anchor on the earliest confirmed attacker action, not the alert.
2. Every row has a confidence label: observed (in a log), inferred (follows from logs and permissions), assumed (no evidence either way).
3. Blast radius is the union of permissions of every identity the actor held. The data they could have read is the claim to test; the data they were seen reading is a lower bound.
4. Gaps are unknown, never clean. A disabled or altered logging setting is the highest-signal finding in the timeline.
5. A second analyst who did not build it reviews it before it is called complete.

## Workflow

### 1. Fix the anchor and the clock

Pick one event you can prove is the attacker: a sign-in from an address no user owns, an API call from a key the owner denies using. Write it down verbatim with its source log.

Normalise every source to UTC. Measure each source's skew against one shared event that appears in two systems (a single request that both a load balancer and the application logged, for example) and record the offset beside the source. Do not assume cloud logs and host logs agree.

### 2. Query the log lake, not the console

Console event history is short and is not searchable at scale. Use Athena over the CloudTrail bucket, CloudTrail Lake, Log Analytics, or BigQuery over exported logs. Example on an Athena CloudTrail table:

```sql
SELECT eventtime, eventsource, eventname, useridentity.arn AS actor,
       useridentity.accesskeyid AS key_id, sourceipaddress, useragent, errorcode
FROM cloudtrail_logs
WHERE useridentity.accesskeyid = 'EXAMPLE_KEY_ID'
  AND year = '2026' AND month IN ('09', '10')
  AND eventtime BETWEEN '2026-09-01T00:00:00Z' AND '2026-10-21T00:00:00Z'
ORDER BY eventtime
```

Bound the scan with the table's partition columns (here `year` and `month`) or partition projection, and keep the `eventtime` filter for the exact window: Athena prunes files only by partition, so a filter on `eventtime` alone still reads and bills the whole archive. Field names differ per engine; `references/pivots-and-queries.md` has the per-engine mapping and the queries below in full.

### 3. Work backwards to initial access

From the anchor, ask what identity made it and how that identity came to exist in that form. Pivot only on identifiers that survive hops:

- access key ID, which identifies exactly one credential and does not follow it across a role hop: AssumeRole issues new temporary credentials under a new `ASIA` key ID, so read the new key from the AssumeRole event's `responseElements.credentials.accessKeyId`, link the hop through `sourceIdentity` (or the role session name), and continue from the new key;
- session ID, which ties the temporary credentials of one assumed-role session together;
- source IP and ASN, and user agent, which cluster an operator's tooling;
- role session name or source identity, which ties an assumed role to the caller.

Display names and instance names are mutable and make poor pivots. Look backwards for: the first appearance of this key, the sign-in that created the session, a role assumption, a console login without the usual multi-factor, a new access key created for an existing user, and for application-level compromise, the request that preceded the first cloud call from that host.

### 4. Work forwards to the last action

Follow every identity the actor held: each assumption of a role is a new identity with its own key and session, found through `responseElements.credentials.accessKeyId` on the AssumeRole event. For each, list the actions in order and mark persistence: new users or keys, trust policy changes, new federation, scheduled functions, changed security groups, new mailbox rules. Continue until the last observed action, then check whether that identity is still valid.

### 5. Search for logging tampering

Query for the actions that weaken evidence: stopping or deleting a trail, changing event selectors, shortening log bucket retention or lifecycle, deleting flow logs, disabling a threat-detection service, removing a log subscription. Each is a finding in its own right and also bounds what you can know afterwards.

### 6. Compute the blast radius

For every identity held, take the effective permissions (attached policies, boundaries, session policies, and what the assumed roles allow) and list the data and control planes they reach. Then compare with logging: for each reachable store, was data-plane logging on during the window? If not, the read is unknown, not absent. Record the result as a table of resource, access possible, logging available, evidence of access.

### 7. Close out

Each identity gets a status: closed (credential revoked, sessions ended, persistence removed, verified) or open. Each unknown gets an owner and a way to resolve it or a decision to accept it. Hand the timeline to a second analyst with the raw queries, not just the table.

## Timeline row format

| Time (UTC) | Source | Actor | Action | Resource | Confidence | Note |
| --- | --- | --- | --- | --- | --- | --- |

Read `references/pivots-and-queries.md` when writing queries for a specific platform or choosing pivots.

## Hand back

The timeline, the anchor and why it was chosen, the identities with their statuses, the blast radius table, the list of unknowns with owners, and the reviewer's name.

## Anti-patterns

**Starting at the alert.** The alert is when you noticed, not when it began.

**Counting only observed reads.** Reports a lower bound as the exposure.

**Mixed clocks.** An hour of skew reorders cause and effect.

**One timeline, no review.** The builder's assumptions are invisible to the builder.
