# Playwright configuration and CI wiring

Everything here is framework-specific and was checked against the upstream documentation in the `microsoft/playwright` repository at tag `v1.63.0`. Version the assumption: option names and defaults change between releases, so re-check any figure before relying on it in a different version.

## Contents

- [The timeouts and their defaults](#the-timeouts-and-their-defaults)
- [Artifact capture](#artifact-capture)
- [Authentication as a setup project](#authentication-as-a-setup-project)
- [Per-worker authentication](#per-worker-authentication)
- [Parallelism and workers](#parallelism-and-workers)
- [Sharding and merged reports](#sharding-and-merged-reports)
- [Pinning the environment](#pinning-the-environment)
- [Network stubbing](#network-stubbing)
- [Useful command-line flags](#useful-command-line-flags)
- [Credentials](#credentials)

## The timeouts and their defaults

| Timeout | Default | Set where |
| --- | --- | --- |
| Test timeout | 30,000 ms | `timeout` in the config; `test.setTimeout()` or `test.slow()` per test |
| Expect timeout, for auto-retrying assertions | 5,000 ms | `expect: { timeout }` in the config; a `timeout` option on one assertion |
| Action timeout | none | `use: { actionTimeout }`; a `timeout` option on one action |
| Navigation timeout | none | `use: { navigationTimeout }`; a `timeout` option on one navigation |
| `beforeAll` and `afterAll` hook timeout | equal to the test timeout | `test.setTimeout()` inside the hook |
| Global timeout for the whole run | none | `globalTimeout` in the config |

Two consequences of the defaults. Actions and navigations have no timeout of their own, so they are bounded only by the test timeout — a test that dies at exactly 30 seconds naming no assertion is usually stuck on an action waiting for an element that never arrives. And the expect timeout is unrelated to the test timeout, so six assertions each waiting their full 5 seconds exhaust a 30-second test with no single assertion having been unreasonable.

Set `globalTimeout` on CI even though there is no default. Without one, a wedged run occupies a runner until the platform's own limit, which reads as slow CI rather than broken CI.

## Artifact capture

```ts
// playwright.config.ts
export default defineConfig({
  use: {
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  retries: process.env.CI ? 2 : 0,
});
```

`trace: 'on-first-retry'` records a trace only when a test is retried, which is precisely the set of tests that flaked and is the cheap default. Use `retain-on-failure` instead when retries are off — it records for every test and discards the traces from the passing ones. `'on'` records everything and is worth it only for a short investigation, because traces are large.

Upload the output directory as a CI artifact from the same job that ran the tests. A trace that was recorded and not uploaded is the most common reason a flake investigation starts with a local rerun.

Open one with `npx playwright show-trace trace.zip`. A statically hosted viewer exists at `trace.playwright.dev`; check your organisation's policy before uploading a trace of an internal application to it, since a trace carries the rendered DOM and the recorded requests.

## Authentication as a setup project

The recommended shape for applications without server-side session state: a setup project logs in once, saves the storage state to a file, and the test projects declare it as a dependency and load the file.

```ts
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
```

```ts
// auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(process.env.E2E_USER ?? '');
  await page.getByLabel('Password').fill(process.env.E2E_PASSWORD ?? '');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.context().storageState({ path: authFile });
});
```

Add the auth directory to `.gitignore`. It contains live session cookies, and committing it is a credential leak with a delay on it.

For several roles, write one file per role in the setup project and select between them per test file with `test.use({ storageState: ... })`.

## Per-worker authentication

A shared account breaks when the application has server-side session state: one worker's logout or session refresh invalidates another's, and the resulting failures look exactly like flake. Override the `storageState` fixture at worker scope and key the file on the worker's parallel index, so each worker authenticates once as its own account. Size the account pool to the worker count and provision the accounts as part of environment setup rather than inside the test run.

## Parallelism and workers

- `fullyParallel: true` runs every test in every file in parallel, which is what makes shared state surface. Turning it off to make a suite green hides the coupling rather than removing it.
- `workers` defaults to a proportion of the logical CPU cores. Set it explicitly for CI: a container with two cores and four browsers swaps, and the resulting timeouts are misread as test defects.
- `test.describe.configure({ mode: 'serial' })` makes a group ordered and aborts the rest of the group on the first failure. Upstream does not recommend it; treat each use as a deferred isolation fix with a comment saying what is shared.
- Worker processes are discarded after a failure and a fresh one starts, so `beforeAll` runs again. A `beforeAll` that is expensive or not idempotent becomes a hidden cost and a hidden source of failures under retry.

## Sharding and merged reports

Sharding across runners is the right way to add parallelism once a single runner is saturated: `--shard=1/3` and so on, with each shard writing a blob report, then one job merging them. The merged report is what step 1 of the skill aggregates over, and a per-shard report will under-count a test that only runs in one shard.

```bash
set -Eeuo pipefail
npx playwright test --shard="${SHARD_INDEX}/${SHARD_TOTAL}" --reporter=blob
```

## Pinning the environment

Pin the timezone, the locale and the viewport in `use`, so the runner and the laptop cannot disagree. Unpinned, they are a standing source of the time-and-locale flake class, and the failures arrive months after the test was written, when someone changes the runner image.

Pin the browser version too. Playwright ships browsers with the package, so the lockfile pins them; a suite that installs browsers separately loses that property and gains failures that correlate with nothing in the diff.

## Network stubbing

```ts
await page.route('**/analytics/**', route => route.abort());
await page.route('**/api/third-party/quote', route =>
  route.fulfill({ status: 200, json: { amount: 1200, currency: 'GBP' } }));
```

For a provider whose payload shape you would otherwise guess at, record it once with `routeFromHAR` and `update: true`, then commit the HAR and run against the recording. Re-record deliberately, as a reviewable diff, rather than on every run.

Route your own API only to inject a failure you cannot otherwise produce — a 500 on one endpoint to check the error state. Stubbing your own API wholesale removes the integration this tier exists to cover.

## Useful command-line flags

| Flag | Use |
| --- | --- |
| `--repeat-each=N` | Run each selected test N times. The instrument for confirming a flake and for proving a fix. |
| `--retries=N` | Override the configured retry count; with retries on, the reporter distinguishes `flaky` from `failed`. |
| `--workers=N` | Reproduce a parallelism-dependent failure, or diagnose runner starvation by lowering it. |
| `--last-failed` | Re-run only the previous run's failures while iterating on a fix. |
| `--only-changed [ref]` | Run the test files changed against a ref. Git only. |
| `--grep @tag`, `--grep-invert @tag` | Select or exclude by tag. The mechanism for keeping a quarantined set out of the blocking run. |
| `--fail-on-flaky-tests` | Fail the run when any test is reported flaky. Turn it on once the quarantine ledger is short enough that it does not block everything. |
| `--forbid-only` | Fail when `test.only` was committed. Cheap, and it catches a whole suite silently reduced to one test. |

## Credentials

Test-account credentials come from environment variables populated from the CI secret store. Do not commit them, do not pass them as command-line arguments — arguments appear in process listings and in any CI log that echoes the command — and do not write them into a fixture file. Rotate them like any other credential; a test account usually has real data behind it.
