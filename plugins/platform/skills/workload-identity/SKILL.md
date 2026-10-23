---
name: workload-identity
description: "Replace static cloud keys with federated identity for pods and CI: IRSA or EKS Pod Identity, GKE and Azure workload identity, GitHub Actions OIDC. The trust policy pins issuer, audience and the exact subject (repository plus branch or environment; namespace plus service account), never a wildcard; one role per workload, short sessions; gate: a deliberate failed assumption from an unlisted repository or service account, and only then disable and delete the old keys. Use when someone wants AWS access keys out of CI, is setting up IRSA, wants to \"stop storing a JSON key in GitHub secrets\", or asks whether a trust policy with repo:org/* is safe. Not for rotating a key that has to remain static, or containing a leaked one (secret-rotation), reviewing who holds which grant (access-review), user login or SSO (auth-design), or hardening a workflow against fork injection (pipeline-hardening)."
allowed-tools: Read, Grep, Glob
---

# Workload Identity

Done means every workload in scope obtains short-lived cloud credentials by presenting a
token its platform issued, each role trusts exactly one workload by issuer, audience and
exact subject, an assumption from outside that list has been shown to fail, and the
static keys the workloads used to hold are deleted and can no longer be created.

Federation removes the key that can leak, but it moves the whole security question into
one condition in a trust policy, and that condition is easy to write too wide. A trust
policy that matches `repo:my-org/*` lets any repository anyone in the organisation
creates assume a production role; one that matches `repo:my-org/app:*` lets any branch,
including one opened by a pull request, do the same. Both work on the first try, which is
why they ship. The other common failure is quieter: the federated path is wired up, the
old key is left in an environment variable "for now", and the SDK's credential chain
keeps using the key because environment variables come first. Federation then looks
done in every dashboard while the key it was meant to replace is still the thing
authenticating.

## Scope

Use for: moving pods on EKS, GKE or AKS from mounted or environment-variable keys to
IRSA, EKS Pod Identity, Workload Identity Federation for GKE or Microsoft Entra Workload
ID; moving CI (GitHub Actions first; any OIDC-issuing CI follows the same shape) from
stored cloud keys to OIDC federation; and reviewing an existing trust policy or binding
for wildcards and shared roles.

Do not use for: rotating or containing a key that has leaked, which is `secret-rotation`
(revoke first; federation is the follow-up); a least-privilege review of what roles may
do, which is `access-review`; human login, SSO or session design, which is
`auth-design`; and protecting a workflow from untrusted fork input, which is
`pipeline-hardening`.

## Workflow

Only Read, Grep and Glob are pre-approved. Every `aws`, `gcloud`, `az` and `kubectl` command, creating associations, disabling or deleting a key and
running the negative tests happen with the user's approval: workflow files, service-account
annotations and audit-log fields are text other people write.

### 1. Inventory the static keys and who uses them

List every long-lived key, then find who actually uses it from provider telemetry rather
than from the runbook.

```bash
aws iam list-access-keys --user-name "$IAM_USER"
aws iam get-access-key-last-used --access-key-id "$KEY_ID"
gcloud iam service-accounts keys list --iam-account="$SA_EMAIL" --managed-by=user
az ad app credential list --id "$APP_ID"
```

For each key, record the consuming workload (a deployment, a CI repository and workflow,
a cron job), what it calls, and the target identity it will become. A key with no
identifiable consumer is not migrated; it goes to `secret-rotation`'s disable-and-watch
path instead.

### 2. Choose the mechanism per workload

| Workload | Mechanism | What carries the identity |
| --- | --- | --- |
| Pod on EKS | EKS Pod Identity, or IRSA where Pod Identity is not available | Pod identity association, or the `eks.amazonaws.com/role-arn` service-account annotation |
| Pod on GKE | Workload Identity Federation for GKE | IAM binding to the `principal://` identifier for namespace and service account |
| Pod on AKS | Microsoft Entra Workload ID | Federated identity credential on a user-assigned managed identity, plus the `azure.workload.identity/client-id` annotation |
| GitHub Actions job | GitHub OIDC | Trust policy or federated credential matching the job's `sub` claim |

One role or identity per workload. A shared "ci-deployer" role that ten repositories
assume makes every one of them as powerful as the most privileged, and makes the trust
condition a list nobody reviews.

### 3. Write the trust condition: issuer, audience, exact subject

Every trust policy or binding pins three things:

- **Issuer**: the cluster's OIDC issuer URL, or `https://token.actions.githubusercontent.com`.
- **Audience**: `sts.amazonaws.com` for AWS, `api://AzureADTokenExchange` for Azure, the
  provider's configured audience for Google Cloud.
