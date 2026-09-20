# CI

CI is the source of truth for whether this repository is correct. Everything a reviewer
would otherwise check by eye — that a skill validates, that its reference files exist,
that it is listed in the marketplace, that no secret is in history — is a job that either
passes or does not. Four workflows run it: two that gate every change, one that runs
weekly, and one that scores trigger evals — monthly over everything, and on every pull
request over what that pull request touched.

## `.github/workflows/ci.yml` — CI

Triggers on push to `main`, on every pull request, and on `workflow_dispatch`. Top-level
`permissions: {}`; each job grants itself the minimum. Every tool the workflow installs
or downloads is pinned in the workflow-level `env` block — `CLAUDE_CODE_VERSION`,
`CODESPELL_VERSION`, `YAMLLINT_VERSION`, `PYTEST_VERSION`, `COVERAGE_VERSION`,
`ACTIONLINT_VERSION` and `ACTIONLINT_SHA256` — for the reason the security section
gives, and at workflow level so a cache key can name one.

| Job | Check name | Failing means |
| --- | --- | --- |
| `validate-skills` | `validate skills` | A skill, a subagent, a command or the manifest is invalid: bad frontmatter, a name that does not match its directory or filename, a dangling `references/` pointer, a malformed eval set for a skill or a subagent, a `.claude/rules/` glob that matches nothing, or something on disk that no plugin lists. Runs with `--strict`, so a warning fails it too. Run `make validate` locally to see the same output; it also prints the per-plugin description total, which is the listing cost every installer pays. |
| `validate-plugin` | `validate plugin manifest` | `claude plugin validate .` rejected `.claude-plugin/marketplace.json`. The schema's source of truth is the definition inside the CLI itself, so this checks against the real thing rather than a copy that would fall behind. The CLI version is pinned in the workflow's `env` for the same reason the scanners are. |
| `test` | `test (3.10)` … `test (3.13)` | The validator's own test suite failed on that interpreter, or line and branch coverage fell below the floor in [`pyproject.toml`](../pyproject.toml). The matrix is four versions because that file declares no dependencies, and running on a bare interpreter across the supported range is how that claim stays true. pytest and coverage are pinned in `PYTEST_VERSION` and `COVERAGE_VERSION`, so a runner failure is a statement about this repository rather than about the day's release of the runner. The coverage table lands in the job summary. |
| `catalogue` | `check catalogue` | A plugin's skill listing grew past its ceiling in [`listing-budget.json`](../listing-budget.json), the README stopped matching the tree, a shell block or shipped script no longer parses, or the hook registration in `.claude/settings.json` names a script that is missing or not executable. The first is the one with no symptom: past the runtime's listing budget, the descriptions of a plugin's least-used skills are dropped, so they stay invocable by name and stop being chosen on their own. Ceilings carry a few hundred characters of slack, so rewording is free and adding a skill is a decision — raise one with `scripts/check_listing_budget.py --update` and say why in the commit. The same file also records each skill's own description length: a new skill must arrive at or under 900 characters, and one already above that is pinned where it measures rather than trimmed to fit a gate. |
| `catalogue` (portable step) | `check catalogue` | `make portable` could not flatten every skill into a file that stands alone. This is how the library reaches ChatGPT, Grok and anything else without a skills runtime: frontmatter becomes a plain "Use this when" line and every `references/` file is inlined, with the pointer that named it rewritten to name the section instead. A pointer that survives as a path is a dangling reference reintroduced at the boundary, for a reader with no filesystem to resolve it against. |
| `spelling` | `lint spelling` | codespell found a likely typo. It ran weekly and warn-only until it was made a gate; the false positives are listed in [`pyproject.toml`](../pyproject.toml) with the reason each is one, which is what lets the check sit at zero and mean something. |
| `lint-markdown` | `lint markdown` | markdownlint-cli2 found a violation in a `*.md` file. Config in `.markdownlint-cli2.yaml`. |
| `lint-yaml` | `lint yaml` | yamllint in `--strict` mode found a problem. Config in `.yamllint.yaml`, version in `YAMLLINT_VERSION`: a release that adds a rule would otherwise redden the build on YAML nobody touched. |
| `lint-actions` | `lint workflows` | actionlint rejected a workflow. It also runs shellcheck over every inline `run:` block, which is where all of this repository's shell lives. The binary is downloaded at a pinned version and checked against a recorded digest before it runs. |
| `links` | `check links` | lychee found a broken link. It runs `--offline`, so only local paths are resolved — a relative link between documents, or from a document into the source tree, that does not exist. |
| `package` | `package` | `scripts/package_skills.py` could not build a `.skill` archive for every skill, or an archive it built is not loadable. It refuses to package a skill that does not validate, so this failing after `validate-skills` passed means a packaging problem, not a content one. Each archive is then opened and checked for a `SKILL.md` at its root whose `name` matches the archive, because building without error only proves a zip was written — a broken layout would ship green and fail at install, for someone else. The archives upload as the `skills` artifact. |
| `ci` | `ci` | One of the ten jobs above failed or was cancelled. |

