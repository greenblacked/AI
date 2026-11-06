# Unsafe site ledger

One review of the unsafe code in one crate or one change. Fill in every field; delete the
guidance in brackets.

## Scope

- Crate and revision: [name and commit]
- Lints in force: [for example `unsafe_op_in_unsafe_fn`, `clippy::undocumented_unsafe_blocks`, `forbid(unsafe_code)` elsewhere]
- Unsafe sites found: [number, from `cargo geiger` or a search, with the command used]

## Sites

One row per `unsafe` block, function, impl or trait.

| Site | Kind | Contract location | Verdict | Miri or sanitizer run |
| --- | --- | --- | --- | --- |
| [file:line] | [block / fn / impl / trait] | [`// SAFETY:` at file:line, or `# Safety` section] | [sound / unsound / unproven / removed] | [command, result, or why it cannot run] |

## Removed or wrapped

| Site | Replacement |
| --- | --- |
| [file:line] | [safe std API, vetted crate, or the safe wrapper that now owns the invariant] |

## Test evidence

| Command | Result | What it does not cover |
| --- | --- | --- |
| [for example `cargo +nightly miri test`] | [pass / fail / not run] | [FFI calls Miri cannot run, interleavings] |

## Gate

[What CI enforces on unsafe code, for example the clippy lint at deny, and who approves a new site.]
