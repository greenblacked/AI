---
name: refactoring
description: "Restructure code without changing behaviour, in steps small enough that each one is provably safe: pin behaviour with a characterisation test before touching code you do not understand, find a seam when there are no tests at all, then apply one operation at a time — rename, extract, inline, move, split a module, break a dependency cycle, replace a conditional — keeping each commit to one kind of change, never mixing a behaviour change with a move, and proving behaviour unchanged before you stop. Use when someone says \"clean this up\", \"this file is 2000 lines\", \"untangle these circular imports\", \"rename this everywhere\", \"extract this into its own module\", or \"make this readable before I add the feature\". Not for judging someone else's change (code-review), writing new code (code-scaffold), choosing test cases (test-design), or moving onto a new major version or API (dependency-upgrade)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git:*), Bash(pytest:*), Bash(rg:*), Bash(lint-imports:*), Bash(pydeps:*), Bash(madge:*)
---

# Refactoring

A refactor is finished when the external behaviour is demonstrably identical — the same suite passes, the same public signatures answer, the same bytes go out — and the history shows a sequence of commits each of which could have been shipped on its own.

Refactoring goes wrong in five ways, and all five are about the size and purity of the step rather than the destination. Someone starts restructuring code they do not understand, so the "obvious" simplification silently drops a branch that existed for a reason nobody wrote down. Someone mixes a behaviour change into a move, so the diff is unreviewable and the bisect that finds the regression lands on a 900-line commit. Someone works for two days without committing, hits a wall, and loses the good half along with the bad. Someone with no tests at all starts editing on the assumption the code is easy to verify by reading. And someone declares victory when the code looks nicer, with no evidence that it does the same thing. The gates below exist so that each of those is impossible rather than merely discouraged.

The habit is worth defending explicitly. GitClear's *The Maintainability Gap* (June 2026), drawn from 623 million changes, puts moved lines at 21% of changes in 2022 and 3.8% in 2026, and code updated after its first year at 1.7% in 2023 and 0.46% in 2026 — a fall of about 74% against that 2023 anchor, alongside the rise in AI-authored volume. It is vendor research and it measures correlation rather than cause, but the direction is consistent across four years: restructuring is now a rare enough act to be worth defending deliberately.

## Scope

Use for: restructuring code you own without changing what it does — extracting, inlining, renaming, moving, splitting an oversized module, breaking a dependency cycle, replacing a conditional with polymorphism or a table, and preparing code for a feature that would otherwise be awkward to add.

Do not use for: judging a change someone else wrote, which is `code-review`; writing something new, which is `code-scaffold`; finding the cause of a defect, which is `debugging`; choosing which cases a suite should contain, which is `test-design`; or a rewrite, which is not a refactor at all — a rewrite changes behaviour in ways nobody has enumerated and needs the plan a migration gets.

## Hard gates

Breaking one of these does not slow the refactor down; it invalidates the claim that behaviour is unchanged.

1. No edit to code you do not understand until a characterisation test pins what it currently does, including the parts that look like bugs.
2. One kind of change per commit. A rename, a move and an extraction are three commits even when they touch the same twenty lines.
3. Never mix a behaviour change with a structural change. If the refactor reveals a bug, commit the refactor, then fix the bug in its own commit, and say so.
4. The suite runs green before every commit, not at the end of the session. A commit that does not pass is a broken bisect point.
5. Start from a clean working tree. A refactor that begins on top of uncommitted work cannot be reverted independently of it.
6. A step that cannot be completed in about thirty minutes is too large — decompose it, or revert and take a smaller bite. Reverting costs half an hour; carrying a broken half-refactor costs the rest of the week.

## Workflow

### 1. Name the smell and the end state

Write one sentence: what is wrong now, and what the code looks like when this is done. "Split `orders.py` so the tax rules live in their own module with no import back into orders" is a destination. "Clean up orders.py" is a mood, and it ends when attention runs out rather than when the work is done.

If the reason is an upcoming feature, say which one. Preparatory refactoring is the strongest case there is — make the change easy, then make the easy change — and it also bounds the work, because anything the feature does not need is out of scope today.

### 2. Establish the safety net

