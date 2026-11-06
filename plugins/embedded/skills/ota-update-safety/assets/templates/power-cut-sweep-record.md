# Power-cut sweep record

<!-- One record per update release. Copy, fill in, keep with the release. How to run the sweep is in references/power-cut-sweep.md. -->

Release: <version>  Hardware: <board and revision>  Date: <date>  Harness: <relay and firmware build>

## Flash writes on the update path

| # | Write (what, offset, length) | Cut point tried (offset into write) | Boot outcome after reboot | Slot state after reboot (A / B / flag) | Pass |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

Every write on the path has a row, and each row has more than one cut point: before, inside and after the write.

## Sign-off

- Trial confirm: the new image is confirmed only after the health check; a cut during the trial rolled back to the old image. Signed: <name, date>
- Anti-rollback counter: raised only after confirmation; a cut before confirmation left the old image bootable. Signed: <name, date>

## Failures and fixes

What failed, the fix, and the sweep run that showed it fixed.
