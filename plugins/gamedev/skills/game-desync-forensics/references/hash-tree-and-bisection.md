# Hash tree and bisection

## Contents

tree layout, what to log, ring-buffer dump, the bisection loop, the field diff, regression test shape

## Tree layout

Per frame, after the tick completes, record:

```text
frame, build_id, rng_hash, entities_hash, physics_hash, pathing_hash, economy_hash, input_hash, full_hash
```

- `full_hash` combines the subsystem hashes in a fixed order. A mismatch in it with all subsystem hashes equal means the combine step or an unhashed subsystem is at fault.
- `input_hash` covers the inputs applied on that frame. If it differs, the cause is the input protocol and the simulation is not at fault.
- Order the subsystem hashes by the order they run in the tick, so "earliest differing" is the leftmost column.
- Hash serialised state, not raw memory: padding and uninitialised bytes in a struct make memory hashes differ for no real reason.

## Ring buffer

Keep the last 256 to 1024 frames of tree rows in memory per peer. On mismatch (detected by exchanging `full_hash` per frame or per few frames), write the buffer to disk together with the build id, the seed and the input log. The buffer is small, so leaving it on in release builds costs little, and it is the difference between a bug report with evidence and one without.

## Bisection loop

```text
good = last frame at which both peers' full_hash agreed
bad  = first frame at which they differ
while bad - good > 1:
    mid = (good + bad) // 2
    replay both runs to mid, compare full_hash
    if equal: good = mid else: bad = mid
first_divergent_frame = bad
```

If tree rows exist for every frame, skip the loop and scan. If you can only replay (not read logs from the field), the loop needs a replay that can fast-forward to a frame deterministically; add periodic state snapshots to the replay so each probe costs seconds rather than a full match.

## Field diff

At the first divergent frame, dump the earliest differing subsystem on both sides in a stable text form: entities sorted by id, fields in declaration order. Diff the two files with an ordinary text diff. Read the first differing line, then ask what ran just before it in that tick. Differences in the least significant digits of a float point to platform maths; a wholly different value points to order or uninitialised state.

## Regression test shape

1. Store the failing inputs, seed and expected per-frame `full_hash` list in the repository (or a test-data store if large).
2. A test per target platform build replays the inputs headlessly and compares its hash list with the expected one.
3. Also run a cross-platform comparison job: replay on each target and compare the hash lists against each other, not only against a stored file, so a new divergence between platforms is caught even when the stored list was recorded on one of them.
4. Run it on every change to simulation code, not nightly: determinism breaks one commit at a time and a nightly run leaves a day of suspects.
