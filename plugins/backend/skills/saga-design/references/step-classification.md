# Step classification

Contents: questions to ask, worked example, awkward steps.

## Questions to ask of each step

1. If this succeeded and the next step failed, can we make the world acceptable again without the customer noticing? If yes, compensable.
2. Does the effect leave our system (money moved, message delivered, goods shipped)? If yes, it is probably the pivot or after it.
3. If it fails, is the failure usually permanent (declined card, out of stock) or transient (timeout)? Permanent failures belong before the pivot or as the pivot.
4. Can it be repeated safely with the same key? If yes and it is not undoable, it is retriable after the pivot.

## Worked example: booking

| Order | Step | Class | Compensation or retry rule |
| --- | --- | --- | --- |
| 1 | Create booking row as `pending` with a deadline | Compensable | Mark `cancelled` |
| 2 | Reserve inventory | Compensable | Release the hold; hold expires on its own at the deadline |
| 3 | Authorise the card | Compensable | Void the authorisation |
| 4 | Capture payment | Pivot | None; after this the saga moves forward only |
| 5 | Issue ticket | Retriable | Retry until success or the retry limit, then `failed_needs_human` |
| 6 | Send confirmation email | Retriable | Retry with a dedupe key |

Declines surface at authorisation, which is compensable and comes before the pivot. Capture is the pivot because it is the first step that cannot be undone, and everything before it is undoable. Authorising first and capturing last is what makes that possible.

## Awkward steps

- **Third party with no undo.** Move it after the pivot, or ask for a hold/confirm two-step API and treat the hold as the compensable half.
- **Step that is undoable only for a window.** Treat it as the pivot once the window is shorter than the saga's worst-case duration.
- **Human approval.** A compensable wait state with a deadline; the timeout compensates, it does not wait forever.
- **Reservation with a time to live.** Give the participant an expiry shorter than the saga deadline so a lost compensation heals itself, and still send the compensation.
