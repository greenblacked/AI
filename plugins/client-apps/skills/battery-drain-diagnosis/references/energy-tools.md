# Energy tools

What each platform tool measures, how to run it, and what it cannot see. Read this
before the first trace at step 3.

## Contents

- [Android on the device](#android-on-the-device)
- [Android: testing low-power states](#android-testing-low-power-states)
- [Android in the field](#android-in-the-field)
- [iOS on the device](#ios-on-the-device)
- [iOS in the field](#ios-in-the-field)
- [Which tool answers which question](#which-tool-answers-which-question)

## Android on the device

```bash
adb shell dumpsys batterystats --reset            # start counting from zero
adb shell dumpsys battery unplug                  # report the device as unplugged while connected
# ... run the scripted scenario ...
adb shell dumpsys batterystats com.example.app    # per-app wake locks, jobs, alarms, network, sensors, GPS
adb bugreport bugreport.zip                       # full report for Battery Historian
adb shell dumpsys battery reset                   # restore real charging state
```

- `dumpsys batterystats` estimates energy from a per-device power profile; treat its mAh
  as an estimate and its durations — wake-lock time, GPS time, radio-active time — as
  the stronger evidence.
- Battery Historian, an open-source tool run locally, renders a bug report as a
  timeline: wake locks, jobs, alarms, radio state and screen against time, which is the
  fastest way to see what woke the device and for how long.
- Android Studio's Power Profiler reads on-device power monitors on devices that have
  them, such as recent Pixels, and shows power per rail (CPU, cellular, Wi-Fi, GPS,
  display) alongside the app's activity.
- `adb shell dumpsys power` lists wake locks held right now; `adb shell dumpsys alarm` and
  `adb shell dumpsys jobscheduler` list the app's scheduled alarms and jobs.

## Android: testing low-power states

Background drain that only happens before the device sleeps is invisible in a short test.
Force the states instead of waiting for them:

```bash
adb shell dumpsys battery unplug                              # Doze testing assumes the device reports unplugged
adb shell dumpsys deviceidle force-idle                       # enter Doze now
adb shell dumpsys deviceidle unforce                          # leave it
adb shell dumpsys battery reset                               # restore real charging state
adb shell am set-standby-bucket com.example.app rare          # put the app in a restrictive standby bucket
adb shell am get-standby-bucket com.example.app               # check which bucket it is in
```

Check that work deferred by Doze runs in maintenance windows and that nothing tries to
work around the restriction with exact alarms or a foreground service.

## Android in the field

- Play's Android vitals report wake-lock and wakeup behaviour per version and device;
  check the console for the current metric definitions and thresholds before quoting
  them.
- The system battery usage screen splits foreground and background use per app, which is
  what users see when they complain.

## iOS on the device

- The Energy Impact gauge in Xcode's debug navigator, on a device, shows the app's energy
  level and what contributes to it — CPU, network, location, GPU, background — while the
  scenario runs.
- Instruments: Time Profiler for CPU, the Network instrument for request patterns, and
  the energy-related templates offered by the installed Xcode. A device must be used; the
  simulator has no radios or real power model.
- On-device energy logging, enabled from the Developer section of the device's settings,
  records a session away from the Mac for later import into Instruments.

## iOS in the field

- Xcode Organizer's energy reports show where the app used excessive energy in the
  field, by version.
- MetricKit delivers daily payloads with CPU time, location activity time by accuracy,
  network transfer, cellular conditions, display and GPU metrics, plus diagnostics for
  CPU exceptions; log them per version to compare releases.
- Settings, Battery shows time on screen and in the background per app over the last
  day or ten days.

## Which tool answers which question

| Question | Android | iOS |
| --- | --- | --- |
| Is it foreground or background? | Battery usage screen; batterystats | Settings, Battery; MetricKit |
| What woke the device? | Battery Historian timeline; `dumpsys alarm` and `jobscheduler` | Instruments over a background session; energy log |
| Which component carries the energy? | Power Profiler rails; batterystats durations | Energy Impact gauge breakdown |
| Did the fix work in the field? | Vitals by version | Organizer and MetricKit by version |
