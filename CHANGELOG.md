# Changelog

All notable changes to this project are documented here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic
Versioning](https://semver.org/spec/v2.0.0.html). A release is a git tag matching
`vX.Y.Z` plus the section below it; see [releasing a
version](docs/ci.md#releasing-a-version) for how one is cut.

## [Unreleased]

### Added

- Add `router.md` and one `router-<plugin>.md` per plugin to the portable export: a
  line per skill naming when it applies and the `skills/<name>.md` path to open then,
  sized to fit inside a terminal agent's own document budget rather than a whole
  bundle. `scripts/export_portable.py` fails the export before writing anything if a
  router grows past `ROUTER_BUDGET_BYTES`.
- Add the `page-history-reader` subagent to `operations`, reading a quarter of pager or
  alert history — PagerDuty, Opsgenie, Grafana OnCall or Cloud IRM, a Prometheus `ALERTS`
  range query, or a plain CSV — and returning per-rule fires, action rate, off-hours share
  and a suggested keep/tighten/demote/delete bucket for `alert-design`'s step 10, so the
  raw export never enters the caller's context.
- Add `.github/workflows/ci-triage.yml` and `scripts/ci_triage.py`, a Python port of
  `greenblacked/status-page`'s `ci-triage.cjs`: on a pull request's `CI` or `Security`
  run completing, keep one self-updating comment naming each failed job, its failed
  step and a likely local command, with a `ci-failed` label kept in step with it. Reads
  only run, job and step metadata through the GitHub API, checks out only the default
  branch, and never touches the pull request's head.

### Changed

- Point terminal-agent AGENTS.md advice at the new router instead of a whole plugin
  bundle or `index.md`, in `docs/using.md`, `README.md` and the portable export's own
  shipped README: both are far past Codex's 32 KiB `project_doc_max_bytes` default,
  which truncates silently past that budget.
- Retry the actionlint and gitleaks downloads in `ci.yml` and `security.yml` on a
  transient network failure, with a 20-second connect timeout and a 60-second cap
  applied per attempt rather than libcurl's 300-second default, so the worst case of
  four attempts stays inside the five-minute job timeout; drop the thirteen
  fast-finishing jobs across both workflows from a ten-minute to a five-minute timeout,
  so a hang there is caught sooner; and add a `concurrency` group to
  `dependabot-auto-merge.yml`, the one workflow that had none, so a second push cancels
  a stale, still-idempotent run instead of racing it.
- Add `--retry-max-time 150` to the same two curl calls: `--retry` honours a server's
  `Retry-After` header and `--max-time` only bounds a single transfer, not the wait
  between retries, so a 429 or 503 with a long enough `Retry-After` could otherwise still
  run past the job's five-minute `timeout-minutes` even with every other cap in place. No
  retry is scheduled after 150 seconds, so the last attempt finishes within the job
  timeout regardless of what a server asks for.
- Re-run `ci.yml` when a pull request's title, body or base branch is edited, so the
  `naming` and `attribution` jobs check the current text instead of leaving a stale
  result standing.
- Define the GitHub pull request review thread lifecycle for findings, replies and resolution.
- Bring the README's CI section and documentation list, and CONTRIBUTING.md's pre-PR
  command list, up to date with the naming and attribution checks, the review
  instructions doc and the settings GitHub records outside this tree.
- Record that the owner enabled GitHub's native secret scanning, push protection,
  Dependabot alerts and Dependabot security updates on 2026-09-26, alongside the existing
  CI checks rather than in place of them, in `docs/ci.md`'s settings section and
  `docs/best-practices.md`'s status tables.
- Stop `docs/ci.md` and `CONTRIBUTING.md` from implying `make naming` and `make
  attribution` check the pull request title and body locally: the Makefile targets never
  set `PR_TITLE` or `PR_BODY`, so only CI checks them, once the pull request exists.
- Give the README a centred header with a navigation line, and collapse the provider
  comparison table behind a `<details>` toggle.
- Add a light and dark banner (`docs/assets/banner-light.svg`,
  `docs/assets/banner-dark.svg`) above the README's header, switching with the reader's
  GitHub theme via the `<picture>` pattern.
- Extend `/ship` to run `explorer` and, when the change rests on an outside claim,
  `investigator` in parallel for the survey stage, then merge the reviewed change itself
  once `reviewer`, `ci` and `security` pass, rather than stopping at judgement; move
  `implementer` and `investigator` off Opus onto Sonnet, with `effort` set per stage
  (`implementer` high, `explorer` and `investigator` medium); widen
  `docs/review-lessons.md`'s ledger to any review of a change here — the review stage, an
  automated PR reviewer, or a live run — and add a live-run trigger to `AGENTS.md`'s
  Review guidelines for a workflow `permissions:` change, a new API write in a shipped
  script, or a `workflow_run`/`schedule`/`pull_request_target` trigger.

### Removed

- Remove Bifrost, and OpenRouter as a general-purpose gateway, from the provider table,
  `docs/deepseek.md` and `providers.json`. OpenRouter stays as the one documented route
  to a DeepSeek model, for Claude Code only.

### Fixed

- Give `ci-triage.yml`'s job `pull-requests: write` alongside `issues: write`, rather
  than `issues: write` with `pull-requests: read`: a live run's first write, the
  triage comment, returned a 403 under the narrower grant, since `GITHUB_TOKEN` needs
  `pull-requests: write` to comment on or label a pull request regardless of GitHub's
  published endpoint data listing those endpoints under "Issues *or* Pull requests".
  `issues: write` stays, since creating the `ci-failed` label the first time a pull
  request needs it — the label does not exist until then — needs that grant
  separately from labelling with it once it exists.

## [1.0.0] - 2026-09-24

First tagged release. The catalogue at this tag:

- **89 agent skills** across eight plugins you install separately: `coding` (18 skills,
  3 subagents), `gamedev` (11 skills, 1 subagent, 1 command), `operations` (15 skills, 5
  subagents, 2 commands), `delivery` (9 skills, 1 subagent), `security` (11 skills, 3
  subagents, 2 commands), `manager` (13 skills, 2 subagents, 1 command), `personal` (7
  skills, 2 subagents) and `career` (5 skills).
- **Seventeen read-only subagents** shipped across seven of those plugins, each denied
  the tools it should not have, plus four more in `.claude/agents/` that ship to nobody
  and only run the two loops this repository uses on itself.
- **Six slash commands** shipped across four plugins, plus six more in
  `.claude/commands/` for working on this repository.
- **`skillcheck`**, the standard-library-only validator behind `make validate`: it
  checks frontmatter, dangling `references/` pointers, trigger eval sets and the
  marketplace manifest, and runs on Python 3.10 through 3.13.
- **A portable export** (`make portable`) that flattens every skill into a file any
  assistant that reads text can use, for ChatGPT, Grok, Codex and anything else with no
  skills loader of its own.
- **CI and Security gates**: `ci` validates, tests, lints and packages; `security` runs
  gitleaks, zizmor, ruff's flake8-bandit rules and CodeQL. Both are required checks on
  `main`.
- **Licence notice in every distributed artefact**: each `.skill` archive carries a
  `LICENSE.txt` and a `NOTICE.txt` beside `SKILL.md`, and the portable export carries
  `LICENSE` and `NOTICE` at its root and a short copy of the notice at the foot of every
  skill file and plugin bundle. The copyright notice names Serhii Zolotov (GitHub:
  greenblacked).

[Unreleased]: https://github.com/greenblacked/AI/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/greenblacked/AI/releases/tag/v1.0.0
