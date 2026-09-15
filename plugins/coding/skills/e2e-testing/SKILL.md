---
name: e2e-testing
description: "Keep a browser end-to-end suite trustworthy instead of rerun until green: measure each test's real flake rate from CI history before fixing any one test, locate elements by role and accessible name rather than CSS or XPath, wait on state instead of a fixed sleep or network idle, give every test its own data, authenticate once through stored session state, stub third parties you do not control, and quarantine a flaking test with a deadline. Use whenever someone says our Playwright tests are flaky, tests pass locally and fail in CI, how should I select elements, should I use page objects, or how do I log in once for all tests. Not for choosing what to test or at which level, which is test-design; not for triaging a red pipeline, which is ci-triage; not for finding the cause of a product bug, which is debugging; not for building the site, which is website-builder."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(npx:*), Bash(npm:*), Bash(gh:*), Bash(jq:*), Bash(git:*)
---

# End-to-End Testing

A browser suite is finished when a red run is believed on the first read. Everything below serves that one property, because a suite people rerun until it goes green has stopped being a test and become a delay.

The defining failure at this tier is not missing coverage, it is flake. A test that fails one run in twenty for a reason unrelated to the product teaches the team a rule — a red e2e run means try again — and once that rule is learned the suite protects nothing, including on the day it is right. Flake is also self-concealing: it is rarest on the machine of the person investigating it, because a laptop running one test is faster and less contended than a CI runner running eight in parallel, which is why "passes locally, fails in CI" is the canonical report rather than an unusual one. The work is therefore statistical before it is technical. Measure which tests actually flake, fix the causes in the order the data gives, and put the ones you cannot fix today under a quarantine that expires.

Playwright is the reasonable default in 2026 and the concrete APIs below are its, verified against the upstream documentation for v1.63.0. Each technique says whether it is general or framework-specific, because the principle usually survives the framework and the method name never does.

## Scope

Use for: a browser end-to-end suite that flakes, is slow, or is not trusted; choosing a selector strategy; replacing waits; isolating test data under parallelism; setting up authentication once; stubbing third parties; deciding whether a page object earns its indirection; quarantining a flaking test; and reading trace, video and screenshot artifacts from a CI failure.

Do not use for: deciding what to test and at which level of the pyramid, which is `test-design` and owns unit and integration strategy, coverage decisions and the question of whether a case belongs in a browser at all — this skill starts after that decision is made and owns only the browser tier. Finding the cause of a product bug, which is `debugging` — the split is that this skill owns a flaking *test*, and `debugging` owns a broken *feature*, including one that an e2e test is correctly reporting. Working out why today's pipeline is red and getting it moving, which is `ci-triage` — it classifies a failure as real, flake, infra, config or dependency drift, and that classification is its call, not this skill's; once it has said "flake", this skill is what makes the test stop flaking, and it hands back the fix rather than a rerun. Building the site or app under test, which is `website-builder`.

## Workflow

### 1. Establish the real flake rate before fixing any single test

Do not start from the test someone complained about. The team's belief about which tests are flaky is reliably wrong: it is shaped by which failures were noticed during someone's on-call week, not by frequency, so the loudest test is usually not the worst one and fixing it changes nothing measurable.

Get the per-test numbers from CI history. Playwright's reporters carry the status you need — a test that failed on its first attempt and passed on a retry is reported as `flaky`, distinct from `passed` and `failed` — so if retries are enabled the data already exists and is only unaggregated. Keep the JSON or blob report as a CI artifact on every run; without that there is nothing to aggregate and the first task is to start collecting.

