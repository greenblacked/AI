---
name: async-ui-races
description: "Remove race conditions from client code that talks to a server: classify the race first - out-of-order responses, double submit, optimistic updates diverging from the server, state set after unmount - then fix each with its own tool: request keys or AbortController so the latest wins, a disabled control plus an idempotency key for submits, rollback reconciled with the server for optimistic updates, cancellation in cleanup; prove it with a test that releases responses in reverse order, not one that relies on timing. Use when \"search shows old results\", \"double click created two orders\", \"the like count flickers back\" or \"typing fast shows the wrong suggestions\". Not for flaky browser test suites (e2e-testing), server idempotency contracts (api-design), server-side cache staleness (application-caching), or queue consumers (event-driven-reliability)."
allowed-tools: "Read, Grep, Glob, Edit"
---

# Async UI Races

Done means every asynchronous path in the feature has a named race class, a guard that makes the final screen independent of response order and click count, and a test that reverses or duplicates the timing on purpose and passes.

The usual failure is a fix that narrows the window instead of closing it. A debounce makes out-of-order responses rarer, not impossible; a spinner makes double clicks rarer, not impossible; and a test that sleeps for 300 ms passes because the network happened to be fast that run. On a slow phone connection the window is wide open again, and that is where the bug reports come from.

## Scope

Use for user-visible races between a client and its server: stale search, filter, tab or pagination results; duplicate orders, payments, messages or rows; optimistic updates that flicker, revert or lie; and results, toasts or redirects that land after the user has moved on. Framework-independent, with React and TanStack Query examples because they are the common case.

Leave elsewhere: a browser test suite that is flaky for reasons in the test itself (`e2e-testing`); designing the server's idempotency and error contract (`api-design`); stale data served by a server-side cache (`application-caching`); duplicate processing in queue consumers and workers (`event-driven-reliability`); a server render that differs from the client's first render (`hydration-mismatch-hunt`).

## Gates

1. Name the class before writing a fix. The four classes have different fixes, and the wrong one hides the symptom: debouncing does not order responses, and disabling a button does not stop a retry after a timeout.
2. For anything with a side effect, the server is the guarantee. Client guards reduce duplicates; only a server that honours an idempotency key removes them, because two tabs, a flaky network and a back-and-resubmit all bypass the button.
3. A fix is proven by a test that controls order deterministically. "I clicked fast and it was fine" is not evidence.

## Workflow

### 1. Reproduce by controlling the order

DevTools throttling slows every request equally, so it rarely reverses two of them. Hold one response and release the other first instead: a Mock Service Worker handler or a Playwright route that waits on a promise the test controls, or a breakpoint in the network layer. Record the request sequence (method, URL, start, end) and the screen state that is wrong. If you cannot make it happen on demand, you do not yet know which class it is.

### 2. Classify the race

| Symptom | Class | Signature in the request log |
| --- | --- | --- |
| Results for an earlier query, filter, tab or page replace the current ones | Out-of-order response | Two requests for the same slot overlap; the earlier one finishes last |
| Two orders, payments, comments or rows from one intent | Double submit | Two writes with the same body; from a double click, Enter plus click, a retry after a timeout, a resubmit after Back, or two tabs |
| UI changes, then reverts or flickers; or shows success the server refused | Optimistic divergence | A refetch started before the mutation lands after it; or two mutations in flight on one item; or an error with no rollback |
| A toast, redirect or data from the previous screen appears on the new one | Update after unmount or navigation | A response resolves after its component or route has gone |

Pushed updates over a WebSocket or server-sent events race the same way as responses: an older event applied after a newer fetch is an out-of-order response.

### 3. Out-of-order responses: make the latest win

Choose in this order:

1. **Keyed data fetching.** TanStack Query, SWR and RTK Query store each response under its key, and the screen reads the current key, so a late answer lands in its own slot instead of on screen. Pass the library's `signal` through to `fetch` so superseded requests are cancelled too.
2. **`AbortController` per slot.** Abort the previous request when a new one starts and treat `AbortError` as a non-event, not an error to display.
3. **A sequence token** where the work cannot be cancelled (a worker, a third-party SDK): number each request and drop any result whose number is not the latest.
4. **`switchMap`** if the code is already in RxJS.

