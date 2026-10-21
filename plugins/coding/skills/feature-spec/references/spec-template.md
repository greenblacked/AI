# Spec template

Write the spec in the order below. Keep it short enough that the requester reads all of it; a spec nobody finishes is approved without being read. Every section earns its place by catching a specific kind of misunderstanding before code exists.

## Header

The feature name, the requester, the date, and a status line: `draft`, `approved` or `superseded`. Status is what lets a later reader know whether the file is the contract or a record of an earlier idea.

## Problem

One short paragraph on what is wrong or missing today, for whom, and what it costs them. Describe the situation, not the solution: "support staff re-type the same report into a spreadsheet every Monday" rather than "add CSV export". A problem written as a solution cannot be checked against alternatives in the approaches step.

## Users

Who will use this, and who will be affected without using it. Name the distinct kinds (an admin, an API consumer, the on-call engineer) because acceptance criteria and constraints usually differ between them. If the answer is "everyone", the interview is not finished.

## Constraints

What the solution has to live within, each one sourced: the existing interface it must not break, the dependency it may not add, the performance or data volume it has to handle, the deadline, the platform. Say where each came from, whether the code, the requester or an outside rule, so a later reader can tell a hard limit from a preference. A constraint found by reading the repository goes here without a question to the requester.

## Non-goals

What this change deliberately does not do. Include the neighbouring work a reasonable person would assume is included, each with a one-clause reason: "No PDF export; no one has asked and it needs a layout engine." This section is the main defence against scope creep during execution, because it turns "should I also do X" into a lookup.

## Acceptance criteria

Each criterion is a check someone else could run and get a yes or no. Number them so the plan, the drift log and the final report can refer to them.

Weak: "Export handles large reports."
Strong: "Exporting a report of 100,000 rows completes without error and the file opens with 100,000 data rows plus a header."

Weak: "Errors are handled gracefully."
Strong: "Requesting an export of a report the user cannot view returns 403 and creates no file."

Weak: "The UI is intuitive."
Strong: "A user who has never seen the page finds the export button within the first attempt in a hallway test of three people." Or drop it: if no check can be written, the requirement is a preference, and belongs under open questions.

Phrase each as a command with an expected result, or as numbered steps with an expected outcome. Include at least one criterion for the failure case and one for the boundary of the volume or permission named in Constraints. Where a repository check already exists (a test suite, a linter, a type check), name it rather than describing it.

## Open questions

Anything the interview did not settle, each with who can answer it and what part of the design waits on it. An open question left out of the spec becomes a guess inside the code.

## Chosen approach

Added after the approaches step: the approaches considered in a line each, the one chosen, the reason, and what evidence would reopen the choice. Keep it brief; if the decision is costly to reverse, link to the decision record instead of expanding it here.