`validate-skills` runs `PYTHONPATH=src python -m skillcheck . --strict`, the same
invocation as `make validate`. The flag is the point: without it, a description one edit
from the 1024-character cap, a skill with no trigger clause, and a skill with no eval set
all report and pass. They are warnings because each is a judgement call rather than a
rule, and they fail the build anyway, because a warning nobody has to clear is a warning
that accumulates until the whole category is ignored.

`validate-plugin` runs without `--strict`, and that is deliberate: each
`plugins/<name>/.claude-plugin/plugin.json` omits `version`, which the CLI warns about.
With a git-sourced marketplace, omitting the version is the documented behaviour — every
commit then resolves as a new version — so the three warnings are the correct state and
`--strict` would force a version field that exists only to silence them.

## `.github/workflows/security.yml` — Security

Same triggers, same empty top-level `permissions`. Tool versions are pinned in `env`
(`GITLEAKS_VERSION`, `GITLEAKS_SHA256`, `ZIZMOR_VERSION`, `RUFF_VERSION`) rather than
floated: a scanner that changes its rule set between runs turns a green build into a
statement about the scanner rather than about the code. ruff is in that list for a
concrete reason — 0.16 began formatting Python blocks inside Markdown, so an unpinned
upgrade would fail the build on skill prose that was green the day before.

| Job | Check name | Failing means |
| --- | --- | --- |
| `secrets` | `secret scan` | gitleaks found a credential. |
| `workflows` | `workflow audit` | zizmor found a workflow vulnerability at medium severity or above. |
| `python` | `python security lint` | `ruff check` or `ruff format --check` failed. |
| `codeql` | `codeql` | CodeQL's `security-extended` query suite found something in the Python source. |
| `permissions-audit` | `permissions audit` | A workflow has no top-level `permissions:` block, an action is not pinned to a SHA, a job sets no `timeout-minutes`, or an `actions/checkout` does not set `persist-credentials: false`. |
| `security` | `security` | One of the five jobs above failed or was cancelled. |

### The security jobs in detail

**gitleaks runs twice, over different things.** `gitleaks dir .` scans the working tree;
`gitleaks git .` scans history, which is why the checkout uses `fetch-depth: 0`. Scanning
only the working tree misses the case that matters most: a secret that was committed and
later removed is still a leaked secret, because the object is still in the repository and
anyone who cloned it has a copy. Both invocations use `--redact` so the finding does not
put the secret in the log. The binary itself is downloaded at the version in
`GITLEAKS_VERSION` and checked against `GITLEAKS_SHA256` before it is unpacked, for the
reason the pinning section below gives: a release asset is as mutable as the tag naming
it, and a secret scanner is a poor thing to run an unverified download of.

**zizmor audits the workflows themselves.** Run as
`zizmor --persona=regular --min-severity=medium .`. It looks for the things that actually
compromise a repository through CI: template injection into `run:` blocks, over-broad
token permissions, unpinned third-party actions, and `pull_request_target` combined with
a checkout of untrusted code.

**ruff carries the flake8-bandit rules.** `[tool.ruff.lint]` selects `S` alongside
`E`, `F`, `I`, `UP`, `B` and `SIM`. `S` is flake8-bandit, so the security lint is the
same tool as the style lint with one more rule set enabled. `tests/*` ignores `S101`,
because asserting is what tests do.

**CodeQL** runs `github/codeql-action` init and analyze with `languages: python` and
`queries: security-extended`. It is the only job that needs `security-events: write`.

**Four shell invariants.** `permissions-audit` is four `grep` and `awk` loops,
deliberately not a tool. Each is one of the workflow conventions `AGENTS.md` states, and
each exists because breaking it is silent:

- Every workflow file must set a top-level `permissions:` block. An absent block means
  jobs inherit the repository default, which is often read and write on everything. The
  failure is silent and permanent, which is exactly the kind worth a one-line check.
