---
name: android-apk-analysis
description: "Analyse an authorized Android APK, AAB or split set from the shipped package: confirm scope, record the target digest, read signing identity and certificate lineage, package metadata (manifest, permissions, components, exported receivers), a classes/dex overview, and the strings and method references that answer the question, citing Evidence IDs and working summary-first. Use REA (inspect_android_package, inspect_apk_signature) or JADX when available, official rea-agents only. Use for APK signing checks, what does this package do, which component sends this request, or authorized malware triage of an APK. Not for general RE routing or non-Android binaries (reverse-engineer-anything), ordinary Java/Kotlin source review (code-review), iOS IPA work, slow or flooding sessions (rea-analysis-efficiency), or DRM, cheat or unauthorized-access work."
allowed-tools: "Read, Grep, Glob, Bash"
---

# Android APK analysis

Good looks like a package answer an independent reviewer could re-derive: the
target's SHA-256, who signed it, what the manifest declares, which classes and
methods carry the behavior in question, and an Evidence ID behind every claim —
with what stayed unproven written down.

The job is hard because an APK is several artifacts at once — a ZIP container,
one or more signature schemes, a binary manifest, multiple dex files, native
libraries, and resources — and decompiled Java/Kotlin is a reconstruction, not
source. Obfuscation, split APKs, and repackaged look-alikes make a confident
wrong answer easy.

Builds on [`reverse-engineer-anything`](../reverse-engineer-anything/SKILL.md)
for connection, routing, and recovery, and on
[`rea-analysis-efficiency`](../rea-analysis-efficiency/SKILL.md) when the
session gets slow or floods context. REA itself: [morluto/rea](https://github.com/morluto/rea),
[rea.tools](https://rea.tools/), npm [`rea-agents`](https://www.npmjs.com/package/rea-agents).

## Scope

Use for: an APK, AAB, or split set you own, build, are contracted to inspect,
or received as an authorized malware/incident sample; signing and provenance
checks; mapping a feature, permission, or network call to the components and
methods that implement it; comparing two builds of the same package.

Do not use for: reviewing Java/Kotlin source you already have (`code-review`);
iOS IPA or non-Android native binaries (`reverse-engineer-anything`);
de-bloating a device you own (`authorized-device-debloat`); license, DRM,
anti-cheat, or integrity-check bypass; repackaging someone else's app; account
or server access the package was not meant to grant you.

## Hard gates

1. **Authorization first.** State who owns the package and why you may inspect
   it. A Play Store listing is not permission for every operation.
2. **Official tooling only.** REA from `github.com/morluto/rea`, `rea.tools`,
   or npm `rea-agents`; JADX/apktool/apksigner from their official releases or
   the Android SDK.
3. **Isolate untrusted samples.** Malware triage runs in a lab VM without
   production credentials; static analysis does not need a device.
4. **No circumvention output.** Do not produce patches, re-signed builds, or
   step-by-step bypasses for licensing, DRM, root/integrity detection, or
   paywalls, even when the code path is identified.
5. **Pseudocode is a lead, not source.** Never present decompiled output as the
   author's code or ship it.

## Workflow

### 1. Pin the target and the question

Record file name, SHA-256, size, and where it came from (build output, device
pull, sample feed). For split sets, list every split; behavior often lives in a
config or feature split. Write the question as facts needed, not "analyse it".

### 2. Signing identity before code

Run `inspect_apk_signature` (or `apksigner verify --print-certs -v`). Record
schemes present (v1/v2/v3/v3.1/v4), signer certificate SHA-256, and rotation
lineage. A mismatch against the expected publisher answers provenance questions
before any decompilation and flags repackaged builds.

### 3. Package metadata

From `inspect_android_package` (or JADX's decoded manifest): package name,
version code/name, min/target SDK, requested and declared permissions, and every
exported activity, service, receiver, and provider with its intent filters.
Exported components and `BOOT_COMPLETED` / `PACKAGE_ADDED` receivers are where
background behavior usually starts.

### 4. Classes and dex overview, summary-first

Take the summary: dex count, package tree, obfuscation signals, native
libraries per ABI, and notable SDKs. Page retained Evidence with
`inspect_analysis_view` instead of requesting full dumps.

### 5. Strings and references to the answer

Search strings (URLs, hosts, intent actions, keys of interest) and follow
method references from the component that matters to the call that matters.
Keep a ledger: claim → Evidence IDs → confidence → unknowns. Use
[the APK evidence checklist](references/apk-evidence-checklist.md) before
finishing.

### 6. Report

Lead with the answer, then signing identity, then the component → method path
with Evidence IDs. Mark anything inferred from naming alone, anything behind
reflection, dynamic loading, or native code not examined, and any runtime claim
that static analysis cannot prove.

## Anti-patterns

**Decompiling first, checking the signer last.** A repackaged APK makes every
later finding about the wrong build.

**Analysing only `base.apk`.** Splits and dynamically delivered features carry
real behavior.

**Trusting class names in obfuscated code.** `a.b.c` renamed to something
plausible by a deobfuscator is an inference; say so.

**Claiming network behavior from a string.** A URL in the dex is a reference,
not proof the request is made; trace the caller or mark it unknown.
