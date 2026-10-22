# Cut checklist

The per-platform checklist under each of the six cuts, in the order the skill makes them,
with the test each one needs before it ships. Record the bytes saved per item; a cut that
saves nothing is reverted.

## Contents

- 1\. Duplicate and unused assets
- 2\. Architectures
- 3\. Image formats
- 4\. On-demand delivery
- 5\. Dead code
- 6\. SDKs

## 1. Duplicate and unused assets

- Hash every file in the built bundle or APK and list identical hashes: the same image,
  font, animation or model shipped by two modules or two pods is common.
- Assets for removed features, old onboarding, A/B variants that finished.
- Fonts: unused weights and full character sets where a subset would do.
- Localised images where text overlays would do.
- Android: enable resource shrinking with code shrinking; run lint's unused-resources
  check; mind resources looked up by name at runtime (`getIdentifier`), which the shrinker
  can only keep if it sees the name.
- Test: the screens that used each removed asset, and a search of the code for dynamic
  lookups of anything removed.

## 2. Architectures

- Android bundles already deliver only the device's ABI. Where APKs are distributed
  outside Play, build per-ABI APKs or set `abiFilters`, and drop x86 variants only if you
  do not support devices or emulators that need them.
- Check that native libraries are stripped of debug symbols in release; upload symbols
  separately for crash reporting.
- iOS: the store delivers one architecture per device. Run `lipo -info` on embedded
  frameworks; extra slices are usually rejected at upload, but a vendored framework can
  still carry unused content worth checking.
- Test: install and launch on each supported ABI or device class.

## 3. Image formats

- Android: convert PNG and JPEG to WebP (Android Studio can do it per file or folder);
  vector drawables for icons; ship the densities you need rather than every bucket.
- iOS: put images in asset catalogues so app thinning delivers one scale per device;
  images loose in the bundle ship every scale to every device. Use vector assets or SF
  Symbols for icons, and a compressed format for photographs.
- Downscale source images to the largest size actually displayed.
- Test: a visual pass or screenshot tests over the changed screens on low- and
  high-density devices.

## 4. On-demand delivery

- Candidates: content most users never open — onboarding video, rarely used features,
  high-resolution packs, large ML models, region-specific content.
- Android: Play Feature Delivery for code and features (install-time, conditional or
  on-demand modules) and Play Asset Delivery for large assets (install-time, fast-follow,
  on-demand packs).
- iOS: On-Demand Resources or Background Assets for downloaded content. Check which
  Apple currently recommends for new work before building on either.
- Every on-demand item needs a defined state while it downloads, when it fails, and when
  the device is offline.
- Test: the feature on a fresh install with no network, with a slow network, and after
  the download completes.

## 5. Dead code

- Android, release build type:

  ```kotlin
  release {
      isMinifyEnabled = true
      isShrinkResources = true
      proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
  }
  ```

  Review keep rules: `-printconfiguration` writes the merged configuration including rules
  that libraries contribute, which is where blanket keeps hide; `-whyareyoukeeping` explains
  why a class survived; `-printusage` lists what was removed.
- iOS: `DEAD_CODE_STRIPPING = YES`; `SWIFT_OPTIMIZATION_LEVEL = -Osize` where profiling
  shows no meaningful regression; `DEBUG_INFORMATION_FORMAT = dwarf-with-dsym` with
  stripping on for the app target so symbols live in the dSYM; prefer static linking where
  it lets the linker strip across module boundaries.
- Test: the full regression suite against the minified or stripped release build — not
  debug — and crash monitoring on an internal track before production. R8 removes code
  reached only by reflection, serialisation or JNI unless kept.

## 6. SDKs

- Measure each SDK by building with it compiled out and comparing; include its transitive
  dependencies, which are often larger than the SDK.
- Look for two SDKs doing one job (two analytics, two image loaders, two networking
  stacks) and for SDKs initialised but unused.
- Present each with its bytes, what it does for the product, and the alternatives; the
  decision to remove or replace belongs to its owner.
- Test: whatever the SDK provided — attribution, crash reporting, payments — verified end
  to end after the change.
