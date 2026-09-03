# Contributing

This is a personal library, so the bar for a new skill is "I would reach for this", not
"this is generally useful". Issues and pull requests are welcome anyway — particularly
corrections, since several skills assert specific command flags and standards, and a
wrong flag in a skill is worse than no skill.

## Before you open a pull request

```bash
make validate
make test
```

Both are what CI runs. `make lint` runs markdownlint, yamllint and actionlint when they
are installed and tells you the install command when they are not.

If you edit this repository with Claude Code, `.claude/settings.json` registers a
`PostToolUse` hook that runs the validator against whichever skill you just wrote and
reports only that skill's errors. It exists so a dangling `references/` pointer surfaces
while you are still holding the context, rather than in a CI log twenty minutes later.
Warnings are left out of it deliberately — a hook that interrupts on a judgement call is
a hook people delete.

## Adding a skill

Follow [`docs/writing-skills.md`](docs/writing-skills.md). In short: copy
`template/SKILL.md`, name the directory and the `name` field identically, write the
`description` last and make it explicit about when the skill should fire, put depth in
`references/` and write every file you name, write `evals/trigger-eval.json`, then list
the skill in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json).

The eval set is twenty queries — ten the skill should fire on, ten near-misses it should
not. Spend the effort on the negatives: a positive only shows the description is not
inert, while a negative drawn from a neighbouring skill shows it actually discriminates.

The validator will catch every mechanical mistake. What it cannot catch is a skill that
restates general good practice — if a capable model would already do what the skill says,
the skill is costing context and returning nothing. The parts worth writing are the
ordering, the gate, and the command that produces the decisive evidence.

## Correcting a fact

Skills in this repository quote real limits, flags and standards. Several of them were
verified against upstream sources at the time of writing and a few carry an explicit note
where verification was not possible. If you find something wrong, a pull request that
fixes the line and cites the source is the most useful thing you can send.

## Changing the validator

`src/skillcheck/` has no dependencies and must keep it that way — the whole CI design
rests on the validator running anywhere. A change to `rules.py` needs a matching case in
`tests/test_rules.py`; a rule with no test is a rule that will be quietly broken later.

Turning an error into a warning to unblock a change is not the fix. If a rule is wrong,
argue that it is wrong and change it deliberately.

## Commits

One logical change per commit, imperative subject line, and a body that explains why when
the diff does not. Please do not add tool-attribution or `Co-Authored-By` trailers.
