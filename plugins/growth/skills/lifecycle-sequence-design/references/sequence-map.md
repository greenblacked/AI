# One-page sequence map

Read this at step 2, when listing every flow that can message a user.

## Contents

- Map table
- Collision checks
- Priority order example

## Map table

| Sequence | Trigger | Goal event | Messages | Exit check | Channel | Owner | Holdout |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Welcome | Account created | First project created | 3 | Project exists | Email | | 5% |
| Setup nudge | No setup action for 2 days after signup | Data connected | 2 | Data connected | Email, in-app | | 5% |
| Trial conversion | Trial started | Paid plan started | 4 | Paid plan or trial cancelled | Email | | 10% |
| Win-back | No visit for 60 days | Visit and an action | 3 | Any visit | Email | | 10% |
| Newsletter | Calendar | None | 1 | Unsubscribed | Email | | none |
| Billing | Billing events | None | as needed | None | Email | | none, outside the cap |

## Collision checks

- Two sequences with the same trigger event.
- A sequence that can enrol a user already inside another one.
- A broadcast scheduled on the same day as an onboarding step.
- A win-back that triggers while a renewal, failed payment or cancellation is in progress.
- Different tools sending to the same list with no shared cap.

For each collision write which sequence wins and what happens to the other message (delay, drop or merge).

## Priority order example

1. Security and billing notices (outside the cap).
2. Onboarding.
3. Activation nudges.
4. Trial conversion.
5. Re-engagement and win-back.
6. Newsletters and promotions.
