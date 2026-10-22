---
name: ota-fleet-rollout
description: "Run a staged firmware campaign across devices that check in rarely and cannot be recalled: rings sized as device counts across every hardware revision, carrier and region (lab, staff, 0.1 per cent, 1, 10, 50, 100), bake time counted in check-in intervals of the slowest cohort, halt signals written first (check-in rate, bootloader rollback and boot-loop counts, crash rate, battery drain) against a held-back control cohort, absentees counted against the target set, pause by stopping the image, rollback as a new higher version, and low-battery devices skipped. Use for \"roll out 2.4 to the fleet\", \"how long should the canary bake for sleepy devices\", \"pause the OTA, check-ins are dropping\", \"which devices first\". Not for web canaries (release-strategy), app-store phased release (mobile-release), on-device update mechanics (ota-update-safety) or a bricked unit (brick-recovery)."
allowed-tools: Read, Glob, Grep
---

# OTA Fleet Rollout

Done means the new firmware reached the target set ring by ring, every ring was held until enough check-in intervals had passed to see a failure, the halt rules were written before the first device updated, and the devices that never reported back were counted as failures, not ignored.

The usual failure is borrowing the web rollout: one per cent, wait an hour, look at the error rate. A sleepy device checks in daily or weekly, cannot be recalled, and the failure that matters most is silence, which an error-rate dashboard cannot show because a dead device sends no errors.

## Scope

Use for: planning and running a staged firmware release across a deployed fleet; choosing rings, bake times and halt signals; deciding to pause; deciding order and eligibility.

Do not use for: canaries for web services (`release-strategy`); app-store phased release (`mobile-release`); the on-device slot, signature and rollback mechanics (`ota-update-safety`); reviving a single dead unit (`brick-recovery`).

## Workflow

### 1. Describe the fleet as cohorts

Build the table of the target set by hardware revision, bootloader version, current firmware, carrier or network, region, power source and check-in interval. A bare percentage of the fleet can land entirely on one revision and tell you nothing about the others. Mark the slowest cohort by check-in interval, because it sets the pace. Read `references/rings-and-signals.md` for the cohort table and a ring plan.

### 2. Define the rings as device counts

Order: lab rigs covering every hardware revision, staff and friendly units, then about 0.1 per cent of the fleet, then 1, 10, 50 and 100 per cent. Each ring must hold enough devices from every revision, carrier and region that a defect specific to one can show; for a small cohort take all of it early rather than a fraction. A ring that is small in percentage terms may still be big enough in absolute terms to fail loudly, and state both.

### 3. Count the bake in check-in intervals

A ring has baked only after enough check-in intervals of its slowest cohort have passed for every device in it to have reported at least a few times. A daily reporter needs at least three days per ring. For a weekly reporter the first ring takes weeks; if that is unacceptable, put fast-reporting devices into the early rings, or use a forced check-in, instead of shortening the bake.

### 4. Write the halt signals before starting

Decide in advance, and write down with thresholds:

- Post-update check-in rate within two check-in intervals, against the expected rate.
- Rollback and boot-loop counts reported by the bootloader on the next successful contact.
- Reset-reason and crash rate by reason, including watchdog resets.
- Battery drain delta over the same period.
- Support contacts and field reports, as a late signal.

Compare each against a held-back control cohort of the same hardware revision that has not been updated, which separates the update's effect from a weather event, a carrier outage or a cloud change. A rule decided after seeing the data bends to what the data shows.

### 5. Count absentees against the target set

The failure to fear is the device that updated and never reported again. Measure by the target set: of the devices in the ring, how many have reported on the new version, how many on the old, how many not at all since the start. Silence beyond two expected intervals is a failure signal on its own. Never compute the health of a ring from the devices that responded; that is the survivors' view.

### 6. Pause and roll back correctly

Pause by making the server stop handing out the image. Devices that already took it cannot be recalled, and those mid-download finish or fail according to the on-device mechanics. Rollback is a new release with a higher version number, because anti-rollback protection refuses an older version number; build it as the next forward version containing the known-good code. Rehearse the pause once before the campaign: which switch, who flips it, and how fast it takes effect on the server and the CDN.

### 7. Choose who goes first and who is skipped

Prefer devices that are plugged in, on good networks, idle and easy to reach, early; leave critical-site or hard-to-reach devices for late. Skip a device that is on low battery, mid-operation (recording, treating, driving), or roaming on a metered network; it keeps its slot in the queue. Stagger downloads over time so that a whole ring does not hit the CDN at once and so a roaming data plan is not billed for a thousand simultaneous images.

### 8. Close the campaign

Report the final state by cohort: updated, held, skipped and why, silent. List the devices not on the target version with a reason and an owner, rather than leaving the campaign open indefinitely.

## Output format

```markdown
## Cohorts
[Revision, carrier, region, interval, count.]

## Rings
[Ring, device count by cohort, bake in intervals, gate.]

## Halt signals
[Signal, threshold, control cohort.]

## Pause and rollback
[Switch, owner, rehearsal date, rollback version.]

## Status
[Updated, held, skipped, silent, with counts.]
```

## Anti-patterns

**Judging a ring by responses.** The healthy-looking set is the one that survived. Count the silent.

**A bake in hours for a device that reports daily.** The first meaningful data arrives after the first interval; an hour proves only that the server serves a file.

**Rolling back to the old build.** Anti-rollback refuses it; ship a new higher version.
