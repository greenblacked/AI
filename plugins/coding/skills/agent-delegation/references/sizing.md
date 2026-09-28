# Sizing a task for one brief

Read this when deciding whether a task is small enough for one brief, or needs handing to `agent-orchestration` instead.

## Contents

- [The roughly-400-line heuristic](#the-roughly-400-line-heuristic)
- [Why it matches code-review's threshold](#why-it-matches-code-reviews-threshold)
- [Splitting a larger task into a sequence of briefs](#splitting-a-larger-task-into-a-sequence-of-briefs)

## The roughly-400-line heuristic

Size the expected diff at roughly 400 changed lines or fewer before writing the brief. This is a planning estimate, not a hard cap enforced after the fact — the useful moment to apply it is before the agent starts, when reshaping the task is still cheap, not after the diff comes back and the only options are accepting an oversized change or asking for a rewrite.

A task that plausibly stays under this size, touches a small and nameable set of files, and can be described in one sentence without an "and" joining two unrelated changes is a good candidate for one brief. A task that needs "and" to describe, or that visibly spans more than a handful of files before any code has been written, is usually two tasks wearing one brief.

## Why it matches code-review's threshold

`code-review` treats a diff far past this size as a signal that review itself will be unreliable — a human or an agent reviewing a very large change either spends disproportionate time on it or, more commonly, skims and misses something. Sizing the task before delegation, rather than discovering the problem at review time, is cheaper for the same reason a bug caught at brief time is cheaper than one caught in production: the fix is a smaller brief, not a large diff someone has to split after the fact or accept unreviewed.

## Splitting a larger task into a sequence of briefs

When a task genuinely exceeds one bounded change, split it along a dependency the agent does not need to resolve itself:

1. **Identify the seam.** A schema or interface change that has to land before the code using it; a refactor that has to complete before new behaviour is layered on top; a shared utility that several call sites will use once it exists.
2. **Write one brief per side of the seam**, each with its own done-check, evidence and scope fence, in the order the seam requires.
3. **Treat each brief's diff as a separate review**, not as a partial change to be batched with the next one — the point of splitting is that each piece is independently reviewable, and batching them again at review time throws that away.
4. **Reach for `agent-orchestration` instead of a sequence of briefs** only when the pieces can genuinely run in parallel with independent ownership of separate files. If they are strictly sequential, a sequence of briefs run one at a time is simpler and needs no coordination machinery.
