# Choosing the fix route for a live defect

Read this at step 6a, once the severity threshold says a defect is a hotfix and the question becomes which mechanism carries the fix. The threshold decides whether to break the calendar; the route decides how much of the calendar's cost the break has to pay.

## Contents

- [The order](#the-order)
- [Choosing by lead time and blast radius](#choosing-by-lead-time-and-blast-radius)
- [Write the rollback before the fix ships](#write-the-rollback-before-the-fix-ships)
- [A worked choice](#a-worked-choice)
- [Where this stops](#where-this-stops)

## The order

Try the routes from the one that changes the least to the one that changes the most, and take the first that actually removes the harm, not the first that sounds adequate.

1. **Server-side configuration change or kill switch.** Turn the broken feature, offer, reward source or code path off, or move a data value, without shipping any code. Fastest to apply and fastest to undo. It only works if the game was built to read that setting live, so find out which settings are live-readable before an incident, not during one.
2. **Feature flag.** Route the affected behaviour back to the old path, or off, for all players or a slice. It needs the flag to exist already in a shipped build; a flag added now rides the same slow route as the fix it was meant to avoid.
3. **Server deploy.** Ship fixed server code. Faster than a client patch because no player action or store review is involved, but it changes behaviour for everyone connected and can strand live sessions. How to roll it out without killing matches is `game-server-rollout`'s procedure, not this one.
4. **Certified client patch.** Last, because it waits on the platform's review queue and then on players installing it. Some players will run the broken build for days after it ships. Use it only when the defect lives in code or content the client owns and no earlier route can neutralise it.

A fix that needs two routes is normal: neutralise with route 1 or 2 now, then correct properly through 3 or 4 on the calendar. Record the neutralising change as temporary, with the condition for removing it, or it becomes permanent by neglect.

## Choosing by lead time and blast radius

Two questions decide the route, answered before anyone starts writing the fix.

**Lead time.** How long until the fix is in front of every affected player? Take the platform's certification turnaround from `game-certification` for each platform the game ships on, plus the time players take to update. Check the real numbers from your last few submissions rather than assuming; they differ by platform and by whether the submission is an expedited one. The longest platform sets the client-patch figure, and a defect that harms players faster than that figure cannot wait for route 4.

**Blast radius.** Who and what does the change touch, if it is wrong? A config value scoped to one region or one offer touches little. A server deploy touches every live session. A client patch touches every installed copy and cannot be pulled back from players who have taken it.

| Defect | Harm per hour | Likely route |
| --- | --- | --- |
| A reward source or offer grants the wrong amount | Compounds | Kill switch on that source now; the cause goes to `economy-exploit-response` if it is being abused |
| A new feature crashes or soft-locks players | Steady | Flag it off; fix on the calendar |
| Server logic returns a wrong result for everyone | Steady | Server deploy, rolled out per `game-server-rollout` |
| A client crash on one platform at launch, no live switch reaches it | Steady, blocks play | Certified client patch, with route 1 or 2 narrowing exposure while it is in review if anything can |
| A cosmetic defect | Negligible | Not a hotfix; backlog per the severity table |

When two routes both work, take the smaller blast radius unless the lead time forbids it. A kill switch that costs players a feature for a day beats a client patch that costs them a build they cannot roll back.

## Write the rollback before the fix ships

Before the change goes out, write down, in the incident or patch ticket:

- **The undo.** The exact reversal: the setting's previous value, the flag state, the previous server build, or, for a client patch, what the next patch reverts and how long that takes. For a client patch the honest answer is often "a second certified submission", and that has to be stated rather than discovered.
- **The trigger.** The observable condition that means the fix is making things worse, chosen now, in the same spirit as the season's stop rule in step 5: an error rate, a crash-free figure, a currency-in-circulation reading, from the game's own baseline.
- **The owner and the clock.** Who has authority to pull the undo without asking, and how soon after shipping the first reading is taken.
- **What the undo cannot reverse.** Granted items, written saves and migrated data do not come back by reverting code. If the fix migrates or writes player data, take a backup or a ledger of the affected records first, and check the undo against a copy of that data.

A fix with no written rollback is a second incident waiting for its first bad reading. Reading the undo aloud to someone who did not write the fix is a cheap test of whether it is a procedure or a hope.

## A worked choice

A reward event pays double the intended currency on one platform, and the loss compounds every hour. The client build that holds the reward table is in certification everywhere.

1. Check route 1: the reward amount is read from server config. Set it to the intended value, or switch the event's payout off, scoped to the affected platform. No code ships.
2. Write the rollback: record the previous value, and name the on-call live-ops lead as its owner. The check that the change worked depends on which one step 1 made: a corrected amount brings the payout rate per player-hour back inside the expected band at the first reading, and a switched-off payout brings it to zero on the affected platform. The trigger is a separate sign that the change is making things worse, never the drop it was made to cause: failed reward claims or event errors rising above baseline, or, for a corrected amount only, the payout falling below the band so players are now underpaid.
3. Record the temporary change and the condition for lifting it.
4. Hand the already-overpaid balances to `economy-exploit-response`, which quantifies them from the ledger; do not decide them here.
5. Move the corrected table into the next scheduled client patch only if the config route cannot hold it permanently.

## Where this stops

This procedure picks the route and requires the rollback. Draining servers and version windows are `game-server-rollout`; containing and repairing an exploit and judging affected accounts are `economy-exploit-response`; staging a build behind rings is `release-strategy`; the platform submission itself is `game-certification`; talking to players during the incident is `incident-comms`. A hotfix that touches a tuned number still owes `game-balance` its prediction and read.
