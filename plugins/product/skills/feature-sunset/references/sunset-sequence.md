# The sunset sequence

Contents: stage gates, brown-out design, message templates, the weekly report, and the removal checklist.

## Stage gates

| Stage | Done when | Gate to move on |
| --- | --- | --- |
| Announce | Blocked and top accounts told by their owners; written notice sent to every affected account; docs and changelog updated | Every blocked account has an owner and a decision in the gap log |
| Close to new sign-ups | Feature unavailable to new accounts and on plan changes | Usage list is no longer growing |
| In-product warning | Users see the date and the guide at the point of use | Warning has been live for at least one full usage cycle of the feature |
| Brown-outs | Scheduled windows run as announced | No new blocked accounts found in the last window; blocked count falling on plan |
| Read-only | No new data; view and export work | Every account with stored data has been offered export, and no blocked account is unresolved (migrated, on an accepted alternative, gone, or extended to a dated end) |
| Remove | Feature, code, data, docs, price-list entry, billing item and macros gone | Removal checklist complete |

If a gate does not hold, stay at the current stage and fix the cause. Moving the end date is a last resort, announced once, with the reason.

## Brown-out design

A brown-out is a short, announced period in which the feature is off, so that unknown dependencies fail while a fix is still cheap.

- Announce each window in advance, in the in-product warning and to every affected account.
- Start short and during business hours in the main customer time zones, so someone notices and calls; lengthen later windows.
- Return a clear message during the window: what is off, until when, the end date, and the guide. For an API, return an error that says the same.
- After each window, sweep support tickets, error logs and API logs for accounts not already on the list, and add them to the classification sheet.
- Stop scheduling brown-outs once a window produces no new accounts.

## Message templates

**Account owner to a blocked or top account (call first, then this in writing):**

> We are retiring [feature] on [date]. You use it for [what they do with it], and [replacement] does not yet cover [gap]. Here is what we are doing about that: [decision and date]. I would like to agree a migration plan with you by [date]; [named person] will help.

**Written notice to every affected account:**

> [Feature] will be retired on [date]. From [date] it will no longer be available to new accounts; from [date] it will be read-only, and you can export your data until [date]. [Replacement] does [what it covers]; the migration guide is at [link]. We are retiring it because [one true sentence]. Questions go to [contact].

**In-product warning:**

> [Feature] will be retired on [date]. Move to [replacement] — guide at [link]. Export your data before [date].

## Weekly report

- Accounts by class: unaffected, replaceable, blocked; change since last week.
- Blocked accounts by gap, with decision, owner and due date.
- Usage trend: accounts and events per week.
- New accounts discovered (brown-outs, support tickets, API logs).
- Current stage, next gate and its date.

## Removal checklist

- Feature code and its configuration removed; endpoints return a clear "retired" response for a period before the routes are deleted.
- Stored data exported where offered, then deleted or retained according to the retention policy and any contract obligation.
- Documentation, help-centre pages and in-product links removed or redirected to the replacement.
- Price-list entry, billing item and quote-template line removed, so it cannot be sold.
- Support macros and sales collateral updated.
- Monitoring for the feature removed, and a watch set for errors and tickets mentioning it for a few weeks after removal.
- The decision log updated with the end date, the final counts and any accounts lost.
