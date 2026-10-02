---
name: agent-instructions
description: "Write or repair a repository's agent instruction file: AGENTS.md and, where Claude Code is used, a CLAUDE.md that imports it, so a cold agent session can work in the repo. Run the real build, test and lint commands first and keep only what was executed, keep the entry file short with pointers to topic files, give every rule its reason and its enforcer, measure size in bytes against Codex's truncation limit, and pass only when a fresh session answers five fixed questions correctly. Use when someone says write an AGENTS.md for this repo, our agents keep ignoring the instructions file, the instruction file got huge, or set up CLAUDE.md and AGENTS.md together. Not for a human README or onboarding guide (technical-docs), shaping one delegated task (agent-delegation), a team rollout plan (ai-enablement), or authoring a skill (new-skill)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git:*), Bash(wc:*), Bash(make:*)
---

# Agent Instructions

An instruction file is finished when an agent session that has never seen this repository, with nothing but the checkout and that file, can say what the project is, build it, change it and prove the change works.

The job is hard because the file is written by someone who already knows the answers. Every command in it feels obviously right to its author, so nobody runs it; every rule feels worth keeping, so nothing is deleted. The file drifts into a mix of stale commands, restated linter config and aspirations, and the agent reading it cannot tell which lines are true. A wrong command costs more than a missing one: the agent trusts it, fails, and then trusts the rest of the file less.

## Scope

Use for: writing a first `AGENTS.md`; repairing one whose commands fail, which agents visibly ignore, or which has grown too large to read; setting up `AGENTS.md` and `CLAUDE.md` side by side so two tools share one set of rules.

Do not use for: a README or onboarding guide aimed at people, which is `technical-docs`. Auditing an existing file by running every command in a throwaway checkout and reporting, which is the `agent-ready` command; this skill writes the file, that command checks one that exists. Shaping a single delegated task, which is `agent-delegation`. Planning how a team adopts AI tooling, which is `ai-enablement`. Writing a skill, which is `new-skill`.

## Hard gates

1. No instruction goes into the file unless its command was executed here and the result recorded. A command nobody ran is a guess, and a guess in this file is read as fact.
2. No file is finished until a fresh session has answered the five questions and each answer was checked by running what it says. Rereading the file yourself is not the test, because you carry the context the file is supposed to supply.
3. A failed answer is a defect in the file. Never rewrite the question, argue the session misread, or hint the answer; fix the file and rerun.

## Workflow

### 1. Evidence before prose

Find the real commands: the build tooling's own files, the CI workflow, the `Makefile` or task runner, the existing instruction file if there is one. Then run them from a clean checkout, a fresh clone or `git worktree add`, so the result does not depend on state you built up while exploring. Record each as a row:

| Command | Directory | Result | Verdict |
| --- | --- | --- | --- |
| the exact text you typed | where you ran it | exit code and the one line that matters | keep, fix or drop |

A command that fails on a clean checkout is a finding in its own right, not a row to omit. It means a missing prerequisite, a stale name or an undocumented service, and the file has to say which, because the next session will hit the same wall. Run only what is safe in a scratch checkout: a command that publishes, deploys, pushes or writes outside the tree is listed with its reason and left unrun, and a command that needs a credential you do not hold is recorded as not run rather than assumed to pass. When a repair starts from an existing file, run every command it contains and let the table decide what survives.

### 2. Shape the entry file

The entry file is short and holds three things: the commands, the boundaries and pointers to deeper files. Depth lives in topic files that are read on demand, because everything in the entry file is paid for on every session whether or not the task needs it.

- **Commands.** Setup, the full verification command, the narrow one that runs a single test, and what counts as passing. Take them from the table in step 1.
- **Boundaries.** What the agent must not touch, each with why. A generated directory, a lockfile, a migration already applied, a file another team owns.
- **Pointers.** One line per topic file saying when to read it: "read `docs/testing.md` before adding or changing a test". A pointer with no trigger is never followed.

Hold every rule to three tests. It carries its reason, because a rule with the cost attached survives a situation its author did not foresee. It names what enforces it, whether a CI job, a hook, a linter or a test, so a reader can tell a gate from a hope. A rule with no enforcement is advice, and is labelled advice rather than dressed as a gate. And do not restate what the repository's linters or tests already enforce: the config is the source of truth, the prose copy drifts, and the agent finds out the config disagrees only when a check fails. Delete a rule whose cause is gone. A file that only grows teaches readers to skim.

