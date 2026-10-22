# Health score back-test

## Contents

- Candidate signals
- Building the score
- Replay procedure
- Leakage traps
- Results table and decision rules

## Candidate signals

Prefer signals that change before a customer decides, measured against the account's
own history rather than an absolute level, since a small account using the product
lightly every week is healthier than a large one whose use halved.

| Signal | How to measure | Why it might lead |
| --- | --- | --- |
| Core usage trend | Last 4 weeks of core actions against the previous 8 | Declining use usually precedes the decision |
| Seat utilisation | Active seats over paid seats | Unused seats are the first thing cut at renewal |
| Breadth | Number of key features used in the last 30 days | Narrow use is easier to replace |
| Champion activity | Days since the main user or buyer was last active | A departed champion leaves nobody to argue for renewal |
| Support signal | Severity-weighted tickets and reopened tickets in the last 60 days | Unresolved pain accumulates |
| Relationship | Days since the last meaningful contact with a decision-maker | A silent account cannot be saved by surprise |
| Payment | Failed payments, late invoices | Can signal distress or disengagement |

## Building the score

Start simple: a few signals, each banded into healthy, watch and at risk with
thresholds set from the distribution of retained accounts, and a rule for combining
them (for example, at risk if two or more signals are at risk). A model fitted to the
data can come later; a rule the success team can explain is used more than a number
they cannot.

## Replay procedure

1. Choose the back-test window: the last four to six quarters. Four is the minimum: precision needs a
   two-quarter outcome horizon and leaves out flags raised in the last two quarters, so a
   shorter window has too few scorable flags.
2. List every account that churned in the window with its decision date (the
   cancellation notice, the non-renewal notice or the downgrade request), and every other
   account active at any point in the window. Replay all of them, not a matched sample of
   renewers: choosing renewers by outcome over-represents churners and adds survivor
   selection.
3. For each week in the window, compute each account's score using only data available
   at that week. Store the weekly snapshots.
4. For each churner, find the first week the score entered at-risk and stayed there
   until the decision. Lead time is the decision date minus that week. A churner never
   flagged has no lead time and counts as missed.
5. For each week, count accounts flagged at-risk, and of those, how many churned within
   the following two quarters. For precision, count each account once, at its first
   flag; an account flagged for twelve weeks otherwise counts twelve times. If sampling cannot be avoided, weight each sampled renewer by the inverse of its
   sampling fraction before computing precision and weekly workload; unweighted, precision
   reads too high and workload too low. Leave out
   flags raised in the last two quarters of the window, which have not had two quarters
   to resolve and would read as false alarms.

## Leakage traps

- Signals computed from data written after the decision: exit surveys, cancellation
  reasons, renewal opportunity stages updated after notice.
- Thresholds tuned on the same churners being tested. Tune on an earlier window, test on
  a later one.
- Using contract end as the decision date, which adds months of free lead time.
- Survivors only: computing usage norms from accounts still active today.

## Results table and decision rules

| Measure | Value |
| --- | --- |
| Churners in window | |
| Share flagged at all before the decision | |
| Median lead time of flagged churners | |
| Share of churners flagged at least 30 days ahead | |
| Precision: flagged accounts that churned within two quarters | |
| Average accounts flagged per week | |
| Revenue covered by churners flagged at least 30 days ahead | |

Decision rules:

- **Discard or rebuild** when the median lead time is under 30 days. The score is
  describing decisions already made.
- **Discard or rebuild** when under half of churners were flagged at least 30 days
  ahead, even if the median lead time of those flagged looks fine: the median ignores
  every churner the score missed.
- **Rebuild** when the weekly flagged count is more than the team can work, whatever the
  lead time; lower the sensitivity or narrow the segment.
- **Keep, provisionally,** when lead time and workload are both acceptable. Re-run the
  back-test every quarter on the newest churners, because a score's lead time decays as
  the product and the customer base change.
