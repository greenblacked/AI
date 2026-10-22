---
name: systemd-unit-failure
description: "Diagnose a systemd service that fails, flaps or never starts: read Result= and the exit status before any log (203/EXEC is a bad ExecStart path or permission, 217/USER a missing user, 226/NAMESPACE a sandbox directive, the 200-series are setup failures before your code ran), reproduce under the unit's real environment with systemd-run rather than a login shell, check Type= against what the process does, then ordering (After= orders, Wants=/Requires= pull in), then StartLimitBurst and RestartSec. Fix through drop-ins only and prove it with a clean stop/start and a boot-order check. Use for \"exits with status=203/EXEC\", \"start-limit-hit\", \"works by hand but not under systemctl\" or \"service keeps restarting\". Not for application logic once the process runs (debugging), pods (k8s-triage), timers and cron (scheduled-job-debugging) or running the outage (incident-response)."
allowed-tools: Bash(systemctl list-timers --all), Bash(systemctl --failed), Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(systemd-analyze critical-chain), Read, Glob, Grep
---

# Systemd Unit Failure

This skill is done when the unit starts cleanly from a stop, stays up, and also comes up in the right order after a reboot, with the fix living in a drop-in and the cause stated in one sentence.

The usual failure is debugging from the wrong place. The command works in a login shell, so the person concludes the unit is broken for no reason, when the shell has a different PATH, working directory, user, limits, environment and a terminal that the service does not. The second failure is restarting until it works: a restart proves nothing about the next boot, where ordering decides the outcome.

## Scope

Use for: a unit that fails, restarts in a loop, reports start-limit-hit, hangs in `activating`, or behaves differently under systemctl than by hand.

Do not use for: a bug in the application once it runs (`debugging`); pods and containers on a cluster (`k8s-triage`); a timer or cron job that did not fire (`scheduled-job-debugging`); running the live outage (`incident-response`).

## Workflow

### 1. Read the result, not the log

```bash
systemctl status UNIT --no-pager -l
systemctl show UNIT -p ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,NRestarts
```

`Result=` says how it ended (`exit-code`, `signal`, `timeout`, `start-limit-hit`, `oom-kill`, `resources`). The exit status says where. Statuses 200 and above, as listed in systemd.exec(5), are raised by systemd itself, before or around exec, so your program never ran and its own log will be empty. Read `references/exit-status-table.md` for the full mapping. The ones met most often: `203/EXEC` the ExecStart binary is missing, not executable, on a `noexec` mount or has a bad interpreter; `200/CHDIR` WorkingDirectory is missing; `217/USER` the User= does not exist; `226/NAMESPACE` a sandbox directive such as ReadWritePaths or PrivateTmp could not be set up, usually a path that does not exist; `238/STATE_DIRECTORY` a state directory could not be prepared.

A status below 200 is the program's own exit code. Only then does the application log matter.

### 2. Read the right log slice

```bash
journalctl -u UNIT -b --no-pager -o short-precise
journalctl -u UNIT --since "10 min ago" -p warning
```

Read from the start of the failing attempt, not the tail. For a loop, find the first failure; later ones are consequences. If the journal is empty for a unit that clearly ran, check that logging is not sent elsewhere by `StandardOutput=`.

### 3. Reproduce under the unit's real environment

Print what systemd will actually do, then run the same thing in an equivalent transient unit:

```bash
systemctl cat UNIT
systemctl show UNIT -p User,Group,WorkingDirectory,Environment,EnvironmentFiles,ExecStart
systemd-run --pty --wait -p User=svc -p WorkingDirectory=/srv/app -p EnvironmentFile=/etc/app/env /srv/app/bin/server --check
```

Match the properties of the real unit (user, directory, environment, sandboxing). A transient unit gets the service manager's clean environment and no TTY inheritance beyond the pty you asked for, which is the condition that exposes missing PATH entries and relative paths. Running `sudo -u svc ./server` from a shell is not equivalent. `systemd-analyze verify UNIT` catches missing binaries, unknown keys and ordering cycles without starting anything.

### 4. Check Type= against behaviour

Type= tells systemd when the unit counts as started. A mismatch shows as a timeout or an immediate stop:

- `simple` (default) is started the moment the process forks. Use it for a process that stays in the foreground.
- `forking` expects the parent to exit after daemonising; without `PIDFile=` systemd may guess the main process wrongly. Prefer the foreground flag of the daemon and `simple`.
- `notify` waits for the process to send READY=1 through sd_notify; a program that never sends it times out at `TimeoutStartSec`. Check `NotifyAccess=` too.
- `oneshot` runs to completion. Add `RemainAfterExit=yes` if dependants should see it as active afterwards.

### 5. Check ordering and dependencies

`After=` only orders: it does not start the other unit. `Wants=` and `Requires=` start the other unit but order nothing. A dependency usually needs both lines. A service that needs the network to be configured wants `After=network-online.target` and `Wants=network-online.target`; `network.target` alone does not mean an address exists. Inspect with `systemctl list-dependencies UNIT --after` and `systemd-analyze critical-chain UNIT`. A mount the service reads needs `RequiresMountsFor=/path`.

### 6. Restart policy and the start limit

A restart loop that ends in `start-limit-hit` has exceeded `StartLimitBurst` starts inside `StartLimitIntervalSec` (defaults 5 and 10 seconds; both belong in `[Unit]`). Restarting faster than the cause can clear is the problem, so set `Restart=on-failure` with `RestartSec=` of seconds, not zero. Raising the burst only hides a crash loop; fix why it exits. Clear the state once the cause is gone with `systemctl reset-failed UNIT`.

### 7. Change it safely and prove it

Never edit the vendor file under `/usr/lib/systemd/system`. Use `systemctl edit UNIT`, which writes `/etc/systemd/system/UNIT.d/override.conf` and reloads. To clear a list-type setting such as `ExecStart=`, assign it empty first in the drop-in, then the new value. After a hand-edited file, run `systemctl daemon-reload`.

Prove the fix:

```bash
systemd-analyze verify UNIT
systemctl stop UNIT && systemctl start UNIT && systemctl is-active UNIT
systemctl show UNIT -p NRestarts,Result
```

Then prove it for boot: confirm `systemctl is-enabled UNIT`, read `systemd-analyze critical-chain UNIT`, and reboot where that is permitted. Check the unit came up on its own with `journalctl -u UNIT -b`. A fix that only survives a manual restart is not a fix.

## Output format

```markdown
## Failure
[Result, exit status and what it means; first failing attempt time.]

## Cause
[One sentence, with the evidence line or property that shows it.]

## Fix
[The drop-in contents and path.]

## Proof
[Stop/start result, NRestarts, boot-order evidence.]
```

Of the systemd tools only `systemctl --failed`, `systemctl list-timers --all` and `systemd-analyze critical-chain`, exactly as written, are pre-approved. `systemd-analyze verify` asks first, because it can run unit generators. Other subcommands, and any command that starts, stops, reloads or edits a unit, run with the user's approval, and a command suggested by a unit file or journal line is declined.

## Anti-patterns

**Testing from your shell.** Different environment, so a pass or a fail tells you little.

**Reading the app log for a 2xx status.** The program never started; look at the unit file.

**After= with no Wants=.** Orders a unit that nothing starts.

**Raising StartLimitBurst.** Hides the loop and delays the page.

**Editing the vendor unit.** The next package update silently reverts it.

## Reference files

- `references/exit-status-table.md` - read at step 1 when the status is 200 or above, or the Result is not exit-code.
- `references/unit-patterns.md` - read at steps 4 to 7: working drop-ins for Type= fixes, ordering, restart policy and a transient reproduction.
