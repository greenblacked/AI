# Deferred links and the test matrix

## Contents

- Deferred-link carriers compared
- Migrating off Firebase Dynamic Links
- The test matrix
- What to measure

## Deferred-link carriers compared

A deferred link carries a destination across an app install. The carrier is what survives
the trip through the store.

| Carrier | Platform | Deterministic | Notes |
| --- | --- | --- | --- |
| Play Install Referrer API | Android | Yes | Put an opaque token in the Play Store URL's `referrer` parameter; read it on first launch; resolve it server-side to the destination |
| Server-side resume after sign-in | Both | Yes | The web page stores the pending destination against the account or an emailed magic link; the app asks the server after login |
| Explicit paste or code entry | iOS mostly | Yes | The web page copies a code; the app offers to paste it. Reading the pasteboard shows a system prompt, so make it a user action |
| Attribution provider SDK | Both | Varies | Use only if already integrated for other reasons; check what it does under platform privacy rules |
| Matching on IP, user agent and time | Both | No | Breaks behind carrier NAT and shared wifi, and conflicts with platform rules against fingerprinting |

Keep the token opaque and short-lived, resolve it on the server, and apply the same
validation as any other link parameter: a deferred link is still untrusted input.

## Migrating off Firebase Dynamic Links

1. Find every place links are minted: share sheets, emails, marketing tools, QR codes,
   server templates.
2. Mint plain `https://` links on your own domain instead, matching the shared route
   table.
3. Make each of those URLs serve a real web page.
4. Add the association files for that domain (see the association-files reference) and
   ship the app with the entitlement and intent filters.
5. Replace the deferred part with one of the deterministic carriers above.
6. Old links already in the wild resolve nowhere now; if they had a recognisable path on a
   custom domain you still control, redirect them on the web side to the new URLs.

## The test matrix

Run every route in the table through each row. Use a clean install for the "fresh" rows,
because association is fetched at install.

| Entry | Auth state | Install state | Expected |
| --- | --- | --- | --- |
| Tap in Messages or Notes (iOS), chat app (Android) | Signed in | Installed, cold | Destination screen |
| Same | Signed in | Installed, warm (app in background) | Destination screen, not just the app brought forward |
| Same | Signed out | Installed | Sign-in, then the destination |
| Same | Any | Not installed | Web page with real content; after install and first launch, destination via the carrier |
| Same | Any | Installed, older version without the route | Web page or a "update to see this" screen, never blank |
| From a push tap | Signed in | Installed, cold | Destination screen |
| Malformed parameter (wrong type, overlong, unexpected host in a URL parameter) | Any | Installed | Safe fallback screen, no action taken |
| Typed into Safari's address bar (iOS) | Any | Installed | Opens in Safari; this is expected and not a bug |

Automate what can be automated: `adb shell am start -W -a android.intent.action.VIEW -d
<url>` and `xcrun simctl openurl booted <url>` in UI tests cover the cold, warm and
malformed rows. Keep a manual pass on a real device for the tap-in-another-app rows,
since that is the path the OS treats differently.

## What to measure

- Share of link opens that reach the app versus the web fallback, per platform and host.
  A sudden drop on one platform after a web deploy is an association file broken by that
  deploy.
- Share of opens that reach the destination screen versus home. A gap here is a routing
  bug, usually the cold-start path.
- Deferred-link resolution rate on first launch, per carrier.
