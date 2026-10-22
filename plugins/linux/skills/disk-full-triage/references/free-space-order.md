# Free space order

## Contents

- Safe and regenerating
- Logs
- Journal
- Containers
- Needs an owner

## Safe and regenerating

| Item | Command | Cost |
| --- | --- | --- |
| apt package cache | `apt-get clean` | Packages are downloaded again on next install |
| dnf cache | `dnf clean all` | Metadata is fetched again |
| pip and npm caches | The tool's cache purge command | Slower next install |
| Old kernels | Remove through the package manager, keeping the running one and one fallback | Fewer boot fallbacks |

Confirm the owner agrees for anything under a home directory or a build agent's workspace.

## Logs

- Compressed rotated logs (`*.gz`) that are shipped elsewhere can go.
- A live log: `truncate -s 0 FILE`. If the writer opened the file without append mode, it keeps its old offset and the file becomes sparse and grows again; restart the writer or have it reopen logs.
- Fix the volume at source: a debug level left on, or a missing logrotate rule. Test a rule with `logrotate -d /etc/logrotate.d/NAME`.

## Journal

```bash
journalctl --disk-usage
journalctl --vacuum-size=500M
journalctl --vacuum-time=2weeks
```

Vacuum deletes archived files only. To keep it bounded, set `SystemMaxUse=` in `/etc/systemd/journald.conf` or a drop-in under `journald.conf.d`.

## Containers

```bash
docker system df
docker image prune
docker builder prune
```

`docker system prune` also removes stopped containers and unused networks; add `--volumes` only after the owner has confirmed no needed data lives in an unattached volume. The json-file log driver grows without bound unless `max-size` and `max-file` are set for it.

## Needs an owner

Database data and WAL or binlog directories, upload stores, backups, VM images. Report size and growth rate, and ask. Removing WAL or binlogs by hand can corrupt recovery.
