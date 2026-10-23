---
name: webkit-only-bug-triage
description: "Triage a bug that only happens in Safari or on iPhone and iPad: reproduce it in real WebKit (a device, the iOS Simulator or Playwright's WebKit build) with Web Inspector attached before reading code, then check the usual causes in order: 100vh against dvh and the safe area, inputs under 16px zooming on focus, sticky and overflow clipping, date inputs and date parsing, ITP's seven-day cap on script-writable storage, IndexedDB eviction, and an API the user's iOS version lacks. Fix with feature queries, not user-agent checks. Use when someone says \"works in Chrome, broken on iPhone\", \"only fails in Safari\", \"the page jumps when the keyboard opens\" or \"iOS users get logged out after a week\". Not for choosing breakpoints (responsive-design), a flaky cross-browser test suite (e2e-testing), a WCAG audit (accessibility-audit), or a bug that fails in every browser (debugging)."
allowed-tools: Read, Grep, Glob
---

# WebKit-Only Bug Triage

Done means the bug reproduced in the same engine and version the user has, a
cause named from the known list or reduced to a minimal case, a fix gated by feature
detection, and a check that keeps it from coming back.

The usual failure is debugging Safari from Chrome. Someone reads the code with a Chromium
mental model, adds a user-agent check that matches the reporter's device, and ships a
fix that misses iPads (which report a desktop Mac user agent by default) and breaks the
next Safari release that fixed the original behaviour. Most WebKit-only bugs are a short
list of well-known differences; checking that list in order, in the real engine, is
faster than reading code.

## Scope

Use for: anything that works in Chromium or Firefox and fails in Safari on macOS, iOS or
iPadOS, including other browsers on iOS, which use WebKit outside the regions where Apple
permits other engines.

Do not use for: choosing breakpoints or reflow (`responsive-design`), a flaky browser
test suite (`e2e-testing`), a WCAG audit including VoiceOver (`accessibility-audit`), a
service worker problem in every browser (`pwa-service-worker`), or a failure that
reproduces in every engine (`debugging`).

## Workflow

### 1. Pin down the exact environment

Get the device, the iOS or macOS version, and where the page runs: a Safari tab, another
browser on iOS, an installed Home Screen app, an in-app web view, Private Browsing, or
Lockdown Mode. Safari on iOS is updated with the operating system, so a user on an older
iOS has an older engine and cannot update it separately; the version decides which APIs
exist. Installed Home Screen apps keep storage separate from Safari tabs, and in-app web
views differ again, so a bug in one may not reproduce in another.

### 2. Reproduce in real WebKit before reading code

Use the highest-fidelity option available, in this order:

1. **A physical device with Web Inspector.** Enable Web Inspector in the device's Safari
   advanced settings, connect it to a Mac, and inspect from Safari's Develop menu. This
   is the only option that reproduces the on-screen keyboard, toolbar resizing, real
   touch input and Intelligent Tracking Prevention (ITP) exactly.
2. **The iOS Simulator.** It runs mobile Safari and is inspectable from the same Develop
   menu. Open a URL in the booted simulator with
   `xcrun simctl openurl booted https://staging.example.com/checkout`.
3. **Playwright's WebKit build.** `npx playwright open --browser webkit <url>` or
   `npx playwright test --project=webkit` when the config defines that project. It is a
   desktop WebKit build, not Safari: good for JavaScript engine and layout differences,
   not for the iOS viewport, keyboard, input zoom or ITP.

Do not start on the code until the bug reproduces, or until the user's console and
network logs are captured from their device. If it will not reproduce, add the engine,
version and display mode to the error reports and wait for the next occurrence rather
than fixing a guess. Setup details are in `references/reproduction-setup.md`.

### 3. Check the known causes in order

Most reports end at one of these. Check them in this order, because the early ones are
both common and cheap to confirm; symptoms, checks and fixes for each, plus less common
causes, are in `references/known-causes.md`.