| What you have | Do this first | Because |
| --- | --- | --- |
| A fast suite that covers the code | Run it, note the time, and treat any pre-existing failure as blocking | You cannot tell your breakage from theirs once you start, and a suite with a known-red test gets re-broken silently. |
| Tests that exist but do not cover this path | Add behavioural cases for the paths you will touch, and commit them before touching anything | Tests committed before the refactor are evidence; tests written after it are shaped by the code you just wrote. |
| No tests at all | Write a characterisation test, as below | Without one there is no difference between a refactor and an unreviewed rewrite. |
| No tests and no seam to test at | Find the seam first — see step 3 | The seam-finding is the work; the restructuring afterwards is straightforward. |
| A pure function with a wide input space | Capture current output for a large sample of inputs and diff old against new | This is cheaper than reasoning about a function you did not write, and it catches the branch you did not notice. |

A characterisation test — Michael Feathers' term, from *Working Effectively with Legacy Code* — asserts what the code does today, not what it ought to do. Call it with representative input, observe the output, and paste the observation into the assertion, surprising values included. Where the output is large, record a snapshot and commit it. Name the file so the next reader knows it pins behaviour rather than specifying it, and add a comment on anything you believe is a bug, so the fix later is a deliberate decision instead of an accident.

### 3. Find a seam when there are no tests

A seam, in Feathers' definition, is a place where behaviour can be altered without editing in that place: you change what happens from somewhere else, through an enabling point such as a constructor parameter, an overridable method or a substituted import. Legacy code resists testing because construction, configuration and I/O are entangled with logic, and the fix is to introduce a seam with the smallest possible edit, then test through it.

| The obstacle | The seam to introduce | The smallest safe first edit |
| --- | --- | --- |
| The class constructs its own dependencies | Constructor injection | Add an optional parameter defaulting to the current construction, so every existing caller is untouched and the test passes a stub. |
| A static or global call in the middle of the logic | Extract the call into an overridable method | Wrap the call in a protected method and subclass it in the test — ugly, reversible, and it buys the test that makes the real fix safe. |
| A function that both computes and writes | Split compute from effect | Extract the pure calculation into a new function the effectful one calls; test the pure half immediately. |
| Everything runs in `main` | A callable entry point | Move the body into a function `main` calls, changing nothing else in the same commit. |
| A hard dependency on the clock, the network or randomness | Inject the source | Pass it in with a default; `test-design` covers which seams to use per language. |

Take the seam edit as its own commit with no other change in it, and verify it by running whatever the code does have — the application itself, a manual invocation — before continuing. Read `references/legacy-seams.md` when the code resists every one of these.

### 4. Apply one operation at a time, in order

Order matters because each step makes the next one's diff readable.

1. **Rename** for accuracy, first, and via the tooling rather than find-and-replace. Renaming before extracting means the extracted unit arrives with the right name; renaming after means a second churn over the same lines.
2. **Extract** a function or variable to name a concept, and **inline** anything whose indirection buys nothing. Extraction is the operation that pays for itself most often, because it converts a comment into a name the compiler checks.
3. **Move** the extracted thing to where it belongs — a move commit that changes nothing but file paths and imports is reviewable in seconds, and one that also edits the body is not.
4. **Split a module** once its pieces are already extracted and named. Splitting first produces two files that both import each other.
5. **Break a cycle** by extracting the shared thing into a third module that both depend on, by inverting a dependency behind an interface owned by the consumer, or by moving the type that both need into a module with no dependencies of its own. Ordering imports differently only hides it.
6. **Replace a conditional** with a table, a dispatch map or polymorphism, once the branches are already extracted into functions with identical signatures. Doing this before the extraction produces a class hierarchy over code nobody has read.

Run the suite after each, and commit each with a subject naming the operation: `extract`, `rename`, `move`, `inline`, `split`. The value shows up months later when a bisect lands on a commit whose subject already says it changed no behaviour.

### 5. Prove behaviour is unchanged

Looking right is not evidence. Use at least two of these, and say which you used:

