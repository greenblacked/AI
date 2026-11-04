# Hard severity calls

The scale in the main file decides most bugs. These are the cases where people disagree, with the reasoning to apply rather than a new rule.

## Exploits and duplication

An item or currency duplication is S2 while it needs obscure steps and the game is single-player: the player who uses it harms only their own experience. It becomes S1 when it is shared by an online economy, a leaderboard or a store, because it damages other players, and the response then belongs in `economy-exploit-response`. A duplication that corrupts the save is S1 on its own account.

## Performance regressions

A frame-time or load-time regression is not S1 merely because it is large. Ask what the player does: a stall that trips a platform watchdog or a certification limit is S1, since certification failure is on the scale. A drop that makes a section unpleasant is S2 or S3 depending on whether it is on the progression path. Measure with the tools `game-performance` names rather than asserting a number.

## Accessibility failures

A required interaction that cannot be done without a particular sense or input, on the progression path, blocks that player from finishing and is S1 for them. Where the game claims a feature in its store listing or in a certification submission, a failure of that claim is also a certification or store-page risk. Otherwise rank by the same question: can the player continue?

## One platform only

Severity is judged per platform, and the gate applies per platform: an S1 on one console blocks that console's release even if the others are clean. Record which platforms were tested and which were not, since an untested platform has an unknown rather than a zero.

## Rarely reached content

Do not lower severity because few players reach the content. A late-game soft-lock affects only players who got there, and they are the most invested. Lower the priority of the fix if you must, never the severity.

## Bugs that only appear after a long session

Memory growth, handle leaks and state drift appear after hours. They are S1 if the build crashes or hangs within a play session a player would plausibly have, and S2 otherwise. Record the session length as part of the narrowing field.

## Disputes

If two people cannot agree, write down the player's next action in each reading and pick the level whose definition that action matches. If the dispute remains, take the higher severity until a measurement settles it.
