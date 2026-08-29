# AI

Agent skills and subagents I use daily, kept in one place and validated by CI.

A skill is a Markdown procedure an agent loads when it recognises the situation. Most of
what is here comes out of platform and DevOps work — triaging a red pipeline, reading a
Terraform plan properly, getting a broken workload back before diagnosing it, hardening a
container image — plus the leadership side of the same job and a few personal ones.

Nothing here is a wrapper around a model's general knowledge. The useful part of a skill
is the opinionated part: the gate that stops you, the ordering that saves an hour, the
command with the flag that actually produces the evidence.

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
| [`ci-triage`](skills/engineering/ci-triage/SKILL.md) | Classify a red pipeline before debugging it — real failure, flake, runner, config, or dependency drift — starting with whether the default branch is already broken. Quarantine policy and retry hygiene included. |
| [`code-scaffold`](skills/engineering/code-scaffold/SKILL.md) | Write new code that survives a 3am cron run: strict error handling, meaningful exit codes, structured logging, validated input, idempotent re-runs. |
| [`iac-review`](skills/engineering/iac-review/SKILL.md) | Review a Terraform change against the plan JSON rather than the plan text, so replacements and destroys surface first instead of being skimmed past. |
| [`image-hardening`](skills/engineering/image-hardening/SKILL.md) | Build or audit a container image: minimal base, digest pinning, numeric non-root UID, no secrets in layers, SBOM, a scan gate that will not get bypassed, signing that is actually verified. |
| [`k8s-triage`](skills/engineering/k8s-triage/SKILL.md) | Mitigate first, diagnose second. The deploy-related question, the fixed evidence order, and a decode table for the failure modes that account for most of them. |
| [`website-builder`](skills/engineering/website-builder/SKILL.md) | Build a site that looks designed for its subject and can still be hosted and maintained afterwards — or audit one that already exists. |

### Manager

| Skill | What it does |
| --- | --- |
| [`ai-enablement`](skills/manager/ai-enablement/SKILL.md) | Assess how a team actually uses AI-assisted engineering and produce a rollout plan, including the metrics that help and the ones that quietly destroy honest feedback. |
| [`decision-record`](skills/manager/decision-record/SKILL.md) | Turn a decision into a MADR-format ADR or a design doc, with at least two genuinely considered options and a confirmation step that names a real check. |
| [`delivery-review`](skills/manager/delivery-review/SKILL.md) | Read delivery health honestly: DORA as a property of the system rather than of people, flow and queue time, and prioritisation frameworks applied only where they belong. |
| [`postmortem`](skills/manager/postmortem/SKILL.md) | Write a blameless postmortem in the Google SRE shape, where "human error" is a prompt for a better question and every action item has an owner. |
| [`status-update`](skills/manager/status-update/SKILL.md) | Bottom line up front for status, Minto for persuasion, and never the two mixed. Numbers are sourced or marked as missing. |

### Personal

| Skill | What it does |
| --- | --- |
| [`health-coach`](skills/personal/health-coach/SKILL.md) | Estimate calories and macros from a photo or a description, as a range with the uncertainty named, then suggest one thing worth changing. |
| [`job-search`](skills/personal/job-search/SKILL.md) | Tailor a CV and prepare for interviews from a real history. Selection and evidence, never embellishment. |
| [`learning-notes`](skills/personal/learning-notes/SKILL.md) | Turn something read into a note that is still useful in a year, on the principle that a summary is not a note. |

## Subagents

`agents/` holds four subagents that exist to keep bulk out of the main context and to be
denied tools they should not have: `ci-log-reader` reads a failing run and returns a
classification, `plan-reviewer` reads a Terraform plan and returns the blast radius,
`incident-scribe` turns triage notes into a postmortem draft, and `skill-reviewer` audits
a candidate skill against this repository's rules.

## CI is the source of truth

Every skill is validated on every push. The validator is standard library only, and the
test matrix runs it on Python 3.10 through 3.13 to keep it that way.

```bash
make validate   # frontmatter contract, dangling references, marketplace cross-check
make test       # the validator's own test suite
make package    # a .skill archive per skill
```

Subagents are held to the same contract, and every skill carries a trigger eval set —
twenty queries it should fire on and near-misses it should not. The schema is checked on
every push because that is free; scoring the queries needs a model, so it runs on demand
rather than gating anything. Each query is judged against the whole catalogue of
descriptions, which is what catches a skill that fires on everything.

The check that earns its place is the dangling-pointer one. Two of these skills shipped
for months naming `references/*.md` files nobody had written — the model loaded nothing
where it expected depth, and no error was ever raised. CI now fails on it.

Alongside `ci`, a `security` gate runs gitleaks over the working tree and history, zizmor
over the workflows themselves, ruff's flake8-bandit rules, CodeQL, and two invariants:
every workflow declares a `permissions:` block, and every action is pinned to a commit
SHA.

## Documentation

- [Writing a skill](docs/writing-skills.md) — the contract, every validator code, and how to write a description that actually triggers
- [Writing a subagent](docs/writing-agents.md) — when a subagent beats doing the work inline
- [AGENTS.md](docs/agents-md.md) — the standard, and how it relates to `CLAUDE.md`
- [CI](docs/ci.md) — what each check means and how to make it required
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Repository conventions for agents live in [`AGENTS.md`](AGENTS.md).

## Licence

[MIT](LICENSE).