```bash
set -Eeuo pipefail
out=$(mktemp -d)
gh run list --workflow e2e.yml --branch main --limit 50 \
  --json databaseId --jq '.[].databaseId' > "$out/ids"
while read -r id; do
  gh run download "$id" --name playwright-json --dir "$out/$id" 2>/dev/null || true
done < "$out/ids"

# One row per test: how often it ran, and how often it did not pass cleanly on the
# first attempt. Confirm the report shape with `jq keys` before trusting the path.
jq -s '
  [ .[] | .. | objects | select(has("specs")) | .specs[]
    | { test: (.file + " :: " + .title), status: (.tests[0].status // "unknown") } ]
  | group_by(.test)
  | map({ test: .[0].test,
          runs: length,
          unclean: ([ .[] | select(.status != "expected") ] | length) })
  | map(. + { rate: (.unclean / .runs) })
  | sort_by(-.rate)
' "$out"/*/*.json
```

Then set the ceiling, and set it by derivation rather than by borrowing a number. There is no published industry threshold that applies to a particular suite, and a figure quoted without its suite size means nothing, because the same per-test rate produces a different experience at 40 tests and at 400. The number is the team's decision, and this is how to make it a decision they can actually take:

1. Ask what fraction of runs must be green on the first attempt before people stop reflexively rerunning. Call it `G`. Teams answer this one readily — "nine in ten" — where they cannot answer a question about per-test probabilities.
2. Count the tests in the suite, `n`.
3. Treating the failures as roughly independent, the per-test ceiling is `p = 1 - G^(1/n)`. At `n = 200` and `G = 0.9` that is about 0.00053, one unclean result in roughly 1,900 test-runs.
4. Compare every test's measured rate against `p`. Everything above it is in scope, worst first. Everything below it is noise you should not spend the week on.

The arithmetic is deliberately unforgiving, and that is the finding rather than a flaw in the model: a suite of 200 tests cannot tolerate per-test flake at any rate a human would call small. It is also the argument for step 2.

### 2. Cut the tier down to what only a browser can catch

Which cases a system needs, and at which level, is `test-design`'s decision. What belongs here is narrower: given the decision to have a browser tier, which journeys populate it. This tier is the slowest and most brittle one you own, so each test has to pay for its seat.

| Candidate | Belongs in the browser tier | Why |
| --- | --- | --- |
| A revenue or safety-critical journey end to end — sign up, check out, submit the claim | Yes, one test per journey | Failure is unrecoverable and no lower level sees the whole path, including the redirects and the third-party handoff. |
| The wiring between front end, API, session and database actually holding together | Yes, covered incidentally by the journeys above | This integration is the only thing the browser tier uniquely proves; it needs no test of its own. |
| Form validation rules, error message wording, field-level behaviour | No — component or unit level | Twenty browser tests to cover twenty validation branches costs twenty browser startups and twenty chances to flake, for defects a component test catches in milliseconds. |
| Permission and role matrices | No — API or integration level | The matrix is combinatorial; drive it at the layer that enforces it and cover one role in the browser. |
| A third party's own behaviour — the payment provider's hosted page, the SSO screen | No | You cannot control it, so a failure there is not a finding about your system. Stub it; see step 7. |
| Visual appearance across viewports | Separately, as visual regression with pinned browser and OS versions | Mixed into functional tests it makes every unrelated style change a functional failure. |

Deleting a browser test that duplicates a lower-level one raises the suite's trustworthiness twice over: one fewer chance to flake, and `n` smaller in step 1's ceiling.

### 3. Locate elements by what the user perceives

The priority ladder, in order. Drop to the next rung only when the one above genuinely does not apply.

| Rung | Playwright | Use it when |
| --- | --- | --- |
| Role and accessible name | `getByRole('button', { name: 'Sign in' })` | Almost always. This is the first choice for anything interactive. |
| Associated label | `getByLabel('Password')` | Form controls, where the label is the contract with the user. |
| Visible text | `getByText('Order confirmed')` | Static content and confirmations. |
| Placeholder, alt text, title | `getByPlaceholder`, `getByAltText`, `getByTitle` | The element has no label and adding one is out of scope. |
| Explicit test id | `getByTestId('order-total')` — the attribute is `data-testid` by default and configurable through `testIdAttribute` | The element has no accessible name, or its text is user-generated, localised, or otherwise not a contract. |
| CSS structure or XPath | last resort | Only with a comment saying why the rungs above failed, because this is the rung that will break. |

