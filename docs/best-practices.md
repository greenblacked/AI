# Best practices: CI, security, and branching and merging

This page is for anyone deciding what to change next in this repository's engineering
process — the maintainer, and any agent asked to propose the next hardening step. It
lists the practice, why it matters, how (or whether) this repository applies it today,
and a status.

Status is judged against what is actually in the tree or documented as configured on
GitHub, not against intent: **Adopted** means a file or check enforces it today,
**Partial** means it holds in practice but nothing gates or fully covers it, and **Not
yet adopted** means nothing here does it. Two changes are in progress elsewhere at the
time of writing — a CI naming lint for branches, commits and file names, and review
guidelines being added to `AGENTS.md` and a new `REVIEW.md` — and are marked as being
added rather than as already running.

## CI

| Practice | Why it matters | How this repository applies it | Status |
| --- | --- | --- | --- |
| One aggregate required check per workflow | A matrix job's check name carries its parameters (`test (3.13)`); requiring it directly breaks the day the matrix changes. A fixed-name aggregate does not. | `ci` and `security` in [`docs/ci.md`](ci.md#why-the-aggregator-jobs-exist), enforced by `scripts/check_job_results.py` | Adopted |
| Every job the aggregate needs is actually named in `needs:` | A job left out of the aggregate can go red while the required check still reports success. | `scripts/check_workflows.py`, part of `make catalogue`, checks the aggregate names every job in its own workflow | Adopted |
| Fast lint before slow tests | A style or spelling failure that could be caught in seconds should not wait behind a multi-version test matrix. | Lint jobs (`spelling`, `lint-markdown`, `lint-yaml`, `lint-actions`, `links`) run in parallel with `test`, not serialised after it, in [`ci.yml`](../.github/workflows/ci.yml) | Partial — parallel rather than gated first, so a lint failure does not shorten the run |
| A matrix only where it proves something | A matrix that does not change behaviour between legs costs runner time for no information. | `test` runs Python 3.10–3.13 because the validator promises to run on a bare interpreter across that range ([`docs/ci.md`](ci.md#githubworkflowsciyml--ci)); nothing else here is matrixed | Adopted |
| Timeouts on every job | Without one, a hung job runs to the six-hour platform default and holds a runner the whole time. | `permissions-audit` in `security.yml` fails the `security` gate for any job missing `timeout-minutes` ([`docs/ci.md`](ci.md#the-security-jobs-in-detail)) | Adopted |
| Concurrency cancelling superseded runs | Rerunning a stale check for a PR that has already moved on wastes runner time and can report on code nobody will merge. | [`docs/ci.md`](ci.md#execution-flow)'s table: a newer PR run supersedes the older one; `release.yml` groups by tag with `cancel-in-progress: false`, deliberately, since a release must not be cancelled mid-publish | Adopted |
| Caching, and never on release triggers | Restoring a cache seeded by an earlier, less trusted run onto a job about to publish with write access is how a cache becomes a supply-chain hole. | The five PyPI-installing jobs and `validate-plugin` cache; `release.yml` explicitly does not, citing zizmor's cache-poisoning audit ([`docs/ci.md`](ci.md#githubworkflowsreleaseyml--release)) | Adopted |
| Pinned tool versions with a digest | An unpinned or tag-pinned tool changes underneath the build; a green run stops meaning anything about the code. | Every downloaded binary (actionlint, gitleaks) is fetched at a pinned version and checked against a recorded SHA-256 before running ([`docs/ci.md`](ci.md#pinning-timeouts-and-checkout-conventions)) | Adopted |
| The same commands locally as in CI | A gate a contributor cannot reproduce is a gate they learn to ignore until CI disagrees with them. | `make validate`, `make catalogue`, `make test` are exactly what the equivalent jobs run, down to the flags ([`AGENTS.md`](../AGENTS.md#testing-instructions)) | Adopted |
| Coverage floors | A floor that only ever rises catches a script sliding back to untested without demanding coverage for its own sake. | `test (3.13)` measures coverage and enforces the floor in [`pyproject.toml`](../pyproject.toml) | Adopted |
| Docs that list every job | A job with no row in the docs is a red check someone has to reverse-engineer out of YAML. | `scripts/check_ci_docs.py`, part of `make catalogue`, checks [`docs/ci.md`](ci.md) against the jobs each workflow actually defines | Adopted |
| Scheduled runs for drift | Some facts (an upstream pin falling behind, an external link rotting) only change with the passage of time, not with a commit here. | [`scheduled.yml`](../.github/workflows/scheduled.yml) runs `external-links` and `pin-freshness` weekly | Adopted |
| Model-dependent evals kept out of the merge gate | A required check that is occasionally wrong on sampling noise is a check people learn to override. | [`evals.yml`](../.github/workflows/evals.yml) has no aggregate and requires nothing; its PR job reports a floor under the scoring bar for exactly this reason ([`docs/ci.md`](ci.md#githubworkflowsevalsyml--trigger-evals)) | Adopted — though the credential that would let it score anything is absent, so it currently scores nothing ([`docs/ci.md`](ci.md#the-eval-credential)) |
| Flaky-test policy: never skip, root-cause | A skipped flaky test is a gap in coverage wearing a green checkmark. | No documented policy or precedent exists yet — the test suite has not produced a flaky case to set one against | Not yet adopted |
| Naming lint for branches, commits and file names | A convention enforced only by review is a convention that erodes; a gate catches it on the branch that breaks it. | Branch naming is already checked by `scripts/check_attribution.py` ([`CONTRIBUTING.md`](../CONTRIBUTING.md#naming-a-branch)); a broader naming lint covering commits and file names, plus ruff's pep8-naming rules, is being added separately | Partial — branch names are covered today; the wider lint is being added |

## Security

| Practice | Why it matters | How this repository applies it | Status |
| --- | --- | --- | --- |
| Top-level `permissions: {}` and least privilege per job | An absent `permissions:` block inherits the repository default, which is usually write access to everything. | Every workflow sets an empty top-level block; each job grants only what it needs — checked by `permissions-audit` ([`AGENTS.md`](../AGENTS.md#security-considerations)) | Adopted |
| Actions pinned to full SHAs with exact version comments | A tag is mutable; a SHA is not. The comment is what lets Dependabot bump a SHA it cannot otherwise identify. | `permissions-audit` rejects any ref that is not forty hex characters; zizmor's `ref-version-mismatch` catches a stale comment ([`docs/ci.md`](ci.md#pinning-timeouts-and-checkout-conventions)) | Adopted |
| `persist-credentials: false` | The default leaves the job's token in `.git/config`, readable and pushable by any later step. | `permissions-audit` rejects any `actions/checkout` that omits it, including one with no `with:` block at all | Adopted |
| No `${{ }}` interpolation in `run:` blocks | Interpolating untrusted input directly into a shell command is template injection into CI. | Every workflow passes such values through an `env:` block instead; zizmor's template-injection audit is one of the checks `workflows` runs | Adopted |
| `pull_request_target` avoided | Combined with a checkout of untrusted code, it runs with base-branch secrets against a fork's content. | `dependabot-auto-merge.yml` uses plain `pull_request` and says why in its own header comment | Adopted |
| Secret scanning over history | A secret committed and later removed is still leaked — the object remains reachable. | `secrets` job runs `gitleaks dir .` and `gitleaks git .` with `fetch-depth: 0` ([`docs/ci.md`](ci.md#the-security-jobs-in-detail)) | Adopted |
| SAST | Static analysis catches classes of bug review does not reliably. | CodeQL's `security-extended` suite over Python, plus ruff's flake8-bandit (`S`) rule set ([`docs/ci.md`](ci.md#the-security-jobs-in-detail)) | Adopted |
| Workflow audit | CI configuration is itself an attack surface — a workflow can grant itself more than the job needs. | zizmor at `--min-severity=medium` in the `workflows` job | Adopted |
| Dependency updates with bounded auto-merge | Routine bumps should not need a human, but a major version is a judgement call. | [`.github/dependabot.yml`](../.github/dependabot.yml) groups minor/patch actions updates weekly with a seven-day cooldown; [`dependabot-auto-merge.yml`](../.github/workflows/dependabot-auto-merge.yml) merges only patch/minor Dependabot PRs, and only once `ci` and `security` both report success | Adopted |
| Signed commits | A signature ties a commit to a key, which is one more thing an attacker would need to forge alongside push access. | Recent commits on `origin/main` carry a GPG signature (`git log --show-signature`), but the branch ruleset documented in [`docs/ci.md`](ci.md#making-ci-authoritative) does not include a signature requirement, so an unsigned commit would not be blocked | Partial |
| CODEOWNERS | Routes review to the person who should see a given path change. | No `CODEOWNERS` file exists in the tree, and the documented ruleset sets `require_code_owner_review: false` | Not yet adopted |
| Branch and tag rulesets | Encodes "PR required, no direct push, checks must be up to date" as a platform rule rather than a habit. | The ruleset in [`docs/ci.md`](ci.md#making-ci-authoritative) requires a pull request (0 approvals — this repository has one maintainer), strict `ci` and `security`, and blocks deletion and force-push on `main`; no separate tag ruleset is documented | Partial — branch ruleset documented and adopted; no tag ruleset |
| Release provenance or attestations (SLSA) | Lets a consumer verify what built an artefact and from what source, rather than trusting the upload. | [`release.yml`](../.github/workflows/release.yml) builds and uploads `.skill` archives and a portable zip via `gh release`, with no signed provenance attestation attached (see the [SLSA build levels](https://raw.githubusercontent.com/slsa-framework/slsa/v1.2/docs/spec/v1.0/levels.md)) | Not yet adopted |
| OIDC instead of long-lived secrets | Removes a standing credential that can leak; a cloud provider issues a short-lived token per run instead. | Nothing here deploys to a cloud provider that OIDC would authenticate to — the only secrets in use are `GITHUB_TOKEN` (already short-lived and scoped) and the eval workflow's model API keys, which are not something [GitHub's OIDC support](https://raw.githubusercontent.com/github/docs/main/content/actions/concepts/security/openid-connect.md) replaces | Not yet adopted (not currently applicable) |
| A GitHub environment with required reviewers gating a release | Adds a human approval step between a tag existing and a release being published, regardless of what the workflow itself checks. | `release.yml` has no `environment:` key; nothing pauses it for review beyond its own automated checks (see [GitHub's environments doc](https://raw.githubusercontent.com/github/docs/main/content/actions/reference/workflows-and-actions/deployments-and-environments.md)) | Not yet adopted |
| A SECURITY.md disclosure policy | A reporting route nobody can find is equivalent to not having one. | [`SECURITY.md`](../SECURITY.md) points to GitHub's private security advisory form | Adopted |
| The licence notice travelling with artefacts | An extracted `.skill` archive or portable export should carry the licence it was distributed under, not rely on the source repository. | `scripts/package_skills.py` and `scripts/export_portable.py` both copy `LICENSE` and `NOTICE` into every artefact they build | Adopted |
| No attribution (no tool or AI-assistant trailers in commits or PRs) | A commit's authorship should read as the person who wrote it; a trailer naming a tool misattributes it. | `scripts/check_attribution.py` runs as the `attribution` job on every pull request and rejects `Co-authored-by` trailers, assistant footers and session links ([`AGENTS.md`](../AGENTS.md#commit-and-pull-request-instructions)) | Adopted |
| The OpenSSF Scorecard itself | An external, standardised score covering most of the rows above in one number, comparable across repositories (see the [Scorecard checks](https://raw.githubusercontent.com/ossf/scorecard/main/docs/checks.md)). | Not run against this repository, on demand or on a schedule | Not yet adopted |

## Branching and merging

| Practice | Why it matters | How this repository applies it | Status |
| --- | --- | --- | --- |
| Trunk-based development with short-lived branches from `main` | Long-lived branches accumulate drift and merge conflicts; short branches keep review small and `main` close to what is deployed. | Every change here is a branch from `main` merged back through a pull request; the changelog and release process assume a single trunk ([`CHANGELOG.md`](../CHANGELOG.md)) | Adopted |
| `<type>/<kebab>` branch names | One shape for every branch means the attribution and naming checks only have to parse one thing, and a reader knows what a branch does without opening it. | [`CONTRIBUTING.md#naming-a-branch`](../CONTRIBUTING.md#naming-a-branch), enforced by `scripts/check_attribution.py` | Adopted |
| Pull request required, no direct push to `main` | Puts every change through the checks that only run on a pull request, and gives it a place to be reviewed. | The ruleset's `pull_request` rule in [`docs/ci.md`](ci.md#making-ci-authoritative); `AGENTS.md`'s boundary against pushing to `main` directly | Adopted |
| Required checks with strict "up to date" | Without strict mode, two individually green pull requests can still combine into a red `main`. | `strict_required_status_checks_policy: true` in the documented ruleset ([`docs/ci.md`](ci.md#making-ci-authoritative)) | Adopted |
| Squash merge with the PR title as the subject | Keeps `main`'s history at one commit per change, with a subject a reader chose rather than one assembled from every fixup. | Merged commit subjects on `main` carry the PR number in the shape GitHub's default squash merge produces (for example, "Document and enforce the branch naming convention (#63)"), but the ruleset's `allowed_merge_methods` was left at GitHub's default of all three methods rather than restricted to squash ([`docs/ci.md`](ci.md#making-ci-authoritative)) | Partial |
| Delete branches on merge | An unpruned branch list is dead weight in `git branch -r` and confusing to a contributor unsure whether it is still live. | 53 branches exist on `origin` today, most already merged; nothing here restricts or deletes them | Not yet adopted |
| Auto-merge only where checks gate it | Auto-merge without a gate behind it is just deferred direct-push. | `dependabot-auto-merge.yml` only calls `gh pr merge --auto` after confirming the update is patch or minor, and the merge itself still waits on `ci` and `security` | Adopted |
| Releases as tags cut from `main` | Ties every published release to a reviewed, merged commit rather than to whatever a branch happened to contain. | [`docs/ci.md#releasing-a-version`](ci.md#releasing-a-version); `release.yml` refuses a tag whose commit is not an ancestor of `main` | Adopted |
| Hygiene for stale branches | A pile of long-dead branches makes it harder to tell an abandoned attempt from a live one. | Eight remote branches on `origin` today do not match the `<type>/<kebab>` shape (for example `bump-stale-tool-pins`, `feature/delivery-agents`) — mostly branches that predate the naming convention landing; no scheduled job or process prunes stale branches | Not yet adopted |
| Merging a stale head is prevented by an expected-head-SHA merge | Stops a merge from landing on top of a `main` that has moved since the check was last green. | Strict required-status-checks already force a branch to be up to date before merging; no tooling here separately passes an expected head SHA to the merge API | Partial — covered by strict mode, not by an explicit expected-head-SHA check |
| A linear history | Makes `git log` and `git bisect` on `main` read as one line of changes rather than a lattice of merge commits. | Consistent with squash-merging in practice; the ruleset does not itself force it, since `allowed_merge_methods` was not restricted (see the row above) | Partial |
| Review guidelines for pull requests | Names what a reviewer should look for so review does not depend on whoever happens to be doing it that day. | Being added to `AGENTS.md` and a new `REVIEW.md`; neither exists on `main` at the time of writing | Not yet adopted |

## Next steps, in priority order

1. **Restrict `allowed_merge_methods` to squash-only in the branch ruleset.** The
   repository already merges this way in practice; the ruleset payload in
   [`docs/ci.md`](ci.md#making-ci-authoritative) needs `"allowed_merge_methods": ["squash"]`
   added explicitly, which also settles the linear-history and squash-merge rows above.
2. **Enable delete-branch-on-merge and clean up the eight stale branches.** A repository
   setting plus one pass of `git push origin --delete` on the branches this document
   lists turns the "hygiene" row from Not yet adopted to Adopted in an afternoon.
3. **Add a `CODEOWNERS` file, even a one-line one.** With a single maintainer it cannot
   route review to a second person yet, but it is the file a second maintainer's review
   requirement would attach to, and its absence is otherwise silent.
4. **Add a `GitHub environment` with required reviewers to gate `release.yml`.** The
   workflow already bounds its `contents: write` grant three ways; an environment adds a
   human checkpoint between a tag existing and a release being published, independent of
   what the automated checks already covered.
5. **Fund the eval credential.** `evals.yml`'s scoring machinery — the harness, every
   skill's eval set, and the docs describing what the numbers mean — has run against no
   credential since it was built, per [`docs/ci.md`](ci.md#the-eval-credential); one
   `CLAUDE_CODE_OAUTH_TOKEN` secret turns "not yet adopted" into "measured monthly and on
   every relevant pull request."
