# Harness ablation

Read this when an agent's working environment has grown past anyone's ability to say which parts matter, and the model or tooling underneath has changed. It covers removing one component at a time and measuring whether the agent does worse without it. Candidate-against-baseline comparison of a prompt, model or tool stays in `SKILL.md`; this file reuses that machinery for a different question: not "is the change safe to ship" but "does this piece still earn its place".

## Contents

- [When it applies](#when-it-applies)
- [Design](#design)
- [Contamination control](#contamination-control)
- [Confirm a surprising result](#confirm-a-surprising-result)
- [Output: a decision record](#output-a-decision-record)
- [Honest limits](#honest-limits)
- [Worked example](#worked-example)

## When it applies

A component is any part of the environment the agent works inside that someone added to improve its results: an instruction block in `CLAUDE.md` or `AGENTS.md`, a check the agent must run before finishing, a hook, a subagent stage in a pipeline, a context or memory file. Components accrete because each was a sensible fix for a failure someone saw. A stronger model or better tooling can make that fix redundant, and a redundant component is not free: it costs context on every run, adds a step that can itself fail, and hides which parts are doing the work.

Use ablation when the harness has grown, the reasons for its parts are lost, and the model or tooling underneath has changed since they were added.

Do not ablate safety, permission, secret-handling or approval controls to see whether quality suffers. A deny rule, a sandbox boundary, a required approval before a destructive action or a secret scan exists to prevent a rare, severe outcome that a task set sized for quality will not show. Removing one is a security decision with its own owner and review, not an experiment, and "the agent did fine without it" is not evidence for it. List these controls in the plan as out of scope, so their absence from the table is visible rather than silent.

## Design

Remove one component at a time. Two components removed together cannot be told apart if the result moves, and they can mask each other if it does not. Compare each ablated harness against the unchanged baseline.

Use a fixed set of representative tasks. Build it as `references/evaluation-design.md` describes: cases from the work the agent actually does, tagged by family, with the task contract written before any run. Choose the component under test first, then check that at least some tasks in the set plausibly call on it; a check on database migrations is not tested by tasks that never touch one. Draw the choice of components from the development and regression sets. Spend the sealed holdout once, on the final decision to remove something, rather than on every arm, so it stays sealed.

Grade the final state, not the agent's account of it. Use the grader ladder in `references/evaluation-design.md`: tests, validators and state queries first, constraint checks on the diff and filesystem next. An agent without its verification step will often still say the work is done, so a grader that reads the final message cannot see the difference the component makes. Judge-scored qualities are allowed only after calibration, as in step 6 of `SKILL.md`, and never override a failed deterministic check.

Run baseline and ablated harness as a pair on the same case snapshots, repeated the same number of times each, with order varied or randomised and recorded. The repeats are not optional: they are how run-to-run noise is measured. Compare the spread among the baseline's own repeats of a case with the shift between baseline and ablated.

State the decision rule before the first run, in the plan, in these terms: keep the component only if the ablated runs degrade by more than the noise measured from the repeats. Degrade covers the primary outcome, constraint compliance and, where it matters, the invalid-run rate. Any new severe constraint violation in the ablated arm settles the question for that component regardless of the outcome totals. A rule written after reading results is fitted to them. If the result lands near the line, investigate; do not move the line.

## Contamination control

An ablation compares arms that must not know about each other. A harness leaks in ways a single-arm evaluation never meets, because the arms share a repository and a person.

- **One isolated directory per arm and per run.** An isolated run means a clean checkout or worktree at the recorded revision, in its own directory, started in a fresh session with no carried-over conversation. This is the same in Claude Code and in Codex or ChatGPT: a separate directory and a new session. Never switch branches inside one working directory to move between arms; untracked files, caches and a stale index go with you and the arms stop being independent.
- **Reset what an earlier run left behind.** Remove or restore progress files, memory files, scratch notes, logs, transcripts and any checked-in evidence of earlier runs before every run, in every arm. An agent that reads an earlier arm's notes, or a log of how a task was solved, is graded on reading, not on working.
- **Apply the ablation to the harness only.** The ablated arm differs from the baseline by the one component and nothing else: the same model identifier, parameters, tool definitions and limits, recorded as the run envelope in `SKILL.md` step 3. A component removed by editing a shared file in the baseline's directory has changed both arms.
- **Keep the oracle out of reach.** Expected outcomes, hidden fixtures and graders live outside the agent's writable scope and run from their trusted version after the task, as `SKILL.md` step 4 requires. Check that the component being ablated is not what was guarding the oracle: a hook that stopped the agent editing tests is a safety-adjacent control, so treat it under the first section rather than as a quality component.

## Confirm a surprising result

Do not stop at the totals. A result that surprises, in either direction, needs attribution before it becomes a decision.

The dangerous surprise is no degradation. It has two readings: the component does nothing the agent needs, or the task set never exercised it. The totals cannot tell them apart. Open the traces of the baseline runs and ask whether the component fired and changed anything: did the check run and catch something, was the instruction block read and followed, did the subagent stage produce something the next step used. Use the milestone alignment and divergence labels in `references/trace-diagnosis.md`. If the component was never exercised, the result is inconclusive, not a licence to remove it.

A degradation needs the same treatment. Attribute each failed ablated run to what the component did: label the earliest consequential divergence and ask whether the component's absence is the reason, such as a verification omitted that the removed check would have forced. A failure with some other cause, for example a harness fault, is not evidence for keeping the component. A degradation that cannot be tied to the component's function is more likely contamination or a flaky case.

## Output: a decision record

Write one record per component. Each ends in exactly one of three outcomes:

| Outcome | What it needs |
| --- | --- |
| Kept | Ablated runs degraded by more than the measured noise, and the failures trace to what the component does. |
| Removed | No degradation beyond the noise, the traces show the task set did exercise the component, no new severe violation, and the holdout agrees. |
| Inconclusive | Name what to measure next: more repeats, more tasks that call on the component, or a sharper grader. |

Record the component, the model and tooling identifiers it was measured against, the dataset version, the number of repeats, the rule as written beforehand, the paired results and the attribution. Rerun the record whenever the model or tooling changes, since each decision is only a claim about the stack it was measured on; treat a model swap, which `references/model-lifecycle.md` covers, as the prompt to do it. A kept component keeps its record so the next review starts from evidence, not from "we added it for a reason".

## Honest limits

Ablation measures the agent on the tasks in the set and no others. Unit tests of the harness and synthetic controls, such as a stub agent that always passes, show that the plumbing works and say nothing about model performance. A small task set gives results that sit inside the noise, and the right answer there is inconclusive. A component that guards a rare failure is almost never exercised by a modest set, so absence of evidence from the set is weak evidence that the failure cannot happen. Treat inconclusive as a result: it says what to measure next and leaves the component in place meanwhile.

## Worked example

An invented harness for a repository agent that makes small code changes. It has five pieces: a layout-and-naming section in `AGENTS.md`, a planning stage that a subagent runs before any edit, a rule that the agent must run the project's test command before declaring completion, a notes file the agent updates between sessions, and a deny rule preventing writes outside the workspace.

The task set is six cases drawn from the repository's own history: `fix-date-parse-timezone`, `add-csv-export-flag`, `rename-config-key`, `migrate-logger-calls`, `bump-dependency-lockfile` and `split-oversized-module`. The plan, written before any run, states the rule above and notes that the deny rule is out of scope as a security control. Each arm runs from its own clean checkout, every case the same number of times, with the notes file and logs reset before each run.

| Component | Ablated runs against baseline | What the traces showed | Decision |
| --- | --- | --- | --- |
| Test-before-completion rule | Degraded beyond the noise | Failed runs stopped with the build red; the earliest divergence in each was verification omitted | Kept |
| Planning subagent stage | No change within the noise | Baseline agents made the same edits the plan proposed and the plan was often discarded; the stage did fire | Removed, then confirmed once on the holdout |
| Layout-and-naming section | No change within the noise | Only `split-oversized-module` could have used it, and the baseline runs did not open it | Inconclusive; add tasks that create new modules |
| Notes file | Improved slightly, inside the noise | A stale note misled one baseline run on `rename-config-key`; most runs never read it | Inconclusive; add multi-session tasks, then rerun |
| Deny rule on writes outside the workspace | Not run | Out of scope as a security control | Not ablated |

The two clean outcomes needed attribution to earn the label: the test rule because the failures traced to its function, and the planning stage because the traces showed it ran and changed nothing. The naming section is the case the totals alone would have got wrong. The ablated arm looked the same as baseline, but the task set barely called on it, so removal would have been a guess. The record for each also names the model and tooling it was measured against, and the whole table is rerun when either changes.
