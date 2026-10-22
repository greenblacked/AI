# Drain suspects

For each suspect in step 4's order: the evidence that confirms it, the APIs involved and
the usual fix. Read this while working through the list.

## Contents

- [Wake locks and background work](#wake-locks-and-background-work)
- [Location](#location)
- [Network pattern](#network-pattern)
- [Animations, timers and sensors](#animations-timers-and-sensors)
- [CPU in your own code](#cpu-in-your-own-code)

## Wake locks and background work

**Confirms it:** long partial wake-lock time in batterystats or Battery Historian;
frequent alarms or jobs; a foreground service notification that stays up after the task;
on iOS, background time in Settings, Battery with no feature that should need it.

| Platform | Look at | Usual fix |
| --- | --- | --- |
| Android | `PowerManager.WakeLock` acquisitions, including those inside SDKs | Acquire with a timeout and release in `finally`; prefer WorkManager, which manages wake locks for you |
| Android | WorkManager periodic work and its interval (15 minutes is the minimum) | Lengthen the interval; add constraints such as unmetered network or charging for work that can wait |
| Android | Exact alarms (`setExactAndAllowWhileIdle`) | Inexact alarms or WorkManager unless the user asked for that exact time |
| Android | Foreground services | Stop the service as soon as the user-visible task ends |
| iOS | `UIBackgroundModes` in `Info.plist` | Remove every mode the app does not truly use |
| iOS | `beginBackgroundTask` calls | End every task, including on the failure path |
| iOS | `AVAudioSession` left active with silence | Deactivate when playback stops |
| iOS | `BGTaskScheduler` requests and silent push frequency | Schedule processing work with `requiresExternalPower` where it can wait; send silent pushes only when there is new data |

## Location

**Confirms it:** GPS time in batterystats or the Power Profiler's GPS rail; location
activity time at the highest accuracy in MetricKit; the location indicator showing while
the feature is not in use.

| Platform | Look at | Usual fix |
| --- | --- | --- |
| Android | Fused location `Priority` | `PRIORITY_BALANCED_POWER_ACCURACY` or lower unless turn-by-turn accuracy is needed |
| Android | Update interval, minimum update interval | As long as the feature tolerates |
| Android | `setMaxUpdateDelayMillis` | Batch updates so the app wakes once for several fixes |
| Android | Removal of updates | Remove updates when the screen or feature closes; use geofences for "tell me when I arrive" |
| iOS | `desiredAccuracy` | `kCLLocationAccuracyHundredMeters` or coarser unless navigation needs best accuracy |
| iOS | `distanceFilter`, `pausesLocationUpdatesAutomatically` | Set a distance filter; allow automatic pausing with the right activity type |
| iOS | `allowsBackgroundLocationUpdates` | True only while a user-started background session runs |
| iOS | Continuous updates for coarse needs | Significant-change monitoring, region monitoring or visit monitoring instead |

## Network pattern

**Confirms it:** radio-active time far larger than bytes transferred would need; many
small requests spread over time in the Network instrument or Battery Historian; requests
continuing while the app is in the background with nothing new to fetch.

- Replace polling with push where the server knows when data changes; where polling must
  stay, lengthen the interval and stop it in the background.
- Batch analytics and logs and send them with other traffic, not per event.
- Defer non-urgent transfers: WorkManager with network constraints on Android;
  a background `URLSession` configuration with `isDiscretionary` set on iOS, which lets
  the system pick a good moment.
- Cap retries with backoff; an offline app retrying every second keeps the radio awake.
  Retry design itself belongs to `lie-fi-resilience`.
- Use HTTP caching (`ETag`, `Cache-Control`) so unchanged data costs a small response, or
  none.

## Animations, timers and sensors

**Confirms it:** CPU or GPU activity while the app's screen is covered or the app is in
the background; display-link or choreographer callbacks continuing in a trace after
navigation; sensor or Bluetooth time in batterystats.

- Stop animations, Lottie or animated images when their view is hidden, not only when it
  is destroyed; a screen kept in a back stack or behind a modal still animates otherwise.
- Invalidate `CADisplayLink` and repeating `Timer`s on iOS, and remove `Choreographer`
  callbacks and repeating `Handler` posts on Android, when the screen goes away.
- Unregister sensor listeners, stop Bluetooth scans with a timeout, and stop camera
  sessions in the matching lifecycle callback.
- Release keep-screen-on flags (`FLAG_KEEP_SCREEN_ON`, `isIdleTimerDisabled`) as soon as
  the reason for them ends.
- Prefer lower frame rates for decorative animation; on high-refresh displays, a
  decorative loop at 120 Hz costs more than one at 30 Hz with no visible gain.

## CPU in your own code

**Confirms it:** sustained CPU time in the app's own stacks during the scenario, with the
suspects above ruled out.

Find the hot path with a CPU profile on the device, then treat it as a performance
problem with `profiling`. Common energy-specific causes: reprocessing unchanged data on
every wake, decoding the same images repeatedly, and JSON parsing of large responses
fetched more often than they change.
