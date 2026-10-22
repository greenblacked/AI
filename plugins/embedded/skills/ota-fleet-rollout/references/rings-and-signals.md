# Rings and signals reference

## Contents

- Cohort table
- Ring plan example
- Halt signal definitions
- Pause rehearsal checklist

## Cohort table

| Cohort | Hardware rev | Carrier | Region | Check-in | Power | Devices |
| --- | --- | --- | --- | --- | --- | --- |
| A | rev B | carrier 1 | EU | 1 hour | mains | 12,000 |
| B | rev B | carrier 2 | NA | 1 day | battery | 8,000 |
| C | rev C | carrier 1 | NA | 1 week | battery | 3,000 |

The slowest cohort (C, weekly) sets the minimum bake for any ring that includes it.

## Ring plan example

For a fleet of 23,000 devices:

| Ring | Devices | Composition | Bake |
| --- | --- | --- | --- |
| 0 | about 20 | lab rigs, one or more per revision, carrier and region | until the test suite and a soak pass |
| 1 | about 50 | staff units | three daily intervals |
| 2 | about 25 (0.1 per cent) | at least a handful from each cohort, all of the smallest | three intervals of the slowest cohort in it |
| 3 | 230 (1 per cent) | proportional, minimum per cohort | same rule |
| 4 | 2,300 (10 per cent) | proportional | same rule |
| 5 | 11,500 (50 per cent) | proportional | same rule |
| 6 | the rest | remainder | until the campaign closes |

If cohort C has 3,000 devices and a weekly interval, ring 2 needs to hold C devices as well as a daily reporter, so ring 2 bakes for three weeks; to avoid that, trigger a forced check-in on the C devices in the early rings.

## Halt signal definitions

| Signal | Source | Compare with | Example halt rule (set your own) |
| --- | --- | --- | --- |
| Check-in rate after update | server | control cohort, same revision | fewer than the control by more than the threshold after two intervals |
| Rollback count | bootloader report | zero expected | any in the early rings |
| Boot loops | bootloader or reset counter | zero expected | any in the early rings |
| Reset reason mix | device telemetry | control | rise in watchdog or brownout share |
| Battery drain delta | telemetry | control | beyond the margin you can tolerate |
| Silent devices | server, against target set | expected misses | above the baseline missed-check-in rate |

The thresholds are examples; derive them from the control cohort's normal variation before the campaign.

## Pause rehearsal checklist

- Where is the switch, and who may flip it out of hours?
- How long until the server stops serving the image, including cached copies at the CDN?
- What do devices in the middle of a download do?
- What is the rollback version number, and has the rollback build been tested on a unit running the new version?
- Who tells support and the customer teams?
