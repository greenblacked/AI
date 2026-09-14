# Cloud saves and conflict resolution

Read this at step 7, as soon as saves sync between devices at all. The work here is not the transfer; it is deciding what the game does when two devices both have real play in them, and doing it without deleting an evening.

## Contents

- [Why last-write-wins is wrong here](#why-last-write-wins-is-wrong-here)
- [What every save carries](#what-every-save-carries)
- [Detecting divergence rather than staleness](#detecting-divergence-rather-than-staleness)
- [The resolution prompt](#the-resolution-prompt)
- [Avoiding the conflict in the first place](#avoiding-the-conflict-in-the-first-place)
- [Platform sync models](#platform-sync-models)
- [Testing it](#testing-it)

## Why last-write-wins is wrong here

The rule sounds reasonable and fails in exactly the case it is invoked for. A conflict only exists when two devices both wrote since they last agreed, which means both copies contain play that happened. Choosing by timestamp then discards one of them.

Clocks make it worse rather than being a detail. A device that was offline may have a clock that is wrong by days, either direction; a player who travels changes time zone; a console that lost power resets its clock until it reaches the network. In each case "most recent" can name the copy with less progress in it, and the game deletes the larger one without asking.

## What every save carries

| Field | Why |
| --- | --- |
| Write counter | Increments on every successful write. Monotonic regardless of the clock, so it orders writes from one device reliably |
| Device identifier | A stable per-installation id, so a conflict can be described to the player as "your handheld" rather than as a hash |
| Accumulated playtime | The single number a player can compare two saves by, and the one they will actually use |
| Wall-clock timestamp | Still useful for display; never the deciding input |
| Lineage | What this write descended from — see below |

Playtime and a chapter or area name should be readable from the header without a full load, because the prompt has to show them before either save is chosen.

## Detecting divergence rather than staleness

The question is not "which is newer" but "did one of these descend from the other".

The cheap scheme that is good enough for a save system: each save stores the counter and device of the save it was written from. If the cloud copy's lineage names the local copy's current write, the cloud copy is a descendant and wins with no prompt. If the local copy's lineage names the cloud's, the local wins and uploads. If neither names the other, the histories have diverged and it is a conflict.

The fuller scheme, for a game with more than two devices in play, is a vector of per-device counters. A save dominates another when every entry is greater than or equal and one is strictly greater; anything else is a conflict. The cost is a few dozen bytes and one comparison function, and it removes a class of false merges the simpler scheme gets wrong when three devices are involved.

What matters either way is that the code has three answers — local wins, remote wins, conflict — rather than two. A design with only two answers has already decided to lose data.

## The resolution prompt

Show the facts, not the storage location:

```text
Two versions of your save do not match.

  This device        Playtime 41h 12m   Chapter 9    Saved 2 hours ago
  Cloud (handheld)   Playtime 39h 50m   Chapter 8    Saved yesterday

  [ Use this device ]  [ Use cloud ]     Both are kept; the other becomes a backup slot.
```

- Never phrase it as "local or cloud". Nobody knows which one they played last by that name.
- Keep the copy that loses, as a recoverable slot. The player choosing wrong under a prompt should not be a permanent loss, and it is the main reason players hate the prompt.
- Do not offer an automatic merge of two divergent saves unless the game's state genuinely decomposes — separate per-character files, or progress that is a set union of unlocks. A merged world state produces a game that is in no state the designers wrote.
- Resolve before play starts, not after. A prompt that arrives after ten minutes of play has created a third version.

## Avoiding the conflict in the first place

Most conflicts are created by the game, not by the player:

- Save and upload on quit, on suspend and on background. A session that ends without an upload guarantees the conflict on the next device.
- Resolve any pending upload at launch, before the main menu allows a slot to be loaded.
- When an upload fails, retry in the background and keep the pending state; a save marked uploaded that was not is what turns a stale copy into a divergence.
- Show a small, honest sync indicator, so a player who is about to close the game on one device can see that it has not finished. This is also a platform requirement in some storefronts.
- If the game has offline play, expect divergence as normal rather than exceptional and make the prompt good, because no amount of avoidance removes it.

## Platform sync models

They differ enough that the abstraction has to be yours:

- **Steam Cloud** syncs declared file patterns around process start and exit, and detects conflicts itself, showing its own dialogue. Keep files inside the declared paths and keep the set small; the Auto-Cloud pattern approach is the one that surprises teams when a backup rotation puts unexpected names in the directory.
- **Console save data** is mediated by the platform's own API and quota, with sync behaviour tied to the account rather than to the game. Test with the same account signed in on two devices, which is the case players hit.
- **iOS and Android** have iCloud and Play Games saved games, each with their own conflict callback. Play Games surfaces conflicts to the game to resolve, which means the resolution code is required rather than optional.
- **Your own backend** gives full control and makes you responsible for authentication, quota, retention and the privacy declarations that go with storing player data.

Whichever is underneath, keep the conflict logic in the game and platform-independent. The platforms disagree about when they sync, and a resolution written against one of them is rewritten for the next.

## Testing it

- Two save directories and a stub sync layer reproduce every case on one machine. Drive it from a test rather than from two consoles.
- The cases worth scripting: clean descendant both directions, genuine divergence, a clock set backwards on one side, an upload that failed after the local write, the same device restored from a backup, and a save from a newer format version arriving from the cloud.
- Assert on what the player keeps, including that the losing copy is still recoverable.
- Include a device that has never synced before, and one whose local save is corrupt while the cloud copy is fine. The second is the case where a naive implementation uploads the damage.
