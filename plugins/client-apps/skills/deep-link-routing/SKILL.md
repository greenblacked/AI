---
name: deep-link-routing
description: "Make https links open the right screen in a native app: iOS universal links, Android App Links and deferred links for people without the app. Host apple-app-site-association and assetlinks.json at their exact well-known paths with no redirect and a JSON content type, check team and bundle IDs and the Play signing fingerprint, verify on a clean install with platform tools, drive app, web and both files from one route table, and treat link parameters as untrusted input. Use when a link opens the browser instead of the app, universal links broke after a deploy, App Links fail verification, a shared link lands on the home screen, or someone asks how to replace Firebase Dynamic Links. Not for OAuth redirect URIs and login (auth-design), the API behind the screen (api-design), or a push that never arrived (push-notification-delivery)."
allowed-tools: Read, Grep, Glob
---

# Deep-Link Routing

Done means every route in one shared table opens the matching screen from a cold start, a
warm start, a logged-out state and a fresh install, verified on real platform tooling;
links to routes the installed version does not know degrade to the web page instead of a
blank screen; and nothing a link carries can make the app act without the user.

Deep links fail silently. When association breaks, the OS does not error: it opens the
browser, which looks like a working link to everyone testing on a laptop. The causes are
almost always outside the app code — a CDN that redirects the well-known path, a WAF that
blocks Apple's or Google's fetcher, a certificate fingerprint for the upload key instead
of the Play signing key, an association file cached from before the change — and the
association is fetched at install time, so a developer's phone that installed last month
keeps working while every new install fails.

## Scope

Use for: universal links and App Links that open the browser; verification failures;
links that open the app but land on the wrong screen; cold-start routing; routing for
logged-out users and for people who do not have the app (deferred links); replacing
Firebase Dynamic Links; reviewing link handling for unsafe parameters.

Do not use for: OAuth and SSO redirect URIs and the login flow itself, which is
`auth-design`; the endpoint the destination screen calls, which is `api-design`; a push
notification that did not arrive, which is `push-notification-delivery` (once a push
arrives and its tap opens the wrong screen, that routing is this skill).

## Workflow

### 1. Check the association files from outside

Fetch both files exactly as the platforms do: over HTTPS, at the exact path, without
following redirects.

```bash
set -Eeuo pipefail
d=$(mktemp -d)
for f in apple-app-site-association assetlinks.json; do
  curl -sS -o "$d/$f" -w "$f: %{http_code} %{content_type} redirect=%{redirect_url}\n" \
    "https://example.com/.well-known/$f" || echo "$f: fetch failed"
  jq . "$d/$f" > /dev/null || echo "$f: body is not JSON"
done
```

The commands in this skill that reach the network or a device (`curl`, `adb`, `xcrun`,
`keytool`) are not pre-approved: association files, link parameters and device output
are text other people control, so each run goes through the user's approval. Omitting
`-L` is deliberate, because a redirect is the failure being looked for; the
`redirect=` field is empty only when there was none. Check the status field as well,
since `curl` exits 0 on a `404`.

| Check | Required |
| --- | --- |
| Status | `200`, with no `3xx` on the way — neither verifier follows redirects |
| Path | `/.well-known/apple-app-site-association` (no `.json`), `/.well-known/assetlinks.json` |
| Content type | `application/json` |
| Every host | Apex and `www` and each subdomain are separate associations; check each one the app declares |
| Reachable by the fetchers | Not behind a login wall, geo-block, bot challenge or WAF rule |

Then check what Apple's CDN holds, since iOS devices fetch the file through it rather than
from your server: `curl -sS https://app-site-association.cdn-apple.com/a/v1/example.com`.
If the CDN copy is stale or missing while your server is right, devices are reading the
CDN copy.

*Gate:* every declared host returns `200 application/json` with no redirect, and the CDN
copy matches.

### 2. Check the identities inside the files

- **iOS:** each entry in `applinks.details` names `appIDs` as `TEAMID.bundle.id`, matching
  the signed app's team and bundle; the app's Associated Domains entitlement lists
  `applinks:` for every host. Paths are matched by `components` in order, first match wins,
  so an `exclude` must come before the broader pattern it carves out of.
- **Android:** `package_name` matches, and `sha256_cert_fingerprints` contains the
  fingerprint of the key that signs the installed build. With Play App Signing that is
  Google's app signing key, shown in Play Console, not the upload key in your keystore. Add
  the upload and debug fingerprints too if those builds must verify. Read local keys with
  `keytool -list -v -keystore <file>` or `./gradlew signingReport`.
- **Manifest:** the intent filter that should verify has `android:autoVerify="true"`,
  `ACTION_VIEW`, the `DEFAULT` and `BROWSABLE` categories, scheme `https`, and each host.

