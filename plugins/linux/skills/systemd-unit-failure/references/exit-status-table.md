# Exit status table

## Contents

- Statuses set by systemd
- Result values
- Quick reading order

## Statuses set by systemd

A status in this range means the failure happened while systemd prepared the child, so the program's own log is empty. Names are those in `systemctl` output after the slash.

| Status | Name | Usual cause | First check |
| --- | --- | --- | --- |
| 200 | CHDIR | WorkingDirectory= missing or unreadable | `ls -ld` the directory as the service user |
| 202 | FDS | Could not set up file descriptors | Socket activation settings |
| 203 | EXEC | ExecStart binary missing, not executable, wrong interpreter line, or on a noexec mount | `namei -l` the path; `findmnt -T path -o OPTIONS`; head -1 of the script |
| 205 | LIMITS | A Limit* setting could not be applied | The `Limit*=` lines |
| 216 | GROUP | Group= does not exist | `getent group NAME` |
| 217 | USER | User= does not exist, or is not resolvable early at boot | `getent passwd NAME`; consider `DynamicUser=` |
| 218 | CAPABILITIES | Capability set could not be applied | `CapabilityBoundingSet=`, `AmbientCapabilities=` |
| 226 | NAMESPACE | Sandbox could not be built: a path in ReadWritePaths, ReadOnlyPaths or BindPaths does not exist, or PrivateTmp failed | Every path named in sandbox directives; prefix a path with `-` to tolerate absence |
| 227 | NO_NEW_PRIVILEGES | NoNewPrivileges= could not be applied | Unit sandboxing lines |
| 228 | SECCOMP | Syscall filter could not be installed | `SystemCallFilter=` |
| 229 | SELINUX_CONTEXT | Required SELinux context could not be set | `ausearch -m avc -ts recent` |
| 231 | APPARMOR | AppArmor profile could not be applied | Profile name exists and is loaded |
| 233 | RUNTIME_DIRECTORY | RuntimeDirectory= could not be prepared | Ownership of /run parents |
| 238 | STATE_DIRECTORY | StateDirectory= could not be prepared | Existing /var/lib path owned by another user |
| 239 | CACHE_DIRECTORY | Same for CacheDirectory= | /var/cache path |
| 240 | LOGS_DIRECTORY | Same for LogsDirectory= | /var/log path |
| 241 | CONFIGURATION_DIRECTORY | Same for ConfigurationDirectory= | /etc path |

Statuses not listed are rarer; the manual page `systemd.exec(5)` has the complete list under its exit status section.

## Result values

| Result | Meaning |
| --- | --- |
| `exit-code` | The main process exited non-zero. Read the status above |
| `signal` | Killed by a signal; `ExecMainStatus` is the signal number. 9 may be the OOM killer: see `oom-kill-forensics` |
| `timeout` | Start, stop or watchdog timeout; check Type= and `TimeoutStartSec=` |
| `start-limit-hit` | Too many starts inside the interval; see step 6 |
| `oom-kill` | The unit's cgroup was OOM-killed |
| `resources` | Systemd could not set up resources for the unit, for example a fork or PID-file failure |

## Quick reading order

1. `Result=` then `ExecMainStatus`.
2. If 200 or above: the unit file and the filesystem, not the app.
3. If below 200: the application log for the first failing attempt.
4. If the journal says `Dependency failed for ...` or `Job ... failed with result 'dependency'`: that is a job result, not a `Result=` value; switch to the unit it names.
