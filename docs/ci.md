# CI

CI is the source of truth for whether this repository is correct. Everything a reviewer
would otherwise check by eye — that a skill validates, that its reference files exist,
that it is listed in the marketplace, that no secret is in history — is a job that either
passes or does not. Four workflows run it: two that gate every change, one that runs
weekly, and one that only runs when somebody asks for it.

## `.github/workflows/ci.yml` — CI

Triggers on push to `main`, on every pull request, and on `workflow_dispatch`. Top-level
`permissions: {}`; each job grants itself the minimum.

| Job | Check name | Failing means |
| --- | --- | --- |
| `validate-skills` | `validate skills` | A skill, a subagent or the manifest is invalid: bad frontmatter, a name that does not match its directory or filename, a dangling `references/` pointer, a malformed trigger-eval set, or something on disk that no plugin lists. Runs with `--strict`, so a warning fails it too. Run `make validate` locally to see the same output. |
| `validate-plugin` | `validate plugin manifest` | `claude plugin validate .` rejected `.claude-plugin/marketplace.json`. The schema's source of truth is the definition inside the CLI itself, so this checks against the real thing rather than a copy that would fall behind. The CLI version is pinned in the job's `env` for the same reason the scanners are. |
| `test` | `test (3.10)` … `test (3.13)` | The validator's own test suite failed on that interpreter. The matrix is four versions because [`pyproject.toml`](../pyproject.toml) declares no dependencies, and running on a bare interpreter across the supported range is how that claim stays true. |
| `lint-markdown` | `lint markdown` | markdownlint-cli2 found a violation in a `*.md` file. Config in `.markdownlint-cli2.yaml`. |
| `lint-yaml` | `lint yaml` | yamllint in `--strict` mode found a problem. Config in `.yamllint.yaml`. |
| `lint-actions` | `lint workflows` | actionlint rejected a workflow. It also runs shellcheck over every inline `run:` block, which is where all of this repository's shell lives. The binary is downloaded at a pinned version and checked against a recorded digest before it runs. |
| `links` | `check links` | lychee found a broken link. It runs `--offline`, so only local paths are resolved — a relative link between documents, or from a document into the source tree, that does not exist. |
| `package` | `package` | `scripts/package_skills.py` could not build a `.skill` archive for every skill. It refuses to package a skill that does not validate, so this failing after `validate-skills` passed means a packaging problem, not a content one. The archives upload as the `skills` artifact. |
| `ci` | `ci` | One of the eight jobs above failed or was cancelled. |

`validate-skills` runs `PYTHONPATH=src python -m skillcheck . --strict`, the same
invocation as `make validate`. The flag is the point: without it, a description one edit
from the 1024-character cap, a skill with no trigger clause, and a skill with no eval set
all report and pass. They are warnings because each is a judgement call rather than a
rule, and they fail the build anyway, because a warning nobody has to clear is a warning
that accumulates until the whole category is ignored.

## `.github/workflows/security.yml` — Security

Same triggers, same empty top-level `permissions`. Tool versions are pinned in `env`
(`GITLEAKS_VERSION`, `ZIZMOR_VERSION`, `RUFF_VERSION`) rather than floated: a scanner that
changes its rule set between runs turns a green build into a statement about the scanner
rather than about the code. ruff is in that list for a concrete reason — 0.16 began
formatting Python blocks inside Markdown, so an unpinned upgrade would fail the build on
skill prose that was green the day before.

| Job | Check name | Failing means |
| --- | --- | --- |
| `secrets` | `secret scan` | gitleaks found a credential. |
| `workflows` | `workflow audit` | zizmor found a workflow vulnerability at medium severity or above. |
| `python` | `python security lint` | `ruff check` or `ruff format --check` failed. |
| `codeql` | `codeql` | CodeQL's `security-extended` query suite found something in the Python source. |
| `permissions-audit` | `permissions audit` | A workflow has no top-level `permissions:` block, or an action is not pinned to a SHA. |
| `security` | `security` | One of the five jobs above failed or was cancelled. |

### The security jobs in detail

