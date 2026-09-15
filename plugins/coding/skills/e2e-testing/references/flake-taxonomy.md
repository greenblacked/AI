# The flake taxonomy

Eight classes cover nearly every intermittent browser-test failure. Identify the class from the artifacts before forming a hypothesis, because the fix differs sharply between classes that look identical in a CI log — "element not found" is the symptom of at least four of them.

## Contents

- [How to use this file](#how-to-use-this-file)
- [1. The race against render](#1-the-race-against-render)
- [2. The race against hydration](#2-the-race-against-hydration)
- [3. Shared state between tests](#3-shared-state-between-tests)
- [4. The moving target](#4-the-moving-target)
- [5. Time, timezone and locale](#5-time-timezone-and-locale)
- [6. The third party](#6-the-third-party)
- [7. Resource starvation on the runner](#7-resource-starvation-on-the-runner)
- [8. The genuine product race](#8-the-genuine-product-race)
- [When the class will not resolve](#when-the-class-will-not-resolve)

## How to use this file

One check comes before the classification. A test whose rate has just dropped to zero without a diagnosis is more often a test that lost its ability to fail than a test that was fixed, so confirm it still fails when the behaviour it asserts is broken before recording it as resolved. That check is step 11 of the skill and it applies to every repair made from this file.

Open the trace at the failing action and answer three questions from the DOM snapshots either side of it: was the target element absent, present but not interactable, or present with unexpected content? Then check the network panel for a request that did not complete, and the console for an error that preceded the symptom. The table below maps those answers to a class.

| Artifact signature | Likely class |
| --- | --- |
| Element absent in the before-snapshot, present in the after-snapshot | 1, race against render |
| Element present and visible, but the click had no effect | 2, hydration |
| Element present with content belonging to another test's data | 3, shared state |
| Element present in a different position, or two elements matched | 4, moving target |
| Content correct but a date, number or string differs | 5, time and locale |
| A pending or failed request to a domain you do not own | 6, third party |
| Failure at the test timeout with no action named, or a browser crash | 7, starvation |
| Correct actions, correct waits, and the application state is still wrong | 8, product race |

## 1. The race against render

**Signature.** The element is absent in the snapshot before the failing action and present afterwards. The failure message names a locator and a timeout.

**Cause.** The test acted on a state the application had not reached. Almost always a fixed sleep that was long enough on the author's machine, or an implicit assumption that navigation completes before the next line runs.

**Fix.** Replace the sleep with a web-first assertion on the element the next step needs. If the wait is already an assertion, the timeout is too short for the real work — find out what the work is before raising it, because a page that takes eight seconds to show its first row is a product finding.

**Not fixed by.** Raising the timeout — the race remains and now costs more to lose. Nor by waiting for the network to go idle, which upstream discourages for testing: a page with any beacon, poll or keepalive never reaches idle, so the wait runs to its timeout, and it does so more often on CI than locally.

## 2. The race against hydration

**Signature.** The element is present, visible and enabled. The action is recorded as succeeding. Nothing happens afterwards.

**Cause.** Server-rendered markup arrives before the JavaScript that attaches the handler, so the click lands on an element that looks complete and is inert. This class is specific to server-rendered and progressively hydrated applications, and it is the one that most often defeats framework auto-waiting: the actionability checks pass, because the element genuinely is visible, enabled and stable.

**Fix.** Wait for evidence that the application is interactive rather than merely rendered — an element that only the client renders, an attribute the framework sets on hydration, or a request that only the hydrated page makes. Adding an explicit hydration marker to the application is a legitimate change and usually the cheapest one.

**Not fixed by.** Clicking twice, which passes locally and produces double submissions in the cases where the first click did land.

## 3. Shared state between tests

**Signature.** The element is present with content belonging to a different test, or an assertion on a count is off by exactly the number of tests running in parallel. The test passes when run alone, and which test fails changes between runs.

**Cause.** A shared database row, a shared user account, a shared feature-flag state, or an assertion on position in a collection that other tests write to.

**Fix.** Unique data per test, created through the API and keyed by the worker index or a generated identifier; assertions on the record you created rather than on the first row. For shared accounts, a pool sized to the worker count.

**Confirm it before fixing it** by running the suspect file with `--repeat-each` and full parallelism. Passing alone and failing in the suite is the proof.

## 4. The moving target

**Signature.** A strictness error naming two matched elements, or a click that lands on the wrong control, or an element found and then detached before the action.

**Cause.** Three distinct causes wear this signature. The locator is ambiguous and previously matched one element by luck. The element moves during a layout shift or an animation, so the click lands where it used to be. Or the component re-renders between the find and the act, detaching the node.

**Fix.** For ambiguity, narrow the locator by role and accessible name, or scope it to a region rather than adding `.first()`, which hides the ambiguity rather than resolving it. For layout shift, disable animations in the test configuration and assert on the settled state first. For detachment, prefer a framework whose locators resolve at action time, and avoid holding element handles across a re-render.

## 5. Time, timezone and locale

**Signature.** Content correct in shape, wrong in value: a date one day off, a currency with the wrong separator, a relative time reading "2 minutes ago" where the test expected "just now". Often fails only at certain hours, or only in CI, or only in one month.

**Cause.** The runner's timezone and locale differ from the developer's, the test asserts on a formatted value, or the test straddles midnight or a daylight-saving transition.

**Fix.** Pin the timezone and locale explicitly in the test configuration so the runner and the laptop agree. Where the application supports it, pin the clock too. Assert on the semantic value rather than on its formatting where you can, and where the formatting is the thing under test, pin the locale and say so in the test name.

## 6. The third party

**Signature.** A pending, slow or failed request to a domain you do not own, in the network panel of the trace. A consent banner or interstitial in the screenshot that no one expected.

**Cause.** Payment providers, SSO, maps, analytics, tag managers, feature-flag services and CDNs, all of which have their own availability, their own rate limits and their own experiments.

**Fix.** Intercept and fulfil those routes with a fixed response. Record a HAR once if the real payload shape matters, and commit it. Block analytics and advertising outright. Keep at most one test — run outside the blocking suite — that exercises a real third-party sandbox, and treat its failures as information about the provider rather than about your build.

## 7. Resource starvation on the runner

**Signature.** Failure at exactly the test timeout with no specific action named; browser or worker crashes; a cluster of unrelated tests failing in the same run; failures that correlate with the worker count rather than with any code change.

**Cause.** Too many parallel workers for the runner's CPU and memory. Browsers are memory-hungry, and a default worker count derived from logical cores is frequently wrong for a small CI container.

**Fix.** Set the worker count explicitly for CI rather than taking the default, and shard across more runners instead of packing more workers onto one. Check the runner's memory against the browser count before concluding anything about the tests. This class is the one most often misdiagnosed as a test defect, and no change to the test will fix it.

## 8. The genuine product race

**Signature.** Every action is correct, every wait is on state, the artifacts show the application reaching a state that is genuinely wrong — a stale value, a lost update, a double submission.

**Cause.** A real concurrency defect in the product: an unsequenced pair of requests, a cache that serves a value written after it, an optimistic update that is not reconciled.

**Fix.** None here. This is the case where the e2e suite did its job, and it hands off to `debugging` to find the cause and to the team that owns the code to fix it. Recognising this class is the reason the taxonomy is worth working through rather than skipping to a quarantine: a test in this class is the most valuable one in the suite, and quarantining it deletes the only signal anyone has.

## When the class will not resolve

If two full sittings with the artifacts have not produced a class, stop investigating and quarantine with a deadline, recording what was ruled out. Continuing past that point has a poor record, and the ledger entry preserves the work so the next person starts where you stopped rather than at the beginning.
