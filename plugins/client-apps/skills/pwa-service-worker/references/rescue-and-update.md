# Rescue worker, update prompt and test matrix

## Contents

- The rescue worker
- The update prompt
- Lifecycle test matrix

## The rescue worker

Deploy this file at the exact URL of the real worker, served with
`Cache-Control: no-cache`, to remove the worker from every browser that has it.

```js
// sw.js, rescue build: same URL as the real worker.
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.map((name) => caches.delete(name)));
    await self.registration.unregister();
    const windows = await self.clients.matchAll({ type: 'window' });
    for (const client of windows) client.navigate(client.url);
  })());
});
// No fetch handler, so every request goes to the network.
```

In the same release, remove the `register()` call from the page, or replace it with code
that unregisters any existing registration; otherwise every page load installs the
rescue again only for it to remove itself. Pages still served from the old worker's
cache will register too, which is fine: what they install is now the rescue.

Rehearse on staging before relying on it:

1. Install the real worker and load the app until its caches are populated.
2. Deploy the rescue at the same URL.
3. Reload the tab once. In DevTools, Application, Service workers shows no worker for
   the origin, and Cache storage is empty.
4. Repeat with a tab that was left open across the deploy, and with the browser offline
   during the deploy and back online afterwards.

Record the date of the last rehearsal. A rescue that has never run is a guess.

## The update prompt

Page side:

```js
const reg = await navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' });
let accepted = false;

function offerUpdate(worker) {
  showUpdateBanner(() => {               // your UI; called when the user accepts
    accepted = true;
    worker.postMessage({ type: 'SKIP_WAITING' });
  });
}

function watch(incoming) {
  incoming.addEventListener('statechange', () => {
    if (incoming.state === 'installed' && navigator.serviceWorker.controller) offerUpdate(incoming);
  });
}

if (reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg.waiting);
if (reg.installing) watch(reg.installing);   // an update that began before this script ran

reg.addEventListener('updatefound', () => {
  if (reg.installing) watch(reg.installing);
});

navigator.serviceWorker.addEventListener('controllerchange', () => {
  if (!accepted) return;                 // first install, or another tab's choice
  accepted = false;
  window.location.reload();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') reg.update().catch(() => {});
});
```

Worker side:

```js
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});
```

The `controller` check separates an update from a first install, which has nothing to
prompt about. The `reg.installing` check covers the update the page load itself started:
the browser checks for a new worker on navigation, and when it finds one before
`register()` resolves, `updatefound` fires with no listener attached and the worker is
still installing, so neither `reg.waiting` nor the listener would ever offer it. The `accepted` flag keeps a tab from reloading because the user accepted
the update in a different tab; that tab keeps running its old HTML under the new worker, so
have the handler set a stale or "reload to finish" state there rather than returning silently.

## Lifecycle test matrix

Run each row in Chromium and in Safari.

| Case | Steps | Expected |
| --- | --- | --- |
| First visit | Clear site data, load | Worker installs; no prompt; no reload |
| Offline reload | Load, go offline, reload, open two routes | Shell and core screens render; writes show as queued |
| Deploy with tab open | Deploy a new build while a tab is open | Prompt appears on next update check; nothing breaks before accepting |
| Accept update | Click the prompt | One reload; the new build is in control |
| Two tabs | Accept in one tab | The other tab does not reload on its own |
| Logout | Sign in, browse, sign out | Per-user caches deleted; offline reload shows no previous user data |
| Offline write | Submit offline, reconnect, retry twice | Exactly one record on the server |
| Quota pressure | Fill storage until writes fail | App reports the failure; the shell still loads |
| Rescue | Deploy the rescue | No worker, empty caches, app loads from the network |