- Every action must be pinned to a commit SHA. The check is inverted rather than
  matching known-bad shapes: a ref that is not forty hex characters fails, whatever it
  looks like. Matching `@v1.2`, `@main` and `@master` let the likeliest regression
  through, which is pasting a tag over the SHA and leaving the `# v7.0.1` comment behind.
- Every job must set `timeout-minutes`. Without one a hung job runs to the six-hour
  platform default, which reads as slow CI rather than broken CI and holds a runner the
  whole time. Jobs are found as the two-space keys under `jobs:`, and a file the walk
  found no job in fails rather than passing — a parse that silently matches nothing is
  the failure this job exists to prevent.
- Every `actions/checkout` must set `persist-credentials: false`, including a checkout
  with no `with:` block at all. The `awk` walk is cross-checked against a plain `grep`
  count of the checkout steps, so a file whose shape it does not understand fails
  instead of reporting a clean run over steps it never saw.

The last two held by habit until they were gated. Both were correct across all twenty
jobs and eighteen checkouts on the day the check landed, which is the point: a ratchet
goes on while the invariant is true, not after it has already been broken.

## `.github/workflows/scheduled.yml` — Scheduled checks

Runs weekly (`cron: '0 6 * * 1'`) and on `workflow_dispatch`. Neither job gates anything.

| Job | Check name | Failing means |
| --- | --- | --- |
| `external-links` | `external links` | lychee could not reach an external URL. Hosts in `.lycheeignore` (example.com and friends, which appear inside skill instructions) are excluded. |

These are here because they depend on the network or a wordlist. A gate that fails
because someone else's site was briefly down is a gate people learn to override, and once
they learn that, the gates that matter stop working too.

## `.github/workflows/evals.yml` — Trigger evals

Three triggers: a monthly `schedule` (`0 7 1 * *`), `workflow_dispatch`, and
`pull_request`. There is no push trigger and, like `ci.yml`, no `paths:` filter — a
workflow skipped by a path filter leaves its check Pending forever, which is the failure
this repository refuses everywhere. Two jobs, and each is guarded by a job-level `if:` so
that exactly one of them runs on any given event:

| Job | Check name | Failing means |
| --- | --- | --- |
| `evaluate` | `score descriptions` | The whole catalogue, on the schedule or on request; skipped on a pull request. A skill scored below the `threshold` input, or a dispatched run has no credential. Nothing depends on this job and no branch rule requires it. Two-hour timeout, because it makes one model call per query per sample. |
| `evaluate-changed` | `score changed skills` | Only on a pull request; skipped otherwise. A skill the pull request changed, or one of that skill's declared neighbours, scored below **0.7**. Forty-five-minute timeout. |

### `evaluate-changed`, the pull request job

`evaluate` measures the catalogue on a cadence. What it cannot do is tell the author of a
new skill that it has taken a neighbour's queries, because the score that reveals the
collision belongs to the neighbour: one skill merged at 95% while breaking the eval set
of the skill next door, and on a monthly cadence nobody would have known for a month.

So the pull request job scores the changed skills **and their declared neighbours** —
every distinct `expected` value in a changed skill's `evals/trigger-eval.json`, resolved
to a skill directory under `plugins/*/skills/` or a subagent file under
`plugins/*/agents/` or `.claude/agents/`. Scoring only the changed skill would not catch
the case above, because the changed skill is the one that scores well.

What it does, in order:

1. Checks out with `fetch-depth: 0` so the base branch is reachable, and lists the
   changed files with `git diff --name-only "origin/${GITHUB_BASE_REF}...HEAD"`. Plain
   git rather than a changed-files action: this is one diff, and an action would be
   another pinned dependency in the supply chain for it.
2. Maps each changed path back to the skill directory that contains it, adds the
   neighbours, and caps the list at twelve targets. Past a dozen the run stops being a
   pull request check and becomes the monthly job; when it truncates, the summary says so
   and by how many.
3. Runs [`scripts/run_trigger_eval.py`](../scripts/run_trigger_eval.py) once per target.
   The harness takes exactly one target per invocation and rewrites `--json` wholesale,
   so each target writes its own results file and the publish step merges them into one
   table — the same six columns the monthly job prints. The merged files upload as the
   `trigger-evals-changed` artifact.

Three outcomes that are green on purpose:

- **No skill changed.** The job reports success with a note in the summary rather than
  being skipped, so nothing sits Pending.
