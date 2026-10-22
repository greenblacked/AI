# Rebind and focus checklists

## Contents

rebind screen test matrix, focus contract per screen, device hot-swap tests, binding file shape

## Rebind screen test matrix

Run each row on every device family you ship. A row passes only when the binding works in game, the prompt shows the new binding, and the saved file survives a restart.

| Case | Expected |
| --- | --- |
| Bind an unused key to an action | Works at once; prompt updates everywhere |
| Bind a key already used in the same context | Offer to swap; neither action ends up unbound without the player seeing it |
| Bind a key used only in a different context | Allowed, no warning |
| Add an alternate binding | Both work; removing one leaves the other |
| Bind a modifier plus a key | Works; releasing the modifier first does not leave the action stuck |
| Bind a lone modifier | Behaviour is defined and tested, not accidental |
| Hold versus press on one binding | Chosen per binding, saved, and honoured in game |
| Chord of two buttons | Fires once on completion; does not also fire each member's own action |
| Try to unbind the menu open action | Refused with a message |
| Try to unbind menu confirm or cancel | Refused with a message |
| Press the cancel key during capture | Capture ends, old binding kept |
| Leave capture waiting | Times out, old binding kept |
| Reset one action | Only that action returns to default |
| Reset the device family | All overrides for that family removed, others untouched |
| Ship a patch that changes a default | Players keep their overrides; unchanged actions pick up the new default |
| Ship a patch that removes an action | Old overrides for it are ignored without error |
| Non-QWERTY layout | Default movement is under the same physical keys; labels show the local characters |

## Focus contract per screen

Fill one row for every screen, popup and overlay, including error dialogs, confirmation prompts, first-run notices, loading and saving overlays and platform-sign-in prompts.

| Field | What to write |
| --- | --- |
| Screen | Name |
| Initial focus | The element focused on open; must be enabled |
| Return target | Where focus goes when this closes (or the element that opened it) |
| Navigation order | Explicit list if the layout is not a plain grid |
| Cancel behaviour | What cancel does here, and whether it is always available |
| Text entry | The controller path, if any |
| Disabled items | Skipped, or focusable with a reason shown |

Debug assertions worth keeping on in development builds:

- A menu is open and no element is focused for more than one frame.
- Focus is on a disabled, hidden or off-screen element.
- A modal is open and focus is outside it.
- A close handler runs and no return target was set.

## Device hot-swap tests

- Unplug the active controller during play: the game pauses or continues as designed, prompts switch to the next device in use, nothing sticks pressed.
- Unplug it in a menu: focus survives, and the keyboard or mouse still works.
- Plug it back in: it is recognised without restarting, and the same player slot is restored.
- Two controllers connected: the rule for which one drives menus and which one is the player is written down and holds.
- Wake from sleep with a wireless pad: it reconnects, possibly under a new id, and bindings still apply.
- Switch from mouse to pad mid-menu: the focus ring appears at the last focused item; back to the mouse and it hides.
- Hold a button, swap devices, release: no stuck action.
- Start the game with a pad already held in a non-neutral position: the first frame does not treat it as drift or a press.

## Binding file shape

An illustration, not a mandated format. Keep the two files separate.

```json
{
  "schema": 3,
  "family": "gamepad",
  "bindings": {
    "gameplay/jump": [{"input": "south", "mode": "press"}],
    "gameplay/aim": [{"input": "right_stick", "mode": "vector2"}],
    "menu/confirm": [{"input": "south", "mode": "press"}]
  }
}
```

Defaults ship with the game and are replaced by patches. The overrides file holds only what the player changed, keyed by `context/action` and slot, with the same `schema` field so it can be migrated.