Read `references/entry-file-shape.md` when drafting or restructuring the file: it has a skeleton with each section's purpose and a worked before and after on an invented repository.

### 3. Measure the size in bytes

Measure with `wc -c AGENTS.md`, not with a line count, because a handful of very long lines passes a line limit and still blows a byte one. This library's documentation of Codex records that its default is `project_doc_max_bytes`, 32 KiB, that it is configurable, and that past whatever it is set to Codex truncates `AGENTS.md` silently: the cut shows up as a log line and is never reported to the interactive session, so an oversize file reads as complete until the missing part turns out to be the part needed. Check the value your own installation uses rather than assuming the default, and stay well inside it. A file near the limit is a signal to move depth into topic files, not to compress the prose.

Measure every file in the chain, not only the root one. Each `AGENTS.md` from the project root down to the working directory counts for Codex, so a package-level file is added to the root file rather than replacing it. Write package-level files to add or override the root and never to restate it, and say so when two instructions conflict.

### 4. Run the fresh-session test

This is the pass gate. Start a session that has no conversation history and nothing but the repository and the instruction file, and have it answer five fixed questions: what is this, how is it laid out, how do I run it, how do I verify a change, where does unfinished work live. Then run what each answer says and judge the answer against what happened.

A fresh session means a different thing per tool. In Claude Code it is a new session in the repository, or a fresh subagent given only the repository path and the questions. In ChatGPT or Codex it is a new conversation or session pointed at the checkout. In every case it must not receive your summary of the repo, or you are testing your summary.

A failed answer means the file is wrong, never the question. Fix the file and rerun with another fresh session, because the one that failed has now seen the answer. Read `references/fresh-session-test.md` before running the test: it has the five questions in full, how to score each against evidence, how to run it in each tool, and which part of the file to fix for each kind of failure.

### 5. Two tools, one set of rules

When Claude Code and another agent both work in the repo, keep the shared rules in `AGENTS.md` and make `CLAUDE.md` an import plus whatever is true of Claude Code alone. The reason is how the two tools choose a file: Claude Code reads `AGENTS.md` only when there is no `CLAUDE.md`, and once a `CLAUDE.md` exists it reads that instead. A `CLAUDE.md` that does not pull the rules in leaves Claude Code working from a different file than every other tool. The import is one line:

```markdown
@AGENTS.md

## Claude-specific notes

Only what applies to Claude Code and not to other agents.
```

Prefer the import to a symlink, which on Windows needs Administrator rights or Developer Mode. A relative import path resolves against the file that contains it, and a path in a code span or fence is text rather than an import. Keep the Claude-specific half small, since it must not contradict the shared file. Then run the step 4 test in each tool the repository supports, because each reads a different file or chain, and a pass in one says nothing about the other.

## Symptoms

| What people report | Check first |
| --- | --- |
| Agents ignore the file | Does a `CLAUDE.md` exist that does not import it? Is it past the size limit? Are its commands failing, so the rest is distrusted? |
| The file got huge | Move depth into topic files, delete rules whose cause is gone, drop anything a linter already enforces. |
| An agent edits what it should not | Is the boundary stated with its reason, and does something enforce it? |
| Works for one tool, not the other | Which file does each tool read? Rerun the fresh-session test in both. |

## Anti-patterns

**The generated dump.** A tool summarises the repo into a file nobody ran. It reads plausibly and fails on the first command. Treat generated text as a draft, and run every line before it stays.

**The restated linter.** Indentation, quote style and import order are already enforced; the prose copy only drifts. Point at the config or say nothing.

**The rule with no owner.** "Keep functions small" has no reason, no enforcer and no test. It is advice at best; label it or cut it.

**The aspirational section.** Describing the process the team wishes it had teaches the agent to distrust the true parts.

**Testing with the author's context.** Rereading your own file proves nothing, since you fill every gap without noticing. Only a session with no history shows the gaps.

## Reference files

- `references/entry-file-shape.md` — read when drafting or restructuring the entry file: the skeleton, what each section is for, and a worked before and after.
- `references/fresh-session-test.md` — read before running the pass gate: the five questions in full, scoring against evidence, how to run it in Claude Code and elsewhere, and what each failure says to fix.