1. **Viewport height.** `100vh` on iOS is the height with the toolbars retracted, so
   content at the bottom hides behind them. Use `100dvh` (or `svh` for the smallest
   viewport) with `100vh` declared first as the fallback, and pad fixed bars with
   `env(safe-area-inset-bottom)` under `viewport-fit=cover`. A bar that jumps when the
   keyboard opens is the visual viewport shrinking; the `visualViewport` API reports it.
2. **Input zoom.** iOS Safari zooms the page when an input with a font size below 16px
   gains focus. Set inputs to at least 16px. Disabling zoom in the viewport meta tag
   also removes pinch zoom where browsers honour it, which is an accessibility failure.
3. **Sticky and clipping.** `position: sticky` stops working when an ancestor has
   `overflow` other than `visible`. That rule holds in every engine, so check whether a
   Safari-only style, often a workaround for another iOS bug, added the overflow;
   Safari before version 13 also needed `-webkit-sticky`. Rounded corners with `overflow: hidden` that fail to clip a
   transformed or animated child are a WebKit-specific difference; `isolation: isolate`
   on the clipping element is the usual fix.
4. **Dates.** Parse with an explicit ISO 8601 form (`2026-10-21T10:00:00Z`) or a library;
   `new Date('2026-10-21 10:00')` with a space has historically been `Invalid Date` in
   Safari. Date and time inputs render native pickers whose display format differs from
   the `value`, which is always `yyyy-mm-dd`.
5. **ITP storage caps.** After seven days of Safari use without the user interacting with
   the site, its script-writable storage is deleted: local storage, IndexedDB, service
   worker registrations and their caches. Cookies written with `document.cookie` are
   separately capped at a seven-day lifetime. A session kept in JavaScript-set storage therefore
   logs iOS users out after a week. Keep the session in a server-set `HttpOnly` cookie
   from your own domain.
6. **IndexedDB eviction.** Data can be evicted under storage pressure or by the cap
   above. Treat IndexedDB as a cache that can disappear, call
   `navigator.storage.persist()` where offline data matters, and check what it returns.
7. **A missing API.** The feature does not exist in the user's version. Check the
   version-by-version compatibility data, not the latest Safari.

### 4. Fix with feature detection, not the user agent

Gate the fix on the capability: `@supports (height: 100dvh)` in CSS,
`CSS.supports('height', '100dvh')` or `'visualViewport' in window` in script, with the
fallback first. A user-agent check is wrong on iPads that request the desktop site,
wrong on other iOS browsers, and wrong the day Safari fixes the behaviour, at which point
the workaround starts breaking a browser that no longer needs it.

### 5. Prove the fix where it failed, then keep it fixed

Confirm on the same device or simulator and version that reproduced it, then on the
oldest iOS version the product supports. Add a test to the WebKit project of the browser
suite when Playwright's WebKit reproduces the bug; when only iOS does, add the case to
the manual device checklist with the version noted. If it is a genuine engine bug,
reduce it to a minimal page and report it at bugs.webkit.org, and link the report from
the workaround so it can be removed later.

## Output format

1. **Environment** — device, OS version, display mode, and how it was reproduced.
2. **Cause** — which known cause, or the reduced test case, with the evidence.
3. **Fix** — the change, the feature query that gates it, and the fallback.
4. **Proof** — versions verified, and the test or checklist entry added.
5. **Upstream** — a WebKit bug link if one was filed, and the condition for removing the
   workaround.

## Anti-patterns

**Reasoning from Chrome DevTools device mode.** It emulates the screen size and user
agent of an iPhone with the Chromium engine; it cannot reproduce a WebKit bug.

**User-agent sniffing.** It misses iPads and other iOS browsers, and outlives the bug.

**`maximum-scale=1` to stop input zoom.** It fixes the symptom by disabling zoom, in every
browser that honours it, for the people who need it; set the input's font size instead.

**Treating Playwright WebKit as Safari on iPhone.** A green WebKit run says nothing about
the keyboard, toolbars or ITP.

**Session state in local storage.** It works everywhere in testing and logs out any iOS
user who goes seven days of Safari use without visiting.