`references/association-files.md` has annotated examples of both files and the
manifest filter.

### 3. Verify on a clean install with platform tools

Association is fetched at install or update, so test on a fresh install, not an existing
one.

```bash
adb shell pm verify-app-links --re-verify com.example.app
adb shell pm get-app-links com.example.app          # per-host state, Android 12 and later
adb shell am start -W -a android.intent.action.VIEW \
  -c android.intent.category.BROWSABLE -d "https://example.com/orders/42"
xcrun simctl openurl booted "https://example.com/orders/42"
```

On iOS devices, test by tapping the link in Notes or Messages; typing it into Safari's
address bar never opens the app, and neither does a link to the same domain tapped inside
a page already open in Safari. During development, `applinks:example.com?mode=developer`
plus the device's associated-domains development setting fetches the file directly
instead of through the CDN. On Android 12 and later an unverified link opens in the
browser with no chooser; on Android 11 and lower a failure on any one declared host fails
verification for all of them.

*Gate:* the platform tool reports the domain verified, and the test link opens the app on
a clean install.

### 4. Route from one table

Keep one table of routes — path pattern, screen, parameters with types, whether it needs a
signed-in user, and the web fallback — and generate or test the association `components`,
the Android intent filters and the web router from it. Three lists maintained by hand
drift; the symptom is a link that opens the app to a screen that does not exist, or one
that a new route never claims.

Handle each entry point, since they arrive by different paths:

| Situation | Where it arrives | Common bug |
| --- | --- | --- |
| Cold start, iOS | Scene connection options' user activities, or `onOpenURL` | Only the warm path is handled; cold start lands on home |
| Warm start, iOS | `scene(_:continue:)` or `onOpenURL` | — |
| Cold start, Android | The launch intent in `onCreate` | Intent read before the navigation graph exists |
| Warm start, Android | `onNewIntent` for `singleTop` or `singleTask` activities | Ignored, so the app just comes to the front |
| Logged out | Any of the above | Login succeeds and drops the destination; store it and resume after sign-in |
| Route unknown to this version | Any of the above | Blank screen; open the web page or say an update shows this |

### 5. Handle people without the app

The link must work as a web page first: the same URL serves real content, so a person
without the app, or on a desktop, is never stranded. Then choose how the destination
survives the install:

- **Android:** the Play Install Referrer API returns the `referrer` value from the Play
  Store URL on first launch — a deterministic carrier.
- **iOS:** there is no OS mechanism. Use a deterministic carrier where you can (the user
  signs in and the server resumes their pending destination), an attribution provider if
  you already have one, or a deliberate paste flow; reading the pasteboard on launch
  triggers a system paste prompt. Probabilistic matching on device signals is unreliable
  and runs into platform privacy rules.
- **Firebase Dynamic Links** has been shut down. Any route still minting those links is
  broken; migrate the links to your own domain's universal links and App Links, and the
  deferred part to one of the carriers above.

`references/deferred-and-testing.md` has the deferred-link options compared and the full
test matrix.

### 6. Treat link input as untrusted

A link is input any website, message or app can construct.

- Validate every parameter against the route table's types. Unknown parameters are
  ignored, not passed through.
- No state-changing action — pay, delete, follow, accept an invitation — from a link
  alone. The link opens a screen; the user confirms.
- Never load a URL taken from a parameter into a web view or redirect to it unless its host
  is on an allow-list. A web view with a native bridge loading attacker content is the
  serious version of this bug.
- No tokens or secrets in links. Custom URL schemes can be claimed by any installed app;
  use verified https links for anything that matters.
- On Android, do not forward a received intent's extras into another component; that is
  intent redirection.

## Anti-patterns

**Testing on the phone you developed on.** It cached a good association file weeks ago.
New installs read today's file, through today's CDN and WAF.

**Fixing the file and expecting existing installs to recover at once.** Association is
refreshed on install and update, not on every tap; check the CDN copy and test on a fresh
install.

**The upload key's fingerprint.** With Play App Signing, users run a build signed by a
different key. Verification fails only for store installs.

**Handling only the warm path.** The demo works because the app was already open.

## Output

Hand back: each host's status, content type, redirect and CDN result; the identity checks
(team and bundle IDs, fingerprints, manifest filters); platform verification output from a
clean install; the route table with its entry-point handling; the deferred-link carrier
per platform; the untrusted-input findings; and what was changed.

## Reference files

- `references/association-files.md` — read at step 2: annotated
  `apple-app-site-association` and `assetlinks.json` examples, the manifest intent filter,
  ordering and exclusion rules, and the server and CDN settings that break them.
- `references/deferred-and-testing.md` — read at steps 3 and 5: the deferred-link
  carriers compared and the test matrix of entry point × auth state × install state.
