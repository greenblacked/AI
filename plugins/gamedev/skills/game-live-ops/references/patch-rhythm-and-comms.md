# Patch and hotfix rhythm, and community communication

Read this at steps 6 and 7, when setting the threshold between a scheduled patch and a hotfix, and when planning how the season communicates with players.

## Contents

- [The severity threshold](#the-severity-threshold)
- [What a hotfix does not skip](#what-a-hotfix-does-not-skip)
- [Writing patch notes players can act on](#writing-patch-notes-players-can-act-on)
- [The known-issues discipline](#the-known-issues-discipline)
- [Roadmap honesty](#roadmap-honesty)

## The severity threshold

Write the line between "waits for the next scheduled patch" and "ships as a hotfix" before an actual candidate is sitting in front of the team, because a threshold negotiated in the moment is negotiated under whatever pressure that specific bug is generating, not against a consistent standard the next bug will also be judged by.

| Severity | Example | Rhythm |
| --- | --- | --- |
| Blocks play or loses progress | A crash on launch, a save or purchase not applying, an exploit duplicating currency at scale | Hotfix, as soon as one can be built, tested and submitted |
| Degrades play for many players without blocking it | A visual bug, a minor balance outlier, an unintended but non-exploitable interaction | Next scheduled patch, noted as a known issue in the meantime |
| Cosmetic or affects few players | A typo, an edge-case visual glitch, an issue only reachable through an unusual setup | Backlog, addressed whenever a patch has room |

Calibrate the middle row to the game's own player impact rather than to how it looks in a bug tracker — a bug affecting a small fraction of a huge player base can still be a hotfix if what it does to those players is severe, and a bug affecting many players with a trivial effect can still wait.

## What a hotfix does not skip

A hotfix compresses the calendar, not the gates. It still owes `game-certification` its own submission wherever the platform requires review — an urgent fix is not exempt from the queue, only prioritised within the team's own process for getting into it. If it touches a tuned number, it still owes `game-balance` a prediction and a read, even if the window is compressed to match the urgency; a number changed under emergency pressure with no evidence is exactly the kind of change `game-balance`'s own anti-patterns warn against, urgency notwithstanding.

## Writing patch notes players can act on

State what changed in terms a player experiences, not the internal ticket or system name that produced it — "reduced the cooldown on X" rather than "fixed ENG-4821". Group by what affects the reader rather than by the game's internal component boundaries, the same ordering principle `release-notes` uses for a software changelog's audience. Where a change is a balance number, cite the reasoning `game-balance` recorded for it rather than restating just the old-to-new numbers with no context — a patch note that says why a change was made is read differently from one that only says what changed.

## The known-issues discipline

Name a known issue in the patch note the moment it is known to be shipping unfixed, rather than waiting for players to report it as though it were a surprise. A known-issues section that consistently gets ahead of player reports is one of the more durable ways a live team earns trust, because it demonstrates the team already knows what the players are about to find. A known-issues list that never shrinks, or that accumulates the same entry across several patches with no visible progress, tells players something true about the team's priorities whether or not that was the intent.

## Roadmap honesty

State roadmap items at the level of confidence the team actually has, and no higher. A specific date attached to a feature the team is not yet certain of costs more trust when it slips than a vaguer statement — "planned for a future season" — would have cost by being less exciting. The failure runs in one direction almost always: teams round confidence up to sound more reassuring in the moment, and pay for it later when the date moves and players remember the promise more precisely than the team does.

Where a roadmap item is cut entirely, say so directly rather than letting it quietly disappear from subsequent notes. Silence reads, correctly, as either forgetting or hoping nobody would notice, and either reading costs more trust than the plain statement that something did not happen.
