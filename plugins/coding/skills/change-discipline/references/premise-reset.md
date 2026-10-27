# Premise reset

The rule: when two fixes that rest on the same assumption have both failed the same check, stop. Write the assumption in one sentence, test the assumption itself, and only then touch the code again.

## Contents

- Why a third fix is the wrong move
- What counts as the same premise
- Stating the premise
- Testing it directly
- A worked example
- After the probe

## Why a third fix is the wrong move

A fix is a bet on an explanation. When the explanation is right the fix works, so a failed fix is evidence against the explanation, not against the fix. After one failure the explanation might still be sound and the edit slightly wrong. After two failures on the same explanation, the likelier case is that the explanation is wrong, and every further edit is built on it.

The cost is not only the time. Each failed attempt leaves code behind: a guard, a retry, a defensive default. The attempts accumulate, the symptom changes shape, and the next attempt now has to account for the leftovers. Reverting the failed edits before the reset keeps the probe clean.

## What counts as the same premise

Two fixes share a premise when the same sentence would justify both, however different the edits look. Examples:

- A guard against null in the caller, then a default value in the callee: both assume the value is null at that point.
- Raising a timeout, then adding a retry: both assume the call is slow rather than stuck.
- Reordering two initialisation steps, then delaying one: both assume the order is the cause.

Two fixes on different premises do not trigger the rule. Failing once on "the cache is stale" and once on "the query is wrong" is ordinary debugging.

## Stating the premise

Write one sentence of the form "X is true at the point where Y fails". It has to be specific enough to be false. "Something is wrong with the cache" cannot be false. "The cache returns the value written before the update at the time of the failing read" can.

If the sentence takes more than one clause, there are two premises. Split them and test the one the failed fixes depended on.

## Testing it directly

A probe is a check that would come out false if the premise were wrong. It observes the system, or changes exactly one input on purpose and observes the effect; it never edits the code under suspicion.

- Print, log or assert the value the premise is about, at the exact point it matters, in the failing run.
- Run the failing case with the premise forced true and see whether the failure goes away. If it does not, the premise was never the cause.
- Find a case where the premise holds and the failure still occurs, or where it fails and the program works.

A good probe takes minutes and has two clearly different outcomes. If both outcomes would leave you doing the same next thing, it is not a probe yet.

For the mechanics of isolating a cause when the probe is not obvious, use `debugging`; this rule only decides when to stop and what to test first.

## A worked example

A nightly export sometimes writes a short file. The first fix flushes the writer before closing it. The second fix wraps the close in a retry. The job still produces a short file about one night in ten.

Both fixes assume the writer's buffered data is lost at close. That is the premise: "rows are still buffered in the writer when the file is closed."

Probe: log the count of rows handed to the writer and the count in the finished file, on the failing night's input, and log the writer's buffered size just before close. Outcome: the buffer is empty at close and the writer received fewer rows than the source query returned. The premise is false, and the rows were never handed over: the writer is short against the source query's count, not against what it received.

The new premise is "the source query returns all rows when the export reads it". Probe: run the query's row count at the start and the end of the export. The count at the end is lower than at the start, because a second job archives and deletes old rows while the export pages through the table by offset. Without an isolated snapshot, each page is a fresh read: every row deleted behind the read position (already read) shifts the later rows back one place, so the row that would have opened the next page is never read, at every page boundary. The file is short against the count at the start. The cause is a read that is not isolated from a concurrent write, which no writer-side fix could touch. The two earlier edits are reverted, and the fix goes where the cause is.

## After the probe

- If the premise was false, revert the failed fixes, write the corrected premise, and start from it. Record the reset in the ledger, with the probe and its result.
- If the premise held, the fixes were wrong in detail. Say why each failed before writing the next, so the third attempt differs for a reason.
- If the probe cannot be run, because the failure cannot be reproduced or the point cannot be observed, that is the stop condition for a missing reproduction, and the change waits on it.