The reason for the ordering is what each rung is a contract with. A role and an accessible name are what a screen reader announces, so a refactor that changes them has changed the product's behaviour and the test failing is correct. A CSS class is a styling decision, so a test bound to it fails on a change no user could perceive — and worse, it passes when the button is renamed from "Sign in" to "Log in", which is a change users do perceive. An XPath path expresses position in the tree, so it breaks when someone wraps the region in a layout div, which happens roughly monthly.

Test ids are the honest escape hatch rather than a failure. An id put in the markup deliberately is a contract, it is greppable, and nobody deletes it during a redesign. What it is not is a substitute for the first three rungs: a suite that reaches for `data-testid` on every button is testing a parallel DOM that no user touches, and it will keep passing after the accessible name breaks.

Two Playwright-specific behaviours worth knowing: locators resolve at the moment of the action rather than at creation, so a locator held across a re-render stays valid; and a locator matching more than one element raises a strictness error rather than silently taking the first, which converts a class of quiet wrong-element failures into loud ones. Both are framework-specific. The ladder itself is general — Testing Library exposes the same priority in React, Vue and Cypress, and Selenium has no equivalent, so a Selenium suite implements the ladder by hand with `data-testid` and accessible-name helpers.

Read `references/selector-strategy.md` when a locator has no accessible name available, when the app is heavily localised, or when porting the ladder to a framework without `getByRole`.

### 4. Wait on state, never on elapsed time

Every fixed sleep is a bet that the machine running the test is at least as fast as the machine it was written on. CI runners are slower, contended and share a disk, so the bet loses under load — which makes a sleep not merely a slow test but a latent flake with an unknown trigger date. Playwright's own documentation marks `page.waitForTimeout` as discouraged in exactly those terms: never wait for a timeout in production, because tests that wait for time are inherently flaky.

Replace each sleep with the condition the next step actually depends on:

| What the sleep was covering | Wait on this instead |
| --- | --- |
| The page or fragment rendering | A web-first assertion on the thing you need: `await expect(page.getByRole('heading', { name: 'Orders' })).toBeVisible()`. These retry until they pass or the expect timeout expires. |
| An in-flight request completing | The response itself: start `page.waitForResponse(...)` before the click that triggers it and await both together, or assert on the state the response produces. |
| A spinner or skeleton disappearing | `await expect(page.getByTestId('spinner')).toBeHidden()`, then assert the content. Waiting for the spinner to appear first is a race you will lose on a fast response. |
| Navigation | An assertion on the destination — `await expect(page).toHaveURL(/\/orders\/\d+/)` — rather than a wait on the navigation event. |
| An animation or transition | Disable animations in the test configuration, so there is nothing to wait for. |
| A background job the UI polls for | Poll the assertion with a raised timeout on that one assertion, and say in a comment which job you are waiting on. |

#### Waiting for the network to go quiet is not waiting on state

`networkidle` looks like the general-purpose answer and is the most damaging single line in most flaky suites. Playwright's own documentation marks it DISCOURAGED in both places it appears — the `waitUntil` option on navigation and the state argument to `waitForLoadState` — with the instruction to rely on web assertions to assess readiness instead.

It is wrong rather than merely disfavoured, and the reason is worth holding. The condition is "no network connections for at least 500 ms", so any analytics beacon, long poll, WebSocket keepalive, chat widget or periodic refresh means the page never goes idle and the wait runs to its timeout. It therefore fails more on CI, where third-party requests are slower and more numerous, which is exactly the environment people add it to fix. What it does when it does work is no better: it converts a deterministic assertion about your application into a race against your own telemetry, so an unrelated change to an analytics tag alters the suite's timing.

Delete every `networkidle` and replace it with an assertion on the state the test needs. When the genuine requirement is a specific request, wait for that request by URL; when it is a rendered result, assert on the result.

