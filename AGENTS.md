# AGENTS.md

Instructions for any coding agent working in this repository. `CLAUDE.md` imports this
file, so there is one set of rules rather than two that drift apart.

## Project overview

A library of Claude Code Skills and subagents, installable as a plugin marketplace.
Skills are Markdown procedures an agent follows; the value is in the opinionated parts —
the ordering, the specific gate, the command with the right flag — not in restating
general good practice.

Everything here is prose and configuration. There is no application. The only code is
`skillcheck`, the validator CI runs against the skills.

## Multi-agent workflow

Which models to use depends on the tool running the session, because each tool offers a
different set. Honour an explicit per-task assignment over either default split below.

- **Codex and ChatGPT:** use Astra at medium effort only for review and decisions; use
  Sol at low effort for research into agent features or configuration and for
  implementation; use Terra at low effort for branch synchronisation and integration
  when assigned.
- **Claude Code:** use the tier each agent in `.claude/agents/` declares, which
  `CLAUDE.md` spells out. Its two loops hand off through a written brief going in and a
  report's `Handoff` section coming back, never a paraphrase of the whole thing; whichever
  stage writes or judges the change reads this file first and `docs/review-lessons.md`
  next.
- **Any other tool:** report which models it offers rather than guessing at a mapping.

Whichever tool runs it, research agents verify facts before implementation begins. Give
implementation agents disjoint files, then have the reviewer validate the combined diff.
Do not substitute another model automatically; if a requested model is unavailable,
report that limitation. Model and effort choices apply when starting agents and cannot
change an already active session.

## Repository layout

| Path | What lives there |
| --- | --- |
| `AGENTS.md` | This file: the rules, in the form Codex and Gemini CLI read too |
| `CLAUDE.md` | The `@AGENTS.md` import plus the four notes that are only true of Claude Code |
| `.claude/rules/` | Path-scoped rules loaded when a file matching the glob is read; `docs/project-structure.md` explains when each fires |
| `.claude/settings.json` | The `PostToolUse` hook registration, checked by `scripts/check_settings.py`; nothing else yet |
| `plugins/coding/skills/` | Reading, reviewing, testing and changing code |
| `plugins/operations/skills/` | Keeping a running system alive |
| `plugins/delivery/skills/` | Getting a change into production |
| `plugins/gamedev/skills/` | Making games, and shipping them |
| `plugins/security/skills/` | The defensive side of shipping software |
| `plugins/manager/skills/` | Engineering leadership |
| `plugins/personal/skills/` | Money, travel, admin, habits and health |
| `plugins/career/skills/` | Applications, negotiation, speaking and writing |
| `plugins/*/agents/` | Subagent definitions, validated on the same run as the skills |
| `plugins/*/commands/` | Slash commands the plugin ships, validated on the same run |
| `.claude/commands/` | Slash commands for working on this repository, not shipped to installers |
| `.claude/agents/` | Two loops — `explorer`, `implementer`, `reviewer` to build; `investigator` and `reviewer` to verify — for working on this repository, validated on the same run |
| `src/skillcheck/` | The validator: `frontmatter.py` parses, `rules.py` decides, `cli.py` reports |
| `tests/` | pytest over the validator, including a check that this repository validates clean |
| `plugins/*/skills/*/evals/` | Trigger eval sets: the queries a skill should and should not fire on |
| `plugins/*/agents/evals/` | The same for each subagent, one `<name>.json` per agent file |
| `docs/` | How to write skills, subagents, commands, `AGENTS.md`, what the project layout loads, and what CI checks |
| `docs/review-lessons.md` | Defect classes review on this repository has actually caught, each with how it shows up, the check that catches it and the PR that found it first; `implementer` and `reviewer` read it before writing or judging anything |
| `template/SKILL.md` | Starting point for a new skill |
| `.claude-plugin/marketplace.json` | Lists the eight plugins; each discovers its own skills |
| `.github/workflows/` | `ci.yml`, `security.yml`, `scheduled.yml`, `evals.yml`, `dependabot-auto-merge.yml`, `release.yml` |
| `listing-budget.json` | Per-plugin ceilings for the skill listing and a per-skill description ratchet; `scripts/check_listing_budget.py` enforces both |
| `providers.json` | Which AI tools read `AGENTS.md` and load skills, with sources and a checked date; `scripts/providers_table.py` renders it into the README |
| `scripts/` | Packaging (`package_skills.py`, `verify_archives.py`), install, the eval harness, the portable export, cutting a release (`release.py`), and the seven catalogue checks |
| `scripts/hooks/` | The `PostToolUse` hook `.claude/settings.json` registers, which validates a skill, subagent, command or rule as it is written |

## Setup commands

No dependencies are needed to validate or package — the validator is standard library
only, and CI runs it on Python 3.10 through 3.13 to keep that true. Only the test run
needs anything installed.

