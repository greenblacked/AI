---
name: qa-workflow
description: "Run FAMILY from QA: own Inspect in depth, push acceptance criteria and testability back into Frame and Architect, and own the go/no-go before Launch. Covers what QA reads at each stage, the test strategy tied to the success criteria, exploratory testing, and turning a repeated defect into a Frame check. Use this skill whenever QA is setting up how it works with a team. Triggers include a QA process, a test strategy tied to acceptance criteria, deciding what QA owns, or \"how do we run QA\" — including phrasings like \"what should our QA do\" or \"how do we stop shipping the same bug\". Do not use it for the stage definitions themselves (family-workflow), writing the tests (test-design), a WCAG audit (accessibility-audit), a solo developer (solo-development), or a developer's own loop (developer-workflow)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*)
---

# QA workflow

QA's run of FAMILY is finished when the success criteria were testable before the build, Inspect was run in depth against them, the go/no-go before Launch was QA's call with evidence, and any defect class that repeated became a check in Frame rather than a comment on the next change.

The failure is that QA is brought in at Inspect, after the frame and the architecture are fixed, to test against criteria nobody wrote down. QA then either rubber-stamps a change that meets no stated intent, or finds the real problem too late to change it cheaply. The second failure is treating QA as a test-running service: bugs are found and fixed one at a time, the same class returns next quarter, and nothing about the process changes. This skill puts QA at Frame and Architect — where testability is decided — and makes a repeated defect a change to the frame rather than to the product alone.

## Scope

Use for: a QA engineer or a team setting up how QA works across the workflow; writing acceptance criteria with the frame; reviewing a design for testability; the deep Inspect pass; the go/no-go before release; turning recurring defects into checks.

Do not use for: the stage definitions themselves, which are `family-workflow`; writing the automated tests, which is `test-design` and `e2e-testing`; a conformance audit against WCAG, which is `accessibility-audit`; a solo developer, which is `solo-development`; or a developer's own loop, which is `developer-workflow`.

## What QA owns across the stages

| Stage | QA's part |
| --- | --- |
| Frame | Help write the success criteria and the out-of-scope list, so "done" is testable |
| Architect | Read the design for testability: can each interface be exercised, each failure mode reached? |
| Make | Consume the change plan; each step's proof should be a test QA would accept |
| Inspect | Own it: strategy, `test-design`, `e2e-testing`, exploratory testing against the criteria |
| Launch | Own the go/no-go against the acceptance criteria |
| Yield | Feed the defect classes back into the frame's checklist |

Read `references/qa-loop.md` for the acceptance-criteria patterns, the test-strategy shape, the exploratory pass, and the defect-class-to-check loop.

## Workflow

### 1. Write the success criteria with Frame

A criterion QA cannot mark pass or fail is not a criterion. Rewrite it until it names a state, an input and an observable result. This is the stage QA adds the most value to, and the one it is usually absent from.

### 2. Read the design for testability

Before the build, ask of each interface and failure mode: can this be exercised, and can this be reached? A failure mode with no way to trigger it is untestable, and untestable means unverified. Raise it at Architect, not at Inspect.

### 3. Build the test strategy around the criteria

Decide what is automated and what is exploratory, and at which level. Hand the automated detail to `test-design` for the module and `e2e-testing` for the browser path. The strategy is QA's; the test code is the specialists'.

### 4. Run Inspect in depth

- The automated suite against the criteria.
- Exploratory testing aimed at the frame's riskiest assumptions.
- `accessibility-audit` for anything user-facing.
- The edge cases the plan named, and the ones it did not.

Report findings by severity, each with evidence and the smallest fix, and say what was not assessed.

### 5. Own the go/no-go

Before Launch, QA states whether the acceptance criteria are met and whether the residual defects allow a release. This is a decision with evidence, not a vote. Name the risk of anything shipping anyway.

### 6. Turn a repeated defect into a Frame check

When the same class of defect appears twice, the fix is not the second bug. Add a criterion to the frame or a check to the strategy, so the class is caught before it is built. This is QA's contribution to Yield.

## Anti-patterns

**QA at Inspect only.** Brought in to test against criteria nobody wrote, finding the real problem too late to change cheaply.

**Untestable criteria.** "Works well", "is fast", "is intuitive" — no state, no input, no result. QA cannot gate what cannot be marked pass or fail.

**Test-running as the job.** Bugs fixed one at a time with nothing learned, so the same class returns every quarter.

**Go/no-go as a vote.** Approving a release by consensus rather than against the criteria, so the decision has no evidence.

**The defect comment.** Reporting the same class on each change instead of adding the check that catches it at Frame.

## References

- `references/qa-loop.md`: read for the acceptance-criteria patterns, the test-strategy shape, the exploratory pass, the go/no-go format, and the repeated-defect-to-check loop.