Two rules about timeouts themselves. Raising a timeout is not a fix: it converts a fast failure into a slow one and leaves the race in place, so a test that only passes at 30 seconds where the rest pass at 5 is telling you about a real product delay or a missing wait condition. And know the defaults you are working against — in Playwright each test gets 30 seconds, each auto-retrying assertion gets 5, and individual actions and navigations have no timeout of their own, so they are bounded only by the test's. A test that dies at exactly 30 seconds with no assertion named is usually stuck on an action waiting for an element that never arrives, not slow.

### 5. Give every test its own data

Shared fixtures produce order-dependent failures, and order-dependent failures only surface under parallelism — which is to say, in CI and not on the laptop. The shape is always the same: test A creates a record, test B asserts on "the first row", and whichever runs second fails, so the blame lands on whichever test the scheduler happened to put there.

Playwright already isolates the browser: each test gets a fresh context, so cookies, local storage and session storage do not leak between tests. The server's database is not isolated, and that is where every real order dependence lives. So:

- Create the data each test needs inside that test, keyed by something unique to it. The worker's parallel index plus the test title, or a generated identifier, both work; the requirement is only that two workers running the same file cannot collide.
- Set up through the API rather than through the UI. Driving the UI to create a precondition doubles the test's length and makes every test a hostage to the creation flow's flake.
- Do not assert on position in a shared collection. Assert on the row you created, located by its unique key.
- Clean up by creating fresh rather than by deleting afterwards. A test that failed did not run its teardown, so a suite that depends on teardown is one failure away from a cascade.
- Prove the isolation rather than assuming it: run the suite in full parallel and again with `--repeat-each` against the suspect file. A test that passes alone and fails in the suite is sharing something, and that is the finding.

`test.describe.configure({ mode: 'serial' })` makes a group order-dependent on purpose. It is occasionally the right answer for a genuinely sequential journey, and it is more often a way to hide the coupling in step 5's list. Upstream's own note is that serial mode is not recommended and isolated tests are usually better; treat each use of it as a deferred fix with a reason attached.

### 6. Authenticate once, through stored session state

Logging in through the UI in every test is the single most expensive mistake at this tier. It multiplies the login form's own flake rate by the number of tests, so a login that fails one time in two hundred fails several times a day across a 300-test suite; it makes the login page a single point of failure for everything; and it spends several seconds per test on a path that is not what the test is about.

Instead, authenticate once and reuse the session state. In Playwright this is a setup project that logs in, writes the browser context's storage state to a file, and is declared as a dependency of the test projects, which then load that file as their `storageState`. Upstream recommends exactly this for applications without server-side session state. The general principle carries to any framework: obtain the session artifact once, inject it, and let each test start already authenticated.

Three things to get right:

- **Credentials come from the environment.** Read them from environment variables sourced from the CI secret store, never committed and never passed as command-line arguments, where they appear in process listings and in CI logs that echo the command. A test account is still a credential.
- **Keep exactly one test that logs in through the UI.** Bypassing the login form everywhere else means nothing covers it, and the login form is the one page whose failure means nobody can use the product at all. One test, running the real form, is the price of the optimisation.
- **Give each worker its own account when the application has server-side session state.** One shared account across parallel workers produces logouts, session invalidation and concurrency failures that look exactly like flake. Playwright's per-worker fixture pattern, keyed on the parallel index, is the mechanism; the general version is a pool of test accounts sized to the worker count.

The session file expires. Treat a suite that fails everywhere at once, immediately after a run of green, as an expired or invalidated session before treating it as a product regression.

### 7. Stub the third parties, not your own API

Anything you do not control — a payment provider's hosted page, an SSO screen, a maps or analytics endpoint, a feature-flag service — is outside the system under test, and its outages, cookie banners and rate limits arrive in your suite as flake you cannot fix. Intercept those routes and fulfil them with a fixed response. Playwright's `page.route` and `context.route` do this; `routeFromHAR` records a real interaction once and replays it, which keeps the shape honest for a provider whose payloads you would otherwise guess at. Commit the HAR so the stub is reviewable.

