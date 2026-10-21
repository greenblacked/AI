# Changelog

All notable changes to this project are documented here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic
Versioning](https://semver.org/spec/v2.0.0.html). A release is a git tag matching
`vX.Y.Z` plus the section below it; see [releasing a
version](docs/ci.md#releasing-a-version) for how one is cut.

## [Unreleased]

### Added

- Add the `llm` plugin for building features on language models, with five skills:
  `rag-design` (a retrieval pipeline shown to retrieve the right passages, with a small
  labelled eval before tuning, permission filtering and refusal on weak retrieval),
  `structured-output` (the schema as contract, the provider's native or strict mode,
  validation in code and a bounded repair loop that fails closed), `mcp-server-design`
  (task-shaped tools, `isError` results, transport and authorisation choices, and a
  `tools/list` snapshot test), `document-extraction` (values read from scans and photos
  with source region, confidence and independent cross-checks) and `model-migration`
  (a retirement or upgrade carried out against a frozen baseline, a canary and a decision
  record). Its listing ceiling in `listing-budget.json` is new, set at 5,000 characters
  for these five skills, so the plugin fits the runtime's default listing budget; the
  catalogue site gives it a page, its own look and an introduction.
- Add seven skills: `data-visualisation` and `visual-review` to `design`, for turning data
  into a readable chart and for reviewing a rendered page from screenshots without trusting a
  vision model for what code can measure; `architecture-diagrams` and `feature-spec` to
  `coding`, for diagrams drawn as code that renders where it is read and for a written spec
  and checkpointed plan before any code; `agent-extension-audit` to `security`, for vetting a
  third-party skill, plugin, hook or MCP server before installing it; and `game-localisation`
  and `game-playtest` to `gamedev`, for taking a game to many languages and for running a
  playtest that ends in decisions.
- Add three subagents: `screenshot-reader` to `design`, which reads screenshots in its own
  context and returns findings by file and region; `extension-reader` to `security`, which
  reads a quarantined third-party extension without running it; and `llm-trace-reader` to
  `operations`, which reads an LLM usage or trace export for cost and latency hotspots.
- Add the `/visual-review` command to `design`, which runs the `visual-review` procedure on a
  page and hands crops to `screenshot-reader`.
- Add reference files to existing skills: a charts and graphics reference to
  `accessibility-audit`, an injection architecture reference to `agent-security-review`, a
  judge calibration reference to `agent-evaluation`, a visual snapshots reference to
  `e2e-testing`, a test-first loop reference to `test-design`, and a telemetry, caching and
  limits reference to `llm-cost`.
- Draw each plugin page's skill to subagent routing as an inline SVG graph at build
  time. The `family` page keeps its own workflow layout and has no graph yet. An edge is
  a subagent's name shown as inline code on the skill's rendered page, outside code
  blocks. Names after a "Not for" or "Do not use for" phrase in the same paragraph or
  list item draw no edge, so the graph is derived from the files and cannot drift from
  them. A name shipped by two other plugins draws no edge.

### Changed

- Accept `release/` as a branch type, for a promotion from `dev` into `stage` or from
  `stage` into `main`, so a promotion no longer has to borrow `chore/`.
- Split the portable router into a per-plugin index once the combined `router.md` would
  exceed its size budget. `router.md` then lists one `router-<plugin>.md` per plugin,
  each keeping every skill's full trigger and each checked against the same budget; the
  budget and the per-entry trigger cap are unchanged. The combined router sat 16 bytes
  under the budget, so any new skill would have overflowed it.
- Route model moves to `model-migration`. `agent-evaluation` now cedes planning a move to
  another model to it, and two queries about swapping a model or an alias that
  `agent-evaluation`'s trigger set listed as positives are now negatives owned by
  `model-migration`. Two distant negatives (profiling and codebase-orientation) were
  dropped, which takes the set from twelve positives and ten negatives to ten a side, so
  earlier trigger scores for `agent-evaluation` are not comparable and need a rerun on the
  revised set. This is a routing correction, not a change to make a check pass. The `llm` skills also name each other as owners in their
  descriptions and trigger sets, and `ai-enablement`'s RAG negative now names `rag-design`.
- Narrow `game-balance` to tuning numbers from playtest evidence. Running a playtest session
  now belongs to `game-playtest`, so the balance skill's playtest protocol is replaced by a
  short reference on carrying a playtest finding into a hypothesis about a number. This is a
  routing correction for the new skill, not an edit made to pass a check.
- Raise the skills badge, the plugin counts and the recommended
  `skillListingBudgetFraction` (0.123 to 0.134) for the new skills.
- Raise the `coding`, `design`, `gamedev` and `security` listing ceilings in
  `listing-budget.json` because this change adds skills to each: `architecture-diagrams`
  and `feature-spec` to `coding`, `data-visualisation` and `visual-review` to `design`,
  `game-localisation` and `game-playtest` to `gamedev`, and `agent-extension-audit` to
  `security`. The `llm` plugin gets its first ceiling.

### Security

- Run Playwright and Jest from the project's own `node_modules/.bin` in `ui-ux-review`,
  `e2e-testing`, `test-design` and `ci-triage`, not through `npx`. When a package is not
  installed locally and standard input is not a terminal, npm assumes `--yes` and `npx`
  installs and runs whatever the registry serves at that moment. The `ci-triage` bisect
  probe now skips a commit whose lockfile has no test runner instead of fetching one, with
  tests for its exit codes, and `ui-ux-review`, `e2e-testing` and `test-design` drop the
  `Bash(npx:*)` pre-approval that only these commands used.
- Remove the last `npx` calls from the skills. `accessibility-audit` and
  `website-builder`'s audit references install their audit tools at exact versions into
  a directory outside the audited project, with a version-controlled lockfile and
  `--ignore-scripts`, then call that directory's binaries against an installed browser. Prisma, Wrangler and
  jscodeshift run from the project's own `node_modules/.bin`, and the deploy job in
  `website-builder`'s example pipeline installs from the lockfile before calling
  Wrangler. The retired `observatory-cli` gives way to MDN's HTTP Observatory, and
  `accessibility-audit` drops `Bash(npx:*)`, and `website-builder` and `game-builder`,
  whose improve modes read a site or a game someone else wrote, now pre-approve only
  `Read`, `Grep` and `Glob`, so every command, fetch and write asks first.

## [0.1.12] - 2026-10-19

### Security

- Treat a contributor's `AGENTS.override.md`, and any name Codex's
  `project_doc_fallback_filenames` setting lists, as an instruction file in the review
  contract, the same as `AGENTS.md`. Codex loads the override in preference to
  `AGENTS.md` in the same directory and reads configured fallbacks after it, but the
  inert-path allowlist and the blocking-finding rule named neither, so a
  `docs/AGENTS.override.md` was read as inert Markdown and could reach the gate
  worktree.
- Make deleting an instruction file, or renaming one away, a blocking finding on a
  contributor change in the review contract, the same as adding or editing one. The
  rule said only "adds or edits", so a deletion of `CLAUDE.md` or of a `.claude/` path
  was left to the owner-must-run flow, whose checklist the owner can clear. The reviewer
  role card in `docs/chatgpt-agents.md` now states the same rule beside its own inert-paths
  list, and the sentence in `reviewer.md`, `docs/chatgpt-agents.md` and `docs/using.md`
  that sent dot-prefixed `.claude/` paths to the owner-must-run flow now makes them a
  blocking finding, leaving only paths such as `.github/` to that flow.
- Require the owner who starts a contributor review to state the resolved
  `project_doc_fallback_filenames` list, read from their own trusted Codex configuration
  and given as a list, `[]` when empty, in the brief. The contract named the setting but not its values,
  which live outside the repository, so a contributor's `docs/TEAM_GUIDE.md` was still
  inert prose when the reviewer's configuration listed `TEAM_GUIDE.md`. The reviewer now
  treats a changed path whose basename matches a stated name, at any depth, as an
  instruction file under the same blocking rule, takes the list from nothing in the
  contributor's branch, and stops and asks when the brief does not state it rather than
  assuming it empty. Every instruction-file name, the fixed ones and the stated
  fallbacks alike, is compared case-insensitively, because a case-insensitive checkout (default macOS and Windows)
  loads `docs/team_guide.md` where `TEAM_GUIDE.md` is configured, and `claude.md` as
  `CLAUDE.md`, which an exact-case comparison read as inert Markdown.

## [0.1.11] - 2026-10-18

### Fixed

- Correct stale technical claims across the coding skills: the `Deprecation`,
  `Sunset` and `RateLimit` headers in api-design, the Playwright version and flake
  count in e2e-testing, the OpenAI evaluation reference in agent-evaluation, what a
  `PostToolUse` hook can stop, staticcheck's SA1019, and the refactoring research
  citation.
- Pin website-builder's CI example to commit SHAs with read-only permissions, job
  timeouts, and have its Lighthouse job audit the build it deploys.
- Give website-builder the `Scope` section its siblings have, note the macOS
  alternatives to `flock` and `sha256sum`, and keep agent-delegation's brief template
  in one place.

### Changed

- Give each plugin page on the catalogue site its own look: the plugin name in large
  coloured capitals with its own entrance, from typed keys for coding to a lifting
  redaction for security, and a coloured accent bar on every skill row. Palettes hold
  4.5:1 contrast in day and night, collapse to one colour in the console theme, and the
  heading is whole when motion is reduced.
- Make the gamedev prototype a written handoff: `game-greenlight` hands `game-builder`
  a brief with the riskiest question, scope, budget and go, no-go and pivot criteria;
  `game-builder` builds to it rather than offering fresh concepts and reports evidence
  against each criterion, keeping a build, a self-playtest and watched players apart.
  A criterion nobody could test is reported unverified or blocked, and `/level` carries
  that status through its stages instead of treating it as passed.
- Add worked examples and concrete numbers to the coding agent skills: a task-graph
  example in agent-orchestration, a filled checkpoint contract in agent-handoff,
  rerun counts in agent-failure-diagnosis, and delegation sizing figures.
- Show the per-worker `storageState` fixture in e2e-testing's Playwright reference so
  the worker-scoped session is concrete, and fold application-caching's duplicated
  rollout and rollback steps into its failure-and-rollout reference.

### Security

- Install the eval CLIs from committed, integrity-locked npm trees with lifecycle
  scripts disabled, in a step that holds no model credentials. Previously a package
  install script ran in, or on the same runner state as, the step that held the API
  keys.

## [0.1.10] - 2026-10-15

### Changed

- Document merging `main` back into `dev` after every release, so dev carries the
  dated changelog and the action bumps that land only on `main`. When `dev` has moved
  on since the release, the difference from `main` is the unreleased `dev` work, which
  stays.

## [0.1.9] - 2026-10-15

### Added

- Smooth the day and night switch: the new theme now spreads from the switch with a soft,
  feathered edge on a gentler curve, the knob glides across while the sun turns into the
  moon, and a browser without view transitions cross-fades the colours instead of
  jumping. A second press while the first reveal is still finishing keeps its own soft
  edge. With motion reduced the theme still changes at once.
- Give the catalogue site one motion language. Pages rise in under a steady header as
  you move between them; a theme chosen by hand spreads out from its switch; header and
  footer links draw their underline from the left; a skill row slides and shows an arrow
  on hover; buttons, chips and pills lift and press; a choice in the profile picker or
  the checklist ticks in; rows the finder brings back fade in; the front page's plugins
  rise as they scroll into view; and opening a FAMILY stage grows the panel, fades its
  lines in turn, pops the letter and tints the stage in its own colour. Every movement
  sits behind `prefers-reduced-motion`; the cues themselves (the underline, the arrow,
  the open stage's tint) show either way.
- Add an offline page and a service worker to the catalogue site. `/sw.js` keeps the
  pages a visitor opens (a plain 200 HTML response only, never a redirect, so Cloudflare
  Access's sign-in is never stored), serves them again when the connection is lost, and
  shows `/offline/` for anything else, which also lists the pages saved on the device.
  The caches are named for the build and the last sixty pages are kept; `_headers` serves
  the worker with `no-cache`.
- Add four skills: `retrieval-evaluation` to `coding` for judging a retriever or ranking
  change against a reproducible benchmark; `feature-flag-lifecycle` and
  `safe-backfill` to `delivery` for wiring and retiring a flag once the rollout is
  chosen and for a checkpointed one-off data repair; and `problem-validation` to `design` for testing
  whether a problem is real before anything is built.
- Merge the `family` plugin page into `/family/`: one page with the typed heading, the
  install command, a profile picker that highlights the stages a role owns, each stage as a
  disclosure naming its agent, verdicts and next hop, a slice checklist kept in the
  browser, the skills with search and the subagents. `/plugins/family/` redirects there,
  and `/family/example/` walks one real slice through all six stages.
- Add the `/family:family` command to the `family` plugin: it frames a request into
  `docs/slices/<name>/frame.md` with the stage templates beside it, prints the next hop and
  stops. `family-workflow` gains the slice-folder convention and a pull request template
  with one label per stage.
- Replace the site's plain "Not found" page with a 404 that types its own number in, in
  three of the FAMILY stage colours, shows the address that was asked for, and suggests up
  to three real pages when it is a near miss, so `/statr/` or `/family-workflw/` offers
  the page that was meant. Home, Start, a search of the catalogue and FAMILY are always
  there, and with scripts off the page is the heading, a sentence and those links.
- Add error pages for 403, 500, 502 and 503 at `/errors/403` and so on, each one file with its styles
  and script inline and nothing loaded from anywhere, so a host can show one in place of
  a failing page. Each has its own effect: a lock that closes, digits that shake, a link
  that drops signal, and a slow progress pulse for maintenance; the 5xx pages have a
  Retry button. They follow the system's light or dark scheme or the choice made on the
  site, stop all motion when it is reduced, and are marked `noindex`.

### Changed

- Serve the website's two typefaces, Instrument Sans and Newsreader, from its own domain
  instead of Google Fonts: no request leaves for a font host, and the files are cached for
  a year under names that carry a hash of their bytes. Both are under the SIL Open Font
  License 1.1, whose text ships beside them and is named in `NOTICE`. Wrapping a bare web
  address in rendered prose, which ran past a 360 px screen once the real serif was
  measured, is fixed with it.
- Redraw the site's tab and home-screen icons as bold cyan "AI" letters on a navy tile,
  so the letters stay sharp at a browser tab's 16 pixels instead of shrinking the crystal
  picture into a blur.
- List the `family` plugin second, right after `coding`, in the marketplace manifest, the
  README and the website, instead of last.
- Write each portable router row as a plain `skills/<name>.md` path and its trigger,
  without the list marker and colon, so `router.md` stays inside its size budget with
  four more skills.
- Separate qualitative from quantitative reads in `information-architecture`'s guidance
  on card sorts and tree tests: five to fifteen participants finds groupings and wrong
  turns, but a tree test's success rate, or a comparison between two trees, needs a
  study sized for the margin it reports.
- Say in `frame-claim-ledger` why its `Agent` grant stays unscoped: the plugin ships no
  research agent, so the claim agent is whichever read-only one the session has, and
  naming one would refuse the rest. The claim brief now tells every agent to write no
  file and run nothing that changes the checkout, since one that holds `Bash` can write
  without an editing tool.
- Build on `dev` in `/ship`: it branches from `origin/dev`, opens its pull request into
  `dev` and squash-merges there, `reviewer` measures an owner change against
  `merge-base HEAD origin/dev` by default, and `CONTRIBUTING.md` says to branch from
  `dev`. `stage` and `main` take only promotions, so a branch cut from `main` missed
  everything `dev` had not promoted yet.
- Prepare a release on the promotion branch from `stage` into `main` instead of a separate
  pull request: `make release-prepare` dates the changelog there, so after that one merge
  Cut release runs straight from `main`.

### Fixed

- Keep the FAMILY page's verdict routes to the routing contract: `FRAMED` and `PROPOSED`
  now go through the main conversation, which accepts the slice or the approach first,
  and `PASS` reaches launcher only once the Inspect owner answers the go or no-go.
- Stop the FAMILY page calling its stage agents read-only: the inspector can run
  commands, so the page now says they have no editing tools and that the inspector runs
  checks only on a change the owner wrote, as the `family-workflow` skill already does.
- Stop the README calling the subagents read-only: some hold `Bash`, so it now counts
  them as subagents and says each FAMILY stage agent has no editing tools, as the site does.
- Run `make naming` and `make attribution` against `origin/dev`, the base a feature pull
  request targets, as CI does; they diffed against `origin/main`, so every commit on `dev`
  not yet promoted was checked as the branch's own. A promotion passes its own base,
  `make naming BASE=origin/main`. `check_attribution.py`'s default range follows.
- Stop a FAMILY stage row from vanishing for a second when it is opened and then left:
  its entrance animation no longer replays when focus moves away.
- Split field labels and error messages between `form-design` and `content-design`.
  `form-design` owns which fields a form asks for, their order, when it validates, where
  an error appears and the keyboard flow; `content-design` owns the words. Each now names
  the other in its description and scope, and each eval set routes a near miss to the
  other.
- Name `family` in `docs/writing-skills.md`'s list of the ten plugins and give it a row
  in `AGENTS.md`'s layout table; a test now checks both against the marketplace manifest.
- Describe the `family` stage agents as having no editing tools rather than as
  read-only in `family-workflow`: `inspector` holds `Bash` and can run commands, which
  it does only on a change the owner wrote.
- Ship each `family` stage agent with the tier `stage-tiering` states: `framer`,
  `maker`, `launcher` and `yielder` on `sonnet` at medium effort, `architect` and
  `inspector` on `opus` at the tool's default effort. Without a `model` line every stage
  ran on the main conversation's model. `stage-tiering` no longer tells you to edit the
  installed plugin, which an update replaces, and drops its `Edit` grant.
- Use the inspector's own meaning of `STOP` in `family-relay`'s routing reference and
  `fresh-inspector-rounds`' round protocol: the frame supplied no success criterion, and
  a person supplies one. A change the owner did not write is a `FIX`, not a `STOP`.
- End each `family` stage agent's return block with a `### Handoff` section naming the
  first question for the next stage and its owner. `family-relay` passes the next hop
  only that section, and no agent returned one. `fresh-inspector-rounds`' copy of the
  inspector's return block carries it too.
- Say in `/ship` that the trusted checkout for a contributor review sits exactly at the
  pinned base, as a clone checked out there or a detached worktree, since `reviewer`
  stops when `HEAD` is anything else.
- Have `reviewer` resolve `refs/review/<n>` to one validated commit SHA before reading a
  contributor's change, and use that SHA in every later diff, show and merge, so a forced
  re-fetch of the ref mid-review cannot change what is read, gated or merged.
- Stop counting a contributor's `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` or anything
  under a `.claude/` segment as inert Markdown in the review allowlist. Those files load
  as instructions wherever a session opens, so `reviewer` now treats adding or editing
  one as a blocking finding, and the ChatGPT and usage guides say the same.
- Return `FIX` pending the owner, not `STOP`, when `reviewer` judges a contributor's
  permissions, API-write or `workflow_run` change with no live check: the live check is
  an owner-must-run item, as the contributor rules and the ChatGPT guide already said,
  and the verdict section now agrees with them.
- List a contributor change's paths with `--no-renames` in `reviewer`, `investigator`,
  `/ship`, `/verify` and the ChatGPT and usage guides. With rename detection on, moving
  a test into `docs/` listed only the new Markdown path, which passed the safe-name check
  and the inert-content allowlist while the test was gone. A reviewer benchmark case and
  a review lesson cover it.
- Run CI in full when a pull request's base is retargeted. `edited` covers a new base as
  well as a new title or body, and the earlier run's pull request list reports the base
  as it is now, so a retarget was answered with the two description checks from a run
  against the old base. `scope` now reads the event's `changes`, treats only a title or
  body edit as text, and counts only earlier runs that list this pull request.
- Show each plugin command on the site's Workflows page by the name an installed plugin
  runs it under, `/plugin:command`, rather than the bare command name.

## [0.1.8] - 2026-10-10

### Added

- Open the `family` plugin's page on the same typed F.A.M.I.L.Y. heading as the FAMILY
  page, with a link to the stage-by-stage guide; every other plugin keeps its plain name.

## [0.1.7] - 2026-10-10

### Added

- Add six skills to the `family` plugin that run its stage agents together:
  `family-relay` routes each stage agent's verdict to the next hop and steps back a stage
  when a verdict repeats; `plan-drift-gate` checks a build against maker's plan before
  inspection; `fresh-inspector-rounds` starts each review round on a new inspector and
  reopens Architect when a finding recurs; `frame-claim-ledger` settles the claims a
  hard-to-reverse decision rests on first; `yield-to-lesson` accepts a retro item only as
  a check the next inspection can fail on; `stage-tiering` sets a model tier per stage.
  The family listing ceiling rises to fit them, and the recommended
  `skillListingBudgetFraction` rises to 0.119.
- Type the FAMILY page's heading in on arrival: F.A.M.I.L.Y., one stage letter and its
  dot at a time, then the stages rise in. Each stage has its own colour, used again on
  its letter and a rule beside it, at least 5.3:1 against the day background and 9:1 at
  night; the console theme stays one colour. CSS only, so reduced motion or no scripts
  shows the whole word at once, and screen readers hear "The FAMILY workflow".

### Changed

- Return the fix packet in `fresh-inspector-rounds` to the contributor when the change
  is not the owner's, so the main conversation applies fixes only to a slice the owner
  wrote and never patches a contributor's change on the trusted checkout. With an unknown
  author the loop stops and the packet goes to whoever asked for the review.
- Let `family-relay`, `plan-drift-gate` and `fresh-inspector-rounds` edit the tree, since
  each runs the build or the fix itself when no writing agent is used, and route a
  launcher `N-A` through a written Launch waiver before Yield.
- Close three gaps in the FAMILY workflow skills. `launcher` returns `READY` only with a
  go from the Inspect owner, so a missing or no-go decision is a `NOT READY` that
  `family-relay` routes back to the Inspect owner rather than to release. `stage-tiering`
  says that `CLAUDE_CODE_EFFORT_LEVEL` overrides every agent's `effort`, unlike the model
  setting. `yield-to-lesson` accepts a lesson on a fixed number of runs before and after,
  not by retrying until one catches.
- Replace the stroked "AI" tab icon with the crystal "AI" artwork, shipped as a 64 px
  `favicon.png` and a 180 px `apple-touch-icon.png` for phone home screens. Both are
  cut square from the artwork and stored under `scripts/site_assets/`.
- Give each FAMILY stage one owner and a first question. The Inspect owner (QA where
  present) owns the go/no-go that closes Inspect, and `launcher` takes it as input and
  returns `NOT READY` only for a missing path, signal or rollback. `inspector` reports each
  success criterion as holding, failing or not assessed and leaves severity-ranked findings
  to `code-review`. The solo, developer and QA skills name the agent for each step. Only
  Architect and Launch may be waived, in writing. A profile is the role and depth is light
  or full per slice, recorded in the frame. The family trigger evals route the
  success-criterion, acceptance and cadence queries to one owner each, the agent evals name
  real neighbouring skills as negatives, and the `launcher`, `architect`, `maker` and
  `inspector` verdicts that were undefined now have a line.

## [0.1.6] - 2026-10-10

### Added

- Add three skills to the `design` plugin: `visual-design` for hierarchy, type scale,
  colour roles and spacing, `responsive-design` for layouts from 320 px up with
  content-first breakpoints, and `form-design` for designing or changing a form, with
  `ui-ux-review` keeping the diagnosis of an existing one. The design listing now runs
  past the runtime's default budget, so the install advice raises
  `skillListingBudgetFraction` to 0.115.

### Changed

- Update the deploy's pinned Wrangler to 4.149.0, with sharp 0.35.5 in the same lock
  file, and move the `WRANGLER_VERSION` pins in `deploy.yml` and `release.yml` with it.

### Fixed

- Give each portable router line its full 100 characters of trigger again. 0.1.4 cut
  them to 85 to fit the router's 16 KiB budget, which took 15 more characters off every
  long trigger; each line now names its file as `- skills/<name>.md:` instead of a
  Markdown link that repeated the name, and that is what keeps the router in budget.

## [0.1.5] - 2026-10-10

### Added

- Show an "AI" icon in the browser tab. The site now ships `favicon.svg`, the header's
  mark drawn as strokes on a dark tile so it reads on light and dark tabs, and every
  page links to it.

## [0.1.4] - 2026-10-09

### Added

- Add a tenth plugin, `family`, built around one development workflow, FAMILY: Frame,
  Architect, Make, Inspect, Launch and Yield. It ships the `family-workflow` skill, one
  skill per profile (`solo-development`, `developer-workflow`, `qa-workflow` and
  `team-workflow`) that sets how deep each stage goes, six read-only stage subagents
  (`framer`, `architect`, `maker`, `inspector`, `launcher` and `yielder`), and a
  hand-drawn `/family/` page on the catalogue site. `inspector` runs a change's checks
  only when the owner wrote it, and hands pull request and diff review to `code-review`.
- Add three skills to the `design` plugin: `content-design` for the words in an
  interface, `information-architecture` for navigation, taxonomy and findability, and
  `design-handoff` for the build spec a developer works from.
- Test the catalogue site in a real browser. A new `test site in a browser` job builds
  the real catalogue, serves it locally and drives it in the Chrome the runner already
  ships: Back returns to the page you came from and never to another site, the bar and
  To top appear and hide when they should, a jump to a heading lands below both bars,
  the theme follows the clock and remembers a choice, the finder filters and counts, no
  page scrolls sideways on a phone, and the controls are at least 44 px. Breaking each of
  those behaviours on purpose turned its test red. Playwright and everything the job
  installs comes from a lock file with every package hashed, installed with
  `pip --require-hashes`. The tests that only checked that a
  CSS or script line existed are replaced, and `make test-browser` runs the same tests
  locally.

### Changed

- Run the full suite before stage and only what a promotion can still break on the way
  into `main`. A new `scope` job reads the GitHub API and git: a pull request into `main`
  whose tree is the one stage's pull request passed in full, apart from the changelog
  and the release benchmark patch, and the push to `main` after it, skip the test
  matrix, the browser tests and the linters of unchanged files, and keep validate,
  catalogue, spelling, markdown, links, attribution, naming, package, every security
  check and, on the pull request, the dry-run deploy. An edit to a pull request's description re-runs only
  attribution and naming once the code has passed against the same base. Anything the
  job cannot prove is a full run, and the aggregate accepts a skipped job only when the
  scope named it.
- Run the test suite on every core. `make test` and the CI `test` job run pytest through
  pytest-xdist, and the 3.13 leg measures coverage in each worker through pytest-cov, so
  the floor still covers every test. Locally the suite drops from about 100 s to about
  55 s, with the same coverage. The install tests link a five-skill tree built per test
  instead of every shipped skill eight times, and one test still links the whole tree.
  Both new test-only packages are pinned and registered with the weekly pin check.

### Fixed

- Stop the agent roles running code or commands taken from a contributor's change. In
  the review loop, `reviewer` and `investigator` take an Author field that `/verify`
  passes (absent means contributor). A printed command is data to check by reading, run
  only for an owner-authored change, in a throwaway directory with no network or
  credentials. On a contributor change `reviewer` runs the gates only when every changed
  path is inert content (Markdown under `plugins/` or `docs/`, a trigger eval set, or
  the root `README.md` or `CHANGELOG.md`, as regular files). Otherwise it runs no gates
  and cites no CI, because a contributor's pull request runs the contributor's own
  workflow files and `Makefile`, and returns `FIX` pending the owner, who runs the gates,
  confirms the required `ci` and `security` checks passed on the current head, and
  confirms `.github/workflows/`, `Makefile`, `pyproject.toml` and the scripts CI calls
  are unchanged against the merge-base (treating CI as untrusted if not); the gates run
  only in a disposable sandbox with no credentials and no network, never in the owner's
  normal environment or clone; `SHIP` is never returned by the reviewer itself on such a change, though a `FIX` whose only open items are the owner-must-run ones (no blocking finding, and the candidate based on the current base) is cleared by the owner's completed checklist recorded on the PR, live check included, for that head commit on that base tip only (a new push voids it, as does a base advance, detected by re-fetching and comparing both refs against the pinned base and reviewed SHA before accepting and again before merge; a post-merge live check is recorded as named but not yet run; a blocking finding or the rebase `FIX` still needs a fix and a fresh review).
  A changed path must also have a whole NUL-delimited name matching
  `^\.?[A-Za-z0-9_][A-Za-z0-9._-]*(/\.?[A-Za-z0-9_][A-Za-z0-9._-]*)*$` (each segment may start with one dot, then a letter, digit or underscore) to be canonical: a name such
  as `docs/$(cmd).md` makes the change non-inert, is never put in a command and is a
  blocking finding asking for a rename (dot-prefixed paths such as `.github/` and `.claude/` are canonical but non-inert, since they are outside the inert allowlist, so they go to the owner-must-run flow, not a rename), and paths are listed NUL-delimited and read in
  single quotes. Such a `FIX` goes back to the owner or contributor, never
  to `implementer`. The build loop (`/ship`, `explorer`, `implementer` and the ChatGPT
  coordinator's build loop) is owner-only: with contributor content the owner has not
  adopted (not on the base branch) in the checkout, `/ship` returns `STOP` and the
  change goes to a fresh `reviewer` delegation with the loop "contributor review" (plus
  `investigator` only for an outside claim). `explorer` and `implementer` carry the same
  guard and stop without running anything. The ChatGPT workflow guide and
  `docs/using.md` carry the same rules. A contributor review runs only from a clean worktree at the pinned base SHA (`HEAD` must equal it exactly, so an older ancestor checkout is `STOP`), never the contributor's, because Claude Code loads agents,
  settings, hooks and instructions from the checkout it opens, and Codex and ChatGPT
  read AGENTS.md and repository instructions from it: the contributor's head is fetched
  as a ref and read with git, and a session opened inside a contributor or stale checkout returns
  `STOP`. The base must be `dev`, `stage` or `main` (any other is `STOP`) and is pinned to its SHA after the fetch; the reviewer is given both, and before any command requires `<base>` to be a full hex SHA equal to the base tip and `<n>` to be all digits (else `STOP`). The reviewer runs inert-only gates on that SHA with `refs/review/<n>`
  merged in (`--no-ff`); a candidate not based on the current base (`git merge-base` differs from the base tip) is `FIX` asking for a rebase before any gate runs, as is a merge conflict; and `<base>` is the
  pinned SHA.
- Stop seven skill pages scrolling sideways on a phone. A long path or identifier in
  running text had no place to break, so one wide `code` span pushed the page past the
  screen; inline code in prose may now break anywhere, and code blocks still scroll
  inside their own box. The new browser tests found it.

## [0.1.3] - 2026-10-06

### Added

- Add the `design` plugin, the ninth, with four skills: `ui-ux-review` reviews one screen
  or flow against usability heuristics with ranked, evidenced findings; `accessibility-audit`
  audits against WCAG 2.2 Level AA, automated pass first and the manual pass automation
  cannot do second; `design-system` sets up role-named tokens, themes and component states,
  including where glass materials belong; `usability-test-plan` plans a small test with
  real people and turns the sessions into severity-rated fixes. The plugin is listed in the
  marketplace under `development` and fits the default listing budget on its own. The install
  advice's `skillListingBudgetFraction` rises from 0.101 to 0.105, which the whole
  marketplace's descriptions now need.
- Add a bar with Back on every catalogue page below the front page. It appears once the
  page has scrolled past its own Back button and hides again near the top, so Back is
  never out of reach on a long skill page. It spans the header's width, so on a wide
  screen Back sits under the header's left edge, clear of the text; it sits on the solid
  page colour below the header, so text scrolls under it and never shows behind the
  button. It is a labelled landmark straight after the header, so the keyboard reaches
  it before the page body, and a jump to a heading lands below it.
- Add To top to every catalogue page, floating at the bottom right. Like the header, it
  goes away while the reader scrolls down and comes back on the way up and at the end
  of the page, so it does not sit over the text being read. On a narrow screen it is a
  round 48px button with only the arrow, on a denser glass tint than Back's so text
  behind it does not compete with the arrow; from 1440px wide, where the margin beside
  the text column can hold it, it carries its label. The footer leaves room to scroll
  clear of it. It respects reduced motion and moves focus to the home link.
- Restyle Back and To top as Material Design 3 buttons made of Liquid Glass: a full
  pill with a leading icon and Material's 8% and 12% state layers, on a translucent,
  blurred tint with a specular top edge, a sheen and a floating shadow, with tokens per
  theme.

### Changed

- Keep the weekly scheduled run green when a pinned tool publishes a release. A pin
  behind upstream, a registry that could not be asked, or a markdownlint pin that no
  longer matches its action is now a warning annotation on the run, with the table still
  in the job summary; the run fails only for a pin with no upstream registered. Claude
  Code and Codex publish nearly every week, so the old rule left the run red nearly every
  week. A registry answer that is not shaped like a version is refused without being
  repeated, since the step log reads a line starting with `::` as a command, and the
  legacy `##[name]` marker is broken wherever outside text is printed, since the runner
  honours it anywhere in a line. Bump
  `CLAUDE_CODE_VERSION` from 2.1.287 to 2.1.291 and `CODEX_VERSION` from 0.160.0 to
  0.160.1.

### Fixed

- Make `design-system`'s inventory count distinct colours: the command counted matching
  lines, so a colour used twice counted twice and two colours on one line counted once.
  Its contrast table now has one row per pair and state and one column per theme, so a
  hover colour that fails only in dark mode has a cell to fail in.

## [0.1.2] - 2026-10-05

### Added

- Add a Back button to every catalogue page below the front page, a tonal pill with a
  leading arrow in the style of Material Design 3, the same shape as the Download and
  View source buttons. It returns to the previous page when that page is on this site,
  and otherwise goes to the page above: the plugin for a skill, the front page for the
  rest, the not-found page included. Without JavaScript it is a plain link to that
  page.

### Fixed

- Stop `scripts/run_review_benchmark.py --jobs` from failing at random when two cases
  create their worktrees at once. `git worktree add` and `remove` now run one at a
  time under a lock, each worktree gets a unique name, and a failed `add` reports git's
  own message instead of only its exit status.

## [0.1.1] - 2026-10-05

### Fixed

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

## [0.1.0] - 2026-10-04

### Added

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

[Unreleased]: https://github.com/greenblacked/AI/compare/v0.1.12...HEAD
[0.1.12]: https://github.com/greenblacked/AI/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/greenblacked/AI/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/greenblacked/AI/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/greenblacked/AI/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/greenblacked/AI/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/greenblacked/AI/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/greenblacked/AI/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/greenblacked/AI/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/greenblacked/AI/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/greenblacked/AI/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/greenblacked/AI/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/greenblacked/AI/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/greenblacked/AI/compare/9365d19bd40e79f52463b046927b17cfd448bb79...v0.1.0
[Initial catalogue]: https://github.com/greenblacked/AI/tree/9365d19bd40e79f52463b046927b17cfd448bb79
