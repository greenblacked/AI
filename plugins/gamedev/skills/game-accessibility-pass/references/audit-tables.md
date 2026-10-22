# Audit tables

## Contents

table template, prompts by area, colour-vision check, flash capture workflow, finding triage

## Table template

One table per area. Keep the evidence column honest: a link to a screenshot or recording, or a settings path and build number.

| Guideline | Tier | Status | Evidence | Fix or reason not applicable |
| --- | --- | --- | --- | --- |
| Subtitles on by default | Basic | Partly | Build 412, first launch screenshot: off | Default on, ship in 0.9 |

Status values: met, partly, not met, not applicable. Never leave a row blank.

## Prompts by area

Vision

- Can every task be completed without distinguishing particular colours?
- Is there a size option for text and is the HUD scalable?
- Is contrast between text and its background sufficient on bright and dark scenes?
- Can a player who cannot see the screen detail rely on audio cues, and is there a screen reader or narration for menus where the platform supports it?

Hearing

- Is every spoken line and every gameplay-relevant sound captioned?
- Is there a visual indicator of direction for off-screen threats?
- Are volume sliders separate for voice, music and effects, so a player can raise one?
- Is any information only in audio?

Motor

- Is every control remappable, including mouse buttons and menu controls?
- Do any actions require rapid repeated presses, holding, or several simultaneous inputs?
- Can holds become toggles, and can the game run with one hand or one switch?
- Are timing windows adjustable, and is there an auto-aim or aim assist option?

Cognitive

- Are objectives, controls and the map available again after the player has left the game for a while?
- Can text and tutorials be re-read, not shown once?
- Are timed puzzles or reading requirements adjustable?
- Is the language plain, and is there an option to reduce on-screen clutter?
- Is there a way to skip content that is repeated or too difficult without punishment?

Speech

- Is voice chat optional, and is there a text or quick-chat equivalent?
- Does any required action depend on speaking or on a voice command?

## Colour-vision check

Take screenshots from real play, including the busiest moments, and run them through a colour-vision simulation (for example the simulators built into some engines and capture tools, or an image-based simulator). View protanopia, deuteranopia and tritanopia. For each screenshot ask whether a player can still tell the two teams apart, read the health state, find the objective and match item rarity. Record failures against the area table.

## Flash capture workflow

1. Record at the shipping resolution and frame rate, uncompressed or lightly compressed, so the analyser sees the true luminance changes.
2. Record each effect in isolation, then the worst combination.
3. Run the analyser and keep its report with the build number.
4. Note the analyser's version and the standard it checks, with a link to the current text.
5. For any failure, record the frames, the effect responsible and the change made, then record again.

## Triage

| Class | Meaning | Action |
| --- | --- | --- |
| Blocker | A player cannot progress or is at risk | Fix before release |
| Barrier | Progress possible at high cost | Fix or provide an option before release where feasible |
| Friction | Annoying, workable | Schedule |

Record the source of every finding, whether a guideline, an analyser or a playtester, so later builds can be re-checked against the same item.
