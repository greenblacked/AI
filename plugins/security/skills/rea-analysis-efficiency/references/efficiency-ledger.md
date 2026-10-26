# The efficiency ledger

Read this before the first measurement, and fill it in again after the fix. The point of the
ledger is that a before-and-after comparison is only meaningful when both rows were produced
the same way. Copy the tables into the task, not into the session transcript, so the numbers
outlive the process that produced them.

## Identity and question

| Field | Why it is needed |
| --- | --- |
| REA version | The engine's behaviour changes between releases; a result without one cannot be reproduced |
| Client id | Which client's policy, timeouts and provider set were in play |
| Target path | What was analysed |
| Target SHA-256 | The bytes, not the path — a path is reused and a digest is not |
| Provider and version | Ghidra, IDA, Hopper, a native scanner — each has its own cost model |
| Options | Detail level, architecture, feature flags |
| Question | The analyst's question, phrased so it can be answered |

A row missing its digest or its version is not a baseline; it is an anecdote about a file that
may no longer exist.

## Baseline

| Metric | How to read it | Baseline | After |
| --- | --- | --- | --- |
| Elapsed time | Wall clock for the whole public workflow | | |
| Producer calls | Calls that do engine work (open, list, match, decompile) | | |
| Follow-up calls | Calls that read or project already-produced Evidence | | |
| Retained Evidence | Count of retained records at the end | | |
| Session context | Bytes or tokens of the transcript the session had to carry | | |
| Output size | Bytes returned to the analyst | | |

Elapsed time and output size are the two that are most often confused. Projection can shrink
the output after the engine has already spent the time; the ledger keeps them apart, which is
the only reason the confusion is visible.

## Oracle

| Field | Value |
| --- | --- |
| What proves the answer is right | |
| Independent of the fast path? | yes / no |
| Verdict before | |
| Verdict after | |

An oracle that is implemented by re-running the same decode proves only that the decode is
deterministic. Prefer one written from the question: a known string, a known function address,
a count that the analyst confirmed by hand, or a second provider.

## Reuse register

For every reuse introduced, record one row. An unregistered reuse is an unstated invalidation
waiting to happen.

| Key | Invalidated by | Lifetime | What it returns |
| --- | --- | --- | --- |
| target digest | a new file | until the file changes | the provider's decoded result |
| target digest + options | a new file, or different options | until either changes | the per-option analysis |
| engine + version | a provider upgrade | until the provider changes | the engine's validated output |

A key that names a path rather than a digest serves the old binary after an update. A key that
omits the options serves the answer to a different question.

## Reading the result

- **Elapsed fell, calls fell, oracle unchanged.** The work moved out of the hot path. Good.
- **Elapsed fell, calls fell, oracle changed.** Coverage probably narrowed; treat it as a
  different analysis until the difference is explained.
- **Output fell, elapsed did not.** Projection, not an optimization. Say so.
- **Elapsed fell only with a warm cache.** The cache is part of the change; report it as such
  and measure the cold path too.

## Close and settle

- Close native sessions with `close_binary` once the investigation is done, so the provider
  releases its engine; export the bundle first if the Evidence is needed later.
- Write down which unknowns the oracle settled, so a later pass does not re-litigate them.
- Before any expensive call, confirm the question still needs REA at all: an artifact that
  ships no binary and has source is a job for ordinary source tools, where none of this
  applies.

## What the ledger cannot show

A single representative artifact is not the fleet; a provider under different load may behave
differently; and a measured improvement on one target says nothing about a target with a
different shape, such as a smaller binary or a different architecture. State the artifact and
the scope beside the numbers rather than after them.
