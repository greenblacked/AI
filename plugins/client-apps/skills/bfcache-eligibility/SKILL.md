---
name: bfcache-eligibility
description: "Make back and forward navigations restore instantly from the browser's back/forward cache: run the DevTools back/forward cache test and read its not-restored reasons, clear blockers in the order they usually occur (unload handlers moved to pagehide, Cache-Control: no-store on pages that do not need it, open WebSocket, BroadcastChannel and IndexedDB connections closed on pagehide, a window.opener reference), refresh stale state on pageshow, and measure the restore rate in the field with the notRestoredReasons API. Use when someone says \"the back button reloads the whole page\", \"going back loses the scroll position and the filters\", \"Lighthouse flags back/forward cache\" or \"why is our page not bfcache eligible\". Not for poor LCP, INP or CLS (web-vitals-triage), server or CDN data caching (application-caching), or offline support (pwa-service-worker)."
allowed-tools: "Read, Grep, Glob"
---

# Back/Forward Cache Eligibility

Done means the DevTools test restores the page from the back/forward cache, every remaining not-restored reason is either fixed or written down as outside your control, the page refreshes whatever goes stale while it sits in the cache, and a field restore rate exists to show the change held.

The back/forward cache keeps a whole page — DOM, JavaScript heap, scroll position, form state — frozen in memory when the user navigates away, and resumes it when they press back. A restore is effectively instant, and it is a large share of all navigations on mobile. Pages lose it silently: one `unload` listener added by an analytics tag, one header set by a framework default, one WebSocket left open, and every back navigation becomes a full reload that refetches, re-renders and forgets where the user was. Nothing errors. The second failure comes after the fix: a page that is now restored shows a cart count, a login state or a price that was true five minutes ago, because nothing listened for the restore.

## Scope

Use for: back or forward navigations that reload instead of restoring; Lighthouse's back/forward cache audit failing; scroll position and form state lost on back; measuring how often restores happen; stale state after a restore.

Do not use for: a poor field LCP, INP or CLS in general (`web-vitals-triage`), even though restores improve those numbers; caching data on a server or CDN (`application-caching`); offline behaviour, install, or a service worker's caches (`pwa-service-worker`).

## Workflow

### 1. Test it and read the reasons

In Chrome DevTools open Application, then Background services, then Back/forward cache, and press "Test back/forward cache". DevTools navigates away and back and reports whether the page was restored and, if not, every reason, sorted into three groups:

- **Actionable** — something the page does that you can change.
- **Pending support** — something Chrome does not yet support caching with; usually a feature the page uses that you can avoid or release before navigation.
- **Not actionable** — outside the page's control, such as an extension or a browser state.

Run it in a clean profile with extensions disabled, and on the real page in its real state: logged in, with the cart filled, after the interactions users actually make. A page that is eligible fresh and ineligible after a chat widget connects is the common case. Repeat for each page template that users go back to — listing and search results pages matter most.

Lighthouse's back/forward cache audit reports the same reasons for a single load, which is useful in CI but sees only the state of an untouched page.

Gate: write down each reason with the template it appears on before changing code.

### 2. Clear the blockers, most common first

`references/blockers.md` has each blocker with the code change that clears it. In the order they usually turn up:

1. **`unload` listeners.** The most frequent blocker, often added by a third-party script rather than your code. Move the work to `pagehide`, which fires in every case `unload` did and does not block the cache. Find the owner with `getEventListeners(window)` in the DevTools console. To stop third parties re-adding one, send `Permissions-Policy: unload=()` where the browser supports it.
2. **`Cache-Control: no-store` on the document.** Often a framework or CDN default rather than a decision. Keep it on pages that genuinely show sensitive data after login, and remove it elsewhere; if the goal is "always revalidate", `no-cache` says that without blocking the cache.
3. **Open connections.** A WebSocket, a WebRTC connection, an IndexedDB connection with a transaction in flight, a `BroadcastChannel`, a held Web Lock, or a fetch still in progress at navigation. Close or release them on `pagehide` and reopen them on `pageshow` when `event.persisted` is true.
4. **`window.opener`.** A page opened by `window.open()` or a link that keeps an opener reference can be ineligible. Open new windows with `noopener` unless the opener relationship is required.
5. **`beforeunload`.** Add it only while there is unsaved data and remove it once the data is saved, so a page with nothing to lose never carries it.

After each change, rerun the DevTools test on the same page in the same state. One blocker usually hides the next.

### 3. Handle the restore

A restored page resumes with its JavaScript state exactly as it was. Listen for it:

```js
window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    refreshVolatileState();   // cart count, auth state, prices, notifications
    reconnect();              // whatever pagehide closed
    reportPageView();         // analytics counts a restore as a page view
  }
});
```

Decide what is volatile per page. A restored product page with yesterday's stock level is a defect the cache introduced, and so is a logged-out user who presses back and sees an account page. For pages that show personal data, check the session on restore and navigate away or reload if it has ended.

Timers and in-memory clocks pause while frozen. A countdown or "last updated" label must be recomputed from the current time on restore.

### 4. Measure the restore rate in the field

The DevTools test proves one page can be restored; the field shows whether it is. Two counts give the rate:

- restores: `pageshow` events with `event.persisted` true;
- back/forward navigations that were not restored: navigation entries whose `type` is `back_forward`.

The restore rate is restores divided by the sum of both, per page template. For the misses, read `notRestoredReasons` from the navigation entry (`performance.getEntriesByType('navigation')[0].notRestoredReasons`, in browsers that support it) and send the reasons with the beacon. It includes reasons from same-origin iframes; a cross-origin iframe's reasons are withheld, so a miss caused by one shows up without detail. The snippet is in `references/blockers.md`.

Gate: the change is done when the restore rate for the template rises and the top remaining reason is one you have decided to accept. A reason affecting a few per cent of misses may not be worth a refactor; say so.

## Anti-patterns

**Assuming a single-page app has no back/forward cache problem.** Navigations inside the app do not use the cache, but leaving to another site and pressing back does, and that restores or reloads the whole app.

**Removing `no-store` from an authenticated page to pass the test.** The cache would then restore account details after logout on a shared device. Keep the header there and accept the miss.

**Closing connections on `visibilitychange` alone.** The page can be hidden without navigating; reconnect logic keyed on visibility then churns the socket every time the user switches tabs. Use `pagehide` and `pageshow` for navigation, visibility for pausing work.

**Fixing the test page only.** The blocker that matters is on the page users go back to, in the state they leave it, which is rarely a freshly loaded homepage.

**Counting restores as no navigation.** Analytics that fire only on load undercount page views once restores rise, and the dashboard shows a traffic drop that is not real.

## Output format

```markdown
## Pages tested
[Template, state tested in, restored or not.]

## Reasons found
[Each reason, its group (actionable, pending support, not actionable), and its source script or header.]

## Changes
[Each blocker cleared and how; the restore handler and what it refreshes.]

## Field
[Restore rate per template before and after, and the top remaining reasons with a decision on each.]
```

## Reference files

- `references/blockers.md` — read in step 2 and step 4: each blocker with the change that clears it, how to find a third-party `unload` listener, and the field snippet that reports restore rate and not-restored reasons.
