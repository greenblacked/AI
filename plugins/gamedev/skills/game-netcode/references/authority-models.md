# Choosing the authority model

Read this at step 2, before committing to a model. The choice is load-bearing: it decides the shape of every entity, every message and every test in the game, and changing it later is a rewrite of the simulation rather than a refactor of the network layer.

## Contents

- [The question the model answers](#the-question-the-model-answers)
- [The four models](#the-four-models)
- [Choosing by genre and player count](#choosing-by-genre-and-player-count)
- [The determinism bill](#the-determinism-bill)
- [The rollback bill](#the-rollback-bill)
- [Topology: who runs the simulation](#topology-who-runs-the-simulation)
- [What a migration between models costs](#what-a-migration-between-models-costs)
- [Sources](#sources)

## The question the model answers

Every multiplayer game has to answer one question: when two machines disagree about what happened, which one is right? The authority model is that answer, and everything else — what is on the wire, what the client may compute, what the server must check, what a cheat can achieve — falls out of it.

A second question follows immediately and is easy to miss: what travels, state or input? Server-authoritative games send state downstream and input upstream. Deterministic games send input in both directions and never send state at all. That difference is why bandwidth for a 500-unit RTS can be smaller than for a 10-player shooter, and why the RTS pays for it in determinism instead.

## The four models

**Server-authoritative.** One machine owns the simulation. Clients send input, receive state, and predict locally to hide the round trip. Cheating is bounded by what the server accepts. Server cost scales with concurrent sessions, and every session needs a machine somewhere near the players. This is the default, and the burden of proof is on anything else.

**Client-authoritative.** Each client simulates the entities it owns and broadcasts the result. Nothing to predict, nothing to reconcile, no server to pay for, and no defence at all — a modified client can set its own position, health, score and inventory, and the only recourse is a player kicking someone from a lobby. Legitimate for co-op with friends, jam entries and anything with nothing to win.

**Deterministic lockstep.** Every peer runs the same simulation from the same inputs and reaches the same state without exchanging any state. Only inputs cross the network, so bandwidth is independent of world size — the reason it is the traditional RTS model. The cost is that the simulation must be bit-exact on every platform, compiler and build configuration, and that a peer cannot advance a frame until it has everyone's input for that frame, so the effective input delay is at least the slowest peer's one-way latency. One divergence ends the match for everyone.

**Rollback.** Deterministic lockstep with speculation. A peer predicts the absent remote input (usually by repeating the last one), advances immediately, and when the real input arrives late and differs, restores the saved state from that frame and re-simulates forward to the present inside a single frame. Local input is applied with zero added delay, which is why it is the standard for fighting games. It buys that by requiring cheap complete state save and restore, several times per frame.

## Choosing by genre and player count

| Genre | Players | Model | Why this one |
| --- | --- | --- | --- |
| Competitive shooter, battle royale | 10–150 | Server-authoritative, full latency hiding | Strangers, ranked, money; lag compensation needs a single authority to rewind against |
| Co-op action, survival, sandbox | 2–8 | Server-authoritative on a listen server | Same code as dedicated, and it upgrades to dedicated later without touching the simulation |
| MMO | Thousands per shard | Server-authoritative with aggressive area of interest | Nothing else scales; the interest management is most of the engineering |
| RTS, large-scale simulation | 2–8 | Deterministic lockstep | Sending 2000 unit states at 20 Hz is not affordable; sending 8 orders per second is free |
| Fighting, precise 1v1 action | 2 | Rollback | One frame of added delay is perceptible in the genre; nothing else gives zero local delay |
| Platform fighter, small-count action | 2–4 | Rollback | Same reasoning; rollback cost grows with the number of predicted inputs |
| Racing | 2–24 | Server-authoritative, or client-authoritative with server validation of lap and collision | Vehicles are physics-heavy and predict well; the cheating surface is lap times and collisions |
| Turn-based, card, async | Any | Server-authoritative, no prediction | Latency is invisible between turns; only correctness matters |
| Party game with friends | 2–8 | Client-authoritative, or host-authoritative | The stake is zero, and the simplest thing that works is the right thing |

Two cross-cutting rules. If the game is ranked, monetised, or open to strangers, it is server-authoritative regardless of genre. If the world state is much larger than the input stream and the player count is small, deterministic lockstep deserves a look before anything else.

## The determinism bill

Deterministic models fail silently and late: the divergence happens in one place, propagates, and surfaces minutes later as two players seeing different winners. Every item below has to be true on every platform, compiler and optimisation level you ship.

**Floating point.** Do not assume it. The failure sources, in rough order of how often they bite:

- Fused multiply-add. A compiler is free to contract `a * b + c` into an FMA with a single rounding, giving a different result from two roundings. Disable contraction explicitly (`-ffp-contract=off`, `/fp:precise`) or accept the platform divergence.
- Fast-math. `-ffast-math` and `/fp:fast` permit reassociation and reciprocal approximation. Both make results build-dependent. Neither belongs in a deterministic simulation.
- Transcendentals. `sin`, `cos`, `pow`, `exp` and `atan2` are not specified to the last bit by IEEE 754, and results differ between libm implementations, versions and vector widths. Ship your own table-driven or polynomial implementations for anything inside the simulation.
- x87 versus SSE. 32-bit x86 builds using the x87 stack keep 80-bit intermediates and round differently from SSE2 code. Force SSE2 on 32-bit targets.
- Auto-vectorisation. A vectorised reduction sums in a different order from a scalar one, and floating-point addition is not associative.

The reliable answer for cross-platform determinism is to remove floating point from the simulation: fixed-point arithmetic for positions, velocities and angles, with a fixed-point trigonometry table. It costs range and precision work up front and buys a class of bug that is otherwise unfixable.

**Everything else that diverges.** Iteration order over a hash map keyed by pointer or by insertion; a sort that is not stable applied to equal keys; a random number generator not seeded from the match and stepped identically on every peer; anything reading wall-clock time, frame time or input polling rate inside the simulation; uninitialised memory; entity IDs allocated from a local counter; multi-threaded simulation with non-deterministic scheduling.

**The detector is not optional.** Hash the full simulation state every frame, or every eight frames, and exchange the hash. When the hashes differ, dump both states and the last N frames of input so the divergence can be replayed. Build this before the netcode, not after the first desync report. A deterministic simulation with an input log also gives free replays, free bug reports and free automated soak testing, which is a substantial part of why the model is worth its cost.

## The rollback bill

On top of the determinism bill, rollback needs:

- **Complete state save and restore, cheaply.** Every frame is saved, and on a late input the engine restores and re-simulates. If a save is a deep copy of a large heap graph, this does not fit in a frame. The simulation state wants to be a flat, fixed-size, pointer-free block that can be memcpy'd.
- **Simulation separated from presentation.** Re-simulating eight frames must not spawn eight sets of particles, play eight sounds, or advance the UI. Presentation reads the simulation; it is never part of it.
- **A bound on rollback depth.** Re-simulating an unbounded number of frames inside one frame is not possible. Cap the depth and stall the local player instead when a peer falls further behind, so a bad connection degrades into delay rather than into a frame-rate collapse.
- **A frame-delay knob.** Adding one or two frames of input delay reduces how often prediction is wrong and how deep the rollbacks go, at a directly perceptible cost in responsiveness. It is the main tuning trade in the model, and it is worth exposing per-match based on the measured connection.

GGPO, the library that made this model standard in the genre, is MIT-licensed and readable; its architecture is the reference implementation of the callback shape — save state, load state, advance frame — that a rollback engine has to provide.

## Topology: who runs the simulation

| Topology | Fits | Costs |
| --- | --- | --- |
| Dedicated servers | Anything competitive, anything at scale | A fleet, in every region where players are, plus the deployment and capacity work around it |
| Listen server, one player hosts | Co-op, small sessions, early development | The host has zero latency and everyone else does not; the session ends when the host leaves unless host migration is built |
| Peer-to-peer mesh | Deterministic models at low player count | N-squared connections; NAT traversal for every pair; any peer can drop the session |
| Relay or proxy | Peer models that cannot traverse NAT | Adds a hop of latency; someone pays for the bandwidth |

Two notes that catch people. NAT traversal is not optional for any peer topology: budget for STUN, a TURN relay fallback, and the connections that will still fail. And a listen server gives its host a latency advantage that is invisible in testing and obvious in a competitive match, which is on its own a sufficient reason for dedicated servers in a ranked mode.

Build a listen server as a dedicated server with a local client attached, rather than as a separate code path. That way the upgrade to dedicated hosting is a deployment change, and the single-player build is the same simulation with one client.

## What a migration between models costs

| From | To | Cost |
| --- | --- | --- |
| Client-authoritative | Server-authoritative | The largest. Every entity's update has to move to the server, the protocol changes from state to input, and prediction and reconciliation are new code. Effectively a rewrite of gameplay. |
| Listen server | Dedicated | Small, if the listen server was built as a server plus a local client. Large if the host was special-cased. |
| Lockstep | Rollback | Moderate: determinism is already paid for; the new work is state save and restore and separating presentation. |
| Lockstep or rollback | Server-authoritative | Moderate to large: the simulation is reusable, but the protocol, the prediction and the trust model are all new. |
| Server-authoritative | Lockstep | Large, and rarely worth it: determinism has to be retrofitted to a simulation that never had it, which is the hardest direction. |

The asymmetry is the argument for step 1. Deciding late is fine only in the direction of listen server to dedicated, and only if it was planned for.

## Sources

- Quake III Arena source, `code/server/sv_init.c`, `code/client/cl_main.c`, `code/server/sv_snapshot.c` — id Software, GPL. The server tick, snapshot and input rate defaults, and the delta-snapshot implementation.
- GGPO, `github.com/pond3r/ggpo` — MIT. The rollback callback architecture and the input-prediction description in its README.
- "The TRIBES Engine Networking Model", Mark Frohnmayer and Kevin Gift, GDC 1999 — the ghost manager and prioritised replication, designed against a 28.8 kbit/s modem budget.
- "Overwatch Gameplay Architecture and Netcode", Tim Ford, GDC 2017 — the simulation and send rates, and the ECS the netcode sits on.
