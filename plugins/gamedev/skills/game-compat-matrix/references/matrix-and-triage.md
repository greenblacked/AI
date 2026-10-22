# Matrix and triage

Read this at steps 1, 2 and 4 of `SKILL.md`.

## Contents

- [Installed-base table](#installed-base-table)
- [The matrix](#the-matrix)
- [The isolation log](#the-isolation-log)
- [Minimal repro for a vendor](#minimal-repro-for-a-vendor)

## Installed-base table

One row per family, refreshed each quarter. The values are invented examples.

```text
family            vendor   driver_range      share_pct   crash_per_1000   source
RTX 30 series     NVIDIA   5xx.x - 5yy.y        18          1.2          telemetry
RX 6000 series    AMD      24.x - 25.x           7          3.9          telemetry
Intel Xe iGPU     Intel    31.0.101.x            9          6.1          telemetry
GTX 10 series     NVIDIA   older                11          2.0          survey
```

Rank by expected crashes, `share_pct` times `crash_per_1000`, which weighs share and pain together; the Intel row above (9 times 6.1) outranks the NVIDIA 30 series row (18 times 1.2) despite its smaller share.

## The matrix

```text
cell  device                  role                         last_build  smoke   notes
A1    low-end desktop, GTX    minimum spec                 7731        pass
A2    mid desktop, RTX        most popular                 7731        pass
B1    AMD 6000 series         one per vendor               7731        FAIL    black screen after alt-tab, link
B2    Intel Xe laptop         history of rendering bugs    7731        pass
C1    mid Android, 4 GB       mobile popular               7731        not run  device farm slot
```

The `role` column is the reason the cell exists. A cell with no stated role is a candidate for removal.

## The isolation log

```text
case: black screen after alt-tab on B1
build: 7731   os: build id here   driver: version here
1  older driver (version)      -> still fails
2  newer driver (version)      -> passes
3  other graphics API          -> passes
verdict: follows the driver version; workaround: reset swap chain after focus loss on driver range; vendor report filed
```

Run each step alone; changing two things makes the result unreadable.

## Minimal repro for a vendor

A small program or captured frame that reproduces the fault with: hardware and driver version, the API calls or shader involved, expected and actual output, and the first driver version where it appears or the last where it works. Strip everything not needed to trigger the fault, and check the repro on a second machine before sending.
