---
name: scheduled-job-debugging
description: "Find out why a cron job or systemd timer did not run, ran twice or behaves differently than by hand. Prove it was scheduled and started before touching the script: grep CRON in the journal, systemctl list-timers, systemd-analyze calendar to validate the expression. Then the causes in order: cron's minimal environment (PATH, no profile), unescaped percent signs in a crontab line, wrong owner, mode or missing trailing newline in /etc/cron.d, timers without Persistent= after downtime, DST and timezone jumps. Wrap in flock -n against overlap, log stdout and stderr explicitly, add a dead-man check-in. Use for \"works in my shell but not at 3am\", \"timer never fires\", \"job overlaps itself\". Not for long-running services (systemd-unit-failure), pipeline schedules (ci-triage) or what should page (alert-design)."
allowed-tools: Bash(systemctl status:*), Bash(systemctl show:*), Bash(systemctl cat:*), Bash(systemctl list-timers:*), Bash(systemctl list-dependencies:*), Bash(systemctl is-enabled:*), Bash(systemctl is-active:*), Bash(systemctl --failed), Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(systemd-analyze calendar:*), Bash(crontab -l), Bash(ls:*), Bash(stat:*), Read, Glob, Grep
---

# Scheduled Job Debugging

This skill is done when you can say which of three things happened (never scheduled, scheduled but never started, started and failed), the cause is fixed, the job has run once at its real time under the real scheduler, and a missed run will now be noticed by something other than a person.

The usual failure is debugging the script first. A job that "does not work from cron" is most often a job cron never started, or started with a different PATH, shell, user and working directory than the shell the author tested in. A close second is calling the job fixed because it worked when run by hand, which proves nothing about the scheduler.

## Scope

Use for: a cron entry or systemd timer that did not fire, fired at the wrong time, fired twice, overlapped itself, or ran and produced a different result from a manual run.

Do not use for: a long-running service that fails or restarts (`systemd-unit-failure`); a schedule in a CI pipeline (`ci-triage`); deciding what should page when a job is silent (`alert-design`); a wrong system clock (repair the time source separately).

## Workflow

### 1. Establish which of the three it is

Do not read the script yet. Find the scheduler's own record of the run.

For cron, the daemon logs each start with the user and command:

```bash
journalctl -u cron --since "yesterday" | grep CRON      # Debian and Ubuntu unit name
journalctl -u crond --since "yesterday" | grep CROND    # RHEL family unit name
grep CRON /var/log/syslog                               # where the journal is not used
```

A `CMD (...)` line at the expected minute means cron started it, so the cause is inside the run. No line means cron never started it: go to step 2. A line followed by `(CRON) error` or a PAM failure means it was refused.

For a timer, look at the timer and the service it triggers as two objects:

```bash
systemctl list-timers --all --no-pager
systemctl status NAME.timer NAME.service --no-pager -l
journalctl -u NAME.service --since "yesterday" --no-pager
```

`list-timers` shows NEXT and LAST. A timer showing NEXT `n/a` is inactive and needs `systemctl enable --now NAME.timer` (the timer, not the service); a timer absent from the list is not loaded at all. A timer whose LAST never changes is waiting on something; read the next step.

If the answer is still unclear, the output can have gone to a mailbox with no MTA behind it. Cron mails stdout and stderr to the owner or `MAILTO`; with no mail system installed that output is discarded. Redirect explicitly (step 5) before concluding there was no error.

### 2. Validate the schedule expression

A schedule that parses is not a schedule that means what you wrote.

```bash
systemd-analyze calendar "Mon..Fri *-*-* 03:30:00"
systemd-analyze calendar --iterations=5 "*-*-01 02:00"
```

The output gives the normalised form and the next elapse times, in local time and UTC. For a timer, check the same `OnCalendar=` string that is in the unit (`systemctl cat NAME.timer`). For cron there is no equivalent validator in the base system; reread the five fields, and remember that day-of-month and day-of-week are ORed in classic cron when both are restricted, not ANDed.

### 3. Walk the cron causes in order

Read `references/cron-and-timer-causes.md` for the full checklist and the exact log lines each cause leaves. The order matters because the early ones silently remove the whole entry.

1. **The file is not read.** In `/etc/cron.d` the file must be owned by root, not writable by group or other, and its name must use only letters, digits, underscores and hyphens on Debian-family systems (a dot in the name means it is skipped). Every line needs the user field, which a per-user crontab does not have. The last line must end in a newline or it is ignored.
2. **The daemon refuses the user.** Check `/etc/cron.allow` and `/etc/cron.deny`, and the account's state. A locked or expired account or a PAM restriction stops the job without running it.
3. **The percent sign.** In a crontab line an unescaped `%` is turned into a newline and everything after it becomes standard input. `date +%F` must be written `date +\%F`. This is the commonest reason a job that works in a shell fails only from cron.
4. **The environment.** Cron runs the command with `SHELL=/bin/sh`, a short PATH (typically `/usr/bin:/bin`), the user's home as working directory and no profile. Set `PATH=` and `SHELL=` at the top of the crontab or use absolute paths, and do not use `source`, arrays or other shell-specific syntax unless `SHELL=/bin/bash` is set.
5. **Time.** Local time jumps at DST: a job set inside the skipped hour may not run, and one in the repeated hour may run twice, depending on the implementation. Move critical jobs out of the 01:00 to 03:00 window or schedule them in UTC (`CRON_TZ=UTC` where the cron supports it, `OnCalendar=... UTC` for timers). Confirm the zone with `timedatectl`.

