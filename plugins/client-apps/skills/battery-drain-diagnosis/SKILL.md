---
name: battery-drain-diagnosis
description: "Find what drains the battery and heats the phone in a native iOS or Android app, and prove the fix. Split foreground from background drain first, trace a scripted scenario on a physical device with batterystats, the Android Studio Power Profiler, Xcode's energy gauge and MetricKit, and check suspects in order: wake locks and background work, location accuracy and frequency, polling instead of batched or pushed network calls, and animations, timers and sensors left running. Re-run the identical scenario to show the delta. Use when someone says \"we are top of the battery settings list\", \"the phone gets hot in our app\" or \"it drains overnight in the background\". Not for slow launch or janky scrolling (mobile-startup-and-jank), a push that did not arrive (push-notification-delivery), background kills and hangs (anr-watchdog-triage), or one slow function (profiling)."
allowed-tools: Read, Grep, Glob, Edit
---

# Battery Drain Diagnosis

Done means the drain is split into foreground and background, the largest consumer is
named from a trace taken on a physical device, the fix is shown as a before-and-after on
the identical scripted scenario repeated several times, and the field metric is watched
per version.

Battery work goes wrong because the obvious instrument is the worst one. The percentage
is coarse, non-linear and moves with temperature, signal strength and battery age, so a
"we saved 3 percent" from one run each way is noise. The settings screen attributes
energy to whatever was in the foreground, so a navigation app gets blamed for the screen
it keeps on. And the energy is rarely spent where developers look: the radios, GPS and
screen dominate, while CPU time in the app's own code is usually a smaller line. An
emulator or simulator has no meaningful battery model at all, so none of this can be
measured there.

## Scope

Use for: an app high in the system's battery list; complaints of drain or heat;
background drain overnight; reviewing location, background work and network patterns for
energy before a release; proving an energy fix.

Do not use for: slow launch or dropped frames, which are `mobile-startup-and-jank`; a push
notification that did not arrive or arrived late, which is `push-notification-delivery`
— though polling added to work around unreliable pushes is a drain source and belongs
here; an app killed in the background or for heat (`0xc00010ff`), which is
`anr-watchdog-triage` for the kill itself; a slow function once it is the confirmed
consumer, which is `profiling`; requests that hang or retry forever on a bad network,
which is `lie-fi-resilience`.

## Hard gates

1. Foreground and background drain are separated before any trace is read.
2. Measurements come from a physical device, unplugged or with charging simulated off,
   with brightness, network and starting state fixed.
3. The suspects in step 4 are checked in order, each with evidence for or against.
4. A fix is claimed only from the same scripted scenario run before and after, at least
   three times each, reported as energy or active time per component rather than battery
   percentage alone.

## Workflow

### 1. Split foreground from background

- **Android:** the system battery usage screen shows per-app foreground and background
  use; Play's Android vitals report wake-lock and wakeup behaviour per version.
- **iOS:** Settings, Battery shows per-app time on screen and in the background; Xcode
  Organizer's energy reports and MetricKit's daily payloads (CPU, location, network,
  display and GPU metrics, plus CPU exception diagnostics) show the field picture per
  version.

Background drain is usually a defect — something running when nobody is looking.
Foreground drain is often a design cost — screen, GPU, location while navigating — and
the question becomes whether it is proportionate.

*Gate:* the complaint is restated as foreground or background, which versions, which
OS versions, and which feature users were using.

### 2. Script the scenario

Write the scenario as steps with durations — "open the map, follow a route for 20
minutes, lock the phone for 60 minutes" — and fix everything else: device model and OS,
brightness, network (Wi-Fi or a known cellular signal), Bluetooth, other apps closed,
battery in the same range at the start. Background scenarios need the device idle long
enough for the OS to enter its low-power states, or Doze and app standby never apply.

### 3. Trace on a device

- **Android:** reset the stats with `adb shell dumpsys batterystats --reset`, mark the
  device as unplugged with `adb shell dumpsys battery unplug`, run the scenario, then read
  `adb shell dumpsys batterystats com.example.app` or load an `adb bugreport` into Battery
  Historian. Android Studio's Power Profiler shows per-rail power on devices with on-device
  power monitors, such as recent Pixels. Restore with `adb shell dumpsys battery reset`.
