# The six stages

## Contents

- Frame
- Architect
- Make
- Inspect
- Launch
- Yield
- How the stages connect

## Frame

**Gate:** can you state the problem, the user, the success criterion and the smallest valuable slice in one page, and does someone who did not write it agree?

### Questions it answers

- What problem, and whose? Not the feature — the problem the feature is for.
- What does "done" mean, as something observable?
- What is the smallest slice that delivers value on its own?
- What is explicitly out of scope for this run?
- What are the constraints: time, budget, platform, compliance?

**Artifact:** a one-page frame — problem, users, success criteria, slice, out of scope, constraints.

**Agent:** `framer`.

**Hands detail to:** `okr-planning` for goals and key results, `decision-record` when the frame itself is a decision, `game-greenlight` for the equivalent in a game.

**Failure it prevents:** building the wrong thing well. The most expensive stage to skip.

## Architect

**Gate:** can you name the approach, the boundaries, the interfaces and the one decision that would be hardest to reverse — and does the approach survive the constraints from Frame?

### Questions it answers

- What is the approach, and what alternatives were considered and rejected?
- Where are the boundaries: what this change owns and what it does not?
- What are the interfaces and the data it reads and writes?
- What are the failure modes, and what happens when each occurs?
- Which decision is expensive to reverse, and why is it the right one?

**Artifact:** a short design note and the ADR for the one hard-to-reverse decision.

**Agent:** `architect`.

**Hands detail to:** `api-design` and `schema-design` for interfaces and data, `decision-record` for the ADR, `threat-model` for the security surface, `auth-design` and `authorization-design` when access is involved, `plan-platform-migration` when the architecture moves a platform.

**Failure it prevents:** a change that fits today and blocks tomorrow, or an interface invented in the build.

## Make

**Gate:** is the slice broken into ordered steps, each small enough to review and to revert, each with the proof it carries?

### Questions it answers

- What is the order of the steps, and why this order?
- Which files and components does each step touch?
- What test or check proves each step?
- What is the first step that produces something demonstrable?
- What is the acceptance check for the slice as a whole?

**Artifact:** an ordered, file-level change plan, one line per step with its proof.

**Agent:** `maker` — read-only. It plans the change and checks a finished diff against the plan; the main agent applies it.

**Hands detail to:** `code-scaffold` for new structure, `test-design` for the tests, `debugging` when a step stalls, `refactoring` when a step is a cleanup, `codebase-orientation` when the code is unfamiliar.

**Failure it prevents:** the one large unreviewable commit, and the change nobody can roll back.

## Inspect

**Gate:** does the change pass its tests and a review by someone who did not write it, and is it accessible and safe for its users?

### Questions it answers

- Do the tests pass, and do they test the behaviour the frame asked for?
- What does an independent review find, by severity?
- Is it accessible — keyboard, screen reader, contrast, target size?
- Is it safe — input, secrets, permissions, dependencies?
- What was not assessed?

**Artifact:** findings by severity, each with evidence and the smallest fix.

**Agent:** `inspector`.

**Hands detail to:** `code-review` for the review, `test-design` and `e2e-testing` for tests, `accessibility-audit` for WCAG, `security-review` and `agent-security-review` for the security pass, `threat-model` when the surface changed.

**Failure it prevents:** shipping a defect the author cannot see in their own work.

## Launch

**Gate:** is there a way to release this, a way to know it worked, and a way back — all three, written down?

### Questions it answers

- How does this reach users: release, migration, cutover, mobile store?
- What is the migration for any data or schema, and can it be reversed?
- What monitoring shows whether it worked, and what is the alert?
- What is the rollback, and who decides to use it?
- What is the communication: release notes, status, support?

**Artifact:** a launch plan — migration, monitoring, rollback, comms, owner.

**Agent:** `launcher`.

**Hands detail to:** `release-strategy` for the timing and shape, `db-migration` and `cutover` for data, `ci-pipeline-design` and `gitops-operations` for the path, `instrumentation` and `slo-design` for the signals, `release-notes` for the comms, `runbook` for the operator.

**Failure it prevents:** the release with no way back, and the change nobody can tell worked.

## Yield

**Gate:** was the success criterion from Frame measured, and is there a written answer to what to keep, what to change, and what the next slice is?

### Questions it answers

- What did the success criterion actually measure?
- What went well, and what would you do differently?
- What should change in the process, not just the product?
- What is the next slice, and does it change the frame?
- What did this run cost, in time and attention?

**Artifact:** a short retro that feeds the next Frame.

**Agent:** `yielder`.

**Hands detail to:** `postmortem` when something failed in production, `delivery-review` for the delivery cadence, `status-update` for sharing the outcome, `retro`-style cadence work to `design-team-cadence` where that is the team's habit.

**Failure it prevents:** repeating the same mistake with more confidence, and a team that cannot tell whether its process works.

## How the stages connect

Each stage's artifact is the next stage's input, and each gate is a yes/no question rather than a feeling.

```text
Frame      -> problem, users, success criteria, slice
Architect  -> approach, boundaries, interfaces, the decision
Make       -> ordered steps, each with its proof
Inspect    -> findings by severity, with evidence
Launch     -> migration, monitoring, rollback, owner
Yield      -> what the outcome taught, and the next slice
                |
                v
             back to Frame
```

A run that fails a gate returns to the stage before it, not to the beginning: a Make step that will not work returns to Architect with a concrete constraint, and Architect does not re-open Frame unless the constraint invalidates the slice.