**gitleaks runs twice, over different things.** `gitleaks dir .` scans the working tree;
`gitleaks git .` scans history, which is why the checkout uses `fetch-depth: 0`. Scanning
only the working tree misses the case that matters most: a secret that was committed and
later removed is still a leaked secret, because the object is still in the repository and
anyone who cloned it has a copy. Both invocations use `--redact` so the finding does not
put the secret in the log.

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

**Two shell invariants.** `permissions-audit` is two `grep` loops, deliberately not a
tool:

- Every workflow file must set a top-level `permissions:` block. An absent block means
  jobs inherit the repository default, which is often read and write on everything. The
  failure is silent and permanent, which is exactly the kind worth a one-line check.
- Every action must be pinned to a commit SHA. The check greps for `uses:` lines ending
  in `@v1.2`, `@main` or `@master` and fails on any match.

## `.github/workflows/scheduled.yml` — Scheduled checks

Runs weekly (`cron: '0 6 * * 1'`) and on `workflow_dispatch`. Neither job gates anything.

| Job | Check name | Failing means |
| --- | --- | --- |
| `external-links` | `external links` | lychee could not reach an external URL. Hosts in `.lycheeignore` (example.com and friends, which appear inside skill instructions) are excluded. |
| `spelling` | `spelling` | codespell found a likely typo. Set to `only_warn: 1`, so it reports without failing. |

These are here because they depend on the network or a wordlist. A gate that fails
because someone else's site was briefly down is a gate people learn to override, and once
they learn that, the gates that matter stop working too.

## `.github/workflows/evals.yml` — Trigger evals

`workflow_dispatch` only: there is no push, pull-request or schedule trigger, so this
workflow runs when a person asks for it and at no other time. One job, `evaluate`, check
name `score descriptions`, with a 45-minute timeout because it makes one model call per
query per sample.

| Input | Default | What it does |
| --- | --- | --- |
| `skill` | `all` | A skill directory to score, such as `skills/engineering/ci-triage`, or `all` for every skill that has an eval set. |
| `runs` | `3` | Samples per query. A majority vote across them decides, which separates a description that genuinely fails from one sitting on the model's decision boundary. |
| `threshold` | `0.8` | Pass rate below which a skill is reported as failing. |

It needs an `ANTHROPIC_API_KEY` repository secret. The first step checks for it and stops
with a one-line annotation if it is absent, because failing there beats failing forty API
calls later with a stack trace. The job then installs the pinned `claude` CLI and runs
[`scripts/run_trigger_eval.py`](../scripts/run_trigger_eval.py), writes a pass rate,
recall and specificity table into the job summary, and uploads the full results as the
`trigger-evals` artifact.

Nothing here gates anything, and that is the design rather than an omission. The schema of
every `evals/trigger-eval.json` is checked by `validate-skills` on every push, because
that check is deterministic and free. Scoring the queries is sampled and costs money, so
it stays manual: a required check that is occasionally wrong is a check people learn to
override. What the run measures, and how to read the three numbers, is in [writing a
skill](writing-skills.md).

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

Neither `ci.yml` nor `security.yml` has a `paths:` filter, and this is deliberate.

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
can move it to anything. A SHA cannot be moved. The trailing `# v7` comment is not
decoration: Dependabot parses it to identify which action version the SHA corresponds
to, and without it the SHA stops being updated. `.github/dependabot.yml` has the
`github-actions` ecosystem on a weekly schedule.

A tool downloaded rather than used as an action gets the same treatment as far as the
mechanism allows. `lint-actions` fetches a specific actionlint release and verifies it
against a recorded SHA-256 before running it:

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
make validate   # skills, subagents and the manifest — the validate-skills job
make test       # pytest — the test job
make lint       # ruff, markdownlint, yamllint, actionlint — the lint jobs
make package    # .skill archives into dist/ — the package job
```

`make validate` passes `--strict`, exactly as the job does, so a warning fails locally
before it fails in CI.

`make lint` skips a tool that is not installed and prints how to get it, so a partial
local toolchain does not block you; CI has all of them.

The trigger evals are not part of `make`, because they need a model and a key. Run them
directly when a description is the thing in question:

```bash
python scripts/run_trigger_eval.py --skill skills/engineering/ci-triage --verbose
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

For the reasoning behind the rules `validate-skills` enforces, see [writing a
skill](writing-skills.md). For the subagents referenced by the manifest, see [writing a
subagent](writing-agents.md).
