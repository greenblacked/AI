# Unit failure report

One failing unit, from the first failed attempt to the proof that the fix holds across a
reboot. Fill in every field; delete the guidance in brackets.

## Unit

- Unit and host: [name.service, hostname or environment]
- Package or source of the unit file: [vendor path, or /etc/systemd/system]
- First failed attempt: [timestamp from the journal]

## Failure

- Result: [exit-code / signal / timeout / start-limit-hit / oom-kill / resources]
- Exit status and meaning: [e.g. 203/EXEC: ExecStart binary missing or not executable]
- Deciding journal line: [quote it, with its timestamp]

## Cause

[One sentence, with the property or line that shows it.]

## Fix

- Drop-in path: [/etc/systemd/system/UNIT.d/override.conf]
- Contents: [the lines added or changed]

## Proof

| Check | Result |
| --- | --- |
| `systemd-analyze verify UNIT` | [clean / findings] |
| Stop then start, `systemctl is-active UNIT` | [active / failed] |
| `NRestarts` and `Result` after the start | [values] |
| Comes up on its own after a reboot | [yes / no / not permitted] |
| `systemd-analyze critical-chain UNIT` | [ordering as expected / finding] |

## Follow-up

[Anything left open, with an owner: a vendor bug report, a change to the deploy tooling.]
