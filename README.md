# Agent skills

[![CI](https://github.com/greenblacked/AI/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/ci.yml)
[![Security](https://github.com/greenblacked/AI/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/security.yml)
[![Scheduled checks](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml)
[![Skills](https://img.shields.io/badge/skills-59-7c3aed)](#skills)
[![License: MIT](https://img.shields.io/badge/license-MIT-0ea5e9)](LICENSE)

59 agent skills, nine read-only subagents and five slash commands, in seven
plugins you install separately. They cover the daily loop of changing code, keeping a
system running, shipping a change, securing it, making a game, leading a team, a career,
and the parts of life that are nobody's job.

A skill is a Markdown procedure an agent loads when it recognises the situation. Nothing
here wraps a model's general knowledge. The useful part of a skill is the opinionated
part: the gate that stops you, the ordering that saves an hour, the command with the flag
that actually produces the evidence. A skill that would only restate what the model
already does is not in here — there is no commit-message writer and no git-worktree
helper, because both are ceremony.

They are procedures, not plugin code, so they are not tied to one assistant. Claude Code
installs them as plugins and fires them automatically; `make portable` flattens every one
into a standalone file for ChatGPT, Grok, Codex or anything else that reads text.
[Using the skills](docs/using.md) covers each route, and is honest about what you lose
outside a runtime that can trigger them for you.

## What is included

| Plugin | Focus | Contents |
| --- | --- | --- |
| `coding` | Reading, reviewing, testing and changing code | 11 skills, 1 subagent |
| `gamedev` | Making games, and shipping them | 5 skills |
| `operations` | Keeping a running system alive | 8 skills, 4 subagents, 2 commands |
| `delivery` | Getting a change into production | 5 skills |
| `security` | The defensive side of shipping software | 5 skills, 2 subagents, 2 commands |
| `manager` | Engineering leadership | 13 skills, 2 subagents, 1 command |
| `personal` | Money, travel, admin, habits and health | 7 skills |
| `career` | Applications, negotiation, speaking and writing | 5 skills |

Install one plugin or all eight. Each is a self-contained directory under `plugins/` with
its own manifest, so installing one does not pull in another's files.

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
least, which leaves them invocable by name and stops them being chosen on their own. Six
of the eight plugins fit the default budget on their own, and the split exists for exactly
this reason. If you install several, raise the budget in `~/.claude/settings.json`:

```json
{ "skillListingBudgetFraction": 0.04 }
```

`/doctor` reports what the listing actually costs and its biggest contributors.

### ChatGPT, Grok, Codex and everything else

There is no marketplace to read, so the skills are flattened into files that stand alone
— frontmatter becomes a plain "Use this when" line and every reference file is inlined, so
nothing is left pointing at a path the reader cannot open.

You do not need a toolchain to get them. Every CI run builds them and attaches them as
the **portable-skills** artifact: open the
[latest run](https://github.com/greenblacked/AI/actions/workflows/ci.yml?query=branch%3Amain),
scroll to Artifacts, and download. Inside are one file per skill, one bundle per plugin,
an index of every description, and a README explaining where each goes.

If you do have a terminal, build them yourself instead:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
make portable       # writes dist/portable/
```

Either way: upload the `plugins/*.md` bundles to a ChatGPT Project or a Custom GPT, paste
a single `skills/<name>.md` into any chat, or append a bundle to the `AGENTS.md` of the
repository a terminal agent is working in. [Using the skills](docs/using.md) has the
instruction text that makes a Project reach for them, and says plainly what does not
survive the trip.

### Working on the skills themselves

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
./scripts/install.sh --dry-run   # see what it would link
./scripts/install.sh             # symlink every skill into ~/.claude/skills
```

## Skills

### Coding

Reading, reviewing, testing and changing code.

| Skill | What it does |
| --- | --- |
| [`api-design`](plugins/coding/skills/api-design/SKILL.md) | Design an interface that can still be changed after other people depend on it — compatibility rules, error structure, pagination, and deprecation with usage telemetry. |
| [`code-review`](plugins/coding/skills/code-review/SKILL.md) | Review a change in a fixed order — the claim, the error path, concurrency, hostile input — finishing correctness before the first style comment, with a severity on every finding and coverage declared rather than implied. |
| [`code-scaffold`](plugins/coding/skills/code-scaffold/SKILL.md) | Write new code that survives a 3am cron run: strict error handling, meaningful exit codes, structured logging, validated input, idempotent re-runs. |
| [`codebase-orientation`](plugins/coding/skills/codebase-orientation/SKILL.md) | Get oriented in code you did not write: what it does before how it is built, one real request traced end to end, the tests as specification and the history as evidence, ending in a map and a first change. |
| [`debugging`](plugins/coding/skills/debugging/SKILL.md) | Drive a failure down to a proven cause before changing any code: reproduce it, reduce it, one falsifiable hypothesis at a time, and prove the fix by turning the failure off and on again. |
| [`dependency-upgrade`](plugins/coding/skills/dependency-upgrade/SKILL.md) | Move onto a new major version without a branch that never lands: deprecation warnings first, one dependency per change, and the uncovered surface named. |
| [`new-skill`](plugins/coding/skills/new-skill/SKILL.md) | Author a skill that actually fires: decide whether it deserves to exist, write the body before the description, and build the eval set from the neighbouring skills it has to beat. |
| [`refactoring`](plugins/coding/skills/refactoring/SKILL.md) | Restructure without changing behaviour, in steps each provably safe: a characterisation test before touching code nobody understands, one kind of change per commit, and a proof at the end. |
| [`technical-docs`](plugins/coding/skills/technical-docs/SKILL.md) | Write documentation still true in six months: name the reader, pick one Diátaxis mode instead of blending two, execute every command you print, and prune the stale page rather than adding a newer one beside it. |
| [`test-design`](plugins/coding/skills/test-design/SKILL.md) | Choose what to test before writing tests: equivalence classes and their boundaries, the error paths nobody writes, pairwise selection when the inputs explode, and the seams that stop a suite going flaky. |
| [`website-builder`](plugins/coding/skills/website-builder/SKILL.md) | Build a site that looks designed for its subject and can still be hosted and maintained afterwards — or audit one that already exists. |

### Gamedev

Making games, and shipping them.

| Skill | What it does |
| --- | --- |
| [`game-assets`](plugins/gamedev/skills/game-assets/SKILL.md) | Get art and audio into the build without it eating the disk, the memory or the download — source kept out of the import path, large binaries behind LFS before the history is too big, and per-platform texture compression chosen rather than defaulted. |
| [`game-balance`](plugins/gamedev/skills/game-balance/SKILL.md) | Tune a game's numbers against evidence rather than taste: decide what balanced means for this game first, read pick rate against win rate by skill band, change one thing with a window, and run playtests where you watch instead of asking. |
| [`game-builder`](plugins/gamedev/skills/game-builder/SKILL.md) | Build a playable game scaled to the brief — core loop first in grey boxes, then a game-feel floor tuned against numbers — or review one that exists for feel, frame time and structure. |
| [`game-netcode`](plugins/gamedev/skills/game-netcode/SKILL.md) | Choose a multiplayer authority model from genre and player count, then hide latency with prediction, reconciliation and interpolation — and treat anything the client is authoritative over as a thing the client can lie about. |
| [`game-performance`](plugins/gamedev/skills/game-performance/SKILL.md) | Hold a frame budget on the hardware you ship to: milliseconds not FPS, captured from a real build on the device, judged at the 1% low, and CPU-bound proved against GPU-bound before a single optimisation. |

### Operations

Keeping a running system alive.

| Skill | What it does |
| --- | --- |
| [`alert-design`](plugins/operations/skills/alert-design/SKILL.md) | Write, review or delete alerting rules so every page is user-visible and actionable now: symptom over mechanism, multiwindow burn-rate rules, and pruning by how often anyone acted rather than by how often it fired. |
| [`capacity-planning`](plugins/operations/skills/capacity-planning/SKILL.md) | Work out whether a system survives an expected load: a demand model first, the one saturating resource, and a defined behaviour past capacity. |
| [`ci-triage`](plugins/operations/skills/ci-triage/SKILL.md) | Classify a red pipeline before debugging it — real failure, flake, runner, config, or dependency drift — starting with whether the default branch is already broken. Quarantine policy and retry hygiene included. |
| [`cost-review`](plugins/operations/skills/cost-review/SKILL.md) | Investigate a bill that grew, or reduce spend deliberately: attribute before acting, read the top movers rather than the top spenders, and name what each saving degrades. |
| [`game-day`](plugins/operations/skills/game-day/SKILL.md) | Plan and run a reliability exercise around a falsifiable hypothesis, with a blast radius chosen in advance and an abort that was executed before the experiment started. |
| [`instrumentation`](plugins/operations/skills/instrumentation/SKILL.md) | Add telemetry so the next incident is diagnosable — instrument backwards from the questions you will need answered at 3am, with cardinality bounded on purpose. |
| [`k8s-triage`](plugins/operations/skills/k8s-triage/SKILL.md) | Mitigate first, diagnose second. The deploy-related question, the fixed evidence order, and a decode table for the failure modes that account for most of them. |
| [`runbook`](plugins/operations/skills/runbook/SKILL.md) | Write what the 3am reader follows: numbered steps, real commands, every mitigation with its blast radius, and a last-verified date, because a wrong runbook is worse than none. |

### Delivery

Getting a change into production without a bad night.

| Skill | What it does |
| --- | --- |
| [`cutover`](plugins/delivery/skills/cutover/SKILL.md) | Run the change that has a point of no return — a traffic switch, a provider move, a region migration — from a rehearsed runbook with a rollback deadline computed before the window opens. |
| [`db-migration`](plugins/delivery/skills/db-migration/SKILL.md) | Ship a schema change to a live database without a stuck lock: expand and contract, each phase its own revertible deploy, batched backfills, and the Postgres operations that are safe versus the ones that rewrite the table. |
| [`plan-platform-migration`](plugins/delivery/skills/plan-platform-migration/SKILL.md) | Plan a production migration around invariants, state authority, phased evidence gates, rehearsed rollback, controlled cutover, and explicit legacy retirement. |
| [`release-notes`](plugins/delivery/skills/release-notes/SKILL.md) | Turn a range of merged changes into notes the affected reader can act on, sorted by who is affected rather than by component, every breaking change carrying the migration it demands. |
| [`release-strategy`](plugins/delivery/skills/release-strategy/SKILL.md) | Separate deploy from release: flags, rings and canaries chosen by how the change fails, with promotion gates, bake times and a flag removal date. |

### Security

The defensive side of shipping software.

| Skill | What it does |
| --- | --- |
| [`access-review`](plugins/security/skills/access-review/SKILL.md) | Reduce who and what can do what toward least privilege without breaking production: evidence over intent, and an audit-only window before enforcement. |
| [`iac-review`](plugins/security/skills/iac-review/SKILL.md) | Review a Terraform change against the plan JSON rather than the plan text, so replacements and destroys surface first instead of being skimmed past. |
| [`image-hardening`](plugins/security/skills/image-hardening/SKILL.md) | Build or audit a container image: minimal base, digest pinning, numeric non-root UID, no secrets in layers, SBOM, a scan gate that will not get bypassed, signing that is actually verified. |
| [`secret-rotation`](plugins/security/skills/secret-rotation/SKILL.md) | Rotate a credential, or contain one that has leaked. The two run in opposite orders, and the skill makes you pick which one you are in before it does anything else. |
| [`security-review`](plugins/security/skills/security-review/SKILL.md) | Walk a diff through the classes that actually get exploited — object-level authorisation, injection, deserialisation, request forgery, secrets, the supply-chain change — reporting each as reachable path, impact, fix. |

### Manager

Engineering leadership.

| Skill | What it does |
| --- | --- |
| [`ai-enablement`](plugins/manager/skills/ai-enablement/SKILL.md) | Assess how a team actually uses AI-assisted engineering and produce a rollout plan, including the metrics that help and the ones that quietly destroy honest feedback. |
| [`decision-record`](plugins/manager/skills/decision-record/SKILL.md) | Turn a decision into a MADR-format ADR or a design doc, with at least two genuinely considered options and a confirmation step that names a real check. |
| [`delivery-review`](plugins/manager/skills/delivery-review/SKILL.md) | Read delivery health honestly: DORA as a property of the system rather than of people, flow and queue time, and prioritisation frameworks applied only where they belong. |
| [`design-team-cadence`](plugins/manager/skills/design-team-cadence/SKILL.md) | Design a minimal management operating rhythm where every recurring forum has a decision or relationship purpose, explicit inputs and outputs, and a cancellation rule. |
| [`difficult-conversation`](plugins/manager/skills/difficult-conversation/SKILL.md) | Prepare and hold the conversation you keep putting off: the outcome fixed first, observed behaviour separated from the story about intent, and an honest answer to whether this is feedback or a decision already made. |
| [`growth-review`](plugins/manager/skills/growth-review/SKILL.md) | Prepare a review, a promotion case or a development plan from evidence over the whole period rather than the last six weeks, where every claim carries an example. |
| [`hiring-loop`](plugins/manager/skills/hiring-loop/SKILL.md) | Design and run a hiring loop from a scorecard: stages that each test something the others do not, written scores before the debrief, and "culture fit" restated as a named behaviour or dropped. |
| [`incident-comms`](plugins/manager/skills/incident-comms/SKILL.md) | Communicate an incident to customers, executives and staff: acknowledge on impact rather than diagnosis, and keep the next-update promise even when nothing has changed. |
| [`okr-planning`](plugins/manager/skills/okr-planning/SKILL.md) | Set goals that change what people do — an objective is the outcome, a key result is the evidence — with baselines before targets and guardrails beside them. |
| [`onboarding-plan`](plugins/manager/skills/onboarding-plan/SKILL.md) | Get a new engineer productive deliberately: access working before day one, something shipped in week one, and 30/60/90 expectations written down and shared. |
| [`postmortem`](plugins/manager/skills/postmortem/SKILL.md) | Write a blameless postmortem in the Google SRE shape, where "human error" is a prompt for a better question and every action item has an owner. |
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

## Subagents

Nine subagents ship across four plugins. Each exists to keep bulk out of the main context
— the input is a log, a plan, a billing export, a contract, a pile of feedback, and the
answer is short — and to be denied the tools it should not have. A reviewer that can apply
is not a reviewer.

| Subagent | Plugin | Reads | Returns |
| --- | --- | --- | --- |
| `ci-log-reader` | `operations` | A failing run's logs | One of five triage classes and the line that decided it |
| `telemetry-reader` | `operations` | Traces and structured logs | The critical path, or why the data cannot answer |
| `cost-analyst` | `operations` | A cloud billing export | The top movers period over period, not the top spenders |
| `incident-scribe` | `operations` | Raw triage notes and scrollback | A blameless postmortem draft |
| `plan-reviewer` | `security` | A Terraform plan JSON | The blast radius, destroys first |
| `policy-auditor` | `security` | IAM policies and access logs | The gap between permitted and used, with the window stated |
| `skill-reviewer` | `coding` | A candidate SKILL.md | What is wrong, why it costs something, the smallest fix |
| `contract-reader` | `manager` | A contract, DPA or SOC 2 report | The clauses that decide the deal, quoted and located |
| `feedback-synthesiser` | `manager` | Collected peer feedback | Themes with a source count and a quoted example |

Three more sit in [`.claude/agents/`](.claude/agents) and ship to nobody. They are for
working on this repository: `explorer` surveys what already covers a change, `implementer`
writes it and runs the gates, and `reviewer` judges the result on a fresh context with no
editing tools. Each runs on the tier its stage needs, and [`/ship`](.claude/commands/ship.md)
runs the three in order. [Writing a subagent](docs/writing-agents.md#the-three-stage-loop)
explains why the split earns its round trips.

## Commands

A command never fires on its own — you type it — which makes it the right shape for work
that takes an argument, or that should run when asked rather than when merely relevant.
Each does the mechanical part and points at the skill holding the full procedure.

| Command | Ships with | What it does |
| --- | --- | --- |
| `/ci-fail` | `operations` | Classify a failing run from annotations and failed-step logs, after checking whether the default branch is red too. |
| `/oncall-handover` | `operations` | Draft a handover from pages, deploys and anything left mid-flight, with the fragile mitigations first. |
| `/blast-radius` | `security` | Read a Terraform plan as JSON and report destroys first, with the attribute forcing each replacement. |
| `/image-audit` | `security` | Audit a built image for secrets in layers, root execution, base currency and a gate that will not get bypassed. |
| `/weekly` | `manager` | Draft a bottom-line-first status update from merged pull requests and commits, every number sourced. |
| `/scaffold-skill` | this repository | Create the directory, SKILL.md and eval stub for a new skill, in the right plugin, refusing a duplicate name. |
| `/eval-skill` | this repository | Score whether one description actually triggers, and name the phrasing it is missing. |
| `/skill-doctor` | this repository | Diagnose one skill: validator findings, description health, eval-set balance, and which siblings it collides with. |
| `/ship` | this repository | Take a change through the three-stage loop: survey what already exists, write it and run the gates, then judge the result independently. |

## CI is the source of truth

Every skill is validated on every push. The validator is standard library only, and the
test matrix runs it on Python 3.10 through 3.13 to keep it that way.

```bash
make validate   # frontmatter contract, dangling references, marketplace cross-check
make test       # the validator's own test suite
make coverage   # the same, with the coverage floor CI enforces
make package    # a .skill archive per skill
```

The check that earns its place is the dangling-pointer one. Two of these skills shipped
for months naming `references/*.md` files nobody had written — the model loaded nothing
where it expected depth, and no error was ever raised. CI now fails on it.

Alongside `ci`, a `security` gate runs gitleaks over the working tree and history, zizmor
over the workflows themselves, ruff's flake8-bandit rules, CodeQL, and two invariants:
every workflow declares a `permissions:` block, and every action is pinned to a commit
SHA.

Subagents are held to the same contract, and every skill carries a trigger eval set —
twenty queries it should fire on and near-misses it should not, with each near-miss naming
the sibling that ought to win it. The schema is checked on every push because that is
free; scoring the queries needs a model, so it runs on demand rather than gating anything.
Each query is judged against the whole catalogue of descriptions, which is what catches a
skill that fires on everything.

## Documentation

- [Using the skills](docs/using.md) — installing and using them in Claude Code, ChatGPT, Grok and terminal agents
- [Writing a skill](docs/writing-skills.md) — the contract, every validator code, and how to write a description that actually triggers
- [Writing a subagent](docs/writing-agents.md) — when a subagent beats doing the work inline
- [Writing a slash command](docs/writing-commands.md) — when a command beats a skill, and why most do not
- [AGENTS.md](docs/agents-md.md) — the standard, and how it relates to `CLAUDE.md`
- [CI](docs/ci.md) — what each check means and how to make it required
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Repository conventions for agents live in [`AGENTS.md`](AGENTS.md).

## Licence

[MIT](LICENSE).
