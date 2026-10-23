---
name: mobile-startup-and-jank
description: "Make a native app open fast and scroll smoothly. Measure cold start on a low-end physical device in a release build with Macrobenchmark, Android vitals, XCTest launch metrics, MetricKit and Instruments; split launch into pre-main or process start, app initialisation and first frame; list every SDK initialised on the launch path with its milliseconds and defer each one; judge scrolling by p95 frame time and hitch rate, not average frames per second; ship a Baseline Profile on Android. Use when someone says \"the app takes 6 seconds to open\", \"the list scrolls badly on low-end Android\", \"startup got slower this release\" or \"should we add a splash screen\". Not for one slow function once located (profiling), a game's frame budget (game-performance), an app killed or reported as hung (anr-watchdog-triage), or download size (app-size-budget)."
allowed-tools: Read, Grep, Glob, Edit
---

# Mobile Startup and Jank

Done means cold start and scrolling are stated as numbers from a release build on a named
low-end device, launch is split into phases with every launch-path initialiser listed in
milliseconds, each change is re-measured on the same device, and a benchmark in CI stops
the time creeping back.

Startup rarely gets slow in one commit. It accretes: each SDK, feature flag client and
analytics wrapper adds "only 40 ms" to `Application.onCreate` or
`didFinishLaunching`, and nobody owns the sum. It is then measured in the conditions that
hide it — a debug build (on Android, a debuggable build without R8 or ahead-of-time
compiled code runs slower than release in ways that move where the time appears to go),
on the developer's flagship phone, with a warm process mistaken for a cold one.
Scrolling has its own blind spot: an average of 58 frames per second hides the half-second
stall every time a new row type appears, and the stall is what users notice.

## Scope

Use for: slow app launch; launch time that regressed; janky lists, transitions and
animations in a native iOS or Android app, including Compose, SwiftUI, Flutter and React
Native screens; deciding what to take off the launch path; setting up startup and frame
benchmarks.

Do not use for: a single function already known to be slow, which is `profiling`; a game
missing its frame budget, which is `game-performance`; a launch that the iOS watchdog
kills, an Android ANR, or a reported hang, which are `anr-watchdog-triage`; the size of
the download, which is `app-size-budget`; battery and heat, which are
`battery-drain-diagnosis`.

## Hard gates

1. Every number comes from a release-configuration build — optimised, minified,
   non-debuggable — on a physical device representative of the low end of the user base.
2. Cold start is measured as cold: the process killed first, at least ten iterations,
   median and spread reported.
3. Launch is split into phases before anything is changed.
4. Every initialiser on the launch path is listed with its milliseconds and a decision.
5. Frames are judged by tail frame time or hitch ratio, never by average frames per
   second.

## Workflow

### 1. Name the start type, the endpoint and the target

Cold start creates the process; warm start recreates the activity or scene in a live
process; hot start brings a backgrounded app forward. Android vitals treat a cold start
of 5 seconds or more, a warm start of 2 seconds or more and a hot start of 1.5 seconds or
more as excessive. Pick the endpoint as well: time to first frame (Android's time to
initial display) or time until the screen is usable. On Android, call
`reportFullyDrawn()` when real content is shown so time to full display is measured; on
iOS, MetricKit can extend its launch measurement over post-first-frame work with
`extendLaunchMeasurement(forTaskID:)`.

*Gate:* the target is written as start type, endpoint, device and number.

### 2. Measure on the right device and build

- **Android:** a Jetpack Macrobenchmark with `StartupTimingMetric` and
  `StartupMode.COLD` reports time to initial and full display per iteration and saves a
  Perfetto trace for each. For a quick check,
  `adb shell am start -W -S -n com.example.app/.MainActivity` force-stops the app,
  launches it and prints `TotalTime`; logcat's `Displayed` line gives the same figure.
- **iOS:** `XCTApplicationLaunchMetric` in an XCTest `measure` block for repeatable runs;
  the Instruments App Launch template to see where the time goes; Xcode Organizer and
  MetricKit's launch histograms for the field.
- **Device:** pick it from the field data — the model at the bottom of your Android
  vitals or analytics device distribution, the oldest iPhone you support — not the
  phone on your desk.

`references/launch-measurement.md` has the benchmark setup, the commands, how compilation
state changes Android numbers, and how to read the phase breakdown on both platforms.
Read it before the first measurement.

*Gate:* a baseline of at least ten cold starts, median and spread, with build
configuration and device named.

### 3. Split launch into phases

- **Android:** process creation and `bindApplication`; every `ContentProvider.onCreate`
  (these run before `Application.onCreate`, and many SDKs auto-initialise through one);
  `Application.onCreate`; the first activity's `onCreate` to `onResume`; first frame;
  fully drawn. Add `trace("name") { }` sections from `androidx.tracing` around your own
  initialisers so they show in the Perfetto trace.
