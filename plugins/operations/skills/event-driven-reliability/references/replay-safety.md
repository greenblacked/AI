# Replay Safety Review

Use this review for Pub/Sub seek or snapshot, dead-letter redrive, or any retained-event replay.

[Pub/Sub replay overview](https://cloud.google.com/pubsub/docs/replay-overview) describes seek and
snapshot behaviour and explains that replay can cause redelivery. Verify the current service
limits and the selected subscription's retention configuration rather than copying numeric
limits into the design.

Approve replay only when the record states:

- immutable start and end positions, selection criteria, expected count, and source retention;
- the event schema versions and required keys or business records remain readable;
- deduplication or business-invariant evidence covers every selected event;
- external idempotency keys remain valid, or uncertain effects have an authoritative query path;
- dry-run classifications, rate limits, durable cursor, owner, audit record, and stop conditions;
- dead-letter payload handling preserves diagnosis without exposing secrets or excess personal data.

For intentional historical recomputation, use a new consumer version and output namespace with
an effect policy that forbids live one-time actions. Do not erase live completion evidence. If
the supported deduplication horizon is shorter than source retention, shorten the replay range or
reconstruct evidence from authoritative state before execution.
