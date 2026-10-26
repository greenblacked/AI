---
name: android-apk-analysis
description: "Analyse an authorised Android APK, AAB or split set from the shipped package: record the target digest, read signing identity and certificate lineage before the code, inventory the manifest's permissions, exported components and receivers, take a summary-first dex overview, then follow strings and method references to the call that answers the question, citing Evidence IDs. Use for \"who signed this APK\", \"which class sends this request\", or authorised triage of a suspicious package. Not for general reverse engineering or a non-Android binary (reverse-engineering), an Apple bundle (apple-app-analysis), a firmware image (firmware-analysis), de-bloating a device you own (authorized-device-debloat), reviewing Java or Kotlin source (code-review), or a session that is slow or flooding context (rea-analysis-efficiency)."
allowed-tools: "Read, Glob, Grep, Bash(file:*), Bash(shasum:*), Bash(sha256sum:*), Bash(unzip:*), Bash(jadx:*), Bash(apktool:*), Bash(apksigner:*), Bash(strings:*), Bash(rea:*), Bash(npx:*)"
---

# Android APK analysis

Good looks like a package answer an independent reviewer could re-derive: the target's
SHA-256, who signed it, what the manifest declares, which classes and methods carry the
behaviour in question, and an Evidence ID behind every claim — with what stayed unproven
written down.

The job is hard because an APK is several artifacts at once — a zip container, one or more
signature schemes, a binary manifest, multiple dex files, native libraries and resources —
and decompiled Java or Kotlin is a reconstruction, not source. Obfuscation, split APKs and
repackaged look-alikes make a confident wrong answer easy.

This is the Android specialist under `reverse-engineering`, which owns the general case and the
REA connection; a non-Android binary, an Apple bundle or a firmware image belongs to its own
skill. REA itself: [morluto/rea](https://github.com/morluto/rea), [rea.tools](https://rea.tools/),
npm [`rea-agents`](https://www.npmjs.com/package/rea-agents).

## Scope

Use for: an APK, AAB or split set you own, build, are contracted to inspect, or received as
an authorised malware or incident sample; signing and provenance checks; mapping a feature,
permission or network call to the components and methods that implement it; comparing two
builds of the same package.

Do not use for: reviewing Java or Kotlin source you already have, which is `code-review`;
a non-Android native binary or an IPA, which is `reverse-engineering` or
`apple-app-analysis`; de-bloating a device you own, which is `authorized-device-debloat`; or
licence, DRM, anti-cheat or integrity-check bypass, repackaging someone else's app, or account
or server access the package was not meant to grant you.

## Hard gates

1. **Authorisation first.** State who owns the package and why you may inspect it. A store
   listing is not permission for every operation, and a sample feed's sample is still someone's
   build.
2. **Official tooling only.** REA from `github.com/morluto/rea`, `rea.tools` or npm
   `rea-agents`; JADX, apktool and apksigner from their official releases or the Android SDK.
3. **Isolate untrusted samples.** Malware triage runs in a lab VM without production
   credentials; static analysis needs no device and no network.
4. **No circumvention output.** Do not produce patches, re-signed builds or step-by-step
   bypasses for licensing, DRM, root or integrity detection, or paywalls, even when the code
   path is identified.
5. **Pseudocode is a lead, not source.** Never present decompiled output as the author's code,
   and never ship it.

## Workflow

### 1. Pin the target and the question

Record file name, SHA-256, size and where it came from (build output, device pull, sample
feed). For split sets, list every split — behaviour often lives in a config or feature split.
Write the question as the facts needed, not "analyse it".

### 2. Signing identity before code

Run `inspect_apk_signature` through REA, or `apksigner verify --print-certs -v` directly.
Record the schemes present (v1, v2, v3, v3.1, v4), the signer certificate SHA-256 and the
rotation lineage. A mismatch against the expected publisher answers provenance questions
before any decompilation, and flags a repackaged build. An AAB is a publishing format, not
an installable APK: generate the artifacts with `bundletool` and record which split set a
device actually receives. [Signing and package
facts](references/signing-and-package-facts.md) has the scheme table, the bundletool
commands and the split-pull procedure.

### 3. Package metadata

From `inspect_android_package` (or `apktool d` for the decoded manifest): package name,
version code and name, min and target SDK, requested and declared permissions, and every
exported activity, service, receiver and provider with its intent filters. The manifest is
binary XML — decode it rather than reading it with `strings`. Exported components and
`BOOT_COMPLETED` or `PACKAGE_ADDED` receivers are where background behaviour usually starts.

### 4. Classes and dex overview, summary-first

Take the summary: dex count, package tree, obfuscation signals, native libraries per ABI and
the notable SDKs. Page retained Evidence with `inspect_analysis_view` instead of requesting a
full dump, and read classes with a DEX-aware tool (`jadx`) rather than a native disassembler.
[Reading dex without fooling
yourself](references/code-reading-and-obfuscation.md) covers multi-dex, reflective and
dynamically loaded code, JNI and WebView bridges, and what a packer does to the read.

### 5. Strings and references to the answer

Search strings — hosts, URLs, intent actions, keys of interest — and follow method references
from the component that matters to the call that matters. Keep a ledger: claim, Evidence IDs,
confidence, unknowns. Run through
[the APK evidence checklist](references/apk-evidence-checklist.md) before finishing.

### 6. Report

Lead with the answer, then the signing identity, then the component-to-method path with
Evidence IDs. Mark anything inferred from naming alone, anything behind reflection, dynamic
loading or native code not examined, and any runtime claim that static analysis cannot prove.

## Anti-patterns

**Decompiling first, checking the signer last.** A repackaged APK makes every later finding
about the wrong build.

**Analysing only `base.apk`.** Splits and dynamically delivered features carry real behaviour.

**Trusting class names in obfuscated code.** A plausible name a deobfuscator produced is an
inference; say so.

**Claiming network behaviour from a string.** A URL in the dex is a reference, not proof the
request is made; trace the caller or mark it unknown.
