---
name: technical-interview-prep
description: "Plan weeks of preparation for algorithm and live-coding interview rounds: one interview language, about ten problem patterns with four or five problems each, a 25-minute timeboxed first attempt, a blank-file redo seven days later (only the redo counts), a failure log kept by cause, a spoken protocol, timed mock interviews with another person from week three, and a freeze on new problems three days before the loop. Use when someone says 'I have a coding interview in 6 weeks', 'how many LeetCode problems should I do', 'I freeze when someone watches me code', 'what should I practise first' or 'I forget problems I solved'. Not for CV, behavioural or system-design rehearsal (job-search), a take-home project (take-home-assignment), analysing a loop that already went badly (interview-retrospective), or designing the loop as the employer (hiring-loop)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Technical Interview Prep

A good plan ends with the candidate solving an unseen medium problem aloud, in one language, in about 35 minutes, while another person watches. Volume is not the measure; recall under observation is.

The usual failure is counting problems. Someone reads two hundred solutions, feels familiar with all of them, and then cannot reproduce one from a blank file with a stranger watching. Recognition feels like learning and is not. The second failure is practising silently: the interview is a conversation, and a correct solution delivered in mute panic scores worse than a half-working one explained clearly.

## Scope

Use for: building a multi-week schedule, choosing and ordering patterns, deciding how to review, diagnosing why practice is not sticking, handling nerves when observed, and the last week before a loop.

Do not use for: CV or behavioural and system-design rehearsal (job-search), the take-home format (take-home-assignment), post-mortems on a finished loop (interview-retrospective).

## Workflow

### 1. Fix the inputs before planning

Ask for the loop date, hours available per week, the language the employer permits, and the current level (can they write a hash-map solution to an easy problem without help). Count backwards from the date: the schedule has to fit inside the real calendar, and a plan that needs fifteen hours a week from someone with five is replaced with a smaller scope, not a hopeful one.

### 2. Pick one interview language and keep it

Choose the language the candidate writes fastest and whose standard library has a hash map, a heap, a deque and sorting with a key function built in. Switching languages mid-plan resets the muscle memory for syntax and library calls, and fumbling an import costs minutes under observation. Check the employer permits it; if not, the permitted language is the language, and week one includes learning its container API.

### 3. Build the pattern list

Work through about ten patterns, four or five problems each:

1. Two pointers
2. Sliding window
3. Hash lookup and counting
4. BFS and DFS on grids and graphs
5. Heap and top-k
6. Intervals
7. Binary search, including binary search on the answer
8. Dynamic programming basics (one dimension, then two)
9. Graph algorithms (topological order, union-find, shortest path)
10. Trees (traversals, recursion on subtrees, lowest common ancestor)

Order by how often they appear and how much they unlock: hash lookup, two pointers and sliding window first, trees and BFS/DFS next, dynamic programming after the candidate is comfortable with recursion. Four or five per pattern is enough to see the shape recur; more is diminishing return and displaces mock practice. Name specific problems from a list the candidate already has access to rather than inventing a list; the pattern matters more than the source.

### 4. Run each problem as a two-pass loop

First attempt: timebox to 25 minutes. If there is no working approach at 25 minutes, stop, read or watch a solution, then close it and write the solution from memory the same day. Record the problem, the pattern and the date.

Redo: seven days later, from a blank file, without the notes. Only the redo counts as learned. A problem passes when it is solved correctly within 25 minutes with no look-ups; otherwise it goes back into the queue with a new date. This is spaced recall: the first solve proves little because the solution is still in short-term memory.

### 5. Keep a failure log by cause

Every miss, in the first attempt or the redo, gets one line with a single cause from a fixed list: did not recognise the pattern, recognised it but could not implement, implementation bug, missed an edge case, wrong complexity, ran out of time, froze. Review the log weekly. The dominant cause sets next week's emphasis: pattern recognition failures mean more problems of mixed type; implementation bugs mean slower, more careful dry-runs; freezes mean earlier mocks. Read `references/failure-log.md` for the template and what each cause implies.

### 6. Rehearse a spoken protocol

Say the steps aloud on every practice problem, from week one, so they are automatic by the loop:

1. Restate the problem in your own words and ask about input size, duplicates, empty input and whether the input is sorted.
2. Work through one or two examples by hand, including an edge case.
3. State the brute force and its complexity, even if it is poor.
4. Find the bottleneck and name the technique that removes it.
5. State the optimised approach and its time and space complexity before writing code.
6. Code it, narrating decisions rather than every keystroke.
7. Dry-run it on a small test, line by line, then on the edge case.

The brute-force step is the safety net: it guarantees a working answer exists and gives the interviewer something to steer from. Skipping straight to the clever solution is how candidates burn ten minutes on a wrong idea in silence. Read `references/spoken-protocol.md` for phrasings and for what to do when stuck.

### 7. Add observed practice from week three

Start timed mock interviews with another person from week three: a friend who codes, a peer-practice platform, or a paid mock with an experienced interviewer. One a week is enough; two in the last fortnight. A recorded self-session is a poor substitute for a second person, because the nerves come from being watched, and nerves are the thing being trained. Ask the observer for three notes: where the explanation lost them, where they would have given a hint, and whether the dry-run was real. Log the notes like any other miss.

### 8. Taper

Stop adding new problems three days before the loop. Those days are for redoing problems that previously failed, one light mock if wanted, rehearsing the protocol, and sleep. A new hard problem in the last 72 hours teaches nothing that will stick and risks a confidence hit with no time to recover. Confirm logistics: the platform the employer uses, whether the editor has autocomplete, whether the camera and screen share work.

## Hand back

```text
Loop date / weeks left / hours per week:
Language and why:
Week-by-week schedule: patterns, problem counts, redo dates, mock dates
Failure-log template and the review day
Taper plan (last three days)
One thing to change first, given the stated weak point
```

## Anti-patterns

**Counting solved problems.** The count includes everything read and nothing tested. Count redos passed from a blank file.

**Reading the solution at minute five.** It removes the struggle that makes the pattern memorable. The 25 minutes is the cost of learning; stop at the limit, not before.

**Practising in an IDE with autocomplete and a debugger.** The loop editor may offer neither. Practise at least half the sessions in a plain editor and run only the tests the interviewer would.

**Silent grinding until week five.** Observed practice starts in week three because nerves and narration are skills with their own learning curve.

**Hard problems only.** Mediums are the bulk of real loops. A candidate who fluently solves mediums and explains them well is better placed than one who half-solves hards.

## Reference files

- `references/failure-log.md` - read for step 5: the log template, the cause list with what each implies for next week, and a weekly review routine.
- `references/spoken-protocol.md` - read for step 6 and step 7: example phrasings for each stage, how to recover when stuck, and what to ask an observer in a mock.
