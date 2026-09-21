# Delegation contract

Use this contract for each live task. Omit a field only when it truly does not apply;
silence about writable scope, evidence, or authority creates work the coordinator cannot
safely integrate.

## Contract template

```markdown
Task ID: [stable ID]
Attempt: [generation or attempt ID]
Role: [researcher / implementer / reviewer / integrator]

Objective:
[One verifiable outcome.]

Inputs:
- Base revision and current working-tree state
- Project and user instructions
- Relevant paths, prior findings, and prerequisite outputs

Ownership:
- Writable paths or mutable resources
- Read-only paths or resources
- Explicit exclusions and the owner of each shared resource

Dependencies:
- Must be complete before start
- Downstream tasks this result unblocks

Acceptance evidence:
- Behaviour or finding that must be demonstrated
- Tests, checks, or source citations required
- Exact revision or diff to which evidence applies

Limits and stop conditions:
- Measurable runtime budget, when supported
- Conditions requiring return to the coordinator
- Actions that require separate user authorisation

Return:
- Status: complete, blocked, failed, or stopped
- Revision and changed paths, or sources and findings
- Commands actually run and their results
- Unresolved risks, assumptions, and external effects
- Checkpoint pointer when durable handoff is needed
```

## Contract rules

**One objective, one owner.** A worker may perform several steps, but one person owns the
synthesis and produces one assessable result. Split unrelated outcomes into separate
tasks rather than accepting a partial bundle with unclear completion.

**Inputs include current state.** Give the starting revision and relevant dirty changes.
An agent working from a clean-base assumption can overwrite user work while satisfying
the textual objective.

**Ownership names files and resources.** Directory-level scope is acceptable when it is
exclusive and precise. Name adjacent tests, snapshots, generated outputs, manifests,
lockfiles, databases, deployment targets, and communication channels separately.

**Tests are part of implementation.** The worker changing behaviour owns the tests that
demonstrate it unless a dependency makes that impossible. The integrator owns combined
validation and cross-cutting generated state.

**Read-only has two meanings.** Prefer a host-enforced capability restriction. If the
runtime cannot remove write tools, describe read-only as a procedural rule and do not
claim isolation that does not exist.

**Evidence binds to a revision.** Record the diff or revision tested. A passing result
from before a repair cannot validate the repaired files.

**Limits must be observable.** A deadline, turn count, or cost ceiling only controls work
when the host reports or enforces it. Otherwise use explicit check-in and stop conditions.

**Authority stays with the user and coordinator.** Delegating a mutation inside the
repository does not authorise commits, pushes, merges, deployments, messages, account
changes, or new access. Pass through authority the user already granted, without asking
again, and reserve every broader action.

## Role-specific additions

| Role | Add to the contract |
| --- | --- |
| Researcher | Required primary evidence, decision it informs, no-write capability |
| Implementer | Exact writable paths, tests owned, interface assumptions |
| Reviewer | Raw diff, acceptance criteria, review scope, enforced read-only status |
| Integrator | All worker revisions, shared files owned, combined gates |

For an independent review, omit the implementer's preferred verdict and proposed answer.
Give the reviewer the problem, acceptance criteria, raw change, and evidence so the
reviewer can reach a fresh conclusion.
