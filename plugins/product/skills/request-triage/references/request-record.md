# Request record

## Contents

- Record fields
- The blocker conversation
- Reply templates
- Monthly review queries

## Record fields

Two tables keep the merge honest: one row per job, one row per customer attached to it.

| Field | Table | Notes |
| --- | --- | --- |
| `job_id` | job | Stable id |
| `job_title` | job | The job in plain words, written by the triager |
| `current_workaround` | job | What customers do today |
| `disposition` | job | now, planned, exploring, declined, redirected-to-existing |
| `disposition_reason` | job | The sentence the requester can repeat |
| `disposition_date` | job | Date the reply was sent |
| `next_step`, `next_step_date` | job | Required when disposition is exploring |
| `job_id`, `account_id` | ask | One row per account per job |
| `requester` | ask | Person inside your company who filed it |
| `customer_quote` | ask | Verbatim words, including the feature they named |
| `received_date` | ask | Starts the five-working-day clock |
| `replied_date` | ask | Date this requester was sent the disposition; empty until then |
| `relationship` | ask | customer or prospect |
| `installed_arr` | ask | Current contract value, zero for a prospect |
| `pipeline_arr` | ask | Value of the open deal, zero when none |
| `blocker` | ask | verified, claimed or none |
| `blocker_evidence` | ask | Link to the email, redline or order-form clause; required when verified |
| `segment` | ask | Your segment definition, so concentration shows |

## The blocker conversation

The requester asks the customer, in these words or close to them:

1. "Tell me about the last time you needed this. What were you doing, and what did you do instead?"
2. "If we never build it, what will you do?"
3. "Would you sign (or renew) without it?"
4. If the answer to 3 is no: "Could you put that in writing for us, so our product team sees it in your words?"

A customer who will not put it in writing is telling you something too. Record the answer as claimed and move on; do not ask the rep to argue the point.

## Reply templates

Keep each to a few sentences. Send to the requester, who forwards or paraphrases to the customer.

### Now

```text
We are building this now. The job as we understand it: [job]. We expect it to reach
customers in [release or month]. [Customer] will hear from [owner] when it ships.
```

#### Planned

```text
This is on the roadmap for [quarter or half]. The job as we understand it: [job].
We will confirm a date once the work is scheduled; until then, [workaround] is the
best way to do it.
```

##### Exploring

```text
We think this is a real need and do not yet understand it well enough to commit.
Next step: [interviews / data pull / test], finishing by [date]. We will come back
to you then with planned or declined.
```

###### Declined

```text
We are not going to build this. [Reason rooted in strategy, segment or cost, one
sentence.] For now, [workaround or partner integration] is the closest option.
We will tell you if that changes.
```

###### Redirected to existing

```text
This can be done today: [steps or link]. If that does not cover the job -- [job] --
reply with what is missing and we will reopen it.
```

## Monthly review queries

Written in standard SQL against the two tables above. Adapt names to your tracker's export.

Top jobs by distinct accounts and installed ARR. The child rows are collapsed to one row per job and account first, because an account that filed the same job twice would otherwise be counted twice in every sum. `MAX` keeps the one value those repeated asks restate:

```sql
WITH per_account AS (
  SELECT job_id,
         account_id,
         MAX(CASE WHEN relationship = 'customer' THEN 1 ELSE 0 END)            AS is_customer,
         MAX(CASE WHEN relationship = 'customer' THEN installed_arr ELSE 0 END) AS installed_arr,
         MAX(pipeline_arr)                                                      AS pipeline_arr,
         MAX(CASE WHEN blocker = 'verified' THEN 1 ELSE 0 END)                  AS verified
  FROM ask
  GROUP BY job_id, account_id
)
SELECT j.job_id,
       j.job_title,
       COUNT(*)            AS accounts,
       SUM(p.is_customer)  AS customers,
       SUM(p.installed_arr) AS installed_arr,
       SUM(p.pipeline_arr)  AS pipeline_arr,
       SUM(p.verified)      AS verified_blockers
FROM job j
JOIN per_account p ON p.job_id = j.job_id
GROUP BY j.job_id, j.job_title
ORDER BY accounts DESC, installed_arr DESC;
```

`accounts` includes prospects; `customers` counts only existing ones. Blank `relationship` or ARR values should be fixed in the tracker, not coalesced here.

Share of blockers that are verified, over the last quarter (this reads the current value only, so it does not measure claimed asks upgraded to verified; to measure that, record the first blocker value and the deal outcome as extra fields):

```sql
SELECT SUM(CASE WHEN blocker = 'verified' THEN 1 ELSE 0 END) AS verified,
       SUM(CASE WHEN blocker IN ('verified', 'claimed') THEN 1 ELSE 0 END) AS claimed_or_verified
FROM ask
WHERE received_date >= DATE '2026-07-01'   -- first day of the quarter under review
  AND received_date <  DATE '2026-10-01';  -- first day of the next one, so a review run in October counts no October asks
```

Requests without an answer, checked per ask rather than per job, because a requester attached after the job was decided has a job with a `disposition_date` and still has not heard anything:

```sql
SELECT a.job_id, j.job_title, a.account_id, a.requester, a.received_date
FROM ask a
JOIN job j ON j.job_id = a.job_id
WHERE a.replied_date IS NULL
ORDER BY a.received_date;
```

Count working days in your tracker or spreadsheet rather than in SQL, because date functions and holiday calendars differ between databases; anything past five working days is overdue.
