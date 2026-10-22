# Capture and isolation

What has to be true before a replay produces diffs worth reading: the capture is safe to hold,
it covers the week, and both systems see the same world.

## Contents

- [Choosing a capture source](#choosing-a-capture-source)
- [Sanitisation checklist](#sanitisation-checklist)
- [Storage, access and retention](#storage-access-and-retention)
- [Aligning the data snapshot](#aligning-the-data-snapshot)
- [Stubbing outbound calls](#stubbing-outbound-calls)
- [The clock](#the-clock)
- [When writes can be replayed](#when-writes-can-be-replayed)

## Choosing a capture source

| Source | Gives you | Watch for |
| --- | --- | --- |
| Packet capture behind TLS termination (GoReplay `--input-raw`) | Full requests including bodies | Needs raw-socket privilege on the host; sees only the hosts it runs on, so sample across the fleet |
| Proxy or mesh access log | Method, path, query, status, sometimes headers | No bodies on most configurations; enough for GET-only APIs |
| Application-level request logging | Whatever you log, already parsed | Logging bodies in production is itself a data decision; get it approved first |
| API gateway export | Structured, often already redacted | Sampling and truncation limits differ by product; check the body size cap |

Whichever you use, record the capture's own sampling: which hosts, which hours, what share of
requests. A replay of 1% of one zone's traffic is a smaller claim than it looks.

## Sanitisation checklist

Do this on the capture host, before the file is copied anywhere:

- Remove `Authorization`, `Cookie`, `Proxy-Authorization` and every vendor API-key header.
- Remove credential-bearing query parameters (`token`, `key`, `signature`, session ids in URLs).
- Mask personal data in bodies and paths: names, email addresses, phone numbers, addresses,
  payment fields, free-text fields. Mask to the same length and character class where the
  service validates format, or the replay exercises validation errors instead of the real path.
- Keep the identity's role, tenant and permission set as metadata, so the replay can substitute
  a test identity with the same authorisation.
- Record what was removed and how, in the capture's manifest.

## Storage, access and retention

Name an owner, an access list and a deletion date before the first capture. Store captures
encrypted, outside general-purpose buckets, and delete them when the exit criterion is met or
on the deletion date, whichever comes first. The question of whether this processing is
permitted, and for how long, belongs to whoever owns data privacy; get that answer in writing
before capture, not after.

## Aligning the data snapshot

Both systems must answer from the same data. Take a snapshot at the start of the capture
window and restore it to an isolated environment for each side.

When the new system uses a different datastore or schema:

1. Run the real data migration from that snapshot, not a sample.
2. Compare row counts per table or collection and a checksum over key columns.
3. Only then replay. Diffs from a half-migrated copy belong to the migration and will be
   misread as service bugs.

Requests captured late in the window refer to records created after the snapshot. Either
restrict the replay to requests whose records existed at snapshot time, or snapshot daily and
replay each day against its own snapshot. The second is what a full weekly cycle usually needs.

## Stubbing outbound calls

Record each outbound response once and serve the same recording to both sides. A live search
cluster, pricing service or third-party API returning different answers a minute apart produces
diffs that have nothing to do with the rewrite.

Where the new system calls different endpoints for the same information, map the recordings
explicitly and note the mapping as an assumption in the report. Where it makes calls the old
system never made, those calls are themselves a finding worth listing.

Stub anything with an external side effect on both sides: email, SMS, payments, webhooks,
message publication to topics other systems consume.

## The clock

Responses that include "now", relative dates ("3 days ago"), expiry calculations or anything
derived from the current date differ between two runs by construction. Prefer pinning the clock
in both systems to the original request's timestamp where both support an injectable clock.
Where only one does, compare time-derived fields by shape (present, well formed, within the
replay window) and list them under "compared by shape only".

## When writes can be replayed

Replay writes only when all of these hold:

- Each side runs on its own copy restored from the same snapshot.
- Requests replay in their original order, serially per entity, so concurrency does not reorder
  them differently on each side.
- Every external side effect is stubbed.
- The comparison includes the resulting state, not only the response: query the affected
  records on both sides after the replay and diff those too.

If any one fails, exclude writes and say so. A clean read replay is a real result; a write
replay with an uncontrolled side effect is an incident.
