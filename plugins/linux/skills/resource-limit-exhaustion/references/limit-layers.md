# Limit layers

## Contents

- Where each limit lives and how to read it
- Counting inotify use
- Drop-in and sysctl.d examples
- Containers and orchestrators
- Reverting a change

## Where each limit lives and how to read it

| Limit | Scope | Read it | Set it |
| --- | --- | --- | --- |
| RLIMIT_NOFILE | One process, inherited by children | `/proc/PID/limits`, `prlimit --pid PID --nofile` | `LimitNOFILE=` in the unit; `limits.conf` for login sessions only |
| `fs.nr_open` | Ceiling for any process's nofile | `sysctl fs.nr_open` | sysctl.d |
| `fs.file-max` | Whole system, open file handles | `sysctl fs.file-max`, `/proc/sys/fs/file-nr` | sysctl.d |
| RLIMIT_NPROC | Per real user, counts threads too | `/proc/PID/limits` ("Max processes") | `LimitNPROC=` or `limits.conf` for sessions |
| TasksMax | One cgroup (a service, a user slice) | `systemctl show UNIT -p TasksMax,TasksCurrent`, `pids.max` and `pids.current` in the cgroup directory | `TasksMax=` in the unit; manager default `DefaultTasksMax=` |
| `kernel.pid_max` | Whole system, pid space | `sysctl kernel.pid_max` | sysctl.d |
| `kernel.threads-max` | Whole system, thread count | `sysctl kernel.threads-max` | sysctl.d |
| `vm.max_map_count` | Per process memory mappings; thread stacks use them | `sysctl vm.max_map_count`, `wc -l /proc/PID/maps` | sysctl.d |
| `fs.inotify.max_user_watches` | Per user, all processes | `sysctl fs.inotify.max_user_watches` | sysctl.d |
| `fs.inotify.max_user_instances` | Per user | `sysctl fs.inotify.max_user_instances` | sysctl.d |

EMFILE comes from the per-process limit (or the per-user inotify instance limit), ENFILE from `fs.file-max`. The two have different fixes, which is why the exact message text matters.

The soft limit is what is enforced; a process may raise its soft limit up to the hard limit without privilege. Many programs do that at start-up, so a low soft limit in `/proc/PID/limits` after start usually means the hard limit or the unit setting is low, not that nothing tried.

For a process that does not appear to have a systemd unit (a login session, a container), read its `/proc/PID/limits` and trace the parent chain with `ps -o pid,ppid,cmd --forest` to find who set it.

## Counting inotify use

Watches and instances are limited per user, so group by the owning user. Each inotify instance is one descriptor of type `anon_inode:inotify`:

```bash
for fd in $(find /proc/[0-9]*/fd -lname 'anon_inode:inotify' 2>/dev/null); do
  pid=${fd#/proc/}; pid=${pid%%/*}
  n=$(grep -c '^inotify' "/proc/$pid/fdinfo/${fd##*/}" 2>/dev/null)
  printf '%s %s %s %s\n' "$(stat -c %u /proc/$pid)" "$n" "$pid" "$(tr '\0' ' ' < /proc/$pid/cmdline | cut -c1-60)"
done > /tmp/inotify.txt
awk '{w[$1]+=$2; i[$1]++} END {for (u in w) print "uid", u, "watches", w[u], "instances", i[u]}' /tmp/inotify.txt
sort -k2 -rn /tmp/inotify.txt | head
```

Run it as root so every process is readable. Columns are uid, watches on that instance, PID and command. Compare each uid's watch sum with `max_user_watches` and its instance count with `max_user_instances`; a total across users says nothing about either limit. Typical heavy users are editors and file-sync tools, IDE indexers, `webpack` or `tsc` in watch mode and container tooling watching a large tree. A single watcher recursing into `node_modules` or a build output directory is the common cause; exclude the directory in the tool rather than raising the limit by a factor of ten.

## Drop-in and sysctl.d examples

A service drop-in (`systemctl edit UNIT` writes it to `/etc/systemd/system/UNIT.d/override.conf`):

```ini
[Service]
LimitNOFILE=65536
TasksMax=4096
```

`LimitNOFILE=` takes a soft:hard pair as `4096:65536` if the soft value should stay low, which suits programs that close all descriptors up to the limit after a fork. Choose the number from the plateau measured at step 4 with headroom, not from a round figure.

A kernel settings file, `/etc/sysctl.d/90-limits.conf`:

```ini
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
```

Apply with `sysctl --system`, and read the value back with `sysctl fs.inotify.max_user_watches`. Number prefixes decide load order, and a later file wins over an earlier one for the same key, so check for a competing file with `grep -rn max_user_watches /etc/sysctl.d /usr/lib/sysctl.d /run/sysctl.d`.

## Containers and orchestrators

A container's limits come from its runtime, not from the host service that started the runtime. For Docker the per-container flag is `--ulimit nofile=65536:65536` and the pid cap is `--pids-limit`; in Compose they sit under `ulimits` and `pids_limit`. Under Kubernetes the nofile limit is inherited from the container runtime's defaults, and the pod can be limited by a node-level pid cap. Read `/proc/1/limits` inside the container to see what it got. The inotify settings are per user on the host kernel and shared by every container on it, so one noisy container can exhaust the watches of the others.

## Reverting a change

Before changing, record the running values:

```bash
sudo sh -c 'umask 077; sysctl fs.file-max fs.nr_open kernel.pid_max kernel.threads-max fs.inotify.max_user_watches fs.inotify.max_user_instances > /root/limits-before.txt'
sudo test -s /root/limits-before.txt && echo saved
```

The redirect runs inside the privileged shell; with `sudo sysctl ... > file` the redirect would run as the calling user and fail on `/root`. Check the file is not empty before changing anything.

To revert a unit drop-in, remove the drop-in (`systemctl revert UNIT` removes all local overrides of that unit) and restart the service. To revert a sysctl change, write the recorded values back with `sysctl -w key=value` and remove the file under `/etc/sysctl.d/`; removing the file alone leaves the new value active until reboot.
