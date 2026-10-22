---
name: time-sync-repair
description: "Fix clock drift and time-sync failures. Use for \"certificate is not yet valid\", \"Kerberos clock skew too great\", \"chrony not syncing\" or \"VM clock jumped after resume\". Measure first with chronyc tracking (offset, frequency, stratum), chronyc sources -v and sourcestats, or timedatectl timesync-status, then diagnose by symptom: UDP 123 blocked, one or exactly two sources (use at least three, ideally four), leap-smearing mixed with non-smearing servers, a VM that steps after pause or migration (hypervisor PTP clock, makestep), a hardware clock in local time. Decide step versus slew before touching a running database, confirm the fleet agrees, and alert on offset, not on the daemon running. Not for TLS failures once the clock is right (tls-handshake-debugging), timezone or DST in a job (scheduled-job-debugging) or a live outage (incident-response)."
allowed-tools: Bash(chronyc tracking), Bash(chronyc sources -v), Bash(chronyc sourcestats), Bash(chronyc activity), Bash(chronyc ntpdata), Bash(timedatectl status), Bash(timedatectl timesync-status), Read, Glob, Grep
---

# Time Sync Repair

This skill is done when every host in scope reports an offset inside the tolerance of the system that cares most (usually well under a second, far under the Kerberos limit), the cause of the drift is named, and an alert on offset exists so the next drift is found before a certificate or ticket check fails.

The usual failure is treating "the daemon is running" as "the clock is right". chronyd and systemd-timesyncd both run happily with no reachable source, and the symptom surfaces somewhere else entirely: a TLS client says the certificate is not yet valid, a Kerberos login says the clock skew is too great, a log line is out of order. The second failure is stepping the clock under a live workload to make the symptom go away, which moves time backwards for a database or log shipper and corrupts ordering.

## Scope

Use for: a host or fleet whose clock is wrong or unstable; chrony or timesyncd not synchronising; clocks that jump after VM pause, resume or live migration; choosing and sizing the time sources.

Do not use for: TLS failures once the clock is right (`tls-handshake-debugging`); a job that fires at the wrong hour because of timezone or DST (`scheduled-job-debugging`); coordinating an incident that is already live (`incident-response`).

## Workflow

### 1. Measure before changing anything

```bash
chronyc tracking          # offset, frequency, skew, stratum, leap status
chronyc sources -v        # which sources, reach, last sample; the -v adds a legend
chronyc sourcestats -v    # per-source offset estimate and standard deviation
timedatectl status        # NTP service active, clock synchronised, RTC mode
timedatectl timesync-status   # only when systemd-timesyncd is the client
```

Read `chronyc tracking`: `System time` is how far the clock is from the daemon's best estimate, `Last offset` and `RMS offset` show recent error, `Frequency` is the local oscillator's error in parts per million (a large value is normal on a VM, a value that keeps changing is not), `Stratum` 0 or a `Leap status` of `Not synchronised` means the daemon has no usable source. In `chronyc sources`, a `*` marks the selected source and `+` a combined one; `?` means unreachable or not yet usable, and a `Reach` of 0 means nothing has answered. Record the numbers: a repair without a before figure cannot be shown to have worked.

### 2. Identify the symptom class

Read `references/symptom-table.md` for the full mapping. The common causes, in the order to check them:

1. **No source answers.** Reach 0 on every line. NTP uses UDP port 123 outbound and replies back; a firewall or security group that allows only TCP is the usual cause, and a host that resolves its pool names through a broken resolver never gets the addresses.
2. **Too few sources.** With one source chrony cannot tell a wrong server from a right one. With exactly two it cannot break a tie when they disagree. Use at least three, ideally four, from independent operators.
3. **Mixed leap handling.** Some public services smear a leap second over many hours; others step it. During a leap event the two disagree by up to a second and the client may reject one or flap. Choose all smearing or all non-smearing sources; never mix them in one configuration.
4. **VM clock steps.** After pause, snapshot restore or live migration the guest's counter is stale and the clock jumps. Prefer the hypervisor's PTP clock as a chrony `refclock PHC` source (the `ptp_kvm` module on KVM, the PTP device from the Hyper-V integration services, the provider's documented device on a cloud) and allow an initial step with `makestep`.
5. **Hardware clock in local time.** `timedatectl status` showing `RTC in local TZ: yes` makes a dual-boot or a reboot shift the clock by the zone offset. Set it to UTC with `timedatectl set-local-rtc 0`.
6. **Two clients.** chronyd, ntpd and systemd-timesyncd running together fight over the clock. Keep exactly one.

### 3. Decide step versus slew

Slewing changes the clock rate by a small amount until the offset is gone; time never goes backwards, but a large offset takes a long time to correct. Stepping fixes it at once and can move time backwards.

- A host with a running database, queue or log shipper: slew, or schedule a drained window and step once. Check that the offset is small before deciding (a few hundred milliseconds slews quickly).
- A fresh boot or a VM just resumed: step is fine; nothing depends on continuity yet. The chrony directive `makestep 1.0 3` steps only if the offset exceeds one second and only during the first three updates after the daemon starts, which is the safe default.
- To correct by hand once, `chronyc makestep` (needs root) steps immediately. Say in the change record that it was done and when.

### 4. Apply the change

Edit the chrony configuration (usually `/etc/chrony/chrony.conf` on Debian-family systems, `/etc/chrony.conf` on Red Hat-family): the source lines, `makestep`, and `rtcsync` so the kernel keeps the hardware clock updated. Restart or reload the service, then wait for convergence rather than checking once:

```bash
chronyc waitsync 20 0.1   # up to 20 tries, until the offset is under 0.1 seconds
chronyc tracking
```

Do not edit the files from this skill's tool set; propose the diff and let the owner apply it, since a bad time source list on a fleet host is a wide change.

### 5. Confirm the fleet agrees

One host fixed is not a fleet fixed. Collect `chronyc tracking` from every host (over SSH or the configuration management tool) and report the spread: the largest absolute offset, the hosts above tolerance, and the hosts with no synchronisation. Compare against the tolerance of the strictest consumer: Kerberos rejects tickets beyond five minutes of skew by default, TLS validity checks tolerate only the clock being plausibly inside the certificate's validity window, and distributed databases often care about a few hundred milliseconds or less.

### 6. Alert on offset

Alert on the quantity that breaks things. With the Prometheus node exporter, `node_timex_offset_seconds` is the kernel's offset estimate and `node_timex_sync_status` is 1 when the kernel believes it is synchronised; alert when the absolute offset stays above the tolerance for several minutes, and when sync status is 0. An alert on "chronyd is active" would have stayed silent through every failure above.

## Output format

```markdown
## Symptom and measurement
[Before figures: offset, frequency, stratum, reach per source.]

## Cause
[Which class from step 2, with the evidence line.]

## Change
[Source list, makestep, refclock, rtcsync; step or slew and why.]

## Verification
[After figures per host; fleet spread; the alert and its threshold.]
```

## Anti-patterns

**Restarting chronyd and moving on.** The restart makes the symptom disappear for a while and teaches nothing about the cause.

**One source, or exactly two.** There is no majority to outvote a bad server.

**Setting the date by hand.** It steps the clock with no record and the drift returns.

**Stepping under a live database.** Time going backwards breaks ordering assumptions; slew or drain first.

**Mixing smeared and unsmeared servers.** They disagree during a leap event by design.

## Reference files

- `references/symptom-table.md` - read at step 2: symptom, probable cause, check and fix, including chrony directives and hypervisor clock sources.
