# Writing a skill

This is the guide to authoring a skill in this repository. It describes the shape on
disk, the frontmatter contract, the rules [the validator](../src/skillcheck/rules.py)
enforces, and how to get from an empty directory to a skill that ships.

## Shape on disk

A skill is a directory containing exactly one `SKILL.md`:

```text
skills/<category>/<name>/
├── SKILL.md          # required: frontmatter + the procedure
├── evals/            # trigger-eval.json: the queries that prove the description fires
├── references/       # optional: depth loaded on demand
├── scripts/          # optional: executable helpers
└── assets/           # optional: templates and files the skill emits
```

`<category>` is one of `engineering`, `manager` or `personal` — the three plugins in
[the marketplace manifest](../.claude-plugin/marketplace.json). `<name>` is the skill
name, and it must equal the `name` in the frontmatter.

Keep references one level deep. A file under `references/` should not point at another
file under `references/`, because a file reached through a chain of references is the one
most likely to be read partially — the model follows the first pointer, reads the head of
the second file, and proceeds on incomplete information without anything going wrong
visibly. If two references genuinely need each other, name the second in `SKILL.md` as
well so it is reachable in one hop, or fold them together.

The validator treats any directory that directly contains a `SKILL.md` as a skill, so a
second `SKILL.md` nested anywhere below one is an error (`nested-skill`): the Skills API
rejects nested skills on upload.

## The frontmatter contract

Frontmatter is a flat block of scalar keys between two `---` lines, at the very top of
the file. It is read by [a hand-written parser](../src/skillcheck/frontmatter.py) rather
than PyYAML, which makes it stricter than real YAML — tabs, a leading byte-order mark,
indentation and duplicate keys are all rejected rather than silently resolved.

Block scalars are the one place strictness is not enough, and the parser folds them the
way YAML does: both indicators (`>` and `|`), all three chomping modes (`>-`, `|+` and
the bare form), and relative indentation preserved inside a literal block. This is not
pedantry. The 1024-character cap on `description` is measured against the folded string,
so a parser that disagrees with YAML about where the newlines go polices a string the
runtime never sees — which is what happened before, on any block containing a paragraph
break. Explicit indentation indicators (`|2`) are not supported; use a quoted scalar if
you need one.

The key set is closed. Only these six are allowed:

| Key | Required | Notes |
| --- | --- | --- |
| `name` | yes | Lowercase letters, digits and single hyphens. Max 64 characters. |
| `description` | yes | Max 1024 characters. No `<` or `>`. |
| `license` | no | Free text. |
| `allowed-tools` | no | Comma-separated tool restriction, scoped per binary where that carries information: `Bash(kubectl:*)` says something, `Bash` does not. Optional in the standard, but every skill here sets it. |
| `metadata` | no | Free-form. |
| `compatibility` | no | Max 500 characters. |

Anything else is an `unknown-key` error. The common near-misses — `tools`,
`allowed_tools`, `allowedtools`, `title`, `desc`, `summary` — are named explicitly in the
error message with the key you probably meant, because the runtime ignores an unknown
key silently and the author never finds out.

