# Credentials, federation and provenance

Read this during step 3, for what a job can reach, and step 6, for moving a stored key to
federation. It does not repeat the `GITHUB_TOKEN` scope table — that lives in
`plugins/operations/skills/ci-triage/references/github-actions.md`, under "The
permissions block" — because the two skills would drift the moment one was edited and
not the other.

## Contents

- [`GITHUB_TOKEN`: what reach actually means here](#github_token-what-reach-actually-means-here)
- [OIDC federation, per provider](#oidc-federation-per-provider)
- [Pin the whole subject, and the audience](#pin-the-whole-subject-and-the-audience)
- [`persist-credentials: false`](#persist-credentials-false)
- [Cache scope across the fork boundary](#cache-scope-across-the-fork-boundary)
- [Artefact attestation and verification at the consumer](#artefact-attestation-and-verification-at-the-consumer)
- [What SLSA level a hosted builder actually gives](#what-slsa-level-a-hosted-builder-actually-gives)

## `GITHUB_TOKEN`: what reach actually means here

`ci-triage`'s reference has the full per-scope table for reading a permission-denied
failure. What this skill adds is the adversarial reading of the same table: for every
scope a job holds, ask not "what does this job need" but "what could this job's most
attacker-influenced step do with it". A job that runs `npm ci` against a `package.json`
the pull request controls and also holds `contents: write` can be made to push a commit,
not just install a dependency — the postinstall script runs with the job's token in its
environment whether or not the workflow author meant to grant it that. Read the scope
table there; judge it here.

## OIDC federation per provider

The shape is the same everywhere: the job requests a token from GitHub's own OIDC
issuer (`token.actions.githubusercontent.com`), presents it to the cloud provider, and
receives a short-lived credential in exchange. Nothing long-lived sits in a secret at
any point.

| Provider | Mechanism | Condition to check |
| --- | --- | --- |
| AWS | `aws-actions/configure-aws-credentials` exchanges the OIDC token for a role via `sts:AssumeRoleWithWebIdentity` | The role's trust policy `Condition` block on `token.actions.githubusercontent.com:sub`, scoped to the exact repository and ref, plus `aud` pinned to `sts.amazonaws.com` |
| GCP | Workload Identity Federation maps the OIDC token to a service account through a workload identity pool provider | The pool provider's attribute condition, which must reference `assertion.repository` or `assertion.ref`, not accept every token the pool issues |
| Azure | A federated credential on an App Registration maps the token's `subject` claim to the app | The federated credential's configured `subject` string, which must match the full `repo:OWNER/REPO:ref:refs/heads/BRANCH` (or `:environment:NAME`) shape, not a prefix wildcard |

`id-token: write` is required in the job's `permissions:` block for the request to
succeed at all, and only the job that federates needs it.

## Pin the whole subject, and the audience

GitHub's OIDC token's `sub` claim is structured — `repo:OWNER/REPO:ref:refs/heads/main`,
or `:pull_request`, or `:environment:production`. An exact match on that whole string is
the condition you want; the hole is a wildcard inside it. `repo:OWNER/REPO:*` accepts
every branch and every pull request in the repository, which includes a branch an
attacker can create, and a bare `*` accepts every workflow able to mint a token from the
issuer. Pin the full `sub`, and pin `aud` to the provider's own audience string rather
than leaving it unconstrained. Repositories created after July 2026 carry immutable
identifiers (`repo:OWNER@ID/REPO@ID:...`), so a policy written against the older shape
matches nothing rather than failing loudly. A trust
policy reviewed once at creation and never re-read is the common way this drifts —
confirm it on every audit rather than trusting the name of the role implies its scope.

## `persist-credentials: false`

`actions/checkout` writes the job's token into `.git/config` by default, where any later
step — including a dependency's postinstall script — can read it and push with it. Every
checkout in a hardened pipeline sets `persist-credentials: false` unless that specific
job's later steps genuinely push, which is rare outside a release job.

## Cache scope across the fork boundary

The platform's defaults already do most of this work, and the audit is mostly a check
that nobody has turned them off. A `pull_request` run's caches are scoped to the merge
ref and cannot be written into the default branch's scope. Runs on other events that
resolve to the default branch — `pull_request_target`, `issue_comment`, `workflow_run`,
the ones whose payload or initiating actor someone outside the repository can influence —
get read-only access to that scope: they restore, they cannot create or overwrite.

What reopens it is an explicit `cache-mode`, whose values are `read`, `write`,
`write-only` and `none`. A write-capable `cache-mode` on a low-trust trigger hands back
the poisoning risk the default removed, so `rg -n 'cache-mode:\s*(write|write-only)'
.github/workflows/*.yml` is the grep, and each hit needs a reason:

- Where a job genuinely should only restore, `actions/cache/restore` says so in the
  workflow rather than relying on the run's scope to refuse the save.
- A cache key that a fork PR can fully control (built only from `github.head_ref`, for
  example) lets that PR choose which cached bytes a later trusted run restores. Key on
  content the PR does not choose alone — a lockfile hash, not a branch name.
- Never cache a populated credential file, a `~/.aws/credentials`, or a login-populated
  package manager config. A cache is not encrypted at rest for this purpose and is
  restorable by anything sharing its scope.

## Artefact attestation and verification at the consumer

Producing an attestation and never checking it is the same gap as `image-hardening`
names for image signing: a control nobody exercises is not a control. `actions/attest-build-provenance` (or `cosign attest` for a container artefact) records what produced
an artefact and from which commit. The verification has to happen where the artefact is
next used — a deploy job pulling a build artefact, a downstream workflow consuming
another workflow's output — with the identity pinned to the expected workflow path, the
same way `image-hardening` pins `cosign verify` to a `--certificate-identity-regexp`
rather than accepting any valid signature. `gh attestation verify` is the GitHub-native
check for this and takes the same identity-pinning argument.

## What SLSA level a hosted builder actually gives

Aligned with `image-hardening`: a hosted GitHub Actions runner producing standard
build provenance — `actions/attest-build-provenance`, or `docker buildx build
--provenance=mode=max` for an image — reaches roughly **SLSA Build L2**: the provenance
is signed and not forgeable by the build steps themselves, and it lists materials and
parameters. It is not L3, because L3 additionally requires the build platform to keep
its provenance signing keys inaccessible to user-defined build steps and to isolate
builds from one another, which are properties of the builder, not of a flag or an action.
Reaching L3 means the `slsa-framework/slsa-github-generator` reusable workflows, or an
equivalently isolated, purpose-built builder. A pipeline claiming L3 on the strength of
attaching an attestation step is a claim this audit should not let stand.
