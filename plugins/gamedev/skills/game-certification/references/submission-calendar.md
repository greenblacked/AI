# The submission calendar and what a rejection costs

Read this at step 1, before the checklist is built and before a date is announced. Everything here is arithmetic on numbers you do not control, which is why it comes first.

## Contents

- [The backwards plan](#the-backwards-plan)
- [The numbers to obtain, and from where](#the-numbers-to-obtain-and-from-where)
- [What each class of rejection costs](#what-each-class-of-rejection-costs)
- [Approvals that start before the build exists](#approvals-that-start-before-the-build-exists)
- [Queue seasonality](#queue-seasonality)
- [Day-one patches](#day-one-patches)
- [A worked example](#a-worked-example)

## The backwards plan

```text
release date
  − storefront release lead time          (notice for the date, pre-orders, features)
  − review turnaround × (1 + N)           (N = resubmissions you have budgeted)
  − final QA pass on the submission build
  − cert-requirement test pass            (step 5 of the skill)
  = content lock
```

Everything after the content lock is a fix to something that fails a requirement. Content, balance and polish stop there, and the team has to agree that in advance, because the pressure at that point is always to slip one more change into the build being submitted.

Plan for N of at least one on a first submission to a platform the team has not shipped to before. Budgeting zero is a decision to move the date on the first rejection.

## The numbers to obtain, and from where

| Number | Source | Note |
| --- | --- | --- |
| Review turnaround for a first submission | The platform's developer portal, and your account manager for a console | First submissions of a new title take longer than patches on every platform |
| Whether a resubmission re-enters the back of the queue | The same | Assume yes unless told otherwise in writing |
| Storefront release lead time | Portal | Pre-orders and feature slots have their own, longer, lead times |
| Rating certificate lead time | The rating board, if the automated questionnaire route does not apply | Weeks, and it needs materials — video of the most extreme content — that take time to prepare |
| Platform account and title setup | Portal | Can be weeks on consoles, and blocks the first submission entirely |
| Minimum SDK or firmware baseline, and when it next moves | Portal | A baseline that moves inside your window forces a rebuild and a retest |

Get these in writing and record them where the schedule lives. Forum answers and last year's numbers are the usual source of a date that was never achievable.

## What each class of rejection costs

| Rejection class | Fix time | Calendar cost | Preventable by |
| --- | --- | --- | --- |
| Upload-time — signing, entitlements, package identity, missing manifest | Minutes to hours | None if caught by your own upload attempt; a lost queue slot otherwise | Step 6, run once against a real upload well before submission |
| Metadata — wrong screenshot size, placeholder art, disallowed copy | Hours | A full review cycle on most storefronts | Step 7, done against the submission build |
| Declaration — privacy form, rating answer, missing disclosure | Hours | A full cycle, and a possible post-launch removal if it went unnoticed | Steps 3 and 4 with an SDK inventory |
| Behaviour — suspend, sign-out, controller, storage, network | Hours to days | A full cycle, occasionally two when the fix breaks a neighbour | Step 5 on retail hardware |
| Crash on a required configuration | Days | A full cycle plus your own regression pass | Step 5 with the full matrix |
| Policy — a mechanic or content the platform does not permit | Weeks, sometimes never | The release | Asking the platform before it is built |

The last row is the one to raise early. A monetisation mechanic, a user-generated-content feature or a content theme that a platform will not accept is not a submission problem, and it is answerable by a question to the account manager months before it is built.

## Approvals that start before the build exists

These block a first submission and have their own queues:

- Developer account and platform agreement, including any company verification.
- Title registration, product identifiers and the reserved store name.
- Devkit or test-hardware allocation, if the team does not already have retail-configuration units.
- Bank, tax and payout setup, which does not block review but does block release on several storefronts.
- Age rating account setup, separate from the platform account.
- Any licence for a middleware, engine or third-party brand that appears in the game, with the attribution the licence requires present in the build.

## Queue seasonality

Review queues lengthen predictably: before major seasonal sales, before platform holidays, and in the weeks before the industry's larger showcases when everyone submits at once. The corresponding quiet periods are the weeks immediately afterwards.

Submitting in the run-up to a sale event is the most common self-inflicted delay, and it is usually done because the team wanted to be in the sale. If the sale is the point, the submission belongs a full extra turnaround earlier, not on the deadline.

## Day-one patches

A patch that lands on release day is a second submission with its own review, and on consoles it is reviewed like any other. Plan it as a dated item rather than as a safety net, because a day-one patch that has not cleared review by release day does not exist.

What it can legitimately carry: fixes found after content lock, balance, and content that was always planned to arrive after the disc or the pre-load was built. What it cannot carry: anything that would have failed cert in the base build, because the base build still has to pass on its own.

## A worked example

A console release targeting the last week of March, with a two-week review turnaround, a two-week storefront lead time for a dated release with pre-orders, one budgeted resubmission, and a one-week final QA pass:

```text
release            last week of March
storefront lead    − 2 weeks   → mid March
review × 2         − 4 weeks   → mid February
final QA           − 1 week    → early February
cert test pass     − 2 weeks   → late January  = content lock
```

The content lock is two months before release. That number surprises people every time, and it is the entire argument for doing this arithmetic on the day the date is chosen rather than in the last month.
