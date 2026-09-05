---
description: Create the directory, SKILL.md and eval-set stub for a new skill in this repository, from the template, in the right plugin.
argument-hint: [skill-name] [engineering, manager or personal]
allowed-tools: Bash(mkdir:*), Bash(cp:*), Bash(python3:*), Read, Write, Glob
---

Scaffold a skill named `$1` in the `$2` plugin. If `$2` is missing, ask which plugin
before creating anything — a skill in the wrong plugin ships to the wrong people.

Refuse and stop if `$1` is not a lowercase hyphenated slug, or if a skill by that name
already exists in any plugin. Duplicate names validate clean and then overwrite each
other at install time, which is why the validator checks for them.

```bash
test -d "plugins/$2/skills" || { echo "no such plugin: $2"; exit 1; }
find plugins -type d -name "$1"          # must print nothing
mkdir -p "plugins/$2/skills/$1/evals"
cp template/SKILL.md "plugins/$2/skills/$1/SKILL.md"
```

Then set `name` to `$1` exactly, and leave the description as the template's placeholder
rather than inventing one. The description is written last, once the body exists, because
a description written first describes the skill you intended rather than the one you
wrote.

Create `evals/trigger-eval.json` containing an empty JSON array, so the file exists and
the schema check has something to fail on rather than the skill silently having no evals.

Finally, print what still has to be done before this will pass `make validate`:

- the body, following the shape in `docs/writing-skills.md`
- the description, last
- `allowed-tools`, scoped to the minimum the procedure needs
- twenty eval queries, ten a side, with several negatives drawn from the neighbouring
  skills in the same plugin

Then name those neighbours by reading their descriptions, so the author knows which
trigger surfaces the new skill has to stay clear of.

Do not write the body. That is the `new-skill` skill, which explains how.
