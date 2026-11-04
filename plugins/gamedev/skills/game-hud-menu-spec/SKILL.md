---
name: game-hud-menu-spec
description: "Write a per-screen spec for a game's HUD and menus, then prove a gamepad can drive every screen. Ranks each piece of information by when the player needs it (always, in a moment of danger, on demand), fixes the safe area, and checks legibility at the smallest supported display and the largest text setting. Then runs a focus-graph check on a node and edge list: every control reachable from the default focus, no focus traps, Back always lands on a defined screen, nothing reachable only by pointer, focus visible at all times. Use whenever someone asks to spec, lay out or review a HUD, pause menu, inventory or settings screen, or says a controller cannot reach a button. Not for key and button bindings or rebinding (game-input-mapping), the accessibility review (game-accessibility-pass), generic usability critique (ui-ux-review), or translated string length (game-localisation)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Game HUD and Menu Spec

Every screen has a written spec, and a gamepad alone can reach, use and leave every control on it, shown on a node and edge list rather than by a tester's impression.

HUDs fail in two quiet ways. The layout is designed on a large monitor with default text, so on the smallest supported display or the largest text setting a number is clipped, overlaps its neighbour or sits under the platform's overscan margin. And menus are built and tested with a mouse, so a control exists that focus can never land on, or a sub-screen has no way back. Neither shows in a screenshot of the happy path. Both are properties of the whole screen set, so they are checked on the set.

## Scope

Use for: specifying a HUD, a pause menu, an inventory, a shop or a settings screen; ranking what the HUD shows and when; setting safe-area and scaling rules; checking that menus are fully navigable by gamepad focus.

Do not use for: what a button is bound to, contexts, rebinding and device glyphs, which is `game-input-mapping`; this skill treats focus movement as given and checks the graph built on it. The full accessibility review (subtitles, colour-only signals, motor and cognitive barriers) is `game-accessibility-pass`; this skill sets the layout rules it will later test. A usability critique of a flow against general heuristics is `ui-ux-review` in the design plugin. Translated string length and fonts per script are `game-localisation`; this skill only names the text-scale extremes to test at.

## Workflow

### 1. List the screens and the target displays

Write the screen inventory first: every HUD state (exploration, combat, dialogue, spectating) and every menu, including the ones reached only from another menu and the ones the platform forces on you, such as a disconnected-controller prompt. A screen missing from the list is a screen missing from the focus graph.

Then fix the display envelope in writing: the smallest physical display and resolution you will support (a handheld at arm's length, a television across a room), the largest, and the minimum and maximum text-scale settings. Specs say "legible at" these, never "looks fine".

### 2. Spec each screen from the template

Copy `assets/screen-spec-template.md` once per screen. Fill the information table before drawing anything: for each item the player sees, record the question it answers and when the player needs the answer.

| Rank | Needed | Treatment |
| --- | --- | --- |
| Always | Every few seconds, without looking away from play | Peripheral, stable position, large, no animation that needs reading |
| Danger | At the moment it is about to matter (low health, out of ammunition, timer) | Hidden or quiet until the threshold, then unmissable and not by colour alone |
| On demand | When the player asks | Behind a button or a menu, never on screen by default |

Most HUDs fail by promoting on-demand items to always. If every item is always, none is. Cap the always tier at what a player could name from memory after a minute of play, and push the rest down a rank.

### 3. Safe area and scale

Anchor every HUD element to a named edge or corner of the safe area, not to the screen edge. Do not assume a margin: read the current platform requirement for title-safe regions on each target and record it in the spec, because televisions and consoles differ, and give players a safe-area adjustment if any target needs one.

Specify size in a unit that scales (a proportion of screen height or a density-independent unit), with a stated minimum for body text and for the smallest tappable or focusable target. Then run the extremes as a table of screenshots or captures: smallest display at maximum text scale, largest display at minimum text scale, and the safe-area adjustment at its limit. Per screen, record clipped text, overlaps between elements and any control pushed off screen. Fix by reflow or truncation rules in the spec, not by shrinking the text scale range.

Read `references/layout-checks.md` at this step for the capture matrix, the overlap and clipping check, and what to do when a screen cannot fit.

### 4. Write the focus graph

For each screen, list nodes (every interactive control, plus the screen itself) and edges (the destination of each direction press, Confirm and Back from each node), as data, in the format `references/focus-graph.md` defines. Name the default focus for every screen: the control focus lands on when the screen opens, and where it returns to after a child screen closes.

### 5. Run the five checks

Run them on the node and edge list, not on the running game, and then confirm each failure against the game. `references/focus-graph.md` has the procedure step by step.

1. **Reachable.** Every interactive control is reachable from its screen's default focus by directional presses alone.
2. **No trap.** From every node, some sequence of presses leaves the screen or reaches Back. A modal that offers no cancel path is the usual trap.
3. **Back is defined.** Back from every screen lands on a named screen, and that screen is the one the player came from, or an explicitly documented parent. Back on the root screen is also defined: either nothing, or a confirmation to quit.
4. **No pointer-only control.** Every control that responds to a click or tap is a node with an edge in and an edge out. Hover-only reveals, drag-only reordering and on-screen scroll bars with no controller route are the usual offenders.
5. **Focus is visible.** Every node has a stated focus indicator that differs from its resting state by more than colour alone, on every background it can sit on, including over gameplay.

Record failures as a table: screen, node, check, fix. A check that cannot be run for lack of data is reported as unrun, never as passed.

### 6. Gate the spec

A spec is done when every screen in step 1's inventory has a filled template, the extremes in step 3 are captured with no unresolved clipping, and all five checks pass or each failure has an owner and a fix. Keep the node and edge list beside the spec and update it in the same change as any screen change, or it will drift from the game.

## Anti-patterns

**Designing at one size.** A layout checked only on the development monitor at default text proves nothing about the display the player owns.

**Everything is always.** A HUD that shows every stat all the time hides the one that matters at the moment of danger.

**Testing menus with the mouse.** The pointer can reach controls focus cannot, so a mouse pass hides exactly the defects step 5 exists to find.

**Back as an afterthought.** Each screen picks its own meaning, and one of them quits the game.

**Focus that disappears.** A highlight that vanishes when a tooltip opens or an animation plays leaves a player with no idea what Confirm will do.

## References

- `assets/screen-spec-template.md` — copy at step 2: the per-screen spec, with the information table, safe-area anchors, extremes and focus data.
- `references/layout-checks.md` — read at step 3: the capture matrix, the overlap and clipping check, and fitting a screen that does not.
- `references/focus-graph.md` — read at steps 4 and 5: the node and edge format and the five checks as a procedure.
