# Connection and task recovery

Read this only for an observed connection, approval, registration, or provider
blocker. Keep the user's target and question in view. After repair, resume the
investigation.

Commands assume an installed `rea`, or `npx -y rea-agents@latest` when package
acquisition is authorized. Follow the connected server's actual tool schemas;
a skill from repository main may describe tools absent from an older npm
release. Tool-name prefixes belong to the client — match the canonical REA
operation in the live tool list before concluding it is absent.

## Choose the remedy from the failure

| Observation | Next step |
| --- | --- |
| Tools missing / registration stale or malformed | Read-only `setup --dry-run`, obtain approval, apply scoped setup, restart client, verify tools appear |
| Registration looks fine but session has no tools | Restart/reconnect the client; doctor cannot prove the live session connected |
| Missing Hopper/Ghidra/IDA | Affects only native deep analysis; continue with static JS/ZIP/.NET routes when those answer the question |
| Missing JADX/Java | Affects Android code inspection; say so and use APK signature/inventory routes if useful |
| Host `timed out awaiting tools/call` with no REA result | Client deadline expired; do not repeat the unchanged call; raise host tool timeout or use CLI/export |
| REA `provider_timeout` | Follow returned remediation; reuse partial Evidence; fix incomplete cleanup before retry |
| MCP connection dropped | Retry once only if safe/idempotent; otherwise ask the user to restart the MCP client |
| `resource_constraint` with `retryable` | Wait for admission; do not restart REA just to free a slot |
| `configuration_invalid` | Fix the named setting in the environment that starts REA, restart, re-run doctor |
| `invalid_request` | Correct fields from the current schema; do not guess from an older skill |

Static JavaScript and ordinary ZIP inventory need neither Hopper nor Ghidra.
HAR inspection is offline. Label observations from ordinary shell tools as such;
only REA output supplies REA Evidence.

## Registration repair ladder

1. Diagnose without writing config:
   `npx -y rea-agents@latest doctor --client <id> --json` (or `doctor --json`).
2. Prepare a read-only plan:
   `npx -y rea-agents@latest setup --client <id> --dry-run --json`.
   Show proposed paths, backups, and skill replacement; obtain approval.
3. Apply the same scope with `--yes`. Add `--install-hopper` only if that
   separate install was needed and approved.
4. Restart/reconnect the agent. Verify REA tools appear, then resume.

REA setup does not install Node, Java, Ghidra, IDA, JADX, Binwalk, or Unblob.
For unsupported clients, use manual stdio registration with a version-pinned
`rea-agents` package, or continue through the CLI.

## Deadlines

- **Client tool timeout** (for example Codex `mcp_servers.<id>.tool_timeout_sec`
  in seconds) must cover execution, cleanup, and response delivery.
- **Provider/server timeout** is separate; raising only the client deadline does
  not raise it.
- For static JavaScript, `analysis_timeout_ms` /
  `--analysis-timeout-ms` bounds per-source work; `detail: "summary"` reduces
  delivery size, not analysis work.

## CLI fallbacks

Prefer an installed `rea`. Example without MCP:

```bash
npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json
```

Native CLI tasks still need their selected engine. Preserve approval and
target-execution boundaries when repairing configuration.