### 4. Walk the timer causes in order

1. **Wrong unit pairing.** A timer starts the service of the same name unless `Unit=` says otherwise. A typo means a timer that elapses and starts nothing.
2. **Missed runs after downtime.** A calendar timer without `Persistent=true` skips an elapse that happened while the machine was off or the timer stopped. With it, systemd runs the missed job once at the next start.
3. **Monotonic timers that never elapse.** `OnUnitActiveSec=` counts from the last activation, so it needs an initial trigger such as `OnBootSec=` or `OnActiveSec=` to start at all.
4. **Jitter and accuracy.** `AccuracySec=` defaults to one minute and `RandomizedDelaySec=` adds a spread on purpose, so a "03:00" timer may fire a minute or more later. That is by design, not a fault.
5. **The service fails on start.** A timer is healthy while its service is failed. Read `systemctl status NAME.service`; the service half follows `systemd-unit-failure`.

### 5. Reproduce under the scheduler's environment

A manual run in your shell is not a reproduction. Strip the environment to what the scheduler supplies:

```bash
env -i SHELL=/bin/sh PATH=/usr/bin:/bin HOME=/home/USER LOGNAME=USER \
  /bin/sh -c 'cd ~ && /opt/app/bin/nightly-report'
```

For a timer, ask systemd to run the service exactly as the timer would, then read the result:

```bash
systemctl start NAME.service
systemctl show NAME.service -p Result,ExecMainStatus
journalctl -u NAME.service -n 50 --no-pager
```

Diffing `env` printed from inside the job against `env` in your shell usually names the cause in one step. For a cron entry, temporarily add `* * * * * env > /tmp/cron-env.txt 2>&1` under the same user, wait a minute, read the file and remove the line.

### 6. Fix it so it cannot fail silently again

- **Overlap.** Take a lock that fails fast, so a slow run does not stack on the next: `flock -n /run/lock/NAME.lock /opt/app/bin/job`. A systemd service of `Type=oneshot` already cannot overlap itself, because a second start waits for the first.
- **Output.** Send stdout and stderr somewhere that outlives the run: `>> /var/log/NAME.log 2>&1`, or run it as a service so the journal keeps it. Do not rely on mail.
- **Exit status.** The job must exit non-zero on failure, and a wrapper such as `set -Eeuo pipefail` in a shell script is what makes that true. For a service, `OnFailure=` can start a notifier unit.
- **Dead-man check-in.** Failure signals cannot report a job that never started. End the job with a request to a check-in endpoint that expects a ping every N hours and alerts when one is missing, sent only after success. What that alert pages on and who answers is `alert-design`.

### 7. Prove it under the real scheduler

Do not close on a manual run. Wait for, or temporarily move, one real elapse and read the record from step 1 again: the `CMD` line or the service's `Result=success`, the log file written, the check-in received. For a fix about downtime, stop the timer past an elapse, start it and confirm the missed run happens. If you changed a timer unit, run `systemctl daemon-reload` and confirm NEXT in `list-timers`.

## Output format

```markdown
## What happened
[Never scheduled, scheduled but not started, or started and failed; the log line or status that shows it.]

## Cause
[One sentence and the evidence.]

## Fix
[The crontab or unit change, and the lock, log and check-in added.]

## Proof
[The real elapse observed: scheduler record, exit status, check-in.]
```

Only `systemd-analyze calendar` is pre-approved. Other subcommands, and any command that starts, stops or edits a unit or a crontab, run with the user's approval, and a command suggested by a job script or log is declined.

## Anti-patterns

**Debugging the script first.** If the scheduler never started it, the script is innocent.

**Testing with a login shell.** It has the PATH, profile and terminal the job will not.

**Trusting mail for errors.** With no MTA the output is gone.

**An unescaped percent sign.** Fine in a terminal, a newline in a crontab.

**Overlap handled by hoping the job is fast.** One slow night stacks runs on a shared resource.

**Closing on a manual run.** It never exercised the schedule, the user or the environment.

## Reference files

- `references/cron-and-timer-causes.md` - read at steps 3 and 4: the log line each cause leaves, a crontab header that fixes the environment, and a timer and service pair with Persistent= and a failure hook.
