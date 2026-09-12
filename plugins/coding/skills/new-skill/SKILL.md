---
name: new-skill
description: "Author a Claude Code skill from scratch — decide whether the procedure deserves a skill at all, name and place it, write the body as scope, workflow and anti-patterns, write the description last because it is the only text that decides whether the skill ever fires, push depth into reference files, and build a twenty-query trigger eval set that proves the description discriminates from its neighbours. Use this skill whenever someone wants to write, create, add, draft, scaffold or repair a SKILL.md, an agent skill, a plugin skill or a skills marketplace entry — including casual phrasings like \"make a skill for X\", \"turn this runbook into a skill\", \"my skill never fires\", \"what should the description say\", or \"add this to my skills repo\". Not for scaffolding ordinary application code, scripts or services, and not for reviewing a skill someone else already drafted."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python3:*), Bash(make:*)
---

# New Skill

A finished skill is one that fires when it should, does not fire when a neighbouring skill should, and tells an agent something it would not otherwise have done. Everything else — the formatting, the file layout, the frontmatter — is bookkeeping that a validator can check for you.

Skills fail in four predictable ways, and only one of them is visible without testing. The common one is under-triggering: the description reads like a product blurb, no query ever matches it, and the skill sits on disk being useless while everyone assumes it works. The second is restating general good practice, which costs context and changes no behaviour, because a competent agent already writes tests and handles errors. The third is a body that names a bundled file the author never wrote, so the progressive-disclosure step silently no-ops — silently, which is what makes it expensive. The fourth is a description that overlaps a sibling skill so both are plausible and which one fires becomes a coin toss. The order below is arranged so each of those is caught before it ships.

## Scope

Use for: writing a new skill, splitting one skill into two, fixing a skill that never triggers or triggers on everything, writing the trigger eval set, or converting an existing runbook, checklist or team convention into a skill.

Do not use for: scaffolding application code, scripts, modules or services; reviewing a skill someone else drafted; writing a subagent definition; or authoring project instructions such as an `AGENTS.md`.

## 1. Decide whether it should be a skill

Answer this before writing anything, because a skill that should not exist cannot be improved by writing it well.

A procedure earns a skill when it has at least one of these, and ideally all three:

- **An order that matters.** Checking whether the main branch is already broken before triaging a pull request is worth writing down; "read the logs carefully" is not.
- **A specific gate or command.** A flag, a threshold, a query, a sequencing rule someone learned the expensive way.
- **A failure mode a general-purpose agent walks into.** If the default behaviour is already correct, the skill is a context tax.

If the answer is a paragraph of encouragement, stop. Put it in project instructions or a document instead.

Then check what already exists. Two skills with overlapping descriptions do not compose; they compete, and the loser fires at random. If an existing skill covers 70 percent of this, extend it rather than adding a neighbour.

## 2. Name it and place it

The directory name and the `name` field must be identical — lowercase, digits and single hyphens, at most 64 characters. Name it after the job, not the tool: `image-hardening` outlives the scanner you happen to use this year.

```text
skills/<category>/<name>/
  SKILL.md
  evals/trigger-eval.json
  references/*.md      # optional, only if you write them
  scripts/*.sh         # optional, executable, with a shebang
```

In a plugin marketplace the skill also has to be listed in the manifest, or it installs for nobody.

## 3. Write the body before the description

You cannot describe a procedure you have not written. Write the body first, then come back to the frontmatter knowing what the skill actually does.

The shape that works:

| Section | Contains |
| --- | --- |
| One opening sentence | What good looks like when this skill runs |
| One paragraph | Why the job is hard — the failure modes the skill prevents |
| `## Scope` | Use for / do not use for |
| `## Workflow` | Numbered `### N. Step` headings, in the order they must happen |
| An output block | The template or format the agent fills in |
| `## Anti-patterns` | A bolded name and the cost of each |

Write imperatively — you are instructing an agent, not describing a product. Explain why a rule matters instead of shouting it; a rule set in capitals is one nobody can reason about, and it earns a warning here for that reason. Prefer a real command with real flags over a paragraph about the command. A table mapping signal to classification to action is worth more than three paragraphs of prose.

Keep the file under about 260 lines. When a section grows past that, it belongs in a file under `references/` — and every such file you name in the body needs a one-line "read this when…" beside it, or the agent has no basis for deciding whether to load it.

Two rules about bundled files, both learned from real breakage:

- Write the file or do not name the path. A pointer to a file that does not exist fails silently at runtime, which is why it is a hard error here rather than a warning.
- All "when to use this skill" information belongs in the description, not the body. By the time the body is loaded, the decision to fire has already been made.

## 4. Write the description

This is the only text loaded before the skill fires. It is the whole triggering mechanism, and the known failure mode is under-triggering, so be explicit and slightly pushy about when to use it.

Three parts, in this order:

1. **What it does**, third person, concrete. Name the steps, not the benefits.
2. **When to use it**, starting with "Use this skill whenever…", listing the casual phrasings someone would actually type — including the vague ones and the ones that name a symptom rather than the task.
3. **What it is not for**, naming the adjacent skill by name where one exists.

Constraints the tooling imposes: at most 1024 characters, and no `<` or `>` anywhere, because those are rejected on upload. Aim for 500 to 900 — long enough to carry the trigger phrasings, short enough to leave room for an edit later.

The test of a description is not whether it reads well. It is whether someone who has never seen the skill could predict, from the description alone, which of ten queries should fire it.

## 5. Declare the tools

`allowed-tools` is a comma-separated list, scoped where scoping helps:

```yaml
allowed-tools: Bash(kubectl:*), Bash(helm:*), Read, Grep, Glob
```

Keep it to the minimum the procedure genuinely needs, and be honest about which side you are erring on. Too broad and the declaration means nothing; too narrow and the skill stalls halfway through its own workflow.

## 6. Build the eval set

Twenty queries in `evals/trigger-eval.json`, ten that should trigger and ten that should not:

```json
[
  {"query": "the deploy broke prod and pods are crashlooping", "should_trigger": true},
  {"query": "write me a helm chart for a new service", "should_trigger": false}
]
```

The positives only prove the description is not inert. The negatives are the half that does the work, so draw several of them from the skills next door — that is where descriptions actually collide, and a near-miss from an unrelated domain proves nothing.

Then run it. A description nobody has tested is a guess, and the interesting result is not the score but the specific query that came out wrong, because that names the phrase the description is missing.

## 7. Validate, then install and use it

Run the repository's validator and its tests. Then package or symlink the skill, start a fresh session, and use it on a real task. Reading a skill tells you whether it is well written; running it tells you whether it works.

## Anti-patterns

**The description written first.** You end up describing the skill you intended rather than the one you wrote, and the trigger phrasings come from imagination instead of from the workflow.

**A description that lists benefits.** "Comprehensive best-practice guidance for reliable deployments" matches nothing anyone types. Trigger phrases are symptoms and casual asks, not value propositions.

**Naming a bundled file you have not written.** The load silently does nothing, the agent proceeds with the shallow version, and no error appears anywhere. This is the defect that justifies a validator.

**Restating general good practice.** Every line that a competent agent would do anyway is context spent for no behavioural change, and it dilutes the lines that would have changed something.

**Ten positives and ten unrelated negatives.** "How do I bake bread" proves nothing. The negatives that matter are the ones a sibling skill should win.

**One skill that does two jobs.** It triggers on both and does neither well, and its description has to be vague enough to cover both, which is exactly the description that fires on everything.

**Editing the description to make a check pass.** If a check disagrees with a description that triggers correctly, the check is what is wrong.
