# Result envelopes, pagination and errors

## Envelope for list results

```json
{
  "items": [{"key": "SUP-1042", "title": "Refund not received", "status": "open"}],
  "returned": 10,
  "total": 1240,
  "next": {"cursor": "c_9f2", "hint": "Add status or a date range to narrow 1,240 matches."}
}
```

Fields named for what they mean, a count returned and a total, and a way to continue. When `total` is expensive to compute, return `"total": 1000` with `"total_is_lower_bound": true` rather than omitting it, so the field stays numeric.

## Pagination for agents

- Default page small (10 to 25 items); let the model ask for more with the cursor.
- Prefer refinement hints to deep paging: a model that pages through 1,240 rows is spending its context on a search that a filter would finish.
- Keep cursors stable for the length of a task, and say when one has expired.
- Sort deterministically so a cursor does not skip or repeat items.

## Error templates

| Case | Message shape |
| --- | --- |
| Not found | `No ticket with key SUP-9999. Keys look like SUP-1042. Call search_tickets with a title phrase to find one.` |
| Invalid argument | `status must be one of open, pending, closed; got "done". Example: status="closed".` |
| No permission | `You do not have access to billing records for this account. Retrying will not help; tell the user access is needed.` |
| Transient | `The ticket service timed out. Retry this call once; if it fails again, tell the user the service is unavailable.` |

Do not include stack traces, internal hostnames or raw SQL. Keep errors whole under any cap.

## Handles for bulky payloads

Return `{"handle": "log_77", "bytes": 482113, "lines": 9120, "preview": "first 20 lines", "tools": ["read_range", "grep", "head", "tail"]}`. Slicing tools take the handle plus a line range or pattern and return a capped slice with the same envelope. Expire handles with the task and say so when one is gone.
