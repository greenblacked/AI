---
name: change-discipline
description: "Make any code change in an order that keeps it small and proven: size it first so the ceremony fits the change, make it work with a failing test and the smallest edit, then make it right with measurable gates on the changed functions only — CRAP score, new structural duplication and diff-scoped mutation survivors — keep a ledger of each action, reason and evidence, and stop after two failed fixes that rest on the same assumption. Use when someone says \"make this change properly\", \"add this feature with tests and quality gates\", \"keep complexity down on what I change\", or \"check the CRAP score of my diff\". Not for designing tests (test-design), restructuring with no behaviour change (refactoring), finding a bug's cause (debugging), mutation testing setup (mutation-testing), reviewing someone's diff (code-review), or turning a rule into a hook (agent-guardrails)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Change Discipline

A change is finished when its size was decided before the first edit, a test that failed for the predicted reason now passes, every function it touched meets a stated quality bar, and a ledger shows what was done, why, and what proved it.

Changes go wrong in a few repeatable ways, and most of them are about proportion. A typo gets the same ceremony as a new subsystem, so the process is abandoned the second time. A new subsystem gets the ceremony of a typo, so it ships with no test that could fail. A fix is bolted onto a design that cannot hold it, and the next requirement bolts on another. A bug fix is retried three times on the same wrong assumption, each attempt looking different and failing the same check. And quality is asserted rather than measured, so "I kept it simple" survives until someone opens the function. This skill sequences the work so the effort scales with the change, and it owns the one thing the sibling skills do not: numeric gates on the changed code.

## Scope

Use for: any change an agent or person makes to code, from a one-line fix to a feature, when the result should arrive tested, measured and explained.

Do not use for: choosing which cases a suite needs, which is `test-design`; restructuring with no behaviour change, which is `refactoring`; finding why something fails, which is `debugging`; setting up a mutation tool and judging equivalent mutants, which is `mutation-testing`; reviewing a change someone else wrote, which is `code-review`; or turning a rule into a hook or CI check, which is `agent-guardrails`. This skill decides when each of those applies and what evidence closes the phase; it does not repeat their depth.

## Workflow

### 1. Size the change first

Before any edit, write the tier on one line. The tier decides which steps run, so a typo does not pay for a feature's ceremony and a feature does not skip its gates.

| Tier | What it is | Required |
| --- | --- | --- |
| T0 | A typo, comment, or configuration value | Make the edit, run whatever already covers the file. No ledger. |
| T1 | A local fix inside one function | Reproduction or failing test, smallest edit, CRAP and mutation on that function, a two-line ledger. |
| T2 | A change across a few files, or one new behaviour | Everything in T1 plus the duplication gate, the data-shape check in step 2 and the full ledger. |
| T3 | A new capability or a cross-cutting change | Everything in T2 plus a written design sketch before the first edit, delivery in ordered steps, and a gate run after each step rather than at the end. |

When unsure between two tiers, take the higher one for anything that touches a data shape, a public signature, or state shared between callers. Re-tier whenever the change grows; a T1 that turns out to touch four files is a T2 from that point, and the ledger says when it changed.

### 2. Phase one: make it work

Reach the first correct behaviour with the least machinery.

1. **Shape the data before the logic.** Choose a representation in which an invalid state cannot be written, because that removes checks that would otherwise be scattered through the code and forgotten in one place. Validate where data enters, trust it inside, and keep the decision logic in pure functions that take values and return values. Effects stay at the edges.
2. **Test first from T1 up.** Write a test that fails, and read the failure: it must fail for the reason you predicted, not because of a typo in the test. Then make the smallest change that passes it. A test that went red for the wrong reason proves nothing when it turns green. If no honest test is possible, say so in the ledger instead of writing one that asserts nothing. Hand off to `test-design` for which cases to write.
3. **Make the smallest edit.** One decision lives in one place. If the edit needs a comment explaining that it must match another place, the decision is in two places.
4. **Subtract first.** Before adding a branch, flag, parameter or layer, ask whether deleting or simplifying something solves it. Removed code has no bugs and needs no tests.
5. **When the design cannot hold the new requirement,** sketch the design as if the requirement had existed from day one, then deliver it in steps. Bolting it on works once and makes the third requirement impossible. `references/change-ledger.md` shows how a restructure like this is recorded.
6. **A mechanical change across many sites** is done once by hand, then by a script or codemod that reproduces that one site exactly, then run on the rest. Diff the script's output against the hand edit before trusting it on the other sites; the hand edit is the specification.
7. **Retries and shared state.** An operation that may be retried or interrupted must end in the same state when it runs twice, so key the effect to something that identifies the request rather than to the attempt. Give concurrent actors separate state, and where they must share it, make one writer the structure's job rather than a convention people remember.
8. **Two failures on one premise means stop.** If two fixes rest on the same assumption and the same check still fails, do not try a third. Read `references/premise-reset.md` and test the assumption itself. Hand the isolation to `debugging`.

