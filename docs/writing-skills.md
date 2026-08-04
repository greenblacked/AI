# Writing a skill

This is the guide to authoring a skill in this repository. It describes the shape on
disk, the frontmatter contract, the rules [the validator](../src/skillcheck/rules.py)
enforces, and how to get from an empty directory to a skill that ships.

## Shape on disk

A skill is a directory containing exactly one `SKILL.md`:

```text
skills/<category>/<name>/
├── SKILL.md          # required: frontmatter + the procedure
├── references/       # optional: depth loaded on demand
├── scripts/          # optional: executable helpers
└── assets/           # optional: templates and files the skill emits
```

`<category>` is one of `engineering`, `manager` or `personal` — the three plugins in
[the marketplace manifest](../.claude-plugin/marketplace.json). `<name>` is the skill
name, and it must equal the `name` in the frontmatter.

The validator treats any directory that directly contains a `SKILL.md` as a skill, so a
second `SKILL.md` nested anywhere below one is an error (`nested-skill`): the Skills API
rejects nested skills on upload.

## The frontmatter contract

Frontmatter is a flat block of scalar keys between two `---` lines, at the very top of
the file. It is read by [a hand-written parser](../src/skillcheck/frontmatter.py) rather
than PyYAML, which makes it stricter than real YAML — tabs, a leading byte-order mark,
indentation and duplicate keys are all rejected rather than silently resolved.

The key set is closed. Only these six are allowed:

| Key | Required | Notes |
| --- | --- | --- |
| `name` | yes | Lowercase letters, digits and single hyphens. Max 64 characters. |
| `description` | yes | Max 1024 characters. No `<` or `>`. |
| `license` | no | Free text. |
| `allowed-tools` | no | Tool restriction for the skill. |
| `metadata` | no | Free-form. |
| `compatibility` | no | Max 500 characters. |

Anything else is an `unknown-key` error. The common near-misses — `tools`,
`allowed_tools`, `allowedtools`, `title`, `desc`, `summary` — are named explicitly in the
error message with the key you probably meant, because the runtime ignores an unknown
key silently and the author never finds out.

Each limit exists for a reason worth knowing:

- **The 64/1024/500 character caps and the angle-bracket ban** come from what the Skills
  API accepts on upload. A description of 1100 characters is not a style problem; the
  skill will not upload. Angle brackets are rejected outright by the same validation, so
  a description mentioning `<region>` breaks the skill rather than reading well.
- **`name` must equal the directory name** for two independent reasons: the Agent Skills
  specification requires it, and [the packaging
  script](../scripts/package_skills.py) names the `.skill` archive and its single
  top-level directory after the directory on disk. Rename a directory without renaming
  the frontmatter and you ship an archive whose contents contradict its manifest.

## The rules the validator adds

The specification does not catch everything that makes a skill broken. These rules exist
because a skill can be perfectly valid and still do nothing.

**Dangling pointers (`dangling-reference`).** Every `references/…`, `scripts/…` or
`assets/…` path named in the body must exist on disk. This is the check the validator
was written for. Two of this repository's oldest skills shipped for months pointing at
reference files nobody had written: `code-scaffold` names `references/terraform.md`, and
`ci-triage` names `scripts/bisect-probe.sh`. Neither file exists. Nothing errors when
this happens — the model reads the pointer, the read fails or is never attempted, and
the skill quietly operates without the depth its author believed it had. A silent
capability gap is the worst defect a skill can carry, because nothing surfaces it.

A path is only treated as a pointer when its last segment contains a dot. A generic
mention such as "put helpers in `scripts/`" is prose, not a pointer, and is ignored.

**Shell scripts (`no-shebang`, `not-executable`).** Every `*.sh` under `scripts/` must
start with `#!` and have the executable bit set. A script the model is told to run and
cannot is the same silent failure in a different costume.

