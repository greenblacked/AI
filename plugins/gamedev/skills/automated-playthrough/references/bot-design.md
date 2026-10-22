# Bot design

Read this at steps 2 to 4 of `SKILL.md`. It covers how to layer a bot so it survives change, what a failure report contains, how a progress watchdog works, and the shape of the CI job.

## Contents

- [Layers](#layers)
- [Checkpoints](#checkpoints)
- [The failure report](#the-failure-report)
- [The progress watchdog](#the-progress-watchdog)
- [The CI job](#the-ci-job)
- [Choosing the route](#choosing-the-route)

## Layers

Keep three layers apart so a change in one does not break the others.

1. **Input layer.** Sends actions the way a player does: key, button or touch events, or named input actions. It knows nothing about the level. One function per action: press, release, hold for a duration, move a stick to a value.
2. **Behaviour layer.** Named behaviours built on the input layer: `navigate_menu(path)`, `walk_to(marker)`, `fight_until_clear()`, `interact(target)`. Behaviours read game state to decide what to do next (where is the marker, is the enemy alive) through a narrow read-only observer, never write to it.
3. **Scenario layer.** A script that chains behaviours into the property being checked: boot, start new game, play level one, reach the end state. Scenarios are short and read like a test plan.

The observer is the one place the bot touches the game's internals, and it only reads. If the bot needs a marker's position, the level exposes markers by a stable name the observer finds. If the bot needs to write state to proceed, that is a sign the real input path is missing something or the scenario is skipping a step players take.

## Checkpoints

A checkpoint is a named point the run must reach: `menu`, `level1-start`, `level1-boss`, `level1-end`. The game logs each as it is reached, with a timestamp and the memory figure. Checkpoints serve three purposes: they give the watchdog something to watch, they give memory checks fixed sample points (for `game-memory-budget`), and they locate a failure ("died between `level1-boss` and `level1-end`").

Add a checkpoint whenever a run could stall unnoticed between two others. Names are stable identifiers, not display text.

## The failure report

On any failure, write one directory per run, with:

- `verdict.txt`: pass or fail, the reason in a sentence, and the checkpoint last reached.
- `seed.txt`: every seed used, and the timestep setting.
- `build.txt`: build identifier, commit, platform, device or machine name.
- `log-tail.txt`: the last 500 lines of the game log.
- `state.json`: the game state at failure: scene, player position, active quests or flags, the observer's view of the bot's current behaviour and target.
- `screenshot.png`: the final frame, where rendering is available.
- `crash/`: any crash dump or stack trace the platform produced.
- `replay` command: the exact command line that reruns this seed on this build.

The report is the artefact the owner receives. If reproducing a failure needs a question to the person who ran it, the report is incomplete.

## The progress watchdog

A timeout on the whole run catches a hang after the longest time you are willing to wait. A progress watchdog catches it after the longest time a run should go without a new checkpoint.

```python
import time


class Watchdog:
    def __init__(self, stall_seconds):
        self.stall_seconds = stall_seconds
        self.last = time.monotonic()

    def checkpoint(self, name):
        self.last = time.monotonic()

    def stalled(self):
        return time.monotonic() - self.last > self.stall_seconds
```

The runner polls `stalled()` while the game runs, and on a stall captures the screenshot and state, then kills the process and fails the run as a soft-lock with the last checkpoint named. Set `stall_seconds` from the slowest healthy gap between checkpoints plus a margin, and revisit it when levels change.

Separately, bound the total run time, so a game that loops through checkpoints forever also ends.

## The CI job

Outline of a smoke job, independent of the CI product:

1. Check out the commit and build the game for the test platform, or fetch the build the pipeline already made, so the bot tests the artefact that ships.
2. Start the game under the runner with a fresh profile, a fixed seed from the job (the run number is a reasonable source, and it is printed) and the fixed timestep.
3. Run the scenario. Poll the watchdog and the total timeout.
4. Collect the report directory, upload it as the job's artefacts, and set the exit code from the verdict.
5. On failure, assign the failure by the owner rule (the author of the latest commit to the area, or the rotation), and link the report.

For the nightly soak, run several seeds in sequence or in parallel on separate machines, include the load loop and the long route, and compare the memory checkpoints with the budget.

## Choosing the route

- Start with the path every player takes: boot, menu, new game, first level, quit to menu, quit.
- Add the loop that loads and unloads, because load and unload code is the most common source of crashes and leaks.
- Add the route through the riskiest content: the biggest level, the one with the most streaming, the one with the most scripted events.
- Add reach (every level, every room) only after the first routes have been stable for a few weeks.
- Where QA reports a soft-lock they cannot reproduce, write the scenario that approaches the area from several directions with several seeds; a bot gets to the state a human saw once.
