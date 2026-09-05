# Evidence: what each source proves, and what it cannot

Read this while gathering evidence for a review. Every account identifier, role name and
job id below is a placeholder — substitute your own. The point of each query is the
question it answers and the lag on the answer, not the syntax.

## Contents

- Choosing the measurement window
- AWS
- Google Cloud
- Entra ID and Microsoft 365
- Kubernetes
- GitHub
- Databases and applications
- What no telemetry can prove

## Choosing the measurement window

The window has to contain a full cycle of the least frequent legitimate use, or the
evidence is telling you about a subset of the work.

| Workload shape | Minimum honest window |
| --- | --- |
| Continuous request-serving | 30 days |
| Weekly batch or reporting | 45 days, so two runs land inside it |
| Monthly close, billing, invoicing | 90 days |
| Quarterly reconciliation, audit export | 180 days |
| Annual: certificate renewal, DR drill, yearly filing | 400 days, or accept the risk explicitly and rely on audit mode |

Where the provider only retains 90 days of last-accessed data, that is your ceiling for
that source; go to raw audit logs, or to the archive of them, for anything longer. If a
long window is unaffordable, write the risk down in the review record rather than
quietly using 30 days and calling it evidence.

## AWS

```bash
# Which services a principal has actually reached, and when (also supports action-level
# granularity for the services that report it)
JOB=$(aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::111122223333:role/example-orders-role \
  --granularity ACTION_LEVEL --query JobId --output text)
aws iam get-service-last-accessed-details --job-id "$JOB"

# Whole-account age and usage sweep: password last used, key last used, MFA
aws iam generate-credential-report >/dev/null
aws iam get-credential-report --query Content --output text | base64 -d

# Unused access findings across the account: unused roles, users, permissions, keys
aws accessanalyzer create-analyzer --analyzer-name example-unused --type ACCOUNT_UNUSED_ACCESS
aws accessanalyzer list-findings-v2 --analyzer-arn ANALYZER_ARN_EXAMPLE

# External access: which resources are reachable from outside the account or organisation
aws accessanalyzer list-findings-v2 --analyzer-arn EXTERNAL_ANALYZER_ARN_EXAMPLE

# The authority when you need exact actions by an exact principal
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=example-orders-role \
  --start-time 2026-06-01 --max-results 200
```

| Source | Granularity | Lag | Proves |
| --- | --- | --- | --- |
| Service last accessed | Service, or action for supported services | Computed on request; tracking period up to 400 days | A service was not reached in the period |
| Credential report | Per credential | Regenerated at most every four hours | Age, last use, MFA state |
| Unused-access analyzer | Permission, role, user, key | Runs on a configured cadence | Candidate reductions, ranked |
| CloudTrail | Exact API call, caller, source IP | Minutes; data events only if enabled | What actually happened |

The trap: CloudTrail records management events by default and **data events only when
you enable them**. A role that reads objects all day looks entirely unused if you are
reading management events alone. Confirm which event types the trail captures before
concluding anything about a data-plane permission.

## Google Cloud

```bash
# Recommendations to shrink over-granted roles, computed from 90 days of usage
gcloud recommender recommendations list \
  --project=example-project --location=global \
  --recommender=google.iam.policy.Recommender --format=json

# Which principals can call a permission on a resource, expanded through groups
gcloud asset analyze-iam-policy \
  --organization=ORG_ID_EXAMPLE \
  --permissions=storage.objects.delete

# Service-account key and impersonation usage
gcloud policy-intelligence query-activity \
  --activity-type=serviceAccountLastAuthentication --project=example-project

# The authority: audit logs for one principal
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail="svc-orders@example-project.iam.gserviceaccount.com"' \
  --freshness=90d --format='value(protoPayload.methodName)' | sort | uniq -c | sort -rn
```

The trap: data-access audit logs are **not enabled by default** for most services, so
reads are invisible until somebody turns them on. Check the configuration before reading
absence as evidence. `analyze-iam-policy` is the tool that expands group membership and
inheritance — a project-level binding on a group is where "who can do this" stops being
answerable by reading one policy.

## Entra ID and Microsoft 365

- Sign-in logs give last interactive and non-interactive sign-in per user; non-interactive
  is the one that reveals a service principal still in use.
- The audit log gives directory changes: role assignments, consent grants, application
  registrations.
- Access reviews are a built-in campaign mechanism, and Privileged Identity Management
  provides the just-in-time elevation that replaces standing admin.
- Enterprise applications and their granted permissions are where third-party OAuth
  consent accumulates, including grants a user made for the whole organisation.
- Conditional access policies support **report-only mode**, which is the audit-mode
  mechanism for this platform.

## Kubernetes

```bash
# What a service account can actually do, expanded through its bindings
kubectl auth can-i --list --as=system:serviceaccount:example-ns:example-sa

# Every binding to cluster-admin
kubectl get clusterrolebindings -o json \
  | jq -r '.items[] | select(.roleRef.name=="cluster-admin") | "\(.metadata.name): \(.subjects)"'

# Roles carrying a wildcard verb or resource
kubectl get clusterroles -o json \
  | jq -r '.items[] | select(.rules[]? | (.verbs[]? == "*") or (.resources[]? == "*")) | .metadata.name'
```

Usage evidence comes from the API server audit log, which has to be configured with a
policy that records the level you need; the default in many distributions records
metadata only, or nothing. Watch specifically for permissions that are escalation in
disguise: creating pods in a namespace that hosts a privileged service account, reading
secrets cluster-wide, `escalate` or `bind` on roles, and access to the token-request
endpoint.

## GitHub

```bash
# Organisation members and their role
gh api /orgs/example-org/members --paginate -q '.[].login'

# Installed apps and the permissions each holds
gh api /orgs/example-org/installations --paginate -q '.installations[] | {app: .app_slug, perms: .permissions}'

# Audit log: who did what, including token and key events
gh api '/orgs/example-org/audit-log?phrase=action:org.add_member' --paginate
```

Personal access tokens and SSH keys belonging to individuals are visible to the
organisation only in limited ways; where the plan supports it, enforce fine-grained
tokens with expiry and organisation approval. Deploy keys and repository-level secrets
are frequently the forgotten path into production.

## Databases and applications

Database grants are outside every cloud IAM tool and are usually the broadest access
anybody holds. Enumerate roles and grants directly, and use the engine's own statistics
for last use where they exist. Application-level roles — an admin flag in your own
product, a support tool that can impersonate a customer — are in scope for the same
reasons and are almost always missed, because no compliance checklist names them.

## What no telemetry can prove

- **That a permission is safe to remove.** Absence of use in a window is evidence, not
  proof. Audit mode is what converts it into a safe change.
- **That an identity is unused.** Only that it did not authenticate through the paths you
  are logging. Check whether the relevant log category was even enabled.
- **Intent.** Logs show that an action occurred, not whether it should have. That
  judgement belongs to the identity's owner, which is why every finding needs one.
