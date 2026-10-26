# Target routing and evidence

## Route first

Pick the first tool from the supplied target. Use `open_binary` for active-target
native or archive workflows; target-free tools take their own path or endpoint.

| Kind | Start with |
| --- | --- |
| ASAR / extracted JS or Electron tree | `analyze_javascript_application` |
| Archive inventory (ZIP, APK, IPA, MSIX, AppX, DMG, PyInstaller) | `open_binary` then `inspect_artifact` as needed; large inventories: `detail: "summary"` |
| Apple bundle resources (plist, IB, assets) | `open_bundle_resources` — not a substitute for native `open_binary` |
| Android APK code / classes / methods | `inspect_android_package` |
| APK / AAB signatures | `inspect_apk_signature` |
| Managed PE/CLI (.NET) | `inspect_managed_artifact` |
| Firmware | `inspect_firmware_regions`; extraction needs caller-supplied Binwalk/Unblob |
| Native executable / library / analysis DB | `open_binary`, then overview → strings/symbols → decompile/xrefs |
| WASM | `inspect_wasm_artifact` (caller-supplied WABT) |
| Go / Rust metadata, PE imports/certs, ELF notes, model artifacts, etc. | Matching `inspect_*` tools when advertised |
| Live browser / Electron / process capture | Only when static evidence cannot answer; requires host runtime access |
| AgentEnv of a web app | Upstream environment-build workflow from a live instance or HAR |

Prefer the connected server's advertised catalog over this table when they
disagree. Deep native analysis needs Hopper, Ghidra, or IDA.

## Summary-first Evidence

1. Take the default or summary reply and its inline Evidence / graph context.
2. For large JS apps or ELF layouts, call with `"detail": "summary"`, then page
   with `inspect_analysis_view` using `parent_evidence_id`.
3. Over MCP, treat truncated client previews as incomplete — use retained IDs or
   `export_evidence_bundle` rather than re-running the producer.
4. On `resource_constraint` with transport limits, request a smaller view of the
   same retained Evidence; do not repeat the oversized call.
5. When the parent ID is unknown, use `get_evidence_bundle` with
   `detail: "summary"` and exact filters (operation, target SHA-256, profile).

## Evidence discipline

- Distinguish **observations**, **inferences**, and **unknowns**.
- Cite Evidence IDs; preserve limitations and incomplete coverage.
- Never imply static analysis observed execution.
- Runtime requests execute the declared target; do not broaden scope silently.
- Page module identities and select `node_id` before requesting an item; one
  path can have several graph roles.
- Do not repeat an identical analysis or rejected call without a changed input
  or resolved blocker.

## Broader investigations

1. Turn the request into a checklist of questions and the evidence each needs.
2. Reuse matching session state, bookmarks, and prior Evidence; avoid duplicate
   opens.
3. Start with the smallest useful overview; expand only for concrete gaps.
4. Corroborate with the evidence type required; use runtime only when static
   cannot answer and access is authorized.
5. Keep a finding ledger: conclusion → Evidence IDs → confidence → unknowns.
6. Before finishing, mark each checklist item answered, partial, or unresolved.
