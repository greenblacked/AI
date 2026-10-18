# Checkpoint Contract

Use this contract for one unfinished work item. Omit inapplicable optional fields, but do
not replace unknown values with guesses.

## Contents

- [Identity and authority](#identity-and-authority)
- [Repository snapshot](#repository-snapshot)
- [Work ledger](#work-ledger)
- [Evidence ledger](#evidence-ledger)
- [Continuation and receipt](#continuation-and-receipt)
- [Copyable checkpoint](#copyable-checkpoint)
- [Filled example](#filled-example)

## Identity and authority

- Checkpoint version, durable location, writer, and UTC time. Hash a sealed artifact
  separately, excluding its own digest field; never claim a self-referential hash.
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

## Copyable checkpoint

Fill unknown or inapplicable fields explicitly; keep recoverable content in durable
artifacts referenced below rather than substituting a filename for the content.

```markdown
Version/location/writer/UTC: [version; durable URI; identity; timestamp]
Sealed artifact digest: [algorithm/value, separately recorded; unknown/inapplicable]
Goal/acceptance/latest steering: [requested outcome; observable criteria; latest direction]
Authority: [user and project instruction sources; granted actions; excluded effects]
Runtime requested/observed: [model, effort, limits requested / verified observation or unknown]
Git: [root; worktree; branch/detached; HEAD; verified base object or unknown]
Dirty state: [staged; unstaged; untracked; submodules; nested repos; user-owned paths]
Recovery artifacts: [durable content and access for each changed state, or unrecoverable]
Snapshot: [commands, results, UTC time; active writer/paths; quiescent/unknown]
Work: [item ID; completed/partial/not started; facts vs hypotheses; blocker; next action]
Evidence: [command; HEAD/diff identity; environment; UTC; exit/output;
           fresh/stale/not run/unavailable/interrupted]
Effects: [system; action; ID/idempotency key; actual/failed/unknown; source; reconcile first?]
Next: [smallest safe action; preconditions; expected observation; stop condition]
Receipt: [successor/time; sources reread; reconciliation/stale resolution; accepted item,
          action and evidence; revised next action; pending until resumed]
```

## Filled example

```markdown
Version/location/writer/UTC: v2; docs/handoff/orders-pagination.md; agent-A; 2026-10-15T16:04:00Z
Sealed artifact digest: sha256:9f2c…; recorded in the task record; n/a for the tree itself
Goal/acceptance/latest steering: add cursor pagination to GET /orders; p95 under 200ms and
  stable ordering under concurrent inserts; user confirmed cursor, not offset
Authority: user turn 12 authorises editing app/ and tests/; deployment not authorised
Runtime requested/observed: model X, effort medium requested; observed model X, effort medium
Git: /srv/repo; worktree orders-pagination; branch feat/orders-pagination; HEAD 4a91c2e;
  base origin/main @ 46f2cd8 verified
Dirty state: staged app/orders.py; unstaged tests/test_orders.py; no untracked; no submodules
Recovery artifacts: patches/orders-staged.patch and patches/orders-tests.patch in the
  checkpoint directory, readable by the successor
Snapshot: git status --short --branch and git rev-parse HEAD at 2026-10-15T16:03Z; no active
  writer (no editor, build or job running); quiescent
Work: T2 pagination — partial; the handler paginates, its tests are not yet written; next:
  add the concurrent-insert test
Evidence: pytest tests/test_orders.py — not run (no local test environment); static read only
Effects: none; no pull request opened and no branch pushed
Next: run `pytest tests/test_orders.py::test_cursor_survives_concurrent_insert`; precondition:
  the test environment can reach its database; stop if it cannot
Receipt: pending until resumed
```
