# Load phases

Read this at steps 2 to 4 of `SKILL.md`.

## Contents

- [The phase table](#the-phase-table)
- [Recording the access order](#recording-the-access-order)
- [Fixes by phase](#fixes-by-phase)

## The phase table

One row per phase; the numbers below are an invented example of a level load on a hard drive.

```text
phase                     cold_s   warm_s   cold/warm   thread
read bytes                 18.0      0.6       30         I/O
decompress                  3.1      3.0        1         worker
deserialise                 4.2      4.1        1         main
instantiate                 2.5      2.4        1         main
GPU upload                  1.1      1.0        1         render
init scripts                1.8      1.8        1         main
shader warm-up              2.0      0.4        5         render
total                      32.7     13.3
```

Reading it: the read row's ratio of 30 says storage dominates the cold run, so packing and compression choice come first. Deserialise and instantiate stay at about 4 and 2.5 seconds warm, so they are the next target once reads are fixed. If the phases overlap on different threads, record the critical path rather than the sum.

## Recording the access order

1. Start from a cold boot of the level.
2. Capture file opens and reads with timestamps: the engine's asset-load trace if it has one, otherwise the OS trace (Windows Performance Recorder, or `strace -f -tt -e trace=openat,read,pread64` on Linux).
3. Reduce the trace to the sequence of first reads per asset.
4. Feed that sequence to the packer so the archive stores assets in that order; rebuild and re-trace to confirm the reads are now sequential offsets.
5. Repeat when the load content changes materially; an order recorded for last year's level is a guess.

## Fixes by phase

| Phase | Typical cause | Fix |
| --- | --- | --- |
| Read bytes | seeks, duplication, tiny files | order by access, de-duplicate, archive |
| Decompress | slow codec on a weak CPU | faster codec, decompress on a worker thread, smaller assets |
| Deserialise | text parsing, reflection | prebuilt binary, off main thread |
| Instantiate | per-object setup, allocation | pools, baked batches, lazy components |
| GPU upload | large textures in one frame | spread uploads over frames, smaller mips first |
| Init scripts | work for areas not yet visible | defer past first frame |
| Shader warm-up | cold shader cache | see `shader-compile-stutter` |