- **iOS:** pre-main (loading dynamic libraries, static initialisers, Objective-C `+load`
  methods); `didFinishLaunchingWithOptions`; scene connection; first frame. Add
  `OSSignposter` intervals around your own work so it shows in Instruments.

*Gate:* each phase has a duration from the median run, and the largest phase is named.

### 4. Inventory the launch path and defer everything not needed for the first frame

List every SDK and component initialised before the first frame:

| Initialiser | Phase | Median ms | Needed for first frame? | Decision |
| --- | --- | --- | --- | --- |
| Analytics SDK | ContentProvider | 85 | No | Remove auto-init provider; start after first frame |
| Remote config fetch | Application | 140 | No — cached values are enough | Use cached values; fetch in background |
| Database open and migration check | Activity | 60 | Yes | Keep, on a background thread with the first screen showing cached state |

Each "no" leaves the launch path: lazy initialisation on first use, a background thread,
or a task scheduled after the first frame. On Android, the App Startup library
(`androidx.startup`) can replace per-SDK providers, and a provider can be removed with
`tools:node="remove"` in the manifest. On iOS, cut pre-main by reducing the number of
dynamic frameworks (link statically, or use mergeable libraries from Xcode 15) and by
removing `+load` methods and static initialisers.

*Gate:* every initialiser above a few milliseconds has a decision, and the sum deferred is
stated.

### 5. Ship a Baseline Profile on Android

Without one, code runs interpreted or JIT-compiled until the runtime's background
compilation catches up, so first launches after install or update are slowest. Generate
a profile with the Baseline Profile Gradle plugin and a `BaselineProfileRule` journey
covering startup and the main scroll paths, include `androidx.profileinstaller` so it
applies outside Play installs, and confirm the gain with Macrobenchmark: compare
`CompilationMode.None()` with `CompilationMode.Partial()`.

### 6. Measure frames by the tail

The budget is 16.7 ms per frame at 60 Hz, 11.1 ms at 90 Hz and 8.3 ms at 120 Hz.

- **Android:** Macrobenchmark's `FrameTimingMetric` gives frame duration and overrun at
  p50, p90, p95 and p99; `adb shell dumpsys gfxinfo <package>` prints janky-frame counts
  and percentiles for a manual run (`reset` first); JankStats reports jank from the field.
  Vitals count frames over 16 ms as slow and over 700 ms as frozen.
- **iOS:** hitch time ratio — milliseconds of hitch per second of scrolling. Apple's
  guidance treats under 5 ms/s as good, 5 to 10 as worth investigating and over 10 as
  critical. The Instruments Animation Hitches template finds them locally; MetricKit's
  scroll hitch time ratio reports them from the field.

`references/jank-causes.md` maps the common causes — main-thread work in cell or item
binding, image decoding, layout depth, recomposition, offscreen rendering, allocation
churn — to how each shows in a trace and the fix. Read it once a trace is open.

*Gate:* frames reported as p95 frame time or hitch ratio for a scripted scroll, before and
after.

### 7. Re-measure one change at a time, then guard it

Change one thing, re-run the same benchmark on the same device, and keep it only if the
median moves by more than the run-to-run spread. Then put the startup and scroll
benchmarks in CI on a fixed physical device or device farm, and watch the field figures
per version in vitals, Organizer or MetricKit.

## Anti-patterns

**Measuring a debug build.** On Android especially, a debuggable build changes the
runtime's behaviour enough that the profile points at the wrong code.

**A longer splash screen.** It moves the wait, it does not remove it. The Android 12
SplashScreen API's keep-on-screen condition should end as soon as the first content can
draw.

**Moving initialisation to a background thread that the first screen then waits on.** The
launch path now includes a thread hop and a wait. Make the first screen not need it.

**Average frames per second.** A 99 percent smooth list with a 400 ms stall on every new
row type averages beautifully and feels broken.

**Tuning on a flagship.** A phone three times faster than the user base's median hides
every problem this skill exists to find.

## Output format

```markdown
## Target
[Start type, endpoint, device, number; scroll scenario and frame target.]

## Baseline
[Median and spread over N cold starts; p95 frame time or hitch ratio; build configuration
and device.]

## Launch phases
| Phase | Median ms |

## Launch-path inventory
| Initialiser | Phase | Median ms | Needed for first frame? | Decision |

## Changes and results
| Change | Cold start median before / after | Frame metric before / after |

## Guard
[Benchmarks added to CI, device used, field metric watched per version.]
```

## Reference files

- `references/launch-measurement.md` — read before the first measurement at step 2:
  Macrobenchmark and XCTest setup, the `adb` and Instruments commands, compilation state on
  Android, and reading the launch phases on both platforms.
- `references/jank-causes.md` — read at step 6 with a trace open: the common causes of
  dropped frames, how each looks in Perfetto or Instruments, and the fix.
