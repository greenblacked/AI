# The QA loop

## Contents

- Acceptance criteria that gate
- Reading a design for testability
- The test strategy
- The exploratory pass
- The go/no-go
- Turning a repeated defect into a check

## Acceptance criteria that gate

A criterion QA can gate on names a state, an input and an observable result.

```text
Given <a state or input>,
When <the user does something>,
Then <the observable result>.
```

- "Works well" cannot be marked pass or fail. Neither can "is fast" without a threshold.
- One behaviour per criterion. A criterion with two "and"s is two criteria.
- Include the extremes: zero, one, many, the longest value, the failed dependency.
- Include the negative: what must not happen when the input is wrong.
- The out-of-scope list is as testable as the criteria; it is what QA will not report.

Write these with Frame, not after it. A criterion added at Inspect was a design decision made too late.

## Reading a design for testability

For each interface and each failure mode the Architect names, ask:

- **Can it be exercised?** Is there a seam, a stub or an input that reaches it?
- **Can the failure be reached?** Can the dependency be made to fail in a test?
- **Is the result observable?** Is there a value, a log or a signal that proves the behaviour?
- **Is it deterministic?** If it depends on time, order or randomness, is that injectable?

A failure mode that cannot be reached is untestable, and untestable is unverified. Raise it at Architect, where changing it is cheap.

## The test strategy

Decide the shape before writing test code:

| Level | Covers | Owner |
| --- | --- | --- |
| Unit | Logic, edge cases, the branches | `test-design` |
| Integration | Interfaces, data, failure modes | `test-design` |
| End-to-end | The user path through the real system | `e2e-testing` |
| Exploratory | The assumptions the criteria did not cover | QA |
| Accessibility | Keyboard, names, contrast, targets | `accessibility-audit` |

- Automate what is stable and repeated; explore what is uncertain and new.
- Cover every criterion at the lowest level that can prove it.
- Name what is not covered, and why — that list is QA's risk register.

## The exploratory pass

Exploratory testing is aimed, not random. Take the frame's riskiest assumptions — the ones the criteria do not fully capture — and try to break them.

- Timebox it: an hour, a charter, a target.
- Record what you did, what you found and what you could not reach.
- The output is findings, not a transcript. A finding with no reproduction is not one.

## The go/no-go

The decision that closes Inspect, with evidence. It is the first question of the Inspect to Launch handoff, which `family-workflow` defines once; QA answers it, and `launcher` takes it as input rather than answering it again.

```text
Go / No-go: <decision>
Criteria met: <which, and how each was checked>
Residual defects: <what ships anyway, its severity and its risk>
Not assessed: <what was not tested, and why>
Owner: <who makes the call>
```

- The decision is against the acceptance criteria, not a consensus. Take the evidence for "Criteria met" from `inspector` and the diff findings from `code-review`.
- A residual defect shipping is acceptable only when named with its risk and its owner.
- "Not assessed" is part of the answer. A go that implies full coverage is worse than a narrow one that states its limits.

## Turning a repeated defect into a check

When the same class of defect appears a second time, the product fix is not the whole fix.

1. Name the class: what kind of mistake is it?
2. Ask where it could have been caught: a criterion at Frame, a seam at Architect, a test at Make, a check at Inspect.
3. Add it there, and add it to the frame's checklist.
4. Report the class, not just the instance, in Yield.

This is how QA changes the process rather than only the product. A defect reported twice with no check added means the process is not learning.
