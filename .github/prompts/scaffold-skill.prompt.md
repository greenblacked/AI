---
description: Create the directory, SKILL.md and eval-set stub for a new skill in this repository, from the template, in the right plugin.
argument-hint: skill-name and plugin (coding, operations, delivery, gamedev, security, manager, personal, career or design)
agent: agent
---
<!-- source: .claude/commands/scaffold-skill.md sha256: 4237ebeec38631c1c8be69ac4a944e0e1a1b68368a340ae00624fe527836a36d -->

Scaffold a skill named `${input:skill:skill-name}` in the `${input:plugin:plugin}` plugin. If the
plugin is missing, ask which plugin before creating anything: a skill in the wrong plugin ships to
the wrong people.

Refuse and stop if the name is not a lowercase hyphenated slug, or if a skill by that name already
exists in any plugin. Duplicate names validate clean and then overwrite each other at install time,
which is why the validator checks for them.

```bash
skill='${input:skill:skill-name}'
plugin='${input:plugin:plugin}'
test -d "plugins/$plugin/skills" || { echo "no such plugin: $plugin"; exit 1; }
find plugins -type d -name "$skill"          # must print nothing
mkdir -p "plugins/$plugin/skills/$skill/evals"
cp template/SKILL.md "plugins/$plugin/skills/$skill/SKILL.md"
```

Then set `name` to the skill name exactly, and leave the description as the template's placeholder
rather than inventing one. The description is written last, once the body exists, because a
description written first describes the skill you intended rather than the one you wrote.

Create `evals/trigger-eval.json` containing an empty JSON array, so the file exists and the schema
check has something to fail on rather than the skill silently having no evals.

Finally, print what still has to be done before this passes `make validate`:

- the body, following the shape in `docs/writing-skills.md`
- the description, last
- `allowed-tools`, scoped to the minimum the procedure needs
- twenty eval queries, ten a side, with several negatives drawn from the neighbouring skills in the
  same plugin

Then name those neighbours by reading their descriptions, so the author knows which trigger
surfaces the new skill has to stay clear of.

Do not write the body. That is the `new-skill` skill, which explains how.

Full prompt: `.claude/commands/scaffold-skill.md`.
