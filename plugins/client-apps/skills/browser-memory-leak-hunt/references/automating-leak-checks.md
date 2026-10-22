# Automating leak checks

Read this in step 5, once a leak is fixed and needs to stay fixed, or when a page needs a
standing check before anyone reports a crash.

## Contents

- A browser test that repeats the action
- memlab for a scripted three-snapshot run
- Field monitoring

## A browser test that repeats the action

The shape: warm up, measure after a forced collection, repeat the action many times,
measure again, and assert the difference is less than one leaked unit per repetition. The
Chrome DevTools Protocol gives both the forced collection and the counts, so this runs in
Chromium only.

```js
// Playwright
import { test, expect } from '@playwright/test';

test('opening and closing the report dialog does not leak', async ({ page }) => {
  await page.goto('/reports');
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Performance.enable');
  await cdp.send('HeapProfiler.enable');

  async function measure() {
    await cdp.send('HeapProfiler.collectGarbage');
    const { metrics } = await cdp.send('Performance.getMetrics');
    const get = (name) => metrics.find((m) => m.name === name).value;
    return {
      heap: get('JSHeapUsedSize'),
      nodes: get('Nodes'),
      listeners: get('JSEventListeners'),
    };
  }

  async function action() {
    await page.getByRole('button', { name: 'Open report' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();
  }

  const N = 30;
  for (let i = 0; i < 3; i++) await action();   // warm-up
  const before = await measure();
  for (let i = 0; i < N; i++) await action();
  const after = await measure();

  expect(after.nodes - before.nodes).toBeLessThan(N);
  expect(after.listeners - before.listeners).toBeLessThan(N);
  expect(after.heap - before.heap).toBeLessThan(before.heap * 0.1);
});
```

Why these assertions:

- DOM nodes and listeners are integers that should return exactly to their floor. Fewer
  than one per repetition tolerates incidental noise while still catching a leak of even a
  single node per action.
- Heap size is noisy even after a forced collection, so it gets a proportional tolerance.
  Tighten it only after watching it across a few dozen CI runs. The assertion is coarse:
  a JavaScript-only leak, such as a growing `Map` holding no nodes or listeners, can stay
  under 10% of a large heap. The node and listener counts are the real gate; for a leak of
  that kind, also bound growth per repetition, for example
  `(after.heap - before.heap) / N` below a byte budget you set from a clean baseline.
- The warm-up keeps lazy modules, caches and pools that are created once out of the
  measurement.

In Puppeteer the same counts come from `page.metrics()`, and the forced collection from a
CDP session on the page sending `HeapProfiler.collectGarbage`.

Run the check against a production build. Development builds retain extra data and, in
React's Strict Mode, mount components twice.

## memlab for a scripted three-snapshot run

memlab, from Meta, automates the snapshot comparison: it loads a page, runs an action,
runs a "back" step that should undo it, takes snapshots at each stage, and reports objects
the action allocated that survived the back step, with their retainer traces.

```js
// scenario.js
function url() {
  return 'http://localhost:3000/reports';
}
async function action(page) {
  await page.click('[data-testid="open-report"]');
}
async function back(page) {
  await page.click('[data-testid="close-report"]');
}
module.exports = { url, action, back };
```

```bash
npx memlab run --scenario scenario.js
```

Use it when a leak is suspected across many interactions and you want the retainer traces
without clicking through DevTools. It drives a Puppeteer-controlled Chromium, so it needs
a page reachable from wherever it runs.

## Field monitoring

`performance.measureUserAgentSpecificMemory()` reports the page's memory, broken down by
frame and worker, in Chromium-based browsers. It is available only when the page is
cross-origin isolated (`self.crossOriginIsolated` is true, which needs the
`Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy` headers), and the promise
resolves after the next garbage collection, which can take a while.

```js
async function sampleMemory() {
  if (!self.crossOriginIsolated || !performance.measureUserAgentSpecificMemory) return;
  const result = await performance.measureUserAgentSpecificMemory();
  navigator.sendBeacon('/rum', JSON.stringify({
    kind: 'memory',
    bytes: result.bytes,
    minutesOpen: Math.round(performance.now() / 60000),
  }));
}
```

Sample at intervals with random jitter rather than on every page, and plot bytes against
minutes open. A line that keeps rising for sessions over an hour is a leak in the field,
even when every test passes. Where cross-origin isolation is not possible, the
non-standard `performance.memory` in Chromium gives coarse, quantised heap figures that
are still enough to see a long-session trend.
