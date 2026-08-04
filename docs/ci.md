# CI

CI is the source of truth for whether this repository is correct. Everything a reviewer
would otherwise check by eye — that a skill validates, that its reference files exist,
that it is listed in the marketplace, that no secret is in history — is a job that either
passes or does not. Three workflows run it.

## `.github/workflows/ci.yml` — CI

Triggers on push to `main`, on every pull request, and on `workflow_dispatch`. Top-level
`permissions: {}`; each job grants itself the minimum.

| Job | Check name | Failing means |
| --- | --- | --- |
| `validate-skills` | `validate skills` | A skill is invalid: bad frontmatter, a name that does not match its directory, a dangling `references/` pointer, or a skill missing from the marketplace manifest. Run `make validate` locally to see the same output. |
| `validate-plugin` | `validate plugin manifest` | `claude plugin validate .` rejected `.claude-plugin/marketplace.json`. The schema's source of truth is the definition inside the CLI itself, so this checks against the real thing rather than a copy that would fall behind. The CLI version is pinned in the job's `env` for the same reason the scanners are. |
| `test` | `test (3.10)` … `test (3.13)` | The validator's own test suite failed on that interpreter. The matrix is four versions because [`pyproject.toml`](../pyproject.toml) declares no dependencies, and running on a bare interpreter across the supported range is how that claim stays true. |
| `lint-markdown` | `lint markdown` | markdownlint-cli2 found a violation in a `*.md` file. Config in `.markdownlint-cli2.yaml`. |
| `lint-yaml` | `lint yaml` | yamllint in `--strict` mode found a problem. Config in `.yamllint.yaml`. |
| `lint-actions` | `lint workflows` | actionlint rejected a workflow. It also runs shellcheck over every inline `run:` block, which is where all of this repository's shell lives. |
| `links` | `check links` | lychee found a broken link. It runs `--offline`, so only local paths are resolved — a relative link between documents, or from a document into the source tree, that does not exist. |
| `package` | `package` | `scripts/package_skills.py` could not build a `.skill` archive for every skill. It refuses to package a skill that does not validate, so this failing after `validate-skills` passed means a packaging problem, not a content one. The archives upload as the `skills` artifact. |
| `ci` | `ci` | One of the eight jobs above failed or was cancelled. |

## `.github/workflows/security.yml` — Security

Same triggers, same empty top-level `permissions`. Tool versions are pinned in `env`
(`GITLEAKS_VERSION`, `ZIZMOR_VERSION`) rather than floated: a scanner that changes its
rule set between runs turns a green build into a statement about the scanner rather than
about the code.

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

## Pinning and checkout conventions

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

`persist-credentials: false` is on every checkout. By default `actions/checkout` writes
the job's token into `.git/config`, where any subsequent step — including anything a
build script pulls in — can read it and push with it. None of these jobs push, so none of
them need the credential to survive the checkout step.

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
make validate   # skills and marketplace manifest — the validate-skills job
make test       # pytest — the test job
make lint       # markdownlint, yamllint, actionlint — the three lint jobs
make package    # .skill archives into dist/ — the package job
```

`make lint` skips a tool that is not installed and prints how to get it, so a partial
local toolchain does not block you; CI has all three.

The security tooling is not wrapped in a `make` target, because the versions are pinned
in the workflow rather than in the repository. Reproduce it directly, matching the
versions in `security.yml`:

```bash
python -m pip install "zizmor==1.29.0" ruff
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
   `PYTHONPATH=src python3 -m skillcheck .`, which is what the job runs.

For the reasoning behind the rules `validate-skills` enforces, see [writing a
skill](writing-skills.md). For the subagents referenced by the manifest, see [writing a
subagent](writing-agents.md).
