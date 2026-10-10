# Recurrence

## Contents

- Why a repeat halts the loop
- What counts as the same finding
- What is not a repeat
- What Architect receives

## Why a repeat halts the loop

A finding that returns after a fix means the fix removed the symptom and left the cause. A third attempt at the same patch has the same odds as the second, and each one adds change that the next inspector has to read. The cheaper move is to change the approach, which is Architect's stage, so the loop stops and goes there.

## What counts as the same finding

Same failing criterion and either the same locator or the same cause, even if the inspector words it differently. Compare against the ledger, not against memory:

- Same criterion, same file and function, different line: the same finding.
- Same criterion, different file, same missing check or same wrong assumption: the same finding, because the cause is one decision made in two places.
- A different criterion that fails because of the same decision: treat it as the same when the fix would have to change that decision.

## What is not a repeat

- A new defect introduced by the fix. Send it back as a new finding; a second one in the same area, though, is a sign to look at the approach.
- A finding that was an observation in an earlier round and is now blocking because the frame changed.
- A check that could not run last round and ran this round. That is progress on not assessed, not a recurrence.

## What Architect receives

The reopened Architect gets, and nothing from the inspector's whole reports:

- The frame, unchanged unless the finding invalidates it.
- The approach that was built, and the decision already recorded.
- **The finding, as a constraint**: "the approach must make this impossible, or must not depend on this", with the criterion it fails and the two attempts that did not hold.

Architect returns `PROPOSED` with a changed approach, which goes back through Make, or `NEEDS FRAME` when the finding shows the frame is wrong. Either way the next Inspect starts at round one with a new ledger. If the new approach rests on a claim nobody has read the source for, settle it first with `frame-claim-ledger`.
