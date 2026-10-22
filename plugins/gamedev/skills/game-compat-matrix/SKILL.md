---
name: game-compat-matrix
description: "Choose the hardware and driver combinations a game must be tested on, from the installed base rather than from what the studio owns, and triage bugs that occur only on some GPUs or devices. Ranks GPU families, drivers, OS versions and RAM tiers by share and crash rate, selects a covering set small enough to run on every release candidate, runs a fixed smoke script per cell, isolates variables to separate driver bugs from content bugs, and publishes a supported and known-issue list re-derived each quarter. Use whenever someone says \"works on my machine but crashes on AMD\", \"which Android phones should we test\", \"black screen on Intel integrated\", \"driver bug or our bug\" or \"minimum spec\". Not for frame budget (game-performance), platform submission (game-certification), one device class such as handhelds (handheld-pc-readiness), or end-to-end web testing (e2e-testing)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Game Compatibility Matrix

The work is done when the test devices were chosen from evidence about the installed base, each release candidate has one result per cell of a fixed smoke script, every failing cell has been classified as driver-following or content-following, and the supported and known-issue lists are published and dated.

The usual failure is testing on whatever the team owns: a few recent NVIDIA desktops. The crash reports then come from a graphics vendor, a driver era or a phone tier nobody on the team has ever run.

## Scope

Use for: picking test hardware; defining minimum spec; bugs that occur on some GPUs, drivers or devices only; deciding whether a bug is the game's or the driver's.

Do not use for: the frame-time budget, which is `game-performance`; console and store submission requirements, which are `game-certification`; the handheld PC class specifically, which is `handheld-pc-readiness`; browser end-to-end tests, which are `e2e-testing`.

## Workflow

### 1. Pull the installed base

Rank by share and by pain. For PC, start from the Steam Hardware and Software Survey, and replace it with the game's own telemetry as soon as there is any (GPU, driver version, OS, RAM, display). For mobile, use the store's device statistics: the Google Play Console reports installs and crash rates by device model, and Android vitals shows which devices crash most. For each GPU family, driver, OS version and RAM tier, record two numbers: share of players, and crash or support rate per player. Pain matters as much as share: a 2 percent family that crashes ten times as often as a 10 percent family outranks it (share times crash rate is the ranking). `references/matrix-and-triage.md` has the table layouts.

### 2. Select a covering set

Choose the smallest set that covers the distinct failure risks, not a sample of the market:

- the minimum-spec device, at the lowest supported settings;
- the most popular device;
- one device per GPU vendor and per recent generation;
- one device with the oldest supported driver;
- any chipset with a history of rendering bugs, from your own tracker or the engine's known-issues list.

Keep the set to a size the team will actually run on every release candidate. A matrix too large to run is skipped, and then it covers nothing. Where owning every device is not possible, name a rental or device farm and the budget, and mark the cell as sampled rather than every build.

### 3. Run one fixed smoke script per cell

The same steps on every device so results compare: boot, reach the menu, load the first level, play three minutes, change resolution and each graphics option once, alt-tab or suspend and resume, quit and relaunch. Record one result per cell per candidate: pass, fail with a link to the capture, or not run with the reason. Attach the build id, driver version and OS build to each result, because a result without them cannot be reproduced.

### 4. Triage a failing cell by isolating variables

Change one thing at a time and keep the notes:

1. Same build on another driver version (one older, one newer) on the same hardware.
2. Switch the graphics API (for example from one backend to another) if the game supports it.
3. Disable one feature at a time: the post-process stack, a shadow technique, compute effects, a texture format.
4. Capture a frame with a graphics debugger (RenderDoc, or the vendor's tool) and compare it with a working device.

Read the result: if the bug follows the driver version, it is a driver bug; ship a workaround (disable the feature on that driver range, or use a different path) and send the vendor a report with a minimal repro, not the full game. If the bug follows the content or a feature on every driver, it is yours. If it follows the hardware regardless of driver, it may be a limit such as memory or a missing capability; check the capability query before assuming.

### 5. Publish and re-derive

Publish the supported and known-issue list from the matrix, with the date, so support can answer "does it run on X". Every quarter, re-derive the installed-base table from telemetry and the survey, and move devices in and out of the matrix. Retire a cell only when its share and crash rate justify it, and write down why.

### 6. Report

```markdown
## Installed base
[Source, date, top families by share and by crash rate.]

## Matrix
[Cells, why each is there, owned or rented.]

## Results
[Per cell for this candidate: pass, fail, not run.]

## Triage
[Failing cells, variables isolated, classification, workaround or vendor report.]

## Published lists
[Supported, known issues, next re-derivation date.]
```

## Anti-patterns

**Choosing by what is on the desk.** The matrix is the player base, not the office.

**Testing every combination.** An unrunnable matrix is a skipped one.

**Calling it a driver bug without a second driver.** Without evidence from another version, it is an assumption.

**Reporting to the vendor with the whole game.** A vendor can act on a minimal repro and will not on a build.

## References

- `references/matrix-and-triage.md` — read at steps 1, 2 and 4: the installed-base and matrix tables, and the isolation log.
