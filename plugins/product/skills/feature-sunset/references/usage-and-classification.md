# Usage and classification

Contents: choosing the window, what to count, the usage query, the classification sheet, and the blocked-gap log.

## Choosing the window

| Feature could serve | Minimum window |
| --- | --- |
| Daily or weekly work | One full quarter, to include a month-end and a quarter-end |
| Month-end or quarter-end tasks | Two full quarters |
| Annual tasks: audits, year-end reporting, annual renewals, tax | Thirteen months |

When in doubt, take the longer window. The cost of a longer query is minutes; the cost of missing an annual user is a customer who discovers the removal on the one day a year they need it.

## What to count

- In-product events that mean the feature was used, not merely seen (a report run or exported, not the menu opened).
- API calls and integration traffic attributable to an account, from API or gateway logs.
- Scheduled jobs the feature runs on the customer's behalf (scheduled exports, recurring reports), which show no user activity at all.
- Data stored in the feature, per account, that will need an export path.
- Contracts, order forms and statements of work that name the feature.

## Usage query

PostgreSQL syntax against a generic `accounts` and `events` schema; adjust table names, event names and date functions for your warehouse. The `LEFT JOIN` keeps every active account, so unaffected accounts appear with zero usage rather than disappearing.

```sql
SELECT
  a.account_id,
  a.plan,
  a.annual_revenue,
  COUNT(e.event_name)                              AS events,
  COUNT(DISTINCT e.user_id)                        AS users,
  COUNT(DISTINCT date_trunc('week', e.occurred_at)) AS active_weeks,
  MAX(e.occurred_at)                               AS last_used
FROM accounts AS a
LEFT JOIN events AS e
  ON  e.account_id = a.account_id
  AND e.event_name IN ('legacy_report_run', 'legacy_report_exported')
  AND e.occurred_at >= now() - INTERVAL '13 months'
WHERE a.status = 'active'
GROUP BY a.account_id, a.plan, a.annual_revenue
ORDER BY COUNT(e.event_name) > 0 DESC, a.annual_revenue DESC;
```

The `status = 'active'` filter leaves out paused, past-due and recently cancelled accounts that may still hold stored data or a contract naming the feature; list those separately from billing and add them to the sheet.

Run the same shape against API logs for the feature's endpoints, keyed by the account that owns the credential, and merge the two by `account_id`. An account with API use and no in-product use is the classic hidden dependency.

## Classification sheet

One row per account with any usage, plus every account whose contract names the feature.

| Account | Plan | Revenue | Users | Active weeks | Last used | API use | Stored data | Contract names it | Class | Gap (if blocked) | Decision | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Rules:

- **Unaffected** only when usage is zero across product, API and scheduled jobs for the whole window, and no contract names the feature.
- **Replaceable** only after someone has checked what this account actually does against the replacement. A feature-list comparison is not enough; ask the account if their use is unusual.
- **Blocked** when any gap remains, a contract names the feature, or retention or regulatory obligations depend on data held in it.

## Blocked-gap log

Group blocked accounts by gap, because one gap closed in the replacement usually unblocks many accounts at once.

| Gap | Accounts blocked | Revenue blocked | Decision | Owner | Due |
| --- | --- | --- | --- | --- | --- |
| Scheduled PDF export | 14 | 380,000 | Build in replacement | Reports team | Before brown-out 1 |
| Custom field in legacy report | 3 | 45,000 | Workaround via export API, guide written | Support | Announce date |
| Contract names feature until 2027 | 1 | 120,000 | Keep a read-only path for this account until contract end, then remove | Account owner and legal | Contract end |

Decisions are one of: close the gap, offer a workaround or partner, extend for a named account with an end date, or accept the loss of the account with revenue owner sign-off.
