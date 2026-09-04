# Agent skills for platform engineering

[![CI](https://github.com/greenblacked/AI/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/ci.yml)
[![Security](https://github.com/greenblacked/AI/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/security.yml)
[![Scheduled checks](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml/badge.svg?branch=main)](https://github.com/greenblacked/AI/actions/workflows/scheduled.yml)
[![Skills](https://img.shields.io/badge/skills-26-7c3aed)](#skills)
[![License: MIT](https://img.shields.io/badge/license-MIT-0ea5e9)](LICENSE)

A focused library of 26 agent skills and four read-only specialist subagents, built from
real platform engineering, DevOps, engineering-management, and technical-writing work.
Everything is installable through a three-plugin marketplace and validated before it ships.

A skill is a Markdown procedure an agent loads when it recognises the situation. Most of
what is here comes out of platform and DevOps work — triaging a red pipeline, reading a
Terraform plan properly, getting a broken workload back before diagnosing it, hardening a
container image — plus the leadership side of the same job and a few personal ones.

Nothing here is a wrapper around a model's general knowledge. The useful part of a skill
is the opinionated part: the gate that stops you, the ordering that saves an hour, the
command with the flag that actually produces the evidence.

## What is included

| Plugin | Focus | Contents |
| --- | --- | --- |
| `engineering` | Platform delivery and operations | 13 skills and 4 specialist subagents |
| `manager` | Engineering leadership | 9 skills |
| `personal` | Health, career, learning and writing | 4 skills |

Install one plugin or all three. Only the `engineering` plugin includes subagents; the
other plugins contain skills alone. Each plugin is a self-contained directory under
`plugins/` with its own manifest, skills and subagents, so installing one does not pull in
the others' files.

## Install

```shell
/plugin marketplace add greenblacked/AI
/plugin install engineering@greenblacked-ai
/plugin install manager@greenblacked-ai
/plugin install personal@greenblacked-ai
/reload-plugins
```

Or, to work on them locally and have edits take effect immediately:

```bash
git clone https://github.com/greenblacked/AI.git && cd AI
./scripts/install.sh --dry-run   # see what it would link
./scripts/install.sh             # symlink every skill into ~/.claude/skills
```

## Skills

### Engineering

| Skill | What it does |
| --- | --- |
| [`alert-design`](plugins/engineering/skills/alert-design/SKILL.md) | Write, review or delete alerting rules so every page is user-visible and actionable now: symptom over mechanism, multiwindow burn-rate rules, and pruning by how often anyone acted rather than by how often it fired. |
| [`ci-triage`](plugins/engineering/skills/ci-triage/SKILL.md) | Classify a red pipeline before debugging it — real failure, flake, runner, config, or dependency drift — starting with whether the default branch is already broken. Quarantine policy and retry hygiene included. |
| [`code-scaffold`](plugins/engineering/skills/code-scaffold/SKILL.md) | Write new code that survives a 3am cron run: strict error handling, meaningful exit codes, structured logging, validated input, idempotent re-runs. |
| [`cutover`](plugins/engineering/skills/cutover/SKILL.md) | Run the change that has a point of no return — a traffic switch, a provider move, a region migration — from a rehearsed runbook with a rollback deadline computed before the window opens. |
| [`db-migration`](plugins/engineering/skills/db-migration/SKILL.md) | Ship a schema change to a live database without a stuck lock: expand and contract, each phase its own revertible deploy, batched backfills, and the Postgres operations that are safe versus the ones that rewrite the table. |
| [`game-day`](plugins/engineering/skills/game-day/SKILL.md) | Plan and run a reliability exercise around a falsifiable hypothesis, with a blast radius chosen in advance and an abort that was executed before the experiment started. |
| [`iac-review`](plugins/engineering/skills/iac-review/SKILL.md) | Review a Terraform change against the plan JSON rather than the plan text, so replacements and destroys surface first instead of being skimmed past. |
| [`image-hardening`](plugins/engineering/skills/image-hardening/SKILL.md) | Build or audit a container image: minimal base, digest pinning, numeric non-root UID, no secrets in layers, SBOM, a scan gate that will not get bypassed, signing that is actually verified. |
| [`k8s-triage`](plugins/engineering/skills/k8s-triage/SKILL.md) | Mitigate first, diagnose second. The deploy-related question, the fixed evidence order, and a decode table for the failure modes that account for most of them. |
| [`new-skill`](plugins/engineering/skills/new-skill/SKILL.md) | Author a skill that actually fires: decide whether it deserves to exist, write the body before the description, and build the eval set from the neighbouring skills it has to beat. |
| [`plan-platform-migration`](plugins/engineering/skills/plan-platform-migration/SKILL.md) | Plan a production migration around invariants, state authority, phased evidence gates, rehearsed rollback, controlled cutover, and explicit legacy retirement. |
| [`secret-rotation`](plugins/engineering/skills/secret-rotation/SKILL.md) | Rotate a credential, or contain one that has leaked. The two run in opposite orders, and the skill makes you pick which one you are in before it does anything else. |
| [`website-builder`](plugins/engineering/skills/website-builder/SKILL.md) | Build a site that looks designed for its subject and can still be hosted and maintained afterwards — or audit one that already exists. |

### Manager

| Skill | What it does |
| --- | --- |
| [`ai-enablement`](plugins/manager/skills/ai-enablement/SKILL.md) | Assess how a team actually uses AI-assisted engineering and produce a rollout plan, including the metrics that help and the ones that quietly destroy honest feedback. |
| [`decision-record`](plugins/manager/skills/decision-record/SKILL.md) | Turn a decision into a MADR-format ADR or a design doc, with at least two genuinely considered options and a confirmation step that names a real check. |
| [`delivery-review`](plugins/manager/skills/delivery-review/SKILL.md) | Read delivery health honestly: DORA as a property of the system rather than of people, flow and queue time, and prioritisation frameworks applied only where they belong. |
| [`design-team-cadence`](plugins/manager/skills/design-team-cadence/SKILL.md) | Design a minimal management operating rhythm where every recurring forum has a decision or relationship purpose, explicit inputs and outputs, and a cancellation rule. |
| [`growth-review`](plugins/manager/skills/growth-review/SKILL.md) | Prepare a review, a promotion case or a development plan from evidence over the whole period rather than the last six weeks, where every claim carries an example. |
| [`hiring-loop`](plugins/manager/skills/hiring-loop/SKILL.md) | Design and run a hiring loop from a scorecard: stages that each test something the others do not, written scores before the debrief, and "culture fit" restated as a named behaviour or dropped. |
| [`postmortem`](plugins/manager/skills/postmortem/SKILL.md) | Write a blameless postmortem in the Google SRE shape, where "human error" is a prompt for a better question and every action item has an owner. |
| [`status-update`](plugins/manager/skills/status-update/SKILL.md) | Bottom line up front for status, Minto for persuasion, and never the two mixed. Numbers are sourced or marked as missing. |
| [`vendor-evaluation`](plugins/manager/skills/vendor-evaluation/SKILL.md) | Run a buy decision to a defensible conclusion, including the decision not to buy — weights agreed before any demo, three-year total cost, and an exit cost established while you still have leverage. |

### Personal

| Skill | What it does |
| --- | --- |
| [`health-coach`](plugins/personal/skills/health-coach/SKILL.md) | Estimate calories and macros from a photo or a description, as a range with the uncertainty named, then suggest one thing worth changing. |
| [`job-search`](plugins/personal/skills/job-search/SKILL.md) | Tailor a CV and prepare for interviews from a real history. Selection and evidence, never embellishment. |
| [`learning-notes`](plugins/personal/skills/learning-notes/SKILL.md) | Turn something read into a note that is still useful in a year, on the principle that a summary is not a note. |
| [`write-technical-article`](plugins/personal/skills/write-technical-article/SKILL.md) | Turn real engineering experience and verifiable sources into a publishable technical article with a defensible thesis and no invented authority. |

## Subagents

`plugins/engineering/agents/` holds four subagents that exist to keep bulk out of the main
context and to be
denied tools they should not have: `ci-log-reader` reads a failing run and returns a
classification, `plan-reviewer` reads a Terraform plan and returns the blast radius,
`incident-scribe` turns triage notes into a postmortem draft, and `skill-reviewer` audits
a candidate skill against this repository's rules.

## Commands

A command never fires on its own — you type it — which makes it the right shape for work
that takes an argument, or that should run when asked rather than when merely relevant.
Each one does the mechanical part and points at the skill that holds the full procedure.

| Command | Ships with | What it does |
| --- | --- | --- |
| `/blast-radius` | `engineering` | Read a Terraform plan as JSON and report destroys first, with the attribute forcing each replacement. |
| `/ci-fail` | `engineering` | Classify a failing run from annotations and failed-step logs, after checking whether the default branch is red too. |
| `/weekly` | `manager` | Draft a bottom-line-first status update from merged pull requests and commits, every number sourced. |
| `/skill-doctor` | this repository | Diagnose one skill: validator findings, description health, eval-set balance, and which siblings it collides with. |

## CI is the source of truth

Every skill is validated on every push. The validator is standard library only, and the
test matrix runs it on Python 3.10 through 3.13 to keep it that way.

```bash
make validate   # frontmatter contract, dangling references, marketplace cross-check
make test       # the validator's own test suite
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
twenty queries it should fire on and near-misses it should not. The schema is checked on
every push because that is free; scoring the queries needs a model, so it runs on demand
rather than gating anything. Each query is judged against the whole catalogue of
descriptions, which is what catches a skill that fires on everything.

## Documentation

- [Writing a skill](docs/writing-skills.md) — the contract, every validator code, and how to write a description that actually triggers
- [Writing a subagent](docs/writing-agents.md) — when a subagent beats doing the work inline
- [Writing a slash command](docs/writing-commands.md) — when a command beats a skill, and why most do not
- [AGENTS.md](docs/agents-md.md) — the standard, and how it relates to `CLAUDE.md`
- [CI](docs/ci.md) — what each check means and how to make it required
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Repository conventions for agents live in [`AGENTS.md`](AGENTS.md).

## Licence

[MIT](LICENSE).
