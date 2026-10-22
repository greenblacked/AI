# Race tests

## Contents

- The principle: hold, then release in the order you choose
- Component tests with Mock Service Worker
- Debounced inputs with fake timers
- Double submit and retry
- Optimistic rollback
- Unmount
- The same patterns in Playwright

## The principle: hold, then release in the order you choose

A race test must make the dangerous order happen every run. Hold each response on a promise the test owns, start the requests, then resolve them in the order that broke production. `Promise.withResolvers()` (Node 22 and current browsers) gives the promise and its `resolve` together; on older runtimes, build the same pair with `new Promise`.

Mock at the network layer rather than by stubbing the client's own API wrapper. A stub that ignores the `AbortSignal` will resolve an aborted request and make a correct fix look broken, and a stub that the fix does not route through will make a broken fix look correct.

Before trusting a race test, revert the fix and watch it fail.

## Component tests with Mock Service Worker

Vitest or Jest with Testing Library and Mock Service Worker v2:

```js
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const held = new Map(); // query string -> { promise, resolve, handled }

const server = setupServer(
  http.get('*/api/search', async ({ request }) => {
    const q = new URL(request.url).searchParams.get('q');
    const gate = Promise.withResolvers();
    const handled = Promise.withResolvers();
    held.set(q, { ...gate, handled });
    await gate.promise;
    handled.resolve();                                   // runs whether or not the client aborted
    return HttpResponse.json({ results: [`result for ${q}`] });
  }),
);

beforeAll(() => server.listen());
afterEach(() => { server.resetHandlers(); held.clear(); });
afterAll(() => server.close());

test('the latest query wins when responses arrive in reverse order', async () => {
  const user = userEvent.setup();
  render(<Search />);

  await user.type(screen.getByRole('searchbox'), 'ab'); // requests for "a" and "ab"
  await vi.waitFor(() => expect(held.has('ab')).toBe(true));

  held.get('ab').resolve();
  expect(await screen.findByText('result for ab')).toBeInTheDocument();

  await act(async () => {
    held.get('a').resolve();                             // the stale one arrives last
    await held.get('a').handled.promise;                 // the server has answered it
    await new Promise((resolve) => setTimeout(resolve, 0)); // let the client process the reply
  });
  expect(screen.queryByText('result for a')).not.toBeInTheDocument();
  expect(screen.getByText('result for ab')).toBeInTheDocument();
});
```

Use `waitFor` from Testing Library instead of `vi.waitFor` under Jest. Import `act` from `@testing-library/react`. The test waits on a signal the handler itself raises, not on MSW's `response:mocked` event, because that event may never fire for a request the code aborted and the test would hang. Revert the fix once and confirm the test fails.

## Debounced inputs with fake timers

```js
vi.useFakeTimers();
const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

await user.type(screen.getByRole('searchbox'), 'a');
await vi.advanceTimersByTimeAsync(300);   // past the debounce: request for "a" starts
await user.type(screen.getByRole('searchbox'), 'b');
await vi.advanceTimersByTimeAsync(300);   // request for "ab" starts while "a" is held
```

Then release in reverse as above. A debounce shorter than the slowest response leaves the race open, and this test shows it; a test that never lets two requests overlap proves only that the debounce exists.

## Double submit and retry

```js
const posts = [];
server.use(
  http.post('*/api/orders', async ({ request }) => {
    posts.push(request.headers.get('Idempotency-Key'));
    return HttpResponse.json({ id: 'order-1' }, { status: 201 });
  }),
);

await user.dblClick(screen.getByRole('button', { name: 'Place order' }));
await screen.findByText('Order placed');
expect(posts).toHaveLength(1);
expect(posts[0]).toMatch(/^[0-9a-f-]{36}$/);
```

Repeat with Enter in a field followed by a click on the button. For the retry case, answer the first attempt with `HttpResponse.error()` (a network error), let the user retry, and assert that both attempts carried the same key. Then answer one attempt with a definite `422`, let the user correct the field, and assert that the next attempt carried a new key.

## Optimistic rollback

Answer the mutation with an error status and assert three things: the optimistic value appeared before the response, the original value is back after it, and the user was told. For overlapping mutations, hold two mutation responses, release them in reverse, then let the settle refetch return the server's final state and assert the screen matches it rather than either optimistic value.

## Unmount

Hold the response, unmount the component (`unmount()` from `render`) or navigate away in the router, then release it. Assert the absence of what the stale callback would have done: no toast, no redirect, no write to a shared store. React 18 and later no longer warn about state updates on unmounted components, so silence in the console is not evidence.

## The same patterns in Playwright

Hold a request on a promise the test resolves, rather than on a delay:

```ts
import { test, expect, type Request } from '@playwright/test';

test('latest query wins', async ({ page }) => {
  const releaseFirst = Promise.withResolvers<void>();
  const firstSettled = Promise.withResolvers<void>();
  const isFirst = (req: Request) => new URL(req.url()).searchParams.get('q') === 'a';
  page.on('requestfinished', (req) => isFirst(req) && firstSettled.resolve());
  page.on('requestfailed', (req) => isFirst(req) && firstSettled.resolve()); // aborted by the client

  await page.route('**/api/search?*', async (route) => {
    if (isFirst(route.request())) await releaseFirst.promise;
    await route.continue().catch(() => {}); // the client may have aborted it meanwhile
  });

  await page.goto('/search');
  await page.getByRole('searchbox').pressSequentially('ab');
  await expect(page.getByText('result for ab')).toBeVisible();

  releaseFirst.resolve();
  await firstSettled.promise;
  await page.evaluate(() => new Promise(requestAnimationFrame)); // let a stale update render
  await expect(page.getByText('result for a', { exact: true })).toHaveCount(0);
});
```

Count writes with `page.on('request', ...)` filtered to the method and URL, and read the idempotency key from `request.headers()`. Keep these as a small number of targeted tests; the component tests above are where most race coverage belongs, because they run in milliseconds and cannot be slowed by a busy CI runner.
