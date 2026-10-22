# Race fixes

## Contents

- Latest wins with AbortController
- Latest wins with a sequence token
- Keyed fetching with TanStack Query
- Submit guard with an idempotency key
- Optimistic mutation with rollback and reconcile
- Discarding stale pushed updates
- Review checklist

The examples use React and plain `fetch` because they are the common case; the shape carries to any framework. Each one is the smallest version that closes the race, not a library to copy wholesale.

## Latest wins with AbortController

```jsx
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal })
    .then((res) => {
      if (!res.ok) throw new Error(`search failed: ${res.status}`);
      return res.json();
    })
    .then((data) => setResults(data.results))
    .catch((err) => {
      if (err.name !== 'AbortError') setError(err);
    });
  return () => controller.abort();
}, [query]);
```

The cleanup runs when `query` changes and when the component unmounts, so the same line fixes both the out-of-order and the unmount race. An abort during `res.json()` rejects with `AbortError` too, which is why the check sits in the final `catch`.

The fix only holds if the signal reaches the real request. A wrapper such as `api.search(q)` that does not accept and forward a `signal` silently turns this back into the original bug: the abort does nothing, the old promise resolves, and `setResults` runs with stale data.

## Latest wins with a sequence token

Use this where the work cannot be cancelled: a Web Worker, a third-party SDK, a promise you do not own.

```js
let latest = 0;

async function runSearch(query) {
  const id = ++latest;
  let results;
  try {
    results = await sdk.search(query);
  } catch (error) {
    if (id === latest) renderError(error); // a superseded failure is as stale as a superseded result
    return;
  }
  if (id !== latest) return; // superseded while in flight
  render(results);
}
```

In a component, keep the counter in a ref so it survives re-renders. The work still completes; only its result is dropped. Check the token on the failure path too: otherwise an older request that times out after the newer one succeeded puts an error over the correct results.

## Keyed fetching with TanStack Query

```jsx
const { data } = useQuery({
  queryKey: ['search', query],
  queryFn: ({ signal }) =>
    fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal }).then((r) => r.json()),
});
```

Each query string gets its own cache entry, and the component reads the entry for the current key, so a late response for an old key never reaches the screen. Forwarding `signal` lets the library cancel superseded requests as well. Placeholder data shown while the new key loads (`placeholderData: keepPreviousData` in v5) is the previous result on purpose; label it as such in the UI if users could mistake it for the answer.

## Submit guard with an idempotency key

```jsx
const inFlight = useRef(false);
const intentKey = useRef(null);

async function onSubmit(event) {
  event.preventDefault();
  if (inFlight.current) return;           // synchronous: blocks the second click before re-render
  inFlight.current = true;
  setSubmitting(true);
  intentKey.current ??= crypto.randomUUID();

  try {
    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': intentKey.current },
      body: JSON.stringify(order),
    });
    if (res.ok) {
      const created = await res.json();   // read first: if the body fails, the retry must reuse the key
      intentKey.current = null;           // intent complete; the next order is a new intent
      onSuccess(created);
    } else if (res.status >= 400 && res.status < 500 && ![408, 409, 429].includes(res.status)) {
      intentKey.current = null;           // definite rejection; the corrected payload is a new intent
      setError(await res.json());
    } else {
      setError('Could not confirm the order. Try again.'); // outcome unknown: keep the key
    }
  } catch {
    setError('Could not confirm the order. Try again.');   // network error: keep the key
  } finally {
    inFlight.current = false;
    setSubmitting(false);
  }
}
```

Attach the handler to the form's `onSubmit`, so Enter and the button go through the same guard. The key lives as long as the user's intent: it survives retries after an unknown outcome, and it is replaced once the server has given a definite answer. Clear it only after the success body has been read: a connection that drops while the body is streaming lands in the `catch`, and a key already cleared there would send the retry with a new key and create a second order. The branch excludes `408`, `409` and `429` from the definite-rejection case: a timeout may have been processed, a `409` from an in-progress duplicate means "still processing", and clearing the key on any of them would send the retry as a second order. Check how your server uses `422` and the other 4xx codes before copying the branch.

## Optimistic mutation with rollback and reconcile

TanStack Query v5:

```jsx
const queryClient = useQueryClient();
const key = ['post', postId];

const likeMutation = useMutation({
  mutationFn: (liked) => api.setLiked(postId, liked),     // absolute value, not a toggle
  onMutate: async (liked) => {
    await queryClient.cancelQueries({ queryKey: key });   // stop an older read overwriting us
    const previous = queryClient.getQueryData(key);
    queryClient.setQueryData(key, (old) => ({ ...old, liked }));
    return { previous };
  },
  onError: (_error, _liked, context) => {
    queryClient.setQueryData(key, context.previous);
    toast('Your like was not saved.');
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
});
```

If two mutations on the same post can overlap, restoring the first one's `previous` on error erases the second's optimistic value. Either serialise mutations per item (`scope: { id: key.join(':') }` runs mutations with the same scope id one after another in v5) or skip the snapshot restore and rely on the `onSettled` refetch as the source of truth.

React 19's `useOptimistic` shows the optimistic value only while its action is pending and falls back to the real state afterwards. That handles the restore, but the real state still has to be refreshed from the server for the reconcile.

## Discarding stale pushed updates

```js
socket.addEventListener('message', (event) => {
  const update = JSON.parse(event.data);
  const current = store.get(update.id);
  if (current && update.version <= current.version) return; // older than what is shown
  store.set(update.id, update);
});
```

A delete must leave a tombstone that keeps its version, or an older update that arrives afterwards finds nothing in the store and re-creates the item. Apply the same check when a fetch response arrives, so a slow fetch cannot overwrite a newer pushed update either. This needs a monotonic version or revision from the server; a client clock or `Date.now()` is not one.

## Review checklist

- [ ] Every request for a shared slot is keyed, aborted on supersede, or tokenised.
- [ ] Every `signal` reaches the real network call through every wrapper.
- [ ] `AbortError` is filtered out of error handling and error reporting.
- [ ] Every write guarded synchronously and through the form's submit event.
- [ ] One idempotency key per intent, kept on unknown outcomes, replaced after a definite answer.
- [ ] The server stores and replays idempotency keys for that endpoint.
- [ ] Optimistic writes cancel reads first, send absolute values, roll back on error and reconcile on settle.
- [ ] Every effect that starts async work cleans it up.
