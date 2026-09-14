# Build identity, signing and the store listing

Read this at steps 6 and 7. Everything here fails fast — at upload, or in the first minutes of a review — which makes it the cheapest class of rejection to prevent and the most annoying one to suffer.

## Contents

- [Attempt a real upload early](#attempt-a-real-upload-early)
- [iOS and macOS](#ios-and-macos)
- [Android](#android)
- [Console packages](#console-packages)
- [PC storefronts](#pc-storefronts)
- [What must not be in the shipping build](#what-must-not-be-in-the-shipping-build)
- [Store listing assets](#store-listing-assets)
- [Store listing copy](#store-listing-copy)
- [The pre-submission sweep](#the-pre-submission-sweep)

## Attempt a real upload early

Long before submission, build the release configuration, sign it as it will be signed, and upload it to the platform as a draft or an internal test track. The upload validators reject on identity, entitlements, manifests and package format, and finding all of that on a day when nothing is at stake costs an hour. Finding it on submission day costs a queue slot.

Repeat the upload from CI rather than from one person's machine, so a certificate that lives only in a desk drawer is discovered now.

## iOS and macOS

Verify what you are about to ship rather than what you configured:

```bash
codesign --verify --strict --verbose=2 "MyGame.app"
codesign --display --entitlements - "MyGame.app"
```

- The signing identity and provisioning profile match the bundle identifier, and the profile has not expired inside the submission window.
- Entitlements list exactly the capabilities the build uses. An entitlement present but unused draws questions; one used but absent fails at runtime in review.
- Bundle version and build number increase over anything already uploaded, which is a frequent and trivially avoidable upload rejection.
- Required device capabilities, supported orientations and minimum OS version are what the game actually needs.
- macOS builds are notarised and the ticket stapled, so the app opens on a machine that has never seen it:

```bash
xcrun notarytool submit "MyGame.zip" --keychain-profile "notary" --wait
xcrun stapler staple "MyGame.app"
spctl --assess --type execute --verbose "MyGame.app"
```

Version-sensitive: the notarisation tooling changed once already, and flags move between Xcode releases. Check the current documentation rather than a cached command line.

## Android

```bash
apksigner verify --print-certs --verbose app-release.aab
```

- Signed with the upload key registered for that package name. A rotated or regenerated key that no longer matches is unrecoverable without the platform's key reset process.
- Target API level at or above the store's current floor, which rises on a published schedule; a floor that moves inside your submission window forces a rebuild.
- Version code strictly greater than anything previously uploaded to any track, including abandoned internal builds.
- Every permission in the manifest justified by something in the game. Permissions inherited from an SDK are the usual surprise, and some require a written justification on the store.
- Sensitive permissions and background behaviour declared where the store requires a form for them.

## Console packages

- Title identifier, content identifier and product identifiers match what is registered in the portal, across the build, the package and the store entry.
- The package is produced by the platform's own packaging tool at the required version, from a build against an SDK at or above the current baseline.
- Region and language configuration matches the territories on the store entry.
- Any required platform metadata file — entitlement descriptions, save data definitions, trophy or achievement configuration — is present, complete and localised.
- Where the platform has a submission-time automated check, run it locally first; it is the same validator and it will find the same things.

## PC storefronts

- Package identity or app id matches the reserved entry.
- Code signing where the store requires it, with a certificate that does not expire inside the window.
- Launch options, depots and branch configuration point at the intended content rather than a leftover test depot.
- The installed size and the download configuration match what the store page claims — `game-assets` owns the size itself.

## What must not be in the shipping build

- Debug menus, developer consoles and profiling overlays reachable by a player, including by a key combination someone remembers.
- Verbose logging to disk, which fills storage and leaks internals.
- Test endpoints, staging URLs and hard-coded development credentials. A build pointed at staging passes local QA perfectly, because staging is up.
- Placeholder art, placeholder text and untranslated strings in shipped languages.
- Content cut from the release that is still reachable, and cheat or unlock commands that were not removed.
- Any third-party asset whose licence does not cover this use, and any required attribution that is not present in the build.

## Store listing assets

- Screenshots from the build being submitted, at every size the platform lists, with no debug overlay, no editor chrome and no content not in the game.
- Trailer or capture meeting the platform's length, resolution and content rules, with any required rating card at the head.
- Icons and key art at each required size, including per-platform shapes and any safe-area rules.
- Rating artwork and content descriptors as each territory specifies them.
- Localised assets where the storefront lists a language, including screenshots with text in them.

Capture assets from the submission build rather than reusing last milestone's. A screenshot showing an older UI is a reason for rejection on stores that check, and a reason for refunds on stores that do not.

## Store listing copy

- Title, subtitle and description within each store's length limits, in each supported language.
- No competitor names, no unsupported superlatives, and no reference to other platforms where that is prohibited.
- No feature claimed that is not in the shipping build. A promised feature that is absent is a removal risk later, not just a rejection now.
- Required disclosures present where the store mandates them in the listing: in-app purchases, randomised items, online requirement, accounts required, and any hardware requirement.
- Support and privacy URLs that resolve and mention the game.

## The pre-submission sweep

Run this on the exact package being submitted, not a rebuild of it:

1. Signature and entitlements verified with the commands above.
2. Version and build numbers greater than anything previously uploaded.
3. Configuration pointing at production, confirmed by watching what the build connects to on first launch.
4. Debug surfaces absent, confirmed by attempting to reach them.
5. Store listing assets regenerated from this build.
6. Declarations from `ratings-and-declarations.md` re-checked against this build's SDK set.
7. A fresh install on retail hardware from the actual package, played to the first save.

Record the result per line with the build identifier. When a rejection comes back, that record is what distinguishes a check that was skipped from a check that was wrong.