- **Subject**, matched exactly: `system:serviceaccount:NAMESPACE:SA` for a pod;
  `repo:OWNER/REPO:environment:production` or `repo:OWNER/REPO:ref:refs/heads/main` for
  a GitHub job.

On AWS use `StringEquals` on both `:aud` and `:sub`, never `StringLike` with `*`. For a
deploy role, prefer the `environment:` subject and put a protection rule (required
reviewers, branch restriction) on that environment in GitHub, because a `ref:` subject
trusts anyone who can push to that branch, while an environment adds the approval step.
Read `references/trust-policy-patterns.md` now for the trust documents and bindings for
each platform, the subject formats, and what each common wildcard actually admits.

*Gate:* no trust condition in scope contains a wildcard in the subject, and no subject
is shared by two workloads.

### 4. Bound the session and the permissions

Keep the role's maximum session at the one-hour default unless a job genuinely runs
longer; credentials are refreshed from the token, so a long session buys nothing but a
longer window for a stolen one. Give each role only what its one workload calls, taken
from the step 1 telemetry, not copied from the key's old policy, which was usually sized
for every consumer at once.

### 5. Wire the consumer and remove the key from it

For pods, create the association or annotate the service account, and restart the pods so
the token is projected. For GitHub, grant `id-token: write` in the job's `permissions:`
block (only on the jobs that need it) and replace the stored-key step with the cloud's
own credentials action, pinned to a commit SHA.

In the same change, delete the key from the workload's environment, mounted secret and
CI secrets. The AWS SDKs read environment variables before the web-identity token file,
and the Google client libraries honour `GOOGLE_APPLICATION_CREDENTIALS` before the
metadata server, so a key left in place silently wins.

### 6. Prove both directions

- **Positive:** the workload's calls now arrive as the federated identity. On AWS, look
  for `AssumeRoleWithWebIdentity` (IRSA, GitHub) in CloudTrail for the role and the
  expected subject; on Google Cloud, the audit log's `principalSubject` shows the
  federated principal; and the old key's last-used timestamp stops advancing.
- **Negative:** deliberately attempt the assumption from something not on the list — a
  workflow in a different repository, a branch other than the pinned one, a pod running
  under a different service account in the same namespace — and confirm it is denied
  (`AccessDenied` on `sts:AssumeRoleWithWebIdentity` for AWS).

*Gate:* the negative test has been run and denied before any key is deleted. A trust
policy that has only ever been tested by the workload it admits has not been tested.
Read `references/verification-and-retirement.md` for the queries, the negative-test
recipes per platform, and the retirement sequence.

### 7. Retire the keys and stop new ones

Disable each key, wait past the provider's last-used reporting lag and at least one full
cycle of the slowest scheduled consumer (a weekly job proves nothing on a Tuesday), then
delete it. Finally block re-creation: a service control policy denying
`iam:CreateAccessKey` for the accounts in scope, or the Google Cloud organisation policy
constraint `iam.disableServiceAccountKeyCreation`, with exceptions listed by name.

## Anti-patterns

**`StringLike` with `repo:org/*` or `repo:org/app:*`.** It passes every positive test
and admits every repository or every branch, including pull-request branches.

**One role for the whole CI estate.** The least-trusted repository sets the security of
the most-privileged deploy.

**Leaving the old key in place as a fallback.** The credential chain prefers it, so the
migration is cosmetic, and the key is still there to leak.

**Deleting keys before the negative test.** A wide trust policy found after the keys are
gone is an incident with no quick rollback other than widening it further.

**Trusting a GKE subject as cluster-scoped.** Every cluster in a project shares the
project's workload identity pool, so the same namespace and service-account name in
another cluster in that project receives the same identity. Separate clusters of
different trust into different projects.

## Output

```markdown
## Keys in scope
| Key | Consumer (from telemetry) | Target identity | Mechanism |

## Trust conditions
| Identity | Issuer | Audience | Subject (exact) | Session max |

## Verification
| Identity | Positive evidence | Negative test and result |

## Retirement
| Key | Disabled on | Last used | Deleted on |
[creation-blocking policy applied, and its named exceptions]
```

## Reference files

- `references/trust-policy-patterns.md` — read at step 3: trust documents and bindings
  for IRSA, EKS Pod Identity, GKE, AKS and GitHub OIDC into each cloud, the subject
  formats, and what each common wildcard admits.
- `references/verification-and-retirement.md` — read at steps 6 and 7: the audit-log
  queries for positive evidence, a negative-test recipe per platform, and the
  disable-bake-delete sequence with the policies that stop keys being recreated.
