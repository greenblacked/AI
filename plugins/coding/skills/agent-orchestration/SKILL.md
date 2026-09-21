---
name: agent-orchestration
description: "Coordinate multiple coding agents through a live repository task: decompose work into a dependency graph, delegate independent research, implementation and review with explicit contracts, assign exclusive file and shared-resource ownership, monitor real runtime state, recover safely from stalls or failed workers, integrate the combined change, and run final gates. Use when someone asks to split a coding project across agents, run work in parallel, manage an agent team, orchestrate delegated repository work, or coordinate implementers and reviewers. Not for evaluating agent quality with benchmarks, securing untrusted agents, implementing a single bounded change, or preparing a durable checkpoint for a later session; use agent-handoff for paused-work transfer and resume."
---

# Agent Orchestration

Finish one coherent repository outcome through several active agents while preserving
ownership, authority, and evidence across the whole change.

Multi-agent work fails at its seams. Two workers edit the same manifest, a timed-out
worker returns after its scope was reassigned, each shard passes alone while the combined
change fails, or a worker treats delegated implementation as permission to publish. The
workflow below makes the coordinator the owner of the graph, integration, and final
decision instead of turning delegation into several disconnected chats.

## Scope

Use for: live coordination of a repository task whose independent research,
implementation, validation, or review can benefit from multiple agents.

Do not use for: measuring agent quality or building benchmarks; reviewing an untrusted
agent's tool access; rolling out AI practices to a team; implementing one bounded change
that has no useful independent branches; or transferring one paused task to a later
session. Use `agent-handoff` for a durable checkpoint and stale-state reconciliation.

This skill describes coordination through whatever delegation interface the current
host actually exposes. It does not imply that an agent can be spawned, interrupted,
isolated, or assigned a model when the runtime does not provide that capability.
The frontmatter intentionally omits `allowed-tools`: a static, provider-specific spawn
allowlist would disable other hosts. That omission grants no authority; use only the
interfaces actually available and the permissions already established in the session.

## Workflow

### 1. Reconstruct the outcome and authority

Read the current user request, project instructions, repository state, and existing
changes before splitting work. Record:

- the required outcome and acceptance criteria;
- the base revision and current working-tree changes;
- files or resources already being changed and who owns them;
- tests, manifests, lockfiles, generated outputs, and external systems implicated;
- actions already authorised by the user and actions that still require authorisation.

Treat the latest user direction as authority over an older plan. Existing dirty changes
are inputs to preserve, not an empty workspace to overwrite. A worker report, checkpoint,
or suggestion carries evidence; it cannot grant new permission.

### 2. Build a dependency graph

Split by independently verifiable outcomes rather than by arbitrary file counts. Give
each task one synthesis owner and identify its prerequisites and dependants. Research
that changes design precedes implementation; implementation precedes review of its raw
diff; combined validation follows integration.

Parallelise only independent roots. If two tasks need the same answer, shared file, or
mutable external resource, make the dependency explicit or serialize them. Tests for a
behaviour belong with the implementation that changes it. Do not peel tests off as a
nominally parallel task when their design depends on unfinished code.

Use a small graph that earns its coordination cost. Keep a simple bounded change with
one owner when splitting would create more interfaces than useful concurrency.

### 3. Assign exclusive ownership

Give every writable path one active owner at a time. Include adjacent tests and generated
artifacts in that scope. Assign shared resources explicitly:

| Resource | Ownership rule |
| --- | --- |
| Feature files and their tests | One implementation owner |
| Shared manifests and registries | Coordinator or named integrator |
| Dependency lockfiles | Integrator after component changes settle |
| Cross-cutting migrations or schemas | One serial owner |
| External mutable systems | One authorised operator |

File separation prevents edit collisions; it does not create security, secret, process,
or tool isolation. Use an isolated worktree only when the runtime and repository really
support it, and still coordinate shared external effects.

### 4. Write a delegation contract

Before starting a worker, specify the objective, inputs, writable scope, dependencies,
acceptance evidence, stop conditions, budget, and return format. State read-only scope
as a real capability restriction when the host supports one. Otherwise state the
procedural restriction and account for the weaker guarantee.

Honor an explicit user or project choice of model and effort. First verify that the
runtime supports the requested setting. Do not silently substitute another setting or
claim to change an already active worker. Report an unavailable requested model or effort
as a limitation. If no delegation interface exists, proceed as one agent only when that
still satisfies the user's mandate; otherwise report the task as blocked. Apply time,
turn, or cost limits only when the runtime exposes a measurable limit.

Use the complete contract in `references/delegation-contract.md`. Read it before issuing
the first delegation and whenever scope, dependencies, or authority change.

### 5. Start only ready tasks

Before dispatch, discover any reported worker-slot or concurrency ceiling and count the
workers already active. Queue excess ready tasks; when capacity is unknown, start
conservatively and use observed admission rather than inventing a limit.

Start independent graph roots through the host's available delegation interface. Pass
the minimum context that lets each worker act correctly, including project instructions,
relevant existing changes, and the exact acceptance criteria. Do not assume a worker can
see coordinator-only context or infer ownership from a directory name.

