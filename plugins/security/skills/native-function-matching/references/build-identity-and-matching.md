# Build identity and matching

Read this before the first comparison. Most bad function diffs are a comparison of two things
that were never the same program.

## Identity fields, by format

| Format | Field | Read with |
| --- | --- | --- |
| ELF | `GNU build ID` in the note segment | `readelf -n` |
| Mach-O | `LC_UUID` load command | `otool -l`, then the `uuid` line |
| PE | debug directory entry (GUID and age) | A PE reader, or the symbol server path |
| Any | SHA-256 of the file | `shasum -a 256` or `sha256sum` |

A build id survives stripping; a version string does not identify a build. Record both, and
the architecture, because a framework ships several slices and a diff between `arm64` and
`x86_64` is meaningless.

## What the matcher consumes

`match_native_functions` pairs two `list_procedures` inventories. It never opens a target,
reads its file or executes it, so the inventories must be complete and retained:

1. `list_procedures` with `"detail": "summary"` on each build, keeping the
   `parent_evidence_id` of each.
2. `match_native_functions` with `left` and `right` referencing those inventories.
3. Export both bundles before `close_binary`, because closing clears session records that the
   ids point at.

Passing only an evidence id after the target closed is a common failure: the id is still a
string, and the record behind it is gone.

## The three buckets, and what each means

- **Exact name match.** Both sides carry the same symbol with a plausible origin. Strong, but
  still a name: a function can be renamed to something misleading, and an imported thunk can
  share a name with a local wrapper.
- **Structural match.** The matcher paired functions by shape and size when names were absent
  or ambiguous. This is a lead. Read both bodies before reporting anything that depends on it,
  and expect aliases and one-to-many candidates on optimised builds.
- **Unmatched.** New, removed, renamed, inlined, or a function the inventory did not represent.
  Report the count and the names when there are names; an unmatched count with no list is a
  number the reader cannot check.

## Confirming a pair

Read both bodies and compare, in this order:

1. The constants and string references — a changed string is usually the change.
2. The direct call sequence, not the addresses.
3. The branches around the part the question is about.

A pair whose constants and calls agree is the same function for practical purposes. A pair
whose shape agrees but whose constants differ is a different function, and the matcher was
doing its job by flagging a candidate.

## What the comparison cannot prove

- That the source changed: a recompile moves and inlines code without a source edit.
- That behaviour is unchanged: two identical bodies can sit behind different callers, or read
  different configuration.
- That the builds are the ones that shipped: the digest identifies the file you hold, not the
  artifact on a device.

Each of those is a separate claim with its own evidence, and the report should say which
bucket it came from.