**Marketplace consistency (`unlisted-skill`, `missing-listed-skill`).** A skill on disk
that no plugin lists installs for nobody; a plugin entry pointing at a directory with no
`SKILL.md` breaks installation for everybody. Both are errors, checked against
[`marketplace.json`](../.claude-plugin/marketplace.json).

## The warnings, and why they are warnings

Warnings do not fail the build unless you pass `--strict`. Each is a judgement call
where a false positive is plausible, so it reports rather than blocks.

| Code | What it means | Why not an error |
| --- | --- | --- |
| `description-headroom` | Description is within 50 characters of the 1024 cap. | It works today. The point is that the next edit breaks it invisibly. |
| `no-trigger` | Description has no "use when / whenever / for / any time" clause. | A description can trigger without the exact phrasing; the heuristic is a prompt, not a proof. |
| `long-skill` | `SKILL.md` is over 500 lines. | Length is a signal that depth belongs in `references/`, not a defect in itself. |
| `no-toc` | A reference file is over 300 lines with no table of contents. | Some long references are genuinely linear. |
| `shouting` | `ALWAYS` or `NEVER` in capitals in the body. | Occasionally the emphasis is earned. Reported once per file, not once per occurrence. |

## Writing a description that triggers

The description is the only text loaded before the skill fires. Everything else in the
file is invisible until the decision to load it has already been made. Spend the effort
here.

Under-triggering is the common failure. It happens when the description describes the
skill to someone who already knows what it is — "Comprehensive CI triage methodology" —
rather than naming the situations in which someone would want it. Write for the cold
read: from this text alone, with no memory of having written the skill, would you reach
for it?

Three things make a description fire:

1. **Name the situations.** Not the capability, the circumstance. "A build, pipeline,
   workflow, job or check is failing and someone wants to know why."
2. **Name the casual phrasings.** Users do not type the skill's vocabulary. `ci-triage`
   lists `"CI is red"`, `"the build broke"`, `"this test keeps failing"`, `"my PR is
   blocked"`, `"is this a flake?"`, `"can we just re-run it"`. Those literal strings are
   what actually matches.
3. **Say what it is not for.** An over-broad description that fires on everything costs
   as much as one that never fires — it displaces the skill that should have run.
   `ci-triage` explicitly excludes authoring a new pipeline, debugging an application bug
   CI is only reporting, and running a production incident.

Two skills whose descriptions both plausibly match the same request means neither fires
reliably. Before adding one, read the descriptions of the skills already in its
category and decide which one owns the overlapping case.

## Writing the body

The body is the procedure the model follows once the skill has fired.

**Imperative, not descriptive.** "Check whether main is red before reading a log line",
not "it is generally advisable to consider the state of the main branch."

**Reasoning over shouting.** A rule with its cost attached survives contact with a
situation the author did not anticipate; a capitalised prohibition does not. This is why
`shouting` is a warning — "never retry a non-idempotent step" earns its weight from the
sentence after it explaining that a retried publish is a duplicate artefact and a
retried migration is a corrupted schema.

**Progressive disclosure.** The body is what the model needs every time. Anything it
needs only sometimes goes in `references/`, listed at the end of `SKILL.md` with a
one-line statement of *when* to read it. A lookup table inlined in the body spends
context on every invocation to save one file read on a few.

**A signal to action table beats three paragraphs.** Most of the value in a skill is the
opinionated part: this signal, that class, this specific command with the right flag.
Prose restating general good practice adds nothing the model did not already know. Where
the content is a mapping, write it as a table.

**Assume no conversation.** A skill loads with no memory of the discussion that produced
it. "The approach we discussed" and unexplained internal names are dead weight.

## Adding a new skill

```bash
mkdir -p skills/engineering/log-shipping
cp template/SKILL.md skills/engineering/log-shipping/SKILL.md
```

[`template/SKILL.md`](../template/SKILL.md) carries the shape: a one-sentence statement
of what good looks like, a paragraph on why the job is hard, an explicit `Scope` section
with "use for" and "do not use for", a numbered workflow, and an anti-patterns section.