The boundary matters in the other direction too: do not stub your own API. An e2e test whose backend is mocked proves that the front end agrees with your mock, which is a question a component or contract test answers in milliseconds. Stubbing your own API is how a browser suite becomes expensive and stops catching the integration defects that were the only reason to have it.

Blocking analytics, telemetry and advertising requests is worth doing on top, for speed and for the noise they add to every trace.

### 8. Use a page object when it removes repetition, not to hide the test

The Page Object Model earns its indirection in some places and destroys readability in others, and the difference is specific.

| Situation | Page object | Why |
| --- | --- | --- |
| A selector used in more than about three tests | Yes | One definition, one place to change when the markup moves. This is the whole original argument and it still holds. |
| A multi-step flow that is a precondition rather than the subject — log in, seed a cart, complete onboarding | Yes, or a fixture | The tests that use it are not testing it, so the steps are noise in their bodies. |
| A page under active redesign | Yes | The churn is exactly what the indirection absorbs. |
| A single test's single interaction | No | A class with one caller is indirection with no payer. |
| Assertions | No — assertions stay in the test | A method that performs its own assertions makes a test body of three calls whose failures name the object rather than the behaviour, and the reader cannot see what is being checked without opening another file. |
| A method named for a whole journey, like `completeCheckout()` | No | It hides the journey the test exists to describe. Expose the steps; let the test compose them. |

The test that can be read is the one whose body is the journey: a sequence of actions in the user's vocabulary, with the assertions visible. Page objects expose actions and queries; the test owns the expectations. In Playwright, a fixture is often a better unit than a class, because it participates in setup and teardown and is injected rather than constructed.

### 9. Quarantine with a deadline, or delete

A test above the step 1 ceiling that cannot be fixed today gets quarantined, and the quarantine carries a date. A quarantine without one is a deletion that still costs CI minutes and still appears as coverage on a report, which is worse than a deletion because it is invisible.

The ledger entry, in the repository beside the test rather than in a ticket system nobody reads:

| Field | Content |
| --- | --- |
| Test | File and title, exactly as the reporter names it. |
| Measured rate | The figure from step 1, with the number of runs it came from. |
| Suspected class | From the taxonomy in `references/flake-taxonomy.md`, with the artifact that supports it. |
| Owner | A person, not a team. |
| Expiry | A date. |
| Coverage at risk | What goes unchecked while it is out, in one line — this is what makes deletion a decision rather than a default. |

Keep quarantined tests running, in a separate non-blocking job. A quarantined test that stops executing stops producing data, so nobody can tell when the underlying cause was fixed, and the ledger entry is renewed forever on no evidence. On the expiry date there are two outcomes: fixed and returned to the blocking suite, or deleted with the coverage gap recorded. Renewal is a third outcome only with new evidence attached.

The length of the deadline is the team's decision and there is no published figure to borrow. Derive it from a cadence the team already runs on — one sprint, or one on-call rotation, so the expiry lands on a date somebody is already looking at a list. What matters far more than the length is that the date exists and that expiry is enforced.

Retries are a reporting mechanism, not a remedy, and the difference decides whether they help or hurt. Running CI with retries enabled is what produces the `flaky` classification step 1 depends on, so keep them — but a suite running with retries on whose flaky count nobody reads is strictly worse than the same suite with retries off, because the failures are now suppressed at the point where they would have been noticed and the cause is untouched. Retries earn their place only when someone reads the count on a schedule. Playwright's `--fail-on-flaky-tests` makes that count blocking, which is the right setting once the ledger is short enough that turning it on does not stop all work.

Setting `workers: 1` on CI is the same mistake in a more expensive costume. It does suppress the failures, because the failures were order-dependent, and it does so by spending the entire parallelism budget — a suite that took four minutes now takes twenty — while leaving the shared state that caused them in place. The coupling then resurfaces as order dependence the first time someone adds a test, reorders a file or shards the run. The defect is in step 5, and single-worker execution is a way of not looking at it.

