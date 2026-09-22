# Runtime and recovery

Use this guide for live tasks that stall, fail, return late, lose their execution
context, or leave an external outcome uncertain. A paused task that must cross sessions
needs the durable checkpoint and resume procedure from `agent-handoff`.

## Runtime record

Keep one record per task attempt:

| Field | Purpose |
| --- | --- |
| Task ID | Stable logical task across retries |
| Generation | Distinguishes current and superseded attempts |
| Owner and scope | Prevents concurrent writers |
| Start revision | Detects stale output and hidden rebases |
| Runtime state | Ready, running, stop requested, quiescent, complete, failed |
| Evidence | Progress, diff, tests, external effect IDs |
| Dependencies | Controls which tasks may start or must be cancelled |

Accept a completion report only from the current generation. A superseded result may
contain a useful diff or diagnosis, but inspect and reapply it under current ownership
rather than merging it as if it still controlled the task. Generation IDs classify
reports; they do not fence a live process or prevent late writes.

## Diagnose before recovery

| Observation | Meaning | Next action |
| --- | --- | --- |
| Wait or poll timed out | No response arrived within that wait | Query state; do not infer termination |
| Worker reports blocked | Task is alive but needs an input or decision | Resolve dependency or stop cleanly |
| Runtime reports failed | Attempt ended unsuccessfully | Preserve evidence, classify, then retry or redesign |
| Runtime disappeared | Termination may be likely but writes may remain | Inspect process, repository, and external state |
| External call lost response | Outcome is uncertain | Read target state or use idempotency record before retry |
| Old generation returns | Result is stale by ownership | Quarantine and compare; never auto-integrate |

## Reassignment sequence

1. Freeze downstream tasks whose assumptions depend on the affected result.
2. Preserve the latest progress report, working diff, test output, and external effect
   identifiers.
3. Request stop through the host when supported.
4. Establish quiescence by confirming the worker and relevant subprocesses, background
   tools, and external jobs ended or were fenced. Acknowledgement that the request was
   accepted, poll silence, or unchanged files is not proof.
5. Inspect uncertain external targets before deciding whether an action needs retry.
6. Increment the generation and issue a new delegation contract with the recovered
   evidence and current base.
7. Reject late reports from the superseded generation and inspect any late writes as an
   ownership violation.

Do not reassign the same writable scope between steps 3 and 4. If quiescence cannot be
established, block the scope and escalate. A timeout is an event in the coordinator's
wait, not proof that the worker released files or resources.

## Retry policy

Retry only when the failure is plausibly transient or the contract has materially
changed. Keep repair attempts bounded. Back off when the failed dependency can be
overloaded or rate limited. Stop looping when successive attempts reproduce the same
failure; return the blocker and evidence to the coordinator.

Before retrying a mutation outside the repository, determine whether it already happened.
Prefer target-state inspection, an idempotency key, transaction record, deployment ID,
or message ID. Absence of a success response is not evidence of absence of the effect.

## Lost context during live work

Capture a durable handoff when a task cannot continue in the present session. At minimum,
the coordinator's task return points to the checkpoint and records its base revision,
scope, current generation, and unresolved dependency. The next session must reconcile
that checkpoint with the current repository and user intent before resuming; the
`agent-handoff` skill owns that procedure.

Checkpoint text is evidence about prior work. It cannot override current user direction,
project instructions, permissions, or repository state.

## Integration after recovery

Compare recovered changes against the current base and assigned scope. Re-run tests whose
code, fixtures, configuration, or dependencies changed after the recorded result. A
review becomes stale after a material change to its reviewed scope, so send the affected
raw diff back through fresh review.

Run combined repository gates after integration. Worker-local evidence helps diagnose
failures but cannot prove that shared manifests, lockfiles, generated files, or interfaces
remain consistent in the assembled change.
