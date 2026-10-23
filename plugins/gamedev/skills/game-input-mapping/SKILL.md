---
name: game-input-mapping
description: "Build an input layer where gameplay reads named actions, never physical keys: contexts that switch on and off, bindings as data with player overrides kept apart from defaults, a rebind screen that swaps instead of stealing, glyphs that follow the last-used device the frame it changes, radial deadzones with rescale, and menus that own focus as state so every screen works without a pointer. Ends with a test list (unplug in-game, two pads, wake from sleep, a no-pointer walkthrough). Use for \"add controller support\", \"players want to remap keys\", \"show the right button icons\", \"stick drift deadzone\", \"switching between mouse and gamepad mid-game\", \"menu doesn't work with a controller\". Not for feel or input latency (game-builder), assists (game-accessibility-pass), platform disconnect tests (game-certification), or web forms (form-design)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Game Input Mapping

The work is done when no gameplay or menu code names a physical key or button, a player can rebind everything without losing the way to open the menu, the on-screen prompts match the device in their hands, and every screen can be completed with a controller alone.

The usual failure is a layer that grew from `if (key == Space)`. Rebinding gets bolted on later and misses the tutorial text, the glyphs and the one dialog nobody tested, and controller support ends at the pause menu because the menus were built for a mouse. Fix the contract first, then the screens.

## Scope

Use for: the action and binding model, the rebind screen, glyphs and prompt tokens, analogue stick handling, menu focus and navigation, and device hot-swapping.

Do not use for: how responsive or forgiving the controls feel (`game-builder`), accessibility options such as hold-to-toggle, one-handed schemes and assists (`game-accessibility-pass`), the disconnect behaviour a platform certifies (`game-certification`), or forms in a web page (`form-design`).

## Workflow

### 1. Make actions the contract

Gameplay and UI code ask "is `jump` pressed", never "is Space pressed". List every action the game needs, then give each a type: digital (pressed, held, released), or analogue (a float or a 2D vector, such as move and aim). A trigger used as a button and a trigger used as a throttle are different actions, because deadzone and threshold rules differ.

Group actions into contexts: gameplay, menu, vehicle, dialogue, photo mode. A context can be enabled or disabled, and a stack of them resolves which one receives an input. The reason to do this early is that the same button must mean "jump" in one context and "confirm" in another without either handler knowing about the other. Engines already provide the plumbing (an action map in Godot, the Input System in Unity, Enhanced Input in Unreal); use it rather than writing a second layer, and keep game code behind a thin interface of your own.

### 2. Store bindings as data, in two layers

Bindings live in a data file per device family (keyboard and mouse, gamepad, and any other family you ship), not in code. Keep two layers: the shipped defaults, and the player's overrides saved separately. Resolve defaults then overrides at load. Why: a patch can then change a default, fix a bad binding or add an action, and players keep every change they made. A single saved file of full bindings freezes every player at the defaults of the day they first launched.

Version the schema, and key overrides by action name and binding slot, not by array position. Reset must work per action and per device family, and the saved file must survive an action being removed.

### 3. Build the rebind screen to survive abuse

Read `references/rebind-and-focus-checklists.md` for the full test matrix. The rules:

- Detect conflicts inside a context, since the same key may legitimately appear in two contexts. On a conflict, offer to swap the two actions; never steal the key silently, because the displaced action is then dead and nobody knows.
- Allow more than one binding per action, a primary and an alternate, per device family.
- Refuse to unbind the only way to open the menu, and the only way to confirm and cancel in menus. A player with no menu button cannot fix the mistake.
- Cancel the capture with a fixed key that cannot itself be captured, and time the capture out, so a stray press does not leave the screen waiting.
- Handle modifiers (hold Shift plus a key), hold versus press as a per-binding property, and chords. Decide whether a lone modifier can be bound and test it, since many bugs hide there.
- Keep keyboard layout in mind: show the key by the character it produces (AZERTY, QWERTZ), but store the physical position so default WASD movement lands correctly on every layout.

