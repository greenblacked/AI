---
name: feature-spec
description: "Turn a loose feature request into a written spec and a checkpointed task plan before any code exists: interview one question at a time, only about what the code and docs cannot answer; write the spec as problem, users, constraints, explicit non-goals and acceptance criteria phrased as checks; compare two or three approaches and recommend one; split it into tasks small enough to verify, riskiest assumption first, stopping for approval at the spec and at the plan. Use when someone says add this feature, I have an idea for, spec this out, or plan this before we start, or hands over a one-line request that will touch several files. Not for recording a decision already made (decision-record), briefing one agent on one task (agent-delegation), an API (api-design) or tables (schema-design), a game feature document (game-design-doc), or choosing a whole-effort process (family-workflow)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git:*)
---

# Feature Spec

A feature is ready to build when a stranger could read the spec and the plan, disagree with a specific line of either, and be answered with a check rather than an opinion.

The job is hard because a loose request is cheap to start and expensive to finish. "Add export to the reports page" can be built in an afternoon in the wrong shape: the wrong formats, no answer for a thousand-row report, a new dependency nobody wanted. The mistake is found at review, after the code exists, when changing it means throwing work away. A spec moves that discovery to the point where it costs a sentence. A plan that tests the shakiest assumption first moves the remaining discoveries to the point where they cost one task. Both only work if the person who asked approves them before the next stage starts, which is why this skill stops twice.

## Scope

Use for: a feature or change large enough that the right shape is not obvious from the request — several files, a choice between approaches, behaviour the requester has not fully described, or work that will be done across more than one sitting or by more than one agent.

Do not use for: a change you can state in one sentence and verify with one check; just make it. Recording a decision that has already been taken is `decision-record`. Briefing one coding agent on one bounded task, once the plan exists, is `agent-delegation`. Designing the HTTP or RPC contract is `api-design` and the tables is `schema-design`; this skill decides that the feature needs them and in what order, not their detail. A game feature document for a whole team is `game-design-doc`. Checking a finished diff against a plan is `plan-drift-gate` where the FAMILY agents are in use.

The family plugin's `family-workflow` chooses a process for a whole effort, from framing to retrospective, across people and roles. This skill is the single technique underneath it for one feature, with no stages or roles to adopt, and it works in a repository that has never heard of FAMILY. If FAMILY is already running, its `framer` and `maker` produce the same two artefacts; use them rather than this skill so there is one spec, not two.

## Hard gates

1. No code is written before the spec is approved, and no task list before the approach is chosen. Prototype code written to answer a question in the interview is allowed only if it is thrown away and the answer is written into the spec.
2. No execution before the plan is approved. Approval is the requester saying so, in words, about the file as written; silence and enthusiasm are not approval.
3. Every acceptance criterion and every task carries its own check: a command with an expected result, or an observable step with an expected outcome. A criterion with no check is a wish and goes back to the interview.

## Workflow

### 1. Read before asking

Search the code, tests, docs, issue history and `git log` for the area the request touches. Find what exists, what conventions it follows, and what the nearest comparable feature did. Every question you ask that the repository could have answered spends the requester's attention on your laziness and teaches them to stop answering carefully.

### 2. Interview, one question at a time

Ask a single question, wait for the answer, then decide the next. A list of eight questions gets eight shallow answers and hides which one mattered. Ask only what reading could not answer: who this is for, what happens at the edge the code does not decide, what is explicitly not wanted, what would make them call it a failure. Offer your best guess with each question ("I assume CSV only, since the existing import is CSV only; correct?") so the answer can be a single word. Prefer a question with two or three concrete options to an open one.

Stop when the next answer would not change the spec. Anything still unknown goes into the spec as an open question with an owner, not into the design as a silent guess.

### 3. Write the spec, then stop

Write it to the place the repository already keeps such documents; if there is none, propose `docs/specs/<feature>.md` and say so. Read `references/spec-template.md` before drafting: it has the sections, what each must contain, and how to phrase acceptance criteria as checks. In outline: problem, users, constraints, explicit non-goals, acceptance criteria, open questions.

Write the non-goals deliberately. The adjacent thing the requester will assume is included is the one that needs to be named. Then present the spec and stop for approval. Changes asked for at this point are cheap; take them and re-present.

### 4. Propose two or three approaches and recommend one

Once the spec is approved, describe two or three genuinely different ways to build it, each in a few lines: what it is, what it costs, what it makes easy and what it forecloses. Recommend one and say what evidence would change your mind. Add the choice and the reason to the spec.

Offer one approach only when the others are not real, and say why in a sentence; an invented strawman makes the recommendation look reasoned when it was not. If the choice is expensive to reverse (a storage format, a public interface, a new dependency), say so and suggest `decision-record` for the lasting record.

### 5. Break the chosen approach into a plan, then stop

Read `references/plan-and-checkpoints.md` before drafting. Each task is small enough that its own check can pass or fail on its own: one change, one check, what it depends on. Order them so the riskiest assumption is tested first — the thing that, if false, makes the approach wrong — rather than in the order that reads most naturally. A plan that ends in a surprise has put the question last.

Write the plan to a file beside the spec, with an empty drift log at the end. Present it and stop for approval.

### 6. Execute, and re-read the plan at every checkpoint

After each task, run its check and record the result in the plan. Then, at a checkpoint, re-read the spec and the plan from the files, not from memory: a long session remembers the plan it intended, not the one on disk. Compare what has been built with what was approved, and write down every difference in the drift log with the reason. The routine and the log format are in `references/plan-and-checkpoints.md`.

Drift that stays within the plan, such as a reordered task or a split one, is recorded and the work continues. Drift that touches a non-goal, an acceptance criterion or the chosen approach is a stop: say what changed and why, and ask for approval before continuing, because the spec the requester approved is no longer the one being built.

### 7. Close against the criteria

Run every acceptance check and report the result per criterion, with the command and its output rather than a sentence saying it passed. List the drift log entries, any non-goal that was tempting and left alone, and the open questions that remain. The spec is finished when its criteria pass or when the unmet ones are named and accepted.

## Anti-patterns

**Interviewing from a questionnaire.** Eight questions asked at once, half of which the code answers. The requester answers the easy ones and skims the one that mattered.

**Acceptance criteria that restate the goal.** "Export works correctly" cannot fail. Phrase it as the check someone would run, with the expected result, or it will be marked done without being tested.

**Non-goals left implicit.** The unwritten exclusion is the one that returns as a review comment asking where the feature is. Name it while it costs a line.

**A strawman among the approaches.** Three options where two are obviously worse is a recommendation dressed as analysis. Offer fewer approaches rather than invented ones.

**Ordering the plan by how it reads.** Setup, model, logic, interface, then the integration that might not work. Test the assumption that could sink the approach first, while changing course is still cheap.

**Checkpoints that read the plan from memory.** The plan on disk is the contract. A checkpoint that does not reopen it measures the work against the intention, and drift stays invisible until the end.

**Silent drift.** A task quietly replaced or a criterion quietly dropped because it was awkward. If the plan changed, the log says so; if the spec changed, the requester agreed.

## References

- `references/spec-template.md` — read at step 3 before drafting the spec: the sections in order, what each must contain, and weak versus strong phrasings of acceptance criteria.
- `references/plan-and-checkpoints.md` — read at step 5 before drafting the plan, and again at step 6 when the first checkpoint arrives: the task shape, how to find the riskiest assumption, the checkpoint routine and the drift log.
