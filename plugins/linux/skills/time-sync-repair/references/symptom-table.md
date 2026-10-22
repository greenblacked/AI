# Symptom table

Each row is a symptom, the likely cause, the check that confirms it and the fix. Confirm
with the check before applying the fix; several causes share a symptom.

| Symptom | Likely cause | Check | Fix |
| --- | --- | --- | --- |
| `Reach` 0 on every source, `Not synchronised` | Outbound UDP 123 blocked, or name resolution broken | `chronyc sources -v`; `chronyc activity` shows how many sources are offline; resolve the pool name from the host | Allow UDP 123 to the sources and their replies; fix the resolver; use addresses of internal sources |
| One source, offset swings when it changes | A single source cannot be cross-checked | Count the `^` lines in `chronyc sources` | Add sources until there are at least three, ideally four, from independent operators |
| Two sources that disagree, selection flaps | No tiebreak with two | `chronyc sourcestats -v` shows both with wide error | Add a third and fourth |
| Offset of up to a second around a leap second, one source marked bad | Smearing and non-smearing servers mixed | Compare the operators' documented leap handling | Use only smearing or only non-smearing sources everywhere in the fleet |
| Clock jumps forward after resume, snapshot restore or live migration | Guest counter stale; host does not hand the clock back | Journal shows a large step from chronyd at the resume time | Hypervisor PTP clock as `refclock PHC`, and `makestep 1.0 3` or an explicit post-resume step |
| Clock is off by exactly the zone offset after reboot | Hardware clock stored as local time | `timedatectl status` shows `RTC in local TZ: yes` | `timedatectl set-local-rtc 0`; keep `rtcsync` in the chrony configuration |
| Offset grows steadily, frequency value large and moving | Poor oscillator, heavy CPU steal, or a second client fighting chrony | `chronyc tracking` frequency over several hours; `systemctl is-active` for ntpd and systemd-timesyncd | Keep one client; on a VM prefer the PTP source |
| Offset corrects but only slowly after a big error | Slew limit; `makestep` threshold not met | `chronyc tracking` shows `System time` shrinking slowly | Accept the slew on a live host, or step once in a window with `chronyc makestep` |
| Synchronised host, but one application still sees wrong time | Application caches a timezone or uses its own clock source | Compare `date -u` with the application's reported time | Fix at the application; this is not a sync fault |

## Hypervisor and cloud clock sources

- KVM guests: load the `ptp_kvm` module so the guest has a PTP clock backed by the host,
  then add a `refclock PHC` line for that device. The device node name varies by kernel and
  udev rules; check `ls /dev/ptp*` and `cat /sys/class/ptp/*/clock_name`.
- Hyper-V guests: the Time Synchronization integration service feeds a PTP device
  (`/dev/ptp_hyperv`). Keep that service enabled and use the device as a `refclock PHC` source;
  disabling the service leaves the device with no host samples. If the clock jumps at
  resume, handle it with chrony's `makestep` settings rather than by turning the service off,
  and check the wording against Microsoft's Linux time sync documentation.
- Cloud instances: use the provider's documented internal time service, reachable without
  crossing the internet, rather than public pools.

## chrony directives worth knowing

- `makestep THRESHOLD LIMIT`: step if the offset exceeds THRESHOLD seconds, but only for
  the first LIMIT updates. A negative LIMIT removes the restriction, which is the
  dangerous form on a live host.
- `rtcsync`: have the kernel copy system time to the hardware clock periodically.
- `minsources N`: do not synchronise unless at least N sources agree.
- `maxdistance`: reject a source whose root distance exceeds the value.
- `refclock PHC /dev/ptpN poll 2`: use a PTP hardware clock as a source.

## A fleet skew report

List every host in scope, one row each: hostname, client (chrony, systemd-timesyncd, other),
signed offset in seconds, and `Stratum`. Collect with `chronyc tracking` on chrony hosts and
`timedatectl timesync-status` on systemd-timesyncd hosts. `chronyc tracking` prints
`System time` as "N seconds fast of NTP time" or "N seconds slow of NTP time": record fast
as positive and slow as negative. A host where collection failed, where chronyd is stopped,
or that is unsynchronised (`Leap status : Not synchronised`, stratum 0) gets the status
`no data` and counts as over tolerance, so it cannot make the fleet look clean. Sort by
absolute offset. Report the maximum over hosts with data, the count over tolerance
including the `no data` hosts, and the list of those hosts. Rerun after the change and show
both tables.
