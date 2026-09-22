# Checkpoint Contract

Use this contract for one unfinished work item. Omit inapplicable optional fields, but do
not replace unknown values with guesses.

## Identity and authority

- Checkpoint version, durable location, content hash, writer, and UTC time.
- User goal, observable acceptance criteria, non-goals, and latest steering.
- Sources for project instructions, file ownership, constraints, and approvals.
- Existing permission scope and explicit exclusions for irreversible effects.
- Requested runtime choices beside observed runtime choices.

## Repository snapshot

- Repository root, relevant subdirectory, worktree, branch or detached state.
- Exact `HEAD`, verified base branch and base object when known.
- Staged, unstaged, untracked, submodule, and nested-repository state.
- Recoverable authorised content for staged, unstaged, untracked, binary, and new-file
  changes, preserving those states; identify user-owned changes separately.
- Snapshot commands, results, and times for volatile claims.
- Active writer or operation, affected paths, and quiescence status.

Verify that the successor can access every recovery artifact. A stat, hash, filename, or
pointer into ephemeral storage does not preserve content. If authorised content cannot
be stored durably, label it unrecoverable. Do not embed secrets, credential material,
private logs, or full environment captures; use an approved durable pointer and state
what access a successor must already possess.

## Work ledger

Give each item a stable identifier and one status:

| Status | Meaning |
| --- | --- |
| Completed | Observable outcome exists and current evidence is linked. |
| Partial | Some output exists; remaining work and intermediate safety are explicit. |
| Not started | No implementation result is claimed. |

For each item record files or artifacts, acceptance criterion, facts, decisions,
hypotheses, blockers, and next action. Keep hypotheses labelled until tested.

## Evidence ledger

For every test or verifier record the exact command, `HEAD`, dirty-tree fingerprint or
diff identity, environment needed, time, exit result, and concise material output. Mark
not run, unavailable, interrupted, and stale results explicitly.

For every external effect record the system, operation, authoritative identifier,
idempotency key if present, observed status, evidence source, and whether the result is
actual, failed, or unknown. Unknown means reconcile before retrying.

## Continuation and receipt

State one next smallest safe action with preconditions, expected observation, and stop
condition. On resume, append or update a receipt containing:

- successor session or identity and receipt time;
- current instruction and authority sources read;
- repository and external-state reconciliation result;
- stale fields and their resolution;
- one accepted work item and action performed;
- current evidence and revised next action.

The receipt records continuation; it does not expand authority or certify old tests
against a changed tree.
