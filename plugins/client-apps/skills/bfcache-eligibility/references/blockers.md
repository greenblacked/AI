# Blockers and how to clear them

Read this in step 2 for the fix that matches a not-restored reason, and in step 4 for the
field snippet.

## Contents

- Blocker table
- Finding a third-party unload listener
- Closing and reopening connections
- Field snippet: restore rate and reasons
- Browser differences worth knowing

## Blocker table

| Reason as DevTools describes it | Typical source | Change |
| --- | --- | --- |
| Unload handler | Analytics, session replay, A/B testing and consent scripts; legacy code that saves state on exit | Listen for `pagehide` instead; send data with `navigator.sendBeacon` there or on `visibilitychange` to hidden |
| `Cache-Control: no-store` on the main resource | Framework default for server-rendered pages, CDN rule applied to all HTML, a session middleware | Remove it where the page holds nothing sensitive; use `no-cache` when the intent is revalidation |
| WebSocket, WebRTC | Chat widgets, live updates, presence | Close on `pagehide`, reconnect on `pageshow` with `persisted` |
| IndexedDB connection with a transaction or a pending version change | Offline storage, client caches | Finish transactions before navigation; close the connection on `pagehide` and reopen on restore |
| BroadcastChannel | Cross-tab sync of auth or cart | Close it on `pagehide`, create a new one on restore |
| Outstanding fetch or XHR at navigation | Polling, long-polling, a slow analytics request | Abort with an `AbortController` on `pagehide`; restart on restore |
| Held Web Lock | Leader election between tabs | Release on `pagehide` |
| `window.opener` or an opened window holding a reference | `window.open()` without `noopener`, payment or login pop-ups | Use `noopener`; pass results back with `postMessage` to a named channel instead of the opener reference |
| Dedicated or shared worker with work in progress | Background computation | Pause work on `pagehide` |

Pending-support reasons change as browsers add support; recheck them against current
DevTools output rather than this table.

## Finding a third-party unload listener

```js
// In the DevTools console on the affected page
getEventListeners(window).unload
getEventListeners(window).beforeunload
```

Each entry has a `listener` you can click through to its source. If it belongs to a vendor
script, the options in order of preference are: a vendor setting that disables it, a newer
version of the tag that uses `pagehide`, the `Permissions-Policy: unload=()` response header
(which stops any script on the page adding one, in browsers that support it), or removing
the tag. Check the policy header against what the vendor needs before sending it; a script
that relied on `unload` to flush data must flush on `pagehide` instead.

## Closing and reopening connections

```js
let socket = connect();
let channel = new BroadcastChannel('cart');

window.addEventListener('pagehide', (event) => {
  if (event.persisted) {
    // The page is entering the back/forward cache.
    socket.close();
    channel.close();
  }
});

window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    socket = connect();
    channel = new BroadcastChannel('cart');
    refreshVolatileState();
  }
});
```

`event.persisted` on `pagehide` is true when the browser intends to cache the page. Closing
connections even when it is false is harmless, since the page is being discarded.

## Field snippet: restore rate and reasons

```js
addEventListener('pageshow', (event) => {
  if (event.persisted) {
    beacon({ kind: 'bfcache', outcome: 'restored', route: currentRouteTemplate() });
  }
});

const nav = performance.getEntriesByType('navigation')[0];
if (nav && nav.type === 'back_forward') {
  // This load is a back/forward navigation that was not restored from the cache.
  const r = nav.notRestoredReasons; // undefined where the API is not supported
  beacon({
    kind: 'bfcache',
    outcome: 'not_restored',
    route: currentRouteTemplate(),
    reasons: r ? flatten(r) : null,
  });
}

function flatten(node, out = []) {
  for (const item of node.reasons ?? []) out.push(item.reason);
  for (const child of node.children ?? []) flatten(child, out);
  return out;
}

function beacon(body) {
  navigator.sendBeacon('/rum', JSON.stringify(body));
}
```

Restore rate per route is `restored / (restored + not_restored)`. Group the misses by
reason and fix from the top. A miss whose reasons are empty or withheld in a browser that
supports the API often points at a cross-origin iframe; list the page's third-party frames
and test with each removed.

## Browser differences worth knowing

- Every major engine has a back/forward cache, but the eligibility rules differ and change
  between releases. Test the browsers your users use rather than inferring from Chrome.
- Treat `unload` as unreliable everywhere: on mobile it often does not fire at all when the
  user switches apps, so any data it was sending was already being lost.
- Chrome limits how long a page stays cached and how many pages it keeps; a long absence
  ends in a normal reload, and that is expected, not a defect.