### 4. Drive glyphs and prompts from the last-used device

Track the last used device family from real input, not from what is connected: a gamepad left plugged in must not force controller prompts on a player using the mouse. Families to cover are keyboard and mouse, Xbox, PlayStation, Switch and Steam Input; map the action to the actual binding for the current family and fetch the glyph for that binding.

Update every visible prompt on the frame the family changes. Ignore tiny noise (a resting stick that jitters above zero) when deciding it changed, or prompts flicker. Never write a button name into text: tutorials, subtitles, hints and loading tips use a token such as `{action:interact}` that the UI resolves at display time to a glyph or a text label, and to the player's own rebound key. Hard-coded text is the reason a rebound game still says "press E".

### 5. Handle analogue input properly

Raw sticks never rest at exactly zero, and a worn one drifts. For each stick:

- Use a radial deadzone, not one per axis, so diagonals are not squashed. Rescale after cutting it: for magnitude `m` and deadzone `d`, output magnitude is `(m - d) / (1 - d)` along the same direction, so the response starts at zero rather than jumping to `d`. With the outer threshold `o` from the next bullet, the combined form is `clamp((m - d) / (o - d), 0, 1)`, so full deflection reaches 1.0.
- Add an outer threshold (the stick rarely reports a full 1.0 at the rim) so full deflection is reachable, then a response curve and a per-axis sensitivity.
- Expose inner deadzone, outer threshold, curve and sensitivity as player settings, with a default that is sane for a new pad. Triggers get their own thresholds.
- Test with a recording of a worn controller, or synthetic noise injected at the deadzone edge, and confirm the camera does not creep, a menu cursor does not drift and the character does not walk on its own.

### 6. Make menus own focus as state

A pointer menu gets by without focus; a controller menu is nothing but focus. Treat the focused element as explicit state with rules:

- Every screen declares its initial focus on open, and a return target when a modal closes, so closing a popup puts focus back where it was rather than on nothing.
- Navigation order is explicit wherever the layout is not a clean grid. Automatic neighbour search picks the wrong item on offset, scrolling or overlapping layouts.
- A debug check logs any frame where a menu is open and nothing is focused. This is the cheapest way to find the dead-end screens.
- Mouse movement hides the focus ring and switches to pointer behaviour; any controller or keyboard navigation input restores it and starts from the last focused element, not from the top.
- Text entry (names, search, chat) has a controller path: the platform's on-screen keyboard, or your own, with confirm and cancel working.
- Scrolling lists scroll to keep the focused item visible, and sliders and toggles respond to left and right.

### 7. Test the hard cases

Run the list in the checklist reference. The ones that break most often: unplug the active controller mid-game and mid-menu, connect a second controller and decide who owns the session, wake the machine from sleep with a pad that reconnects under a new id, and a walkthrough of every screen and popup, including error dialogs and first-run prompts, with no pointer, done by someone who did not build it. The builder knows where focus goes; a fresh tester finds where it does not.

## Hand back

The action list with contexts and types; where bindings live and how defaults and overrides merge; the rebind rules implemented; how glyphs and tokens resolve; the analogue settings and their defaults; the per-screen focus table (initial focus, return target); and the test list with what passed. Name any screen you could not reach without a pointer.

## Anti-patterns

**Reading keys in gameplay code.** One direct read becomes the thing a rebind cannot reach.

**Saving the whole binding table.** It blocks every future default change.

**Prompts decided by what is plugged in.** The wrong glyphs appear for everyone with a pad in a drawer.

**Per-axis deadzones.** The stick feels square and diagonals are weak.

**A modal with no return target.** It closes, focus is gone and the controller player is stuck.

## References

- `references/rebind-and-focus-checklists.md` - read at steps 3 and 6 and before the final test pass: the rebind test matrix, the per-screen focus contract and the hot-swap test list.
