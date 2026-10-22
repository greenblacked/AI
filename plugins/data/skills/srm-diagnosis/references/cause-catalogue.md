# Cause catalogue

Each row: the signal that points at the cause, the check that confirms it, and the fix. Work the first five in order; the rest are less common but cheap to rule out once the five are clear.

| # | Cause | Signal | Confirming check | Fix |
| --- | --- | --- | --- | --- |
| 1 | Bot filtering by arm | Ratio fine before the bot filter, off after; treatment adds clicks, requests or a new endpoint | Unit counts per arm before and after the filter; which filter rule removes the extra units | Make the rule arm-blind or exempt the new behaviour; or filter bots at assignment, before arms exist |
| 2 | Redirect or slower load | Exposure-to-first-event drop-off higher in one arm; worse on slow devices or networks | Drop-off per arm by device class or connection type; page timing per arm | Serve the variant without a redirect; fire exposure server-side at assignment; fix the slow path |
| 3 | Cache or CDN serving | Served variant does not match assigned arm on some requests; skew by region or edge | Join served-variant logs to assignments per request; inspect the cache key | Include the arm in the cache key, or assign before the cache and vary on it |
| 4 | Triggering depends on treatment | Mismatch appears only after the trigger filter; trigger is a component or page only one arm reaches as often | Recompute the trigger at a point both arms pass identically; log a counterfactual trigger in control | Move the trigger to a point upstream of the change, logged identically in both arms |
| 5 | Logging loss on one arm | Server exposure balanced, client events not; skew by app version or browser | Server-side exposure count against client event count per arm; client crash or flush errors | Fix the event in the new code path; key the readout on server-side exposure |
| 6 | Allocation changed mid-run | Ratio breaks on the day of a ramp; sticky assignment keeps early units | Experiment change log against the daily ratio | Analyse only a window with constant allocation, or rerun at fixed allocation |
| 7 | Overlapping experiments | Mismatch correlates with assignment in another test | Cross-tabulate arms of the two tests; check whether they share a salt | Independent salts per test, or mutually exclusive layers |
| 8 | Identity merging | Units move arm when anonymous ids merge into a logged-in id | Count units seen in both arms; trace merges per arm | Randomise on the id that survives the merge, or freeze arm at first assignment |
| 9 | Assignment bug | Ratio already off at assignment | Re-hash a sample of unit ids offline and compare with logged arms | Fix the hash or eligibility code; run an A/A test before the rerun |
| 10 | Arm-dependent crashes or errors | Error rate higher in one arm; units vanish after exposure | Error and crash rate per arm around exposure | Fix the defect; it is also a guardrail finding in its own right |

## Why not reweight

Reweighting the arms back to the designed ratio assumes the lost units resemble the ones that stayed. Every cause above removes units for a reason related to their behaviour or environment — slow devices, heavy clickers, users who bounce — so the remaining treatment population differs from the remaining control population in ways that also move the outcome. The direction of the resulting bias depends on who was lost, and nothing in the data says how large it is.

## What to tell the owner

Two lines: the test is blocked and why, and the date the rerun can start once the fix ships. Avoid quoting the original effect at all; a number mentioned once with a caveat is repeated later without it.