- The full suite green, including the characterisation tests written in step 2.
- A structural diff of the public surface — exported names and signatures before and after. An unintended visibility or signature change is the commonest accidental break.
- For a pure transformation, a differential run: the old and new implementations against the same corpus of inputs, asserting byte-identical output. This is the strongest evidence available and it is cheap for parsers, formatters, serialisers and pricing logic.
- For a service, a shadow or replay run over recorded production traffic, comparing responses.
- For a move-only commit, `git show -M --stat` showing renames rather than deletions and additions, which demonstrates mechanically that no content changed. Once the move is committed `git diff -M --stat` compares the working tree against it and prints nothing; use `git show -M --stat`, or `git diff -M --stat HEAD~1 HEAD`.

Read `references/legacy-seams.md` again at this point when the code has no suite worth trusting and you need evidence anyway; its last section is the differential and replay machinery.

### 6. Stop deliberately

Stop when the destination from step 1 is reached, and note anything you saw and did not do rather than doing it now. An unbounded refactor is how a one-day change becomes a three-week branch that conflicts with everything and gets abandoned.

Land the work in small pull requests, each independently revertible. A branch that has been open for two weeks is accumulating conflicts faster than it is accumulating value.

## Refactoring without a merge window

Large restructurings that cannot land in one commit need a strategy that keeps the trunk working throughout.

Read `references/large-refactors.md` when the change spans more than a handful of files or cannot be finished in one sitting: it chooses between parallel change, branch by abstraction and a delegating facade per situation, and works each one through phase by phase.

## Output format

Report a refactor in this shape:

```markdown
## Goal
[The smell and the destination, one sentence each.]

## Safety net
[Which suite, what it covers, and any characterisation tests added — with their commit.]

## Steps
[Ordered list: operation, what moved, commit subject. One kind of change per line.]

## Behaviour evidence
[Which two proofs from step 5, and their results.]

## Behaviour changes
[Anything that did change, with the reason and its separate commit. Write "none" if none — do not omit the section.]

## Not done
[Smells noticed and deliberately left, so the next person is not surprised by them.]
```

## Anti-patterns

**Refactoring code you have not read the tests for.** You remove a branch that looks dead, and it was the workaround for a client that still calls the endpoint. Characterise first; the surprising branches are the ones that exist for a reason.

**Mixing a fix into a move.** The diff becomes unreviewable, the reviewer approves the shape rather than the change, and the bisect that finds the regression six weeks later lands on a commit nobody can read. Two commits cost thirty seconds and make both halves revertible.

**Find-and-replace as a rename.** It renames the string in unrelated identifiers, in comments that were already wrong, and in the one place where the same word means something else. Use the language server's rename; where none exists, review every hit individually.

**The big-bang restructuring on a long-lived branch.** Two weeks of work that conflicts with everything merged in the meantime, and the resolution silently reverts other people's changes. Parallel change lands the same work in increments that are each mergeable the day they are written.

**Extracting for line count.** Splitting a 300-line function into ten 30-line functions that are each called once and share eight parameters produces a call graph nobody can follow. Extract where there is a concept to name; leave the rest.

**Introducing an abstraction for one implementation.** An interface with a single implementer, a factory that constructs one class, a strategy with one strategy — all cost indirection now and buy flexibility that is speculative. Wait for the second case; it will tell you where the seam actually is.

**Reformatting in the same commit.** A whitespace or import-order pass over a file buries the four lines that matter in a 600-line diff, and `git blame` on that file now points at you for everything. Reformat in its own commit and add it to the blame-ignore list.

**Declaring success because it reads better.** Readability is the goal, not the evidence. Without a green suite, a differential run or a structural diff, "I did not change behaviour" is a belief.

**Refactoring a module nobody touches.** Effort spent where change is infrequent buys nothing measurable. Cross the change-frequency list (`git log --format= --name-only | sort | uniq -c | sort -rn`) with the modules that hurt to work in, and start at the intersection.

**Continuing past the stated destination.** Scope creep during a refactor is unusually easy to justify, because everything you can see is genuinely improvable. Write the extra smells down and stop.

## Reference files

- `references/operations.md` — read when about to perform a specific operation: the mechanics of extract, inline, rename, move, split, cycle-breaking and conditional replacement, each with its preconditions and the check that it was safe.
- `references/legacy-seams.md` — read when the code has no tests and resists testing: the seam types, the smallest edit that introduces each, and how to characterise behaviour before the seam exists.
- `references/large-refactors.md` — read when the change cannot land in one commit: parallel change, branch by abstraction, facades and deprecation windows, and how to keep the trunk green throughout.
