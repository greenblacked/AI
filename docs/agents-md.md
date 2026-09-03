# AGENTS.md and CLAUDE.md

## What AGENTS.md is

`AGENTS.md` is a README for coding agents. It holds the things a human contributor picks
up by osmosis and an agent cannot: how to build, how to run the tests, which commands are
the real ones, what the conventions are, and what will get a change rejected. Putting
that in the human README clutters it; putting it nowhere means every agent session
rediscovers it, usually badly.

The format is open and is now stewarded under the Linux Foundation's Agentic AI
Foundation. It is read by a long list of agents and editors — Codex, Cursor, Jules,
Gemini CLI, Aider, Zed, GitHub Copilot coding agent, and others — which is the whole
point: one file instead of one file per vendor.

There are no required fields and no required headings. It is Markdown, and agents read it
as prose. The headings that have become conventional through use are:

- **Project overview** — what this is, in three sentences.
- **Setup commands** — how to get to a working checkout.
- **Code style** — the conventions a linter does not encode.
- **Testing instructions** — the exact command, and what counts as passing.
- **PR instructions** — title format, what must be green, what must be updated.
- **Security considerations** — what must never be committed or executed.

## Nested files

A monorepo can carry an `AGENTS.md` per package. The stated rule is nearest file wins:
the one closest to the file being edited takes precedence.

The honest nuance is that implementations generally do not read *only* the nearest file.
Most concatenate the ancestor chain from the repository root down to the nearest
directory, so the root file is still in context and the nearer file overrides it where
they conflict. Write with that in mind: a package-level file should add and override, not
restate the root. Contradicting the root file without saying so produces two instructions
in context with no marker for which one is current.

## The Claude Code relationship

This is the part people get wrong.

**Claude Code reads `CLAUDE.md`, not `AGENTS.md`.** Dropping an `AGENTS.md` into a
repository does nothing for Claude Code on its own. The supported pattern is a
`CLAUDE.md` that imports it:

```markdown
@AGENTS.md

## Claude-specific notes

Anything that applies to Claude Code and not to other agents goes here.
```

A symlink from `CLAUDE.md` to `AGENTS.md` also works, and on macOS and Linux it is a
one-liner. It is a poor default because creating a symlink on Windows requires
Administrator rights or Developer Mode, so a contributor on Windows gets a broken
checkout or a literal text file containing a path. The import works everywhere, and it
leaves a place to put Claude-specific content that would be noise for other agents.

### Import rules

The `@path` syntax has a few rules worth knowing:

- **Relative paths resolve against the file containing the import**, not against the
  working directory. An import inside `packages/api/CLAUDE.md` written as
  `@../../docs/style.md` resolves from `packages/api/`.
- **Recursion is allowed, to a maximum depth of 4.** An imported file may import
  further files. Beyond four levels the chain stops.
- **Import parsing skips code spans and fenced code blocks.** A path written in
  backticks, or inside a fence, is text — not an import. That is how this document can
  discuss `@AGENTS.md` without importing it, and it is the escape hatch when you need to
  show a literal path.

Absolute paths and `~`-relative paths are also accepted.

### `/init`

The `/init` command generates a starting `CLAUDE.md` by reading the repository. It also
reads existing Cursor rules and Copilot instructions, so a repository that already has
vendor-specific rules does not start from nothing. It reads `AGENTS.md` when
`CLAUDE_CODE_NEW_INIT=1` is set in the environment:

```bash
CLAUDE_CODE_NEW_INIT=1 claude
```

Then run `/init` inside the session.

## How this repository arranges it

This repository uses exactly the import pattern above.
[`AGENTS.md`](../AGENTS.md) at the root holds everything vendor-neutral: the project
overview, the repository layout as a table, setup and testing commands, how to add a
skill, code style, commit and pull-request rules, security considerations, an explicit
boundaries section, and a closing review checklist.

[`CLAUDE.md`](../CLAUDE.md) is four lines of substance: the `@AGENTS.md` import, a note
that the subagents in `plugins/engineering/agents/` are the intended way to do heavy
reading here, and a note
to use plan mode for anything touching `src/skillcheck/` or `.github/workflows/`, since
those two decide whether every other change is allowed to merge.

The import, rather than a symlink, because a symlink needs Administrator or Developer
Mode on Windows and this repository is public.

## Writing a good one

Three patterns are worth stealing, taken from repositories where the file has clearly
been maintained rather than generated once.

**A module map.** `apache/airflow`'s file spends its length telling the agent where
things live — which directory owns which concern, and which ones are generated and must
not be edited by hand. This is the single highest-value section, because the alternative
is the agent spending its first several tool calls reconstructing the layout, and
sometimes reconstructing it wrong. For this repository the map is short: `skills/` by
category under `plugins/`, `plugins/engineering/agents/`, `src/skillcheck/`, `scripts/`,
`template/`.

**The one shortcut that saves a wasted cycle.** `openai/codex`'s file names the fast path
explicitly — the narrow test command to run instead of the full suite, and the exact
formatting invocation — because an agent that guesses will run the slow thing, or run the
wrong thing and get a confusing failure. Find the place in your repository where an agent
predictably burns a cycle and write the command down. Here it is that the validator needs
`PYTHONPATH=src`, and that `make validate` already handles it.

**A closing review checklist.** `temporalio/sdk-java`'s file ends with a list the agent
verifies its own work against before declaring done. This works better than the same
content scattered through the document, because it is read at the moment it applies. Keep
it short and make every line checkable: a checklist item the agent cannot verify is
decoration.

Two things to avoid. Do not restate what a linter already enforces — the config is the
source of truth and the prose will drift from it. And do not write aspirations: the file
describes the repository as it is, and an instruction that does not match reality teaches
the agent to distrust the rest of it.

Related: [writing a skill](writing-skills.md), [writing a subagent](writing-agents.md),
and [what CI checks](ci.md).
