---
name: pwa-service-worker
description: "Make a web app work offline and install cleanly, with a way out when its service worker goes wrong: ship the rescue first, a no-op worker at the same URL that clears caches and unregisters itself; pick a strategy per resource class (precache the hashed shell, stale-while-revalidate for tolerant reads, network-only for writes); name caches by build and delete old ones on activate; show a waiting worker as an update prompt, not a blind skipWaiting; queue offline writes with idempotency keys. Use when someone asks to \"make it work offline\" or \"turn this into a PWA\", or reports \"users stuck on an old version\" or \"the service worker serves stale files\". Not for server-side data caching (application-caching), chunk errors in old tabs with no worker involved (deploy-version-skew), back-button reloads (bfcache-eligibility), or a native store release (mobile-release)."
allowed-tools: Read, Grep, Glob
---

# PWA Service Worker

Done means the app opens and does its core job with no network, a new release
reaches every user within one visit of shipping, writes made offline arrive exactly once,
and there is a tested way to remove the worker from every browser that has it.

A service worker sits between the page and the network for every request in its scope,
and it outlives deploys. The failure that hurts is not "offline does not work"; it is a
worker that cached a broken shell and keeps serving it, so nothing the team deploys
reaches the users who need it. Teams discover that the escape hatch has to be served at
the same URL as the worker, by the same origin, before the day they need it.

## Scope

Use for: adding offline support or installability to a web app, reviewing an existing
worker, recovering users pinned to an old version, update prompts, and offline write
queues.

Do not use for: runtime caching of application data on the server (`application-caching`),
chunk-load errors after a deploy when no worker is involved (`deploy-version-skew`),
back and forward navigations that reload (`bfcache-eligibility`), HTTP caching semantics
of a public API (`api-design`), or a native app (`mobile-release`).

## Workflow

### 1. Ship the rescue before the first real worker

Browsers look for a newer worker by fetching the script at the URL it was registered
with. Deleting that file is not a reliable way out: under the specification a failed
update check simply fails, and the installed worker keeps control and keeps serving its
caches. So the worker's URL is permanent, and the way out
is a replacement script at that URL.

- Pick one URL (`/sw.js`) and never rename it. Registering a new name leaves the old
  worker installed beside it.
- Serve it with `Cache-Control: no-cache` from the origin and the CDN, and register with
  `updateViaCache: 'none'` so imported scripts are revalidated too.
- Write the rescue worker now, keep it in the repository, and rehearse swapping it in on
  staging. It takes over at once, deletes every cache it owns, unregisters, and reloads
  open windows onto the network. The code and the rehearsal are in
  `references/rescue-and-update.md`.
- The `Clear-Site-Data` response header is a second lever where the browser supports it.
  Only `"storage"` (or `"*"`) unregisters the worker and empties Cache Storage; `"cache"`
  clears the HTTP cache only and will not free a pinned user. `"storage"` also wipes
  IndexedDB and local storage, including any queued offline writes, so use it knowingly.

### 2. Classify every request before choosing a strategy

List the request classes the app makes and give each one strategy, with the reason
written down. A single "cache everything" handler is how a logged-out user sees the
previous user's data.

| Class | Strategy | Why |
| --- | --- | --- |
| Hashed static assets | Precache at install, or cache-first | Content never changes under a given name |
| App shell for navigations | Precached shell (single-page), or network-first falling back to the cached shell | The page must open offline; server-rendered pages want fresh HTML when online |
| Reads that tolerate staleness | Stale-while-revalidate, with an entry cap and maximum age | Instant on repeat, refreshed in the background |
| Per-user or sensitive reads | Network-first or network-only; if cached, cleared on logout | A shared device must not show the last user's data |
| Writes (`POST`, `PUT`, `PATCH`, `DELETE`) | Network-only, queued when offline (step 5) | The Cache API stores only `GET` requests, and a replayed write needs a key |
| Login, payment, third-party auth | Network-only | Correctness beats availability here |
| Cross-origin opaque responses | Do not cache by default | Status is unreadable, so an error is cached as a success, and Chromium counts them at an inflated size against quota |

