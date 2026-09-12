# Project structure

What Claude Code loads from a project without being asked, what it loads only when it
needs to, and what is only a naming convention. This page is the map for this
repository, but the mechanics are the same in any project, so it doubles as the answer
to "where does this file go".

The distinction that matters is **discovery**. A file Claude Code discovers is found and
used because of where it sits. A file it does not discover is inert until something
points at it, however conventional its name looks. Getting that backwards produces the
most expensive kind of mistake here: a file that looks like configuration, reads like
configuration, and does nothing.

## Contents

- [The map](#the-map)
- [Loaded at session start](#loaded-at-session-start)
- [Loaded when relevant](#loaded-when-relevant)
- [Not discovered at all](#not-discovered-at-all)
- [What this repository has, and what it leaves out](#what-this-repository-has-and-what-it-leaves-out)

## The map

```text
CLAUDE.md                     every session, and every directory above the cwd
CLAUDE.local.md               every session, loaded last, not committed
AGENTS.md                     the portable form; CLAUDE.md imports it with @AGENTS.md
.mcp.json                     MCP servers, shared through git
.claude/
  settings.json               permissions, environment, hooks
  settings.local.json         the same, per developer, not committed
  rules/*.md                  always, or on a path match with `paths:`
  commands/*.md               a slash command per file
  skills/<name>/SKILL.md      on a description match, or /<name>
  agents/*.md                 on a description match, or @agent-<name>
  hooks/*.sh                  nothing; a settings file has to name each one
```

## Loaded at session start

These cost context on every turn, whether or not the session touches what they describe.
That is the budget to think about when deciding what belongs in them.

**`CLAUDE.md`.** Read from the working directory and from every directory above it, so a
monorepo can put shared rules at the root and specific ones in a package. A nested
`CLAUDE.md` below the working directory loads when Claude reads a file in that subtree,
not before.

**`CLAUDE.local.md`.** A first-class feature rather than a deprecated one: it loads
automatically, and it is read *last* at each level. Memory files are concatenated rather
than overridden, so a contradiction between it and the committed `CLAUDE.md` beside it is
resolved arbitrarily — write it to add, not to overrule. It is for preferences that are
yours rather than the project's —
the scratch directory you use, the service you point a local run at. Git-ignore it;
this repository does.

**`AGENTS.md`.** Not a Claude Code feature. It is the cross-tool convention Codex,
Gemini CLI and others read, and the reason this repository keeps its rules there and has
`CLAUDE.md` import them with `@AGENTS.md` — one set of rules rather than two that drift.
[AGENTS.md](agents-md.md) covers what that split costs and what it buys.

**`.claude/settings.json`** and **`.claude/settings.local.json`.** Both load
automatically. Precedence runs highest first: managed policy, then the command line,
then project-local, then the committed project file, then user-level (`~/.claude/`).
Managed policy is the one nothing below it can override, which is the point of it.
Lists merge rather than replacing, so a permission granted at one level is not taken
away by silence at another. The `.local` file is git-ignored for the same reason as
`CLAUDE.local.md`.

**`.mcp.json`.** MCP server definitions at the project root, discovered automatically and
committed so a team shares them. An interactive session asks before trusting servers from
a repository it has not seen; a non-interactive one (`-p`, the SDK, a cloud session) does
not get that prompt, which is worth knowing before putting a server in a repository
strangers run.

## Loaded when relevant

**`.claude/rules/*.md`.** Discovered recursively and concatenated into context — this is
a real loading mechanism, not a convention someone documented. A rule with no
frontmatter loads every session. A rule whose frontmatter carries a `paths:` glob list
loads only once Claude reads a file matching one of those globs, which is what makes it
cheap: the rule arrives when it applies rather than sitting in context all day hoping to
be relevant.

That conditional loading is also its failure mode, and the reason `skillcheck` validates
this directory. A glob with a typo in it matches nothing, so the rule never loads, and
nothing anywhere reports it — the author simply believes a gate is in place that is not.
`make validate` checks this directory for three things:

| Code | Means | Fix |
| --- | --- | --- |
| `dangling-glob` | A `paths:` entry selects nothing in the repository, so the rule never loads. | Correct the glob, or drop the key and let the rule load every session. |
| `empty-paths` | `paths:` is present with no entries, which scopes the rule to nothing. | List a glob, or remove the key. |
| `empty-rule` | The file has no content to load. | Write it or delete it. |

Prose pointers and capitalised shouting are checked as they are in a skill, with paths
resolved against the repository root because that is where a rule's prose points. Brace
groups (`src/**/*.{ts,tsx}`) are expanded before matching, since `pathlib` has none. A
glob is matched against the working tree, so scope a rule to something committed rather
than to `dist/`, which exists only after a build.

This repository has three, each scoped to a path class whose gate fails expensively:

| Rule | Scope | Why it exists |
| --- | --- | --- |
| `.claude/rules/validator.md` | `src/skillcheck/**`, `tests/**` | This package decides whether every other change may merge |
| `.claude/rules/workflows.md` | `.github/workflows/**` | Every item in it is something zizmor or actionlint fails the build for |
| `.claude/rules/skills.md` | `plugins/**/SKILL.md`, `plugins/**/evals/*.json` | The frontmatter contract and the eval floor, at the moment a skill is open |

Each says `AGENTS.md` is the authority and restates only the part that applies to the
file just opened. A rule that grows into a second copy of the contract is how the two
start to disagree.

**`.claude/skills/<name>/SKILL.md`.** Project-level skills are discovered exactly like
the ones a plugin ships: the `description` is resident, the body loads when it fires.
A project skill takes its directory name as its command (`/code-review`); a plugin skill
is namespaced (`/coding:code-review`). Writing one is
[writing a skill](writing-skills.md).

**`.claude/agents/*.md`.** Discovered by walking up from the working directory, with the
closest definition winning a name collision. Claude picks one by matching the
`description`, or you name it with `@agent-<name>` — `@agent-reviewer` here, and
`@agent-plugin:name` for one a plugin ships. [Writing a subagent](writing-agents.md)
covers when delegating beats doing the work inline.

**`.claude/commands/*.md`.** One slash command per file, discovered automatically.
`$ARGUMENTS` captures everything the caller typed, and `$0`, `$1` pick individual
arguments out of it, zero-indexed. A command never fires on its own, so it is the
right shape only for work that takes an argument or that should happen when asked —
[writing a slash command](writing-commands.md) is mostly an argument for writing a skill
instead.

## Not discovered at all

**`.claude/hooks/*.sh`.** Nothing scans this directory. Hooks are configured in a
settings file, as a `hooks` block naming an event, a matcher and a command:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          { "type": "command", "command": "$CLAUDE_PROJECT_DIR/scripts/hooks/skill_hook.py" }
        ]
      }
    ]
  }
}
```

The path in `command` is the only thing that matters; the directory it points into can be
called anything. Diagrams of this layout often list `.claude/hooks/` beside
`.claude/agents/` as though both were discovered, and a script dropped in there on that
belief never runs. This repository keeps its hook at `scripts/hooks/skill_hook.py`,
named from `.claude/settings.json`, which is the arrangement above.

## What this repository has, and what it leaves out

Two entries in the map are deliberately absent here.

**No `.mcp.json`.** Nothing in this repository talks to a service. The validator is
standard library only and runs offline, which is the guarantee the whole pipeline rests
on; adding an MCP server to the project root would hand every contributor a trust prompt
in exchange for nothing.

**No `.claude/skills/`.** The skills here are the product, so they live in
`plugins/*/skills/` where `make package` and `make install` can find them and the
marketplace can ship them. A project-level skill would be one installers never get.

The three-stage loop in `.claude/agents/` — `explorer`, `implementer`, `reviewer` — and
the commands in `.claude/commands/` go the other way: they exist to work *on* this
repository and are not shipped, which is exactly the split the `.claude/` directory is
for.

See also [using the skills](using.md), [writing a skill](writing-skills.md), and
[AGENTS.md](agents-md.md).
