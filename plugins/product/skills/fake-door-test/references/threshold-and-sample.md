# Threshold, sample size and copy

## Contents

- Threshold from the value of the build
- Sample size
- Reading the result
- Follow-up page copy
- Responder email

## Threshold from the value of the build

Fill this in and date it before the door exists.

| Line | Value | Source |
| --- | --- | --- |
| A. Build cost (engineering, design, first year of upkeep) | 120,000 | Estimate from the team |
| B. Gross margin per customer over the payback period | 6,000 | Finance, from the nearest existing plan |
| C. Customers needed to pay back: A / B | 20 | |
| D. Assumed share of costly actions that become customers | 25% | Assumption: state the comparable it came from |
| E. Costly actions needed: C / D | 80 | |
| F. Qualified people you can reach in the period | 10,000 | Traffic or user counts for the target segment |
| G. Threshold: E / F | 0.8% | |

Line D carries most of the uncertainty. If you have no comparable, run the calculation at two values (for example 15% and 35%) and take the stricter threshold, so the test fails a build that only pays back under the optimistic assumption.

## Sample size

For a threshold `t` and a chosen margin `m` (half-width of the 95% interval), the normal approximation gives:

```text
n = 1.96^2 * t * (1 - t) / m^2
```

Setting `m = t / 2` means a result exactly at the threshold has an interval whose lower end sits at about half the threshold, which is enough to tell "at threshold" from "half of it". With that choice the formula simplifies to `n = 15.37 * (1 - t) / t`, rounded up.

| Threshold `t` | Exposures `n` with `m = t / 2` |
| --- | --- |
| 0.5% | 3,058 |
| 0.8% | 1,906 |
| 1% | 1,522 |
| 2% | 753 |
| 5% | 292 |
| 10% | 139 |

If the reachable audience in the test window is smaller than `n`, either lengthen the window, accept a wider margin and say so in the decision rule, or recognise that a door test cannot answer the question and go to interviews instead.

## Reading the result

Use the Wilson score interval rather than the normal approximation for the reported interval, because conversion rates near zero make the normal interval run below zero.

```text
p  = x / n
z  = 1.96
centre = (p + z^2 / (2n)) / (1 + z^2 / n)
half   = z * sqrt(p(1 - p)/n + z^2 / (4 n^2)) / (1 + z^2 / n)
interval = centre ± half
```

Worked example against the 0.8% threshold and 1,906 exposures:

| Costly actions | Rate | 95% Wilson interval | Against the rule |
| --- | --- | --- | --- |
| 16 | 0.84% | 0.52% to 1.36% | Pass: at or above 0.8% |
| 9 | 0.47% | 0.25% to 0.90% | Fail: below 0.8%; the interval reaching 0.9% is not a reason to reopen it |

Exclusions come before the count: internal staff, test accounts, known bots, and visitors outside the target segment. Write the exclusion rules into the decision rule so they are not chosen after seeing which way they move the number.

## Follow-up page copy

```text
[Feature or product] isn't available yet.

We're considering building [one-sentence description of what it would do] and want
to know whether it would help teams like yours before we do.

If it would, join the early list with your work email. We'll contact you within two
days to hear how you handle [job] today, and you'll be first to try it if we build it.
We'll only use your email for this.

[Work email field]  [Join the early list]
```

For a deposit, add: the amount, that it is refundable on request at any time, and that it is refunded automatically if the product is not built by a stated date.

## Responder email

Send within 48 hours of the action, from a named person.

```text
Subject: Thanks for your interest in [feature]

Thanks for joining the list for [feature]. To be clear, it isn't built yet -- we're
deciding whether to build it, and people like you are how we decide.

Could we have 20 minutes in the next week? I'd like to hear about the last time you
needed to [job] and how you handled it. [booking link]

If you'd rather not, no problem; we'll write when there's something to try.
```
