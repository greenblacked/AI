# Incrementality test design

Read this at step 4 when a channel's credit is disputed.

## Contents

- Choosing a design
- Checklist before starting
- Reading the outcome

## Choosing a design

| Design | Use when | Weakness |
| --- | --- | --- |
| Geographic holdout | the channel can be targeted by region and regions are comparable | needs matched regions and enough volume per region |
| On-off (pause) test | targeting by region is not possible | seasonality and other changes confound it |
| Audience holdout | the platform offers a built-in control group | relies on the platform's randomisation |

## Checklist before starting

1. One primary metric from the backend, such as orders per region per day.
2. A baseline period and the regional or weekly variance, so the minimum detectable effect is known.
3. Matched regions chosen on history, not on convenience.
4. A duration long enough to cover the purchase cycle, with no promotions or launches planned inside it, or applied equally to test and control.
5. A stop rule and a decision rule written down: what lift means keep, what means cut.
6. A change freeze on the other levers in the tested regions.

## Reading the outcome

Compare the test regions with control on the primary metric, with an interval, not a single point. Incremental conversions divided by spend gives the real cost per incremental acquisition, which is typically higher than the platform's figure. A result inside the noise means the channel is not shown to matter at this spend, not that it has zero effect.
