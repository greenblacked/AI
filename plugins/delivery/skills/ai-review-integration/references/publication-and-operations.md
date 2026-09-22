# Publication state and operations

## Run and finding identities

Derive a run key from the GitLab instance, project, merge request, immutable version
identity, reviewer policy revision, prompt revision and model configuration. Derive each
finding fingerprint in trusted code from the run key plus canonical path, side, line,
rule or category, and normalised evidence. Do not use model-provided identifiers.

Store a state machine such as:

`received -> fetched -> analysed -> validated -> publication-pending -> published`

Terminal alternatives include `stale`, `partial`, `rejected`, `budget-exhausted`,
`provider-failed` and `publication-failed`. Persist transitions atomically enough that a
worker restart cannot forget a successful write or publish an unvalidated candidate.

## Comment ownership and reconciliation

Store the GitLab object ID returned for every published discussion or note. Put a
controller-owned, non-secret marker in its visible content as a secondary correlation
hint. Markers are forgeable by contributors, so a match counts only when GitLab also
reports the configured bot as author or the stored object ID agrees. Before creating a
comment, query existing integration-owned notes or discussions and reconcile those facts.

Serialize publication per merge request. GitLab does not document an idempotency key for
creating a discussion, so this is controller-owned reconciliation rather than a platform
guarantee.

Use conditional or idempotent platform operations when the chosen API provides them.
Otherwise serialise publication per merge request and apply this rule to timeouts,
connection loss and server errors whose commit status is unknown:

1. Record the attempted fingerprint and request correlation identifier.
2. Query GitLab for the marker.
3. If exactly one matching comment exists, record success.
4. If none exists, retry only after the first request is proven not to have committed or
   the request channel has reached a defined quiescent state that prevents a late commit.
5. If absence cannot be proven, several matches exist, or the query is inconclusive,
   keep the outcome unknown, stop writing and alert for
   reconciliation.

Re-read the MR version after a successful write. The pre-write check and POST are not
atomic; if the head changed between them, mark the publication stale and use the declared
supersession policy without deleting human history. Do not delete or overwrite a
discussion containing human replies. On a new MR version,
leave old discussion history intact and publish only current findings according to the
declared supersession policy. Never mark a human thread resolved.

## Retry and budget policy

Classify failures before retrying. Retry transient fetch, provider and GitLab errors with
bounded exponential backoff, jitter and a total deadline. Honour rate-limit guidance.
Do not retry authentication, authorisation, schema, policy, invalid-anchor or stale-version
failures without a changed input or operator action.

Set per-run and aggregate limits for files, bytes, input and output tokens, findings,
provider calls, elapsed time, attempts and spend. Queue admission enforces the aggregate
limit before work starts. A retry consumes the same run budget; it does not reset it.

## Telemetry and audit

Correlate webhook delivery, run, version, provider call and publication request without
logging source, prompts, secrets or personal data. Record:

- accepted, rejected, coalesced and duplicate events;
- files complete, partial, unavailable and excluded, with reason counts;
- redaction counts and policy decisions;
- model latency, token use, cost, retry count and error class;
- candidates returned, validation rejections and published findings;
- stale runs, duplicate suppression and ambiguous writes;
- human disposition or false-positive feedback where available; and
- kill-switch state and configuration revision.

Alert on authentication failures, redaction or validation anomalies, duplicate comments,
ambiguous publication, sustained stale rate, queue age, budget pressure and provider or
GitLab error rate. Audit access to stored prompts or source excerpts if policy permits
their retention at all.

## Rollout and rollback

1. Replay redacted historical snapshots offline and exercise adversarial fixtures.
2. Run in shadow mode with no GitLab write credential; compare findings and coverage.
3. Enable advisory comments for a small project cohort with a conspicuous feedback path.
4. Expand only after predeclared precision, coverage, latency, cost and safety gates pass.

The kill switch disables trigger intake and publication independently. Rollback removes
write capability, drains or cancels queued work, and reconciles unknown publication
outcomes. It does not delete audit history or human conversations. Re-enable only with a
new configuration revision and an operator-recorded reason.
