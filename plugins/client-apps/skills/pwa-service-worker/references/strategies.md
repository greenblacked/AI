# Caching strategies by resource class

Contents: the decision table, expiry and quota, navigation handling, and the Workbox
names for each strategy.

## Decision table

| Class | Examples | Strategy | Expiry | Cleared when |
| --- | --- | --- | --- | --- |
| Hashed build output | `/assets/app-3f9a1c.js`, fonts, CSS | Precache from the build manifest | Replaced by the next build's precache | Activate of a newer build |
| Unhashed static files | `/favicon.ico`, `/manifest.webmanifest` | Stale-while-revalidate | Short maximum age | Activate |
| Navigation, single-page app | Any in-scope URL | Serve the precached shell | With the shell | Activate |
| Navigation, server-rendered | Article and product pages | Network-first with a timeout, falling back to the cached copy or an offline page | Entry cap | Activate |
| Public reads that tolerate staleness | Catalogue, reference data | Stale-while-revalidate | Entry cap and maximum age | Activate, or on a data version change |
| Per-user reads | Profile, inbox, orders | Network-first, or network-only | Short | Logout, account switch |
| Writes | Any non-`GET` | Network-only; queue in IndexedDB when offline | Until acknowledged | Never silently |
| Auth, payment, third-party login | `/login`, `/oauth/*`, payment pages | Network-only, never intercepted for caching | — | — |
| Cross-origin opaque | Third-party images or scripts loaded `no-cors` | Not cached, or cache-first with a strict entry cap if offline display needs it | Strict cap | Activate |
| Media with range requests | Video, large audio | Not cached by default | — | — |

Decide per class and write the reason next to it. A class nobody can justify caching is
better left on the network: an uncached request fails visibly offline, while a wrongly
cached one fails quietly online.

## Rules that apply to every class

- Store a response only when `response.ok` is true. An opaque response has status `0` and
  cannot be checked, which is why the table treats it separately.
- Key per-user caches so logout can delete them in one call, and delete them on logout
  and on account switch.
- Set an entry cap on every runtime cache. A cache with no cap grows until the browser
  evicts the whole origin, offline shell included.
- Read usage with `navigator.storage.estimate()`, and call `navigator.storage.persist()`
  for apps whose offline data matters; check the result rather than assuming it was
  granted.

## Navigations

For a network-first navigation, enable navigation preload in `activate`
(`self.registration.navigationPreload.enable()`) and use `event.preloadResponse` in the
fetch handler, so the network request is not delayed by worker start-up. Give the
network a timeout before falling back; a slow connection that never errors otherwise
leaves the user staring at a blank page while a perfectly good cached copy sits unused.

## Workbox equivalents

If the project uses Workbox, the table maps onto its modules:

| Strategy | Workbox |
| --- | --- |
| Precache | `precacheAndRoute(self.__WB_MANIFEST)` from `workbox-precaching` |
| Cache-first | `CacheFirst` from `workbox-strategies` |
| Network-first with timeout | `NetworkFirst` with `networkTimeoutSeconds` |
| Stale-while-revalidate | `StaleWhileRevalidate` |
| Network-only | `NetworkOnly` |
| Entry cap and maximum age | `ExpirationPlugin` from `workbox-expiration` (`maxEntries`, `maxAgeSeconds`) |
| Status filtering | `CacheableResponsePlugin` from `workbox-cacheable-response` |
| Offline write queue | `BackgroundSyncPlugin` from `workbox-background-sync` |

The library does not decide the classes; the table does. Workbox with a single
catch-all route is the same mistake as a hand-written worker with one.