```bash
python -m pip install pytest coverage   # only for `make test` and `make coverage`
make validate                  # every skill, subagent and the marketplace manifest
make catalogue                 # listing ceilings, the README, shell blocks, the hook, providers
make test                      # the validator's own test suite
make coverage                  # the same, failing below the floor in pyproject.toml
make package                   # build a .skill archive per skill into dist/
make install                   # symlink every skill into ~/.claude/skills
make release-prepare VERSION=x.y.z  # on a branch: move Unreleased into a dated section
make release VERSION=x.y.z          # on main, after that PR merges: tag the release
```

## Testing instructions

`make validate`, `make catalogue` and `make test` are the same commands CI runs. Run all
three before finishing; a change to `rules.py` that does not also change `tests/` is
almost always missing a case.

`make catalogue` is the seven checks on what the repository claims about itself: the
listing ceilings, the README against the tree, `docs/ci.md` against the jobs the
workflows actually define, that each workflow's aggregate names every job in it and each
pinned version means one thing, that every shell block and shipped script parses, that
the hook `.claude/settings.json` registers points at a script that exists and can run,
and that the README's table of AI tools is what `providers.json` renders to. Edit that
file rather than the table and run `make providers`; a row not re-checked within
`stale_after_days` warns without failing.
Adding a skill pushes its plugin's listing past the ceiling in `listing-budget.json`,
on purpose: past the runtime's budget the descriptions of a plugin's least-used skills
are dropped silently, so growth has to be a decision rather than a drift. Raise the ceiling with
`scripts/check_listing_budget.py --update` and say why in the commit, or split the
plugin. The same target checks that the README still lists every skill, subagent and
command that exists and nothing that does not, that `docs/ci.md` still has a row for
every job CI runs — a job with no row is a red check someone has to reverse-engineer out
of YAML — and that a job left out of `ci`'s or `security`'s `needs:` cannot go green by
being forgotten.

The suite covers the scripts, not only the validator. `tests/conftest.py` holds the two
fixtures they share: `mini_repo`, a complete plugin repository built in a temporary
directory, and `fake_claude`, a stand-in for the `claude` CLI that answers from a table
so the eval harness can be exercised without a model. A change to a script under
`scripts/` should come with a case in the matching `tests/test_*.py`, and CI fails the
test job when coverage drops below the floor in `pyproject.toml`.

The block-scalar cases in `tests/fixtures/block_scalars.json` are recorded from PyYAML
by `tests/fixtures/generate_block_scalars.py`. Regenerate them when `frontmatter.py`
changes; the generator refuses to write the file while the two parsers disagree.

`make validate` runs with `--strict`, so warnings fail too. They are warnings because
each is a judgement call rather than a rule, but a warning nobody has to clear is one
that accumulates until the whole category stops being read.

CI additionally runs markdownlint, yamllint, actionlint, codespell, an offline link
check, gitleaks, zizmor, ruff (with the flake8-bandit rules) and CodeQL. `make lint` runs
the first four locally when they are installed and tells you the command when they are
not. codespell's false positives live in `pyproject.toml` with the reason each is one;
add to that list rather than silencing the check, and only for a word that is genuinely
not a typo.

The validator must keep working on a bare interpreter. Importing a third-party package
in `src/skillcheck/` breaks the guarantee CI is built on, so do not add one.

## Adding or changing a skill

1. Copy `template/SKILL.md` into `plugins/<plugin>/skills/<name>/SKILL.md`.
2. Set `name` to exactly the directory name. Write the `description` last, when you know
   what the skill does — it is the only text loaded before the skill fires, so it decides
   whether the skill is ever used.
3. Put depth in `references/*.md` and name each one in the body with a line saying when
   to read it. If you name a path, write the file: the validator fails on a pointer to
   something that does not exist, which is the defect that motivated it.
4. Write `evals/trigger-eval.json`: twenty queries, ten the skill should fire on and
   ten near-misses it should not. On each negative that has an obvious owner, add
   `"expected"` naming the skill or subagent that should win it — that is what turns
   "did not fire" into "routed correctly", and it is the only way the score can see one
   description stealing another's queries. The validator's floor is sixteen with eight a side,
   so twenty leaves room to drop one without failing. The negatives are the useful half — they are what
   catches a description that fires on everything. Draw several from the skills next
   door, because that is where the real collisions are.
5. Keep the description inside the 500–900 character guidance rather than at the cap.
   Every description a plugin ships is resident in context for the whole session, and the
   runtime drops the least-used ones when the listing overflows its budget — `make
   validate` prints the per-plugin total, and `docs/writing-skills.md` explains what to do
   with it.
6. Set `allowed-tools` to the minimum the procedure genuinely needs, scoped per binary
   where scoping carries information — `Bash(kubectl:*)` says something, `Bash` does not.
7. Nothing to add to `.claude-plugin/marketplace.json`: each plugin discovers its own
   `skills/`. What the validator checks is that the skill sits inside a plugin at all —
   one stranded outside `plugins/<name>/skills/` installs for nobody.
8. Run `make validate && make catalogue && make test`. The catalogue check will fail
   until the README has a row for the skill, and may fail on the plugin's listing
   ceiling — both are the gate working.

`docs/writing-skills.md` has the full contract, including every validator code and how to
fix it.

