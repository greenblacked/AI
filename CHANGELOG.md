# Changelog

All notable changes to this project are documented here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic
Versioning](https://semver.org/spec/v2.0.0.html). A release is a git tag matching
`vX.Y.Z` plus the section below it; see [releasing a
version](docs/ci.md#releasing-a-version) for how one is cut.

## [Unreleased]

- Added `docs/best-practices.md`, a status page for CI, security, and branching and
  merging practices: what each one is, why it matters, how this repository applies it
  today with a link to the file that proves it, and an honest not-yet-adopted where it
  does not.
- Added a `naming` CI job and `make naming`, checking branch names, commit subjects and
  the pull request title against the conventions `CONTRIBUTING.md` documents, plus
  every tracked skill, agent, command, reference, eval, script and doc file name
  against the convention for its category. Code identifiers are covered separately by
  ruff's `pep8-naming` rules, already running in the security lint job.
- Added a benchmark for the quality of `reviewer`'s output, under
  `.claude/agents/benchmarks/reviewer/`: eight defect cases drawn from
  `docs/review-lessons.md` and three clean ones. `scripts/run_review_benchmark.py` runs
  it headless in throwaway worktrees and reports a catch rate and a false-alarm rate,
  and a model-free drift guard in `make test` keeps every case applying to the tree. It
  needs a model and a key, so it is not a CI job.

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
