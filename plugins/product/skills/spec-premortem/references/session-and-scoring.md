# Session and scoring

## Contents

- Facilitation script
- Reason sheet
- Tripwire template
- Prediction sheet
- Worked scoring example
- Running calibration tally

## Facilitation script

Seventy-five minutes for a typical spec; scale the sorting time with the number of reasons.

| Minutes | Step | Facilitator says or does |
| --- | --- | --- |
| 0-5 | Frame | State the decision, the definition of failure, and the rules: write alone first, no rebuttals, everything gets sorted |
| 5-15 | Silent writing | "It is six months from now. This shipped and failed, as defined. Write every reason you can, one per line." |
| 15-35 | Round-robin | One reason per person per turn, written up as stated. Merge only exact duplicates. Owner may clarify facts only |
| 35-40 | Elephant call | "What do we all know and are not saying?" Offer the anonymous form |
| 40-60 | Sort | Real risk, paper tiger (needs evidence) or elephant (needs an owner) |
| 60-70 | Fix or tripwire | For each real risk, spec change or tripwire with all four parts |
| 70-75 | Predictions | Each reviewer writes three estimates alone; collect before sharing |

## Reason sheet

| # | Reason (as stated) | Raised by | Category | Evidence or owner | Next |
| --- | --- | --- | --- | --- | --- |
| 1 | Import fails on files over 50 MB, which large customers have | Support | Real risk | | Tripwire T1 |
| 2 | Competitor launches the same thing first | Sales | Paper tiger | Their changelog and hiring show no work in this area; checked 2026-10-20 | None |
| 3 | The team does not believe the 30% adoption goal | Anonymous | Elephant | Owner: product lead, raise with sponsor by 2026-10-28 | |

## Tripwire template

| Id | Risk | Metric (source) | Threshold | Check date | Owner | Action when tripped |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | Large imports fail | Import failure rate for files over 50 MB (import job logs) | Above 5% over 7 days | Day 14 and day 30 | Import team lead | Pause rollout to accounts over 1,000 seats; fix before resuming |

A tripwire is incomplete until every column is filled. If the metric's source does not exist yet, write the instrumentation task instead and give it a date before launch.

## Prediction sheet

Ask for an 80% range: the reviewer should be surprised one time in five if the actual lands outside it.

| Prediction | Reviewer | Low | High | Probability (yes-or-no events) |
| --- | --- | --- | --- | --- |
| P1: weekly active teams at day 90 | A | 120 | 260 | |
| P1 | B | 80 | 200 | |
| P2: success metric at day 90 (export completion rate) | A | 55% | 75% | |
| P3: launch ships by 2026-12-15 | A | | | 0.7 |

Record each individual estimate and the group median. Individual records are what let a reviewer learn their own calibration over time.

## Worked scoring example

At day 90:

| Prediction | Range or probability | Actual | Inside range or outcome | Brier contribution |
| --- | --- | --- | --- | --- |
| P1 (reviewer A) | 120 to 260 | 95 | No | |
| P2 (reviewer A) | 55% to 75% | 61% | Yes | |
| P3 (reviewer A) | 0.7 | Shipped 2026-12-19, late | 0 | (0.7 - 0)^2 = 0.49 |
| P4 (reviewer A, another event) | 0.9 | Happened | 1 | (0.9 - 1)^2 = 0.01 |

Reviewer A's Brier score over the two probability predictions is (0.49 + 0.01) / 2 = 0.25. A forecaster who always said 0.5 would score 0.25 on any outcome, so on this small set reviewer A's confident forecasts did no better than saying "no idea"; the late launch at 0.7 cost almost all of it. Read Brier scores over many predictions, not two.

Then list the unlisted failures, for example "support volume doubled because the new export emails confused customers; nobody raised it". These are the inputs to the next premortem's facilitation: next time, invite whoever would have seen it.

## Running calibration tally

Keep one row per premortem so calibration is visible across them:

| Premortem | Date | Ranges scored | Inside range | Share inside | Probability predictions | Mean Brier | Unlisted failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Export v2 | 2026-10-21 | 6 | 3 | 50% | 2 | 0.25 | 1 |

A share far below 80% over several premortems means ranges are too narrow; near 100% means they are too wide to inform anything.
