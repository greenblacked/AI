# Quarantine policy

A quarantine is a decision to stop a test blocking merges while keeping the intent to fix it. It is only that if it expires. Without an expiry it is a deletion that still consumes CI minutes and still appears as coverage, which is strictly worse than deleting the test, because a deletion is visible in a diff and a permanent quarantine is visible to nobody.

## Contents

- [What qualifies](#what-qualifies)
- [The ledger](#the-ledger)
- [Keeping quarantined tests running](#keeping-quarantined-tests-running)
- [Deriving the deadline](#deriving-the-deadline)
- [The expiry review](#the-expiry-review)
- [Deleting well](#deleting-well)
- [Reporting the ledger](#reporting-the-ledger)

## What qualifies

Quarantine a test when all three hold:

1. Its measured rate is above the ceiling derived in step 1 of the skill, over a stated number of runs. A single failure is not a rate.
2. It is not in flake class 8 — a genuine product race. A test that keeps catching a real concurrency defect is the most valuable test in the suite, and quarantining it deletes the only signal anyone has that the defect exists. Escalate that one instead.
3. Nobody can fix it inside the current piece of work. Quarantine is for deferral, not for triage convenience.

A test that fails every time is not flaky and does not belong here. It is either a real regression, which is `ci-triage`'s to classify and the owning team's to fix, or a test that no longer describes the product, which should be updated or deleted now.

## The ledger

Keep it in the repository, beside the tests, in a file that changes through pull requests. A ticket in a tracker satisfies process and is read by nobody who is about to touch the test.

```markdown
| Test | Rate | Class | Owner | Expires | Coverage at risk |
| --- | --- | --- | --- | --- | --- |
| checkout.spec.ts :: applies a promo code | 6/50 | 3 shared state | a.patel | 2026-10-13 | Promo codes are unchecked end to end; the API test covers the calculation but not the cart update. |
```

The last column is the one that does the work. It converts "we will fix this" into a statement about what is unprotected while it is out, which is the only thing that makes deletion a decision somebody is willing to take at expiry instead of a renewal nobody argues with.

Record the rate with its denominator. `6/50` and `1/50` demand different responses, and a bare percentage loses the sample size that says whether the figure means anything.

## Keeping quarantined tests running

Tag the test and exclude the tag from the blocking run, rather than skipping it:

```bash
set -Eeuo pipefail
npx playwright test --grep-invert @quarantine         # the blocking job
npx playwright test --grep @quarantine || true        # a separate, non-blocking job
```

Skipping — `test.skip` or its equivalent — stops the test executing, which stops it producing data. Once that happens nobody can tell whether the cause was fixed by some unrelated change, and the entry is renewed forever on no evidence at all. A quarantined test that keeps running accumulates exactly the statistics that will end the quarantine: a run of clean results is the argument for returning it, and a continuing failure rate is the argument for deleting it.

The non-blocking job also protects against the second failure mode, where a quarantined test silently stops compiling. A test that has not run in six weeks usually no longer runs at all.

## Deriving the deadline

There is no published figure for how long a quarantine should last, and a number borrowed from another team's blog post is an invention with a citation attached. It is the team's decision. Derive it from a cadence the team already observes, so the expiry lands on a day somebody is already looking at a list:

- One sprint, when the team runs sprints and reviews a board at the end of one.
- One on-call rotation, when the suite is owned by whoever is on call, so the expiry lands in a handover.
- One release cycle, when releases are the rhythm and the question "what is unprotected in this release" is already asked.

Pick one and use it for every entry. Per-test negotiation over the length is how the deadline stops being a constraint. What matters is far less the length than that the date exists, is in the repository, and is enforced.

## The expiry review

On the date, there are exactly two outcomes, and renewal is not one of them by default:

- **Fixed.** The cause is identified from the taxonomy, the fix is landed, and the test returns to the blocking suite. Confirm two things before it returns: a measured rate over a fresh window, not one green run, since a test that flaked at one in twenty passes a single rerun 95% of the time; and that the test still fails when the behaviour it asserts is broken, because the cheapest way to make a flaky test green is to remove its ability to fail.
- **Deleted.** Nobody has fixed it in a full cadence, which is evidence about its priority rather than about the team. Delete it and record the coverage gap.

Renewal requires new evidence: a diagnosis reached since, a dependency upgrade scheduled, a product fix in flight. Write the evidence in the ledger. A renewal with no new evidence is the failure mode this whole policy exists to prevent, and it is recognisable because the entry's text is unchanged from the last review.

Cap the ledger. A fixed maximum — a number the team picks, applied to the whole suite — means a new quarantine requires resolving an old one, which is what keeps the list from becoming a graveyard. The cap does more work than any individual deadline.

## Deleting well

A deletion is a decision about coverage and should read as one. In the commit that removes the test, say what is no longer covered and what the cheaper replacement is. Frequently the honest replacement is a lower-tier test: a case that could not be made reliable in a browser is often entirely reliable as a component or API test, covering most of what mattered at a fraction of the cost. That is the most common good outcome of an expiry, and it is `test-design`'s decision where the replacement belongs.

A deletion with no note is indistinguishable a year later from a test that was lost in a merge.

## Reporting the ledger

Publish two numbers alongside the suite's results, on the same cadence as the deadline:

- The suite's green-on-first-attempt rate, against the `G` the team chose. This is the number that says whether the suite is trusted, and it is the only one non-specialists should be asked to read.
- The size of the ledger and the count of entries renewed at least once. A growing ledger with rising renewals means the policy is being observed and not enforced, which is a different problem from a flaky suite and needs a different conversation.
