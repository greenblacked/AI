---
name: rea-analysis-efficiency
description: "Cut unnecessary reverse-engineering analysis cost while preserving Evidence: pin the analyst question and a correctness oracle, find the earliest redundant work (repeated scans, full reports for selected facts, oversized MCP replies), prefer summary-first and retained Evidence paging, and verify equivalent completed investigations before claiming a win. Use when REA or a decompiler session is slow, floods context, or re-runs the same native analysis. Not for writing REA itself (out of scope), CI suite tuning, ordinary source debugging (debugging), or starting a fresh RE investigation (reverse-engineer-anything)."
allowed-tools: "Read, Grep, Glob, Bash"
---

# REA analysis efficiency

Good looks like the same investigation answers, with less repeated engine work
and smaller agent context — measured against an explicit oracle, not a feeling
that JSON got shorter.

Adapted from the official REA skill
`rea-analysis-optimization` in [morluto/rea](https://github.com/morluto/rea),
rewritten for operators using REA rather than for changing REA's own code.

## Scope

Use for: an authorized REA or provider-backed investigation that is slow,
memory-heavy, flooding the model context, or clearly redoing the same analysis.

Do not use for: starting the investigation (use `reverse-engineer-anything`);
ordinary application debugging without REA; tuning REA's CI or implementing REA
tools; DRM or unauthorized targets.

## Workflow

### 1. Pin the question and the oracle

Write the analyst's completed task: facts needed, detail level, source access,
and meaningful unknowns. Pick a representative artifact and a small/empty case.
Record baseline: REA/package version, target digest, engine identity, options,
and host.

Choose a correctness oracle independent of the slow path: known fixture
expectations, independently mapped bytes, or a second producer you trust.
Comparing two wrappers around the same faulty decode proves nothing.

### 2. Locate the earliest unnecessary work

Trace one public CLI or MCP task through to its producer. Note phases that
matter: identity checks, native analysis, decoding, projection, serialization,
Evidence retention, cleanup, and extra follow-up calls.

| Observed cost | Prefer |
| --- | --- |
| Repeated scans of validated facts | Reuse order/lookup already established |
| Repeated equivalent engine work | Share a validated result; do not reopen the same binary cold |
| Full reports when only selected facts are needed | `"detail": "summary"` then page retained Evidence |
| Oversized MCP frames / transport constraints | `inspect_analysis_view` on `parent_evidence_id`, or export a bundle |
| Broad bidirectional traces on large JS graphs | Select `node_id` first; narrow seeds before tracing |

Do not invent a cache or batch layer without naming the work it removes.
Projection after materializing a full report can shrink output while leaving
analysis time unchanged — fix that at the producer/request shape.

### 3. Keep one interpretation

Let the producer validate and normalize once. Consumers should query retained
Evidence rather than re-interpret raw dumps. For any reuse, state key,
invalidation, and lifetime (target bytes, engine, options, architecture).

### 4. Compare completed tasks before claiming a win

Re-run the same public workflow before and after with equivalent inputs,
coverage, and Evidence semantics. Report outcome, elapsed time, whether warm
caches were involved, and remaining limits. Smaller JSON alone does not prove
fewer model tokens or better investigation quality.

## Anti-patterns

**Re-running the identical analysis because the client truncated the reply.**
Use retained Evidence IDs.

**Raising only the client tool timeout when the server returned
`provider_timeout`.** Different budgets.

**Optimizing before the facts are correct.** Fix wrong or missing evidence
first.

**Benchmark theater on a toy binary when the real target is a multi-gigabyte
blob.** Measure the representative artifact.
