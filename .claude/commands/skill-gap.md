---
description: Survey the library for what it does not cover — a topic with dangling demand and no owner — and say which of skill, subagent, command or nothing it deserves.
argument-hint: '[plugin name, or a topic to test for coverage]'
allowed-tools: Bash(python3:*), Read, Grep, Glob
---

Survey `$0` for coverage the library does not have. With no argument, survey the whole
library, plugin by plugin, ordered by which plugin has the most headroom under the
runtime's listing budget — take the per-plugin totals from step 4 and start with the ones
furthest under 8,000 characters, because a skill landing there keeps its description.

## 1. Read descriptions, never bodies, and test the sense rather than the word

Use the repository's own frontmatter parser, not grep: some descriptions are YAML block
scalars, and a fixed `-A` count truncates them.

```bash
python3 scripts/run_trigger_eval.py --skill plugins/coding/skills/new-skill --show-listing
```

That prints every description in full, free, with no model call — any one target will do,
since the listing it renders is the whole catalogue. Adding `--budget 8000` instead shows
what survives when the listing overflows, which is a different question: it blanks
descriptions until the rest fits, so it is for seeing what is lost, never for reading.
A cache mention in a skill body does not establish coverage: CI caches, prompt caching
and BuildKit cache mounts do not imply ownership of runtime application caching. Inspect
the complete descriptions to decide which procedure actually claims the request; a word
search can report a gap backwards in both directions.

## 2. Generate candidates from the library's own dangling demand, not free-form

Do not brainstorm a topic list. Three mechanical places demand shows up, and all three
are checkable where a topic list is not:

- a cede clause pointing at something that does not do the job it was ceded for
- a template or output block asking for a section nothing produces
- a checklist item with no named owner

## 3. Apply the go/no-go test by citing it, not restating it

Judge every candidate against step 1 of `plugins/coding/skills/new-skill/SKILL.md`
("Decide whether it should be a skill"). Point at it; do not copy its three criteria into
this command's output. Two rubrics for one judgement is drift — if the wording here ever
disagrees with what that step actually says, this command is wrong, not the skill.

## 4. Check the destination's budget before developing the idea

Four numbers bind:

- the plugin ceiling in `listing-budget.json`, raisable with a reason in the commit
- the 8,000-character runtime default, distinct from the recorded plugin ceiling and a
  user's configured listing budget
- `DESCRIPTION_TARGET` of 900 for anything new
- the 500-character floor `short-description` warns under

```bash
python3 scripts/check_listing_budget.py
```

This prints each plugin's measured total against its ceiling and flags the ones over the
runtime default. That is where the per-plugin numbers come from; step 1's listing does
not carry them. Raising a ceiling is the same script with `--update`, and the reason for
raising it goes in the commit.

Where a plugin is already over the runtime default, the budget stops sizing the
description and starts deciding whether a description is worth writing at all, because
the runtime will drop it. That is step 5, not a veto. Note the known gap before trusting the
ceiling alone: `ceiling_for()`, the function that computes it, adds slack above the
measured total, so the listing-budget gate can pass characters the runtime would drop.
Compare the plugin's measured total from step 1 against 8,000 directly, not only against
its ceiling.

## 5. In an over-budget plugin, read the name with the description covered up

Cover the description and read only the skill name, because that is what survives the
budget once the description is dropped. If the name alone cannot carry the trigger, a
skill is the wrong shape for that plugin regardless of how well the description reads.

## 6. Check cessions both ways, and twice over

For any existing cede clause the candidate would sit behind, or any it would receive:
does the target's own description actually claim the act being ceded to it, and does the
target's eval set contain a positive for that exact query? `dangling-cede` checks only
that the name resolves to a real skill or subagent, not that the claim is true or that
the eval set backs it up. The threat-model misroute survived in four places at once — a
description, a body, a reference file and an eval set — because nothing compares two
eval sets against each other.

## 7. Say which of four shapes, explicitly

Skill, subagent, command, or nothing — pick one and say why. For an over-budget plugin
the budget argues for a subagent, since a subagent's description costs nothing against
the listing. For a skill and subagent that would sit side by side, the skill's
description must claim a different act than the subagent performs; when it does not, the
fix is a handoff line in the skill's body, not a longer subagent description.

## 8. Score the neighbours, not only the candidate

```bash
python3 scripts/run_trigger_eval.py --skill plugins/<plugin>/skills/<neighbour> --runs 3
python3 scripts/run_trigger_eval.py --agent plugins/<plugin>/agents/<neighbour>.md --runs 3 --jobs 2
```

Run-to-run noise is about five points, so read the gap and the failure mode rather than
the digits. This calls a model for every query, so it costs real money — say what it is
about to run before running it.

## 9. Expect a refusal

The normal output of this survey is a documented no. Put the reason in the commit
message, because a refusal with no reason recorded looks identical to a survey nobody
ran.

## Hand off

Do not write the skill, subagent or command this turns up. Report the gap, the shape
from step 7, and the citation for the go/no-go judgement from step 3, then stop. Writing
a skill is `new-skill`'s job and its step 1 owns the go/no-go test used above; writing a
subagent follows `docs/writing-agents.md`; writing a command follows
`docs/writing-commands.md`.
