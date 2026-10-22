# Spoken protocol

## Contents

- Phrasings by stage
- When stuck
- Dry-run discipline
- Questions for an observer in a mock

## Phrasings by stage

| Stage | Example |
| --- | --- |
| Restate | "So given a list of intervals, I need to return the merged non-overlapping ones. Is the input sorted?" |
| Clarify | "Can the list be empty? Can values repeat? Roughly how large can n get?" |
| Example | "Take [1,3], [2,6], [8,10]. The first two overlap, so I get [1,6] and [8,10]." |
| Brute force | "The simple way compares every pair, which is quadratic. That works but is slow for large n." |
| Optimise | "Sort by start; after sorting, each interval only needs comparing with the last merged one, so one pass suffices: O(n log n) time, O(n) space for the output." |
| Code | "I will keep a result list and compare the last merged end to the next start." |
| Dry-run | "Running the first example: result starts as [1,3]; next start 2 is at most 3, so end becomes 6." |

## When stuck

1. Say what you know: "I have the brute force; I am looking for what makes the repeated work avoidable."
2. Return to the examples and look for what is recomputed.
3. Try a smaller or special case: sorted input, one element, all equal.
4. Ask a precise question rather than "can I have a hint": "Would sorting first help here?"
5. If a hint is given, say how it changes the approach; interviewers score how it was used.

Silence for more than about a minute is the thing to avoid. Narrating a dead end is acceptable; hiding one is not.

## Dry-run discipline

Run the code on a small input line by line, tracking variable values on paper or in comments, not in your head. Then run the edge case: empty, single element, duplicates. Most interview bugs are caught here, and an interviewer watching a real dry-run gains confidence even when a bug turns up.

## Questions for an observer in a mock

- Where did my explanation lose you?
- Where would you have given a hint in a real loop?
- Was the dry-run real, or did I assert the result?
- What did I do when stuck that looked calm, and what looked panicked?

Write the answers into the failure log as ordinary rows.
