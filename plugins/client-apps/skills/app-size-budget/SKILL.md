---
name: app-size-budget
description: "Cut a native app's download and install size and keep it cut. Start from the size the store reports per device, not the IPA or AAB on disk; decompose it with an App Thinning size report or bundletool and a link map; cut in a fixed order — duplicate and unused assets, extra architectures, image formats, on-demand resources or dynamic feature modules, dead code with R8 and dead stripping, then SDKs — measuring each cut; and gate the size delta on every pull request so it cannot creep back. Use when someone says the app is 300MB, size is hurting installs, the APK grew 40MB in one release, or wants a size check in CI. Not for a game's textures, audio and asset pipeline (game-assets), the store rollout (mobile-release), slow launch or dropped frames (mobile-startup-and-jank), or CPU hot spots (profiling)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# App Size Budget

Done means the team knows the store-reported download and install size for its most
common devices, has a breakdown attributing that size to components, has made the cuts in
order with the bytes each one saved, and has a CI check that shows every pull request's
size delta and fails past an agreed threshold.

The usual failure is optimising the wrong number. The `.ipa` or `.aab` on the build
machine is not what anyone downloads: the App Store thins the app per device and encrypts
the executable, which compresses worse than it did on your disk, and Google Play generates
split APKs per device from the bundle. A team that shrinks the artefact can see no change
in what users download, or miss that one device class pulls three times the median. The
second failure is a one-off diet: size is cut for a release and grows back within two,
because nothing measures it per change.

## Scope

Use for: an app whose download or install size is too large; a size jump between
releases; deciding what to move to on-demand delivery; R8, dead stripping and resource
shrinking; measuring what each SDK costs; a per-PR size gate.

Do not use for: a game's texture compression, audio formats and asset import pipeline,
which is `game-assets`; the staged rollout of the smaller build, which is `mobile-release`;
launch time and frame drops, which is `mobile-startup-and-jank` (a smaller binary can help
launch, but measure launch there); CPU hot paths, which is `profiling`.

## Workflow

### 1. Read the number users actually get

- **iOS:** App Store Connect shows each build's App Store file sizes — download and install
  size per device variant. Use the most common device variants from analytics, and the
  largest.
- **Android:** Play Console reports download and on-device size for the bundle per device
  configuration, in its app bundle explorer. Note the spread between the smallest and the
  largest configuration.

Record download and install size separately: download size drives install conversion on
cellular and slow networks; install size decides whether the app fits on a nearly full
phone and how soon it is offloaded or uninstalled when space runs out.

*Gate:* a table of device variant × download size × install size for the current release,
from the store, before any cut.

### 2. Decompose it

Attribute the bytes to components — the executable, each framework or native library,
asset catalogues, resources, fonts, media, ML models, localisations.

- **iOS:** export the archive with app thinning for all variants to get an App Thinning
  size report per variant; generate a link map (`LD_GENERATE_MAP_FILE = YES`) to attribute
  executable size to modules and SDKs. The thinning report is an estimate; App Store
  Connect's figure is the reference.
- **Android:** `bundletool get-size total` over the APK set gives download size by
  dimension or for one device spec; `apkanalyzer` breaks an APK into files, resources and
  dex packages.

`references/measurement-commands.md` has the exact commands, the export options and how
to read each report. `xcodebuild` runs the project's build scripts, and `bundletool` and
`unzip` write files and sign or install packages, so those run with the user's approval;
`apkanalyzer`, which reads an APK, asks for approval too.

*Gate:* the largest ten components with their bytes, summing to most of the store figure.
If they do not sum, the decomposition is wrong — usually a component measured
uncompressed against a compressed total.

### 3. Cut in order, measuring each step

Work down this order. It runs from no behaviour change to product decisions, so the cheap
wins land before anything needs a meeting. Rebuild and re-measure after each cut and record
the bytes saved; a cut that saves nothing is reverted.

| Order | Cut | Where the bytes usually are |
| --- | --- | --- |
| 1 | Duplicate and unused assets | The same image, font or animation shipped by two modules or pods; assets for removed features; unused resources — Android's `shrinkResources` and lint's unused-resource check find many |
| 2 | Architectures | Android: native libraries for ABIs the device does not need, when shipping APKs outside the bundle; unstripped `.so` files. iOS: prebuilt frameworks carrying extra slices, checked with `lipo -info` |
| 3 | Image formats | PNG where WebP or vector would do on Android; iOS images outside asset catalogues, which app thinning cannot slice per scale; oversized source images scaled down at runtime |
| 4 | On-demand delivery | Content most users never open: onboarding video, rarely used features, high-resolution packs. Android Play Feature Delivery and Play Asset Delivery; on iOS, On-Demand Resources or Background Assets — check which Apple currently recommends for new work |
| 5 | Dead code | Android: `isMinifyEnabled` with R8, with keep rules reviewed rather than blanket. iOS: dead code stripping on, `-Osize` where profiling shows no regression, symbols in the dSYM rather than the binary |
| 6 | SDKs | Measure each by building with and without it. An analytics, ads or UI SDK can cost more than the app's own code; the decision to drop or replace it belongs to the product owner, with the number |

Code shrinking and on-demand delivery change behaviour: R8 can remove code reached only by
reflection, and an on-demand module is absent until downloaded. Each needs the release
regression tests and a test of the not-yet-downloaded path before it ships.

`references/cut-checklist.md` has the per-platform checklist under each of the six
headings.

### 4. Gate the delta on every pull request

Build the release configuration on each pull request and on the main branch, measure the
same number both times, and report the difference by component in the pull request.

- Measure something stable and close to the store number: `bundletool get-size total`
  against a fixed device spec on Android; the App Thinning report's figure for one
  reference device variant on iOS.
- Keep main's measurement as a stored artefact so a pull request compares against its
  merge base, not against a number someone wrote down.
- Fail above an agreed delta, with an explicit override that records who accepted the
  growth and why. A gate with no override gets disabled; a gate with an unrecorded one
  measures nothing.

*Gate:* a deliberately bloated test change (a large unused asset) fails the check.

### 5. Report against the store again

After the release ships, read step 1's table again from the store. The local measurement
predicts; the store figure is the result. Keep the table per release so a jump is visible
the release it happens.

## Anti-patterns

**Measuring the artefact.** The universal IPA or the AAB is not a download. Optimise what
the store serves.

**Cutting SDKs first.** It is the most contentious cut and often not the largest.
Unused assets and image formats usually pay for themselves with no meeting.

**Blanket keep rules.** A `-keep class **` added to silence one R8 crash undoes most of
the shrinking without anyone noticing.

**On-demand content with no failure path.** A feature whose module has not downloaded,
on a phone with no signal, needs a defined state, not a crash.

**A one-off diet.** Without the per-PR gate, the size returns within a few releases, one
reasonable-looking dependency at a time.

## Output

Hand back: the store table before and after; the top components before and after; each
cut with the bytes it saved and its risk; anything moved on-demand and its not-downloaded
behaviour; SDK costs measured; and the CI gate's measure, baseline, threshold and override.

## Reference files

- `references/measurement-commands.md` — read at steps 2 and 4: App Thinning export
  options, link maps, `bundletool` and `apkanalyzer` commands, and how to read each report.
- `references/cut-checklist.md` — read at step 3: the per-platform checklist under each of
  the six cuts, including the build settings and the tests each cut needs.
