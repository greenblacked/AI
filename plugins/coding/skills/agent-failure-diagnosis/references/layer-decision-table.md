# Layer decision table

Use this after the captures exist and the cheaper explanations are ruled out. The short table in `SKILL.md` names the five layers; this file gives the signals that distinguish them in practice, the check that confirms each, and what to do when one failure fits two.

## Contents

- [How to read a row](#how-to-read-a-row)
- [The table](#the-table)
- [Not a layer: the cheaper explanations](#not-a-layer-the-cheaper-explanations)
- [Telling neighbouring layers apart](#telling-neighbouring-layers-apart)
- [Splitting a failure that fits two layers](#splitting-a-failure-that-fits-two-layers)

## How to read a row

Each row starts from something visible in a capture, not from a guess about the cause. The confirming check is the cheapest observation that separates that layer from its neighbours; run it before changing anything. The first fix is the smallest change at that layer. A row that sends you to another skill names it, because the wording of an instruction file, the design of a guardrail and the sizing of a task each have an owner.

A fresh session means a session that starts from the repository with none of the earlier conversation: a newly started session in Claude Code, a new task or thread in Codex or ChatGPT.

## The table

| # | Signal in the capture | Layer | Confirming check | First fix |
| --- | --- | --- | --- | --- |
| 1 | The agent breaks a convention that is written in the rules file, and a fresh session asked about it cannot quote it | Instructions (not loaded) | Ask a fresh session, with no hint, what the instructions say about the rule. Look for the rule's file against the host's loading behaviour: a file the host does not read at that location, a rule scoped to paths the agent never opened, a file past the host's documented size limit. | Make the host load it: right filename and location, scope that matches, the rule moved ahead of any truncation point. Check the limit in the host's documentation, not from memory. |
| 2 | The session quotes the rule correctly and the run still contradicts it, and two sections of the instructions disagree | Instructions (contradictory) | Put the two sections side by side and ask which one the agent followed in the capture. | Decide which rule wins, delete the other, and say why in one line. Hand the rewrite to `agent-instructions`. |
| 3 | The rule is present once, deep in a long file, and the agent follows items near the top and skips this one | Instructions (buried) | Count the items competing with it; check whether the skipped rule has any marker that it applies before finishing. | Shorten the file by removing what the agent already does unprompted. Move the rule to where it applies, such as a path-scoped rule. Hand the restructure to `agent-instructions`. |
| 4 | The rule states an aim ("keep the code clean", "be careful with migrations") and the agent does something reasonable that is not what the author meant | Instructions (not actionable) | Ask what command or observable result would show the rule was followed. If nothing, it is an aim. | Replace the aim with the exact command or the exact condition. |
| 5 | The instructions name a directory, command or target that no longer exists, and the agent follows them into a dead end | Instructions (wrong content) | Run each command and open each path the file names. | Correct or delete the stale line. A fact that changes with the task belongs in state, not here. |
| 6 | A command fails with "not found", the agent substitutes another approach or skips the step, and the report does not mention it | Tools and permissions | Run the same command in a shell with the agent's environment and PATH. | Install the dependency in the environment the agent runs in, or document the bootstrap step in the one place setup lives. |
| 7 | The test run fails on imports or missing files, the agent concludes the suite is broken and moves on | Tools and permissions (working directory) | Run the same command from the repository root and from the agent's starting directory; compare. | Give the command a wrapper that sets its own directory, such as a make target, and have instructions name the wrapper. |
| 8 | A write or command is denied and the agent either gives up or writes elsewhere to get the effect | Tools and permissions (denial) | Read the denial and the rule behind it. Decide whether the boundary was intended. | If intended, tell the agent the sanctioned route. If not, grant the narrowest permission the task needs. Enforcement design goes to `agent-guardrails`. |
| 9 | The agent cannot reach the network and supplies a dependency version or API shape from memory | Tools and permissions (reachability) | Check what the sandbox allows: fetch the same resource from the agent's shell. | Provide the dependency or the documentation inside the environment, or state in the task that outside access is unavailable. |
| 10 | The agent's results differ from the project's own checks because its interpreter or tool version differs | Tools and permissions (environment parity) | Compare the version output from the agent's shell with what the project pins. | Align the agent's environment with the pinned versions. If the project's CI then fails, that run is `ci-triage`. |
| 11 | A constraint given at the start of a long session is violated hours of work later | State and context (dropped constraint) | Find the turn where the constraint was given and the first action that broke it; note how much intervened. | Split the task. Put the constraint where every fresh session reads it, and restate it at the start of each. Hand a long-running case to `agent-handoff`. |
| 12 | The agent acts on a stale fact: an old branch, a test result from earlier, a summary of a file that has since changed | State and context (stale information) | Compare what the agent believed with the repository at that moment: branch, `HEAD`, the file itself. | Have the step re-read current state before acting on it. Treat a recorded result as belonging to the revision it ran on. |
| 13 | A session resumed from a summary retries an approach that was already tried and rejected | State and context (lost decision) | Look for the rejection in the earlier transcript and for its absence from the carried summary. | Record decisions with the alternatives rejected, in a durable place a successor reads. This is `agent-handoff`. |
| 14 | The same task passes in one session and fails in the next, with no change to the repository | State and context (hidden carried state) | Compare the two runs' starting conditions: leftover files, caches, environment variables, untracked paths. | Start each attempt from a clean worktree at a fixed commit, so earlier runs cannot leak into later ones. |
| 15 | The agent reports "done" and nothing in the repository would reveal that it is wrong: no test, no build, no command that fails | Verification (no check) | Ask what command a person would run to see the result is wrong. If none, the check does not exist. | Add a check that exercises the behaviour and name it where the agent finishes work. Enforcement goes to `agent-guardrails`. |
| 16 | A check exists and passes while the result is wrong: it runs a subset, mocks the part that broke, or passes with no tests collected | Verification (too weak) | Break the behaviour on purpose in a scratch worktree and run the check. If it still passes, it proves nothing. | Strengthen the check until the deliberate break fails it, then remove the break. |
| 17 | The agent edits the test, the snapshot or the expected value alongside the code so the check passes | Verification (writable oracle) | Read the diff for changes to the files the check compares against. | Put the oracle out of the agent's reach for that task, and fence the paths in the brief with `agent-delegation`. Do not loosen the check. |
| 18 | The agent never runs a check that exists, and the capture shows no mention of it | Split: Instructions and Verification, or Tools | Ask a fresh session how it would verify a change here. If it does not name the check, instructions; if it names it and cannot run it, tools. | Fix the one the confirming question points to first; see the splitting section below. |
| 19 | The check runs only after the agent has stopped, such as in a pipeline, so the agent never sees it fail | Verification (late) | Note where in the run the feedback arrives. | Provide a quick version of the check the agent can run before it reports. A red pipeline itself is `ci-triage`. |
| 20 | The diff touches many unrelated files and nobody can say whether it is right | Scope (too large) | Count the concerns in the request; check whether the diff could be reviewed as one change. | Split the request into separate tasks, each with its own done-check. `agent-delegation`. |
| 21 | The agent stops at a plausible point or keeps polishing after the work is done, and the request never said what finished means | Scope (done undefined) | Look for any command or observable condition in the request that decides finished. | Write the runnable done-check into the request before rerunning. |
| 22 | A ticket lists three problems, the agent fixes one and reports the work complete | Scope (compound task) | Compare the report against each item the request listed. | One task per problem, or an explicit checklist the report must address item by item. |

## Not a layer: the cheaper explanations

These explain a failure without any fault in the environment. Rule them out first; they have different owners.

| Explanation | How to recognise it | What to do |
| --- | --- | --- |
| Ambiguous request | Two readers of the captured request describe different deliverables | Rewrite the request. The brief shape is in `agent-delegation`. |
| Real defect in the repository | The check fails at the starting commit with no agent involved | Debug it as product code with `debugging`. |
| Wrong model or effort for the task | A stronger tier passes the same case under the same setup | Pick the tier on purpose for that kind of task; do not compensate with rules. |
| One-off | One capture, and no second occurrence | Wait for the next one and save it. |
| Evaluation harness fault | The failure appears only inside a scored run, and the setup or grader is suspect | That is `agent-evaluation`'s territory: setup outages and graders are classified there. |
| Untrusted content steering the agent | The capture shows text from a page, file or tool result changing what the agent did | `agent-security-review`. |

## Telling neighbouring layers apart

Three pairs get confused in captures.

**Instructions against state.** Instructions are durable text meant to apply to every session in the repository. State is information that belongs to one task or one session: what has been done, what was decided, what is currently true. A rule that is true every time and missing is an instructions failure; a fact that was true yesterday and false today is a state failure, even if it sits in a file.

**Tools against verification.** Tools is about whether the agent could do something at all. Verification is about whether anything would show the result is wrong. An agent that could not run the tests had a tools failure. An agent that ran them and they passed on a broken result had a verification failure. If the agent could not run the check, there is also no verification in practice, so log both and see the splitting section.

**Verification against scope.** A check that cannot tell the result is wrong is verification. A task with no defined finished state, so that any check would be arbitrary, is scope. Writing the done-check is the fix for both, which is why a single change often moves the two together; log them as two rows anyway.

## Splitting a failure that fits two layers

A failure that fits two layers is two failures, because each has its own evidence, its own fix and its own way of being wrong.

1. Write both as separate rows in the log, with the transcript evidence for each.
2. Pick the one whose confirming check gave a definite answer, and change only that. If neither did, take the one that appears earlier in the run.
3. Rerun the captured cases and the control. Record the result against that row alone.
4. Move to the second row only after the first has a result. A change that fixes the second row and also, incidentally, the first is still logged against the one you intended; the other row is closed only by its own rerun.

Typical pairs: the rule is not loaded and nothing checks the result (instructions and verification); the command cannot run and the agent reports success anyway (tools and verification); the task was too large and the early constraint was lost (scope and state). The second member of each pair is often what let the first reach a user, so removing it alone makes the failure louder, not rarer. Fix the cause row first when the evidence allows, and the catching row second.
