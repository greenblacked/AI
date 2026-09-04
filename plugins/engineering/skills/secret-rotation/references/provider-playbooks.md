# Provider playbooks

The per-provider mechanics of a planned rotation: whether two credentials can be live at
once, the exact create / verify / disable / delete sequence, and what to do when the
provider only supports one.

All identifiers below are obvious placeholders. Substitute the real ones at the shell;
do not commit a filled-in copy of this file.

## Contents

- [Dual-credential support at a glance](#dual-credential-support-at-a-glance)
- [AWS IAM access keys](#aws-iam-access-keys)
- [GCP service-account keys](#gcp-service-account-keys)
- [Azure app registrations](#azure-app-registrations)
- [GitHub tokens, apps and deploy keys](#github-tokens-apps-and-deploy-keys)
- [Kubernetes secrets](#kubernetes-secrets)
- [Database passwords: the single-credential case](#database-passwords-the-single-credential-case)
- [SaaS API keys and webhook signing secrets](#saas-api-keys-and-webhook-signing-secrets)
- [TLS certificates](#tls-certificates)
- [When the provider allows only one credential](#when-the-provider-allows-only-one-credential)

## Dual-credential support at a glance

| Credential | Two live at once | Disable without delete | Last-used telemetry |
| --- | --- | --- | --- |
| AWS IAM access key | Yes, two per user | Yes, `--status Inactive` | Yes, with lag |
| GCP service-account key | Yes, several per account | Yes, `keys disable` | Yes, via activity analyzer or logs |
| Azure app client secret | Yes, `--append` | No — delete only | Sign-in logs |
| GitHub fine-grained PAT | Yes, independent tokens | No — revoke only | Day-granularity last-used |
| GitHub App private key | Yes, multiple keys per app | No — delete only | Audit log |
| Webhook signing secret | Sometimes, provider-dependent | Rarely | Rarely |
| Database password | Not for one role; yes with two roles | Via role revoke | Connection logs |
| TLS certificate | Yes, overlapping validity | Revocation is separate | Handshake logs |

Where the "two live at once" column says no, the rotation needs the indirection described
at the end of this file, or a scheduled restart.

## AWS IAM access keys

An IAM user holds at most two access keys, which is the mechanism, not a limitation. If
the user already has two, one of them is a previous rotation that was never cleaned up —
verify and delete it before starting rather than deleting the one in use.

```bash
aws iam list-access-keys --user-name svc-orders
aws iam create-access-key --user-name svc-orders          # capture the secret once; it is not retrievable later
aws iam get-access-key-last-used --access-key-id EXAMPLE_OLD_KEY_ID
aws iam update-access-key --access-key-id EXAMPLE_OLD_KEY_ID --status Inactive --user-name svc-orders
aws iam delete-access-key --access-key-id EXAMPLE_OLD_KEY_ID --user-name svc-orders
```

Fleet-wide age and usage sweep:

```bash
aws iam generate-credential-report
aws iam get-credential-report --query Content --output text | base64 -d | \
  cut -d, -f1,9,11,14,16   # user, key_1_active, key_1_last_used_date, key_2_active, key_2_last_used_date
```

The credential report is regenerated at most every four hours, so a fresh report can still
describe a four-hour-old world. Treat it as a sweep tool, not as the go/no-go for a
disable.

The far better outcome for anything running in CI or on AWS compute is that no access key
exists at all: an OIDC trust policy for the CI provider, or an instance profile, IRSA or
EKS Pod Identity for workloads. When a rotation surfaces a static key on AWS compute, log
the federation work as the follow-up.

## GCP service-account keys

User-managed keys are the thing to rotate; Google-managed keys rotate themselves.

```bash
gcloud iam service-accounts keys list --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com --managed-by=user
gcloud iam service-accounts keys create ./new-key.json --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com
gcloud policy-intelligence query-activity \
  --activity-type=serviceAccountKeyLastAuthentication --project=PROJECT \
  --filter='activities.fullResourceName:svc-orders'
gcloud iam service-accounts keys disable EXAMPLE_OLD_KEY_ID --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com
gcloud iam service-accounts keys delete EXAMPLE_OLD_KEY_ID --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com
```

Two properties matter. The private key material exists only in the file you were handed at
creation — Google does not store it, so a deleted key cannot be restored and a lost file is
a rotation. And the near-real-time source of truth is Cloud Logging on the principal, not
the activity analyzer, which is convenient but delayed.

Write the JSON key straight into the secret manager and remove the local file in the same
command sequence. A key file that lives in a home directory for a week is the next leak.

## Azure app registrations

Azure supports several client secrets on one application, and `--append` is what keeps the
existing one alive:

```bash
az ad app credential list --id EXAMPLE_APP_ID
az ad app credential reset --id EXAMPLE_APP_ID --append --years 1
az ad app credential delete --id EXAMPLE_APP_ID --key-id EXAMPLE_OLD_CREDENTIAL_ID
```

Without `--append` the command replaces every existing secret, which is an in-place edit
with a friendly name. There is no disabled state, so the bake window is spent with the old
secret still valid — compensate by confirming from sign-in logs that only the new
credential is authenticating before deleting.

Certificate credentials rotate the same way and are preferable for long-lived
integrations. Managed identities remove the credential entirely and are preferable to
both.

## GitHub tokens, apps and deploy keys

- **Fine-grained PAT**: create the replacement, update every consumer, then revoke the old
  one. There is no disabled state, and the token settings page reports last use only to
  the day — which is enough to spot an abandoned token and not enough to clear a rotation.
  Pair it with the organisation audit log.
- **Classic PAT**: prefer replacing it with a fine-grained token or a GitHub App during the
  rotation. A classic PAT's scopes are organisation-wide, so its blast radius is every
  repository the human can see.
- **GitHub App**: generate a second private key, deploy it, then delete the first. Apps
  support multiple keys precisely for this. Installation tokens are already short-lived, so
  the private key is the only thing being rotated.
- **Actions secrets**: `gh secret set NAME --repo OWNER/REPO`, or `--org` with a visibility
  setting. Note that environment-scoped, repository-scoped and organisation-scoped secrets
  can all define the same name, and the innermost wins — check all three during inventory
  or you will rotate the one that is being shadowed.
- **Deploy keys and SSH keys**: enumerate per repository and per user; these are the copies
  that survive an offboarding checklist.

```bash
gh api /orgs/ORG/audit-log --paginate -X GET -f phrase='actor:EXAMPLE_ACTOR' -f include=all
gh secret list --repo OWNER/REPO
gh api /repos/OWNER/REPO/keys
```

## Kubernetes secrets

A Secret update does not restart anything. Pods that read a secret into an environment
variable at start keep the old value until they are replaced; pods with the secret mounted
as a volume see the new file after the kubelet's refresh period, and only if the
application re-reads the file.

```bash
kubectl create secret generic orders-api --from-file=key=./new-key --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/orders-api
kubectl rollout status deployment/orders-api
```

Rolling restart is part of distribution. Also check init containers, sidecars, CronJobs
(which will not restart — they pick up the new value at the next scheduled run, which is
the timing you must wait for in step 4 of the main workflow), and any external secrets
operator whose sync interval sits between your write and the pod's read.

## Database passwords: the single-credential case

One role with one password cannot be rotated without a coordinated restart. Two roles can:

1. Create a second role with identical grants — `orders_app_b` beside `orders_app_a`.
2. Move consumers to the second role one at a time, verifying from the server's connection
   log which role each is using.
3. Revoke the first role once nothing has connected as it for a full cycle.
4. Next rotation moves back the other way, so the procedure is symmetrical and practised.

Better, remove the shared password entirely: IAM database authentication on RDS and Cloud
SQL mints a short-lived token per connection, and a secret manager with dynamic credentials
issues a per-lease user that expires on its own. Either turns rotation into expiry, which
is the only rotation that never gets deferred.

Where the application connects through a pooler or proxy, the proxy holds the credential
and the applications hold a reference to the proxy. That decouples consumer restarts from
the rotation entirely, which is the single highest-value change for a database credential
that many services share.

## SaaS API keys and webhook signing secrets

Read the vendor's documentation for one fact before planning: how many keys can be active
at once. Most modern products allow several; some allow one, and the ones that allow one
usually also lack usage telemetry, which means you cannot verify adoption and must fall
back to a coordinated restart with a rollback plan.

Webhook signing secrets rotate in the opposite direction — the vendor produces, you
consume. The safe sequence is to accept both the old and the new secret in your verifier,
ask the vendor to switch, confirm from your own logs that every recent delivery verified
against the new one, then stop accepting the old. A verifier that accepts only one secret
makes this a scheduled failure of inbound webhooks.

Inbound integrations configured in someone else's console — a monitoring agent, a CI
integration, a status page — are the consumers most often missing from the inventory,
because rotating them requires a login that the person doing the rotation does not have.
Name the owner during step 1, not during the outage.

## TLS certificates

Certificates rotate by overlapping validity, which is the same dual-credential idea with a
different vocabulary. Automate issuance and renewal, alert on days-to-expiry rather than on
expiry, and remember that revocation and rotation are separate acts: replacing a
certificate does not stop the old private key from working until the old certificate is
revoked and the revocation is actually checked by clients.

For a private key believed to have leaked, revoke and re-issue; renewing on the same key
pair rotates nothing.

## When the provider allows only one credential

Three options, in order of preference.

**Indirection.** Put a secret manager, a connection proxy or a small gateway between the
consumers and the credential. The consumers then hold a reference; the credential is
rotated in one place and the consumers do not restart. This is the fix that converts a
recurring outage into a routine operation, and it is worth building the first time you hit
the problem rather than the third.

**Coordinated restart.** Accept it, but schedule it: name the window, order the restarts,
prepare the rollback (the old value stays in the manager as a previous version until the
window closes), and confirm each consumer before moving to the next. This is a small
planned outage, so it belongs in the same change process as any other — the `cutover`
skill covers running one with a rollback point.

**Provider pressure.** Log it as a product defect and raise it with the vendor, especially
at renewal when you have leverage. "Supports two concurrent API keys" is a legitimate line
item in a vendor evaluation, and the reason to ask for it is precisely this page.
