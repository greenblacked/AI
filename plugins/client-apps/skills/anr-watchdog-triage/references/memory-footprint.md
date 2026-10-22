# Memory footprint

How to record what an app's memory looks like over the scenario that got it killed, and
what usually makes up the peak. Read this at steps 2 and 4 for memory kills.

## Contents

- [What the OS counts](#what-the-os-counts)
- [Recording a timeline on iOS](#recording-a-timeline-on-ios)
- [Recording a timeline on Android](#recording-a-timeline-on-android)
- [What makes up a peak](#what-makes-up-a-peak)
- [Testing the response to pressure](#testing-the-response-to-pressure)

## What the OS counts

- **iOS** kills by footprint: dirty and compressed memory belonging to the process.
  Clean memory that can be reloaded from disk is not counted. Limits differ by device and
  are higher in the foreground than for an app extension or a backgrounded app.
- **Android** kills background processes first, in order of importance, when free memory
  runs low; a foreground app can still be killed on a low-RAM device or exhaust its Java
  heap and crash with `OutOfMemoryError`. `dumpsys meminfo` reports PSS split into Java
  heap, native heap, graphics, code and stack.

A footprint is a curve, not a number. Record it over the whole scenario, with markers at
each screen transition, so the peak can be tied to what the user was doing.

## Recording a timeline on iOS

- Xcode's debug navigator memory gauge shows footprint live; use it for a first look on a
  device, not the simulator.
- Instruments with the Allocations and VM Tracker instruments records the curve and what
  grew; add `os_signpost` markers at screen transitions to line the curve up with the
  user's path.
- Log `os_proc_available_memory()` at suspected peaks in a test build: it reports the
  headroom left before the limit.
- The Memory Graph debugger exports a `.memgraph` that `vmmap --summary` and `leaks` can
  read on a Mac, for retained objects and reference cycles.
- MetricKit's memory metric reports peak memory per day from the field, per version.

## Recording a timeline on Android

- `adb shell dumpsys meminfo <package>` at each step of the scenario, on a low-RAM device.
- Android Studio's Memory Profiler records the curve and can capture a heap dump at the
  peak; `adb shell am dumpheap <pid> <path on device>` takes one from the command line.
- LeakCanary in debug builds reports retained objects such as destroyed activities, which
  raise the baseline the peak sits on.
- `ApplicationExitInfo` with `REASON_LOW_MEMORY`, logged on the next launch, gives the field
  count per version where the device supports reporting it.

## What makes up a peak

| Source | Why it is large | Fix |
| --- | --- | --- |
| Decoded images | Width times height times four bytes: 48 MB for 4000 by 3000, whatever the file size | Decode at display size: ImageIO thumbnails with a maximum pixel size on iOS; Coil, Glide or `inSampleSize` on Android |
| Unbounded caches | Grow with use and never shrink | Bound by bytes, not entry count, and clear on pressure |
| Retained screens | A navigation stack keeping every previous screen's views and images | Release offscreen resources; check for leaks of destroyed screens |
| Whole-document parsing | A large JSON or XML response held as a tree, plus its string | Stream or page it |
| WebViews and media players | Large native allocations per instance | Reuse one; release when hidden |

## Testing the response to pressure

- iOS Simulator's Debug menu has Simulate Memory Warning; check that caches clear and the
  footprint falls.
- `adb shell am send-trim-memory <package> RUNNING_LOW` sends a trim level to a running
  process; check that `onTrimMemory` releases caches.
- Turn on the "Don't keep activities" developer option and walk the app, and kill the
  backgrounded process with `adb shell am kill <package>`, then return to it: state must
  restore. A background kill is expected behaviour; losing the user's work after one is
  the defect.
