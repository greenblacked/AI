---
name: field-failure-triage
description: "Work out why deployed units are failing, going silent or coming back, and decide containment: read flash, faults and battery state of a returned unit before reflashing; scope a silent cohort by last-seen (a step at one timestamp points at cloud, certificate, DNS or release, so check broker and auth logs first; a slope at batteries); classify each unit as firmware, component or assembly, environment or use; compute failure rate over units in the field by version, revision, lot, line, carrier and region one dimension at a time; read the age-at-failure curve; swap-test; contain first. Use for \"return rate is up\", \"batteries dying early in one batch\", \"is this firmware or hardware\", \"40 RMAs with the same symptom\", \"2,000 devices went offline overnight\". Not for incident review (postmortem), live outage (incident-response), one crash (hard-fault-triage), one bench unit (brick-recovery)."
allowed-tools: Read, Glob, Grep
---

# Field Failure Triage

A field failure is triaged when the affected population is bounded, every examined unit is classified, the failure rate is compared across the dimensions that differ, one hypothesis has survived a bench test that could have refuted it, and containment has been decided without waiting for the root cause.

The usual failure is acting on the first plausible story. A return rate rises, someone blames the latest firmware, the fix ships, and the rate keeps rising because the cause was a capacitor lot. Or a fleet goes quiet, an engineer reflashes a returned unit and erases the only evidence, or a failure count is compared with no denominator and the biggest firmware version looks guiltiest because it has the most units. Order and denominators prevent most of this.

## Scope

Use for: rising returns or RMAs, a cohort of units that stopped reporting, early battery death in some units, and the question of whether a fault is firmware or hardware.

Do not use for: reviewing an incident after it ended, which is `postmortem`; a live outage of a service, which is `incident-response`; decoding a single crash, which is `hard-fault-triage`; reviving one unit on the bench, which is `brick-recovery`; a broker-side connect failure once the cause is located, which is `mqtt-session-debug`.

## Workflow

### 1. Preserve before fixing

On any returned or failed unit, read everything before touching it: dump flash, read the fault record and reset reason, pull the logs and counters, record the battery voltage and any state, and photograph the board and its marks. Do not reflash, factory reset or power-cycle first, because the evidence lives in state those actions destroy. Log the unit's serial, lot and date code, firmware and hardware revision, and the customer's description in their own words. A unit that works after a power cycle has still told you something; record that too.

### 2. Scope the population

State the problem as a count and a denominator before any theory: how many units failed, out of how many in the field, over what period. For a silent cohort, plot the last-seen time for the silent units, where silent means two missed check-in intervals for that fleet rather than a fixed day.

- A step, many units going quiet at one timestamp, points to something shared and central: a cloud or broker change, an expired certificate, a DNS change, a release, a carrier event. Check the broker and authentication logs for that moment before touching any device.
- A gradual slope, units going quiet one after another, points to batteries, attrition or wear-out.
- A cluster by region or carrier points to the network.

Do not sample devices until the central explanations are excluded; they cost minutes to check and they are common.

### 3. Classify each unit

Put every examined unit into one class from a fixed taxonomy, and keep the count by class:

- Firmware: a reproducible logic fault, a crash, a corrupt update.
- Component or assembly: a part out of tolerance or failed, a solder joint, a mis-assembled board.
- Environment: ESD, moisture, temperature, battery chemistry or discharge.
- Use: misuse, wrong installation, a feature used outside its design.

Unclassified is a legitimate class and should be kept visible rather than forced into another. Read `references/failure-taxonomy.md` for the signs that separate the classes and the evidence to record.

### 4. Correlate, one dimension at a time

Compute the failure rate for each value of a dimension, using the number of units in the field in that bucket as the denominator, not the total failures or the total fleet. Go through, separately: firmware version, hardware revision, lot or date code, contract-manufacturer line, carrier, region, and time in service. Looking at one dimension at a time keeps a confound from hiding: a bad lot that shipped only with one firmware version makes the firmware look guilty. When two dimensions both separate failures, cross them and compare rates inside each cell. Read `references/correlation-queries.md` for the queries and for small-sample cautions.

### 5. Read the age-at-failure curve

Plot failures by time in service for the affected group.

- An early cluster, failing within the first days or weeks, points to a batch defect, such as a bad lot or assembly problem.
- A steady rate through life points to a design flaw or a random cause.
- A rising rate points to wear-out: batteries, flash, connectors, seals.

The shape selects the hypotheses worth a bench test.

### 6. Reproduce with a swap test

On the bench, take a failing unit and a good one and exchange the suspect pieces one at a time: board, battery, firmware, and where relevant the enclosure or the sensor. The failure follows the part that is at fault. Run it with the original state first, since a reflash can hide the fault. If swapping the firmware does not move the failure, it is not the firmware; if swapping the battery does, the next question is the lot. Write the prediction before the test so the result can refute it.

### 7. Decide containment before the root cause

Waiting for a certain cause while units keep shipping or failing is a choice. Decide the containment that is cheap and reversible: hold the suspect lot, stop shipping a hardware revision, pause the rollout of a firmware, or apply a server-side fix that needs no device reachability, such as extending a keepalive on the broker or, only as a last resort, relaxing a server-side certificate check. Relaxing a check is time-boxed with an expiry date, logged, and needs a security owner's sign-off. It stays consistent with `device-trust-anchors`, which rules out disabling certificate validation to get past a clock or trust problem, so the relaxation applies to the server's own checks of a peer and never to a device's validation of the server. Record what is held and what evidence would release it.

### 8. Verify against the next lot

After the fix or the containment, check it against the next lot or the next period: the failure rate in the new group, with its denominator, should move. A fix that cannot be seen in the next lot's numbers has not been shown to work.

## Hand back

The problem statement with count and denominator, the scoping result, the classification table, the correlation results by dimension, the age curve reading, the swap test and its prediction and result, the containment decision and what releases it, and the verification plan for the next lot.

## Anti-patterns

**Fixing the unit first.** The reflash erases the fault record.

**Counting failures, not rates.** The largest group always looks worst.

**Blaming the newest firmware.** It is the easy story and often the wrong one.

**Waiting for root cause to contain.** Units keep failing meanwhile.

## Reference files

- `references/failure-taxonomy.md` - read at step 3: the signs that separate firmware, component, environment and use, what to record for each, and the return inspection checklist.
- `references/correlation-queries.md` - read at steps 2 and 4: last-seen distribution and rate-by-dimension queries, the age curve, and cautions for small samples.
