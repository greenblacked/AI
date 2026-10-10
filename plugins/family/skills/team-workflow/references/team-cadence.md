# The team cadence

## Contents

- The handoff contract
- What each stage owes
- The cadence
- Making a stall visible
- Running the profile without ceremony

## The handoff contract

For each edge in the owner table, write four things:

```text
From: Make (developer)
To: Inspect (QA, or the reviewer where there is no QA)
Artifact: the ordered change plan and the diff
First question: <the Inspect stage's First question line, verbatim>
Owner next: the named Inspect owner
```

- **From / To** — the two stages and the people.
- **Artifact** — the one document that moves; if it is not written, the handoff did not happen.
- **First question** — what the next stage must answer before anything else. This is what makes the handoff a gate rather than a notification. Copy it from the `First question` line of that stage in `family-workflow`'s stage reference rather than rewording it; the Inspect to Launch handoff opens with the go/no-go, which the Inspect owner answers once.
- **Owner next** — the person accountable for the next gate.

A handoff with no owner is where the work stalls.

## What each stage owes

| Stage | Owes the next stage |
| --- | --- |
| Frame | A testable success criterion and a named slice |
| Architect | A design the next stage can build, and the hard-to-reverse choice |
| Make | A plan the reviewer can follow, and a working tree |
| Inspect | Criterion-by-criterion evidence, ranked findings, and the go/no-go with evidence, owned by the Inspect owner |
| Launch | A path, a signal, a rollback and an owner |
| Yield | A change to the frame's checklist, not only a lesson |

## The cadence

- **Per slice:** the six stages, with the handoffs above.
- **Weekly:** a Yield touchpoint — what worked, what stalled, what the frame should check next. Fifteen minutes.
- **Per incident:** `postmortem` feeds the next Yield; the fix is a stage's gate, not a reminder.
- **Per quarter:** `delivery-review` reads the retros for the pattern the weekly touchpoints are too close to see.

The cadence keeps Yield scheduled. A team that retrospects only after an incident learns only from failure.

## Making a stall visible

A stage stalls when its artifact does not exist. Track the artifacts, not the meetings:

| Artifact missing | The stall is |
| --- | --- |
| The frame | Frame is waiting on product for the problem or the criterion |
| The design note | Architect is blocked on a decision nobody will make |
| The change plan | Make is building without a shape, or the plan was never written |
| The inspection evidence | Inspect has not started, or is not reporting |
| The launch plan | Launch is unrehearsed; the rollback is unplanned |
| The retro | Yield is not happening, so the process is not learning |

A missing artifact names the stage to unblock. A missed meeting names nothing.

## Running the profile without ceremony

- Keep each artifact to what the next stage needs; a long frame is read by nobody.
- Write the handoff where the work lives — the issue, the PR, the design doc — not in a separate tracker.
- Use the stage agents (`framer`, `architect`, `maker`, `inspector`, `launcher`, `yielder`) for the depth a person would otherwise not have time for.
- Record light or full depth for each slice in the frame; a light run on a heavy slice is then a decision.
