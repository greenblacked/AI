---
name: reverse-engineer-anything
description: "Investigate shipped binaries, packages, Electron/JavaScript apps, APKs, firmware and related artifacts with REA (local MCP/CLI) when source is missing or insufficient: confirm authorized scope, prefer official rea-agents only, route the target to the right tool, work summary-first with Evidence IDs, and recover connection/provider blockers without repeating unchanged calls. Use for reverse engineer, decompile, how does this binary feature work, malware triage on authorized samples, or reconstruct behavior from a shipped app. Not for ordinary source-repo architecture (codebase-orientation), vetting whether to install REA as an MCP (agent-extension-audit), a diff security review (security-review), or DRM/cheat/unauthorized access work."
allowed-tools: "Read, Grep, Glob, Bash"
---

# Reverse Engineer Anything

Good looks like an investigation that answers the user's question from shipped
artifacts, cites Evidence IDs, states what was not proven, and never treats
pseudocode as original source.

The job is hard because REA is a bridge, not a sandbox and not a decompiler of
its own: it drives local tools (Ghidra, Hopper, IDA, JADX, and built-in static
inspectors) with the current user's permissions. Untrusted binaries, impostor
packages, and over-claimed reconstructions are the failure modes this skill
exists to prevent.

Adapted from the official REA skill at
[morluto/rea](https://github.com/morluto/rea) (`.agents/skills/reverse-engineer-anything`),
condensed for this catalogue. Prefer upstream docs when contracts change:
[rea.tools](https://rea.tools/), npm [`rea-agents`](https://www.npmjs.com/package/rea-agents).

## Scope

Use for: authorized reverse engineering, malware or incident analysis of samples
you are allowed to examine, interoperability and debugging of software you own
or are contracted to inspect, education/CTF labs, and reconstructing behavior
from a shipped app when source is absent or incomplete.

Do not use for: ordinary analysis of a complete source repository; DRM, license,
or anti-cheat circumvention; game cheats; unauthorized access or bypass;
copying proprietary code into a product from REA output alone; installing an
unknown MCP package without an extension audit.

## Hard gates

1. **Authorization first.** Confirm the target is owned or authorized. Public
   availability of a file is not permission for every operation.
2. **Official distribution only.** Install or invoke REA only from
   `github.com/morluto/rea`, `rea.tools`, or npm `rea-agents`. A similar name or
   copied README is not proof of authenticity.
3. **Not a sandbox.** Opening an untrusted binary delegates parsing to the local
   provider with the user's permissions. Prefer an isolated lab VM for untrusted
   samples.
4. **Evidence, not vibes.** Every conclusion distinguishes observations,
   inferences, and unknowns. Cite Evidence IDs; preserve limitations.
5. **Commercial tools need lawful licenses.** REA grants no IDA/Hopper/JEB
   entitlement. Cracked tools are out of bounds.

## Workflow

### 1. Decide whether REA is needed

Use REA when the claim depends on a shipped binary or package, decompilation,
requested runtime evidence, or comparison with behavior not established by
available source. For ordinary source-repository architecture, use normal repo
tools and do not run REA readiness commands.

### 2. Connect only when tools are missing

If REA MCP tools are already available and not known to be stale, go straight to
the target. Do not run setup or doctor before every investigation.

When tools are absent, a call is blocked, or a required provider is unavailable,
follow [connection and recovery](references/connection-and-recovery.md). Diagnose
the observed blocker; do not repeat an unchanged failing call.

Setup sketch (review the plan before applying):

```bash
npx -y rea-agents@latest doctor --json
npx -y rea-agents@latest setup --client <client_id> --dry-run --json
# after approval:
npx -y rea-agents@latest setup --client <client_id> --yes
```

Pass a client id from the upstream `rea-agents` client list to `--client`.
Pin an exact `rea-agents` version in durable MCP registrations. Node.js
requirements follow the published package (22.x / 24.x / 26.x floors).

CLI fallback without MCP (JavaScript/Electron tree or ASAR):

```bash
npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json
```

### 3. Route the target first

Choose the first tool from the target the user supplied. See
[target routing and evidence](references/target-routing-and-evidence.md).

Common routes:

| Target | First tool / approach |
| --- | --- |
| ASAR or extracted JS/Electron tree | `analyze_javascript_application` |
| ZIP/APK/IPA/MSIX/DMG/PyInstaller inventory | `open_binary` / `inspect_artifact` |
| Android APK code/classes | `inspect_android_package` |
| Managed .NET assembly | `inspect_managed_artifact` |
| Native executable/library | `open_binary`, then native overview tools |
| Firmware | `inspect_firmware_regions` / `extract_firmware` (BYO Binwalk/Unblob) |
| APK signatures only | `inspect_apk_signature` |
| AgentEnv of a web app | environment-build workflow (see upstream environments guide) |

Static JavaScript and ordinary ZIP inventory need neither Hopper nor Ghidra.
Native deep analysis needs a local Hopper, Ghidra, or IDA install.

### 4. Work summary-first

Start with the default or `"detail": "summary"` result. Page retained Evidence
with `inspect_analysis_view` / `parent_evidence_id` instead of repeating the
producer. Do not re-run identical analysis without a changed input or resolved
blocker.

### 5. Finish

Explain findings in plain language tied to Evidence. When asked to build
something, use normal coding tools and separate observed behavior from design
choices. Close an opened native session with `close_binary` when done.

## Anti-patterns

**Running REA on a daily-driver with production secrets against an untrusted
sample.** Same-user permissions; REA is not containment.

**Installing from a viral mirror or Telegram "release".** Supply-chain malware
has used copied READMEs.

**Treating decompilation as redistributable source.** Pseudocode and
reconstructions are leads; check rights before shipping.

**Repeating an unchanged MCP call after a host timeout.** The client deadline
expiring does not prove REA finished; see the recovery guide.

**Setup before every task.** Registration repair is for missing/stale tools, not
a ritual.
