---
name: authorized-device-debloat
description: "De-bloat or cut ads on an Android TV, smart TV, streaming box, or similar Android-based device the operator owns or is authorized to modify: identify ad and bloat packages from Evidence (package names, receivers, observed network endpoints, APKs pulled from that device), plan removal as reversible steps (pm disable-user before uninstall for user 0, package backup, rollback commands), use ADB only where already enabled on the owned device, and keep factory reset or reimaging as the documented recovery path. Use for remove ad packages from my TV, which preinstalled apps are safe to disable, or debloat a box I own. Not for package deep-dives (android-apk-analysis), binary RE (reverse-engineer-anything), image region work (firmware-image-inspection), or DRM, Widevine/HDCP bypass, piracy, anti-theft defeat, or any device you do not own."
allowed-tools: "Read, Grep, Glob, Bash"
---

# Authorized device de-bloat

Good looks like a device that shows fewer ads and runs fewer unwanted
background services, where every removed package was identified from Evidence,
every step can be undone, the owner knows the recovery path, and streaming,
updates, and security features still work.

The job is hard because "bloat" on a TV is tangled with the system: the
launcher that serves ads may also be the home screen, an "ad" package may share
a process with input or HDMI-CEC handling, and removing the wrong system
package can boot-loop the device. The lawful boundary matters as much as the
technique — customizing your own hardware is not the same as defeating content
protection or touching someone else's device.

Use [`android-apk-analysis`](../android-apk-analysis/SKILL.md) for a deep look
at any single package, and
[`reverse-engineer-anything`](../reverse-engineer-anything/SKILL.md) for native
binaries. REA ([morluto/rea](https://github.com/morluto/rea),
[rea.tools](https://rea.tools/), npm [`rea-agents`](https://www.npmjs.com/package/rea-agents))
helps when a package's role is unclear from metadata alone.

## Scope

Use for: lawful personal-device customization, interoperability, and security
research on hardware the operator owns or holds written authorization to
modify (for example, a managed fleet the operator administers); identifying ad,
telemetry, and preinstalled bloat packages; planning disable or uninstall
steps with rollback; documenting factory reset or reimaging as recovery.

Do not use for: DRM circumvention, Widevine or HDCP bypass, enabling piracy or
unlicensed streams; defeating anti-theft, activation, or account locks; account
takeover or access to services you do not hold; any device you do not own or
are not authorized to modify (a neighbor's, landlord's, venue's, or employer's
without authorization); distributing modified vendor images.

## Hard gates

1. **Ownership or authorization stated.** Write down who owns the device and
   the basis to modify it. No ownership, no plan — this skill gives nothing
   aimed at other people's devices.
2. **Content protection is out of bounds.** Do not disable, remove, patch, or
   spoof DRM, Widevine, PlayReady, HDCP, or integrity/attestation components,
   and do not suggest it as a way to "fix" playback.
3. **Reversible first.** Prefer `pm disable-user --user 0` over uninstall, and
   uninstall for user 0 (`pm uninstall -k --user 0`) over system-image changes.
   Rewriting or reflashing system images is a last resort, only when authorized,
   with a full backup and a verified recovery path.
4. **ADB only where already authorized.** Use developer options and ADB that
   the owner has enabled on the owned device over a trusted local network or
   USB. Do not use exploits, unlock bootloaders, or root to gain access you were
   not given; turn network ADB off afterward.
5. **Respect service terms where they bind the owner.** Blocking ads on your own
   device is a choice; account sharing, stream ripping, or region-lock evasion
   are not part of this skill.

## Workflow

### 1. Record the device and its baseline

Model, OS and firmware version, security patch level, and the owner. Export the
package baseline before changing anything:

```bash
adb shell pm list packages -f -u > packages-before.txt
adb shell pm list packages -d > disabled-before.txt
adb shell dumpsys package > dumpsys-package-before.txt
```

### 2. Identify candidates from Evidence

For each candidate, collect: package name, installer and whether it is a system
package, declared receivers (boot, package-added, network-change), running
services, and network endpoints observed from the owned device (for example via
the operator's own DNS resolver or router logs). Pull a candidate's APK from the
owned device (`adb shell pm path <pkg>`, then `adb pull`) for
`android-apk-analysis` when its role is unclear. A package name containing "ad"
is a hypothesis, not Evidence.

### 3. Classify

Sort candidates into: **ad/telemetry** (serves or reports ads), **optional
bloat** (preinstalled apps the owner does not use), **shared/critical**
(launcher, input, CEC, updater, DRM, Play services, setup wizard), and
**unknown**. Shared/critical and unknown are not touched without a deeper look.
See [the safe-removal checklist](references/safe-removal-checklist.md) and
[owned-device boundaries](references/owned-device-boundaries.md).

### 4. Change one package at a time

Disable, reboot, and check the acceptance list: boots to home, remote and CEC
work, streaming apps play, settings and updates open. Record the command and
result. Roll back with `pm enable <pkg>` or `cmd package install-existing <pkg>`
if anything breaks. Batch only packages already proven safe on this model.

### 5. Network-level option

When a package cannot be disabled without breaking the device, blocking its
ad endpoints at the owner's own DNS resolver or router is often enough and
leaves the system untouched.

### 6. Recovery path and handover

Document the rollback list, the factory-reset procedure for this model, and —
only if a reimage was authorized — where the backup and official vendor image
live. Note that firmware updates may re-enable removed packages.

## Anti-patterns

**Uninstalling the stock launcher to remove ads.** It is often the home screen;
switch the default launcher instead, then disable.

**Copy-pasting a debloat list from a forum for another model.** Package roles
differ by firmware; verify on this device.

**"Playback broke, so remove the DRM package too."** Out of bounds and makes
licensed playback fail permanently.

**Leaving network ADB enabled.** It exposes a shell to anyone on the network.
