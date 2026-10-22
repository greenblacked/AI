---
name: game-accessibility-pass
description: "Run a structured accessibility review of a game and fix what blocks players. Works by barrier type (vision, hearing, motor, cognitive, speech) against the Game Accessibility Guidelines tiers, one evidence table per area, cheap high-reach items first: subtitles on by default with size, background and speaker names, no information by colour alone, full remapping, hold actions that can toggle. Includes a photosensitivity gate (flash analyser on captured footage, reduce-flashing setting, warning screen), assists that do not lock achievements, and paid disabled playtesters. Use for \"make the game accessible\", \"colourblind mode\", \"subtitles size and background\", \"one-handed play\", \"photosensitivity warning\", \"hold-to-press is hard\". Not for web or app UI against WCAG (accessibility-audit), remapping mechanics (game-input-mapping), session craft (game-playtest), or difficulty tuning (game-balance)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Game Accessibility Pass

The work is done when each barrier area has an evidence table checked against a real build, the cheap, high-reach items from step 2 are complete, the photosensitivity gate has run on footage and passed, and disabled players have played an early build and their findings are triaged.

The usual failure is a wishlist: someone adds a colourblind filter and a text-size slider, declares the game accessible and ships. Barriers are not features. A player who cannot hold a trigger for two seconds is blocked by a mechanic, and a filter does nothing for them. Audit by what stops a person from playing, then pick fixes.

## Scope

Use for: auditing a game build or design for barriers, choosing and implementing fixes, the flashing-light safety check and the store-page statement of supported features.

Do not use for: accessibility of a website or application interface against WCAG (`accessibility-audit`), the implementation of rebinding, glyphs and menu focus (`game-input-mapping`), how to run a playtest in general (`game-playtest`), or tuning difficulty for the target audience (`game-balance`).

## Workflow

### 1. Audit by barrier, with evidence

Use the Game Accessibility Guidelines (gameaccessibilityguidelines.com), which sort recommendations into basic, intermediate and advanced tiers by cost and impact. Work through five areas in turn: vision, hearing, motor, cognitive and speech. For each, write a table with one row per guideline: requirement, status in this build (met, partly, not met, not applicable), the evidence, and the fix. Evidence is a screenshot, a recording or a settings path, not a belief. Use the template in `references/audit-tables.md`.

Rows marked "not applicable" need a reason (a single-player game has no voice chat to caption), since "not applicable" is where unexamined gaps hide.

### 2. Close the cheap, high-reach items first

Start with these; most sit in the basic tier of the guidelines, and a few (toggling instead of holding, subtitle defaults) come from the intermediate tier or platform guidance, so check each against the guidelines site as well as the running build:

- Subtitles are on by default, with adjustable size, a background or outline, and speaker names or colours that are not the only cue. Include non-speech sounds that matter to play (alerts, off-screen threats) as captions.
- Text is legible at ten-foot distance on a television at the default setting, with a size option. Check at the smallest supported resolution and in handheld mode too.
- No information is carried by colour alone. Pair it with shape, icon, pattern or label, and verify it on a colour-vision simulation of real screenshots (protanopia, deuteranopia, tritanopia), not on the palette in the design file. Team colours, health bars, rarity tiers and map markers are the usual offenders.
- Full remapping of controls, no required rapid repeated presses and no required simultaneous holds, and every hold action can be switched to a toggle.
- Menus and tutorials do not time out while the player is reading.
- Instructions are not delivered only as audio or only as text on screen for a moment.

### 3. Run the photosensitivity gate

Flashing and high-contrast moving patterns can trigger seizures, so this is a safety gate and not an option to polish later. This is a testing procedure, not medical or legal advice: a certified analyser report, together with the platform or regulator's own published text, is the authority.

1. Capture representative footage: every cutscene, every effect that flashes (explosions, lightning, muzzle flash, UI pulses, transitions), and worst-case combat with effects stacked, at the shipping resolution.
2. Run a flash analyser over the footage. Check for more than three flashes in any one second above the luminance and saturated-red thresholds, and for large high-contrast patterns such as stripes, checks or spirals that move or flicker. Cite the threshold values from the current published sources and quote the version you used: the Harding test and the standard it implements (the ITU broadcast recommendation on flashing, and WCAG success criterion 2.3.1, which states the general and red flash thresholds) and Ofcom's guidance. Do not paraphrase them from memory, because the numbers depend on area of screen and viewing conditions.
3. Fix failures at source by lowering contrast, area or rate, not just by warning.
4. Ship a reduce-flashing setting and a reduce-screen-shake setting that really remove the effects, and a warning screen at first launch that points to them.
5. Re-run the analyser on every new effect or cutscene, since this is the regression that returns with each content drop.

### 4. Difficulty, assists and pause

Offer difficulty and assist options that do not lock achievements or trophies away, since punishing a player for needing an assist defeats it. Useful ones: aim assist and slower game speed, extended or skippable timers, auto-complete for repeated inputs, and the ability to skip or reduce a quick-time event. Make pause work everywhere, including cutscenes and during online-offline transitions where the design allows, and make sure it stops timers that matter. Describe each assist in plain language in the menu.

### 5. Test with disabled players, early

Pay disabled players to playtest an early build, covering a range of barriers. Do it early enough that findings can change design; at launch, only settings can change. Compensate them as consultants, prepare a build that runs reliably, and follow `game-playtest` for session craft. Triage findings as blockers (cannot progress), barriers (can progress at high cost) and friction.

Reject a feature list that shipped without anyone testing it. A setting nobody tried has often never worked: a subtitle size that overlaps the HUD, a toggle that resets on load.

### 6. Say what you support

Document supported features on the store page and in the in-game menu, in specific terms ("subtitles with size and background options, full control remapping, toggle for all hold actions"). Do not claim "accessibility support" in general, which tells players nothing and invites distrust. Keep the list synchronised with the build.

## Hand back

The five audit tables with evidence; the list of fixes made and deferred with reasons; the flash analyser tool, version, the thresholds cited with their source, and the footage it ran on; the settings added; the playtest findings and their triage; and the draft store-page wording.

## Anti-patterns

**A colourblind filter as the whole answer.** Filters change hues globally and often make other things worse; pair meaning with shape.

**A warning screen instead of a fix.** The warning is a supplement to reduced flashing, not a licence for it.

**Testing the settings only in the menu.** Check that each setting works in game, persists and does not reset on load.

**Assuming one disabled playtester speaks for everyone.** Barriers vary widely within a category.

## References

- `references/audit-tables.md` - read at step 1: the per-area audit table template, prompts for each area and the simulation and capture workflow.
