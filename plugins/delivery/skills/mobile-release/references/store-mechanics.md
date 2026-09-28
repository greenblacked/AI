# Store rollout mechanics

Read this at step 2, when deciding what the schedule actually lets you control on each
platform.

## Contents

- [Apple: phased release](#apple-phased-release)
- [Android: staged rollout](#android-staged-rollout)
- [Why the difference matters](#why-the-difference-matters)

## Apple: phased release

App Store Connect's phased release for an app update runs a fixed seven-day schedule that
Apple sets, not the publisher:

| Day | Percentage of users with automatic updates |
| --- | --- |
| 1 | 1% |
| 2 | 2% |
| 3 | 5% |
| 4 | 10% |
| 5 | 20% |
| 6 | 50% |
| 7 | 100% |

That percentage governs automatic-update delivery only. A user who opens the App Store
and taps Update — or installs for the first time — gets the new version immediately,
regardless of what day of the phased schedule it is.

Two controls exist on top of the fixed schedule, and only two: pause it, for up to 30
days in total and any number of times, which holds the rollout at its current percentage
rather than advancing further; or choose Release to All Users at any point, which jumps
straight to 100% immediately. Neither control lets the schedule be slowed to a custom
curve or advanced to an arbitrary intermediate percentage — pause and hold, or release to
everyone, are the only two moves available.

Source: Apple's own App Store Connect help documentation for releasing an app update in
phases.

## Android: staged rollout

Google Play's console offers its own staged-rollout controls for a release. This file
does not restate what those controls are, because their exact mechanics — which
percentages are offered, whether the publisher chooses them or the platform fixes them,
and what can be changed once a stage is live — are the kind of detail a console changes
over time and a document like this one goes stale against silently.

Check the Play Console's staged-rollout screen for the release in question before writing
the schedule into a release plan. Read what it actually offers today rather than what a
previous release used, and record what you found in the plan's Schedule section along
with the date you checked it.

## Why the difference matters

Treating both stores as one mechanism is the mistake this file exists to prevent. Apple's
schedule is fixed, with only pause-and-hold or release-to-everyone as levers; whatever
Android's console currently offers may or may not share that property. A release plan
that assumes symmetry between the two platforms is a plan that has not actually read
either console.
