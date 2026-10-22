# Unit patterns

## Contents

- Override drop-in skeleton
- Replacing ExecStart
- Ordering on the network and on a mount
- Restart policy that avoids start-limit-hit
- Transient reproduction

## Override drop-in skeleton

Create with `systemctl edit UNIT`. The file is `/etc/systemd/system/UNIT.d/override.conf`:

```ini
[Service]
Environment=PATH=/usr/local/bin:/usr/bin:/bin
WorkingDirectory=/srv/app
```

## Replacing ExecStart

A list-type setting is appended to unless it is reset with an empty assignment:

```ini
[Service]
ExecStart=
ExecStart=/usr/local/bin/server --config /etc/app/app.toml
```

Use an absolute path. Systemd does not search PATH for the first word, and it does not run a shell, so pipes, globbing and `$VAR` expansion in the shell sense do not happen. Wrap in `/bin/sh -c '...'` only when a shell is genuinely needed.

## Ordering on the network and on a mount

```ini
[Unit]
Wants=network-online.target
After=network-online.target
RequiresMountsFor=/srv/data
```

`network-online.target` only means something if a wait-online service for your network manager is enabled. Check with `systemctl is-enabled systemd-networkd-wait-online.service` or `NetworkManager-wait-online.service`.

## Restart policy that avoids start-limit-hit

```ini
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=5
```

That allows five attempts in five minutes, five seconds apart, then stops and reports start-limit-hit so the failure is visible rather than a silent loop. After fixing the cause: `systemctl reset-failed UNIT && systemctl start UNIT`.

## Transient reproduction

```bash
systemd-run --pty --wait \
  -p User=svc -p Group=svc \
  -p WorkingDirectory=/srv/app \
  -p ProtectSystem=strict -p ReadWritePaths=/srv/app/data \
  /srv/app/bin/server --check
```

Copy only the properties that the real unit sets. Add them one at a time when hunting a sandbox failure: the property whose addition turns a pass into a failure is the cause.
