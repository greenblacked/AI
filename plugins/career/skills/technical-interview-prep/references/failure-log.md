# Failure log

## Contents

- Template
- Causes and what they imply
- Weekly review

## Template

One row per miss. Keep it in a plain text file or spreadsheet the candidate will open every week.

| Date | Problem | Pattern | Attempt (first or redo) | Cause | One-line fix | Redo date |
| --- | --- | --- | --- | --- | --- | --- |

The one-line fix is a rule the candidate can apply next time, such as "ask whether input can be empty before coding" or "write the loop invariant as a comment".

## Causes and what they imply

| Cause | What it means | Response next week |
| --- | --- | --- |
| Did not recognise the pattern | The trigger signals for the technique are not learned | Mixed-pattern sets; before coding, write which pattern and why |
| Recognised it, could not implement | The technique is understood but not fluent | Re-type the template solution from memory on three problems |
| Implementation bug | Off-by-one, wrong update order, shadowed variable | Slower dry-runs; write the invariant before the loop |
| Missed an edge case | Empty input, single element, duplicates, overflow | Fixed edge-case checklist run before declaring done |
| Wrong complexity | Hidden cost in a library call or nested loop | State complexity before coding and recheck after |
| Ran out of time | Too long on brute force or on a wrong idea | Hard stop on exploring: at 10 minutes without a plan, ask for a hint in a mock |
| Froze | Observation anxiety rather than knowledge | Earlier and more frequent mocks; rehearse the protocol opening until it is automatic |

## Weekly review

1. Count rows by cause. The largest group is the focus for the coming week; on a tie, take the cause that recurred in redos, then the most recent.
2. List problems whose redo is due and schedule them first.
3. Check that no cause appears more than three times without a changed practice; the same miss repeating means the response is not working.
4. Compare the first-attempt pass rate with the redo pass rate. A high first-attempt rate with a low redo rate means recognition without recall; add no new problems; move the time to redos.
