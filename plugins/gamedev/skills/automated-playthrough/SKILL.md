---
name: automated-playthrough
description: "Build a bot or scripted run that plays the game unattended in CI to find crashes, soft-locks and leaks. Starts with the smallest bot on the riskiest path, drives the game through the player input path rather than internal functions, records a seed with every run so failures replay, writes final state, last 500 log lines, screenshot and build id on failure, judges runs by machine-checkable criteria with a progress watchdog, and runs smoke per commit and soak nightly. Use whenever someone says \"we need a smoke test for the game\", \"soak test overnight\", \"QA can't reproduce the soft lock\", \"bot that plays through the level\" or \"automated gameplay test\". Not for web UI journeys (e2e-testing), human sessions (game-playtest), designing test cases (test-design), or the memory budget a soak checks (game-memory-budget)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Automated Playthrough

The work is done when a bot plays the game unattended on a fixed machine on every commit, a longer soak runs nightly, each failure arrives as a report that can be replayed from its seed, and a failing bot has an owner the same day.

The usual failure is a bot that tests a different game. A script that calls internal functions to start a level, teleport the player and flip the win flag passes while the real input path, the menu flow and the load screen are broken. The second failure is ambition: a bot meant to play the whole game, which breaks on every UI change, is switched off within a month, and leaves the team with nothing. Start small, drive the game as a player does, and add reach only when it pays.

## Scope

Use for: a smoke test that the game boots and reaches a state; a soak over many loads or hours; reproducing a soft-lock QA cannot; a bot that completes a level; automated checks for crashes, hangs, leaks and hitches.

Do not use for: end-to-end journeys through a web interface, which is `e2e-testing`. Sessions with human players that find confusion and fun are `game-playtest`. Designing unit and integration test cases for code is `test-design`. The memory budget and leak analysis that a soak feeds are `game-memory-budget`; this skill produces the run that records the numbers.

## Workflow

### 1. Choose the property to check

Pick the smallest property that covers the riskiest path, and build only that:

1. The game boots and reaches the main menu.
2. It completes the first level, from menu to the end state.
3. It survives N load and unload loops without crashing or growing.
4. It visits every level, or every room, or every item.

Each step is more work and more maintenance than the one before. Most teams get the most value from 1 and 3, because boot and load crashes are common, cheap to detect and the first thing a release breaks. Write the property as a sentence: "from a clean profile, reach the end of level one within ten minutes with no exception." That sentence is the test.

### 2. Drive the game as a player does

The bot must use the input path a player uses: synthetic input events injected where the platform delivers input, or the engine's recorded-input replay. Do not call internal functions to load a level or set state, because then the menu, the input mapping and the transition code are untested and they are where much of the breakage is.

Bind the bot to stable action names, not screen coordinates: "confirm", "move_forward", "open_inventory", or a stable identifier on a UI element. A button that moves by ten pixels must not break the test. Keep the bot's script in a small set of named behaviours (navigate menu, walk to marker, fight until clear) so a change to one screen means changing one behaviour.

Per engine, the injection points are:

- **Godot**: build input events and send them with `Input.parse_input_event`, or trigger named actions with `Input.action_press` and `Input.action_release`. Run headless with `godot --headless` and bound the run with `--quit-after`.
- **Unity**: the Input System package has test support for queuing device state, and the Unity Test Framework runs play mode tests from the command line with `-batchmode -runTests -testPlatform PlayMode -testResults <file>`. Note that `-nographics` removes rendering, so a run that needs screenshots or shader paths must not use it.
- **Unreal**: the automation system runs tests from the command line with `-ExecCmds="Automation RunTests <filter>; Quit"`, and Gauntlet orchestrates multi-process or device runs. Rendering-dependent checks need a real or virtual display.

See `references/bot-design.md` for the layered design, the failure report and the watchdog.

### 3. Make every run replayable

Randomness is what makes a failure unrepeatable. Seed every source: the engine's random number generator, the bot's own choices, and anything the level generates. Fix the timestep where the engine allows it (`Time.captureFramerate` in Unity, `--fixed-fps` in Godot) so frame timing does not vary with machine load. Print the seed at the start of every run and put it in the report, so the same seed reproduces the same inputs.

On failure, write a report that stands alone: the final game state, the last 500 lines of the log, a screenshot if rendering is available, the build identifier and the seed. A report that needs the tester to be there is a note, not a bug. Attach it to the failed CI job and, where the tracker allows, to an issue created automatically.

### 4. Define pass and fail by machine

Each run ends in a verdict a program computes:

- The end state was reached within a time limit.
- No exception, assertion or crash dump was produced.
- Memory at each checkpoint was within its budget.
- No frame exceeded a hitch threshold (set from the frame budget; `game-performance` explains how to choose it).

A hang is the case people forget. Add a watchdog on progress, not on elapsed time alone: if no new checkpoint is reached in N minutes, kill the run, take the screenshot and the state, and fail it as a soft-lock. A level that takes six minutes normally should have a checkpoint every minute or so, so the watchdog fires after a few minutes without one.

### 5. Schedule it by cost

- **Every commit or pull request**: the cheap smoke, one to ten minutes, on a fixed machine so the timing is comparable.
- **Nightly**: the full soak, with load loops, the long route and the memory checkpoints. Several seeds, so each night covers different ground.
- **Before release**: the soak on the release candidate on each target platform, on real devices where the failures are device-specific.

Fixed hardware matters. A shared runner whose speed varies makes timing thresholds flaky, and flaky tests get ignored.

### 6. Treat a bot failure as a failing test

A red bot run has an owner the same day, like any failing test. Reproduce it by rerunning the recorded seed; if it fails again, bisect to the commit by rerunning that seed over the commits in the range. If it does not fail again, the run was not deterministic, and that is a defect in the bot or the game to fix, not to retry through. Do not add automatic retries that turn a real intermittent soft-lock into a green build.

Track three numbers over time: the pass rate, the share of failures that were bot or environment problems, and the time from failure to owner. A bot that cries wolf is switched off; the second number tells you it is heading there.

### 7. Report

```markdown
## Property
[The sentence the bot checks, and why that path.]

## Bot
[Input path, behaviours, how actions are named.]

## Determinism
[Seeds, timestep, what was verified by rerunning.]

## Verdicts
[Pass criteria, time limit, hitch threshold, watchdog interval.]

## Schedule
[Smoke, soak and release runs; the machines.]

## First results
[Failures found, replayed or not, who owns each.]
```

## Anti-patterns

**Calling internal functions.** The bot then tests a different game from the one players have.

**Clicking by coordinates.** The first UI change breaks every run; use named actions.

**Retrying to green.** It hides the soft-lock that appears one run in ten, which is exactly what the bot is for.

**A bot that tries to play everything first.** It is brittle and abandoned; grow reach one verified path at a time.

**Failing with no report.** A hang killed by the CI timeout with no state is a day of reproduction work.

**Unseeded randomness.** A failure that cannot be replayed cannot be bisected.

## References

- `references/bot-design.md` — read at steps 2 to 4: the layered bot design, the failure report contents, the progress watchdog, and the CI job outline.