- **No credential.** A pull request from a fork is handed no secrets. The job says so in
  a notice and stands down, because a red check a contributor has no way to make green is
  a check everybody learns to ignore. The same is now true of the scheduled run of
  `evaluate`: a scheduled run skips with a notice, and only a dispatched run — where a person
  asked for a score and is owed the error — fails on a missing credential.
- **A score between 0.7 and 0.8.** Reported in the summary and as a notice annotation,
  and advisory.

The floor is 0.7 rather than the 0.8 reporting bar because the measurement is sampled.
Run-to-run variance here is about five points — one skill read 85% and 90% on the same
tree — so a gate at 0.8 would fail on noise, and a gate that fails on noise is a gate
people learn to override, at which point the gates that matter stop working too. 0.7 sits
below the noise and still well above a description that has actually stopped working.
Anything under it fails the job with an error annotation naming the target.

An exit code of 1 from the harness means "below the reporting bar" and the job carries
on; anything higher means the harness itself failed — an unreachable model, a malformed
eval set — and stops the job with an error, because a run that cannot reach the model has
no score to report. The scores already paid for are published and uploaded either way.

### Dispatch inputs

The six inputs belong to `evaluate`; `evaluate-changed` takes none and always scores with
the `claude` backend at three samples per query. `skill` is marked required and the
others are not, but all carry a default, so dispatching the form unchanged scores
everything against Claude:

| Input | Default | What it does |
| --- | --- | --- |
| `skill` | `all` | A skill directory such as `plugins/operations/skills/ci-triage`, a subagent file such as `plugins/operations/agents/ci-log-reader.md`, or `all` for everything that has an eval set. |
| `budget` | empty | A listing budget in characters. Set it to score descriptions the way the runtime shows them — the runtime's default is about 8,000 on a 200k model — rather than at full length. |
| `runs` | `3` | Samples per query; must be odd. A majority vote across them decides, which separates a description that genuinely fails from one sitting on the model's decision boundary. |
| `threshold` | `0.8` | Pass rate below which a target is reported as failing. |
| `backend` | `claude` | Which model CLI answers: `claude`, `codex` (OpenAI) or `gemini`. The job installs only that one, at the version pinned in its `env`. |
| `model` | empty | A model name passed to the CLI. Blank uses the CLI's own default. |

The harness reads no API key of its own. Each CLI reads the credential it expects, and
the first step checks that the chosen backend has one, stopping with a one-line annotation
if not, because failing there beats failing forty model calls later with a stack trace. A
dispatched run fails on an absent credential; a scheduled run and a pull request skip with
a notice instead, for the reasons above:

| Backend | Repository secret | Where it comes from |
| --- | --- | --- |
| `claude` | `CLAUDE_CODE_OAUTH_TOKEN`, or `ANTHROPIC_API_KEY` | The token is a subscription login: run `claude setup-token` on a signed-in workstation and store what it prints. No API key or billing account is needed. |
| `codex` | `OPENAI_API_KEY` | The OpenAI platform. Locally, a ChatGPT login through `codex login` is enough. |
| `gemini` | `GEMINI_API_KEY` | Google AI Studio. Locally, a Google login through the CLI is enough. |

`evaluate` then runs [`scripts/run_trigger_eval.py`](../scripts/run_trigger_eval.py) with
`--backend`, writes a table of pass rate, recall, specificity, routing and the count of
narrowly decided queries into the job summary, and uploads the full results as the
`trigger-evals` artifact. Each result records the backend and model it was scored with, so
a `--baseline` diff against a run on a different model is visible for what it is. Download
that artifact and pass it back as `--baseline` on the next local run to see what an edit
moved.

Neither job is a required check, and that is the design rather than an omission. A trigger
eval has two halves that cost different amounts. The schema — twenty queries, at least
eight on each side, no duplicates, `should_trigger` a real boolean — is deterministic and
free, so `validate-skills` checks it on every push. The score is sampled and costs money
per run, so what it gets on a pull request is a floor well under the reporting bar rather
than a required check: a required check that is occasionally wrong is a check people
learn to override, and once they learn that, the checks that matter stop working too.

What the run measures is discrimination rather than recall alone. Each query is put to the
model alongside the descriptions of every skill in the repository at once, so a skill
counts as having fired only when the model picks it by name out of that catalogue — which
means a description that fires on everything passes its positives and fails its negatives.
Three numbers come back per skill: pass rate over all queries, recall over the positives,
and specificity over the negatives. Reading them, and writing the queries in the first
place, is covered in [writing a skill](writing-skills.md).

## Why the aggregator jobs exist