A slash command is a different thing and is not a substitute for a skill: it never fires
on its own, so it is the right shape only for work that takes an argument or that should
happen when asked rather than when merely relevant. A command that restates a skill is a
worse version of a skill whose description should have triggered.
`docs/writing-commands.md` has that contract.

## Code style

Prose in skills is imperative and explains why a rule matters rather than shouting it —
a capitalised ALWAYS or NEVER earns a warning for that reason. No emoji, no marketing, no
exclamation marks. Be consistent with spelling inside a file.

Python follows `ruff` with the configuration in `pyproject.toml`; run `ruff format`
before finishing. Comments explain why, not what.

Shell in this repository, including inline `run:` blocks in workflows, uses
`set -Eeuo pipefail`. actionlint runs shellcheck over those blocks in CI.

## Commit and pull request instructions

- Commits are authored by the person who wrote them and nobody else. Do not add `Co-Authored-By`
  trailers, tool attributions, or "generated by" lines to commit messages, pull request
  bodies, or files.
- One logical change per commit; a subject line in the imperative under about 70
  characters, and a body explaining why when the reason is not obvious from the diff.
- Branch names describe the change, not the tool that made it, following the
  `<type>/<short-kebab-description>` convention [`CONTRIBUTING.md`](CONTRIBUTING.md#naming-a-branch)
  documents.
- `ci` and `security` both have to be green before merge.

## Pull request review threads

For reviews on this repository, use one inline thread per distinct actionable finding.
Prefix findings with `blocking`, `should-fix`, `consider` or `nit`, as the
`code-review` skill defines. The reviewer owns verification and resolution of blocking
threads after the author replies with a fix commit and check results. Keep follow-up on
the original thread; open a new one only for a different defect. Put the verdict,
coverage and checks in the overall review, and do not recommend merge with an unresolved
blocking finding or a failing `ci` or `security` gate.

## Security considerations

- No secrets in this repository, ever — gitleaks scans the working tree *and* history,
  because a secret that was committed and later removed is still leaked.
- Every workflow sets a top-level `permissions:` block. An absent one inherits the
  repository default, which is usually write access to everything.
- Every job sets `timeout-minutes:`. Without one a hung job runs to the six-hour
  platform default, which reads as slow CI rather than broken CI.
- Nothing in a workflow pipes a downloaded script into a shell. Tools are fetched at a
  pinned version and checked against a recorded digest.
- Every action is pinned to a full-length commit SHA, commented with the exact release
  tag that SHA belongs to — `# v7.0.1`, not `# v7`. The SHA is what makes it immutable;
  the comment is what lets Dependabot bump it. A major-version comment goes stale
  silently the moment upstream moves the floating tag, and zizmor fails the build for it.
- Checkouts set `persist-credentials: false`. Nothing here pushes from CI. There are two
  bounded exceptions. `dependabot-auto-merge.yml`'s single job is the first: it can enable
  auto-merge on a Dependabot pull request that is a patch or minor update and whose head
  branch is in this repository, which stays bounded because GitHub only completes that
  merge once the `ci` and `security` checks the branch ruleset requires have both reported
  `success`. `release.yml`'s single job is the second: it holds `contents: write` and
  nothing else, runs only on a `vX.Y.Z` tag push, and refuses to proceed when the tagged
  commit is not an ancestor of `main`. It spends that permission creating a GitHub Release
  and uploading assets to it through the preinstalled `gh` CLI, never on pushing a commit
  — its checkout still sets `persist-credentials: false`, the same as every other job here.
- Skills may describe security tooling and defensive procedure. They must not contain
  working exploit code, credentials, or instructions whose obvious use is unauthorised
  access.

## Boundaries

- Do not edit a skill's `description` to make a test or check pass. If a check is wrong,
  fix the check and its test.
- Do not add a dependency to `skillcheck`.
- Do not add a frontmatter key to a `SKILL.md` outside the six the validator allows,
  however useful Claude Code makes it. The Skills API upload route rejects every other key
  with a hard error, and every skill here has to survive `make package`. `when_to_use` is
  the tempting one; its content belongs in `description`. A key the portable six cannot
  carry is the one reason to write a command instead of a skill.
- Do not turn a validator error into a warning to unblock a change. The dangling-pointer
  check in particular exists because that failure is silent in production.
- Do not edit a fixture to satisfy a new rule without saying so. A fixture that trips a
  rule is often the pattern the rule exists to discourage, and quietly changing it is how
  the rule gets defanged on the day it lands. Say in the commit which it was.
- Do not rewrite the exported skills' voice. `code-scaffold`, `website-builder` and
  `health-coach` were written by hand; new reference files match them rather than the
  other way round.
- Do not push to `main` directly.

## Review checklist

Before finishing, confirm each of these and say so honestly if one does not hold:

- [ ] `make validate` exits 0
- [ ] `make catalogue` exits 0
- [ ] `make test` passes
- [ ] Every `references/`, `scripts/` or `assets/` path named in prose exists
- [ ] Any new skill sits inside `plugins/<name>/skills/` and has an eval set
- [ ] No secrets, tokens or personal data added
- [ ] Commit messages carry no tool attribution
