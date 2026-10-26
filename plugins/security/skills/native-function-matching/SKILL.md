---
name: native-function-matching
description: "Compare two builds of the same native target you are authorised to examine — a patch release, a vendor update, or a version you have and one you do not — and say which functions are the same, which moved, which changed, and which are new or gone. Establishes identity from digests and build ids, inventories procedures on both sides, pairs them with a matcher that prefers exact names then structure, and confirms the pairs that matter by reading both bodies. Use for \"what changed between 1.2 and 1.3 of this binary\", \"did the license check survive the update\", or a 1-day diff. Not for analysing one binary (reverse-engineering), comparing package versions (dependency-triage), firmware images (firmware-analysis), or shipping a patch (release-strategy)."
allowed-tools: "Read, Glob, Grep, Bash(file:*), Bash(shasum:*), Bash(sha256sum:*), Bash(strings:*), Bash(rea:*), Bash(npx:*)"
---

# Native function matching

Good looks like two builds with recorded identities, a pairing that states how many functions
matched exactly, how many matched structurally, and how many are unknown, and a confirmed
diff for the handful of functions the question is actually about.

The job fails when the two builds are not identified first, so a build with a different
compiler or optimisation level is compared as if the bytes should line up. It fails when a
matcher's pairing is reported as equivalence: a structural match is a hypothesis, and the
function behind it can be a different implementation that happens to share a shape. And it
fails when the evidence inventory is dropped when the target closes, so the comparison cannot
be re-run or reviewed.

## Scope

Use for: a patch release against the version it replaced; a vendor update against the build
you already analysed; verifying that a fix landed in a binary you cannot build; and the
first pass of a 1-day analysis, where the question is which functions the patch touched.

Do not use for: analysing a single binary, which is `reverse-engineering`; deciding whether a
dependency upgrade is safe, which is `dependency-triage`; comparing firmware images, which is
`firmware-analysis`; or preparing and shipping a patch, which is `release-strategy`.

## Hard gates

1. **Authorisation for both builds.** The permission covers each artifact, not the pair; a
   build you were given does not authorise the one you found.
2. **Identify both builds before comparing.** Record the SHA-256, the build id or UUID, the
   version string and the architecture of each. Two binaries with the same version string are
   not necessarily the same build.
3. **A match is a hypothesis until the body is read.** Name matches are strong, structural
   matches are leads, and nothing in the pairing proves the two functions behave alike.
4. **Preserve the inventories.** Retained Evidence is what the matcher consumes; export each
   side's bundle before closing a target, because closing clears the session records and an
   evidence id alone is not enough to reopen it.
5. **Do not infer source changes from byte differences.** A function that changed can be
   recompiled with the same source. Report what changed in the binary, not what the developer
   did.
6. **No patch artifact.** The deliverable is the diff and its evidence; a patched binary or a
   bypass derived from it is out of scope.

## Workflow

### 1. Pin the question and the oracle

Write the question as something answerable: "which functions changed between 1.2.0 and 1.2.1
of this library, and is the license check among them". Choose the evidence that settles it —
the matched pairs, plus a read of the bodies for the specific function. A comparison with no
question produces a list nobody reads.

### 2. Establish identity

```bash
shasum -a 256 ./old ./new
file ./old ./new
strings -n 8 ./new | grep -iE 'version|[0-9]+\.[0-9]+\.[0-9]+' | head
```

Then read the build id the format carries: `readelf -n` on ELF (`GNU build ID`), `otool -l`
and the `LC_UUID` on Mach-O, the debug directory on PE. On macOS, `otool -l ./new | grep -A2
LC_UUID` prints it. If both are stripped and carry no id, the digest is the only identity and
the report should say so. [Build identity and
matching](references/build-identity-and-matching.md) has the identity field per format, what
the matcher consumes, and how to read the three buckets it returns.

### 3. Inventory procedures on each side

REA's `list_procedures` with `"detail": "summary"` retains the complete row set without
transferring the whole inventory, and its `parent_evidence_id` is what matching consumes. Do
this for each build, and note the counts: how many named, how many unnamed, and how many
thunks or imported stubs the inventory includes.

### 4. Match, and read the result as three buckets

`match_native_functions` takes the two retained inventories as `left` and `right`. It pairs
unique exact names first, then structural candidates, and reports what it could not pair.
Treat the output as:

- **matched exactly** — the same name on both sides; still confirm the body if the question
  depends on it.
- **matched structurally** — a candidate pair; disassemble both and compare the call sites
  that matter before calling it the same function.
- **unmatched** — new, removed, or renamed; each is a finding, not a parsing failure.

### 5. Confirm the pairs that matter

Disassemble the two bodies, compare the call sequences and constants, and look for the
change the version claims. Where the pair does not line up, say the matcher paired them and
the bodies disagree, rather than reporting the pair as a match.

### 6. Report and preserve

Report the two identities, the inventory counts, the three buckets with counts, the confirmed
diffs with evidence ids, and the functions that remain unknown. Export both bundles before
closing the targets, or the next session cannot reproduce the comparison.

## Anti-patterns

**Comparing builds from different toolchains as if they should match.** A different compiler
or optimisation level moves and inlines functions legitimately; the unmatched count says more
about the build than about the code.

**Reporting a structural match as "the same function".** Similar shape, different constant or
different callee is a different function, and only the body read settles it.

**Closing both targets and keeping only the evidence ids.** The ids reference retained records
that the close discarded; export first.

**Treating a recompiled function as a source change.** The binary diff is the fact; the source
inference is a guess with a plausible-looking address next to it.
