# Focus-graph check

Read at steps 4 and 5 of the skill. The check runs on data, so it can be done before the screens are built and repeated whenever one changes.

## The format

One node line per interactive control, one edge line per press that moves focus or changes screen.

```text
node: settings.volume | type: slider | indicator: outline plus arrow glyphs
node: settings.back   | type: button | indicator: outline plus fill change
settings.volume --down--> settings.back
settings.volume --back--> screen:pause
settings.back   --confirm--> screen:pause
```

Rules for the data:

- Node ids are prefixed by their screen, so they are unique across the set.
- A target is a node id or `screen:<name>`. A screen target means focus moves to that screen's default focus, or to the remembered focus if the spec says the screen restores it.
- Absent edges mean the press does nothing. That is allowed, but it must be written by omission knowingly; step 3 below surfaces the consequences.
- A slider or text field consumes left and right, so those directions are not exits from it. Write that down, since it is the cause of many traps.
- Each screen lists its default focus and its parent.

## The procedure

Do each pass per screen, then once across the set.

1. **Reachability.** Start at the screen's default focus. Follow every directional edge and every edge that stays on the screen (Confirm on a toggle, say), marking nodes visited. Any node on the screen not visited is unreachable. The fix is an edge in, not a shortcut around it.
2. **Trap search.** Build the set of nodes from which a screen exit is reachable: start from every node with a Back edge or a `screen:` edge and walk edges backwards. Any node outside that set is a trap. Also check the screen as a whole: a modal whose only exits are Confirm paths that re-open the modal is a trap.
3. **Back.** Every screen needs a Back edge from every node, or a screen-level Back that applies to all nodes. List each screen's Back target and compare with the screen that opened it. A mismatch is fine only when the spec documents the parent. Flag Back that loops (A back to B, B back to A) and Back that skips a screen the player did not intend to skip.
4. **Pointer-only.** For every control the spec marks as responding to click, tap, hover or drag, confirm a node exists with an incoming and outgoing edge. Then search the spec for the pointer-only forms: hover to reveal, drag to reorder, click-away to dismiss, scroll bar with no list node, tap on a map or grid with no cell nodes. Each needs an equivalent that focus can drive.
5. **Focus visibility.** Check the indicator column of every node: it must be present and must differ from resting state by shape, outline, size or glyph, not only by hue. Then list the states that could hide it: a tooltip, an animation, a transition between screens, a background of similar brightness, a modal opening over the HUD. A node with a hidden state needs a rule.

## Across the set

- Walk from the root screen to every other screen using Confirm edges. A screen not reached is orphaned: either dead, or reachable only by an event the inventory should name.
- For every screen reached, walk Back until the root. If Back never reaches the root, a path exists that the player cannot undo.
- After a child screen closes, check where focus lands. Landing on the first node instead of the control that opened the child makes a list-heavy screen unusable for someone repeating an action.

## Confirm on the running game

The data check finds defects; the game confirms them and finds the data was wrong. Play each failing path with only the controller connected and the pointer unplugged or ignored, once with focus starting on the default and once after returning from a child screen. If the engine can log focus changes, log them and diff against the edge list; any transition in the log with no edge in the list means the spec is out of date.

Record results in the Checks table of the screen spec. A check not run is written as unrun.
