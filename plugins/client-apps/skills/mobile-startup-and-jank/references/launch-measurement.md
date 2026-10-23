# Launch measurement

Benchmark setup, quick commands and how to read launch phases on both platforms. Read
this before the first measurement at step 2.

## Contents

- [Android: Macrobenchmark](#android-macrobenchmark)
- [Android: quick checks](#android-quick-checks)
- [Android: compilation state](#android-compilation-state)
- [Android: reading the trace](#android-reading-the-trace)
- [iOS: XCTest and Instruments](#ios-xctest-and-instruments)
- [iOS: reading the phases](#ios-reading-the-phases)
- [Field data](#field-data)

## Android: Macrobenchmark

The benchmark lives in its own module and drives a release-like build of the app: a
build type that is minified, not debuggable, and marked `profileable` so the benchmark
can trace it.

```kotlin
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule val rule = MacrobenchmarkRule()

    @Test fun coldStartup() = rule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
        compilationMode = CompilationMode.Partial(),
    ) {
        pressHome()
        startActivityAndWait()
    }
}
```

It reports `timeToInitialDisplayMs` (and `timeToFullDisplayMs` when the app calls
`reportFullyDrawn()`) as minimum, median and maximum, and keeps a Perfetto trace per
iteration. For scrolling, add `FrameTimingMetric` to a test whose block flings the list
with UI Automator.

## Android: quick checks

```bash
adb shell am start -W -S -n com.example.app/.MainActivity   # force-stop, launch, wait; prints LaunchState and TotalTime
adb logcat -d -s ActivityTaskManager | grep Displayed       # the same figure; -d dumps and exits, without it logcat never ends
adb shell dumpsys gfxinfo com.example.app reset              # clear frame stats before a manual scroll
adb shell dumpsys gfxinfo com.example.app                    # janky frames and frame-time percentiles since reset
```

Run each quick check several times; a single launch is noise.

## Android: compilation state

How much of the app is ahead-of-time compiled changes startup more than most code
changes. A build installed from Android Studio or `adb install` starts with no profile
applied; a Play install gets cloud profiles over time. Control it explicitly:

```bash
adb shell cmd package compile --reset com.example.app             # back to the post-install state
adb shell cmd package compile -m speed-profile -f com.example.app # compile what the profile names
```

Macrobenchmark's `CompilationMode` does this per run: `None()` is the worst case,
`Partial()` applies the Baseline Profile, `Full()` compiles everything. Report which one
a number came from.

## Android: reading the trace

Open a Perfetto trace from the benchmark output in the Perfetto UI or Android Studio and
read the main thread from process start:

| Slice | What it is |
| --- | --- |
| `bindApplication` | Process attach: content providers, then `Application.onCreate` |
| `activityStart`, `activityResume` | The first activity's lifecycle |
| `inflate` | Layout inflation; large if the first screen's XML is deep |
| `Choreographer#doFrame` | A frame; the first one after resume is the first draw |
| `OpenDexFilesFromOat`, `VerifyClass` | Loading and verifying code; large when code is not compiled ahead of time |
| Your `trace("...")` sections | Your own initialisers, named |

Gaps on the main thread with work on another thread usually mean the main thread is
waiting for that thread.

## iOS: XCTest and Instruments

```swift
func testLaunchPerformance() {
    measure(metrics: [XCTApplicationLaunchMetric()]) {
        XCUIApplication().launch()
    }
}
```

Run it on a device in the Release configuration, and set a baseline in Xcode so a
regression fails the test. `XCTApplicationLaunchMetric(waitUntilResponsive: true)`
measures until the app responds to input rather than to the first frame.

The Instruments App Launch template records the launch with its phases. From the command
line, `xcrun xctrace record` with `--template 'App Launch'` records the same trace; check
`xcrun xctrace help record` for the launch and device arguments of the installed Xcode.

The first launch after an install or a reboot is slower than later ones. Record it
separately rather than mixing it into the median.

## iOS: reading the phases

| Phase | What happens | What makes it slow |
| --- | --- | --- |
| Process creation and pre-main | dyld loads dynamic libraries and runs static initialisers and `+load` methods | Many dynamic frameworks; Objective-C `+load`; C++ static constructors |
| `UIApplicationMain` to `didFinishLaunchingWithOptions` returning | App delegate set-up | SDK initialisation, synchronous disk or keychain reads, database set-up |
| Scene connection and first view controller | Window, root view, first layout | Heavy first screen, synchronous data loads in `viewDidLoad` |
| First frame | First commit to the screen | Large images decoded on the main thread, complex layout |

## Field data

| Platform | Source | What it gives |
| --- | --- | --- |
| Android | Play Console Android vitals | Cold, warm and hot start against the excessive thresholds, per version and device |
| Android | `ApplicationStartInfo` (Android 15 and later) | Per-launch timestamps and start type, reported by the app itself |
| iOS | Xcode Organizer | Launch time per version and device class |
| iOS | MetricKit `MXAppLaunchMetric` | Histograms of time to first draw, resume time and extended launch |
