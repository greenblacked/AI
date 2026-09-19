# STRIDE per crossing

Read this at step 2, with one boundary crossing in front of you. The six questions are
asked of the crossing — two named parties and a specific payload — not of a component.

Each category below gives the question, what a useful answer looks like, and where that
category usually bites. A quick and confident no is a good answer; write it down so the
next reader knows it was asked.

## Spoofing — can either party be impersonated?

Useful answer names what proves identity on this crossing and what happens when the proof
is absent, not merely invalid. Absent is the common gap: a handler that validates a token
when present and proceeds when it is not.

Usually bites on internal service-to-service calls, on webhooks, and anywhere identity
arrives in a header.

## Tampering — can the payload be changed in flight or at rest?

Useful answer distinguishes transport integrity from payload integrity. TLS covers the
first and says nothing about the second, which matters when a message is queued, stored
and acted on later by something that never saw the sender.

Usually bites on queues and event streams, on anything cached, and on client-supplied
identifiers that later select a record.

## Repudiation — could either party deny this happened?

Useful answer names the log, where it is written, and whether the party being held to it
can edit that log. A log a compromised process can rewrite is not evidence.

Usually bites on admin and support actions, on anything money touches, and on deletion.

## Information disclosure — who else can read this?

Useful answer covers the payload and its metadata, including where it ends up
incidentally: a log line, an error message, a URL, an analytics event, a support
transcript. Personal data landing in logs belongs to `data-privacy`; this step's job is to
notice the flow exists.

Usually bites on errors that quote input, on debug endpoints, and on any store shared
between tenants.

## Denial of service — can one party stop this working?

Useful answer names the limit and what happens at it. Unbounded is an answer, and a bad
one. Whether a limit is per tenant matters more than its value, because a shared limit
means one customer can deny service to the rest.

Usually bites on anything unauthenticated, anything that fans out, and anything that
accepts a size or a count from the caller.

## Elevation of privilege — can either party gain rights it was not granted?

Useful answer names the rights on each side and what would have to be true to move
between them. This is the category that makes the others worth exploiting, so ask it even
when the crossing looks read-only.

Usually bites where one service holds a credential broader than its own need, on paths
that skip a gateway, and on anything that takes an identifier and returns a record
without checking the caller owns it.

## Recording the answer

Per crossing, per category: the threat in one sentence naming what an attacker gains, or
a no. Then the state from step 3 of the skill, with an owner. A threat without a named
gain is a category restated, and it will be closed by whoever reads it next without
anything changing.