This is the seam with `ci-triage`: it decides whether today's red build is a flake and gets the pipeline moving, and it hands the test over here. Coming back the other way, a fix made here is what lets that build stop being classified as flake. Neither owns both halves.

### 10. Debug from the artifacts, not from a local rerun

Rerunning locally to reproduce a CI failure is the slowest available move and usually the least informative, because your laptop is the configuration that already passes. The failure happened on a slower, contended machine under parallelism, and the evidence from that machine was already captured if the run was configured to capture it.

Configure the capture so the evidence exists before you need it. In Playwright, `trace: 'on-first-retry'` records a trace only for tests that were retried, which is the cheap setting that covers exactly the flaky ones; `retain-on-failure` keeps traces for failures when retries are off; `screenshot: 'only-on-failure'` and a video mode such as `retain-on-failure` fill in the rest. Upload them as CI artifacts from the same job.

Read them in this order:

1. **The trace, at the failing action.** Open it with `npx playwright show-trace trace.zip`. The DOM snapshots either side of the failing action answer the first question — was the element absent, present but covered, present but disabled, or present with different text — and that answer selects the flake class before any hypothesis is formed. A hosted viewer exists; check whether a trace of your application may leave your network before using it, since a trace contains the rendered page and its requests.
2. **The network panel, for the request that did not happen.** A large share of e2e flake is a request that was slower, was never fired because a handler had not attached yet, or returned a different shape. The trace records them.
3. **The console, for the error that preceded the symptom.** An unhandled rejection several actions earlier is frequently the real event.
4. **The video, only for ordering questions** — did the modal open before the click landed. It is the lowest-information artifact and the largest.

Reproduce locally only after the artifacts have narrowed it to a hypothesis, and reproduce under the conditions that made it fail: `--repeat-each` with a high count, full parallelism, headless, and the same browser version the runner used. A single local pass proves nothing about a test that fails one run in fifty.

Read `references/flake-taxonomy.md` once the trace has told you what the DOM looked like: it maps each artifact signature to its cause and its fix.

### 11. Prove the test can still fail

A repaired test is not finished when it passes. A large share of "fixed" flaky tests are fixed by accidentally removing their ability to fail at all, which converts an intermittent failure into a permanent, silent pass — the worst outcome available, because the suite now reports green for a journey nobody is checking and no artifact will ever say otherwise.

So close every repair, and every new test, with one falsification run: break the behaviour the test asserts, and confirm the test fails, at the line you expect and for the reason you expect. Invert the assertion, change the expected text, point the stub at a failing response, or comment out the product code that produces the result. A test that stays green through that is not a test.

The always-pass defects worth knowing by sight, because none of them is visible in a passing run:

| Defect | Why it passes regardless |
| --- | --- |
| An assertion that is not awaited | The assertion returns a promise that nobody waits on, so the test finishes before the check resolves and any failure lands after the result was recorded. |
| Asserting on a locator's truthiness rather than its state | A locator object exists whether or not it matches anything, so the assertion is about the object, not the page. |
| A committed `test.only` | The rest of the file stops running while the run still reports success. `--forbid-only` catches this one for free. |
| An action or assertion wrapped in a swallowing `try`/`catch` | The failure is caught and discarded, usually added during a flake investigation and never removed. |
| A conditional assertion — `if (await thing.isVisible()) expect(...)` | On the run where the element is missing, nothing is checked, which is precisely the run that mattered. |
| An assertion on an element that also exists on the error page | Passes on the failure path too, so it distinguishes nothing. |

Two of these also explain a test that mysteriously stopped flaking after someone touched it. When a flaky test goes quiet without a diagnosis in the taxonomy, run the falsification check before believing it.

## Output format

Report suite work in this shape, so the numbers stay attached to the decisions:

