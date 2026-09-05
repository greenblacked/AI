# Writing a slash command

A command is a prompt you invoke deliberately, by name, usually with an argument. It
lives in `commands/` — inside a plugin if it ships to whoever installs that plugin, or in
this repository's own `.claude/commands/` if it is contributor tooling. The filename is
the invocation: `blast-radius.md` becomes `/blast-radius`.

## Contents

- [When a command beats a skill](#when-a-command-beats-a-skill)
- [Shape on disk](#shape-on-disk)
- [The frontmatter contract](#the-frontmatter-contract)
- [Arguments](#arguments)
- [What the validator checks](#what-the-validator-checks)

## When a command beats a skill

This is the only question that matters, and getting it wrong produces the most common
defect in a plugin: a command that restates a skill and adds nothing.

A **skill** fires on its own, when a description matches what someone is doing. Its
whole design problem is triggering: it has to be recognised without being asked for.

A **command** never fires on its own. Someone types it. That makes it the right shape
for exactly two things:

- **Work that takes an argument.** A file path, a run id, a date. A skill cannot be
  handed a parameter; a command is built around one.
- **Work you want run on purpose and not otherwise.** A review, an audit, a report —
  something whose cost or side effects mean it should happen when asked and not when
  merely relevant.

A command that says "use the ci-triage skill" is a worse version of a skill that already
triggers correctly. If the answer to "why is this not a skill?" is nothing more specific
than "it feels like a command", write the skill instead — or improve the description of
the skill that should have fired.

Commands compose with skills rather than replacing them. `/blast-radius plan.json` does
the mechanical part — convert, query, order the output by recoverability — and points at
`iac-review` for the full procedure. Each does what the other cannot.

## Shape on disk

```text
plugins/engineering/commands/blast-radius.md   # ships with the plugin
.claude/commands/skill-doctor.md               # contributor tooling, not shipped
```

Subdirectories are allowed and are scanned, so a plugin with many commands can group
them. A `README.md` in a commands directory is documentation and is skipped.

The filename becomes the slash command, so it has to be typeable: lowercase letters,
digits and single hyphens, at most 64 characters. `Deploy_Thing.md` is an error.

## The frontmatter contract

The key set is closed. Only these five are allowed:

| Key | Required | Notes |
| --- | --- | --- |
| `description` | yes | What the picker shows. Max 1024 characters, no angle brackets. |
| `argument-hint` | no | What to pass, shown beside the name — `[path to plan.json]`. |
| `allowed-tools` | no | Comma-separated, scoped where that carries information. |
| `model` | no | Pin a model for this command. |
| `disable-model-invocation` | no | Keep it out of automatic invocation entirely. |

There is deliberately no `name`: the filename is the name, so a `name` key is a second
source of truth that can disagree with the first. It is rejected as an `unknown-key`.

Unlike a skill, `description` here is not a triggering mechanism — the caller has already
decided. It is a picker label. Say what the command does and what it needs, in one line,
without the "Use this whenever" pushiness a skill description needs.

## Arguments

`$ARGUMENTS` is everything the caller typed. Individual arguments are
**zero-indexed**: `$ARGUMENTS[0]` is the first, and `$N` is shorthand for the same thing,
so `$0` is the first argument and `$1` is the second. This catches people out — it is not
shell numbering, and getting it wrong is silent, because an index with no argument at that
position expands to nothing rather than erroring. Write the body so it still does
something sensible when the argument is absent: `/ci-fail` with no run id should find the
latest failing run rather than stop.

If the body reads an argument, declare `argument-hint`. Without it the picker shows the
command with no indication that it takes anything, so people type the bare name and it
runs against nothing. That is a warning rather than an error because a `$0` inside a
fenced example is not an argument the command actually reads — fenced blocks are excluded
before the check runs.

## What the validator checks

Commands are validated on the same run as skills and subagents.

| Code | Level | Means | Fix |
| --- | --- | --- | --- |
| `frontmatter` | error | The block is missing, unterminated, or not a flat mapping. | Fix the syntax at the reported line. |
| `unknown-key` | error | A key outside the five above. `name` is the usual cause. | Delete it; the filename is the name. |
| `bad-command-name` | error | The filename is not a lowercase hyphenated slug. | Rename the file. |
| `missing-description` | error | No usable `description`, so the picker shows nothing. | Write one line. |
| `angle-brackets` | error | The description contains `<` or `>`. | Use square brackets. |
| `long-description` | error | Over 1024 characters. | It is a label, not a manual. |
| `empty-command` | error | Frontmatter with no prompt body. | Write the prompt. |
| `dangling-reference` | error | The body names a `references/`, `scripts/` or `assets/` path that does not exist. | Write the file or drop the pointer. |
| `no-argument-hint` | warning | The body reads `$1` or `$ARGUMENTS` but declares no hint. | Add `argument-hint`. |
| `shouting` | warning | `ALWAYS` or `NEVER` in capitals. | Explain why the rule matters. |

Run them with everything else:

```bash
make validate
```

See also [writing a skill](writing-skills.md), [writing a subagent](writing-agents.md),
and [what CI checks](ci.md).