### 3. Phase two: make it right

1. **Fix the cause, not the symptom.** A guard that only stops the crash is a mitigation; record it as one in the ledger with the cause still open, so nobody mistakes it for the fix.
2. **Work in small units,** each verified before the next starts. A unit is whatever one test run can confirm; if a failure could come from three edits, the unit was too large.
3. **Tests state what a caller sees.** A test that would still pass if the function returned nothing is deleted or rewritten, not counted.
4. **Run three gates on the changed functions only.** Scope them to the diff rather than the repository: the gate is then achievable on legacy code, a ratchet that only tightens, and the output is short enough to read. `references/gate-tools.md` has per-language tools and a recipe that joins them.
   - **CRAP score:** complexity squared times (1 minus coverage) cubed, plus complexity. Changed functions score 10 or less unless the project sets another bar, and the bar used is written in the ledger. Lower a score by splitting the function, by adding tests, or both. A flat dispatch over many cases may be recorded as an accepted exception with its reason; a nested one may not.
   - **Structural duplication:** the diff introduces no new clone pair above the project's threshold. With no project setting, use a token-based duplicate of 50 or more tokens.
   - **Mutation:** run the mutation tool on the changed lines. Each surviving mutant and each no-coverage mutant on a changed line is killed by a test, shown equivalent, or leads to deleting the dead code it exposed. Hand setup and equivalence judgement to `mutation-testing`; this skill requires only the diff-scoped result.
5. **Refactor only under pinned behaviour:** characterise, change the structure, show the same tests pass. The mechanics belong to `refactoring`.

### 4. Phase three: practice

1. **Keep the ledger as you go,** not at the end: each action, its reason, its evidence. A ledger written afterwards records what you remember, which is what went well.
2. **Keep the working context small.** Send bulk output such as a long log or a full test run to a file or a subagent and keep the summary and the path.
3. **Clean up what you created:** scratch worktrees, temporary branches, generated files. Anything uncommitted that you did not create waits for the owner's decision and is never deleted.
4. **Commit in small ordered commits,** each saying why, what, and how it was proven. Push only where the repository's flow says to.

## Stop conditions

Each of these halts the change. Name the one that fired and wait.

- A bug fix at T1 or above has no reproduction. Without one, a green test proves nothing about the bug.
- A gate cannot run because its tool is missing, and the owner has not accepted skipping it. Report which gate and which tool; do not substitute an easier measure silently.
- The premise-reset rule fired and the assumption has not yet been tested.
- Uncommitted work belonging to someone else is in the way of the edit.

## Output format

```markdown
## Tier
[T0-T3, and any re-tiering with the point it happened.]

## What changed
[Paths and one clause each.]

## Gates
| Gate | Before | After | Bar |
| --- | --- | --- | --- |

## Ledger
[The table from references/change-ledger.md, or the two-line form for T1.]

## Open risks
[Mitigations still standing, exceptions accepted, anything not measured and why.]
```

## Anti-patterns

**Raising coverage with assertion-free tests to pass CRAP.** The score drops and the function is no safer. The mutation gate exists to catch this: such tests leave every mutant alive.

**Running the gates on the whole repository.** The first run reports hundreds of old findings, nobody reads them, and the gate is switched off. Scope to the diff and let the rest of the code improve when it is touched.

**Skipping the tier.** Applying feature ceremony to a typo trains everyone to skip the process; applying a typo's ceremony to a feature is how an untested capability ships.

**A third fix on a failed premise.** Each attempt feels different and costs an hour. Two failures on one assumption is the signal to test the assumption.

**Recording a mitigation as a fix.** The crash stops, the ledger says fixed, and the cause waits for the next incident.

**Writing the ledger at the end.** It becomes a story. Record the action and its evidence when they happen.

## Reference files

- `references/gate-tools.md` — read when about to run a gate: per-language tools for complexity, coverage, duplication and mutation, the flags that scope them to a diff where one exists, and a script that computes CRAP per changed function.
- `references/change-ledger.md` — read when starting a T1 or higher change: the ledger template and a worked T2 example.
- `references/premise-reset.md` — read when a second fix has failed on the same assumption: how to state the premise, probe it directly, and what to do with the result.
