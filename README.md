<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
  <img alt="The seventeen plugins: coding, family, gamedev, operations, delivery, security, manager, personal, career, design, llm, data, techdocs, assurance, client-apps, product and platform" src="docs/assets/banner-light.svg" width="100%">
</picture>

# Agent skills

241 agent skills, 30 subagents and ten slash commands, in seventeen
plugins you install separately.

[![CI](https://github.com/greenblacked/AI/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/ci.yml)
[![Security](https://github.com/greenblacked/AI/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/security.yml)
[![Scheduled checks](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab)](pyproject.toml)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A595%25-22c55e)](pyproject.toml)
[![Skills](https://img.shields.io/badge/skills-241-7c3aed)](#skills)
[![License: MIT](https://img.shields.io/badge/license-MIT-0ea5e9)](LICENSE)

[Website](#website) · [Start here](#start-here) · [Install](#install) · [What is included](#what-is-included) · [Skills](#skills) · [Subagents](#subagents) · [Commands](#commands) · [CI](#ci-is-the-source-of-truth) · [Documentation](#documentation) · [Licence](#licence)

</div>

A library of practical Markdown procedures for changing code, operating systems,
shipping safely, reviewing design and usability, building on language models, making games, leading teams, and
handling career and personal work.
An agent loads a skill when its description matches your task; the skill supplies the
ordering, checks and evidence to collect. This is a procedure library, not an application.

## Start here

- **Claude Code:** install a plugin from the [marketplace](#claude-code), then reload it
- **Codex or another terminal agent:** follow the [first-run walkthrough](docs/using.md#first-run-with-codex) or check the [supported tools](#chatgpt-grok-codex-and-everything-else)
- **ChatGPT or another chat assistant:** use the [portable files](docs/using.md#chatgpt)
- **Browse the website:** [ai.szolotov.com](https://ai.szolotov.com) has a page for every
  plugin and skill, with the install line, examples and quality evidence
- **Browse before installing:** the [plugin overview](#what-is-included) links to the full [skills catalogue](#skills), with [subagents](#subagents) and [commands](#commands) below

**Prerequisites:** an installed assistant for its route. Local installation needs Git,
Bash and standard Unix tools; local validation and packaging need Python 3.10 or newer,
and the `make` examples need Make. Only the test suite needs pytest, with pytest-xdist and pytest-cov. Downloading the
portable CI artifact needs no local toolchain.

Claude Code installs plugins with automatic triggering. Other tools can load native
skills or read the portable export; [Using the skills](docs/using.md) explains each route
and what the runtime does or does not enforce.

## What is included

| Plugin | Focus | Contents |
| --- | --- | --- |
| [`coding`](#coding) | Reading, reviewing, testing and changing code | 26 skills, 5 subagents, 1 command |
| [`family`](#family) | One development workflow, from a vague request to a measured outcome | 11 skills, 6 subagents, 1 command |
| [`gamedev`](#gamedev) | Making games, and shipping them | 13 skills, 1 subagent, 1 command |
| [`operations`](#operations) | Keeping a running system alive | 19 skills, 7 subagents, 2 commands |
| [`delivery`](#delivery) | Getting a change into production | 12 skills, 1 subagent |
| [`security`](#security) | The defensive side of shipping software | 15 skills, 5 subagents, 2 commands |
| [`manager`](#manager) | Engineering leadership | 16 skills, 2 subagents, 2 commands |
| [`personal`](#personal) | Money, travel, admin, habits and health | 7 skills, 2 subagents |
| [`career`](#career) | Applications, negotiation, speaking and writing | 5 skills |
| [`design`](#design) | Usability, accessibility and design systems | 13 skills, 1 subagent, 1 command |
| [`llm`](#llm) | Building features on language models: retrieval, structured output, MCP servers, extraction and model migration | 5 skills |
| [`data`](#data) | Analytics data: wrong numbers, warehouse cost, metrics, history and pipelines | 11 skills |
| [`techdocs`](#techdocs) | Developer documentation: tested tutorials and samples, drift, stable URLs, API and CLI reference | 11 skills |
| [`assurance`](#assurance) | Quality engineering and compliance: order-dependent, mutation, property and fuzz testing, replay and load, DPIAs, licences, audit evidence | 11 skills |
| [`client-apps`](#client-apps) | Browser and mobile clients: field performance, hydration, memory, version skew, service workers, crashes, hangs, startup, battery, networks | 22 skills |
| [`product`](#product) | Product and go-to-market: interviews, demand tests, design partners, premortems, pricing, metric diagnosis, activation, churn, win-loss, RFPs | 22 skills |
| [`platform`](#platform) | Cloud and platform engineering: Kubernetes control plane, networking and storage, Terraform estates, cloud networks, identity, databases, the edge, commitments | 22 skills |

Install one plugin or all seventeen. Each is a self-contained directory under `plugins/` with
its own manifest, so installing one does not pull in another's files.

Install what you will use, though, rather than everything by reflex. Every description you
install stays resident in context, and Claude Code's default listing budget is about 8,000
characters against this library's total — `make validate` prints the current figure — so
installing all seventeen at the default drops most of them, silently. The Install section
below says what to set instead.

## The FAMILY workflow

FAMILY is a development workflow that keeps its shape whether one person or a whole team
is running it: Frame, Architect, Make, Inspect, Launch, Yield. It takes one slice of work
from a vague request to a measured outcome, and each stage has one gate, one artifact and
one handoff to the next.

| Letter | Stage | The decision it owns | Artifact |
| --- | --- | --- | --- |
| F | Frame | What problem, for whom, what done means, and the smallest valuable slice | A one-page frame |
| A | Architect | The approach, the boundaries, the interfaces, and the hardest decision to reverse | A design note and the ADR |
| M | Make | The order the slice is built in, and the proof each step carries | An ordered, file-level change plan |
| I | Inspect | Whether the change is correct, safe and accessible | Findings by severity, with evidence |
| L | Launch | Whether it is ready to reach users, and how it comes back | A launch plan: migration, signal, rollback |
| Y | Yield | What the outcome teaches the next slice | A short retro that feeds Frame |

The stages never change. Four profiles say who runs them — **solo**, **developer**,
**QA** and **team** — and each slice records whether it runs light or full, so a
shortcut is a decision rather than an accident. A solo developer runs all six in an afternoon; a
team of ten gives each stage a named owner and a handoff contract.

The [`family`](#family) plugin ships the `family-workflow` skill, a skill for each of the
four profiles — `solo-development`, `developer-workflow`, `qa-workflow` and `team-workflow`
— and a subagent per stage with no editing tools, `framer`, `architect`, `maker`, `inspector`,
`launcher` and `yielder`, so the main conversation keeps the conclusion of each stage and
not the material it read. Six more skills run those agents together: `family-relay`
routes each verdict to the next stage, `plan-drift-gate` holds a build to its plan before
inspection, `fresh-inspector-rounds` keeps every review round independent,
`frame-claim-ledger` settles the claims a decision rests on, `yield-to-lesson` turns a
retro into a check that can fail, and `stage-tiering` sets the model tier per stage. It is also the one page on the
[website](https://ai.szolotov.com/family/) drawn by hand rather than generated from a
plugin's files.

## Website

[ai.szolotov.com](https://ai.szolotov.com) is this catalogue as a website, rebuilt from
the repository for every release. It shows the latest release that deployed successfully:
if a deploy fails its check and rolls back, the previous one keeps serving.

| Page | What it shows |
| --- | --- |
| [Home](https://ai.szolotov.com) | The seventeen plugins with their skill counts, and a search across plugins and skill names |
| `/plugins/<plugin>/` | One page per plugin: what it covers, its install line and its skills |
| `/plugins/<plugin>/<skill>/` | One page per skill: its description, install line and allowed tools when it declares them, the full procedure, its reference files, and the requests it fires on and hands elsewhere |
| [FAMILY](https://ai.szolotov.com/family/) | The one page that is not generated from a plugin's own files: the Frame–Architect–Make–Inspect–Launch–Yield workflow, drawn as a stage-by-stage guide with the four profiles |
| [Start](https://ai.szolotov.com/start/) | Installing in Claude Code and in other tools, followed by [Using the skills](docs/using.md) |
| [Workflows](https://ai.szolotov.com/workflows/) | The subagents and slash commands each plugin ships, and how they fit with the skills |
| [Examples](https://ai.szolotov.com/examples/) | A week of real use, and sample requests for every skill |
| [Quality](https://ai.szolotov.com/quality/) | Figures computed from the repository: trigger-eval coverage, listing budgets, the coverage floor, reviewer benchmark cases and review lessons |

The same host serves each release's files: [`marketplace.json`](https://ai.szolotov.com/marketplace.json),
[`portable-skills.zip`](https://ai.szolotov.com/portable-skills.zip), one
`skills/<name>.skill` archive per skill, and `version.txt` naming the release it was built
from.

The site is light by day, dark from 20:00 to 06:00 by the visitor's clock, and has a
switch for either plus a terminal-style console theme. It is static HTML with no analytics
and no cookies, built with nothing but Python; its two fonts are served from the site itself.
It does store pages on the visitor's own device: a small service worker keeps each page you
open in your browser's cache, so a visitor who loses the connection can read those pages again
and sees an offline page for any other. That cache never leaves the browser, holds at most
sixty pages, and is emptied by clearing the site's data or dropped when a new release deploys. [`scripts/build_catalogue_site.py`](scripts/build_catalogue_site.py)
writes every page, and [`scripts/site_markdown.py`](scripts/site_markdown.py) renders the
Markdown with all source text escaped, raw HTML shown as text, and only `http`, `https`,
`mailto`, fragment and in-repository links kept. To build and view it locally:

```shell
make site
python -m http.server --directory dist/site 8000
```

A release publishes it: **Cut release** in the Actions tab tags `main`, and the release
workflow deploys that version to the Cloudflare Worker behind `ai.szolotov.com`, checks it
answers, and rolls back automatically if it does not. [Releasing a version](docs/ci.md#releasing-a-version)
has the steps.

## Install

### Claude Code

```shell
/plugin marketplace add greenblacked/AI
/plugin install coding@greenblacked-ai
/plugin install gamedev@greenblacked-ai
/reload-plugins
```

The first line registers the marketplace and downloads nothing. Each `/plugin install`
adds one plugin, and `/reload-plugins` makes them live in the session you are already in
— skip it and you will wonder why nothing fires. After that you do not invoke a skill:
you describe the situation, and the one whose description matches is loaded.

Install the plugins you will use rather than all of them. Every description a plugin ships
stays in context for the whole session, and the runtime caps that listing at about 1% of
the context window; past the cap it silently drops the descriptions of the skills you use
least, which leaves them invocable by name and stops them being chosen on their own. Only
`career`, `llm` and `personal` fit the default budget on their own. The other fourteen are over it —
each by enough that installed alone at least one of its descriptions is dropped — and the
split exists to keep that number as small as it can be.

The description budget is shared across installed plugins. Splitting a plugin does not
reduce the total when both halves are installed, and shortening every description to a
label sacrifices the trigger phrases that distinguish neighbouring skills. Check the
current totals with `scripts/check_listing_budget.py`; either install only what you need
or raise the budget in `~/.claude/settings.json`:

```json
{ "skillListingBudgetFraction": 0.23 }
```

That figure covers the whole marketplace, with a little headroom. Anything smaller
silently drops the difference — 0.04 covers barely half of it, which reads like a fix and
is not. `scripts/check_listing_budget.py` prints the fraction the listing currently needs
and fails if this number falls below it, so the advice cannot go stale as skills are
added.

`/doctor` reports what the listing actually costs and its biggest contributors.

### ChatGPT, Grok, Codex and everything else

Several agent tools now load the same `SKILL.md` format natively and activate a skill when
it is relevant; the table below says which, and where each one looks. Gemini CLI, Copilot
and Mistral Vibe all read the shared `.agents/skills` location, and one command links every
skill there:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
CLAUDE_SKILLS_DIR=~/.agents/skills make install
```

This repository's subagents, both the ones shipped under `plugins/*/agents/` and the ones
under `.claude/agents/`, and its slash commands are a Claude Code feature and do not
travel. Grok Build and Mistral Vibe read the `allowed-tools` key, but whether they enforce
it as a restriction is not verified here, so rely on it only in Claude Code.

For adapted coordinator and role prompts, use the [ChatGPT workflow guide](docs/chatgpt-agents.md);
whether a session can actually delegate to subagents depends on the tools it exposes.

<details>
<summary>Which tools read AGENTS.md and load skills</summary>

<!-- providers-table:start -->
<!-- Generated from providers.json by `python scripts/providers_table.py --write .`. Do not edit this table by hand: edit that file and regenerate. -->

| Provider | Tool | Reads `AGENTS.md` | Loads skills | How to use this library | Checked |
| --- | --- | --- | --- | --- | --- |
| Anthropic | Claude Code | Yes when there is no `CLAUDE.md`; beside one, through an `@AGENTS.md` import | Yes — plugins, `~/.claude/skills`, `.claude/skills` | Install the plugins from this marketplace | [2026-09-23](https://code.claude.com/docs/en/memory), [2](https://code.claude.com/docs/en/skills) |
| DeepSeek | DeepSeek API | Not applicable — a model API, not an agent tool | Through whichever agent tool calls it | Route Claude Code to DeepSeek through OpenRouter, unsupported by Anthropic; see docs/deepseek.md | [2026-09-23](https://github.com/deepseek-ai/DeepSeek-V3), [2](https://github.com/OpenRouterTeam/docs/blob/main/cookbook/coding-agents/claude-code-integration.mdx) |
| GitHub | Copilot | Yes; in VS Code, files outside the workspace root are off by default | Yes — `.github/skills`, `.claude/skills`, `.agents/skills`, `~/.copilot/skills`, `~/.agents/skills` | `CLAUDE_SKILLS_DIR=~/.agents/skills make install` | [2026-10-01](https://github.com/github/docs/blob/main/content/copilot/concepts/agents/about-agent-skills.md), [2](https://github.com/github/docs/blob/main/content/copilot/how-tos/copilot-in-your-ide/customize-copilot/configure-custom-instructions/add-repository-instructions-in-your-ide.md) |
| Google | Gemini CLI | Opt-in — add `AGENTS.md` to `context.fileName` in `settings.json`; the default is `GEMINI.md` | Yes — `.agents/skills`, `.gemini/skills`, and both under `~` | `CLAUDE_SKILLS_DIR=~/.agents/skills make install` | [2026-09-23](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md), [2](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md) |
| Mistral | Mistral Vibe | Yes — `~/.vibe/AGENTS.md` and project directories; needs folder trust | Yes — `.agents/skills`, `.vibe/skills`, `~/.vibe/skills`, `~/.agents/skills` | `CLAUDE_SKILLS_DIR=~/.agents/skills make install` | [2026-09-23](https://github.com/mistralai/mistral-vibe/blob/main/README.md) |
| OpenAI | Codex CLI | Yes — each `AGENTS.md` from the project root down to the working directory | Yes — `~/.agents/skills` (user), `.agents/skills` (repository); also `$CODEX_HOME/skills` (default `~/.codex/skills`, legacy compatibility) | `CLAUDE_SKILLS_DIR=~/.agents/skills make install` | [2026-09-30](https://github.com/openai/codex/blob/main/codex-rs/core/src/agents_md.rs), [2](https://github.com/openai/codex/blob/main/codex-rs/skills/src/lib.rs), [3](https://github.com/openai/codex/blob/main/codex-rs/utils/home-dir/src/lib.rs), [4](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills), [5](https://github.com/openai/codex/blob/rust-v0.144.0-alpha.4/codex-rs/core-skills/src/loader.rs) |
| xAI | Grok Build | Yes, and `CLAUDE.md`; needs folder trust | Yes — `.grok/skills`, `.agents/skills`, and `~/.claude/skills` | `make install` already links every skill where it looks | [2026-09-23](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/08-skills.md), [2](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/12-project-rules.md) |

<!-- providers-table:end -->

</details>

For a chat product with no skills loader, the portable export still applies. There is no
marketplace to read there, so the skills are flattened into files that stand alone
— frontmatter becomes a plain "Use this when" line and every reference file is inlined, so
nothing is left pointing at a path the reader cannot open.

You do not need a toolchain to get them. Every CI run builds them and attaches them as
the **portable-skills** artifact: open the
[latest run](https://github.com/greenblacked/AI/actions/workflows/ci.yml?query=branch%3Amain),
scroll to Artifacts, and download. Inside are one file per skill, one bundle per plugin,
an index of every description, a router sized to fit inside a terminal agent's own
document budget, and a README explaining where each goes.

If you do have a terminal, build them yourself instead:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
make portable       # writes dist/portable/
```

Either way: upload the `plugins/*.md` bundles to a ChatGPT Project or a Custom GPT, paste
a single `skills/<name>.md` into any chat, or paste `router.md` — or one narrower
`router-<plugin>.md` — into the `AGENTS.md` of the repository a terminal agent is working
in, with `skills/` copied in beside it. Once the catalogue outgrows the router's size
budget, `router.md` is an index of the `router-<plugin>.md` files rather than the
combined router, so paste the plugin files you want. [Using the skills](docs/using.md) has the
instruction text that makes a Project reach for them, why a terminal agent gets the
router rather than a bundle, and says plainly what does not survive the trip.

### Running the skills on DeepSeek

The one route this repository takes a position on is below, linked to its full
configuration in [`docs/deepseek.md`](docs/deepseek.md).

| Route | Tool | Gateway | Set this | Status |
| --- | --- | --- | --- | --- |
| [Claude Code → OpenRouter → DeepSeek](docs/deepseek.md#claude-code-through-openrouter-to-deepseek) | Claude Code | OpenRouter | `ANTHROPIC_BASE_URL=https://openrouter.ai/api`, `ANTHROPIC_API_KEY` empty, model = OpenRouter's DeepSeek id | OpenRouter only guarantees its Anthropic first-party provider; unsupported by Anthropic |

### Working on the skills themselves

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
./scripts/install.sh --plugin coding --dry-run   # preview one plugin
./scripts/install.sh --plugin coding             # link it into ~/.claude/skills
```

Omit `--plugin` to install every skill, or repeat it to select several plugins.

## What a real week looks like

You never type a skill name. You describe the situation in the words you would use to a
colleague, and the skill whose description matches that situation loads itself. This is
one service going from nothing to running badly to running well, with the sentence that
fired each step.

**Monday — the service does not exist yet.**

| You say | What loads | What it makes you do first |
| --- | --- | --- |
| "set up a pipeline for this repo" | `ci-pipeline-design` | Decide which checks may block a merge before drawing a single stage |
| "what should I set for resource limits" | `k8s-workloads` | Measure the workload under load before writing any number |
| "write me a script that prunes old snapshots" | `code-scaffold` | Ask the questions that change the shape of the code, in one batch, before writing |

**Wednesday — it ships.**

| You say | What loads | What it makes you do first |
| --- | --- | --- |
| "canary or blue-green for this one" | `release-strategy` | Separate deploy from release, then pick the mechanism from how the change fails |
| "we need to move the DNS without dropping requests" | `cutover` | Name the roles and the point of no return before the window opens |
| "this migration adds a column to a 40M-row table" | `db-migration` | Expand, backfill, migrate reads, migrate writes, contract — each revertible alone |

**Thursday, 3am — it breaks.**

| You say | What loads | What it makes you do first |
| --- | --- | --- |
| "pods are in CrashLoopBackOff and I am on call" | `k8s-triage` | Restore service first; diagnosis is the second job |
| "the payment provider's status page just went red" | `incident-response` | Name an IC who will not debug, set severity once, and mitigate by symptom |
| *(a 200MB CI log)* | `ci-log-reader` *(subagent)* | Returns which of five triage classes it is and the log line that decided it |
| "what do we tell customers" | `incident-comms` | Acknowledge on impact, not on diagnosis, and promise a next update you keep |

**Friday — you find out why, and stop it recurring.**

| You say | What loads | What it makes you do first |
| --- | --- | --- |
| "write this up without blaming anyone" | `postmortem` | Separate the root causes from the trigger; every action item gets an owner and a date |
| "our pager is out of control" | `alert-design` | Classify every signal as page, ticket or dashboard-only, and alert on SLO burn |
| "I renamed a module and now it wants to destroy everything" | `terraform-state` | Back up state before touching it, and prefer the form that shows up in a plan |
| "our bill went up 30% and nobody knows why" | `cost-review` | Attribute the spend before touching anything, then read top movers over top spenders |

Two things in that week are worth naming. The subagent on Thursday exists so a
200MB log never enters your context — you get the verdict, not the bytes. And every
"what it makes you do first" column is the actual value: the model already knows what a
liveness probe is, but it will happily write you one that checks a database and restarts
healthy pods during someone else's outage. The gate is the skill.

## Skills

### Coding

Reading, reviewing, testing and changing code.

| Skill | What it does |
| --- | --- |
| [`agent-delegation`](plugins/coding/skills/agent-delegation/SKILL.md) | Brief one coding agent on one bounded task: a runnable done-check, the failing evidence, an explicit scope fence, stop conditions, and evidence required back before anyone accepts the diff. |
| [`agent-evaluation`](plugins/coding/skills/agent-evaluation/SKILL.md) | Evaluate an agent against reproducible tasks, tool-call outcomes and calibrated judges, with held-out cases and explicit release gates. |
| [`agent-failure-diagnosis`](plugins/coding/skills/agent-failure-diagnosis/SKILL.md) | Find which layer of an agent's environment makes it repeat one mistake in a repository: capture the failing runs first, rule out cheaper explanations, attribute each failure to instructions, tools, state, verification or scope, and change one thing at a time. |
| [`agent-guardrails`](plugins/coding/skills/agent-guardrails/SKILL.md) | Turn a rule or a repeated agent mistake into the cheapest mechanism that enforces it: a checkable statement, the lowest rung of the ladder that can hold it, red before green, a failure message the agent can fix from, protected guard paths, and a replay over recent merges before it blocks anyone. |
| [`agent-handoff`](plugins/coding/skills/agent-handoff/SKILL.md) | Preserve one agent task as a durable checkpoint another session can resume, with verified state, evidence, decisions, the next action and the completion test. |
| [`agent-instructions`](plugins/coding/skills/agent-instructions/SKILL.md) | Write or repair a repository's AGENTS.md, and a CLAUDE.md that imports it: run the real commands first and keep only what was executed, keep the entry file short with pointers to topic files, give every rule its reason and its enforcer, measure size in bytes, and pass only when a fresh session answers five fixed questions correctly. |
| [`agent-orchestration`](plugins/coding/skills/agent-orchestration/SKILL.md) | Coordinate a live team of agents: split independent ownership, schedule within the concurrency limit, track progress, resolve blockers and synthesise the results. |
| [`api-design`](plugins/coding/skills/api-design/SKILL.md) | Design an interface that can still be changed after other people depend on it — compatibility rules, error structure, pagination, and deprecation with usage telemetry. |
| [`architecture-diagrams`](plugins/coding/skills/architecture-diagrams/SKILL.md) | Draw architecture, sequence and flow diagrams as code that renders where it will be read: the tool chosen by target surface, one C4 level per diagram under a node cap, quoted labels, a render that fails the build on a non-zero exit, and source kept beside the output. |
| [`application-caching`](plugins/coding/skills/application-caching/SKILL.md) | Design a runtime data cache from its correctness contract: define authority and allowed staleness, make keys preserve isolation, close stale-fill races, control miss load and outage fallback, then roll out against measured safety gates. |
| [`code-review`](plugins/coding/skills/code-review/SKILL.md) | Review a change in a fixed order — the claim, the error path, concurrency, hostile input — finishing correctness before the first style comment, with a severity on every finding and coverage declared rather than implied. |
| [`code-scaffold`](plugins/coding/skills/code-scaffold/SKILL.md) | Write new code that survives a 3am cron run: strict error handling, meaningful exit codes, structured logging, validated input, idempotent re-runs. |
| [`codebase-orientation`](plugins/coding/skills/codebase-orientation/SKILL.md) | Get oriented in code you did not write: what it does before how it is built, one real request traced end to end, the tests as specification and the history as evidence, ending in a map and a first change. |
| [`debugging`](plugins/coding/skills/debugging/SKILL.md) | Drive a failure down to a proven cause before changing any code: reproduce it, reduce it, one falsifiable hypothesis at a time, and prove the fix by turning the failure off and on again. |
| [`dependency-upgrade`](plugins/coding/skills/dependency-upgrade/SKILL.md) | Move onto a new major version without a branch that never lands: deprecation warnings first, one dependency per change, and the uncovered surface named. |
| [`e2e-testing`](plugins/coding/skills/e2e-testing/SKILL.md) | Keep a browser suite trustworthy instead of rerun until green: measure each test's real flake rate first, locate by role and accessible name, wait on state rather than a sleep or network idle, authenticate once, and prove a repaired test can still fail. |
| [`feature-spec`](plugins/coding/skills/feature-spec/SKILL.md) | Turn a loose feature request into a written spec and a checkpointed task plan before any code exists: one question at a time, explicit non-goals, acceptance criteria phrased as checks, two or three approaches compared, and tasks small enough to verify with the riskiest first. |
| [`new-skill`](plugins/coding/skills/new-skill/SKILL.md) | Author a skill that actually fires: decide whether it deserves to exist, write the body before the description, and build the eval set from the neighbouring skills it has to beat. |
| [`profiling`](plugins/coding/skills/profiling/SKILL.md) | Make slow application code fast or prove it cannot be: rule out the database and the network first, sample the real process under load, read self time and call paths rather than the function that feels slow, and prove each change against measured variance. |
| [`refactoring`](plugins/coding/skills/refactoring/SKILL.md) | Restructure without changing behaviour, in steps each provably safe: a characterisation test before touching code nobody understands, one kind of change per commit, and a proof at the end. |
| [`retrieval-evaluation`](plugins/coding/skills/retrieval-evaluation/SKILL.md) | Compare retrievers on frozen, access-scoped queries with paired recall and ranking metrics, a sealed holdout and an independent access-leak veto. |
| [`schema-design`](plugins/coding/skills/schema-design/SKILL.md) | Design the tables for a new feature before any migration exists: the query list first, keys and constraints chosen deliberately, and every type decision — money, time, soft delete — made on purpose rather than inherited from an ORM default. |
| [`sql-performance`](plugins/coding/skills/sql-performance/SKILL.md) | Make a slow query fast or prove it cannot be: start from the statement with the most total time rather than the one someone complained about, read the plan from the deepest node out to the first place estimates and reality diverge, and decide between an index, a rewrite and accepting it. |
| [`technical-docs`](plugins/coding/skills/technical-docs/SKILL.md) | Write documentation still true in six months: name the reader, pick one Diátaxis mode instead of blending two, execute every command you print, and prune the stale page rather than adding a newer one beside it. |
| [`test-design`](plugins/coding/skills/test-design/SKILL.md) | Choose what to test before writing tests: equivalence classes and their boundaries, the error paths nobody writes, pairwise selection when the inputs explode, and the seams that stop a suite going flaky. |
| [`website-builder`](plugins/coding/skills/website-builder/SKILL.md) | Build a site that looks designed for its subject and can still be hosted and maintained afterwards — or audit one that already exists. |

### Family

One development workflow, from a vague request to a measured outcome, run by a solo developer, a developer, a QA engineer or a whole team, light or full per slice.

| Skill | What it does |
| --- | --- |
| [`family-workflow`](plugins/family/skills/family-workflow/SKILL.md) | Run one slice through Frame, Architect, Make, Inspect, Launch and Yield, each with a gate, an artifact and a handoff, run by one of four profiles — solo, developer, QA or team — at a light or full depth chosen per slice, routing the detail to the skill that owns it. |
| [`solo-development`](plugins/family/skills/solo-development/SKILL.md) | Run all six stages as one person, with the stage agents as the independent checkers a solo developer otherwise lacks, and waive a gate only in writing. |
| [`developer-workflow`](plugins/family/skills/developer-workflow/SKILL.md) | Own Frame, Architect, Make and Yield, and hand Inspect and Launch to someone independent with the frame, the plan and the uncertainty. |
| [`qa-workflow`](plugins/family/skills/qa-workflow/SKILL.md) | Own Inspect, push testable acceptance criteria back into Frame and Architect, own the go/no-go before Launch, and turn a repeated defect into a Frame check. |
| [`team-workflow`](plugins/family/skills/team-workflow/SKILL.md) | Run all six stages with a named owner and a handoff contract between each, make a stall visible as a missing artifact, and run Yield on a cadence. |
| [`family-relay`](plugins/family/skills/family-relay/SKILL.md) | Chain the six stage agents so each verdict word picks the next hop, pass only the artifact and the previous handoff, and step back a stage when the same verdict returns twice. |
| [`frame-claim-ledger`](plugins/family/skills/frame-claim-ledger/SKILL.md) | List the claims a frame or design rests on, settle the two heaviest in parallel before the hard-to-reverse decision, and send an unverified one back to Frame. |
| [`plan-drift-gate`](plugins/family/skills/plan-drift-gate/SKILL.md) | Build from maker's plan one step and commit at a time, and check the diff against the plan before inspection so the inspector judges correctness rather than shape. |
| [`fresh-inspector-rounds`](plugins/family/skills/fresh-inspector-rounds/SKILL.md) | Inspect in rounds with a new inspector each time, send back only blocking findings, and reopen Architect when the same finding returns. |
| [`yield-to-lesson`](plugins/family/skills/yield-to-lesson/SKILL.md) | Accept a retro's change item only as a lesson plus a seeded case the next inspection can fail on, and promote a lesson caught twice to a mechanical check. |
| [`stage-tiering`](plugins/family/skills/stage-tiering/SKILL.md) | Run each stage agent on the model tier its cost of being wrong deserves, at most two in parallel on disjoint questions, then combine their results in a named step. |

### Gamedev

Making games, and shipping them. [`docs/gamedev.md`](docs/gamedev.md) is the route
through this plugin's skills by production scale and game type.

| Skill | What it does |
| --- | --- |
| [`game-greenlight`](plugins/gamedev/skills/game-greenlight/SKILL.md) | Turn a game concept into a chosen idea before any design document exists: a one-page pitch, a feasibility read against team, time, money, platform and technical risk, a risk register naming the one riskiest assumption, and go, no-go and pivot criteria written before the prototype exists to argue for itself. |
| [`game-assets`](plugins/gamedev/skills/game-assets/SKILL.md) | Get art and audio into the build without it eating the disk, the memory or the download — source kept out of the import path, large binaries behind LFS before the history is too big, and per-platform texture compression chosen rather than defaulted. |
| [`game-balance`](plugins/gamedev/skills/game-balance/SKILL.md) | Tune a game's numbers against evidence rather than taste: decide what balanced means for this game first, read pick rate against win rate by skill band, change one thing with a window, and carry what a playtest shows into the numbers as a hypothesis. |
| [`game-builder`](plugins/gamedev/skills/game-builder/SKILL.md) | Build a playable game scaled to the brief — core loop first in grey boxes, then a game-feel floor tuned against numbers — or review one that exists for feel, frame time and structure. |
| [`game-design-doc`](plugins/gamedev/skills/game-design-doc/SKILL.md) | Turn a game idea or a design conversation into a feature specification the whole team can build from: out of scope before scope, every statement marked as a decision, an assumption, a recommendation or an open question, and acceptance criteria a stranger can fail. |
| [`game-level-design`](plugins/gamedev/skills/game-level-design/SKILL.md) | Lay out a level as a space: player metrics fixed before any geometry so every dimension derives from them, pacing charted as explore, combat, choreo and puzzle beats with no category repeating, and wayfinding cues built into the blockmesh and playtested there rather than asserted after art. |
| [`game-localisation`](plugins/gamedev/skills/game-localisation/SKILL.md) | Take a game from one language to many without shipping broken text: keyed strings with translator notes and length limits, pseudo-localisation early, plurals through ICU MessageFormat, fonts and right-to-left planned per script, and linguistic QA in context with a bug taxonomy. |
| [`game-netcode`](plugins/gamedev/skills/game-netcode/SKILL.md) | Choose a multiplayer authority model from genre and player count, then hide latency with prediction, reconciliation and interpolation — and treat anything the client is authoritative over as a thing the client can lie about. |
| [`game-certification`](plugins/gamedev/skills/game-certification/SKILL.md) | Clear platform certification and store submission on the first try: work backwards from the release date to a content lock, run the checks that can fail cert before the ones that only polish, and declare ratings and data collection against what the build actually does. |
| [`game-save-system`](plugins/gamedev/skills/game-save-system/SKILL.md) | Name the compatibility promise before the format — how many builds back a save must load — then version the schema, migrate one step per bump, write atomically so an interrupted save is not a corrupt one, and settle cloud conflicts by lineage rather than by timestamp. |
| [`game-performance`](plugins/gamedev/skills/game-performance/SKILL.md) | Hold a frame budget on the hardware you ship to: milliseconds not FPS, captured from a real build on the device, judged at the 1% low, and CPU-bound proved against GPU-bound before a single optimisation. |
| [`game-live-ops`](plugins/gamedev/skills/game-live-ops/SKILL.md) | Run a game after launch: a content and season calendar planned ahead rather than assembled week to week, economy tuning scheduled with guardrails, KPIs and a stop rule chosen before the season starts, a patch-and-hotfix rhythm, and community communication that keeps the roadmap honest. |
| [`game-playtest`](plugins/gamedev/skills/game-playtest/SKILL.md) | Run a playtest so it ends in decisions rather than opinions: one question per session, the target player instead of friends, silent observation before asking, a short survey on fixed scales, bugs kept apart from design findings, and a ranked change list with the measurement that would show each fix worked. |

### Operations

Keeping a running system alive.

| Skill | What it does |
| --- | --- |
| [`alert-design`](plugins/operations/skills/alert-design/SKILL.md) | Write, review or delete alerting rules so every page is user-visible and actionable now: symptom over mechanism, multiwindow burn-rate rules, and pruning by how often anyone acted rather than by how often it fired. |
| [`backup-recovery-design`](plugins/operations/skills/backup-recovery-design/SKILL.md) | Design recoverability around business recovery objectives, backup consistency, independent recovery access and dependency-ordered restoration. |
| [`capacity-planning`](plugins/operations/skills/capacity-planning/SKILL.md) | Work out whether a system survives an expected load: a demand model first, the one saturating resource, and a defined behaviour past capacity. |
| [`ci-triage`](plugins/operations/skills/ci-triage/SKILL.md) | Classify a red pipeline before debugging it — real failure, flake, runner, config, or dependency drift — starting with whether the default branch is already broken. Quarantine policy and retry hygiene included. |
| [`cost-review`](plugins/operations/skills/cost-review/SKILL.md) | Investigate a bill that grew, or reduce spend deliberately: attribute before acting, read the top movers rather than the top spenders, and name what each saving degrades. |
| [`disaster-recovery-exercise`](plugins/operations/skills/disaster-recovery-exercise/SKILL.md) | Rehearse restoration from recovery copies, measure end-to-end RTO and RPO, verify integrity, and obtain business acceptance with an isolated target and tested abort. |
| [`docker-compose`](plugins/operations/skills/docker-compose/SKILL.md) | Compose containers into a working environment for local development and CI: every dependency edge gated on a healthcheck condition, because started is not ready, plus service discovery, mount semantics, config layering and digest pinning. |
| [`event-driven-reliability`](plugins/operations/skills/event-driven-reliability/SKILL.md) | Make an event consumer safe to retry and replay: state delivery assumptions, map every crash window, choose durable identities and atomicity boundaries, bound retries and dead letters, and verify duplicates, reordering and recovery. |
| [`game-day`](plugins/operations/skills/game-day/SKILL.md) | Plan and run a reliability exercise around a falsifiable hypothesis, with a blast radius chosen in advance and an abort that was executed before the experiment started. |
| [`incident-response`](plugins/operations/skills/incident-response/SKILL.md) | Declare, command and mitigate a live production incident on any surface — a managed database failover, a third-party outage, a VM fleet, serverless, a CDN or DNS provider — mitigating by symptom before the diagnosis is complete, and handing off to `k8s-triage` for a Kubernetes workload. |
| [`instrumentation`](plugins/operations/skills/instrumentation/SKILL.md) | Add telemetry so the next incident is diagnosable — instrument backwards from the questions you will need answered at 3am, with cardinality bounded on purpose. |
| [`k8s-triage`](plugins/operations/skills/k8s-triage/SKILL.md) | Mitigate first, diagnose second. The deploy-related question, the fixed evidence order, and a decode table for the failure modes that account for most of them. |
| [`k8s-upgrade`](plugins/operations/skills/k8s-upgrade/SKILL.md) | Upgrade a Kubernetes cluster one minor at a time: find deprecated API usage from live traffic before the window opens, clear every blocking PodDisruptionBudget, and canary each node pool across a full traffic peak. |
| [`k8s-workloads`](plugins/operations/skills/k8s-workloads/SKILL.md) | Specify a workload so it holds under pressure: measure before setting any number, then requests and limits knowing CPU throttles where memory kills, distinct probes, a disruption budget that does not deadlock drains, and the SIGTERM race closed. |
| [`llm-cost`](plugins/operations/skills/llm-cost/SKILL.md) | Control what an LLM feature costs without degrading it: attribute spend to a prompt path first, judge caching on reads per write rather than hit rate, route cheap steps against a measured quality bar, and decide degrade, queue or refuse before a budget runs out. |
| [`routeros-config`](plugins/operations/skills/routeros-config/SKILL.md) | Change, upgrade or recover a MikroTik RouterOS device without locking yourself out: a second way in proven before the change, a text export either side of it, the change made under safe mode, and verification over a path you did not touch. |
| [`runbook`](plugins/operations/skills/runbook/SKILL.md) | Write what the 3am reader follows: numbered steps, real commands, every mitigation with its blast radius, and a last-verified date, because a wrong runbook is worse than none. |
| [`slo-design`](plugins/operations/skills/slo-design/SKILL.md) | Define measurable user journey SLIs, targets, compliance windows and error budgets with an owner and evidence before alert rules are written. |
| [`terraform-state`](plugins/operations/skills/terraform-state/SKILL.md) | Execute the state operation already decided — import, move, remove, reconcile drift, recover a lost file, clear a stuck lock — taking a backup first and preferring the block forms that show up in a plan over the imperative subcommands. |

### Delivery

Getting a change into production without a bad night.

| Skill | What it does |
| --- | --- |
| [`ai-review-integration`](plugins/delivery/skills/ai-review-integration/SKILL.md) | Design or implement an advisory AI reviewer for GitLab merge requests around a trusted controller, immutable MR versions, explicit diff coverage, deterministic finding validation, reconciled comments, and a staged rollout with a kill switch. |
| [`ci-pipeline-design`](plugins/delivery/skills/ci-pipeline-design/SKILL.md) | Design a pipeline that does not exist yet, or restructure one that grew badly: decide what may block a merge first, then a stage graph that waits on nothing it does not use, cache keys tied to what invalidates them, and one artefact promoted by digest. |
| [`cutover`](plugins/delivery/skills/cutover/SKILL.md) | Run the change that has a point of no return — a traffic switch, a provider move, a region migration — from a rehearsed runbook with a rollback deadline computed before the window opens. |
| [`db-migration`](plugins/delivery/skills/db-migration/SKILL.md) | Ship a schema change to a live database without a stuck lock: expand and contract, each phase its own revertible deploy, batched backfills, and the Postgres operations that are safe versus the ones that rewrite the table. |
| [`feature-flag-lifecycle`](plugins/delivery/skills/feature-flag-lifecycle/SKILL.md) | Implement a sticky, failure-safe flag with a verified off path, kill-switch exercise and mixed-version compatibility before retirement. |
| [`gitops-operations`](plugins/delivery/skills/gitops-operations/SKILL.md) | Operate GitOps reconciliation safely: identify desired-state ownership, review sync and pruning effects, and recover without fighting the controller. |
| [`mobile-release`](plugins/delivery/skills/mobile-release/SKILL.md) | Ship a native iOS or Android build through the app store's own phased or staged rollout: a server-side flag for the binary that cannot be recalled, an agreed crash-free halt threshold, and a rejection triaged against the guideline it cites. |
| [`pipeline-hardening`](plugins/delivery/skills/pipeline-hardening/SKILL.md) | Audit or harden a CI/CD workflow's own definition against what an attacker can reach through it: untrusted input into a `run:` step, `pull_request_target` paired with a checkout of fork code, credential reach per job, and every pin, with zizmor findings judged rather than counted. |
| [`plan-platform-migration`](plugins/delivery/skills/plan-platform-migration/SKILL.md) | Plan a production migration around invariants, state authority, phased evidence gates, rehearsed rollback, controlled cutover, and explicit legacy retirement. |
| [`release-notes`](plugins/delivery/skills/release-notes/SKILL.md) | Turn a range of merged changes into notes the affected reader can act on, sorted by who is affected rather than by component, every breaking change carrying the migration it demands. |
| [`release-strategy`](plugins/delivery/skills/release-strategy/SKILL.md) | Separate deploy from release: flags, rings and canaries chosen by how the change fails, with promotion gates, bake times and a flag removal date. |
| [`safe-backfill`](plugins/delivery/skills/safe-backfill/SKILL.md) | Run a standalone data repair in bounded, restartable batches with guarded writes, scanned-key checkpoints and independent reconciliation. |

### Security

The defensive side of shipping software.

| Skill | What it does |
| --- | --- |
| [`access-review`](plugins/security/skills/access-review/SKILL.md) | Reduce who and what can do what toward least privilege without breaking production: evidence over intent, and an audit-only window before enforcement. |
| [`agent-extension-audit`](plugins/security/skills/agent-extension-audit/SKILL.md) | Vet a third-party skill, plugin, hook, MCP server or slash command before installing it: fetch to quarantine without running anything, read every executable file, list declared and effective permissions, then install, restrict or reject and record the pinned commit and hash. |
| [`agent-security-review`](plugins/security/skills/agent-security-review/SKILL.md) | Review an agent from untrusted content to privileged effect: trace provenance into tool arguments, enforce authorization and tenant scope at execution, bind approval to the exact action, constrain capabilities and prove deny paths with inert tests. |
| [`auth-design`](plugins/security/skills/auth-design/SKILL.md) | Design or review how a system proves who a caller is and keeps that proof safe: whether to build identity at all, the flow that fits each client type, session rotation on every privilege change, and where a token's claims can be trusted. |
| [`authorization-design`](plugins/security/skills/authorization-design/SKILL.md) | Design application permissions around trusted subject, tenant and resource facts, with default-deny policy, server-side enforcement on every path, bounded revocation latency and tests for allowed actions and tenant boundaries. |
| [`certificate-automation`](plugins/security/skills/certificate-automation/SKILL.md) | Move a certificate estate onto automated ACME issuance and renewal ahead of the CA/Browser Forum's shrinking maximum lifetimes: inventory from outside first, classify every endpoint by ACME capability, schedule by ACME Renewal Information with a lifetime-fraction backstop, and alert on renewal failure. |
| [`data-privacy`](plugins/security/skills/data-privacy/SKILL.md) | Handle personal data end to end: settle controller or processor before anything else, classify what is held, enforce retention with a job rather than a document, and make deletion reach the search index, the caches and the restore path instead of only the primary row. |
| [`dependency-triage`](plugins/security/skills/dependency-triage/SKILL.md) | Work a queue of vulnerability alerts into a decision each — reachability before severity, the two signals that mean today rather than this quarter, safe patches batched and risky ones isolated, and suppression that expires. |
| [`host-hardening`](plugins/security/skills/host-hardening/SKILL.md) | Harden a Linux or Unix host against a named baseline without locking yourself out: preserve a second way in before touching sshd or sudo, export the config either side, change one class at a time on a canary, and verify over a path you did not edit — across SSH, sudo, auditd, sysctl, services and permissions. |
| [`iac-review`](plugins/security/skills/iac-review/SKILL.md) | Review a Terraform change against the plan JSON rather than the plan text, so replacements and destroys surface first instead of being skimmed past. |
| [`image-hardening`](plugins/security/skills/image-hardening/SKILL.md) | Build or audit a container image: minimal base, digest pinning, numeric non-root UID, no secrets in layers, SBOM, a scan gate that will not get bypassed, signing that is actually verified. |
| [`secret-rotation`](plugins/security/skills/secret-rotation/SKILL.md) | Rotate a credential, or contain one that has leaked. The two run in opposite orders, and the skill makes you pick which one you are in before it does anything else. |
| [`security-review`](plugins/security/skills/security-review/SKILL.md) | Walk a diff through the classes that actually get exploited — object-level authorisation, injection, deserialisation, request forgery, secrets, the supply-chain change — reporting each as reachable path, impact, fix. |
| [`security-test-engagement`](plugins/security/skills/security-test-engagement/SKILL.md) | Commission or run an authorised pentest, red-team or bug-bounty engagement from the asset owner's side: signed authorisation and scope before anything starts, rules of engagement with stop conditions, a reachable emergency contact, rules for test data, and a path from each finding to a confirmed retest. |
| [`threat-model`](plugins/security/skills/threat-model/SKILL.md) | Model a design before the code exists: draw the flows, mark every trust boundary, apply STRIDE per crossing rather than per component, and write down the threats you chose to accept with a name against each. |

### Manager

Engineering leadership.

| Skill | What it does |
| --- | --- |
| [`ai-enablement`](plugins/manager/skills/ai-enablement/SKILL.md) | Assess how a team actually uses AI-assisted engineering and produce a rollout plan, including the metrics that help and the ones that quietly destroy honest feedback. |
| [`compensation-benchmarking`](plugins/manager/skills/compensation-benchmarking/SKILL.md) | Set or defend pay from evidence — the level before the price, a band from sources that fit, placement by compa-ratio, compression and pay-equity checked before the offer rather than after the complaint. |
| [`decision-record`](plugins/manager/skills/decision-record/SKILL.md) | Turn a decision into a MADR-format ADR or a design doc, with at least two genuinely considered options and a confirmation step that names a real check. |
| [`delivery-review`](plugins/manager/skills/delivery-review/SKILL.md) | Read delivery health honestly: DORA as a property of the system rather than of people, flow and queue time, and prioritisation frameworks applied only where they belong. |
| [`design-team-cadence`](plugins/manager/skills/design-team-cadence/SKILL.md) | Design a minimal management operating rhythm where every recurring forum has a decision or relationship purpose, explicit inputs and outputs, and a cancellation rule. |
| [`difficult-conversation`](plugins/manager/skills/difficult-conversation/SKILL.md) | Prepare and hold the conversation you keep putting off: the outcome fixed first, observed behaviour separated from the story about intent, and an honest answer to whether this is feedback or a decision already made. |
| [`growth-review`](plugins/manager/skills/growth-review/SKILL.md) | Prepare a review, a promotion case or a development plan from evidence over the whole period rather than the last six weeks, where every claim carries an example. |
| [`hiring-loop`](plugins/manager/skills/hiring-loop/SKILL.md) | Design and run a hiring loop from a scorecard: stages that each test something the others do not, written scores before the debrief, and "culture fit" restated as a named behaviour or dropped. |
| [`incident-comms`](plugins/manager/skills/incident-comms/SKILL.md) | Communicate an incident to customers, executives and staff: acknowledge on impact rather than diagnosis, and keep the next-update promise even when nothing has changed. |
| [`okr-planning`](plugins/manager/skills/okr-planning/SKILL.md) | Set goals that change what people do — an objective is the outcome, a key result is the evidence — with baselines before targets and guardrails beside them. |
| [`onboarding-plan`](plugins/manager/skills/onboarding-plan/SKILL.md) | Get a new engineer productive deliberately: access working before day one, something shipped in week one, and 30/60/90 expectations written down and shared. |
| [`performance-improvement-plan`](plugins/manager/skills/performance-improvement-plan/SKILL.md) | Run the formal improvement process honestly — the gaps as observable behaviour, real support, a dated end, and an outcome the evidence decides rather than one set before the plan began. |
| [`postmortem`](plugins/manager/skills/postmortem/SKILL.md) | Write a blameless postmortem in the Google SRE shape, where "human error" is a prompt for a better question and every action item has an owner. |
| [`retention-review`](plugins/manager/skills/retention-review/SKILL.md) | Read why people actually leave and who is at risk — attrition aggregated over a year, stay interviews held before the resignation, and survey results turned into a few owned actions. |
| [`status-update`](plugins/manager/skills/status-update/SKILL.md) | Bottom line up front for status, Minto for persuasion, and never the two mixed. Numbers are sourced or marked as missing. |
| [`vendor-evaluation`](plugins/manager/skills/vendor-evaluation/SKILL.md) | Run a buy decision to a defensible conclusion, including the decision not to buy — weights agreed before any demo, three-year total cost, and an exit cost established while you still have leverage. |

### Personal

The parts of life that are nobody's job.

| Skill | What it does |
| --- | --- |
| [`habit-change`](plugins/personal/skills/habit-change/SKILL.md) | Change one behaviour so it survives a bad week: small enough that a bad day cannot stop it, anchored to a cue rather than a clock, with the environment redesigned and a recovery rule written before it breaks. |
| [`health-coach`](plugins/personal/skills/health-coach/SKILL.md) | Estimate calories and macros from a photo or a description, as a range with the uncertainty named, then suggest one thing worth changing. |
| [`life-admin`](plugins/personal/skills/life-admin/SKILL.md) | Get through a renewal, claim, registration or dispute in one attempt: the authoritative requirement first, the documents that need other documents, a record of every submission, and the escalation path for when it stalls. |
| [`major-purchase`](plugins/personal/skills/major-purchase/SKILL.md) | Decide on something expensive you will live with for years: the requirement written before any option is looked at, cost over its whole life rather than its sticker, and the financing arithmetic a monthly payment is designed to hide. |
| [`personal-finance`](plugins/personal/skills/personal-finance/SKILL.md) | Build the picture from real statements rather than memory, annualise what monthly thinking hides, size the buffer against fixed outgoings rather than pay, and model the decision before making it. |
| [`travel-planning`](plugins/personal/skills/travel-planning/SKILL.md) | Plan around the constraints that actually break trips: entry rules verified at the official source, connection minimums, what a self-transfer costs you when the first leg is late, and change windows before booking. |
| [`weekly-review`](plugins/personal/skills/weekly-review/SKILL.md) | Run a short weekly review whose only output is what you are doing next week and what you are consciously not doing, planned against the hours that are actually free. |

### Career

Applications, negotiation, speaking and writing.

| Skill | What it does |
| --- | --- |
| [`conference-talk`](plugins/career/skills/conference-talk/SKILL.md) | Take a talk from idea to accepted proposal to a delivery that lands: one takeaway, a structure that survives being heard once, and rehearsal out loud and timed. |
| [`job-search`](plugins/career/skills/job-search/SKILL.md) | Tailor a CV and prepare for interviews from a real history. Selection and evidence, never embellishment. |
| [`learning-notes`](plugins/career/skills/learning-notes/SKILL.md) | Turn something read into a note that is still useful in a year, on the principle that a summary is not a note. |
| [`offer-negotiation`](plugins/career/skills/offer-negotiation/SKILL.md) | Evaluate and negotiate an offer: total compensation decomposed, levelling as the negotiation that compounds, and nothing real until it is in writing. |
| [`write-technical-article`](plugins/career/skills/write-technical-article/SKILL.md) | Turn real engineering experience and verifiable sources into a publishable technical article with a defensible thesis and no invented authority. |

### Design

Usability, accessibility and design systems, and the words, structure and handoff around them.

| Skill | What it does |
| --- | --- |
| [`accessibility-audit`](plugins/design/skills/accessibility-audit/SKILL.md) | Audit a page, flow or component against WCAG 2.2 Level AA: the automated tools first because they are cheap, then the manual pass they cannot do, with every finding tied to a success criterion, a severity and a fix. |
| [`data-visualisation`](plugins/design/skills/data-visualisation/SKILL.md) | Turn data into a chart that is correct and readable in any medium: the chart chosen from the question, bars on a zero baseline, no dual axes or 3D, a colour-blind-safe palette that holds contrast on light and dark, direct labels, a text alternative with the data table, and a re-read of the rendered image against the data. |
| [`content-design`](plugins/design/skills/content-design/SKILL.md) | Write and review the words in an interface: every label naming the user's action, every error saying what happened and what to do, empty and loading states designed rather than left blank, and a voice that holds while the tone shifts by moment. |
| [`design-handoff`](plugins/design/skills/design-handoff/SKILL.md) | Turn an approved design into a buildable spec: every state and edge case, content extremes, responsive behaviour, token and component mapping, accessibility annotations and acceptance criteria an engineer can check against. |
| [`design-system`](plugins/design/skills/design-system/SKILL.md) | Set up design tokens named by role, themes that redefine the same roles, and component states derived from them, with a contrast check of every role pair in every theme and a rule for where glass materials belong. |
| [`information-architecture`](plugins/design/skills/information-architecture/SKILL.md) | Structure a site or app so people can find things: sitemap, navigation, taxonomy and labels, and browse versus search, grouped by the user's mental model and tested with a card sort or tree test before build. |
| [`problem-validation`](plugins/design/skills/problem-validation/SKILL.md) | Test a problem before proposing a solution: prewritten disconfirming criteria, evidence of past behaviour, deidentified interviews and an honest insufficient-evidence decision. |
| [`ui-ux-review`](plugins/design/skills/ui-ux-review/SKILL.md) | Review one screen or flow against usability heuristics: evidence first, the primary task before polish, every interaction state walked, and each finding written as a problem, a consequence, the smallest fix and a severity from 0 to 4. |
| [`usability-test-plan`](plugins/design/skills/usability-test-plan/SKILL.md) | Plan and run a small test with real people: a question tied to a decision, about five participants a round, neutral tasks, think-aloud, task success and SUS, and severity-rated fixes before the next round. |
| [`visual-design`](plugins/design/skills/visual-design/SKILL.md) | Review or set a screen's visual design: the hierarchy that tells the eye where to go, a type scale, colour roles and a spacing scale, alignment, and the one action that is unambiguously primary. |
| [`visual-review`](plugins/design/skills/visual-review/SKILL.md) | Review a rendered web UI from screenshots without trusting a vision model for what code can measure: a pinned environment, a viewport and theme matrix, a pixel diff, contrast, overflow and DOM checks, then native-resolution crops with every finding tied to a selector and box or labelled unverified. |
| [`responsive-design`](plugins/design/skills/responsive-design/SKILL.md) | Make a layout work from 320 px up: breakpoints chosen from where the content breaks, reflow that changes arrangement and never availability, thumb-sized targets, and the widths to verify. |
| [`form-design`](plugins/design/skills/form-design/SKILL.md) | Design a form people finish: cut the fields, label every one, validate after input rather than on every keystroke, put errors with the field and say how to fix them, and keep the form keyboard-operable. |

### LLM

Building features on language models, and the checks that keep them honest.

| Skill | What it does |
| --- | --- |
| [`rag-design`](plugins/llm/skills/rag-design/SKILL.md) | Design a retrieval-augmented generation pipeline you can show retrieves the right passages: a small labelled eval before any tuning, retrieval scored apart from answer faithfulness, structure-aware chunking with citable source ids, hybrid search, reranking, permission filtering inside the query, and refusal when retrieval is weak. |
| [`structured-output`](plugins/llm/skills/structured-output/SKILL.md) | Get machine-readable output from a model that a program can trust: the schema as the contract, the provider's native structured or strict tool mode rather than prompt-only instructions, validation in code, a bounded repair loop that fails closed, and fixtures of real failures. |
| [`mcp-server-design`](plugins/llm/skills/mcp-server-design/SKILL.md) | Build, test and secure a Model Context Protocol server: a few task-shaped tools written for the model, strict schemas, recoverable failures returned as `isError` results, stdio or Streamable HTTP with Origin checks and audience-validated OAuth, and a `tools/list` snapshot test. |
| [`document-extraction`](plugins/llm/skills/document-extraction/SKILL.md) | Extract structured data from receipts, invoices, forms, tables, charts and scans with a vision model or OCR, and prove the values are right: triage text layer against pixels, source region and confidence per field, arithmetic cross-checks, a second independent extraction and a human for numeric disagreements. |
| [`model-migration`](plugins/llm/skills/model-migration/SKILL.md) | Move an LLM-powered feature to a different model or version without a silent regression: the provider's behaviour changes listed against your requests, a frozen baseline from repeated runs, case-by-case output diffs, cost and latency compared per request, shadow then canary with a rollback trigger, and a decision record. |

### Data

Analytics engineering: why a number is wrong, why a query costs what it does, and what the data really shows.

| Skill | What it does |
| --- | --- |
| [`as-of-history`](plugins/data/skills/as-of-history/SKILL.md) | Answer what was true, or what we believed, on a past date, and keep the history to answer it: classify the question as state, validity or arrival, pick a periodic snapshot, type-2 dimension or append-only change log to match, add recorded time beside valid time for anything restated or backdated, join facts on half-open intervals, accept the design only when a known past report reproduces to the unit, and when history was never captured, rebuild it from audit logs, backups or exports and mark the span inferred. |
| [`consumer-discovery`](plugins/data/skills/consumer-discovery/SKILL.md) | Find who really reads a warehouse table, view or column before you rename, drop or retire it, and retire it safely: pull 90 days or more of warehouse access history and BI query logs, resolve views, service accounts and BI extracts to named people and jobs, add orchestrator lineage and a code search, check for readers logs miss such as data shares and quarter-end jobs, then announce, rename first, run a one-day brownout and read who failed, archive, and drop after a quiet period. |
| [`data-quality-checks`](plugins/data/skills/data-quality-checks/SKILL.md) | Decide which data quality checks a warehouse table gets, what each threshold is and what happens when one fails. Mine the last ten data incidents and write one check per root cause before anything generic, then cover freshness, volume, key uniqueness, null rate and enum drift on the columns consumers use; give every check an action (block publish, warn an owner, or log), take thresholds from 30 days of history and backtest them, and each month delete or demote checks that fired and nobody acted on. |
| [`entity-resolution`](plugins/data/skills/entity-resolution/SKILL.md) | Match records for the same customer, company, person or product across systems that share no key, so that a merge can be measured and undone. Normalise fields first, block on cheap candidate keys instead of comparing all pairs, apply deterministic match and hard non-match rules before any fuzzy score, set match and review thresholds from about 200 hand-labelled pairs with precision and recall per threshold, and keep the link table apart from the golden record so a false merge, the worse error, is reversible. |
| [`join-fanout-hunt`](plugins/data/skills/join-fanout-hunt/SKILL.md) | Find why a total is inflated or a row count grew after a join, and fix it at the grain instead of hiding it: write the grain of every input in one sentence, compare COUNT(*) with COUNT(DISTINCT key) after each join while bisecting the query join by join, classify the cause as many-to-many, a dimension not unique on its key (an unfiltered type-2 history table, overlapping validity ranges) or duplicate source rows, and fix by pre-aggregating to the join grain, never by DISTINCT on the output. |
| [`late-data-maturity`](plugins/data/skills/late-data-maturity/SKILL.md) | Decide when a daily or hourly figure is final enough to publish, from measured arrival lag: record event time and load time on every row, build a maturity curve of the share of each day's eventual rows and value present 1h, 6h, 24h and 7d after the day closes, publish where it passes an agreed completeness on bad days, not the median day, label earlier figures provisional, compare only at equal age, and fix a restatement window incremental models honour. |
| [`metric-movement-decomposition`](plugins/data/skills/metric-movement-decomposition/SKILL.md) | Explain why a ratio metric moved — conversion, average order value, churn — with arithmetic instead of a story: rule out data breaks first (volume, null rate on the segment column, a tracking release, an incomplete latest day), check the move is outside normal week-on-week variation, split the change into rate effect within segments and mix effect from shifting segment shares with a symmetric Kitagawa decomposition, rank segments by contribution, test for Simpson's paradox by recomputing with last period's mix, and report the top three contributors with the sums. |
| [`metric-reconciliation`](plugins/data/skills/metric-reconciliation/SKILL.md) | Settle why two dashboards, teams or systems report different values for the same metric, and end with one definition instead of an explanation: freeze one metric, one day and one segment, reproduce each figure from raw data, diff the two row sets by key with a full outer join, and assign the gap to causes tested in a fixed order — time zone and day boundary, snapshot time, filters and inclusion, dedupe rule, join grain, currency and units — until the residual is zero. Close with one owned, versioned definition and the duplicate retired or renamed. |
| [`scan-cost-forensics`](plugins/data/skills/scan-cost-forensics/SKILL.md) | Find which queries, users, dashboards and jobs drive a data warehouse bill on Snowflake, BigQuery, Redshift or ClickHouse: group query history by normalised-SQL fingerprint and rank by total bytes or credits across every run rather than by the slowest single run, attribute each fingerprint to a dashboard refresh or job schedule, test the usual culprits in order (refresh faster than the data changes, SELECT * on wide tables, unpruned partitions, identical repeats missing the result cache), fix the schedule before the SQL, and measure before and after on a matching window. |
| [`spreadsheet-retirement`](plugins/data/skills/spreadsheet-retirement/SKILL.md) | Replace a business-critical spreadsheet or manual report with a pipeline without losing the trust of the people who rely on it. Inventory the hidden logic first by tracing every input, hard-coded cell, manual override, macro, external link and monthly ritual; turn each override into an explicit, owned rule; run old and new side by side for at least two cycles and reconcile line by line to the cent; make the sheet's owner the acceptance tester; and freeze the sheet read-only only after a clean run. |
| [`upstream-change-defense`](plugins/data/skills/upstream-change-defense/SKILL.md) | Protect warehouse pipelines from source teams changing a field's schema or meaning: classify each surprise as structural (column dropped, renamed, retyped) or semantic (same column, new meaning: a new status code, pence to pounds, a time zone switch, re-keyed ids), land raw untouched, diff the schema at ingest, catch semantic drift with enum, range and match-rate checks, quarantine failing rows and replay from raw after the fix, then give the producer a CI compatibility check and a named contact. |

### Techdocs

Documentation as something that can be tested: tutorials run from a clean machine, samples executed in CI, drift caught when the product changes, and URLs that keep working.

| Skill | What it does |
| --- | --- |
| [`accessibility-conformance-report`](plugins/techdocs/skills/accessibility-conformance-report/SKILL.md) | Turn accessibility audit results into an Accessibility Conformance Report (a completed VPAT) and a public accessibility statement that buyers and disabled users can rely on. Fixes the product version, platforms, standard edition and test method first; rates every criterion Supports, Partially Supports, Does Not Support or Not Applicable with evidence, the known gap and a remediation target; refuses a full-conformance claim without a complete audit; publishes a feedback route with a response time; and re-issues the report each release. Use whenever someone says "a customer wants our VPAT", "the RFP asks for an ACR", "write our accessibility statement", "fill in the 508 or EN 301 549 report" or "our VPAT is two versions old". |
| [`cli-reference`](plugins/techdocs/skills/cli-reference/SKILL.md) | Document a command-line tool so --help, the man page, the web reference and shell completions all come from one source, the parser definition. Lays help out as a usage line, a one-line purpose, flags grouped by task with defaults and environment variables, three real examples and exit codes; states which flags conflict, require each other or override; generates the man page, reference and completions in the build instead of copying them; and snapshot-tests --help so an interface change shows up in review. Use whenever someone says "document this command-line tool", "our --help and the README disagree", "generate a man page for our CLI", "add shell completions" or "what exit codes should we document". |
| [`code-sample-testing`](plugins/techdocs/skills/code-sample-testing/SKILL.md) | Make every code sample in the documentation executable. Samples live as real source files and the page includes them by region marker, never by pasting; CI compiles and runs each one against the released package and against main, asserts its output rather than its exit code, and fails on a pasted runnable block; a sample that genuinely cannot run is labelled as pseudo-code; and each failure is routed to the sample's owner. Use whenever someone says "our docs examples are broken", "the snippets in the SDK reference don't compile", "how do we test the code in our docs" or "users copy the example and it errors". |
| [`docs-drift-detection`](plugins/techdocs/skills/docs-drift-detection/SKILL.md) | Find which documentation pages a code change makes false, before it merges. Build a reviewed map, kept in the repository, from code paths, config keys, CLI flags, environment variables and endpoints to the pages that name them; have CI list the affected pages on every pull request touching mapped code, and fail it when a removed identifier is still documented; give pages that map to no code a review date or delete them; track the share of mapped-code changes that also touched docs. Use whenever someone says "our docs keep going stale after code changes", "which pages does this PR affect", "nobody remembers to update the docs" or "the docs still mention a flag we deleted". |
| [`docs-search-vocabulary`](plugins/techdocs/skills/docs-search-vocabulary/SKILL.md) | Fix documentation findability by mining the docs search log for the gap between the reader's words and the docs' words. Export zero-result queries and sessions reformulated twice without a click, cluster them by intent, and decide each cluster: add a search synonym, rename the heading to the reader's term, add an alias redirect, or write the missing page; put the reader's term in the title and the internal term in the body; measure the zero-result rate before and after. Use whenever someone says "people can't find X in our docs", "docs search is useless", "what are users searching for that we don't have" or "we have an export of search analytics, what now". |
| [`docs-url-permanence`](plugins/techdocs/skills/docs-url-permanence/SKILL.md) | Move, rename or restructure a documentation site without breaking inbound links. Before anything moves, harvest the URLs that matter from search console exports, access logs, links inside the product and READMEs; write the old-to-new redirect map first and test it as a table; give each page one permanent single-hop redirect to its true successor, never the homepage; keep every redirect indefinitely; and after launch replay the old URL list until it returns zero 404s. Use whenever someone says "we're reorganising the docs", "migrating the docs to a new site generator", "moving the docs to a new domain" or "our old Stack Overflow links are all 404". |
| [`error-catalogue`](plugins/techdocs/skills/error-catalogue/SKILL.md) | Give every error a product shows a stable code and its own documentation page, and keep the two in step. The code is a namespaced, immutable contract that is never reused; each page states the cause, how to confirm it, the fix and whether retrying helps; the runtime message links to its page; CI fails on a code thrown in source with no page or a page with no code; and a new code lands in the same pull request as its throw site. Use whenever someone says "document our error codes", "users paste error messages into support and nobody knows what they mean", "build an error reference like rustc --explain" or "two services use the same error number for different things". |
| [`openapi-diff-gate`](plugins/techdocs/skills/openapi-diff-gate/SKILL.md) | Catch breaking API changes from the OpenAPI document itself before they merge. Diff the last released spec against the pull request's with a structural differ such as oasdiff, never a text diff; classify each change by direction, because request and response compatibility invert — narrowing what a request accepts breaks callers, and so does widening what a response returns; fail CI on a breaking diff unless the pull request carries a versioning label and a migration entry; and seed the API changelog from the diff. Use whenever someone says "diff our spec against the last release", "add a breaking-change check for the OpenAPI file", "did this PR break any API clients" or "write the API changelog from the spec". |
| [`screenshot-rot`](plugins/techdocs/skills/screenshot-rot/SKILL.md) | Stop documentation screenshots and diagrams going stale. Inventory every image in the docs and decide per image whether text, a code block or a table would serve instead; replace the hand-taken screenshots that remain with scripted captures (browser automation, seeded demo data, fixed viewport, clock, locale and fonts) regenerated in CI, where a changed image opens a pull request for review; keep diagrams as text sources beside the page; and write alt text that states the image's point. Use whenever someone says "our screenshots are out of date", "the docs still show the old UI", "who re-shoots the images after a redesign" or "can we generate docs screenshots automatically". |
| [`terminology-lock`](plugins/techdocs/skills/terminology-lock/SKILL.md) | Make one word mean one thing across the product UI, docs, API and support. Inventory the competing terms and where each appears, choose the canonical one, and keep a glossary in the repository giving each term's definition, its banned synonyms and the reason for each ban; generate Vale substitution rules and a UI string check from that one glossary, so docs and interface strings are linted by the same list; run any rename as one tracked change sweeping code, UI, docs, translations and the search synonym list. Use whenever someone says "we call it three different things", "is it a workspace or a project", "lint our docs for product terms" or "we're renaming this feature everywhere". |
| [`tutorial-clean-room`](plugins/techdocs/skills/tutorial-clean-room/SKILL.md) | Prove a tutorial, quickstart or getting-started guide works for a stranger before it ships: run it in a brand-new container or VM with no cached credentials, dotfiles or warm caches, stopwatch running, executing only what the page literally says; log every stumble as a defect with the minutes it cost; state a time-to-first-result target on the page; then watch one outsider follow it with no questions allowed, and ship only after a zero-stumble run. Use whenever someone says "write our getting-started guide", "verify the quickstart still works", "new users keep getting stuck on install" or "how long does it really take to get going with our SDK". |

### Assurance

Evidence that software does what it should and that the organisation can show it: tests that find their own blind spots, load and replay before a change ships, and privacy, licence and audit work run as procedure rather than legal advice.

| Skill | What it does |
| --- | --- |
| [`audit-trail-design`](plugins/assurance/skills/audit-trail-design/SKILL.md) | Design the audit log for user and admin actions: start from the investigation questions (who did what to which record, when, from where, allowed or denied), log denials as well as successes, write state changes in the same transaction as the change, keep the trail in an append-only store separate from application logs with tamper evidence from a hash chain or write-once storage, keep secrets and full personal data out of entries, fix retention and reviewer access, and accept it only when a staged incident can be reconstructed from the trail alone. |
| [`control-evidence`](plugins/assurance/skills/control-evidence/SKILL.md) | Collect SOC 2 or ISO 27001 audit evidence without a screenshot scramble: map each control to one system-generated artefact, with an API export preferred over a screenshot; define every population and the sampling period before the auditor asks, reconciled against an independent source; automate dated collection on the audit cadence; keep a tracker of request, owner and due date; and test each control yourself first, filing exceptions with remediation inside the period. |
| [`dpia`](plugins/assurance/skills/dpia/SKILL.md) | Run a data protection impact assessment as a dated, versioned procedure rather than a form filled in after launch: screen against a written trigger list first and record the answer either way, describe every data flow, test necessity and proportionality field by field, list risks to the people whose data it is rather than to the company, give each mitigation a named owner, have a named person with authority accept the residual risk, and re-run when the design changes. Procedure, not legal advice. |
| [`fuzz-harness`](plugins/assurance/skills/fuzz-harness/SKILL.md) | Put a coverage-guided fuzzer on your own parsing and decoding code: one small harness per entry point that takes bytes and must not crash, hang or exhaust memory, a seed corpus from real files and past bug reports, builds under AddressSanitizer and UndefinedBehaviorSanitizer, every crash minimised, deduplicated by stack and committed as a regression input, and a short fuzz run on each pull request with a long one on a schedule. Covers libFuzzer, AFL++, cargo-fuzz, Go native fuzzing, Atheris and Jazzer. |
| [`licence-compliance`](plugins/assurance/skills/licence-compliance/SKILL.md) | Audit the open-source licence obligations of what you ship: inventory every component from lockfiles and built artefacts, with transitive packages, vendored code, fonts and base images included; classify each artefact by how it reaches people — hosted, sent to browsers, shipped binary or image, published library — since the same licence binds differently in each; enforce an allowlist in CI where an unknown or missing licence blocks; generate the NOTICE or third-party attribution from the inventory; record exceptions pinned to a version. Procedure, not legal advice. |
| [`load-testing`](plugins/assurance/skills/load-testing/SKILL.md) | Run a load test that answers one stated question and cannot pass by accident: fix the question and SLO-based pass thresholds before the run, take the workload mix and parameters from production logs, drive an open arrival-rate model, not fixed virtual users, so coordinated omission cannot hide stalls, warm up, ramp and hold on production-shaped infrastructure and data, prove the generator hit the offered rate, correlate with server telemetry, and report percentiles and errors, never averages. |
| [`mutation-testing`](plugins/assurance/skills/mutation-testing/SKILL.md) | Measure whether the tests fail when the code is wrong, not merely whether they run it: run a mutation tool on only the lines a pull request changed, triage every surviving mutant as an equivalent mutant, a missing assertion or an untested branch, kill the worst survivors by writing the test that notices, and ratchet on changed code instead of chasing a global mutation score. Covers diff-scoped runs in Stryker, PIT, mutmut, cargo-mutants and Infection. |
| [`property-based-testing`](plugins/assurance/skills/property-based-testing/SKILL.md) | Replace hand-picked example lists with properties a library checks across generated inputs: choose the property class first (round trip, idempotence, oracle comparison, an invariant after any sequence of operations, never crashes), build generators that construct valid domain objects instead of filtering, pin every shrunk counterexample as a permanent example test, run a small seeded budget on pull requests and a large one nightly, and test stateful APIs against a simple model. |
| [`risk-acceptance-register`](plugins/assurance/skills/risk-acceptance-register/SKILL.md) | Record knowingly accepted risk so the acceptance expires instead of becoming permanent: each entry states the risk, the compensating control and how it is verified, an accountable owner above the engineer who proposed it, and an expiry date; every tool-level suppression points to an entry; owners are reminded 30 days before expiry; an expired entry counts as an open finding; and the register is the one place auditors and security review read. |
| [`test-order-bisect`](plugins/assurance/skills/test-order-bisect/SKILL.md) | Find the polluter behind a test that passes alone and fails in the full suite, then remove the leak rather than the symptom: replay the failing order from its recorded random seed, delta-debug the tests that ran before the victim by halving until one polluter and one victim remain, name the shared state it leaked (a global, env var, temp file, port, database row, clock or patch left in place), isolate that state instead of pinning the order, and add a randomised-order CI job so it cannot return. |
| [`traffic-replay-diff`](plugins/assurance/skills/traffic-replay-diff/SKILL.md) | Prove a rewrite, port or migrated service answers the same as the old one by replaying captured production requests offline against both and diffing responses: capture sanitised read traffic, start both from one data snapshot with identical stubs, replay old against old first to measure noise, normalise timestamps, ids and unordered collections, bucket every diff by cause, and close each bucket as a bug or a signed-off intentional change. Done at zero unexplained buckets across a full weekly cycle. |

### Client-apps

Code that runs on someone else's device: field performance and memory in the browser, version skew and service workers, Safari-only bugs, and on phones the crashes, hangs, slow starts, battery drain, bad networks and migrations that only show up in the wild.

| Skill | What it does |
| --- | --- |
| [`anr-watchdog-triage`](plugins/client-apps/skills/anr-watchdog-triage/SKILL.md) | Diagnose hangs and OS kills that never throw: Android ANRs, iOS watchdog terminations and hangs, and memory-pressure kills such as jetsam. Map each kill to its cause first — an ANR trace whose main thread is blocked on a lock, disk I/O or a binder call; a watchdog kill because launch or resume ran out of time; a memory kill driven by peak footprint, not necessarily a leak — then read the main-thread stack, move blocking work off the main thread, and judge memory from a footprint timeline, not one heap snapshot. |
| [`app-size-budget`](plugins/client-apps/skills/app-size-budget/SKILL.md) | Cut a native app's download and install size and keep it cut. Start from the size the store reports per device, not the IPA or AAB on disk; decompose it with an App Thinning size report or bundletool and a link map; cut in a fixed order — duplicate and unused assets, extra architectures, image formats, on-demand resources or dynamic feature modules, dead code with R8 and dead stripping, then SDKs — measuring each cut; and gate the size delta on every pull request so it cannot creep back. |
| [`async-ui-races`](plugins/client-apps/skills/async-ui-races/SKILL.md) | Remove race conditions from client code that talks to a server: classify the race first - out-of-order responses, double submit, optimistic updates diverging from the server, state set after unmount - then fix each with its own tool: request keys or AbortController so the latest wins, a disabled control plus an idempotency key for submits, rollback reconciled with the server for optimistic updates, cancellation in cleanup; prove it with a test that releases responses in reverse order, not one that relies on timing. |
| [`battery-drain-diagnosis`](plugins/client-apps/skills/battery-drain-diagnosis/SKILL.md) | Find what drains the battery and heats the phone in a native iOS or Android app, and prove the fix. Split foreground from background drain first, trace a scripted scenario on a physical device with batterystats, the Android Studio Power Profiler, Xcode's energy gauge and MetricKit, and check suspects in order: wake locks and background work, location accuracy and frequency, polling instead of batched or pushed network calls, and animations, timers and sensors left running. Re-run the identical scenario to show the delta. |
| [`bfcache-eligibility`](plugins/client-apps/skills/bfcache-eligibility/SKILL.md) | Make back and forward navigations restore instantly from the browser's back/forward cache: run the DevTools back/forward cache test and read its not-restored reasons, clear blockers in the order they usually occur (unload handlers moved to pagehide, Cache-Control: no-store on pages that do not need it, open WebSocket, BroadcastChannel and IndexedDB connections closed on pagehide, a window.opener reference), refresh stale state on pageshow, and measure the restore rate in the field with the notRestoredReasons API. |
| [`browser-memory-leak-hunt`](plugins/client-apps/skills/browser-memory-leak-hunt/SKILL.md) | Find and fix a memory leak in a long-lived browser page: confirm the growth is JavaScript heap or DOM rather than images or GPU, run the three-snapshot technique (warm up, snapshot, repeat the action ten times, snapshot, repeat, snapshot) keeping only objects allocated between the first two snapshots that survive into the third, read retainer chains for detached DOM nodes, listeners, closures, timers and observers, and confirm the fix as a flat sawtooth after forced garbage collection. |
| [`crash-triage`](plugins/client-apps/skills/crash-triage/SKILL.md) | Prioritise native iOS and Android crashes so each release fixes the ones hurting most people. Verify symbolication first — dSYM UUIDs, the R8 mapping.txt, native symbols — since an unsymbolicated crash is a pipeline bug before an app bug; then group by signature, rank by affected users not events, split each top signature by app version, OS version and device, fix the top one per release, and prove it on the new version's cohort, not the blended rate. |
| [`csp-report-only-rollout`](plugins/client-apps/skills/csp-report-only-rollout/SKILL.md) | Introduce a Content-Security-Policy without breaking the site: start with Content-Security-Policy-Report-Only and a hardened report endpoint, read about two weeks of violation reports grouped by directive, blocked source and page, move scripts to per-response nonces or hashes with strict-dynamic rather than a host allow-list, enforce path by path starting with the least risky, and keep a stricter report-only policy running beside the enforced one. |
| [`datetime-bug-hunt`](plugins/client-apps/skills/datetime-bug-hunt/SKILL.md) | Fix off-by-one-day, wrong-hour and daylight-saving bugs in apps and their APIs. Classify each temporal value as an instant, a local wall-clock time or a calendar date; store instants in UTC, wall-clock times with an IANA zone name rather than an offset, and dates as dates, never midnight timestamps; expand recurrence in the event's own zone; then prove the fix against one fixed hostile set: DST gap and overlap, UTC+14 and UTC-12, a leap day, and a device zone unlike the user's. |
| [`deep-link-routing`](plugins/client-apps/skills/deep-link-routing/SKILL.md) | Make https links open the right screen in a native app: iOS universal links, Android App Links and deferred links for people without the app. Host apple-app-site-association and assetlinks.json at their exact well-known paths with no redirect and a JSON content type, check team and bundle IDs and the Play signing fingerprint, verify on a clean install with platform tools, drive app, web and both files from one route table, and treat link parameters as untrusted input. |
| [`deploy-version-skew`](plugins/client-apps/skills/deploy-version-skew/SKILL.md) | Stop tabs opened on an earlier release breaking when a new one ships: keep earlier releases' hashed assets on the origin and CDN rather than deleting them, upload assets before the HTML that names them, return a real 404, not the SPA fallback, for a missing chunk, stamp the live build id on API responses and compare it with the client's, retry a failed chunk import with one guarded reload, refresh at the next navigation, not mid-form, and keep API changes compatible across two client versions. |
| [`hydration-mismatch-hunt`](plugins/client-apps/skills/hydration-mismatch-hunt/SKILL.md) | Find why server-rendered HTML and the first client render disagree, and fix the cause rather than the warning: diff the raw server HTML from curl against the parsed DOM and the first client render, never the final DOM, then check the five usual sources (time, randomness or locale read during render; typeof window branches; invalid nesting the HTML parser repairs; nodes injected by browser extensions; per-request data the client never receives) and move the value into serialised props or an effect. |
| [`lie-fi-resilience`](plugins/client-apps/skills/lie-fi-resilience/SKILL.md) | Make a mobile or web client survive bad networks, not only no network: reproduce under conditioning at 3G, at 100% loss and on a link that is up but carries no data (captive portal, lie-fi), give every request a deadline, a capped retry budget with jittered backoff and an idempotency key, derive the offline banner from failed requests instead of the reachability flag, and queue writes durably so they survive a killed process. |
| [`locale-edge-sweep`](plugins/client-apps/skills/locale-edge-sweep/SKILL.md) | Find internationalisation defects by sweeping every screen through a fixed hostile locale set, not whichever language is next on the roadmap. Externalise strings as ICU plural and select messages, then sweep: a pseudo-locale with about 40 percent expansion, Turkish dotless i in case mapping, right-to-left with logical properties, German compound words, Thai and Japanese without spaces, collation for sort and search, name and address formats, and numbers, currency and dates via the platform formatter; then gate it in CI. |
| [`mobile-startup-and-jank`](plugins/client-apps/skills/mobile-startup-and-jank/SKILL.md) | Make a native app open fast and scroll smoothly. Measure cold start on a low-end physical device in a release build with Macrobenchmark, Android vitals, XCTest launch metrics, MetricKit and Instruments; split launch into pre-main or process start, app initialisation and first frame; list every SDK initialised on the launch path with its milliseconds and defer each one; judge scrolling by p95 frame time and hitch rate, not average frames per second; ship a Baseline Profile on Android. |
| [`on-device-migration-safety`](plugins/client-apps/skills/on-device-migration-safety/SKILL.md) | Ship a change to an app's on-device database — Core Data, SwiftData, Room, SQLite — when the store cannot roll it back and every phone migrates alone. Enumerate every app version still in the field from analytics, keep a fixture database per schema version and run migrations from every one in CI, not just the previous release, migrate inside a transaction after a backup copy, and ship a failure path that restores and degrades instead of bricking launch. Steps are forward-only; old fields stay one release. |
| [`push-notification-delivery`](plugins/client-apps/skills/push-notification-delivery/SKILL.md) | Find why a push notification did not arrive or did not show by walking the delivery chain in order: permission, token registration and refresh, the APNs or FCM request (push type, priority, collapse key, expiry), the provider's response with dead tokens deleted on 410 or UNREGISTERED, then on-device suppression — Doze, vendor battery killers, channels, Focus. Fix opt-in by asking after a moment of value, never at first launch. |
| [`pwa-service-worker`](plugins/client-apps/skills/pwa-service-worker/SKILL.md) | Make a web app work offline and install cleanly, with a way out when its service worker goes wrong: ship the rescue first, a no-op worker at the same URL that clears caches and unregisters itself; pick a strategy per resource class (precache the hashed shell, stale-while-revalidate for tolerant reads, network-only for writes); name caches by build and delete old ones on activate; show a waiting worker as an update prompt, not a blind skipWaiting; queue offline writes with idempotency keys. |
| [`text-input-edge-cases`](plugins/client-apps/skills/text-input-edge-cases/SKILL.md) | Harden text fields against what people really type, paste and autofill: count graphemes with Intl.Segmenter rather than .length, ignore Enter during IME composition, normalise to NFC before comparing or storing, trim once at the storage boundary, never reject a name with a pattern, keep client and server limits in one unit, and test every field against a fixed corpus - ZWJ emoji, combining marks, right-to-left text, 4-byte characters, pasted control characters, autofill. |
| [`web-app-seo`](plugins/client-apps/skills/web-app-seo/SKILL.md) | Make a JavaScript-rendered site indexable: fetch each template without JavaScript first and compare it with the rendered HTML from Search Console's URL Inspection, then fix in order - rendering mode, status codes and soft 404s, canonicals, truthful sitemap lastmod, reciprocal hreflang, valid structured data - with a crawl policy for faceted URLs and an indexing watch after every migration. |
| [`web-vitals-triage`](plugins/client-apps/skills/web-vitals-triage/SKILL.md) | Find why a Core Web Vital is poor for real users and fix the part that dominates: refuse lab scores until p75 field data is split by device and URL group, pull attribution (the LCP element and its four sub-parts, the slow interaction's target with its input delay, processing and presentation phases, the node that shifted), change only the dominant sub-part, and judge the fix on the 28-day field window rather than a Lighthouse re-run. |
| [`webkit-only-bug-triage`](plugins/client-apps/skills/webkit-only-bug-triage/SKILL.md) | Triage a bug that only happens in Safari or on iPhone and iPad: reproduce it in real WebKit (a device, the iOS Simulator or Playwright's WebKit build) with Web Inspector attached before reading code, then check the usual causes in order: 100vh against dvh and the safe area, inputs under 16px zooming on focus, sticky and overflow clipping, date inputs and date parsing, ITP's seven-day cap on script-writable storage, IndexedDB eviction, and an API the user's iOS version lacks. Fix with feature queries, not user-agent checks. |

### Product

Product management and go-to-market run on evidence: interviews about what people actually switched from, cheap tests of demand before a build, pricing changed without a revolt, metrics diagnosed before anyone reacts, and churn, deals and support load read for their causes.

| Skill | What it does |
| --- | --- |
| [`activation-analysis`](plugins/product/skills/activation-analysis/SKILL.md) | Define activation from your own data and find where new users stall: cohorts by sign-up week, candidate early actions scored against week-8 retention, the winning event and threshold proven with a randomised nudge test, not declared from a correlation, each drop-off checked for tracking artefacts first, one testable hypothesis per drop-off, and a retention curve that must flatten before anyone calls the product retained. |
| [`churn-analysis`](plugins/product/skills/churn-analysis/SKILL.md) | Explain why customers cancel or shrink: split logo churn from revenue churn and voluntary from involuntary before anything else, cohort by acquisition month and segment, code reasons from cancellation notes, tickets and the prior 90 days of usage rather than the cancellation dropdown, and back-test any health score on known churners, discarding it if it warns less than 30 days before the customer decided. |
| [`competitor-signal-watch`](plugins/product/skills/competitor-signal-watch/SKILL.md) | Infer where a competitor is heading from the traces it leaves in public: job postings counted by team, changelog and pricing pages archived and diffed over time, review-site themes, partner and integration pages. Every inference carries its source, the date it was captured and a confidence level; the output is what they appear to be betting on plus three watch triggers that would change what we do, reviewed every 90 days with stale claims deleted. Public sources only. |
| [`concierge-mvp`](plugins/product/skills/concierge-mvp/SKILL.md) | Deliver a product's outcome by hand to the first five to ten customers before automating anything, and let what happens decide what gets built. Log every manual step with the time it took and the customer's reaction, so the log becomes the spec; automate only a step that has run ten or more times and costs over fifteen minutes; track the cost of serving each customer by hand; stop when customers do not come back unprompted, because automating a service nobody repeats only makes the failure cheaper to run. |
| [`contact-reduction-review`](plugins/product/skills/contact-reduction-review/SKILL.md) | Treat support tickets as a defect list and cut the contacts at their cause: tag a month of tickets by contact driver, the customer's reason for getting in touch, capped at about twenty tags; cost each driver as volume times handle time; give each of the top ten one fix: product change, copy change, help article, automation, or accept it; track contacts per active customer rather than raw volume; and send a monthly top five to product, each with an owner and a date. |
| [`design-partner-program`](plugins/product/skills/design-partner-program/SKILL.md) | Run a small cohort of design partners or a customer advisory board that shapes the product without capturing it. Choose five to eight partners for fit to one segment, not logo size; write the give-get (a weekly 30-minute session, real data, a reference at the end, for early access and visible influence); keep a fixed cadence and a shared decision log of what changed because of them; remove a partner after two missed sessions; at the end convert, keep as a reference, or release each one, never leaving them drifting. |
| [`discount-discipline`](plugins/product/skills/discount-discipline/SKILL.md) | Put deal-desk rules around discounting so margin stops leaking one deal at a time: audit the last 50 closed deals for realised against list price by rep, segment and closeness to quarter end before writing any rule, then set a discount ladder with a named approver per level, a give-get rule so every point of discount buys something (longer term, prepayment, volume, a logo or case study), a first-year cap with the renewal price written into the contract, and no anonymous special-pricing requests. |
| [`dunning-recovery`](plugins/product/skills/dunning-recovery/SKILL.md) | Recover failed subscription payments before they become churn: measure the involuntary share of churn first, retry by decline code (soft declines retried on a spaced schedule, hard declines sent to the customer), switch on a card account updater, send pre-expiry notices, run a three-email sequence over 14 days with an in-app banner, hold a grace period before access changes, and report recovered MRR per stage. |
| [`escalated-account-recovery`](plugins/product/skills/escalated-account-recovery/SKILL.md) | Recover a key customer account that is angry and threatening to leave: one named owner who acknowledges within 48 hours, the complaint written back in the customer's own words and agreed before any fix is proposed, a written recovery plan with dated commitments and an executive sponsor on each side, a weekly cadence until agreed exit criteria are met, and root causes fed back to product and support. |
| [`fake-door-test`](plugins/product/skills/fake-door-test/SKILL.md) | Measure demand for an unbuilt feature or product with a fake door, smoke test or landing page, and decide from a rule written before launch. Set the pass threshold and sample size from what the build is worth; count only a costly action (a waitlist sign-up with a work email, a refundable deposit, a booked call), never a click; tell responders on the follow-up page that it is not live, and contact every one within 48 hours. A pass leads to serving those responders by hand, not to a build. |
| [`feature-sunset`](plugins/product/skills/feature-sunset/SKILL.md) | Retire a feature, plan, integration or whole product without stranding the customers who depend on it: pull usage by account before deciding, classify every account as unaffected, replaceable or blocked, set the end date from the slowest-migrating segment rather than engineering convenience, then run the sequence (announce, close to new sign-ups, in-product warning, brown-out windows, read-only, remove) with a gate at each stage, and call it done only when blocked accounts reach zero. |
| [`jobs-timeline-interview`](plugins/product/skills/jobs-timeline-interview/SKILL.md) | Reconstruct why recent buyers or switchers chose your product, from first thought to first use, so positioning and roadmap rest on what happened rather than on opinions. Interview only people who bought or switched in the last 90 days; walk the timeline (first thought, passive looking, active looking, deciding, first use) asking for the day, the place and who was there; code the four forces (push, pull, anxiety, habit), each with a verbatim quote, into a force table across six or more interviews. |
| [`metric-anomaly-triage`](plugins/product/skills/metric-anomaly-triage/SKILL.md) | Decide whether a sudden move in a product metric is real before anyone explains it: a fixed elimination order of tracking or tag change, pipeline lag or late data, definition or filter change, bot or internal traffic, mix shift, and seasonality or calendar, each ruled out by one named query, and only then a real change in user behaviour located by segment and confirmed from a second source. |
| [`metric-gaming-audit`](plugins/product/skills/metric-gaming-audit/SKILL.md) | Stress-test product KPIs and key results for the cheap ways to hit them while harming customers: write the three cheapest moves that raise each metric while damaging the customer, pair each with a counter-metric and a data check that would expose it, require every key result to carry a baseline, written definition, source table and owner, and turn anything not measurable today into an instrumentation task before it counts. |
| [`poc-plan`](plugins/product/skills/poc-plan/SKILL.md) | Scope and run a customer proof of concept or pilot as the vendor so it ends in a decision rather than drifting: success criteria taken from the buyer's own problem, measurable and signed by the buyer before any environment is set up; a fixed window of two to four weeks with a named customer sponsor and a decision date; a mid-point checkpoint that can end it early; and an exit review that states results against each criterion and the agreed commercial next step. No criteria means no POC. |
| [`price-change-rollout`](plugins/product/skills/price-change-rollout/SKILL.md) | Raise prices or move existing customers onto a new price or plan without a churn spike: model revenue by cohort first (plan, tenure, size, discount, renewal date), choose grandfather-with-sunset or migrate-at-renewal per cohort, give notice of at least the renewal window (60 to 90 days for annual B2B contracts) and whatever contracts, consumer law and app stores require, have account owners tell top accounts before any email goes out, and set a rollback tripwire on churn and downgrade rate against baseline with a dated review. |
| [`pricing-research`](plugins/product/skills/pricing-research/SKILL.md) | Find out what customers will pay before a price is set: pick the method by sample size (under about 30 respondents, value interviews anchored on what the current alternative costs them; above it, Van Westendorp for the acceptable range plus Gabor-Granger for demand at each price), ask the buyer who signs separately from the user who benefits, cross-check against the economic value the product creates and the share of it you can capture, and hand back a price range with its stated risk rather than one number. |
| [`request-triage`](plugins/product/skills/request-triage/SKILL.md) | Handle feature requests from sales and customers so real deal-blockers surface and every requester hears back. Record the job and the customer, never the feature wording; ask "what will you do if we never build it, and would you sign without it?" and count a blocker only with the customer's contingency in writing; merge duplicates into one record with customer count and ARR; give one of five dispositions (now, planned, exploring, declined, redirected-to-existing) within five working days with a reason the requester can repeat. |
| [`rfp-response`](plugins/product/skills/rfp-response/SKILL.md) | Respond to an RFP, RFI, tender or customer security questionnaire as the vendor: score bid or no-bid within 24 hours before anyone writes a word, build the compliance matrix from every requirement before the narrative, answer from an approved-answer library where each answer has an owner and a review date, mark roadmap items as planned with a date range rather than claiming them as capability, and clear legal and security sign-off on a pre-submit checklist. |
| [`roadmap-disruption-triage`](plugins/product/skills/roadmap-disruption-triage/SKILL.md) | Decide what to do when a key customer, an executive or a competitor's move tries to force something onto a committed roadmap: write the trade-off ledger before answering (the item moving in, the named items slipping, their new dates, who must be told), sort the demand into promise, proof or pressure, test claimed revenue against a signed contingency rather than a forecast, offer three costed options (do it, a smaller version, do not), and log the decision with a re-plan trigger. |
| [`spec-premortem`](plugins/product/skills/spec-premortem/SKILL.md) | Attack a spec, PRD, launch plan or big bet before committing to it, then score the forecast afterwards. Assume it failed six months out; have each reviewer write reasons alone before any discussion; sort them into real risks, paper tigers and unspoken elephants; turn each real risk into a tripwire with a metric, threshold, date and owner; record three numeric predictions and score them at day 30 and day 90 so the team learns how well it forecasts. |
| [`win-loss-review`](plugins/product/skills/win-loss-review/SKILL.md) | Find out why deals are won, lost or stall, from the buyers rather than the CRM: separate no decision, often the biggest bucket, from lost to a competitor; sample every closed deal in the period rather than the ones reps pick; have someone outside the sales team interview buyers within 30 days of close; code answers against the buyer's own decision criteria; report a competitor-specific pattern only once five or more deals show it. |

### Platform

Cloud and platform engineering for the situations that recur and hurt: an overloaded Kubernetes control plane, network policy and storage, Terraform estates that grew by hand, cloud networks and identity, database upgrades and replicas, the edge, and commitments sized to real usage.

| Skill | What it does |
| --- | --- |
| [`apiserver-pressure`](plugins/platform/skills/apiserver-pressure/SKILL.md) | Find out why the Kubernetes API server or etcd is slow, throttling or near its limits, and fix the client before raising any limit: slice request rate and latency by verb and resource, name the top caller from the audit log's user agent, count stored objects per resource, read etcd database size against its quota, then fix the offending controller's selectors, caching and reconnect behaviour, and only last give it its own API Priority and Fairness flow. |
| [`bootstrap-dependency-audit`](plugins/platform/skills/bootstrap-dependency-audit/SKILL.md) | Hostile audit of the tooling needed to recover production, hunting for cycles: could you still sign in, read secrets, pull images, deploy, run Terraform and change DNS if CI, the registry, the identity provider, the secrets store, DNS or the state backend is down? Write the recovery path's dependencies as an edge list, find the loops (a registry on the cluster it repairs, an IdP behind the VPN that needs it, break-glass passwords in an SSO-locked vault), name a break-glass path per loop, then dry-run each with that dependency blocked. |
| [`brownfield-iac-adoption`](plugins/platform/skills/brownfield-iac-adoption/SKILL.md) | Bring a hand-built, click-ops estate under Terraform or OpenTofu, or measure how much of it is still unmanaged. Enumerate from the provider's inventory API (AWS Resource Explorer or Config, Cloud Asset Inventory, Azure Resource Graph) rather than memory, diff it against every state for the unmanaged set, exclude what another tool rightly owns, import in dependency order with generated configuration then rewrite it into modules, hold a zero-diff plan gate per batch, and schedule a coverage report that makes unmanaged resources a number. |
| [`cdn-configuration`](plugins/platform/skills/cdn-configuration/SKILL.md) | Tune CDN and edge caching for origin offload and safe purges: audit the origin's Cache-Control and Vary before any edge rule, normalise the cache key (strip tracking parameters, allowlist cookies), make fingerprinted assets immutable and HTML short-lived with stale-while-revalidate, shield the origin, purge by surrogate key rather than wildcard, keep authenticated responses out of shared cache, and report origin offload, not hit ratio alone. |
| [`commitment-planning`](plugins/platform/skills/commitment-planning/SKILL.md) | Decide how much Savings Plan, reserved instance or committed-use discount to buy, and when, so a discount never becomes a floor paid for idle capacity: rightsize first, measure the trailing 90-day hourly floor of eligible usage rather than the average, convert it to a commitment at the discounted rate net of existing coverage, prefer flexible compute instruments, ladder small purchases monthly so expiries stagger, price the exit of every term against the roadmap, and review utilisation and coverage weekly. |
| [`connection-exhaustion-hunt`](plugins/platform/skills/connection-exhaustion-hunt/SKILL.md) | Hunt intermittent timeouts caused by exhausting the network path — NAT or SNAT ports, local ephemeral ports, a full conntrack table, or 5-second DNS stalls from ndots:5 search expansion or the conntrack race. Read counters before changing anything, compute connections per destination IP and port against that path's ceiling, then fix in order: client keepalive and pooling, a private endpoint or more NAT addresses, NodeLocal DNSCache or fully qualified names, and last a bigger conntrack table. |
| [`data-transfer-forensics`](plugins/platform/skills/data-transfer-forensics/SKILL.md) | Find which workloads generate the bytes behind a data-transfer line on the cloud bill — cross-AZ, NAT gateway processing, internet egress, inter-region — and fix the costliest. Enable VPC flow logs with the extended fields, aggregate bytes by source, destination, zone pair, path and port in a query engine, join addresses to the pod or instance that owned them at the time, price each flow at the rate the bill implies, reconcile, and rank by dollars rather than bytes. Typical fixes: same-zone routing, gateway endpoints for object storage, a NAT per zone, compression. |
| [`db-major-upgrade`](plugins/platform/skills/db-major-upgrade/SKILL.md) | Upgrade a PostgreSQL or MySQL major version, managed or self-hosted: scan extensions, removed features and authentication plugins first; restore a production snapshot and rehearse the whole upgrade with timings; choose in-place pg_upgrade, blue/green or logical replication by the downtime you can tolerate; ANALYZE straight after; compare plans for the top queries by total time; keep the old cluster until a full business cycle passes. |
| [`db-replication`](plugins/platform/skills/db-replication/SKILL.md) | Operate PostgreSQL and MySQL replicas, logical replication and failover, including a replication slot filling the primary's disk: set a lag budget per read path and send read-your-writes reads to the primary; alert on lag in bytes and seconds and on slot-retained WAL well before the disk fills; write a promotion runbook that fences the old primary first; test failover under load. |
| [`dns-operations`](plugins/platform/skills/dns-operations/SKILL.md) | Run DNS as code and audit it, so a forgotten record cannot be taken over and a key rollover cannot take the domain offline. Put every zone under Terraform, octoDNS or DNSControl with a reviewed plan and a drift check, harden the registrar (domain locks, MFA, a recovery email off the domain), sweep CNAME, alias, NS, MX and A records on a schedule by resolving each target and proving the resource is still yours, roll DNSSEC keys in order with a TTL wait at every step, and write down split-horizon views. |
| [`ephemeral-environments`](plugins/platform/skills/ephemeral-environments/SKILL.md) | Build per-pull-request preview environments that are cheap, safe and gone when the pull request is: isolate by data sensitivity and never in the production account, label every resource with owner, pull request and expiry and refuse anything unlabelled, seed synthetic data rather than a production copy, keep production secrets from unreviewed and fork code, tear down on close and run a scheduled reaper for whatever teardown missed, and cap each environment with a quota and a budget alert. |
| [`gateway-api-migration`](plugins/platform/skills/gateway-api-migration/SKILL.md) | Move HTTP routing off an Ingress controller, such as the retired ingress-nginx or a setup leaning on annotations and snippets, onto Gateway API or another controller without a flag day. Inventory every annotation, snippet and controller-wide default, map each to a Gateway API field or mark it unportable, run the new controller side by side on its own load-balancer address, shift traffic with weighted DNS rather than swapping the class in place, diff status codes and latency per route, then retire the old one. |
| [`iac-version-upgrade`](plugins/platform/skills/iac-version-upgrade/SKILL.md) | Upgrade Terraform or OpenTofu core, or move a provider across a major version, without an apply nobody meant: read every release's breaking changes against the arguments you use, clear deprecation warnings on the old version first, move one provider at a time with the lock file committed for every platform, back up state and go lowest environment first because a newer provider's schema upgrade in state is one-way, and gate every step on an empty plan in every environment, investigating any diff rather than applying it. |
| [`intermittent-502-hunt`](plugins/platform/skills/intermittent-502-hunt/SKILL.md) | Find the cause of sporadic 502s and 504s behind a load balancer or proxy, in order: confirm the balancer's idle timeout is shorter than the upstream's keepalive timeout (the reverse makes the backend close a connection the balancer is reusing), then deregistration delay against the longest request, health-check depth, and 502 bursts on deploy from SIGTERM handling; correlate balancer and app logs by request id to prove which side closed. |
| [`ip-exhaustion-recovery`](plugins/platform/skills/ip-exhaustion-recovery/SKILL.md) | Recover from running out of IP addresses — subnets with no free addresses, pods stuck in ContainerCreating because the CNI cannot assign one, nodes that will not launch, or networks that cannot be peered because their CIDRs overlap — without rebuilding the VPC. Measure who holds the addresses per subnet and per node first, free what the warm pool holds idle, add space with a secondary CIDR from 100.64.0.0/10 and custom networking, raise density with prefix delegation only when the ceiling is per node, bridge overlaps with PrivateLink or private NAT, and leave recreating the network last. |
| [`k8s-network-policy`](plugins/platform/skills/k8s-network-policy/SKILL.md) | Roll out default-deny Kubernetes NetworkPolicy, or its Cilium or Calico equivalent, without an outage: confirm the CNI enforces policy at all, observe real flows for a full business cycle before writing a rule, generate allows from the observed edges, allow DNS and the API server explicitly, run in audit or log mode until nothing legitimate would be dropped, then enforce one namespace at a time with a one-command rollback that works because policies are additive. |
| [`k8s-storage`](plugins/platform/skills/k8s-storage/SKILL.md) | Run persistent volumes and stateful workloads on Kubernetes without losing data: set reclaimPolicy Retain, allowVolumeExpansion and WaitForFirstConsumer binding before the first claim, treat a zonal volume as a scheduling constraint, grow a PVC or a StatefulSet's claims, snapshot and prove the restore in a scratch namespace, delete a StatefulSet with --cascade=orphan on purpose, and prefer an operator to hand-rolled database manifests. |
| [`monolith-state-split`](plugins/platform/skills/monolith-state-split/SKILL.md) | Split one oversized Terraform or OpenTofu state, thousands of resources and half-hour plans, into smaller stacks without destroying or recreating anything. Back up, draw the dependency graph, cut by blast radius and change cadence (network, data, compute, applications), replace in-state references with outputs and data lookups first, then move one slice at a time by scripted state mv or removed and import block pairs, gated by a zero-diff plan in both the old and new state after every slice. |
| [`resource-decommission`](plugins/platform/skills/resource-decommission/SKILL.md) | Retire an unused service, cloud account or orphaned resource without deleting something still in use: prove no use across a full business cycle including month-end jobs, run a scream test (deny access or scale to zero) for a set window, take a final snapshot, keep deletion protection on until the last step, remove DNS records pointing at it before the address or bucket is released, delete in dependency order through the owning IaC, then clear IAM, monitors and runbooks. Includes orphan sweeps for unattached disks, stale snapshots, idle load balancers and unused IPs on AWS, GCP and Azure. |
| [`restore-canary`](plugins/platform/skills/restore-canary/SKILL.md) | Build a scheduled, unattended restore of the newest database backup into a throwaway instance, verified and torn down daily, so "we have backups" becomes a measurement rather than a belief. Fails first when the newest backup is older than its interval, restores into an isolated scratch target, compares row counts and checksums on key tables over a closed watermark range, runs a canary query suite, records restore duration against the RTO, tears down on every exit path, and alerts on a missed run as loudly as a failed one. |
| [`spot-readiness`](plugins/platform/skills/spot-readiness/SKILL.md) | Make workloads survive spot or preemptible capacity being reclaimed, and decide which must not run there: classify each workload by its recovery time against the interruption notice (two minutes on AWS, 30 seconds on GCP and Azure), diversify across many instance types and every zone, run exactly one interruption handler that cordons and drains, enforce an on-demand floor at the pod level rather than the node group, and prove it by interrupting a spot node under load while the SLO holds. |
| [`workload-identity`](plugins/platform/skills/workload-identity/SKILL.md) | Replace static cloud keys with federated identity for pods and CI: IRSA or EKS Pod Identity, GKE and Azure workload identity, GitHub Actions OIDC. The trust policy pins issuer, audience and the exact subject (repository plus branch or environment; namespace plus service account), never a wildcard; one role per workload, short sessions; gate: a deliberate failed assumption from an unlisted repository or service account, and only then disable and delete the old keys. |

## Subagents

30 subagents ship across nine plugins. Each exists to keep bulk out of the main context
— the input is a log, a plan, a billing export, a contract, a pile of feedback, a release
range, and the answer is short — and to be denied the tools it should not have. A reviewer
that can apply is not a reviewer.

| Subagent | Plugin | Reads | Returns |
| --- | --- | --- | --- |
| `ci-log-reader` | `operations` | A failing run's logs | One of five triage classes and the line that decided it |
| `telemetry-reader` | `operations` | Traces and structured logs | The critical path, or why the data cannot answer |
| `k8s-evidence-reader` | `operations` | Captured Kubernetes evidence | Up to five capture-time evidence chains, with contradictions and missing evidence |
| `frame-capture-reader` | `gamedev` | A profiler capture or frame trace | CPU-bound or GPU-bound with the numbers, or what to capture instead |
| `screenshot-reader` | `design` | One or more screenshots of a UI | Findings by file and region, with what the image cannot show listed for measurement in code |
| `cost-analyst` | `operations` | A cloud billing export | The top movers period over period, not the top spenders |
| `incident-scribe` | `operations` | Raw triage notes and scrollback | A blameless postmortem draft |
| `page-history-reader` | `operations` | A quarter of pager or alert history | Per-rule fires, action rate, off-hours share and a suggested keep/tighten/demote/delete bucket |
| `llm-trace-reader` | `operations` | An LLM usage or trace export | Cost and latency hotspots by feature, prompt path, model and user, with spend-cap 429s kept apart from rate-limit 429s |
| `plan-reviewer` | `security` | A Terraform plan JSON | The blast radius, destroys first |
| `policy-auditor` | `security` | IAM policies and access logs | The gap between permitted and used, with the window stated |
| `pii-reader` | `security` | A schema dump, a row sample or a log excerpt | Which fields carry personal data, their class and where they flow |
| `extension-reader` | `security` | A third-party agent extension in a quarantine directory | What executes automatically, permissions, text aimed at the model quoted as data, and risk findings anchored to file and line |
| `supply-chain-exposure-reader` | `security` | Lockfile git history and CI run logs across many repositories | Every repository and run that resolved or executed a bad package or action, with the secrets each could reach |
| `skill-reviewer` | `coding` | A candidate SKILL.md | What is wrong, why it costs something, the smallest fix |
| `change-impact-reader` | `coding` | A diff and matching repository snapshots | Up to five impact chains, their evidence and unresolved boundaries |
| `agent-run-trace-reader` | `coding` | Historical agent-run artifacts | A task-and-attempt evidence ledger with unanswered calls and verification gaps |
| `test-history-reader` | `coding` | Hundreds of JUnit, pytest or go test reports across many CI runs | A flake-rate ledger with a denominator, co-failure clusters and a quarantine order by CI time and retries burned |
| `review-comment-miner` | `coding` | A pile of exported PR review comments or postmortem action items | Recurring clusters with an independent-instance count, a quoted example and candidate destinations |
| `contract-reader` | `manager` | A contract, DPA or SOC 2 report | The clauses that decide the deal, quoted and located |
| `feedback-synthesiser` | `manager` | Collected peer feedback | Themes with a source count and a quoted example |
| `changelog-reader` | `delivery` | A release range of commits and PRs | Audience-sorted inventory, breaking changes flagged, noise collapsed |
| `statement-reader` | `personal` | Bank, credit-card and digital-wallet transaction exports | Spending by category bucket, recurring charges, fees, transfers and anomalies |
| `terms-reader` | `personal` | An insurance policy, tenancy, loan or subscription's terms | The renewal date, notice period, exit charges and exclusions, each quoted and located |
| `framer` | `family` | A vague request and any known constraints | A frame: problem, users, success criterion, smallest slice, out of scope |
| `architect` | `family` | A frame and the surrounding architecture | The approach, boundaries, interfaces, failure modes and the hard-to-reverse decision |
| `maker` | `family` | A frame, an architecture note and the files a change touches | An ordered, file-level change plan with a proof per step, or the divergence from it |
| `inspector` | `family` | A change, its frame and the commands to run | What holds and what fails against the frame, with evidence, and what was not assessed |
| `launcher` | `family` | An inspected change and its deployment target | A launch plan — path, migration, signal, rollback — or the gaps blocking it |
| `yielder` | `family` | A slice's outcome and its success criterion | A retro: what was measured, what to keep, what to change, and the next slice |

Four more sit in [`.claude/agents/`](.claude/agents) and ship to nobody. They are for
working on this repository, in two loops that share a judge.

| Subagent | Loop | Role |
| --- | --- | --- |
| `explorer` | build | Surveys what already covers a change |
| `implementer` | build | Writes it and runs the gates |
| `investigator` | both | Settles one claim against primary sources |
| `reviewer` | both | Judges the result on a fresh context with no editing tools |

To build something: [`/ship`](.claude/commands/ship.md) runs `explorer` and, when the
change rests on an outside claim, `investigator` in parallel, then `implementer`, then
`reviewer`, then opens one pull request and merges once `reviewer`, `ci` and `security`
pass.

To establish whether something is true: `investigator` settles one claim against primary
sources, labels every finding primary, consensus or inference, and says what it could not
verify and why; then `reviewer` judges whether the finding actually supports the change.
[`/verify`](.claude/commands/verify.md) runs the two. It exists because a skill in this
repository once asserted that a `kubectl drain` flag skipped graceful shutdown, and the
source said otherwise.

Each runs on the tier its stage needs.
[Writing a subagent](docs/writing-agents.md#the-two-loops) explains why the splits earn
their round trips.

## Commands

Commands here explicitly declare `disable-model-invocation: true`, so they run only
when invoked explicitly. That makes them the right shape for work that takes an
argument, or that should run when asked rather than when merely relevant.
Each does the mechanical part and points at the skill holding the full procedure.

| Command | Ships with | What it does |
| --- | --- | --- |
| `/ci-fail` | `operations` | Classify a failing run from annotations and failed-step logs, after checking whether the default branch is red too. |
| `/oncall-handover` | `operations` | Draft a handover from pages, deploys and anything left mid-flight, with the fragile mitigations first. |
| `/level` | `gamedev` | Run a level or feature through spec, layout, grey-box, tuning, frame budget and build size, with a gate between each stage. |
| `/visual-review` | `design` | Review a rendered page from screenshots: pin the render, capture a viewport and theme matrix, diff against an optional baseline, run the code checks, then have `screenshot-reader` read crops and report measured and unverified findings separately. |
| `/agent-diff-audit` | `coding` | Run mechanical detectors for shrunk test counts, newly silenced checks and invented dependencies over an agent-written diff, then hand the flagged list to code-review. |
| `/blast-radius` | `security` | Read a Terraform plan as JSON and report destroys first, with the attribute forcing each replacement. |
| `/image-audit` | `security` | Audit a built image for secrets in layers, root execution, base currency and a gate that will not get bypassed. |
| `/weekly` | `manager` | Draft a bottom-line-first status update from merged pull requests and commits, every number sourced. |
| `/agent-ready` | `manager` | Clone a repository and actually run its AGENTS.md, checking instruction-file size against a known agent tool cap and flagging dangling paths and exposed secrets. |
| `/family:family` | `family` | Start a FAMILY slice: validate the slice name, have framer frame the request into `docs/slices/<name>/frame.md`, create the other five stage files as empty templates, and print the verdict and the next hop. |
| `/scaffold-skill` | this repository | Create the directory, SKILL.md and eval stub for a new skill, in the right plugin, refusing a duplicate name. |
| `/eval-skill` | this repository | Score whether one description actually triggers, and name the phrasing it is missing. |
| `/skill-doctor` | this repository | Diagnose one skill: validator findings, description health, eval-set balance, and which siblings it collides with. |
| `/skill-gap` | this repository | Survey the library for coverage it lacks, from its own dangling demand, and say which of skill, subagent, command or nothing the gap deserves. |
| `/ship` | this repository | Take a change from survey to merge: research in parallel, write it and run the gates, judge it independently, then open one pull request and merge once review, `ci` and `security` pass. |
| `/verify` | this repository | Take a claim through the verification loop: settle it against primary sources, labelling what is verified and what is not, then judge whether the finding supports the change. |

## CI is the source of truth

Every skill is validated on pull requests, pushes to `main`, merge-group checks and
manual CI runs. The validator is standard library only, and the test matrix runs on
Python 3.10 through 3.13. Coverage is measured on 3.13; the full suite runs on all four.
Independent checks run in parallel, then packaging builds the review artifacts only
after the CI checks pass. The stable `ci` and `security` gates reject every non-success
dependency, including skipped jobs. See the [execution flow](docs/ci.md#execution-flow).

```bash
make validate     # frontmatter contract, dangling references, marketplace cross-check
make catalogue    # listing ceilings, the README and CI docs, workflows, shell, the hook, providers
make test         # the validator's own test suite
make coverage     # the same, with the coverage floor CI enforces
make test-browser # drive the built site in Chromium (needs playwright)
make package      # a .skill archive per skill
make attribution  # commits and branch name against the attribution rules
make naming       # branch, commit and file-naming conventions
```

The check that earns its place is the dangling-pointer one. Two of these skills shipped
for months naming `references/*.md` files nobody had written — the model loaded nothing
where it expected depth, and no error was ever raised. CI now fails on it.

Alongside `ci`, a `security` gate runs gitleaks over the working tree and history, zizmor
over the workflows themselves, ruff's flake8-bandit rules, CodeQL, and four invariants:
every workflow declares a top-level `permissions:` block that is not `write-all` or
`read-all` and grants `write` on no scope, every action is pinned to a commit SHA, every
job sets `timeout-minutes`, and every checkout sets `persist-credentials: false`.
actionlint and gitleaks, the two binaries CI downloads by hand rather than through an
action or a package manager, are pinned to a version and checked against a recorded
digest, with retries capped by a total deadline so a slow or rate-limiting server cannot
run past a job's own timeout. A `naming` gate checks the same shape this repository holds
contributors to — branch names, commit subjects, pull-request titles, and file and folder
names — against [`CONTRIBUTING.md`](CONTRIBUTING.md#naming); `make naming` reproduces
everything but the pull request title, which is checked only in CI, once the pull request
exists.

When `ci` or `security` goes red on a pull request,
[`ci-triage.yml`](docs/ci.md#githubworkflowsci-triageyml--ci-triage) posts one comment
naming each failed job, its first failed step, the likely cause, with the local command
that reproduces it where one exists, and links to that job's docs section and log — plus
a `ci-failed` label kept in step with it. Once both gates pass, it edits the same comment
to say `Recovered` and drops the label; a pull request that never fails gets no comment
at all. It runs only from the workflow file already on `main`, never a pull request's own
head, and holds `actions: read`, `contents: read`, `issues: write` and `pull-requests:
write` — enough to read runs and comment on and label the pull request, never to write to
contents or push anything, and spent only on that one comment and that one label.

Some repository controls live in GitHub's settings rather than in this tree — the branch
ruleset, private vulnerability reporting, secret scanning and push protection, Dependabot
alerts and security updates, and which CodeQL setup runs — and no file here can see
whether they are switched on. [CI](docs/ci.md#recorded-state)
names those controls, records which ones the owner has confirmed as on, and gives the
commands to read each one's state back, since a repository can look rigorous while a
control it describes is silently off.

Subagents are held to the same contract, and every skill carries a trigger eval set —
twenty queries it should fire on and near-misses it should not, with most near-misses
naming the sibling that ought to win it. The schema is checked on every push because that is
free; scoring the queries needs a model, so it runs on demand rather than gating anything.
Each query is judged against the whole catalogue of descriptions, which is what catches a
skill that fires on everything.

## Documentation

- [Using the skills](docs/using.md) — installing and using them in Claude Code, ChatGPT, Grok and terminal agents
- [The repository workflow in ChatGPT](docs/chatgpt-agents.md) — adapted coordinator and role prompts for the survey, write and review loop, and where actual delegation depends on the session's tools
- [DeepSeek via OpenRouter](docs/deepseek.md) — routing Claude Code to a DeepSeek model through OpenRouter, and what that costs you
- [Gamedev: start here](docs/gamedev.md) — picking a production scale and a game type, and the route through the thirteen gamedev skills
- [Project structure](docs/project-structure.md) — what Claude Code loads from a project, what it loads only when relevant, and what is only a convention
- [Writing a skill](docs/writing-skills.md) — the contract, every validator code, and how to write a description that actually triggers
- [Writing a subagent](docs/writing-agents.md) — when a subagent beats doing the work inline
- [Writing a slash command](docs/writing-commands.md) — when a command beats a skill, and why most do not
- [Review lessons](docs/review-lessons.md) — defect classes review on this repository has actually caught, read after `AGENTS.md` by the build and verify loops
- [Review instructions](REVIEW.md) — severity redefined for Claude Code's managed GitHub code review, and what it skips; points back to `AGENTS.md`'s Review guidelines for the triggers and comment format
- [AGENTS.md](docs/agents-md.md) — the standard, and how it relates to `CLAUDE.md`
- [CI](docs/ci.md) — what each check means and how to make it required
- [Best practices](docs/best-practices.md) — CI, security, and branching and merging: the practice, why it matters, how this repository applies it, and what is not yet adopted
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Code of conduct](CODE_OF_CONDUCT.md)

Repository conventions for agents live in [`AGENTS.md`](AGENTS.md).

## Licence

[MIT](LICENSE). Use it, copy it, change it, ship it inside something you sell — the
condition, in MIT's own words, is that the copyright notice and the permission notice
(the full licence text) are included in all copies or substantial portions of the
software, not merely that the notice travels with it. The notice names **Serhii
Zolotov**, the username **greenblacked**, and links to this repository, so any copy,
fork or derivative has to say where it came from:

```text
Copyright (c) 2026 Serhii Zolotov (GitHub: greenblacked), https://github.com/greenblacked/AI
```

Keep both the notice and the licence text with it — in a `LICENSE` file, a header, or a
credits page, anywhere a reader of the copy will find them. The copies this repository
produces already comply: every `.skill` archive carries `LICENSE.txt` and `NOTICE.txt`
beside `SKILL.md`, and `make portable`'s output carries `LICENSE` and `NOTICE` at its
root plus a short copy of the notice at the foot of every skill file and plugin bundle,
so lifting one of those elsewhere needs no extra step from you. What the licence does
not require is asking first, or sharing changes back.

### Independence and disclaimer

This is an independent personal project. It is not affiliated with, endorsed by or made
on behalf of any employer or any company named in it. The research, drafting and testing
used AI models reached through the author's own personal subscriptions and accounts,
paid for by the author, and nothing here is professional advice. [`NOTICE`](NOTICE) has
the full statement, including the trademark note; it does not change the terms of the
MIT licence above.