```markdown
## Measured flake rates
[Table: test | runs sampled | unclean runs | rate. Worst first. State the window.]

## Ceiling
[G the team chose, n, the derived per-test ceiling, and which tests exceed it.]

## Findings
[Per test above the ceiling: class from the taxonomy, the artifact that proves it,
the fix, whether it is landed or quarantined, and how the repaired test was shown
to still fail when the behaviour is broken.]

## Quarantine ledger changes
[Added, returned, deleted — each with its expiry date and the coverage at risk.]

## Tier changes
[Tests deleted or pushed down a level, with what now covers them.]
```

## Anti-patterns

**Fixing the test someone complained about.** It is the test that failed while a particular person was watching, which is uncorrelated with the rate. Fixing it produces no measurable change in the suite's green rate, which is then read as evidence that flake is unfixable.

**Retry as the remedy.** Turning on retries and looking no further converts a measurable defect into an untracked tax on every run, and it hides the regression on the day the test starts failing for a real reason. Retries are how you measure flake; they are not how you remove it, and unread they are worse than no retries at all.

**Single-worker CI to make the failures stop.** It works, which is the trap. It spends the whole parallelism budget to hide shared state, and the coupling returns as order dependence the moment anyone adds a test or shards the run.

**Waiting for the network to be idle.** The wait never completes on a page with any beacon, poll or keepalive, so it runs to the timeout — worse on CI than locally, which is backwards from what it was added to fix. Upstream marks it discouraged for testing in both places it appears.

**The test that cannot fail.** A missing `await` on an assertion, a locator asserted for truthiness, a swallowing `try`/`catch`, a committed `test.only`. Each turns an intermittent failure into a permanent silent pass, which is the one outcome no artifact will ever report.

**Raising the timeout until it passes.** The race is still there; it now takes longer to lose. A test that needs 30 seconds where its neighbours need 5 is reporting either a product delay worth fixing or a missing wait condition.

**Sleeping for a fixed duration.** It is slower on every run and still fails on a loaded runner, which is the worst of both. It also encodes an assumption about machine speed that nobody will remember when it breaks.

**Selecting by CSS class or XPath position.** Both break on changes that no user can perceive and survive changes that every user perceives, so the test fails at the wrong times and passes at the wrong times.

**A `data-testid` on every element.** It makes the suite test a parallel DOM that nobody interacts with, and it keeps passing after the accessible name breaks — which is a real defect for anyone using a screen reader.

**Logging in through the UI in every test.** It multiplies the login form's flake by the test count, makes one page a single point of failure for the entire suite, and spends seconds per test on something the test is not about.

**Mocking your own API in an e2e test.** It proves the front end agrees with your mock. The integration it stubbed out was the only thing this tier could uniquely catch.

**A shared seeded database.** Order-dependent failures that appear only under parallelism, are blamed on whichever test ran second, and disappear when anyone tries to reproduce them serially.

**Assertions inside page object methods.** The test body becomes three method calls whose failure messages name the page object, and what is actually being checked is invisible without opening another file.

**A quarantine with no expiry.** It becomes permanent, and a permanently quarantined test is a deleted test that still consumes CI time and still counts as coverage on a report nobody rereads.

**Pushing a case into the browser tier because it was easier to write there.** Every case at this tier costs a browser start and a chance to flake. If a component or API test can catch it, that is where it belongs, and `test-design` is the skill for that decision.

## Reference files

- `references/flake-taxonomy.md` — read when a test is flaking and the cause is not obvious from the trace: the eight recurring classes, the artifact signature that identifies each, and the fix.
- `references/selector-strategy.md` — read when an element has no accessible name, when the app is localised, or when applying the locator ladder in Cypress, Testing Library or Selenium.
- `references/playwright-config.md` — read when setting up or repairing the configuration: timeouts, artifact capture, the authentication setup project, parallelism, sharding and the CI job shape, verified against upstream v1.63.0.
- `references/quarantine.md` — read when deciding whether to quarantine, delete or fix: the ledger format, how to run quarantined tests without blocking, and how to derive the deadline and the expiry review.
