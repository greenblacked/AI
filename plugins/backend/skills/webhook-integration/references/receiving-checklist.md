# Receiving checklist

Read this when building or reviewing the receiving side: it has the failure table and the replay procedure.

## Failure table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Signature fails only in production | Body parsed and re-serialised before verification, or a proxy altered the body | Capture raw bytes ahead of the parser; compare on the same bytes |
| Handler times out, provider retries, work done twice | Inline processing | Persist then acknowledge; unique constraint on event id |
| Order shows "paid" then reverts to "pending" | Older event applied after newer | Fetch current state or compare object version before writing |
| Event refers to a row that does not exist | Webhook beat your own commit | Retry with backoff, bounded, then dead-letter |
| Nothing arrives for days | Endpoint disabled by provider after failures | Silence alert per event type; re-enable, then replay from the provider's event list |
| Valid events rejected after a deploy | Secret changed or clock skew beyond tolerance | Check secret per environment; sync clocks; keep tolerance near five minutes |
| Duplicate effects with distinct event ids | Provider emits several events for one change | Idempotency on the business effect, not only the event id |

## Stored event table

Keep at least: provider event id (unique), event type, received time, raw body, verification result, processing status, attempt count, last error, processed time. Retain it for as long as the provider can resend or you may need to replay.

## Replay procedure

1. Pick the selection: event type and time range, or the failed status.
2. Dry run: parse and classify each event as would-apply, already-applied or invalid, with no writes.
3. Replay through the same processing path the live worker uses, in received order, at a limited rate.
4. Because processing re-fetches current state and is idempotent, replaying an event that was already applied is harmless; confirm that with one known case before the full run.
5. Record who ran it, the range and the counts.

## Reconciliation

On a schedule, list the provider's events for the last day and compare ids with the stored table. Missing ids are events that were never delivered or were rejected; fetch and process them. This catches the disabled-endpoint case without waiting for a customer to notice.
