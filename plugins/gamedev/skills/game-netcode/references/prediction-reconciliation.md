# Prediction, reconciliation, interpolation and lag compensation

Read this at step 4, while implementing any of the four. They are four separate mechanisms, each removing one specific visible artefact, and the most common bug is building one of them and expecting another one's benefit.

## Contents

- [What each one is for](#what-each-one-is-for)
- [The input protocol everything rests on](#the-input-protocol-everything-rests-on)
- [Client-side prediction](#client-side-prediction)
- [Server reconciliation](#server-reconciliation)
- [Error smoothing](#error-smoothing)
- [Entity interpolation](#entity-interpolation)
- [Sizing the interpolation buffer](#sizing-the-interpolation-buffer)
- [Lag compensation](#lag-compensation)
- [Peeker's advantage](#peekers-advantage)
- [The rollback variant](#the-rollback-variant)
- [Latency bands by genre](#latency-bands-by-genre)
- [Shipped rates](#shipped-rates)
- [Diagnosing by symptom](#diagnosing-by-symptom)
- [Sources](#sources)

## What each one is for

| Technique | Applies to | Removes |
| --- | --- | --- |
| Client-side prediction | The local player's own entity | The round trip between pressing a key and moving |
| Server reconciliation | The local player's own entity | The drift and snap that prediction alone accumulates |
| Entity interpolation | Every remote entity | The stutter and teleporting between snapshots |
| Lag compensation | Instant-effect actions, on the server | Having to lead targets by your own ping |

Note what is absent: none of these makes the game fair for a player at 250 ms. They make it feel local. Fairness is a separate decision about matchmaking by region and about the rewind cap below.

## The input protocol everything rests on

Prediction and reconciliation both depend on the client and server agreeing on which inputs have been processed. The protocol is small and it is worth writing down before either technique:

1. The client stamps each input with a monotonically increasing sequence number and the simulation tick it was sampled for.
2. The client stores the input in a ring buffer alongside the local state that resulted from applying it.
3. The client sends the newest input plus the last few unacknowledged ones in the same packet. Inputs are tiny — a bitfield and two angles — and re-sending them makes packet loss cost nothing, which is far cheaper than making the channel reliable.
4. The server applies inputs in sequence order, clamps the claimed tick into an accepted window around its own tick, and discards anything outside it.
5. Every state update the server sends carries the sequence number of the last input it processed for that client.

Everything after this is built on that acknowledgement. A protocol without it can predict but cannot correct, which is the worst of both.

## Client-side prediction

The client applies its own input to its own entity immediately, using the same simulation code the server runs. The words "the same code" are the requirement: a client that approximates the server's movement will disagree with it constantly, and every disagreement is a correction the player sees. Share the movement function between client and server builds.

Predict only what the local player owns and what depends solely on their input. Predicting the result of an interaction with another player — whether a shot hit, whether a door was already opened — means predicting something the client cannot know, and it produces the worst artefact in the catalogue: an action that visibly succeeds and is then undone.

The exception worth making is presentation. Play the fire animation, the muzzle flash and the sound immediately on the client, while leaving the damage to the server. The player perceives the responsiveness and never sees the mispredict, because the flash was never authoritative.

## Server reconciliation

Each time a state update arrives:

1. Read the acknowledged input sequence number and the authoritative state that goes with it.
2. Compare against the stored local state for that same sequence number.
3. If they agree within a tolerance, discard everything up to that sequence and stop. This is the common case.
4. If they disagree, overwrite the local state with the server's, then replay every stored input after the acknowledged one through the same simulation step, in order, to arrive back at the present tick.

The replay is what makes the correction invisible. Without it, the client is snapped to a position that is one round trip old, then continues from there — which is exactly the rubber-band: the player walks forward, is pulled back to where they were 80 ms ago, walks forward again.

Two details decide whether this works in practice. The tolerance must be small; a large one lets error accumulate until the correction is big enough to see. And the replay must be deterministic with respect to the client's own inputs, which means the same fixed timestep, the same constants and no dependence on frame rate.

## Error smoothing

Even with reconciliation there will be corrections, from a mispredicted collision or a server-side effect the client could not know about. Applying a correction instantly is visible as a jump. Instead, keep the correction as an offset between the rendered position and the simulated position and decay that offset over a short window — 100 to 200 ms is the usual range — so the character walks to where it should be rather than appearing there.

Smooth the render, never the simulation. If the smoothed position feeds back into collision or hit detection, the client and server disagree about where the player is, and the next correction is larger than the one just smoothed away.

## Entity interpolation

Remote entities are not predicted; they are rendered in the past. The client keeps a buffer of received snapshots and renders each remote entity at a render time that is deliberately behind the newest snapshot received, interpolating between the two snapshots that bracket it.

This is why interpolation is independent of prediction and why it is the cheapest of the four to build: it needs no acknowledgement, no replay and no shared simulation. It is also the first thing to build, because the artefact it removes — remote players teleporting at the send rate — is the one players notice first.

Extrapolation is the tempting alternative: project the entity forward from its last known velocity instead of rendering it late. It is right for short gaps, roughly one send interval, as a way to survive a single lost packet without a visible stall, and it is wrong as a general policy, because a player who changes direction is drawn somewhere they never were and then corrected. Bound extrapolation in time and stop rather than extrapolating further.

## Sizing the interpolation buffer

The buffer is a latency you are adding on purpose, so size it from measurements rather than from a round number.

- The floor is one send interval, because below that there is no second snapshot to interpolate towards.
- Two send intervals absorbs a single lost packet with no visible stall. This is the standard starting point.
- Add the measured jitter of that client's connection — the variation in inter-arrival time, not the average latency.

Worked from the rates in the table below: at a 64 Hz send rate the interval is 15.6 ms, so a two-interval buffer is 31 ms, which is the value Source's `cl_interp_ratio 2` over `cl_updaterate 64` produces. At a 20 Hz send rate the same ratio gives 100 ms, which is what the older `cl_interp 0.1` default encoded.

Adapt it per client. A single fixed buffer is either too small for the worst connection or a tax on every good one, and the difference between 31 ms and 100 ms of added latency is directly perceptible in an aiming game.

## Lag compensation

Without compensation, a client at 100 ms sees every other player 100 ms plus the interpolation buffer in the past, and must lead their targets by that much. Compensation moves that burden to the server: when a fire command arrives, the server reconstructs where the other entities were at the moment the firing client saw them, and resolves the shot against that reconstruction.

The server therefore keeps a short history of every entity's collision state — position and hitbox pose, one entry per tick, covering the largest latency it is willing to compensate for. On a fire command it computes the client's view time as roughly the server's receive time minus the client's half round trip minus that client's interpolation buffer, rewinds the relevant entities to that time, traces, and restores.

Three rules keep it from being abused:

- **Cap the rewind window** and refuse to compensate beyond it. The cap is the point at which the target's experience is worse than the shooter's gain, and it is also the exploit: without a cap, a player with a deliberately degraded connection kills targets who have been behind cover for a second.
- **Derive the rewind from the server's own measurement** of the client's latency and interpolation setting, never from a client-supplied timestamp. A client that can name its own rewind can shoot into the past at will.
- **Compensate the trace, not the outcome.** A shot that hits a rewound player still applies damage at the present tick against present health. Rewinding the damage as well produces revived players and negative health.

Compensation applies to instant effects — hitscan weapons, melee, interaction. Projectiles with travel time are usually better handled by spawning them on the server from the client's aim and letting them fly, since the travel time already hides the round trip.

## Peeker's advantage

The player who moves around a corner sees the stationary defender before the defender sees them. This is not a bug and it cannot be removed: the peeker's own position is predicted locally and therefore current, while the defender sees the peeker through the network, delayed by the peeker's upstream latency, the server's send interval and the defender's interpolation buffer. Lag compensation then resolves the peeker's shot against where the defender was, so the defender can be killed before the peeker appears on their screen.

Reducing it means reducing the three delays that make it up: raise the send rate, shrink the interpolation buffer to the measured jitter, and keep the server near the players. It cannot be designed away in the netcode, and games in the genre design around it instead — sound cues, longer sightlines, weapons with spin-up. Riot's "Peeking into VALORANT's Netcode" works the arithmetic through with the engine's real numbers.

## The rollback variant

In a rollback game the four techniques above collapse into one mechanism, because the simulation is deterministic and shared.

- Local input is applied on the frame it is pressed, with no added delay. That is the prediction step, and it is exact for the local player.
- Remote input is predicted, almost always by repeating the last input received, which is correct most of the time because held buttons dominate.
- When a remote input arrives and differs from the prediction, the engine loads the saved state for that frame and re-simulates every frame since, applying the now-known inputs. That is the reconciliation step, and it happens inside one frame.
- There is no interpolation and no lag compensation, because there is no separate authority and no snapshot stream.

The tuning knobs are input delay and maximum rollback depth. Adding one or two frames of input delay reduces both the frequency and the depth of rollbacks, at 16 or 33 ms of responsiveness. Capping rollback depth bounds the worst-case frame cost; beyond the cap the engine stalls the local player rather than re-simulating further, so a bad connection degrades into a visible hitch instead of a frame-rate collapse.

Deep rollbacks are visible as remote characters snapping when a prediction was wrong, which is why the model suits games with short, committed animations: a character mid-attack is easy to predict, and a character freely moving is not.

## Latency bands by genre

Claypool and Claypool's model classifies player actions by the precision they demand and the deadline they must meet, and gives tolerance thresholds by class — roughly 100 ms for the precise, deadline-bound actions of a first-person shooter and a racing game, around 500 ms for role-playing and MMO actions, and around 1000 ms for the low-precision, loose-deadline actions of a strategy game. These are the points at which measured player performance degrades, not the points at which the game stops working.

Useful consequences for planning:

- Inside one country, 10–40 ms is realistic; across a continent, 40–90 ms; across an ocean, 120–250 ms. These are physics plus routing, and no amount of netcode changes them.
- A shooter therefore needs regional servers, because a shooter is played at the 100 ms threshold rather than near it.
- An RTS or a turn-based game can be run from one region worldwide.
- Rollback is worth its cost in a fighting game precisely because the genre's actions sit at the strict end of the precision scale, where even one frame of added delay is measurable by players.

## Shipped rates

| Game | Simulation | Network send | Source |
| --- | --- | --- | --- |
| Quake III Arena | `sv_fps` 20 | 20 snapshots per second requested by `snaps`; up to 30 input packets per second from `cl_maxpackets`; `rate` capped at 3000 bytes per second | GPL source, `code/server/sv_init.c` and `code/client/cl_main.c` |
| Valorant | 128 Hz | 128 Hz | Riot Games tech blog, "VALORANT's 128-Tick Servers" |
| Overwatch | 62.5 Hz | 20.8 Hz originally, one tick in three; 62.5 Hz with high bandwidth enabled | Tim Ford, GDC 2017, "Overwatch Gameplay Architecture and Netcode" |
| Rocket League | 120 Hz physics | — | Jared Cone, GDC 2018, "It IS Rocket Science! The Physics of Rocket League Detailed" |
| Rollback fighting game | 60 Hz lockstep | Inputs every frame; no state | GGPO |

The Quake III defaults are worth sitting with, because they are from a game that felt responsive on dial-up: 20 Hz of state, 3 KB/s of bandwidth, and everything else done by prediction and interpolation. Most modern netcode complaints are not solved by exceeding those rates.

## Diagnosing by symptom

| Symptom | Most likely cause |
| --- | --- |
| Local character responds late to every input | No client-side prediction |
| Local character walks forward and is pulled back | Prediction without reconciliation, or a reconciliation tolerance that is too large |
| Local character jitters constantly in place | Corrections applied to the simulation rather than smoothed on the render |
| Remote players move in visible steps | No interpolation, or a buffer smaller than one send interval |
| Remote players glide past a corner then snap back | Unbounded extrapolation |
| Shots visually connect and do nothing | No lag compensation, or a rewind derived from the wrong clock |
| Being shot after reaching cover | Lag compensation working as designed; the rewind cap is the knob |
| Everything is fine until a packet is lost, then a freeze | Reliable ordered delivery used for state |
| Two clients slowly disagree with no correction | A deterministic model without a desync detector |

## Sources

- Quake III Arena source, id Software, GPL — `code/server/sv_init.c`, `code/client/cl_main.c`, `code/server/sv_snapshot.c`.
- "Latency Compensating Methods in Client/Server In-game Protocol Design and Optimization", Yahn Bernier, GDC 2001 — the original written description of prediction, reconciliation and lag compensation as a set.
- Source Multiplayer Networking, Valve Developer Community — `cl_interp`, `cl_interp_ratio` and `cl_updaterate` and how the interpolation period is derived from them.
- "Latency and Player Actions in Online Games", Mark Claypool and Kajal Claypool, Communications of the ACM 49(11), 2006 — the precision and deadline model and the per-class tolerance thresholds.
- "Peeking into VALORANT's Netcode" and "VALORANT's 128-Tick Servers", Riot Games tech blog.
- "Overwatch Gameplay Architecture and Netcode", Tim Ford, GDC 2017.
- "It IS Rocket Science! The Physics of Rocket League Detailed", Jared Cone, GDC 2018.
- GGPO, `github.com/pond3r/ggpo`, MIT — the rollback model and its input-prediction description.
