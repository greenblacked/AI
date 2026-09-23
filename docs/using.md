# Using the skills

This library is a set of procedures written as Markdown. How you load them depends on
what you are using, and only a tool that loads skills natively gives you the thing that
makes a skill worth having: automatic triggering, where the assistant recognises the
situation and reaches for the procedure without being told. Claude Code is the first
option below; the [table in the README](../README.md#chatgpt-grok-codex-and-everything-else) says which other agent tools do the same,
and where each one looks.

- [Claude Code](#claude-code) — install the plugins; skills fire on their own
- [ChatGPT](#chatgpt) — upload the bundles to a Project or a Custom GPT
- [Grok](#grok) — paste the skill, or attach a bundle
- [Codex, Gemini CLI and other terminal agents](#terminal-agents-that-read-agentsmd) — several now load skills natively; see the [README table](../README.md#chatgpt-grok-codex-and-everything-else)
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

Installing `gamedev`: [`docs/gamedev.md`](gamedev.md) picks a production scale and a game
type and routes through the plugin's nine skills from there, rather than leaving you to
read all nine cold.

Install the plugins you will actually use. Every description a plugin ships sits in
context for the whole session, and the runtime caps that listing at about 1% of the
context window. Past the cap it drops the descriptions of the skills you invoke least,
which leaves them invocable by name and stops them being chosen on their own — silently.
Only `career`, `delivery` and `personal` fit the default budget by themselves. If you
install any of the other five, or more than one plugin, raise it in
`~/.claude/settings.json`:

```json
{ "skillListingBudgetFraction": 0.09 }
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

Seventeen ship across seven plugins, and they work differently: the main agent delegates to one
when the work would otherwise flood your context with material you do not need afterwards.
A megabyte of CI logs, a Terraform plan, a billing export, a release range. You get the
conclusion; the raw material never enters your session.

You do not usually invoke them either. Paste a failing run and `ci-log-reader` is chosen.
Ask for one by name when you want to be sure.

### Slash commands

Six ship, and unlike skills they never fire on their own — you type them. That makes them
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
editing tools. See [writing a subagent](writing-agents.md#the-two-loops).

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

Several terminal agents, Codex and Gemini CLI among them, now load `SKILL.md` skills
natively and fire them on their own. That is the better route where it exists: the
[table in the README](../README.md#chatgpt-grok-codex-and-everything-else) says which tools do and how to install for each.

For one that does not, most terminal agents read `AGENTS.md` from the working directory.
Append what you want to the repository you are working in:

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

- **Automatic triggering**, except in the agent tools that load skills natively — the
  [README table](../README.md#chatgpt-grok-codex-and-everything-else) lists them. Everywhere else you either tell the assistant to check the
  library, or name the skill yourself. The instruction text above is the closest
  approximation and it is not the same thing.
- **Tool restriction.** `allowed-tools` and a subagent's denied `Write` are enforced by
  the runtime. In a chat window they are a description of intent.
- **Subagents.** Context isolation needs a runtime that can spawn one. A flattened
  subagent is just a prompt you can paste.
- **The listing budget**, which is a real constraint and also the reason the plugins are
  cut narrowly. Uploading one bundle to a Project has no such cap, which is a genuine
  advantage of that route.

The content itself travels intact. Of eighty-seven skills, two name Claude anywhere in
their text: `new-skill`, which is about authoring a skill in this format and could not
avoid it, and `website-builder`, which names a real constraint of Claude.ai artifacts.
The rest are procedures about code, systems, teams and life, and nothing in them assumes
which assistant is reading. CI builds the export on every run, so that stays true.

## Running the loop without a subagent mechanism

The "Subagents" loss above is the one worth a substitute rather than just a note, because
`/ship` and `/verify` are how changes to this repository get made. Without a runtime that
can spawn an isolated subagent, the replacement is three conversations rather than three
agents — the same stages, run by hand, in separate windows instead of separate contexts.

**Survey**, in a new conversation, report-only. Describe the change and ask what already
covers it, where the affected files are, and which existing description its trigger
surface would overlap. Take the answer, then close the conversation — the closing is what
does the isolating, not the asking. A survey window left open and reused for writing has
stopped being a survey.

**Decide the shape yourself.** Which plugin owns the change and what it must not collide
with is not something `/ship` delegates either — that decision needs judgement built up
over the session, and it travels badly through a cold prompt whether the prompt goes to a
subagent or to a fresh conversation. This step does not change when the mechanism goes
away.

**Write**, in your working session, and run the gates yourself — `make validate`,
`make catalogue`, `make test` — rather than accepting a report that they passed. There is
no separate context to trust here; you are both the one writing the change and the one
who has to believe the result.

**Review**, in a new conversation, and hand it `git diff` as text, together with every
file `git ls-files --others --exclude-standard` names, in full. The diff alone omits
untracked files, which on a change that adds one is the whole change. Pasting rather than
pointing removes the material only when the reviewing conversation cannot reach the
checkout; in a terminal agent sitting in the repository it has the tree whatever you
paste, so open the review somewhere that does not. Ask for the same output
contract a reviewing subagent is written to produce: a one-line verdict; blocking defects
ranked by cost, each with the observation, the concrete consequence and the smallest fix
described rather than written; non-blocking findings kept separate from blocking ones;
the gate output quoted rather than summarised; and what was not assessed, said plainly
rather than left to be inferred from silence.

Carry what it finds back to the writing conversation. Never paste a fix into the
reviewing one — that single move is what collapses the two stages back into one, because
a conversation that has just fixed what it was asked to judge is not the reviewer
any more; it is the author, with an extra turn.

**What is genuinely lost**, and pretending otherwise costs more than naming it:

- **The runtime-enforced no-write.** A subagent with no `Write` or `Edit` cannot act on a
  decision to fix what it is reviewing, however tempted; a conversation with no such
  restriction can, and a review that quietly turns into a rewrite reads exactly like a
  review until someone checks whether anything actually changed underneath it.
- **Automatic delegation.** `/ship` reaches for the survey stage without being asked.
  Three separate conversations require you to remember to open each one, and the stage
  that goes missing is whichever felt optional when time was short — usually the survey,
  because the change already looks obvious from where you are standing.
- **Enforced tiering.** A subagent's `model` key pins its tier regardless of what the
  main conversation is running on. Three manual conversations run on whatever tier each
  happens to be open on, and nothing stops all three running on the same one out of
  convenience.

**What is not lost.** Context isolation is not the runtime's alone to give — it is what
closing a conversation buys, with or without a subagent mechanism behind it. The cold
read survives too: a review conversation started fresh from `git diff` alone knows
exactly as little as a reviewing subagent does. The ordering — survey, then write, then
review, never collapsed into one sitting — is a discipline kept by opening three
conversations in sequence, not a property a runtime grants automatically. And the output
contract above is exactly as enforceable by asking for it in the prompt as by writing it
into a subagent's system prompt; nothing about it needs a runtime feature.

The four files in `.claude/agents/` are where this repository's current stage names and
prompts actually live, if the description above is not enough and the wording itself is
wanted.

One caveat on the tiering point, so as not to overstate it: a more capable model is a
cost hedge on a review that is expensive to get wrong, not a requirement of the stage
itself. What review needs is a context that has not written the change and is not
allowed to — that holds in a fresh conversation on whatever model is already in use, and
paying for a stronger one on top of that is a choice about how much a missed defect would
cost, not a precondition for the review being real.
