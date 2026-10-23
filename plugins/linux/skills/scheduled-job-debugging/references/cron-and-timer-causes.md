# Cron and timer causes

## Contents

- What each cause looks like in the log
- A crontab header that fixes the environment
- A timer and service pair
- Checks for duplicates and overlap
- Time zones and daylight saving

## What each cause looks like in the log

| Symptom | Likely cause | How to confirm |
| --- | --- | --- |
| No `CMD` line at the expected minute | Entry not parsed: bad file in `/etc/cron.d`, missing trailing newline, syntax error | `ls -l /etc/cron.d`, `tail -c 1 FILE \| od -c`, cron syslog lines about the file |
| `(CRON) bad minute`, `bad command` or `ORPHAN` in the log | Syntax error or a file cron does not trust | The log names the file; fix and wait for the reload |
| `CMD` line present, no output file | Percent sign split the command, or redirection missing | Look for `%` in the line |
| `CMD` line present, command not found | PATH is the short default | `env -i` reproduction, or add `PATH=` |
| Works as root, not from cron under another user | The entry runs as that user, with different permissions | `stat` the files, run with `sudo -u USER env -i ...` |
| PAM or account message beside the CRON line | Locked, expired or restricted account | `chage -l USER`, `passwd -S USER`, `/etc/security/access.conf` |
| Two `CMD` lines for one slot | Same entry in `/etc/crontab`, `/etc/cron.d` and a user crontab, or two hosts | `grep -r NAME /etc/cron* /var/spool/cron` and check the other hosts |
| Timer listed, LAST never changes | Not elapsed yet, unit pairing wrong, or timer inactive | `systemctl status NAME.timer`, `systemctl cat NAME.timer` |
| Timer elapsed, service failed | The job failed, not the schedule | `systemctl status NAME.service` |
| Run missing after reboot | No `Persistent=true` and the machine was off at the elapse | `systemctl cat NAME.timer` |

Reading a file's last byte: `tail -c 1 /etc/cron.d/FILE | od -c` prints `\n` when the newline is there.

Per-user crontabs are not files to edit by hand. List one with `crontab -l -u USER` and edit with `crontab -e`, which validates syntax on save.

## A crontab header that fixes the environment

```cron
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""
# m h dom mon dow command
30 3 * * * flock -n /run/lock/nightly.lock /opt/app/bin/nightly >> /var/log/nightly.log 2>&1
0 4 * * * /opt/app/bin/report --date "$(date +\%F)" >> /var/log/report.log 2>&1
```

Setting `MAILTO=""` is a decision: it stops mail, so the explicit log redirection and the check-in must replace it. In `/etc/cron.d` files add the user name as the sixth field. Variable assignments in a crontab are not shell assignments: they are not expanded, so `PATH=$PATH:/x` does not extend anything.

## A timer and service pair

`/etc/systemd/system/nightly.service`:

```ini
[Unit]
Description=Nightly report
OnFailure=notify-failure@%n.service

[Service]
Type=oneshot
User=reports
WorkingDirectory=/srv/reports
ExecStart=/opt/app/bin/nightly
ExecStartPost=/usr/bin/curl -fsS --retry 3 https://heartbeat.example.internal/ping/nightly
```

`/etc/systemd/system/nightly.timer`:

```ini
[Unit]
Description=Run the nightly report

[Timer]
OnCalendar=*-*-* 03:30:00 UTC
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
```

Then `systemctl daemon-reload` and `systemctl enable --now nightly.timer`. `ExecStartPost=` runs only after `ExecStart=` succeeds, which is what a check-in needs. `notify-failure@.service` is a template you provide; the name is a placeholder. The `heartbeat.example.internal` host is a placeholder as well.

Test the pair without waiting: `systemd-analyze verify /etc/systemd/system/nightly.service /etc/systemd/system/nightly.timer`, then `systemctl start nightly.service`.

## Checks for duplicates and overlap

- List every place a schedule can live: `/etc/crontab`, `/etc/cron.d/`, `/etc/cron.hourly` and its siblings, `/var/spool/cron/`, and `systemctl list-timers --all`. A duplicate between a user crontab and a timer is common after a migration.
- The `/etc/cron.hourly`, `daily`, `weekly` and `monthly` directories run through `run-parts`, which skips names with a dot and files that are not executable. Anacron, where installed, sets their actual time of day.
- A job that runs on several hosts at once from configuration management runs several times. Check the host list before the entry.
- To see whether a lock is held: `flock -n /run/lock/NAME.lock true && echo free`. This takes and releases the lock at once, so run it only to test.

## Time zones and daylight saving

- Cron uses the system zone unless the cron implementation honours `CRON_TZ`. Check `timedatectl` and `ls -l /etc/localtime`.
- In the hour skipped at the spring change a fixed-time job may not run, and in the repeated hour at the autumn change it may run twice or once, depending on the cron implementation and version. Do not rely on the behaviour: schedule outside the window or in UTC.
- A systemd timer can state the zone in the expression, as in `OnCalendar=*-*-* 03:30:00 UTC`. `systemd-analyze calendar` echoes the zone it understood.
- Containers often run in UTC while the people reading the schedule think in local time. State the zone in a comment beside the entry.
