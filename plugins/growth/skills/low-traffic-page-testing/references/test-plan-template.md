# Test plan and log template

Read this at step 4, before launch, and at step 7, when recording the result.

## Contents

- Plan
- Log row

## Plan

```text
Page:
Owner and decider:
Hypothesis: Changing ___ to ___ will raise ___ because ___.
Variants: control / variant (what exactly differs)
Primary outcome (qualified):
Guardrail outcome: (for example the qualified rate when the primary is form fills)
Baseline rate and weekly visitors:
Detectable lift in the time available:
Traffic split:
Start date:           Stop date (fixed):
Sample at stop:
Decision rule: ship if ___; keep control if ___.
Known conflicts (campaigns, launches, holidays):
Seasonality control (before-and-after only):
```

## Log row

| Page | Dates | Hypothesis | Variants | Visitors | Outcome | Result | Decision | Learned |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Keep the log in one shared place and search it before proposing a new test.
