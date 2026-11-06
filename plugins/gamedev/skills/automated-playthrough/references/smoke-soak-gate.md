# Smoke and soak gate before QA hand-off

Read this at step 5 of `SKILL.md`, when a build is about to be handed to QA or a certification pass. The point of the gate is that a tester never spends a morning on a build that cannot boot, cannot load its own save or leaks itself to death in two hours. Those are cheap for a machine to find and expensive for a person.

The gate runs on the release candidate, in a release configuration, on the fixed machine or device the nightly soak uses. A build that fails it is not handed over; the hand-off note names the failing step and links the report.

## Smoke steps

Run these in order from a clean profile, through the player input path as `bot-design.md` describes. Each step is a checkpoint for the progress watchdog, and each fails the gate on a crash, an exception, a hang past its limit or a missing expected state.

1. **Cold boot.** Start the process with no cached shaders, no save and no settings file, and reach the title screen. Record the time to title as a number; the budget belongs to `game-load-times`.
2. **Load a save.** Use a save made by the previous shipped build, kept in the repository as a fixture, not one the current build wrote. Reach the playable state and check one fact from the save (a level name, an inventory count) so a silent fallback to a new game fails. The format and migration rules are `game-save-system`.
3. **Save.** Trigger a save through the menu, then check the file exists, is non-empty and loads again in step 4. Do not stop at "no error was logged".
4. **Quit to title, then load that save again.** This is the step that exposes state left over from the first load: static caches, event subscriptions, a scene that does not unload.
5. **Controller disconnect and reconnect.** While playing, remove the controller device (the engine's virtual device removal, or the platform's own test hook), then add it back. Pass when the game pauses or prompts as designed, input resumes on reconnect and nothing throws. Action names and prompts are `game-input-mapping`.
6. **Suspend and resume**, where the platform has it (handhelds, consoles, laptops with sleep, mobile backgrounding). Suspend mid-play, resume after a fixed delay, and check the game state, the audio and the network session are intact. A platform with no suspend gets this step marked "not applicable" in the report, never silently omitted.
7. **Quit to desktop or home.** Exit cleanly and check the exit code and that no process is left behind.

Keep the smoke under ten minutes so it can run on every release candidate. Anything longer belongs in the soak.

## The two-hour soak

The soak repeats a short gameplay loop (load a level, play the route, unload, return to title) for two hours of wall-clock time on one process, with a fixed seed per run and the fixed timestep. Two hours is long enough for a per-loop leak of a few megabytes to show as a trend; shorten it only with a stated reason, and run several seeds across nights rather than one seed for longer.

### Sample resident memory

Sample the process, not the engine's own counter, so native leaks are visible too. On a fixed interval (60 seconds is a reasonable start; check that it is shorter than one loop), read the resident set of the game process and append a line with elapsed time, loop count and the value.

- Linux: `VmRSS` in `/proc/<pid>/status`.
- Windows: the process working set, and private bytes beside it.
- Consoles and phones: the vendor's profiler or device tooling; confirm which counter it reports before comparing across platforms.

Take the same sample on the same schedule on every run. A sampler that fires at level boundaries only will hide the growth within a level.

### Fail on slope, not on a single peak

A resident set that rises during a load and settles is normal. A set that keeps climbing across loops is a leak. So fit a straight line to the samples, discard the first 15 minutes as warm-up (caches fill, pools grow to their working size), and fail the build when the slope exceeds a threshold.

```python
def slope_mb_per_hour(samples, warmup_s=900):
    """samples: list of (elapsed_seconds, resident_mb). Least-squares slope."""
    pts = [(t, m) for t, m in samples if t >= warmup_s]
    n = len(pts)
    if n < 10:
        raise ValueError("too few samples after warm-up to fit a slope")
    mt = sum(t for t, _ in pts) / n
    mm = sum(m for _, m in pts) / n
    num = sum((t - mt) * (m - mm) for t, m in pts)
    den = sum((t - mt) ** 2 for t, _ in pts)
    return num / den * 3600
```

Choose the threshold from a known-good build: run the soak on it three times, take the worst slope, and set the limit at a small multiple of that (twice is a reasonable start), written down with the build id it came from. Fail when the limit is exceeded, and also fail when the run ends with too few samples, since a crashed sampler would otherwise read as flat.

Check a second condition alongside the slope: the final resident value against the platform ceiling less the OS reserve. The per-system budget table, the ceiling and the leak analysis that follow a failure are `game-memory-budget`; this gate only runs the loop, takes the samples and applies the slope limit.

### What the failing report carries

The standard failure report from `bot-design.md`, plus the full sample file, a plot of resident memory against elapsed time with the fitted line, the loop count at failure, and the seed. Without the series, the next person cannot tell a steady leak from a step at one level.

## Hand-off

Pass requires all of: every applicable smoke step green, the soak completed its full duration, the slope under its limit, and no crash dump or hang. The hand-off note to QA gives the build id, the seeds used, the slope measured against its limit, the steps marked not applicable and why, and the known failures with owners. Do not re-run a failed gate until it goes green without saying so; a pass on the second attempt is reported as an intermittent failure with its first report attached.