`ci` and `security` are otherwise-empty jobs that `needs:` every job in their workflow,
run `if: always()`, and fail when any dependency reports `failure` or `cancelled`. They
exist so that branch protection has a stable name to require.

The concrete problem: a matrix job's check name carries its parameters. The `test` job
appears as `test (3.10)`, `test (3.11)`, `test (3.12)` and `test (3.13)`. Requiring
`test (3.13)` works until someone drops 3.13 from the matrix or renames the matrix key,
at which point the required check never reports, and every pull request is blocked on a
check that no longer exists. A fixed-name aggregator does not have that property: the
jobs behind `ci` can change freely and the required check keeps the same name.

`if: always()` is load-bearing. Without it the aggregator would be skipped when a
dependency fails, and a skipped required check blocks the pull request rather than
failing it.

`scheduled.yml` and `evals.yml` have no aggregator, because nothing requires them. An
aggregator exists to give branch protection a stable name to point at; a workflow that
gates nothing has no use for one.

## Why there is no `paths:` filter

No workflow here has a `paths:` filter, and this is deliberate. `evals.yml` is the one
where the temptation is real — its pull request job has nothing to do unless a skill
changed — and it runs on every pull request anyway, reporting "no skill changed" in the
job summary.

A workflow skipped by a path filter does not report a result at all — its check sits
Pending forever. If that check is required, the pull request can never merge, and the
only escape is an admin override. A job skipped by an `if:` condition behaves
differently: it reports success, and the pull request merges. The two look like the same
mechanism and are not.

This repository is small enough that running everything on every change is cheaper than
the failure mode. Where a skip is genuinely wanted, use a job-level `if:`, never a
workflow-level `paths:`.

## Pinning, timeouts and checkout conventions

Every action is pinned to a full-length commit SHA with the version in a trailing
comment:

```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7
  with:
    persist-credentials: false
```

A tag is a mutable reference — the maintainer can move `v7`, and a compromised account
can move it to anything. A SHA cannot be moved. The trailing `# v7.0.1` comment is not
decoration: Dependabot parses it to identify which action version the SHA corresponds
to, and without it the SHA stops being updated. `.github/dependabot.yml` has the
`github-actions` ecosystem on a weekly schedule.

Comment the exact release tag, not the major. A `# v7` is true only until upstream moves
the floating `v7` tag to a newer commit, at which point the comment quietly describes a
different version from the one being run — and zizmor's `ref-version-mismatch` fails the
`security` gate for it. That is not a hypothetical: it is how `codespell-project/actions-codespell`
and `github/codeql-action` first broke here, months after being pinned correctly.

A tool downloaded rather than used as an action gets the same treatment as far as the
mechanism allows. `lint-actions` fetches a specific actionlint release and verifies it
against a recorded SHA-256 before running it, and `secrets` fetches gitleaks the same
way:

```yaml
run: |
  set -Eeuo pipefail
  archive="actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
  curl -fsSL -o "$archive" \
    "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/${archive}"
  echo "${ACTIONLINT_SHA256}  ${archive}" | sha256sum --check --status
  tar -xzf "$archive" actionlint
  ./actionlint -color
```

The upstream instructions are a `curl | bash` of a script on a moving branch, which the
`image-hardening` skill describes as adding an unreviewed commit author to your build.
A repository that publishes that advice should not run CI that way. Bumping the version
means bumping the digest beside it; if the two disagree the job fails before the binary
executes, which is the whole point.

`persist-credentials: false` is on every checkout. By default `actions/checkout` writes
the job's token into `.git/config`, where any subsequent step — including anything a
build script pulls in — can read it and push with it. None of these jobs push, so none of
them need the credential to survive the checkout step.

Every job sets `timeout-minutes` — ten for most, twenty for CodeQL, forty-five for the
eval scoring, five for the aggregators. The default is six hours, which is long enough
that a hung step looks like a slow one for most of a working day, and it holds a runner
the whole time. A timeout turns that into a failure with a name.

Both of those are enforced rather than remembered: `permissions-audit` fails the
`security` gate for a job with no `timeout-minutes` and for a checkout that does not set
`persist-credentials: false`. They were conventions held by habit for as long as the
workflows existed, and a convention held by habit is one the next job quietly skips.

## Making CI authoritative

The workflows only mean something if the checks are required. Create a ruleset on the
default branch:

```bash
gh api --method POST /repos/greenblacked/AI/rulesets \
  --input - <<'JSON'
{
  "name": "default branch protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "ci" },
          { "context": "security" }
        ]
      }
    }
  ]
}
JSON
```

