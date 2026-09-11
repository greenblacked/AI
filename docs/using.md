# Using the skills

This library is a set of procedures written as Markdown. How you load them depends on
what you are using, and only the first option below gives you the thing that makes a
skill worth having: automatic triggering, where the assistant recognises the situation
and reaches for the procedure without being told.

- [Claude Code](#claude-code) — install the plugins; skills fire on their own
- [ChatGPT](#chatgpt) — upload the bundles to a Project or a Custom GPT
- [Grok](#grok) — paste the skill, or attach a bundle
- [Codex, Gemini CLI and other terminal agents](#terminal-agents-that-read-agentsmd)
- [Anything else, or nobody at all](#no-assistant-at-all)

## Claude Code

### Install

```shell
/plugin marketplace add greenblacked/AI
/plugin install coding@greenblacked-ai
/plugin install gamedev@greenblacked-ai
/reload-plugins
```

The first line registers the marketplace; it downloads nothing on its own. Each
`/plugin install` adds one plugin. `/reload-plugins` makes them live in the current
session — without it you will wonder why nothing fires.

Install the plugins you will actually use. Every description a plugin ships sits in
context for the whole session, and the runtime caps that listing at about 1% of the
context window. Past the cap it drops the descriptions of the skills you invoke least,
which leaves them invocable by name and stops them being chosen on their own — silently.
Six of the eight plugins fit the default budget by themselves. If you install several,
raise it in `~/.claude/settings.json`:

```json
{ "skillListingBudgetFraction": 0.04 }
```

### How a skill fires

You do not invoke a skill. You describe the situation, and the model matches what you
said against every installed description and loads the one that fits. "this file is 2000
lines and I need to add a feature to it" reaches `refactoring` without you naming it.

That is the whole design, and it is also why a description is written the way it is: it
names the circumstances and the casual phrasings someone actually types, because the
description is the only text loaded before the skill runs.

Two things follow. If a skill never seems to fire, the description is the suspect, not the
body. And you can always force it — "use the refactoring skill" works, and is the right
move when you know exactly what you want.

### Subagents

Nine ship across four plugins, and they work differently: the main agent delegates to one
when the work would otherwise flood your context with material you do not need afterwards.
A megabyte of CI logs, a Terraform plan, a billing export. You get the conclusion; the raw
material never enters your session.

You do not usually invoke them either. Paste a failing run and `ci-log-reader` is chosen.
Ask for one by name when you want to be sure.

### Slash commands

Five ship, and unlike skills they never fire on their own — you type them. That makes them
the right shape for work that takes an argument, or that should happen when asked rather
than when merely relevant.

```shell
/ci-fail 18234567          # classify a failing run
/blast-radius plan.json    # what the apply destroys
/weekly                    # draft this week's status update
```

### Working on this repository

If you cloned this repository to change the skills themselves, `/ship` runs the
three-stage loop over a change: `explorer` surveys what already covers it, `implementer`
writes it and runs the gates, `reviewer` judges the result on a fresh context with no
editing tools. See [writing a subagent](writing-agents.md#the-three-stage-loop).

### Updating and removing

```shell
/plugin marketplace update greenblacked-ai
/plugin uninstall coding@greenblacked-ai
```

There are no version numbers. The marketplace source is a git ref, so Claude Code derives
a version from the commit and an update takes you to the latest commit on the default
branch.

### When something does not work

- **Nothing fires.** Did you run `/reload-plugins`? Then check the description names your
  situation — `/doctor` reports what the skill listing costs and its biggest contributors.
- **A skill fires that should not.** Say so plainly in the session, and open an issue: a
  description stealing a neighbour's queries is a defect in this repository, and the eval
  sets exist to catch exactly that.
- **Some skills stopped being chosen after you installed more plugins.** That is the
  listing budget. Raise it, or uninstall a plugin you do not use.

## ChatGPT

There is no marketplace to read, so the skills are flattened into files that stand alone
— frontmatter turned into a plain "Use this when" line, and every reference file inlined
so no path is left for a reader with no filesystem to follow.

**Download them, no toolchain needed.** Every CI run builds the flattened files and
attaches them as the **portable-skills** artifact. Open the
[latest run](https://github.com/greenblacked/AI/actions/workflows/ci.yml?query=branch%3Amain),
scroll to Artifacts, and download `portable-skills`. This is the route to use if you are
here because you do not have a coding setup — being told to clone a repository and run
`make` would be the distribution problem restated as instructions.

**Or build them.** If you do have a terminal:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
make portable          # writes dist/portable/
```

**A Project** is the closest fit to how the skills are meant to work. Create one, upload
the `plugins/*.md` bundles you want **and `index.md` alongside them** — a Project answers
from retrieved chunks rather than the whole file, so the index is what guarantees the
model can see every "Use this when" line at once and choose between them. Then put this in
the project instructions:

> You have a library of procedures in the project files. Before answering, check whether
> one applies — each begins with "Use this when". If one does, follow it rather than
> improvising, and say which you used. If none applies, answer normally.

**A Custom GPT** is the same arrangement: bundles in Knowledge, that text in Instructions.

**For one skill**, paste `dist/portable/skills/<name>.md` into the conversation and say
"follow this". The bundles are large — `coding` is several hundred kilobytes — so the
single-skill files are the better unit when you already know which one you want.

`dist/portable/index.md` lists every skill with its description. Give a model the index
when you want it to choose, then hand it the file it asks for.

## Grok

The same flattened files. Grok's surfaces differ in whether they keep files around, so the
single-skill file is usually the right unit: paste `dist/portable/skills/<name>.md` and
say "follow this procedure". Where you have custom instructions and attachments, use the
project text above with a bundle attached.

## Terminal agents that read AGENTS.md

Codex, Gemini CLI and most other terminal agents read `AGENTS.md` from the working
directory. Append what you want to the repository you are working in:

```bash
cat dist/portable/plugins/coding.md >> AGENTS.md
```

That is blunt and it works. For something narrower, append one skill instead, or keep the
index in `AGENTS.md` and the individual files beside it.

The trigger eval harness in this repository already speaks to several of these. It scores
whether a description actually fires, against whichever CLI you have signed in:

```bash
python scripts/run_trigger_eval.py --skill plugins/coding/skills/refactoring --backend codex
```

## No assistant at all

They are procedures. `plugins/*/skills/*/SKILL.md` reads fine on its own, and several of
them — the review checklists, the prep sheets, the incident timelines — were written by
someone who wanted the checklist more than the automation.

## What does not travel

Be clear about what you lose outside Claude Code, because it is the valuable part:

- **Automatic triggering.** Everywhere else you either tell the assistant to check the
  library, or name the skill yourself. The instruction text above is the closest
  approximation and it is not the same thing.
- **Tool restriction.** `allowed-tools` and a subagent's denied `Write` are enforced by
  the runtime. In a chat window they are a description of intent.
- **Subagents.** Context isolation needs a runtime that can spawn one. A flattened
  subagent is just a prompt you can paste.
- **The listing budget**, which is a real constraint and also the reason the plugins are
  cut narrowly. Uploading one bundle to a Project has no such cap, which is a genuine
  advantage of that route.

The content itself travels intact. Of fifty-five skills, exactly one names a Claude Code
concept anywhere in its text — `new-skill`, which is about authoring a skill in this
format and could not avoid it. The rest are procedures about code, systems, teams and
life, and nothing in them assumes which assistant is reading. `make portable --check`
runs in CI, so that stays true.
