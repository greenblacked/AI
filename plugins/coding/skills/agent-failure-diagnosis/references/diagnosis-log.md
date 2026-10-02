# Diagnosis log

A log keeps the diagnosis honest: it records what was believed, what was tried and what happened, so a wrong attribution shows up as a run of rows that did not move the result rather than as a feeling that the work is stuck. This file gives the template and one worked example in which the first attribution was wrong.

## Contents

- [The template](#the-template)
- [Rules for filling it in](#rules-for-filling-it-in)
- [Worked example: ledgerline](#worked-example-ledgerline)

## The template

Two records. The first describes each captured case once, plus the control. The second is the log proper, one row per change.

```markdown
## Captures

| Id | Date | Start commit | Model and effort | Request as worded | Agent's claim at the end |
| --- | --- | --- | --- | --- | --- |
| C1 | | | | | |
| K1 (control) | | | | | |

## Log

| # | Failure | Layer | Evidence | Change | Rerun | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | |
```

Each column earns its place:

- **Failure** is the observable behaviour in one sentence, not a cause. "Reported done with a failing generated-file check", not "ignored the rule".
- **Layer** is one of instructions, tools and permissions, state and context, verification, scope. One value per row.
- **Evidence** cites the capture and the turn or call that shows it. A layer with no citation is a guess.
- **Change** is a single edit or setting, described so someone else could make it.
- **Rerun** lists the cases run, each in a fresh session at the same starting commit, how many times each ran, how many passed, and what the control did.
- **Decision** is keep when the result moved, flat when it did not (the change stays in place and counts toward the stop rule), or re-attribute when the stop rule fires and the flat changes are reverted.

## Rules for filling it in

1. Write the row before the rerun, then fill in the result. An expected result written afterwards fits whatever happened.
2. Count flat rows as you go. A flat row stays in place until the stop rule fires. When three consecutive changes do not move the result, revert every change that did not help and re-attribute from fresh captures.
3. A control that changes is a result. Record it, and treat the change as too broad.
4. A fix at a second layer gets its own row, even when a single edit seems to cover both.
5. Keep the failed attribution in the log. The rows that were wrong tell the next reader which signals misled.

## Worked example: ledgerline

The repository is invented: `ledgerline`, a billing service in which a checked-in client library under `internal/gen/` is generated from the API definition by `make generate`, and `make verify` fails when generated files are out of date. The figures belong to the example.

### The failure

In three separate sessions the agent changed handler code, ran the unit tests, and reported the task done. Each time `make verify` then failed because `internal/gen/` was stale. A person pointed it out, the agent corrected it, and the next session did the same.

### Captures

| Id | Date | Start commit | Model and effort | Request as worded | Agent's claim at the end |
| --- | --- | --- | --- | --- | --- |
| C1 | day 1 | a1f09c2 | default, medium | add a currency field to the invoice response | "Done: handler updated, unit tests pass" |
| C2 | day 3 | a1f09c2 | default, medium | return the due date on the payment endpoint | "Done: all tests pass" |
| C3 | day 4 | b72e5d0 | default, medium | rename the refund status to settled | "Implemented and tested" |
| K1 (control) | day 4 | b72e5d0 | default, medium | fix a typo in the README | "Fixed" |

In each of C1 to C3 the diff held handler and test changes and nothing under `internal/gen/`. The control touches no generated file and needs no generation, so a change aimed at generation should leave it alone.

### Ruling out

- Request ambiguity: a colleague asked what to deliver for C1 described the same change.
- Repository defect: in a clean worktree at `a1f09c2`, `make generate` followed by `make verify` succeeded.
- Model and effort: not tested at a higher tier. The same tier handled other tasks in the repository correctly, so this was recorded as not ruled out and not the first suspect.

### First attribution: instructions

`AGENTS.md` mentioned `make generate` once, on line 410 of a long file. In C1 the agent never mentioned generation. A fresh session asked what to do after changing a handler gave a vague answer. That fits buried instructions (row 3 of the decision table), so the log began there.

| # | Failure | Layer | Evidence | Change | Rerun | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Reported done with stale generated files | Instructions | C1 turn 14: no mention of generation; rule at line 410 | Move the generation line to the top, under "before you finish" | C1-C3 each run twice: 0 of 6 passed; K1 unchanged | Flat (1 of 3); leave in place |
| 2 | Same | Instructions | A fresh session now quotes the rule when asked; the runs still skip it | Rewrite the line as the exact command with its reason | C1-C3 twice each: 0 of 6; K1 unchanged | Flat (2 of 3); leave in place |
| 3 | Same | Instructions | Same | Add the line to a checklist the agent must copy into its report | C1-C3 twice each: 0 of 6; K1 unchanged | Flat (3 of 3): stop rule fires; revert rows 1 to 3 and re-attribute |

After row 2 the agent could quote the rule, which should have prompted a rethink. Quoting a rule is not following it, and the evidence had stopped pointing at instructions. By row 3 the file had gained three edits and the failure was unchanged. The stop rule applied: three consecutive changes had not moved the result. Every change that had not helped was reverted, which here meant all three edits and returned the file to its original size.

### Re-attribution from fresh captures

Two new failing runs were saved after the reverts, and the earlier captures were reread without the instructions theory. The tool returns, which the transcript summaries had skipped, said this:

```text
C5 turn 9:   agent runs `make generate`
             returns: ledgergen: command not found; make: *** [generate] Error 127
C5 turn 10:  agent runs `go test ./...` and finishes with "Done: tests pass"
C6 turn 11:  same call, same return, same next step
```

C1 held the same error at turn 12. The agent had been following the rule. It could not run the command, and it then reported success without saying so. Two layers were involved, and the first attribution had assumed neither existed: the generator was missing from the agent's environment (tools and permissions), and the report depended on no check that would have shown the gap (verification). Logged as two failures.

| # | Failure | Layer | Evidence | Change | Rerun | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | `make generate` cannot run in the agent's environment | Tools and permissions | C1 turn 12, C5 turn 9, C6 turn 11: `ledgergen: command not found` | Add the pinned generator install to the setup step the agent's environment runs; no instruction change | C1, C2, C3, C5, C6 twice each: 10 of 10 passed; K1 unchanged | Keep |
| 5 | Reported done though a required command had failed | Verification | C5 turn 10: finishes after unit tests; no check of generated files in the report | Name `make verify` as the done-check in the task brief | C1, C2, C3, C5, C6 twice each: 10 of 10 passed. Generator removed in a scratch worktree: `make verify` failed and the agent reported the failure | Keep |

Row 4 went first because its evidence was a tool return, not an interpretation. Row 5 had its own evidence: the report did not depend on any check, so a command that could not run was invisible. Its change was tested by removing the generator in a scratch worktree, to show the check fails when it should.

### What the log shows

- Rows 1 to 3 are the pattern the stop rule exists for: one attribution, three edits to text, no movement.
- The signal that should have prompted re-attribution earlier came after row 2: the agent could quote the rule and still failed. Evidence of knowing is not evidence of doing.
- The final instruction file is the original. The fix lived in the environment and the done-check, and the instructions never needed more words.
- Routing: the setup change is an environment fix; making `make verify` the done-check is the brief shape `agent-delegation` owns; making a failed generation impossible to report as success, without anyone writing the brief, is the concern of `agent-guardrails`.
