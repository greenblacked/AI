# Changelog

All notable changes to this project are documented here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic
Versioning](https://semver.org/spec/v2.0.0.html). A release is a git tag matching
`vX.Y.Z` plus the section below it; see [releasing a
version](docs/ci.md#releasing-a-version) for how one is cut.

## [Unreleased]

### Added

- Add floating Back and To top buttons on the right of every catalogue page, after
  Material Design 3's floating action button. They appear once the page has scrolled
  past its own Back button and hide again near the top, so Back is never out of reach
  on a long skill page. The front page has only To top. To top respects reduced motion
  and moves focus to the home link.
- Add a Back button to every catalogue page below the front page, a tonal pill with a
  leading arrow in the style of Material Design 3, the same shape as the Download and
  View source buttons. It returns to the previous page when that page is on this site,
  and otherwise goes to the page above: the plugin for a skill, the front page for the
  rest, the not-found page included. Without JavaScript it is a plain link to that
  page.
- Cut a release from the Actions tab. After the prepare pull request merges, running Cut
  release on `main` with a version checks it with the new `scripts/release.py check`
  (a non-empty changelog section, no such tag on `origin`, a version greater than every
  existing tag, `HEAD` equal to `origin/main`), creates the annotated tag through the API
  and dispatches `release.yml` on it. `release.yml` now also accepts `workflow_dispatch`,
  but only on a `vX.Y.Z` tag ref; its first step in each job refuses anything else.
  `make release` and a hand-pushed tag still work.
- Grow the catalogue site from one page into a full site, in a new design. The front
  page now lists the eight plugins, each linking to its own page at `/plugins/<plugin>/`
  with its skills, and each skill to a page at `/plugins/<plugin>/<skill>/` carrying its
  description, install line, allowed tools, rendered `SKILL.md`, references and the queries
  it fires on and goes elsewhere for. `/start/`, `/workflows/`, `/examples/` and
  `/quality/` add the install steps and usage guide, the shipped subagents and commands,
  example requests, and figures computed from the repository at build time; they are
  reached from the footer. The header drops the text "Black" button for a day/night
  switch and a console theme, in Instrument Sans and Newsreader loaded from Google Fonts.
  The Markdown is rendered by `scripts/site_markdown.py`, standard library only, which
  escapes all source text, shows raw HTML as text and keeps only `http`, `https`,
  `mailto`, fragment and in-repository links.
- Publish a released catalogue to Cloudflare Workers. A `vX.Y.Z` tag still cuts the
  GitHub Release, and the same workflow then uploads that version's skill archives,
  portable bundle and marketplace manifest as static assets on the Worker `ai`, served
  at `https://ai.szolotov.com` and on its `workers.dev` host. Pull requests dry-run the
  upload with no credential. A push to `stage` uploads a Preview named `stage` of the
  same Worker, served at `https://stage.ai.szolotov.com`; production keeps running the
  last tagged version. With one Worker the staging token can also deploy production,
  so `docs/ci.md` has the owner protect `stage` with a ruleset. The Cloudflare token is
  an environment secret, not a repository secret; what to create is in `docs/ci.md`.
- `scripts/smoke_site.sh` retries `version.txt` until it reports the expected version,
  so a host still serving the previous version while a deploy propagates no longer
  fails a healthy deploy.

- Add three skills to `coding` for building the environment an agent works in:
  `agent-instructions` writes or repairs a repository's `AGENTS.md` and the `CLAUDE.md`
  that imports it, and passes only when a session with no history answers five fixed
  questions from the repository alone; `agent-guardrails` turns a rule or a repeated
  agent mistake into the cheapest mechanism that enforces it, proven by failing on a real
  violation first; `agent-failure-diagnosis` attributes one recurring agent failure to
  instructions, tools, state, verification or scope and changes one thing at a time. All
  three work in Claude Code and, through the portable export or the skills directory, in
  ChatGPT and Codex. `agent-evaluation` gains a reference on removing one harness
  component at a time to see whether it still earns its place. The coding ceiling in
  `listing-budget.json` moves from 18,000 to 20,500 because three skills were added, and
  the install advice's `skillListingBudgetFraction` from 0.098 to 0.101, which the budget
  check requires at the new total. `ai-enablement` no longer claims writing an
  `AGENTS.md` in its description, and its eval query about it is now a negative owned by
  `agent-instructions`, so two descriptions do not claim one request.

- Add a bounded mock recovery runner that generates observations and final state from
  evaluator-controlled outcomes, independently of candidate tool request sequences.

- Add an offline recovery trace grader with deterministic cases for stale repository
  state, uncertain remote writes, worker quiescence and superseded generations. Its
  synthetic fixtures validate the grader rather than claiming live model performance.

- Add the `/agent-ready` command to `manager`, cloning a repository and actually running
  the fenced shell commands its `AGENTS.md` contains — after listing them and stopping for
  confirmation, and with a stripped environment, which is not a sandbox — checking the
  `AGENTS.md` chain's size against Codex's 32 KiB project-doc cap and its
  silent-truncation behaviour, and flagging the path and shape of an exposed secret before
  anyone hands the repository to an agent.
- Add the `/agent-diff-audit` command to `coding`, running mechanical detectors over an
  agent-written diff against a base ref — shrunk test counts, newly silenced checks
  including ESLint's `--suppress-all` and suppressions-file surface, and dependency lines
  that 404 against their own registry — then handing the flagged list to `code-review`.
- Add the `review-comment-miner` subagent to `coding`, reading a pile of exported PR
  review comments or postmortem action items and returning recurring clusters with an
  independent-instance count and a quoted example, leaving the choice of what a recurring
  finding becomes to whoever owns that surface. `new-skill` now hands off to it by name
  when a candidate skill comes from an uncounted backlog of complaints.
- Add the `test-history-reader` subagent to `coding`, reading hundreds of JUnit, pytest or
  `go test -json` reports across many CI runs into a flake-rate ledger for non-browser
  suites — each test's rate with its denominator, co-failure clusters, and a quarantine
  order ranked by CI time and retries burned — leaving the quarantine policy itself to
  `ci-triage`. `ci-triage` and `e2e-testing` now hand off to it by name for the bulk
  historical read.
- Add the `supply-chain-exposure-reader` subagent to `security`: given a compromised
  package, action SHA or version window, it walks lockfile git history and CI run logs
  across every repository in scope and returns which repositories, workflow runs and
  jobs actually resolved or executed the bad version, split from merely present in
  history, with the secrets each executed run's job could reach — never a secret's
  value, only its name — so the raw logs and history never enter the caller's context.
  `dependency-triage`'s cross-repository blast-radius step now hands off to it by name.
- Add the `security-test-engagement` skill to the `security` plugin, covering
  commissioning and running an authorised penetration test, red-team exercise or
  bug-bounty engagement from the asset owner's side: signed authorisation and scope
  before anything starts, rules of engagement with stop conditions, a confirmed
  emergency contact, rules for test data and accounts, and a path from each finding to a
  confirmed retest. The skill's own text carries no attack technique, tool command or
  payload. `game-day` now names it as the owner of the "security red-teaming or
  penetration testing" exclusion it already carried. Raise the `security` plugin's
  listing ceiling to 11,500 for the new skill.
- Add a `k8s-upgrade` skill to `operations`: sequence a planned Kubernetes minor
  upgrade — control plane, add-ons, node pools — finding removed and deprecated APIs
  from live traffic before the window opens rather than from git manifests, clearing
  every blocking PodDisruptionBudget before the drain, and canarying one node pool
  across a full traffic peak before rolling the rest. `k8s-triage`'s cede for a cluster
  upgrade planned in advance now names it. Raise the `operations` plugin's listing
  ceiling to 15,500 for the new skill.
- Add a `mobile-release` skill to `delivery`: stage or phase a shipped iOS or Android
  build through the app store's own rollout, where the binary itself cannot be
  recalled — an agreed crash-free halt threshold set before the rollout starts, a
  server-side flag for every risky behaviour, the API compatibility window and
  force-upgrade path for old clients, and a store rejection triaged against the
  guideline it cites. Apple's fixed phased-release schedule, its 30-day pause limit,
  its release-to-all-users override, and that a manual download always gets the
  current version are stated as fact; Play Store mechanics are left to the console,
  which the skill points at for its current staged-rollout options rather than
  assuming a schedule for Android.
  `release-strategy` and `game-certification` now cede a shipped binary's own rollout
  to it. Raise the `delivery` plugin's listing ceiling to 9,500 for the new skill, and
  `gamedev`'s to 10,500 for `game-certification`'s longer cede clause.
- Fold the `llm-model-lifecycle` idea into `agent-evaluation` as
  `references/model-lifecycle.md` rather than shipping it as its own skill, since
  `agent-evaluation`'s description already claims the release-gate act it deepens:
  pin a dated model snapshot rather than a moving alias, track a vendor's own
  retirement date on a named owner's calendar the way `certificate-automation` tracks
  a certificate's expiry, and the production drift signals — refusal rate,
  schema-violation rate, output-length distribution — to watch once a version is
  live. No new listing cost.
- Add a `schema-design` skill to `coding`: model the tables for a new feature before any
  migration exists — the query list first, a deliberate primary-key strategy, constraints
  pushed into the database, soft delete as a whole-table decision with its partial unique
  index, and every type chosen on purpose instead of inherited from an ORM default. Points
  finished DDL at `db-migration` and unresolved query tuning at `sql-performance`; those
  two skills, plus `api-design`, now cede back to it for greenfield schema work. Raise
  the coding ceiling for the new description.
- Add an `agent-delegation` skill to `coding`: brief one coding agent on one bounded task
  with a runnable done-check set before anything else, the failing evidence pasted in
  rather than described, an explicit scope fence over tests, CI config, lint and coverage
  thresholds and lockfiles, named stop conditions, and evidence required back rather than
  a claim of "done". `agent-orchestration`'s cede for "a single bounded change" now names
  it as the owner. Raise the coding plugin's listing ceiling from 16,000 to 18,000 across
  schema-design and agent-delegation.
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
- Add the `certificate-automation` skill to the `security` plugin: inventory a whole
  estate's TLS certificates from certificate-transparency logs and endpoint scans first,
  classify every endpoint by ACME capability, automate issuance and renewal on ACME
  Renewal Information with a lifetime-fraction backstop, and monitor for renewal failure —
  ahead of the CA/Browser Forum's ballot SC-081 cutting maximum certificate validity from
  398 to 200 days on 2026-03-15, 100 days on 2027-03-15 and 47 days on 2029-03-15. Raise
  the `security` plugin's listing ceiling accordingly. The `operations` plugin's ceiling
  and `game-live-ops`'s recorded description length also moved in this run of
  `check_listing_budget.py --update`: both are the script recomputing every plugin's
  ceiling and every skill's recorded length from what is actually on disk today, not a
  change made to either skill.
- Add an `incident-response` skill to `operations`: platform-agnostic incident command,
  severity and mitigation-by-symptom for a live production incident on any surface — a
  managed database, a third-party dependency, a VM fleet, serverless, a CDN or DNS
  provider — with `references/incident-command.md` moved from `k8s-triage`, which now
  hands off to it for anything that is not a Kubernetes workload. Raise the `operations`
  plugin's listing ceiling to 14,500 for the new skill and the cedes retargeted at it.
- Add `.github/workflows/ci-triage.yml` and `scripts/ci_triage.py`, a Python port of
  `greenblacked/status-page`'s `ci-triage.cjs`: on a pull request's `CI` or `Security`
  run completing, keep one self-updating comment naming each failed job, its failed
  step and a likely local command, with a `ci-failed` label kept in step with it. Reads
  only run, job and step metadata through the GitHub API, checks out only the default
  branch, and never touches the pull request's head.

### Changed

- Verify Terraform backend/provider identity and the live Kubernetes target before
  state operations or incident mutations. Bind review evidence to remote revision
  identities or a recorded local tree, and recheck freshness before the verdict.

- Align live agent task and runtime status records, check ownership overlaps before
  dispatch, and filter untrusted worker evidence before relaying it. Add a copyable
  checkpoint and successor receipt for interrupted work.
- Cover delegated agent output in security review and distinguish candidate-caused
  permission failures from evaluation infrastructure outages.
- Clarify that ambiguous GitLab publication failures require reconciliation before a
  write retry, even when the failure appears transient.

- Point terminal-agent AGENTS.md advice at the new router instead of a whole plugin
  bundle or `index.md`, in `docs/using.md`, `README.md` and the portable export's own
  shipped README: both are far past Codex's 32 KiB `project_doc_max_bytes` default,
  which truncates silently past that budget.
- Add a cede clause to `secret-rotation`'s description pointing scheduled renewal or an
  ACME rollout at the new `certificate-automation` skill — a genuine routing boundary
  between the two, not a change made to pass a check. Trimmed repeated filler
  ("provider", "whenever") elsewhere in the same description to keep it clear of the
  validator's headroom warning; its recorded length moved from 967 to 973 characters
  accordingly, and the `security` plugin stays well under its 11,000 ceiling at 10,473.
- Narrow `k8s-triage` to Kubernetes workload symptoms: drop its "or a live production
  incident" claim and the generic declare, comms-cadence, handoff and
  mitigated-versus-resolved steps, each replaced with a pointer to the new
  `incident-response` skill, which now owns them for every surface, Kubernetes included.
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
- Record the security settings as of 2026-10-03: the owner re-confirmed secret scanning,
  push protection, Dependabot alerts and Dependabot security updates, and private
  vulnerability reporting is confirmed on from the public API. Record that CodeQL runs
  from `security.yml`'s `codeql` job and that GitHub's default setup must stay off, since
  the two cannot both upload; `SECURITY.md` and the README now name these controls too.
  Stop claiming that Dependabot alerts cover what is pinned here: GitHub raises none for
  an action pinned by SHA, which every action here is, nor for a tool pinned in a
  workflow variable, and `pyproject.toml` declares no runtime dependencies, so
  `.github/dependabot.yml`'s version updates are what keep actions current. Name the
  unpinned `hatchling` build backend as the one package no update covers.
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

- Stop `scripts/run_review_benchmark.py --jobs` from failing at random when two cases
  create their worktrees at once. `git worktree add` and `remove` now run one at a
  time under a lock, each worktree gets a unique name, and a failed `add` reports git's
  own message instead of only its exit status.
- Smoke-test releases and the stage Preview through `workers.dev` instead of the custom
  domain. Bot Fight Mode on the zone answers GitHub runners with a 403, which rolled
  production back on `v0.1.0` twice, and it cannot be skipped by a WAF rule. The
  blocking check is now `scripts/smoke_site.sh` against the Worker's `workers.dev`
  address plus a read of `wrangler deployments status` (`read_wrangler_deploy.py
  --active-is`) showing the deployed version at 100%, and the deploy must list
  `ai.szolotov.com (custom domain)` as a target. The custom-domain request is logged
  for information and cannot fail the job.

- Stop the stage Preview from fetching stage pages. Stage is behind Cloudflare Access,
  which serves a GitHub runner its login page or a redirect to it, so the `workers.dev`
  smoke failed every stage deploy. The `preview` job now checks only that `wrangler
  preview` uploaded and reported `https://stage.ai.szolotov.com`.

- Stop a pull request description edit from leaving a red `ci` on the head commit. An
  `edited` event no longer cancels the run in flight, which the `ci` gate counted as a
  failure, and the `attribution` and `naming` jobs read the title and body from the API
  when they run, with `pull-requests: read`, instead of from the event payload frozen at
  the moment the run was triggered.
- Roll a failed production release back to the version that was serving before it. The
  `cloudflare` job now records that version with `wrangler deployments status --json`
  before deploying and passes its ID to `wrangler rollback`; without one, Wrangler picks
  the version uploaded before the newest, which after an earlier failed release is that
  failed release.
- Correct the initial catalogue's unpublished release claim and link to its immutable
  commit, keeping first-release preparation compatible with that comparison baseline.
- Refresh the Claude Code, Codex and Gemini CLI pins. Set the Claude trigger classifier's
  permission mode explicitly to `dontAsk` so the CLI's changed default cannot enable
  automatic approvals. Codex's unspecified model now defaults to GPT-6.1 Sol; compare
  eval runs only with the same explicit model and rerun both baseline and candidate.

- Bind recovery fences and late commits to submission attempt identities, so delayed
  notifications cannot authorize a retry of a newer pending request.

- Compare recall, specificity and expected-neighbour routing alongside aggregate rate
  in trigger-eval baseline reports, including legacy reports with missing metrics.

- Give `ci-triage.yml`'s job `pull-requests: write` alongside `issues: write`, rather
  than `issues: write` with `pull-requests: read`: a live run's first write, the
  triage comment, returned a 403 under the narrower grant, since `GITHUB_TOKEN` needs
  `pull-requests: write` to comment on or label a pull request regardless of GitHub's
  published endpoint data listing those endpoints under "Issues *or* Pull requests".
  `issues: write` stays, since creating the `ci-failed` label the first time a pull
  request needs it — the label does not exist until then — needs that grant
  separately from labelling with it once it exists.

## [Initial catalogue] - 2026-09-24

Initial catalogue snapshot; no release tag has been published. The catalogue at this commit:

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

[Unreleased]: https://github.com/greenblacked/AI/compare/9365d19bd40e79f52463b046927b17cfd448bb79...HEAD
[Initial catalogue]: https://github.com/greenblacked/AI/tree/9365d19bd40e79f52463b046927b17cfd448bb79
