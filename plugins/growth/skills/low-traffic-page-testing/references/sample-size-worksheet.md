# Sample size worksheet

Read this at step 1, when doing the detectability arithmetic.

## Contents

- Inputs
- Rule of thumb
- Worked table
- Reading the result

## Inputs

- Weekly visitors to the page (unique, from the analytics tool, excluding staff and bots).
- Baseline rate of the chosen outcome, from at least four weeks of data.
- Weeks you can run without a conflicting launch.

## Rule of thumb

For about 80 percent power at the 5 percent two-sided significance level:

n per variant ~ 16 x p x (1 - p) / d squared

with p the baseline rate and d the absolute difference (relative lift x p). It is an approximation; confirm with a proper sample-size calculator before committing.

## Worked table

Per-variant visitors by the rule of thumb, rounded.

| Baseline | 10% relative lift | 20% relative lift | 50% relative lift |
| --- | --- | --- | --- |
| 1% | 158,000 | 40,000 | 6,400 |
| 3% | 52,000 | 13,000 | 2,100 |
| 10% | 14,400 | 3,600 | 580 |

Weeks needed = (n per variant x 2) / weekly visitors. At 3 percent and 500 visitors a week, a 50 percent lift takes about 8 weeks; a 20 percent lift about 52.

## Reading the result

- If the weeks needed for the lift you care about exceed what you can wait, choose a bigger change or a higher-frequency outcome, not a longer wait.
- A rate this low is a reason to test the outcome one step earlier in the journey, if that step is a real signal of value.
- Write down the detectability line in the test plan, so a later "no significant difference" is read as "nothing larger than this".
