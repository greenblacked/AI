---
name: handheld-pc-readiness
description: "Make a PC game work well on Steam Deck and similar handheld PCs, treating Valve's current Deck Verified criteria (input, display, seamlessness, system support) as the spec. Tests on the actual device, not a 1280x800 window, through Proton from a clean install, measures a sustained 30-minute session at the default preset against the performance requirement the current criteria state plus battery draw, covers suspend, resume and network loss, and fixes in the order input, text size, launcher, performance. Use whenever someone says \"will this be Deck Verified\", \"runs on Proton but the text is tiny\", \"handheld PC support\", \"ROG Ally controls\" or \"Deck unplayable with default launcher\". Not for console and store submission (game-certification), frame budget (game-performance), the input action layer itself (game-input-mapping), or web layouts (responsive-design)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Handheld PC Readiness

The work is done when the game has been played on a real handheld from a clean install, each of Valve's four Deck Verified categories has a recorded result against the criteria as currently published, and the failures are fixed in a fixed order and re-checked on a release candidate.

The usual failure is judging readiness in a desktop window sized to 1280x800. That window has a mouse, a keyboard, a fast disk and mains power, so the launcher dialogue that needs a click, the text that is unreadable at arm's length, and the battery that lasts ninety minutes all stay hidden until a player finds them.

## Scope

Use for: Deck Verified preparation; a game that runs on Proton but plays badly on a handheld; controller-only and text-size problems; choosing handheld defaults for other handheld PCs.

Do not use for: console and store submission requirements, which are `game-certification`; frame-budget work as a generic query, which is `game-performance` (this skill only applies a budget to the handheld case); building the action-mapping layer itself, which is `game-input-mapping`; web or app layouts, which are `responsive-design`.

## Workflow

### 1. Read the current criteria first

Open Valve's current Deck Verified documentation at the start of the work, not from memory, and record the page and the date you read it. Treat its four categories as the spec: input, display, seamlessness and system support. The criteria change, so a summary written from last year is a defect. Copy the exact performance and any other numeric requirements into your notes from the page; do not substitute a rule of thumb.

### 2. Get a real device and a clean state

Test on the actual handheld. A desktop window resized to 1280x800 does not reproduce the panel, the controls, the thermals or the storage. Install the game from the store as a player would, with a fresh profile and no prior configuration. For a Windows game, run through Proton from a clean install and wipe the game's compatibility prefix and saved settings between runs, so a first launch is always tested. Other handhelds (for example the ROG Ally) run Windows, so test there natively as well if you claim support.

### 3. Pass each category

- **Input.** Full controller support from first launch to quit, with correct glyphs for the controller in use. No mouse or keyboard needed anywhere, including launchers, EULA and age dialogues, login screens, and anti-cheat prompts. Text entry brings up the on-screen keyboard. Check every menu and every mini-game for a controller path, and for a way to get back out.
- **Display.** Native 1280x800 (or 1280x720 where the current page allows it), or a scaling mode that is exact for it. The default text is readable at handheld distance; check the smallest text in the game (tooltips, subtitles, inventory numbers) on the device, not in a screenshot. No interface element clipped or off-screen.
- **Seamlessness.** First-run and launcher dialogues usable by controller; no crash or hang on suspend and resume; no stale network prompts. The game should be playable without leaving it to fix something.
- **System support.** Runs under Proton or natively with working middleware (video codecs, anti-cheat, DRM). Record anything that needs a workaround and test it from clean.

`references/handheld-checklist.md` has the per-category checklist and the log template.

### 4. Measure a sustained session

Play 30 minutes at the default preset on battery, not a 60-second spot check, because thermal limits and power budgets reduce clocks over time. Record frame rate over the session against the requirement taken from the current criteria (step 1), and battery draw from the device's built-in performance overlay. Choose preset defaults that fit the device: lower the default preset and cap frame rate or resolution scaling before shipping rather than leaving the desktop defaults. Re-measure after each change and keep the numbers in the report.

### 5. Exercise the awkward states

Suspend during play and resume; suspend during a load; put the controller to sleep and wake it; drop the network mid-session and restore it; unplug and plug the charger. Each should return the player to a working game or a clear message, without a restart.

### 6. Fix in order and re-run

Record failures per category, then fix in this order: input first (a game that cannot be controlled has no other problems worth fixing), then text size, then launcher and first-run dialogues, then performance. The order is by who it blocks: input and text size stop play, performance degrades it. After the fixes, re-run the full pass on a release candidate from a clean install, not only the cases that failed.

### 7. Report

```markdown
## Criteria
[Page read, date, the numeric requirements copied from it.]

## Device and state
[Hardware, OS and Proton version, clean-install procedure.]

## Results by category
[Input, display, seamlessness, system support: pass or fail with notes.]

## Sustained session
[Frame rate over 30 minutes against the stated requirement, battery draw, preset chosen.]

## Fix order and re-run
[Failures in order, status, re-run date on the candidate.]
```

## Anti-patterns

**Verifying in a desktop window.** It proves nothing about input, text or thermals.

**Quoting the criteria from memory.** The thresholds move; read the page and date it.

**Short performance checks.** A 60-second test misses the throttling that a 30-minute one shows.

**Leaving the launcher for later.** A launcher that needs a mouse fails the first run, whatever the game does.

## References

- `references/handheld-checklist.md` — read at steps 2 to 5: the per-category checklist, the clean-install procedure and the session log.
