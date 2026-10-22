# Capture and symbols

## Where the limit is set

| Process started by | Set it with |
| --- | --- |
| A shell or script | `ulimit -c unlimited` before exec |
| A systemd unit | `LimitCORE=infinity` in the `[Service]` section |
| Docker | `docker run --ulimit core=-1` |
| Kubernetes | The container runtime's default ulimit; there is no pod field for it, so set it in the node's runtime configuration or have the entrypoint raise the soft limit up to the hard limit |

A soft limit cannot exceed the hard limit; check both with `ulimit -Sc` and `ulimit -Hc`.

## core_pattern

Read it with `cat /proc/sys/kernel/core_pattern`; change it with `sysctl -w kernel.core_pattern=...` and persist it in a file under `/etc/sysctl.d/`. It applies to every process on the host.

- A path form such as `/var/crash/core.%e.%p.%t` writes a file. `%e` is the executable name, `%p` the pid, `%t` the time. Every file-form path, absolute or relative, is resolved inside the crashing process's mount namespace, so in a container it lands in the container's own filesystem and disappears with it. Mount a volume at that same path in every container, or use the pipe form.
- A pipe form begins with `|` and runs a handler with the dump on standard input. `systemd-coredump` is the common handler; list with `coredumpctl list`, inspect with `coredumpctl info <pid>`, open with `coredumpctl gdb <pid>`, export with `coredumpctl dump <pid> -o core`.
- A pipe handler runs in the host's namespace, so the container's filesystem is not where it writes.

Size the volume for the largest resident set you run, multiplied by how many crashes you retain, and delete by age. A crash loop can fill the disk and take the host down with it, so cap the count.

## Split debug files

```bash
objcopy --only-keep-debug app app.debug
objcopy --strip-debug --add-gnu-debuglink=app.debug app
readelf -n app          # Build ID under .note.gnu.build-id
```

Store `app.debug` at a path derived from the build ID, conventionally `.build-id/<first two hex digits>/<rest>.debug`, because gdb and debuginfod both look there. For a build you control, link with `-Wl,--build-id` so the note is always present.

## debuginfod

Run a debuginfod server over the directory of debug files and set `DEBUGINFOD_URLS` on the analysis machine; gdb then fetches the executable's and libraries' symbols by build ID. Index only artefacts from your own build system, since the server serves whatever it is given.

## Language notes

- Rust: build release with `-C debuginfo=1` or `debug = 1` in the profile to keep line tables without full debug info; `strip` settings in the profile remove it.
- Go with cgo: Go's own runtime prints a goroutine dump on a fatal signal, and `GOTRACEBACK=crash` makes it abort so a core is written.
- C++: keep the debug file for every shared library you ship, not only the executable.