1. Set `name: log-shipping` in the frontmatter. It must match the directory.
2. Write the description last, after the body exists — you will know what triggers it
   only once you know what it does.
3. Add the skill to the right plugin's `skills` array in
   [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json), keeping the
   array alphabetical:

   ```json
   "./skills/engineering/log-shipping"
   ```

4. Validate:

   ```bash
   make validate
   ```

5. Optionally check that it packages and installs:

   ```bash
   make package
   make install
   ```

`make package` refuses to build an archive for a skill that does not validate, so a
green `make validate` is a precondition, not a formality. For a review that goes beyond
the mechanical checks, hand the draft to the `skill-reviewer` subagent described in
[writing agents](writing-agents.md).

## Validator codes

Run directly with `PYTHONPATH=src python -m skillcheck .`. Useful flags: `--strict`
(warnings become failures), `--skip-marketplace` (skip the manifest cross-check),
`--github` (emit annotations and a job summary; implied under Actions). Exit code 1 means
findings, 2 means the repository layout was unusable.

| Code | Level | Meaning | Fix |
| --- | --- | --- | --- |
| `nested-skill` | error | A second `SKILL.md` below the skill directory. | Move it to its own directory under `skills/<category>/`. |
| `frontmatter` | error | The block could not be parsed at all: missing or unclosed `---`, a tab, a byte-order mark, indentation, a duplicate key, an unreadable line. | Follow the message; it carries the line. |
| `unknown-key` | error | A key outside the allowed six. | Rename it, or delete it. The message names the likely intended key. |
| `missing-name` | error | No `name`. | Add it. |
| `empty-name` | error | `name` present but blank. | Fill it in. |
| `bad-name` | error | Not lowercase letters, digits and single hyphens. | No capitals, underscores, leading, trailing or doubled hyphens. |
| `long-name` | error | Over 64 characters. | Shorten it. |
| `name-mismatch` | error | `name` differs from the directory name. | Change one to match the other. |
| `missing-description` | error | No `description`. | Add it. |
| `empty-description` | error | `description` present but blank. | Fill it in. |
| `angle-brackets` | error | `<` or `>` in the description. | Remove them; upload rejects them. |
| `long-description` | error | Over 1024 characters. | Cut the least load-bearing phrasings, not the trigger list. |
| `description-headroom` | warning | Within 50 characters of the cap. | Trim now, before an edit crosses it. |
| `no-trigger` | warning | No explicit "use when…" clause. | Add one naming the situations. |
| `long-compatibility` | error | `compatibility` over 500 characters. | Shorten it. |
| `dangling-reference` | error | A `references/`, `scripts/` or `assets/` path in the body does not exist. | Write the file, or remove the pointer. |
| `no-shebang` | error | A `scripts/*.sh` file has no `#!` line. | Add `#!/usr/bin/env bash`. |
| `not-executable` | error | A `scripts/*.sh` file is not executable. | `chmod +x` it. |
| `long-skill` | warning | `SKILL.md` over 500 lines. | Push depth into `references/`. |
| `no-toc` | warning | A reference over 300 lines with no contents heading. | Add a `## Contents` (or "Table of contents", or "In this file") heading. |
| `shouting` | warning | `ALWAYS` or `NEVER` in capitals. | Replace with the reason the rule exists. |
| `no-marketplace` | error | `.claude-plugin/marketplace.json` is missing. | Restore it. |
| `bad-json` | error | The manifest is not valid JSON. | Fix the syntax at the reported line. |
| `missing-listed-skill` | error | A plugin lists a path with no `SKILL.md`. | Write the skill, or remove the entry. |
| `unlisted-skill` | error | A skill on disk is in no plugin. | Add it to a plugin's `skills` array. |

CI runs the same validator on every push and pull request; see [what CI checks](ci.md).