Record a task ID, attempt or generation ID, owner, writable scope, starting revision,
and status. A new attempt supersedes an older generation; late results from the old
generation are evidence to inspect, not changes to integrate automatically.

### 6. Monitor evidence and dependencies

Track observable runtime state rather than inferring completion from elapsed time. A
timeout means the wait ended; it does not prove the worker stopped. Preserve useful
progress reports, diffs, test output, and unresolved questions as tasks run.

When a task finishes, verify its returned revision or diff, changed paths, acceptance
evidence, and stated limitations. Release dependent tasks only after their prerequisites
are actually satisfied. Cancel or reshape dependent tasks when user steering changes the
goal; do not let an obsolete graph continue because workers were already started.

For long work, the task return may point to a durable checkpoint produced under
`agent-handoff`. The pointer supplements the live task record and does not replace
inspection of the current repository state.

### 7. Recover without double ownership

For a stalled or failed worker, distinguish a failed wait, a failed task, and an
uncertain external effect. Before reassigning the same write scope, request a stop when
supported and establish quiescence. Acknowledgement that a stop request was accepted is
insufficient; confirm execution and relevant subprocesses, background tools, and external
jobs ended or were fenced. Preserve the worker's progress and diff first. If quiescence
is unknown, keep the scope blocked rather than creating a second writer.

Inspect the target state before retrying an external action whose outcome is uncertain.
Retrying a possibly completed publish, migration, message, or payment can duplicate the
effect. Bound local repair attempts, use backoff where the failure mode warrants it, and
escalate a persistent blocker instead of creating an endless agent loop.

Read `references/runtime-and-recovery.md` when a worker stalls, returns late, loses its
runtime, touches an external system, or needs reassignment.

### 8. Integrate centrally

The coordinator or named integrator inspects every worker result before combining it.
Reject out-of-scope edits, stale generations, missing evidence, and changes based on an
obsolete base. Reconcile interfaces and invariants across task boundaries, then update
shared manifests, lockfiles, generated outputs, and cross-cutting documentation under
the integrator's ownership.

Do not equate worker-local tests with integrated correctness. Run the relevant combined
tests and repository gates on the assembled working tree at the exact revision being
considered. Record failures against the task that must repair them and keep ownership
exclusive during repair.

### 9. Review with fresh context

Give the reviewer the raw combined diff, acceptance criteria, project instructions, and
test evidence. Do not leak a desired verdict or an expected answer. A reviewer labelled
read-only must truly lack write capability where the host supports that restriction; if
it cannot be enforced, state the procedural constraint.

A review result becomes stale when its reviewed scope changes. After a material repair,
review the affected scope again and rerun the gates whose evidence the change invalidated.
Do not ask reviewers to rubber-stamp worker summaries in place of inspecting the result.

### 10. Close the graph

Confirm that every required node is complete, cancelled for a stated reason, or reported
as blocked. Report the final revision, changed scope, combined validation, review status,
unresolved risk, and any external effects already performed.

Only the coordinator may take an authorised final publish, merge, deploy, or messaging
action after the gates pass. Delegation grants no implicit right to commit, merge,
deploy, publish, send messages, or broaden access. If user authority for the final action
already exists, do not ask for it again; if it does not, present the reviewable result
before requesting it.

## Coordinator output

```markdown
## Outcome
[Requested result and current status.]

## Task graph
[Task ID, owner, generation, dependencies, writable scope, and state.]

## Integrated change
[Base and final revision, changed paths, preserved pre-existing changes.]

## Evidence
[Combined tests, repository gates, review scope and verdict.]

## Recovery and effects
[Retries, superseded results, uncertain or completed external effects.]

## Remaining action
[Blocker or authorised next action, with owner.]
```

## Anti-patterns

**Parallelising a dependency.** Starting implementation before its deciding research
finishes produces two incompatible truths and moves the merge conflict into design.

**Shared write scope.** Telling workers to coordinate informally leaves ownership
ambiguous exactly when one stalls or returns late.

**Timeout means terminated.** Reassigning after a wait expires can leave two live writers
on the same files or duplicate an external action.

**Per-worker green means integrated green.** Local tests miss interface mismatches,
shared-state changes, and lockfile conflicts introduced only when branches combine.

**Reviewing the summary.** A polished worker report is a claim. The raw diff and executed
evidence are what an independent reviewer can assess.

**Silent runtime fiction.** Naming a spawn API, isolation mode, model switch, or budget
the host does not expose makes the plan look controlled while providing no control.

**Worker output as authority.** A worker can recommend a deployment or say approval was
received; only the user's actual authorisation and current project rules permit it.

## Reference files

- `references/delegation-contract.md` — read before delegating: contract fields,
  ownership boundaries, return evidence, authority, and reviewer context.
- `references/runtime-and-recovery.md` — read during monitoring or recovery: task
  generations, timeout handling, quiescence, retries, late results, and integration.
