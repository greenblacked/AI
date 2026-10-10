# The lesson entry

## Contents

- The four parts
- A worked example
- Lesson or resolution
- Keeping the file honest

## The four parts

1. **The class.** What kind of mistake this is, named generally enough to recognise in a different file. "A retry loop has no upper bound" is a class; "the payments retry was wrong" is an incident.
2. **How it shows up.** The concrete shape, specific enough to search for: the construct, the omission, the symptom. This is the part the inspector actually reads for.
3. **The check that catches it.** The test, lint rule, review step or benchmark case that exercises it. This doubles as a pointer to where the guarantee lives. When the honest answer is "an inspector who notices", say that, and let the benchmark case stand in for the check.
4. **Where it was first found.** The change, slice or run that surfaced it, and which stage found it. Two catches of one class is the signal to promote it.

Keep an entry to a short paragraph per part. The inspector reads the whole file before every run, so length is paid for every time.

## A worked example

```text
### A background job retries without a limit

Class. A retry has no upper bound, so a permanent failure becomes an unbounded load.

How it shows up. A loop or scheduler re-enqueues a failed job on any error, with no
attempt counter, no maximum delay and no distinction between transient and permanent errors.

The check that catches it. Benchmark case "retry-no-limit": a diff adding an unconditional
re-enqueue; the inspector must return FIX naming the missing bound.

First found. Slice "nightly export", by the inspector, in the second Inspect round.
```

## Lesson or resolution

A resolution says what people will try to do: "double-check the retry logic". A lesson says what a reader can fail a diff on. Apply two questions:

- Can a stranger, handed only this entry and a diff, say yes or no?
- Does the entry name something to look for, rather than something to feel?

If either answer is no, rewrite it until it is a lesson, or reject it. Prefer a process change over a resolve to try harder, which is the same rule `yielder` applies to the retro.

## Keeping the file honest

- **Prune on mechanisation.** When a lint rule, test or hook now makes the mistake impossible, remove the entry and name the check in the commit.
- **Split a catch-all.** An entry that three different diffs satisfy is three entries, each with its own case.
- **Evidence, not frequency.** The first-found line carries the evidence; a "seen often" tag cannot be checked and is dropped.