For pushed updates, compare a server version or `updated_at` and discard anything older than what is on screen. Aborting a request does not stop the server's work, which is fine for reads; do not abort a write to make the latest one win, because the server may already have applied it.

### 4. Double submit: guard at three layers

- **Control.** Block re-entry synchronously at the start of the handler, with a ref or a flag, not only with state, because a state update has not re-rendered the disabled button when the second click arrives. Guard the form's `submit` event, not the button's click, so Enter is covered. Re-enable on failure.
- **Request.** Create one idempotency key per user intent with `crypto.randomUUID()` and send it on every attempt of that intent, conventionally as an `Idempotency-Key` header. A key generated per click defeats the purpose. Keep it across a network error or timeout, where the outcome is unknown; replace it when the user changes the payload after a definite rejection, because servers that implement keys usually refuse a reused key with a different body.
- **Server.** Confirm the endpoint stores the key with its result and returns that result for a repeat. If it does not, the client cannot fix this on its own; raise it as a server change and record it in the hand-back.

### 5. Optimistic updates: snapshot, cancel, apply, roll back, reconcile

1. Cancel in-flight reads for the affected key, so a fetch that started before the mutation cannot overwrite the optimistic value with an older snapshot.
2. Snapshot the current value.
3. Apply the optimistic value.
4. On error, restore the snapshot and tell the user what did not save.
5. On settle, success or failure, refetch or merge the server's answer, which is the truth.

Send absolute values (`liked: true`) rather than deltas or toggles; two toggles in flight cancel each other out on the server while the screen shows one. When several mutations on one item can overlap, serialise them per item or reconcile from the server rather than restoring the first snapshot, which would erase the second change. React 19's `useOptimistic` reverts to the real state when the action finishes, which covers step 4's restore but not step 5's reconcile.

### 6. Unmount and navigation: cancel in cleanup

Abort the request in the effect's cleanup, or set an `ignore` flag there and check it before setting state. Clear timers and subscriptions in the same cleanup. Pass the router's request signal into loaders where the router provides one. React's development Strict Mode mounts, unmounts and remounts each component once, so a bug that appears only in development is often this race showing up honestly rather than a Strict Mode artefact.

`references/race-fixes.md` has the code for each fix: an aborting effect, a sequence token, a submit guard with an idempotency key, a TanStack Query optimistic mutation with rollback, and version checks for pushed updates. Read it when writing or reviewing the fix.

### 7. Prove it with reversed and duplicated timing

Write one test per class you fixed, each failing before the fix:

| Class | The test |
| --- | --- |
| Out-of-order | Start two requests, release the second, then the first; assert the screen shows the second |
| Double submit | Double-click, and press Enter then click; assert one request. Fail the first attempt with a network error and retry; assert the same key |
| Optimistic | Make the server reject; assert rollback and a message. Run two toggles; assert the final state matches the server |
| Unmount | Unmount or navigate before the response; release it; assert no state change, toast or redirect |

Hold responses on promises the test resolves, not on timers. Where the code debounces, use fake timers and advance them explicitly. The skill does not pre-approve `npm` or `npx`, which can run any package script or download and run any package; the user approves each test run. `references/race-tests.md` has the patterns for Vitest or Jest with Testing Library and Mock Service Worker, and for Playwright. Read it when writing the tests.

## Output format

- A table of the feature's async paths: trigger, class, guard added, test name.
- The request log or reproduction that showed each race before the fix.
- Server dependencies: endpoints that do not honour an idempotency key, or lack the version field the client needs to discard stale pushes.
- Anything left at "narrowed" rather than "closed", and why.

## Reference files

- `references/race-fixes.md` — read when writing or reviewing a fix: code for latest-wins with `AbortController`, sequence tokens, the submit guard with an idempotency key, an optimistic mutation with rollback and reconcile, and stale-push discards.
- `references/race-tests.md` — read when writing the proof: held-response tests with Mock Service Worker, fake timers for debounced inputs, double-submit and retry assertions, and the same patterns in Playwright.