Cache a response only when `response.ok` is true. The full decision table, with
expiration and quota notes, is in `references/strategies.md`.

### 3. Version caches and clean up on activate

- Name caches with the build id (`shell-3f9a1c`, `api-reads-v4`), and prefix them so the
  worker deletes only its own.
- Precache in `install` with `cache.addAll()`: if any file fails, install fails and the
  previous worker stays in charge, which is the behaviour you want.
- In `activate`, inside `event.waitUntil()`, delete every cache with your prefix that the
  current build does not name.
- For network-first navigations, enable navigation preload so the network request starts
  while the worker boots.

### 4. Make updates visible instead of forced

A new worker installs and then waits until no tab uses the old one. Calling
`self.skipWaiting()` unconditionally in `install` lets the new worker take over pages that
were loaded with the old HTML, whose next lazy import still asks for the old build's file names, now through a worker whose
`activate` step has deleted the old caches, so those requests fall through to the network and
break once the origin has pruned them: version skew inside one tab.

- Detect a waiting worker (`registration.waiting`, or `updatefound` followed by the new
  worker reaching `installed` while `navigator.serviceWorker.controller` is set) and show
  an "update available" prompt.
- On accept, post a message to the waiting worker; it calls `self.skipWaiting()`. Reload
  once on `controllerchange`, behind a flag so it cannot loop.
- A single-page app that never does a full navigation may go a long time without an
  update check. Call `registration.update()` when the tab becomes visible again.

### 5. Queue offline writes with idempotency keys

- Generate the idempotency key when the user acts, not at replay time, and store it with
  the request in IndexedDB.
- Replay on reconnect: at app start, on the `online` event, and through Background Sync
  where it exists (Chromium only, so it is an addition, not the mechanism).
- The server deduplicates on the key; the contract for that belongs to `api-design`.
- Show queued items as pending in the interface, surface conflicts and permanent failures
  to the user, and never drop a queued write silently.

### 6. Check installability where it is decided

Write a manifest with `name`, `short_name`, `start_url`, `scope`, `display` and icons
including 192 and 512 pixel sizes, served from the same origin. Read the installability
problems Chromium reports in DevTools, Application, Manifest, rather than a checklist,
because the criteria change. On iOS there is no `beforeinstallprompt`: installation is
Share, then Add to Home Screen, and the installed app keeps its storage separate from
Safari's, so a user signed in on the website is not signed in in the installed app.
Safari-only storage behaviour belongs to `webkit-only-bug-triage`.

### 7. Test the lifecycle, not just offline

Run the matrix in `references/rescue-and-update.md`: first visit, offline reload, a
deploy while a tab is open, accepting the update, logout clearing per-user caches, quota
pressure, and the rescue deploy. Use DevTools, Application, Service workers (Offline,
Update on reload, Bypass for network) and `chrome://serviceworker-internals` in
Chromium, and the Web Inspector in Safari.

## Output format

1. **Rescue** — the worker URL, its cache headers, the rescue script's location and the
   date it was last rehearsed.
2. **Strategy table** — every request class, its strategy, expiry and the reason.
3. **Update flow** — how a waiting worker is detected, the prompt, the reload guard.
4. **Offline writes** — queue storage, key generation, replay triggers, conflict handling.
5. **Test results** — each row of the matrix, in Chromium and Safari.

## Anti-patterns

**A worker with no rescue.** The first bad deploy pins users to it, and the fix cannot be
shipped through the channel that is broken.

**Renaming the worker to escape a bad one.** The old registration stays in control of its
scope; the new one never reaches those users.

**`skipWaiting()` in every install.** It looks like faster updates and produces mixed
versions inside one tab.

**Caching every `GET`.** Error pages, per-user data and opaque responses end up served
offline, to the wrong user, or as successes.

**An offline queue without keys.** Every reconnect that retries a half-sent request
creates a duplicate order.
