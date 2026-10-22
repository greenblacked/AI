# Queries and tables for a stuffing response

Read this when you need the aggregation to confirm the attack type, the fields a login log must hold, or the lockout-safe rule table. The queries assume a login event table with the fields below; rename to match yours.

## Fields worth having

Timestamp, account identifier (or its hash), whether the account exists, outcome, source IP, ASN, user agent, TLS or HTTP fingerprint, device identifier, whether the device was previously seen for that account, and the session identifier so a later action can be joined to the login. If a field is missing, say so in the report; the sizing is weaker without it.

## Accounts per source and sources per account

```sql
-- sources trying many distinct accounts: the stuffing shape
SELECT source_ip, COUNT(DISTINCT account_id) AS accounts,
       COUNT(*) AS attempts,
       AVG((outcome = 'success')::int) AS success_rate
FROM login_events
WHERE ts >= now() - interval '6 hours'
GROUP BY source_ip
HAVING COUNT(DISTINCT account_id) >= 20
ORDER BY accounts DESC;

-- accounts attacked from many sources: the victim-side view
SELECT account_id, COUNT(DISTINCT source_ip) AS sources, COUNT(*) AS attempts
FROM login_events
WHERE ts >= now() - interval '6 hours' AND outcome = 'failure'
GROUP BY account_id
HAVING COUNT(DISTINCT source_ip) >= 5
ORDER BY sources DESC;
```

Choose the thresholds from the baseline window, not from this file. Run the same query on the baseline and compare the distributions.

## Success rate by fingerprint and ASN

```sql
SELECT client_fingerprint, asn, COUNT(*) AS attempts,
       AVG((outcome = 'success')::int) AS success_rate
FROM login_events
WHERE ts >= now() - interval '6 hours'
GROUP BY client_fingerprint, asn
ORDER BY attempts DESC
LIMIT 50;
```

A fingerprint with large volume and a success rate in the low single digits of percent, against a baseline several times higher, is typical of a list of old leaked pairs.

## Successes followed by a risky action

```sql
SELECT l.account_id, l.source_ip, l.ts AS login_ts, a.action, a.ts AS action_ts
FROM login_events l
JOIN account_actions a
  ON a.session_id = l.session_id
 AND a.ts BETWEEN l.ts AND l.ts + interval '1 hour'
WHERE l.outcome = 'success'
  AND l.client_fingerprint IN (/* suspect fingerprints from the previous query */)
  AND a.action IN ('email_change','password_change','payout_change','export','payment_method_add');
```

These rows are the confirmed takeovers. Start remediation with them.

## Lockout-safe rule table

| Situation | Response | Why it does not harm the owner |
| --- | --- | --- |
| Known device, correct password | Allow | Normal login |
| New device, no recent failures | Allow, notify | Most new devices are real |
| New device, recent failures on the account | Step-up challenge | Owner passes; password-only bot fails |
| Suspect fingerprint or ASN | Bot challenge, then step-up | Scoped to the campaign |
| Password in breach corpus | Require reset after verifying | Fixes the root cause |
| Same source across many accounts | Slow, then challenge | Per-source cost, not per-account lock |

## Breached-password range lookup, step by step

1. Compute SHA-1 of the password, uppercase hex.
2. Send the first five characters to the range endpoint.
3. Receive a list of suffix and count lines; compare your suffix locally.
4. Treat any non-zero count as breached. Never log the password or its full hash.
