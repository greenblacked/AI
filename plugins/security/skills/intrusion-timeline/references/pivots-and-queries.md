# Pivots and queries

Read this when writing log queries for a specific platform, choosing which identifiers to pivot on, or checking a timeline for gaps.

## Contents

- Pivot reliability
- Query set (AWS)
- Equivalents on other platforms
- Gap checklist

## Pivot reliability

| Identifier | Survives role hops | Spoofable by actor | Notes |
| --- | --- | --- | --- |
| Access key ID | Per key only | No | Temporary keys start with a different prefix and map to a session |
| Session name or source identity | Yes, carried in the assumed-role identity | The caller chooses a session name | Useful for linking, not for attribution |
| Source IP and ASN | Yes | Moves with infrastructure | Cluster by ASN and by user agent together |
| User agent | Yes | Easily changed | Odd or default SDK strings are leads |
| Instance or resource name | Yes | Mutable | Do not pivot on this |

## Query set (AWS, Athena over CloudTrail)

Everything this key did, in order:

```sql
SELECT eventtime, eventname, eventsource, sourceipaddress, useragent, errorcode
FROM cloudtrail_logs WHERE useridentity.accesskeyid = 'EXAMPLE_KEY_ID'
ORDER BY eventtime
```

First sighting of an address across the account (find initial access):

```sql
SELECT sourceipaddress, min(eventtime) AS first_seen, count(*) AS calls
FROM cloudtrail_logs WHERE sourceipaddress = '203.0.113.7' GROUP BY 1
```

Role assumptions by that actor (hops to new identities):

```sql
SELECT eventtime, requestparameters, responseelements
FROM cloudtrail_logs WHERE eventname = 'AssumeRole' AND sourceipaddress = '203.0.113.7'
ORDER BY eventtime
```

Persistence and tampering events:

```sql
SELECT eventtime, eventname, useridentity.arn, sourceipaddress
FROM cloudtrail_logs
WHERE eventname IN ('CreateUser','CreateAccessKey','CreateLoginProfile','UpdateAssumeRolePolicy',
  'AttachUserPolicy','PutUserPolicy','StopLogging','DeleteTrail','UpdateTrail','PutEventSelectors',
  'DeleteFlowLogs','DeleteDetector','PutBucketLifecycle')
ORDER BY eventtime
```

Failed calls (errorcode not null) show what the actor tried and was refused, which also shows what they were looking for.

## Equivalents on other platforms

- CloudTrail Lake: the same fields in SQL against an event data store; start queries with `aws cloudtrail start-query`.
- Azure: sign-in and audit logs in Log Analytics (`SigninLogs`, `AuditLogs`, `AzureActivity`), queried with KQL.
- GCP: Cloud Audit Logs exported to BigQuery or read with `gcloud logging read`; data access logs must have been enabled to exist.
- Identity providers and SaaS: export sign-in, token grant and admin-action logs; mailbox rules and OAuth consents are common persistence.

## Gap checklist

- Is data-plane logging (object-level, database, secrets reads) on for the stores in scope?
- Does log retention cover the whole window back to the earliest plausible access?
- Was a trail, flow log or detector stopped or changed during the window?
- Does each host source have the same clock as the cloud logs, and is the offset recorded?
- Are there regions or accounts with no logging at all?
Each "no" is an unknown with an owner.