- **iOS:** Xcode's Energy Impact gauge while running on a device, Instruments with Time
  Profiler, Network and the energy-related templates your Xcode version offers, and
  on-device energy logging from the Developer settings for scenarios away from the Mac.

`references/energy-tools.md` has the commands, the Doze and standby test commands, what
each tool attributes and how to read it. Read it before the first trace.

*Gate:* a trace of the scripted scenario showing which component — CPU, cellular or Wi-Fi
radio, GPS, screen, GPU, wake locks — carries the energy.

### 4. Check the suspects in this order

The order is by how often each is the cause in practice and how cheap it is to rule out.

1. **Wake locks and background work.** Partial wake locks held too long or never
   released, periodic jobs scheduled too often, foreground services left running, alarms
   that wake the device; on iOS, background modes declared but not needed, an audio
   session left active, background tasks not ended, frequent silent pushes.
2. **Location.** Highest accuracy where city-level would do, short update intervals,
   updates continuing in the background or after the feature closed. Continuous tracking
   where a geofence, significant-change monitoring or batched updates would answer the
   same question.
3. **Network pattern.** Polling on a timer, analytics flushed per event, retries in a
   tight loop while offline. The cellular radio stays in a high-power state for seconds
   after each transfer, so ten small requests a minute apart cost far more than one batch.
4. **Animations, timers and sensors left running.** Animations on screens that are hidden
   or covered, display-link callbacks never stopped, repeating timers, sensor listeners,
   Bluetooth scans and camera sessions not torn down, the screen held awake.
5. **CPU in your own code.** Only after the above are ruled out; then hand the hot path
   to `profiling`.

`references/drain-suspects.md` gives, for each suspect, the evidence that confirms it, the
APIs involved on each platform, and the usual fix. Read it while working through the list.

*Gate:* each suspect is marked confirmed, ruled out (with the evidence) or not
applicable.

### 5. Fix, then prove the delta

Fix the confirmed suspect only, re-run the same scenario on the same device the same
number of times, and report the component's energy or active time before and after with
the spread: wake-lock time, GPS-on time, radio-active time, mWh from the Power Profiler,
MetricKit's cumulative CPU or location time. Battery percentage can be reported alongside,
never alone.

Respond to heat as well as to drain: `ProcessInfo.thermalState` on iOS and
`PowerManager.getCurrentThermalStatus()` on Android 10 and later let the app reduce frame
rate, quality or background work when the device is already hot.

### 6. Watch the field per version

Compare the new version's figures in vitals, Organizer or MetricKit with the previous
version's at the same days since release.

## Anti-patterns

**Measuring battery percentage once each way.** The percentage moves with temperature,
signal and battery age; one run each way proves whatever the author hoped.

**Profiling CPU first.** A CPU profile cannot see the GPS, the radio or a wake lock held
while idle, which is where most drain lives.

**Polling to work around unreliable pushes.** It turns a delivery problem into a battery
problem. Fix delivery with `push-notification-delivery`; keep a slow, batched fallback at
most.

**Requesting the strongest background capability "to be safe".** Continuous background
location or an always-on foreground service costs energy every minute it is held, and
both platforms' reviews and users ask why.

**Testing in the simulator or emulator.** No radios, no GPS hardware, no real power model:
any number from it is invented.

## Output format

```markdown
## Complaint
[Foreground or background; versions, OS versions, feature in use.]

## Scenario
[Scripted steps and durations; device, OS, brightness, network, start state.]

## Trace finding
[Component carrying the energy, from which tool.]

## Suspects
| Suspect | Status | Evidence |

## Fix
[What changed, and why it removes the confirmed cause.]

## Delta
| Metric | Before (median, spread, N) | After (median, spread, N) |

## Field
[Version comparison once released.]
```

## Reference files

- `references/energy-tools.md` — read before the first trace at step 3: batterystats,
  Battery Historian, the Power Profiler, Doze and standby test commands, Xcode's energy
  gauge, Organizer energy reports and MetricKit, and what each attributes.
- `references/drain-suspects.md` — read at step 4 while working the list: the evidence,
  platform APIs and usual fix for each suspect.