Three things to note. `~DEFAULT_BRANCH` is a symbolic target, so the ruleset follows the
default branch if it is ever renamed. `strict_required_status_checks_policy: true`
requires the branch to be up to date with its base before merging, which is what stops
two individually-green pull requests from combining into a red `main`. The `deletion` and
`non_fast_forward` rules block branch deletion and force-pushes.

This requires repository admin. A workflow's `GITHUB_TOKEN` cannot create or modify
rulesets no matter what `permissions:` it is granted, so this is a one-time manual step
by an owner, not something to automate in Actions.

Verify with:

```bash
gh api /repos/greenblacked/AI/rulesets
```

## Running the checks locally

```bash
make validate   # skills, subagents, commands, rules and the manifest — the validate-skills job
make catalogue  # listing ceilings, README drift, shell blocks — the catalogue job
make portable   # flatten every skill for ChatGPT, Grok and other assistants
make test       # pytest — the test job
make coverage   # the same run under coverage, failing below the floor
make lint       # ruff, markdownlint, yamllint, actionlint, codespell — the lint jobs
make package    # .skill archives into dist/ — the package job
```

`make validate` passes `--strict`, exactly as the job does, so a warning fails locally
before it fails in CI.

`make coverage` needs `coverage` installed alongside `pytest`. The suite reaches the
scripts as well as the validator: the eval harness runs against a fake `claude` on
`PATH` that answers from a table, `install.sh` runs against a temporary target
directory, and the packager and the `PostToolUse` hook run against a small repository
built in a temporary directory. The floor is set below the measured figure on purpose.
It exists to catch a script sliding back to untested, which is the state the harness and
the packager were in before the suite covered them, not to be chased.

`make lint` skips a tool that is not installed and prints how to get it, so a partial
local toolchain does not block you; CI has all of them.

`make catalogue` needs nothing installed beyond `bash`. It is the four checks that
keep the repository's claims about itself true — the per-plugin listing ceilings, whether
the README still lists every skill, subagent and command that exists and nothing that
does not, whether every shell block and shipped script actually parses, and whether the
hook registered in `.claude/settings.json` names a script that is there and executable.
Each failure is invisible without a gate: the first costs you the skills you use least,
silently; the second is only ever caught by someone reading; the third ships a
command that reads fine and fails in someone else's terminal; and the fourth turns the
hook off, so skills are written unvalidated and the first sign of it is one reaching CI
weeks later. `.claude/settings.json` is read by the runtime and by nothing else here,
which is why the path in `command` needed a check of its own rather than a habit.

The trigger evals are not part of `make`, because they need a model and a key. Run them
directly when a description is the thing in question:

```bash
python scripts/run_trigger_eval.py --skill plugins/operations/skills/ci-triage --verbose
```

The security tooling is not wrapped in a `make` target, because the versions are pinned
in the workflow rather than in the repository. Reproduce it directly, matching the
versions in `security.yml`:

```bash
python -m pip install "zizmor==1.29.0" "ruff==0.16.1"
zizmor --persona=regular --min-severity=medium .
ruff check .
ruff format --check .
```

## Reproducing a failure

1. **Read the annotations before the log.** The validator emits
   `::error file=…,line=…,title=<code>::…` so failures land on the right line of the
   diff, and writes a per-skill table into the job summary. ruff and yamllint both run
   with GitHub output formats for the same reason.
2. **Pull only the failed step's log** rather than the whole run:

   ```bash
   gh run view <run-id> --log-failed
   ```

3. **Match the interpreter.** A `test` failure names its Python version in the check
   name. Reproducing 3.10 on 3.13 is not reproducing.
4. **Re-run the exact command.** Every job in `ci.yml` is one command; the `make` targets
   above wrap the same invocations. `make validate` runs
   `PYTHONPATH=src python3 -m skillcheck . --strict`, which is what the job runs — down
   to the flag, so a warning that fails CI fails locally too.

`validate-skills` also reads `.claude/rules/`, which is loaded into the session rather
than shipped to installers. A rule scoped with a `paths:` glob loads only when Claude
reads a matching file, so a glob with a typo in it never matches, the rule never loads,
and nothing else would ever say so — `dangling-glob` and `empty-paths` are that failure
made loud. [Project structure](project-structure.md) has the rest of what the loader
picks up automatically.

For the reasoning behind the rules `validate-skills` enforces, see [writing a
skill](writing-skills.md). For the subagents referenced by the manifest, see [writing a
subagent](writing-agents.md).
