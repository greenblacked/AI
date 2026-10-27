# Analysis bridge tooling: connect, route and cite

Read this when the analysis bridge (the `rea-agents` package and its `rea` command) is installed, when the
target needs a decompiler or a provider this machine does not have on `PATH`, or when a
bridge call fails. Read it before the first bridge call in a session, not on every task: an
already-connected server that answers is not a reason to run setup again.

The bridge runs with the caller's own permissions, not a sandbox and not a decompiler of
its own. It drives Ghidra, Hopper, IDA, JADX, WABT and built-in static inspectors, and it
grants no licence to any of them. It is MIT-licensed; the
version these instructions were written against is **6.8.0**, and the supported runtimes
are Node.js `>=22.23.4`, `>=24.22.1` and `>=26.12.1` — 23, 25 and earlier 26.x are
refused, so check `node --version` before blaming the tool for not starting.

## Contents

- [Connect only when the tools are missing](#connect-only-when-the-tools-are-missing)
- [Route the target before calling anything](#route-the-target-before-calling-anything)
- [Evidence, not transcripts](#evidence-not-transcripts)
- [When a call fails](#when-a-call-fails)
- [Record what the finding rests on](#record-what-the-finding-rests-on)

## Connect only when the tools are missing

`doctor` is read-only and answers whether the tools are there. Run it when a call reports
a missing tool, not before every investigation:

```bash
npx -y rea-agents@6.8.0 doctor --client claude_code --json
```

`--client` takes the client id this agent runs as (`claude_code`, `codex`, `opencode`,
`cursor`, among others). Leave out `--skill`: it requires the bridge's own bundled skill,
which this setup does not install. To register the MCP server, preview the exact writes
first and read the plan before applying it:

```bash
npx -y rea-agents@6.8.0 setup --client claude_code --skill=false --dry-run --json
npx -y rea-agents@6.8.0 setup --client claude_code --skill=false --yes
```

`--skill=false` registers the server without the bridge's bundled skill, which `setup`
installs by default and which would compete with these skills for the same requests.
`--yes` is what lets `setup` apply with no terminal prompt, as an agent runs it; without it
the command stops and asks to be rerun interactively. Pass it only after the dry-run plan
has been read.

Pin the version. `@latest` belongs to a deliberate update, not to a registration written
into a config file that outlives this session; an unpinned entry is whatever npm published
this morning. A global install runs the same commands as `rea doctor`, `rea setup` and
`rea analyze-javascript-application`; when in doubt, the global binary is the one the MCP
server is running, so its version is the one to record.

The setup names every path and change it will make, and applies nothing until approved.
Read it for the three things that go wrong quietly: it may offer to install the paid-licence provider (Hopper), which
is a licence you may not hold; it edits agent configuration outside this repository;
and a client id that is not the agent you are actually using produces a registration that
works and is never loaded.

## Route the target before calling anything

Choose the first tool from the artifact, not from familiarity. Prefer the connected
server's advertised tool list when it disagrees with this table; the table is the shape of
the released tool set, the server is the authority on what is installed.

| Target | First call |
| --- | --- |
| Extracted JavaScript or Electron tree, `app.asar` | `analyze_javascript_application` |
| ZIP, APK, IPA, MSIX, DMG, or a PyInstaller executable as an inventory | `open_binary`, then `inspect_artifact` |
| APK code, manifest, resources | `inspect_android_package` |
| APK signing block only | `inspect_apk_signature` |
| Managed PE (CIL) assembly | `inspect_managed_artifact` |
| Native executable, library or analysis database | `open_binary`, then overview, strings, symbols, decompile |
| Firmware image | `inspect_firmware_regions`; extraction is caller-supplied Binwalk or Unblob |
| Desktop `.app`, mobile IPA or DMG inventory | `inspect_artifact`, then the app-bundle projection |
| WebAssembly bytes | `inspect_wasm_artifact`, which needs caller-supplied WABT |
| Two builds of the same native target | `list_procedures` on each, then `match_native_functions` |

Static JavaScript and archive inventory need neither Ghidra nor Hopper; opening a provider
for them is time spent on a tool the route did not ask for. Live observation — a browser,
an Electron main process, a running process capture — is the last resort, only when static
evidence cannot answer and the runtime access is authorised.

## Evidence, not transcripts

Every evidence-producing call returns a record with a stable `evidence_id` and a
`normalized_result`. Read the summary first (`"detail": "summary"` where offered) and page
the retained record instead of re-running the producer:

- `inspect_analysis_view` with the parent `evidence_id` returns a smaller view of the same
  analysis.
- `export_evidence_bundle` preserves it; `close_binary` clears session records, so export
  before closing when the work continues later.
- A citation in the report is the `evidence_id`, the target digest and the operation — not
  "the decompiler showed".

An inline preview truncated by the client is incomplete Evidence, not an empty result.
Page the retained record; do not repeat the call that was truncated.

## When a call fails

Diagnose the observed failure class before changing anything, and never repeat an
unchanged call hoping for a different answer.

| Symptom | What it means | Next move |
| --- | --- | --- |
| `provider_timeout` from the server | The engine ran out of its own budget | Narrow the request (one function, one region) or raise the provider budget if the client allows it |
| The client's own deadline expired | The client stopped waiting; the server may still be working | Wait, then read the retained Evidence by id; do not resend the same request |
| `resource_constraint` or an oversized frame | The reply is larger than the transport | Request a summary view or a bundle, not the whole record again |
| A missing provider | Ghidra, Hopper, IDA or WABT is not installed or not configured | `doctor --provider <name> --json`, then install only what the licence and the target need |
| A tool that is not in the list | The connected server does not ship it | Check the server's tool list and version; do not invent a call |

Raising only the client timeout when the server returned `provider_timeout` treats two
different budgets as one. A host timeout does not prove the analysis failed, and a
successful retry does not prove the first call was harmless: the first may still be
writing.

## Record what the finding rests on

In the session notes, before the first call, write down the bridge version, the client id,
the target path and SHA-256, the provider and its version, and the route chosen. A finding
that cannot be tied to those cannot be reproduced, and a bridge upgrade can change a
projection's shape without changing the bytes it read.
