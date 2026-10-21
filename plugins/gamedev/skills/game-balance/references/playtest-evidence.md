# Playtest evidence

Read this at step 6, when findings from a playtest have arrived and some of them mention a number. How to run the session, recruit the testers and sort what came out into bugs and design findings is `game-playtest`; this file starts after that and covers only what a balance pass can take from it.

## Contents

- [What a finding can be](#what-a-finding-can-be)
- [From finding to hypothesis](#from-finding-to-hypothesis)
- [What a handful of sessions cannot establish](#what-a-handful-of-sessions-cannot-establish)

## What a finding can be

Sort each finding into one of three before a value moves.

| Finding | Example | Where it goes |
| --- | --- | --- |
| Comprehension | Testers die repeatedly to an encounter because they never noticed what the mechanic does | Back to `game-playtest`'s ranked change list. No number fixes it |
| Candidate number | Testers understood the encounter, tried it several times and could not clear it | A hypothesis for steps 2 to 4 of `game-balance` |
| Preference | A tester finds an option annoying or boring | Context only. One person's annoyance does not make an option strong |

The first row is the one a dashboard hides. A death spike at an encounter reads as a difficulty problem in the data and can turn out to be a telegraphing, camera or UI problem once someone watches, which is why the sort comes before the tuning.

## From finding to hypothesis

State the candidate as a claim the telemetry can contradict: "the second boss is too hard for players who cleared the first, because testers needed many attempts after understanding the pattern". Then name the reading that would test it: attempts-to-clear per encounter, the death rate at that encounter and where the players who stopped did so.

When the testers proposed a fix, record the complaint and drop the fix. "Make the boss weaker" is a report that the fight was frustrating. The same report fits health, a damage source nobody explained and a hard-to-read attack, and the number is the least likely of the three.

Where there is no telemetry yet, a count of attempts per tester per encounter, taken from the recordings, is the evidence available. Report it as counts of testers, never as a rate, and treat it as enough to decide where to place instrumentation and as not enough to size a change.

## What a handful of sessions cannot establish

- Whether the numbers are balanced. That needs the volume in `references/telemetry.md`.
- How common a problem is. A few people show that something is possible, not how often it happens.
- Whether players will keep playing over weeks. A retention question has to be measured over that time.
- Whether the game balances for an audience nobody recruited.

A change prompted by playtest evidence still follows steps 5 to 7: one change, a written prediction and a window to read it.
