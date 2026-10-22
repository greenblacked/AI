---
name: game-desync-forensics
description: "Find the first frame and the subsystem where two peers of a lockstep or rollback game diverge, from a failed hash check or a bug report. Makes the failure replayable (per-peer input log, match seed, build id, a headless single-process replay), replaces one whole-state hash with a per-subsystem hash tree in a ring buffer, bisects to the first divergent frame and field, classifies the cause from a fixed list, then hashes the missing state and keeps the replay as a regression test on every target. Use for \"our RTS desyncs after ten minutes\", \"rollback match ended with different winners\", \"hash mismatch on frame 41200\", \"desync only on the console build\", \"bisect a desync replay\". Not for choosing the authority model or installing the first hash check, or the bare \"the clients desync\" (game-netcode), steady frame cost (game-performance), or general bugs (debugging)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Game Desync Forensics

The work is done when you can name the first frame two peers disagreed, the subsystem and field that differed, and the category of cause, and a replay that reproduced it now runs as a test on every target platform and passes.

`game-netcode` chooses the model and installs the hash check; this skill is what to do once the check fires. The usual failure is resyncing: the game detects the mismatch, copies one peer's state to the other and carries on. The match survives, the defect ships, and it comes back as an unreproducible "desync after ten minutes" report in a different form each month. A hash mismatch is a precise signal that two machines ran the same inputs and got different answers, and that has only a handful of possible causes, all findable.

## Scope

Use for: a failed state-hash comparison, a rollback or lockstep game ending with different results on different peers, a desync that appears on one platform or build only, and bisecting a recorded replay.

Do not use for: picking lockstep versus a server-authoritative model, the determinism checklist, or the bare complaint that "the clients desync" with no hash or replay in hand (`game-netcode`), a game that is slow rather than divergent (`game-performance`), or a bug unrelated to peers disagreeing (`debugging`).

## Workflow

### 1. Make the failure replayable before reading code

Reading code to guess the cause is slow because the space is the whole simulation. Collect, for the failing match: each peer's input log with the frame each input applied on, the match seed, and the exact build id of every peer (a source revision is not enough when platforms differ; record compiler and flags too).

Then prove a headless, single-process replay reproduces the mismatch: run the simulation twice from the same seed and inputs, in one process, and compare hashes per frame. Three outcomes:

- It diverges: the simulation is non-deterministic against itself. Continue to step 2 for the per-subsystem hashes, then bisect in step 3; step 2 can be skipped only if a hash tree already exists.
- It matches, but the two peers' builds differ in platform or flags: the cause is a cross-platform difference. Replay the same logs on each target build and compare against each other.
- It matches on every build you can run: the cause is outside the simulation as defined, such as uninitialised memory, a wall-clock read, thread timing, or an input that was recorded differently from the one the peer applied. Look at what feeds the sim, not the sim.

Do not continue to step 2 until a reproduction exists. A desync you cannot replay cannot be shown to be fixed.

### 2. Replace the single hash with a hash tree

One hash of the whole state says only that something differs. Hash each subsystem separately every frame: RNG state, entities, physics, pathing, economy, and any other system that mutates simulation state. Log the tree per frame to a ring buffer holding the last few hundred frames and dump it on mismatch, so a production desync arrives with its own evidence. Keep the hash cheap enough to run every frame in release builds (a non-cryptographic hash over the serialised state is enough); the cost of a tree is far below the cost of a desync you cannot localise.

Read `references/hash-tree-and-bisection.md` for the layout, the ring-buffer dump and what to log beside each hash.

### 3. Bisect to frame, subsystem, field

With the replay and the tree:

1. Find the first frame whose full-state hash differs between the two runs. If hashes are logged every frame this is a scan; if they are logged every N frames, bisect between the last equal checkpoint and the first differing one by replaying with the hash on every frame.
2. In that frame, find the first subsystem hash that differs. If several differ, take the one that runs earliest in the tick, because later ones inherit its error.
3. Serialise that subsystem's state on both sides and diff it field by field. The first differing field and entity is the answer or points directly at it.

Treat "first" strictly. A divergence found at frame 41200 may have started at frame 41197 in a field that was not yet hashed; if the earliest differing subsystem looks innocent, look for state outside the hash (step 4).

### 4. Classify the cause

Pick from this list; each has a distinct fingerprint and fix.

| Cause | Fingerprint | Fix |
| --- | --- | --- |
| Float or compiler difference between platforms | Same-platform peers agree, cross-platform ones do not; tiny low-bit differences first | Fixed-point or deterministic maths library, pinned compiler flags (disable fast-math and fused multiply-add contraction), no platform maths intrinsics in the sim |
| Unordered container iteration | Same build differs between runs; order of entities or events differs | Iterate in a defined order (sorted by stable id) |
| Unstable sort on equal keys | Two equal-priority entities swap | Add a unique tiebreaker to the comparator |
| RNG drawn from presentation code | Peer with different frame rate, effects setting or window focus diverges | Separate RNG streams: one for the sim, one for cosmetics |
| Uninitialised field | Differs between runs of one build; may differ only after memory reuse | Initialise at construction; run with memory sanitisers on the headless replay |
| State outside the hash | Hashes match for frames after the real divergence, then a hashed field goes wrong | Add it to serialisation and the tree |
| Dropped or reordered input | Input logs disagree on frame or order | Fix the input protocol, not the sim; check the frame an input is stamped with |

Anything that does not fit usually turns out to be a combination, or a thread-timing issue in code the sim calls: check for threads reading or writing sim state, and for any read of wall-clock time.

### 5. Close it properly

Add the missing state to the hash so the same class cannot hide again. Keep the failing replay as a regression test that runs the simulation on every target platform build in CI and compares hashes across them; a fix verified on only the platform that was easy to debug on will fail on the one that was not. Resyncing state and moving on hides the defect and ships it: if a resync mechanism exists for resilience, it must log loudly and count occurrences, and a nonzero count in testing is a bug.

## Hand back

Replay artefacts (inputs, seed, build ids) and where they are stored; first divergent frame, subsystem and field; the category from step 4 with the evidence; the fix; the hash coverage added; and the CI job that now runs the replay on each platform. If no cause was found, hand back what was ruled out and the narrowest region still open.

## Anti-patterns

**Resyncing instead of diagnosing.** It converts a loud, local defect into a quiet one that surfaces as lost player trust.

**Logging only the final hash.** A hash taken at the end of a match, or every few hundred frames, forces a long bisect for every report.

**Testing the fix on one platform.** Float and compiler differences are the bug on the platform you did not test.

**Blaming the network.** The inputs are the only thing the network carries in a deterministic game. If the input logs agree, the network is not the cause.

## References

- `references/hash-tree-and-bisection.md` - read at steps 2 and 3: tree layout, ring-buffer dump, bisection loop and the field diff.
