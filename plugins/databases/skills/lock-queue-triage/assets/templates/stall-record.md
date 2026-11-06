# Lock stall record

<!-- Copy per incident and fill in. Record the chain before ending any session. -->

## Start (UTC)

When the stall began, as a UTC timestamp.

## Symptom and traffic affected

What users or jobs saw, and which tables, endpoints or queues were stuck.

## Blocking chain

Head of the chain first, with the head marked.

| Pid | State | Wait start | application_name | Owner | Query |
| --- | --- | --- | --- | --- | --- |
| (head) | | | | | |

## Decision

Wait, cancel or terminate, naming the literal pid, and who approved it.

## Timeouts set

`lock_timeout`, `idle_in_transaction_session_timeout`, `log_lock_waits` or the MySQL
equivalents, with the values.

## Recovery check

The query or metric that showed the waiters gone, and when.

## Follow-up

The fix at source and the person who owns it.