Six is not this repository's preference; it is what the distribution boundary allows.
Claude Code itself accepts many more — `when_to_use`, `argument-hint`,
`disable-model-invocation`, `context: fork`, `paths`, `hooks` and others — but the
[skills reference](https://code.claude.com/docs/en/skills#using-skill-frontmatter-outside-claude-code)
is explicit that claude.ai uploads, the Skills API and `package_skill.py` accept only
`name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`, and
that any other key fails packaging or upload with a hard error:

```text
Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name
```

Every skill here has to survive `make package`, so the validator names those keys
specifically and says why, rather than reporting them as merely unexpected. The one that
stings is `when_to_use`: it is exactly the trigger-phrase surface these descriptions carry,
and the answer is to put that text in `description` itself. Forgoing the rest is the price
of portability, and it is a standing decision rather than an inherited one.

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
`assets/…` path named in the prose of the body must exist on disk. This is the check the
validator was written for. Two of this repository's oldest skills shipped for months
pointing at files nobody had written: `code-scaffold` named `references/terraform.md`,
`ci-triage` named `scripts/bisect-probe.sh`, and neither existed. Nothing errors when
this happens — the model reads the pointer, the read fails or is never attempted, and
the skill quietly operates without the depth its author believed it had. A silent
capability gap is the worst defect a skill can carry, because nothing surfaces it. Both
files exist today because the check made their absence loud.

Two things narrow what counts as a pointer.

A path is only treated as a pointer when its last segment contains a dot. A generic
mention such as "put helpers in `scripts/`" is prose, not a pointer, and is ignored.

Fenced code blocks are skipped entirely, backtick and tilde fences alike. A path inside a
fence is almost always an illustration — a directory tree showing how some other project
is laid out, or a command the skill tells the user to run against their own repository —
not a pointer the model is expected to follow. Treating those as pointers made it
impossible to document a layout without failing the build, a poor trade for a check whose
purpose is to catch pointers written in prose.

For an author that means: a path in prose is a promise that the file exists, and that
includes one in inline backticks — `references/x.md` in a sentence is checked. A path in a
fence is a picture, and nothing is checked. If you are showing a layout, fence it; if you
are telling the model to read something, do not. Only fenced blocks are exempt, so a
four-space-indented code block is still scanned.

**Shell scripts (`no-shebang`, `not-executable`).** Every `*.sh` under `scripts/` must
start with `#!` and have the executable bit set. A script the model is told to run and
cannot is the same silent failure in a different costume.

**Marketplace consistency (`unlisted-plugin`, `missing-listed-plugin`, `unowned-skill`,
`unowned-agent`).** Each plugin owns its own directory and discovers its own `skills/`
and `agents/`, so [`marketplace.json`](../.claude-plugin/marketplace.json) lists plugins
rather than individual skills. Two things still have to hold, and both are errors: every
listed plugin must exist and carry a `.claude-plugin/plugin.json`, and nothing on disk
may be stranded outside a plugin — a skill no plugin ships installs for nobody, which is
the same silent failure the explicit list used to catch.

## The warnings, and why they are warnings

A warning is a judgement call where a false positive is plausible, so the level exists to
say "this is an opinion, not a rule". It does not mean you can leave it standing: both
`make validate` and CI run with `--strict`, which turns every warning into a build
failure. A warning nobody has to clear is one that accumulates until the whole category
is ignored, and a category everyone ignores is worse than no check at all. If a warning
is genuinely wrong for a skill, the answer is to fix the skill or fix the check — not to
walk past it.

| Code | What it means | Why it is a warning and not an error |
| --- | --- | --- |
| `description-headroom` | Description is within 50 characters of the 1024 cap. | It works today. The point is that the next edit breaks it invisibly. |
| `no-trigger` | Description has no "use when / whenever / for / any time" clause. | A description can trigger without the exact phrasing; the heuristic is a prompt, not a proof. |
| `long-skill` | `SKILL.md` is over 500 lines. | Length is a signal that depth belongs in `references/`, not a defect in itself. |
| `no-toc` | A reference file is over 100 lines with no table of contents. | Some long references are genuinely linear. |
| `shouting` | `ALWAYS` or `NEVER` in capitals in the body. | Occasionally the emphasis is earned. Reported once per file, not once per occurrence. |
| `no-evals` | The skill has no `evals/trigger-eval.json`. | A skill can be correct before anyone has written its eval set; the rest of the eval rules are errors once the file exists. |

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

## The listing budget

Every description a plugin ships is resident in context for the whole session, whether or
not the skill ever fires, and the runtime caps the whole listing at about **1% of the
context window** — roughly 8,000 characters on a 200k-token model. When the listing
overflows, Claude Code keeps every skill's name but
[drops the descriptions of the least-used skills](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short),
so those skills can still be invoked by name and stop being chosen on their own. A
newly installed skill has never been used, so it is first to lose its description.

This repository's forty descriptions total about 36,000 characters; `engineering` alone is
over twice the budget. `make validate` prints the per-plugin total on every run, and
`--listing-budget CHARS` turns exceeding it into a warning:

```bash
PYTHONPATH=src python -m skillcheck . --listing-budget 8000
```

It is not a gate, because the fix is not on the author's side: at twenty-one skills, even
descriptions cut to five hundred characters would still overflow. What the number tells
you is which of two things to do. Installers of more than one plugin should raise
`skillListingBudgetFraction` in their settings, or mark rarely used skills `"name-only"`
in `skillOverrides`. Authors should keep descriptions inside the 500–900 guidance rather
than at the cap, and should score them with `--budget` to see what the runtime actually
shows.

## Trigger eval sets

A description that reads well and never fires is indistinguishable from a good one until
something measures it. That is what `evals/trigger-eval.json` is for: a JSON array of
twenty queries, ten that should fire the skill and ten that should not.

```json
[
  {"query": "CI is red again on the payments service, third time today", "should_trigger": true},
  {"query": "add a new github actions workflow that publishes to npm on tag", "should_trigger": false}
]
```

A negative may also name the sibling that **should** win that query:

```json
  {"query": "pods are crashlooping since the 11:40 deploy", "should_trigger": false, "expected": "k8s-triage"}
```

Without `expected`, a negative passes whenever anything other than this skill is chosen —
including `NONE`, and including a completely wrong neighbour. That means the harness can
see a description failing to fire, but not a description stealing a query from the skill
that owns it, which is the failure the negatives exist to catch. With `expected`, the
negative passes only when the named sibling is chosen, and the run reports a separate
routing number over the negatives that carry one. Write it on every negative where you
can name the owner; leave it off the genuinely ownerless ones.

The validator checks the schema of that file on every run, and nothing more: at least 16
queries, at least 8 on each side, no query string appearing twice, no keys beyond `query`,
`should_trigger` and `expected`, `should_trigger` a real boolean rather than the string
`"true"`, and `expected` only on a negative, never naming the skill itself, and naming a
skill or subagent that exists — a misspelling there is a permanent miss. The codes are
`no-evals` (a warning, the only one), `bad-eval-json`, `bad-eval-shape`, `bad-eval-entry`,
`unknown-expected`, `duplicate-eval-query`, `thin-eval-set` and `unbalanced-eval-set`.

Subagents carry eval sets too, at `agents/evals/<name>.json` beside the agent file, with
the same schema. Their descriptions do the same routing job, and several compete directly
with a skill — `ci-log-reader` and `ci-triage` most obviously — so the catalogue the
harness scores against contains both.
Twenty and ten are the house convention; sixteen and eight are the floor below which the
result stops meaning anything.

One check reaches across skills. The same query may not be a positive in two eval sets:
whichever skill wins the invocation, the other is scored as a miss, so one of the two sits
permanently below its threshold for a reason that has nothing to do with its description.
That is `conflicting-eval-query`, and the fix is to decide which skill owns the query and
make it a negative in the other.

The reverse is not a conflict and is worth doing deliberately: a query that is a positive
for one skill and a negative for its neighbour is the strongest test either set can
contain, because it names the exact sibling the description has to beat.

Scoring the queries needs a model, so it lives somewhere else:
[`scripts/run_trigger_eval.py`](../scripts/run_trigger_eval.py), driven manually by the
`.github/workflows/evals.yml` workflow. The split is the whole design. The schema check is
deterministic and free, so it gates every push; the scoring is sampled and costs money, so
it gates nothing at all. A gate that is occasionally wrong is a gate people learn to
override, and once they learn that, the gates that matter stop working too.

What the runner measures is discrimination, not recall. Every query is put to the model
alongside the descriptions of *every* skill in this repository, and the skill counts as
having fired only when the model picks it by name out of that catalogue. A description
broad enough to fire on everything therefore passes all ten positives and fails the
negatives — which is exactly the failure a test of one skill in isolation cannot see, and
the reason the negatives are worth more effort than the positives. Take them from the
adjacent skills: the queries that should land on `k8s-triage` or `image-hardening` are the
ones that reveal whether `ci-triage` is stealing them.

Four numbers come back per target: the pass rate over all queries, recall over the
positives, specificity over the negatives, and routing over the negatives that name an
expected winner. A skill at 100% recall and 40% specificity is not a good skill with a
rough edge; it is a skill that fires on everything. A skill at 100% specificity and 50%
routing is one whose neighbours are quietly losing queries to something else.

Run it locally with the `claude` CLI on `PATH`:

```bash
python scripts/run_trigger_eval.py --skill plugins/engineering/skills/ci-triage --verbose
python scripts/run_trigger_eval.py --agent plugins/engineering/agents/ci-log-reader.md
python scripts/run_trigger_eval.py --all --budget 8000 --baseline evals/last-run.json
```

Three flags change what the number means:

- `--runs` samples each query more than once and takes the majority. The default is three
  and it must be odd, so a vote cannot tie and be broken by whichever sample happened to
  run first. The `narrow` column counts queries decided by a split, which is where a
  description sits on the model's decision boundary.
- `--budget` scores descriptions the way the runtime shows them rather than the way they
  are written: it applies the listing budget above and drops the target's own description
  first, which is the realistic case for a skill nobody has used yet. A description that
  scores well only without `--budget` is one that never reaches the model in a real
  session.
- `--baseline` takes an earlier `--json` output and prints the per-target delta. With
  forty descriptions competing for the same queries, the expected consequence of editing
  one is a change in a neighbour's score, and a fixed threshold cannot see a skill slide
  from 100% to 85%. Commit a run and diff against it.

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
mkdir -p plugins/engineering/skills/log-shipping/evals
cp template/SKILL.md plugins/engineering/skills/log-shipping/SKILL.md
```

[`template/SKILL.md`](../template/SKILL.md) carries the shape: a one-sentence statement
of what good looks like, a paragraph on why the job is hard, an explicit `Scope` section
with "use for" and "do not use for", a numbered workflow, and an anti-patterns section.

1. Set `name: log-shipping` in the frontmatter. It must match the directory.
2. Write the description last, after the body exists — you will know what triggers it
   only once you know what it does.
3. Write `evals/trigger-eval.json` alongside it: twenty queries, ten `true` and ten
   `false`. Write them in the user's words rather than the skill's, and draw the
   negatives from the skills this one sits next to. Doing this straight after the
   description is what turns "this reads well" into a number.
4. Add the skill to the right plugin's `skills` array in
   [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json), keeping the
   array alphabetical:

   ```json
   "./plugins/engineering/skills/log-shipping"
   ```

5. Validate:

   ```bash
   make validate
   ```

6. Optionally score the description, and check that the skill packages and installs:

   ```bash
   python scripts/run_trigger_eval.py --skill plugins/engineering/skills/log-shipping --verbose
   make package
   make install
   ```

`make package` refuses to build an archive for a skill that does not validate, so a
green `make validate` is a precondition, not a formality. For a review that goes beyond
the mechanical checks, hand the draft to the `skill-reviewer` subagent described in
[writing agents](writing-agents.md).

## Validator codes

Run directly with `PYTHONPATH=src python -m skillcheck .`. One run covers every skill
under `skills/`, every subagent under `agents/`, and the marketplace manifest; the last
line reports how many of each were checked. Useful flags: `--strict` (warnings become
failures, which is how `make validate` and CI both run it), `--skip-marketplace` (skip the
manifest cross-check), `--github` (emit annotations and a job summary; implied under
Actions). Exit code 1 means findings, 2 means the repository layout was unusable.

Every code the validator can emit is below, grouped by what it is looking at.

### Frontmatter and body

| Code | Level | Meaning | Fix |
| --- | --- | --- | --- |
| `not-utf8` | error | The file is not valid UTF-8. | Re-save it as UTF-8. Reported rather than raised, because one mis-encoded file used to abort validation for every other skill. |
| `duplicate-skill-name` | error | Two skill directories share a name. | Rename one. `name` equals the directory name, so a duplicate directory is a duplicate skill: the second silently replaces the first on install and in `dist/`, and every counter still reports success. |
| `nested-skill` | error | A second `SKILL.md` below the skill directory. | Move it to its own directory under `skills/<category>/`. |
| `frontmatter` | error | The block could not be parsed at all: missing or unclosed `---`, a tab, a byte-order mark, indentation, a duplicate key, an unreadable line. | Follow the message; it carries the line. |
| `unknown-key` | error | A key outside the allowed six. | Rename it, or delete it. The message names the likely intended key. |
| `missing-name` | error | No `name`. | Add it. |
| `empty-name` | error | `name` present but blank. | Fill it in. |
| `bad-name` | error | Not lowercase letters, digits and single hyphens. | No capitals, underscores, leading, trailing or doubled hyphens. |
| `reserved-name` | error | The name contains `anthropic` or `claude`. The upload route rejects it, so the skill passes locally and fails at the boundary. | Name it after the job rather than the tool. |
| `long-name` | error | Over 64 characters. | Shorten it. |
| `name-mismatch` | error | `name` differs from the directory name. | Change one to match the other. |
| `missing-description` | error | No `description`. | Add it. |
| `empty-description` | error | `description` present but blank. | Fill it in. |
| `angle-brackets` | error | `<` or `>` in the description. | Remove them; upload rejects them. |
| `long-description` | error | Over 1024 characters, measured on the folded value. | Cut the least load-bearing phrasings, not the trigger list. |
| `description-headroom` | warning | Within 50 characters of the cap. | Trim now, before an edit crosses it. |
| `no-trigger` | warning | No explicit "use when…" clause. | Add one naming the situations. |
| `long-compatibility` | error | `compatibility` over 500 characters. | Shorten it. |
| `dangling-reference` | error | A `references/`, `scripts/` or `assets/` path named in prose does not exist. | Write the file, remove the pointer, or fence it if it was only an illustration. |
| `no-shebang` | error | A `scripts/*.sh` file has no `#!` line. | Add `#!/usr/bin/env bash`. |
| `not-executable` | error | A `scripts/*.sh` file is not executable. | `chmod +x` it. |
| `long-skill` | warning | `SKILL.md` over 500 lines. | Push depth into `references/`. |
| `no-toc` | warning | A reference over 100 lines with no contents heading. The threshold is upstream's, and the reason is partial reads: Claude may read only the head of a long file, so the contents list is what makes the rest visible. | Add a `## Contents` (or "Table of contents", or "In this file") heading. |
| `shouting` | warning | `ALWAYS` or `NEVER` in capitals. | Replace with the reason the rule exists. |

### Eval sets

| Code | Level | Meaning | Fix |
| --- | --- | --- | --- |
| `no-evals` | warning | The skill has no `evals/trigger-eval.json`. | Write one: twenty queries, ten each way. |
| `bad-eval-json` | error | The file is not valid JSON. | Fix the syntax; the message carries the parser's reason. |
| `bad-eval-shape` | error | The top level is not a JSON array. | Wrap the entries in `[ … ]`. |
| `bad-eval-entry` | error | An entry is not an object, has no usable `query`, has a `should_trigger` that is not a real boolean, or carries a key other than those two. | The message names the entry's index. |
| `duplicate-eval-query` | error | The same query string appears twice. | Replace one of them; a duplicate inflates the count without testing anything. |
| `thin-eval-set` | error | Fewer than 16 queries. | Add more. Below that the pass rate moves too far on one result. |
| `unbalanced-eval-set` | error | Fewer than 8 on either side. | Add to the short side — usually the negatives, which are what catch a description that fires on everything. |
| `unknown-expected` | error | A negative names an `expected` winner that is not a skill or subagent here. | Fix the spelling. Left alone it scores as a permanent miss. |
| `listing-over-budget` | warning, only with `--listing-budget` | A plugin's descriptions together exceed the given listing budget. | Not an author-side fix at this scale; see [the listing budget](#the-listing-budget). |
| `conflicting-eval-query` | error | The same query is a positive in two skills' eval sets. | Decide which skill owns it and make it a negative in the other. Left alone, one of the two always scores as a miss. |

### Subagents

These run over every `agents/*.md`. The key set differs from a skill's; see [writing a
subagent](writing-agents.md) for why.

| Code | Level | Meaning | Fix |
| --- | --- | --- | --- |
| `frontmatter` | error | The block could not be parsed, as above. | Follow the message. |
| `unknown-key` | error | A key outside `name`, `description`, `tools`, `model`. | Rename or delete it. `allowed-tools` here is the usual cause; the subagent key is `tools`. |
| `missing-name` | error | No `name`, or blank. | Add it. |
| `bad-name` | error | Not lowercase letters, digits and single hyphens, or over 64 characters. | Rewrite it in kebab-case. |
| `name-mismatch` | error | `name` differs from the filename stem. | Change one to match the other. |
| `missing-description` | error | No `description`, or blank. | Add it. The main agent has nothing else to choose on. |
| `angle-brackets` | error | `<` or `>` in the description. | Remove them. |
| `long-description` | error | Over 1024 characters. | Shorten it. |
| `bad-tools` | error | `tools` is present but empty, or has a blank entry — a trailing comma is the usual cause. | Write it as a comma-separated list, or omit the key entirely. |

### Marketplace manifest

| Code | Level | Meaning | Fix |
| --- | --- | --- | --- |
| `no-marketplace` | error | `.claude-plugin/marketplace.json` is missing. | Restore it. |
| `bad-json` | error | The manifest is not valid JSON. | Fix the syntax at the reported line. |
| `bad-marketplace-shape` | error | The manifest is not an object, `plugins` is not a list, a plugin entry is not an object, or a `skills`/`agents` value is not a list of strings. | Fix the shape. This is reported rather than raised because reaching `.get` on a string used to abort the whole run with a traceback. |
| `missing-listed-plugin` | error | A plugin listed in `marketplace.json` has no `.claude-plugin/plugin.json` at its `source`. | Write the plugin manifest, correct the `source` path, or remove the entry. |
| `unlisted-plugin` | error | A plugin exists on disk but is absent from `marketplace.json`, so it installs for nobody. | Add an entry for it to the manifest's `plugins` array. |
| `unowned-skill` | error | A skill is not inside any plugin's `skills/` directory, so no plugin ships it. | Move it under `plugins/<name>/skills/`. |
| `unowned-agent` | error | A subagent is not inside any plugin's `agents/` directory. | Move it under `plugins/<name>/agents/`. |

CI runs the same validator on every push and pull request; see [what CI checks](ci.md).
Subagents and slash commands are validated on the same run — see
[writing a subagent](writing-agents.md) and [writing a slash command](writing-commands.md).
