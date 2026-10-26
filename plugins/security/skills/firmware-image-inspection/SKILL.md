---
name: firmware-image-inspection
description: "Inspect an authorized firmware, flash, or disk image without trusting its contents: record the image digest and source, inventory regions (bootloader, partition table, kernel, root filesystem, configuration, signatures) with offsets, extract with caller-supplied Binwalk or Unblob into a quarantine directory, keep extraction notes, and back every claim with Evidence IDs while stating what was not proven. Prefer REA inspect_firmware_regions and extract_firmware when advertised. Use for what is in this firmware dump, map the partitions of a flash image, or authorized vendor-image security research. Not for starting general RE on a single binary (reverse-engineer-anything), reviewing your own firmware source (firmware-code-review), recovering a bricked board (brick-recovery), or defeating secure boot, DRM, or anti-theft on devices you are not authorized to modify."
allowed-tools: "Read, Grep, Glob, Bash"
---

# Firmware image inspection

Good looks like a region map an independent reviewer could reproduce from the
same bytes — offsets, sizes, types, and digests — with every extracted file
traced back to its region and every conclusion tied to Evidence, not to a
filename that looked familiar.

The job is hard because a firmware image is a container nobody documented for
you: vendor headers, compressed and encrypted regions, padding, overlapping
signatures that carvers report as false positives, and filesystems whose
contents were never meant to run on your host. Extracted blobs are untrusted
input, not source.

Builds on [`reverse-engineer-anything`](../reverse-engineer-anything/SKILL.md)
for REA connection and routing. REA: [morluto/rea](https://github.com/morluto/rea),
[rea.tools](https://rea.tools/), npm [`rea-agents`](https://www.npmjs.com/package/rea-agents).
REA does not ship Binwalk or Unblob; supply them yourself.

## Scope

Use for: images you built, vendor images for hardware you own or are
contracted to assess, dumps read from an owned device, and authorized
security-research samples; region inventory, extraction, locating a component
or configuration, and comparing two image versions.

Do not use for: reviewing firmware source you have (`firmware-code-review`);
recovering a device that no longer boots (`brick-recovery`); designing OTA
delivery (`ota-update-safety`); a single extracted executable once located
(`reverse-engineer-anything`); unlocking bootloaders or removing anti-theft,
activation, or carrier locks on devices you do not own; DRM key extraction.

## Hard gates

1. **Authorized images only.** Record the owner and basis. A firmware file on
   a download mirror is not permission to attack the devices that run it.
2. **Never execute extracted content on the host.** Treat every extracted
   file as hostile: no `chroot` into it, no running its binaries or scripts
   outside an isolated emulator or lab VM.
3. **Extraction into quarantine.** A dedicated directory, no symlink following
   outside it, and size limits — carvers can produce archive bombs and path
   traversal.
4. **No security-defeat instructions.** Do not produce steps to bypass secure
   boot, signature verification, anti-theft, or DRM for a device whose owner has
   not authorized it. Identifying that a check exists is fine; defeating it for
   someone else's device is not.
5. **Secrets found are reported, not used.** Keys, credentials, or tokens in an
   image go to the owner or the disclosure process (`vulnerability-disclosure`).

## Workflow

### 1. Pin the image

Record file name, SHA-256, size, source (vendor URL with date, owned-device
dump with method), and the device model and hardware revision it belongs to.

### 2. Region inventory before extraction

Run `inspect_firmware_regions` (or a read-only Binwalk/Unblob scan). Produce a
table: offset, size, detected type, entropy note, Evidence ID. Call out high
entropy regions (compressed or encrypted), signatures that overlap another
region, and gaps. See [firmware region notes](references/firmware-region-notes.md).

### 3. Extract deliberately

Use `extract_firmware` with caller-supplied tools, or the carver directly, into
quarantine. For each output, record the source region, tool and version, and
digest. Failed or partial extraction is a finding, not something to retry
blindly with different flags until it "works".

### 4. Answer the question from Evidence

Locate the component, configuration, or service the question is about. Route
individual executables to `reverse-engineer-anything`, APKs inside an Android
image to `android-apk-analysis`. Keep the ledger: claim → Evidence IDs →
confidence → unknowns.

### 5. Report what you can and cannot claim

Without Evidence, do not claim: that a region is encrypted (high entropy may be
compression), that a service runs at boot (an init script reference is not
execution), the device's runtime behavior, or that two images are identical
beyond the regions you compared.

## Anti-patterns

**Trusting the first carver hit.** Magic bytes inside compressed data produce
phantom filesystems; confirm with a header parse and a sane size.

**`sudo`-extracting an untrusted image.** Device nodes, setuid bits, and
traversal paths land on your host with root ownership.

**Reporting a filename as a version.** `busybox` in a path says nothing about
its build; check the binary's own strings or headers.

**Diffing extracted trees without diffing regions.** Changes in bootloader or
signature regions are invisible to a filesystem diff.
