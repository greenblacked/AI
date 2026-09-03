---
name: secret-rotation
description: "Rotate a credential, or contain one that has leaked, without an outage and without leaving a copy behind: choose the planned or incident path first, inventory every consumer from provider access logs rather than the runbook, issue a second live credential instead of editing one in place, prove adoption from provider last-used telemetry past its reporting lag, then disable, bake and delete. Use this skill whenever someone needs to rotate, replace, expire or revoke an API key, access key, token, service-account key, database password, signing secret or certificate, whenever a secret has been committed, pushed or pasted somewhere it should not be, whenever someone with access leaves or a vendor reports a breach, and for phrasings like \"this key is in a public repo\", \"do we need to rotate\", or \"how do we roll this password without downtime\". Do not use it for designing an authentication system, choosing a secrets manager, or reviewing IAM policy in general."
allowed-tools: "Bash(aws:*), Bash(gcloud:*), Bash(az:*), Bash(gh:*), Bash(kubectl:*), Bash(vault:*), Bash(git:*), Read, Grep, Glob"
---

# Secret Rotation

A rotation is finished when every consumer is provably on the new credential, the old one is deleted, and nothing paged. A leak is contained when the credential stops working — not when the commit is gone.

Rotation is hard because it is a two-writer problem in disguise. Every consumer has to accept the new secret before any producer stops accepting the old one, and the set of consumers is always larger than the runbook says: the service you knew about, the cron job someone wrote in 2023, the vendor integration configured through a web form, a laptop, and a screenshot in a closed ticket. Teams paper over that by editing the value in place, which turns a rotation into a synchronised outage, and by deleting the old key as soon as the new one is deployed, which converts a small mistake into an incident with no undo. Leaks fail differently: the instinct is to make the evidence disappear — force-push, delete the repo, redact the ticket — none of which revokes anything. The credential is public from the moment it was pushed, and the only action that matters is the one that makes it stop authenticating.

## Scope

Use for: a scheduled or policy-driven rotation, a rotation triggered by a departure or a vendor breach notice, a leaked or suspected-compromised credential, designing a rotation procedure for something that has never been rotated, setting a cadence, and moving a workload off long-lived static keys.

Do not use for: designing an authentication or authorisation system, choosing between secret managers, a general IAM policy or least-privilege review, or anything intended to obtain, harvest or test credentials you were not given. This skill is defensive procedure; it does not produce exploitation tooling.

## Hard gates

Breaking one of these does not slow the rotation down, it invalidates it.

1. Decide planned or incident before touching anything. The two paths run in opposite orders and mixing them gives you the worst half of each: an outage *and* an uncontained credential.
2. Issue a second credential; do not edit one in place. In-place editing means every consumer is broken between the write and its own restart, and there is nothing to roll back to.
3. Disable the old credential first, delete it later. A disabled key is re-enabled in seconds when you discover the consumer nobody listed; a deleted key is an incident.
4. Adoption is proven by provider-side last-used telemetry, past that telemetry's reporting lag. A team saying "we deployed it" is a statement about a deployment, not about which credential the process is sending.
5. In an incident, revoke before you investigate. Every minute spent scoping the exposure is a minute the credential still works.
6. Rewriting git history revokes nothing. Treat the value as public from the moment it was pushed.
7. The new secret never travels through a channel that retains it. Chat, email, tickets and shared documents are all copies you will not find during the next rotation. Write it into the secret manager or the consumer's own configuration store and share the reference, not the value.

## Workflow

### 0. Choose the path

Classify from the signal, then run the matching path. This table is the whole decision.

| Signal | Classification | Action |
| --- | --- | --- |
| Secret in a public repo, public gist, public S3 bucket, public CI log | Incident, exposed | Revoke inside minutes. Assume it was collected by an automated scraper before you noticed. |
| Secret in a private repo, internal wiki, or ticket | Incident, low confidence | Revoke on the incident path, but the exposure window is bounded by who had repo access. Scope from audit logs before deciding whether to notify. |
| Secret pasted into a third-party tool — a pastebin, an unapproved AI tool, a personal machine | Incident, exposed | Treat as public. You cannot audit the other side's retention. |
| Vendor breach notice naming your integration | Incident, assume compromised | Revoke, then scope your own logs. Do not wait for the vendor's follow-up detail. |
| Key older than policy, no evidence of misuse | Planned | Full planned path. No urgency, no shortcut. |
| Departure of someone with access | Planned, time-boxed | Planned path with a deadline — days, not the next quarterly window. Treat as an incident if the departure was involuntary or contested. |
| Suspected compromise, no evidence either way | Incident | Cheaper to rotate than to prove a negative. Run the incident path and scope in parallel; if the logs come back clean you have lost an hour. |
| A consumer is failing to authenticate right now | Neither | This is an outage. Diagnose before rotating — a rotation started mid-incident hides the cause. |

The rest of steps 1-7 is the **planned** path. For the incident path, read `references/leak-response.md` and start at revocation; you rejoin this sequence at step 2 once the credential is dead.

### 1. Inventory every consumer

The inventory doc is a hypothesis. Provider access logs are the ground truth: they list identities that actually authenticated, including the ones nobody documented.

Start from the provider, then reconcile against the places a secret is stored:

```bash
# AWS: who used this key, from where, over the last 90 days
aws cloudtrail lookup-events --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=EXAMPLE_KEY_ID \
  --start-time 2026-06-05 --max-results 200 \
  --query 'Events[].{time:EventTime,name:EventName,src:CloudTrailEvent}'

# GCP: every principal that authenticated as this service account
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail="svc-orders@PROJECT.iam.gserviceaccount.com"' \
  --freshness=90d --format='value(protoPayload.requestMetadata.callerIp,protoPayload.methodName)' | sort -u
```

Distinct source IPs, user agents and calling methods are your consumer list. An IP you cannot name is the finding — resolve it before rotating, because it is either an undocumented consumer that your rotation will break or an unauthorised one that your rotation should break.

Then reconcile against every store that can hold a copy:

- Secret manager entries and their versions — and anything referencing them by name in code or IaC.
- CI/CD variables: repository, environment and organisation secrets, self-hosted runner environments, Jenkins credential bindings.
- IaC and state. A secret passed as a Terraform variable is in state in cleartext; see the `iac-review` skill for reading state safely.
- Container images and manifests: env vars, mounted secrets, init containers, sidecars, and anything baked into a layer at build time — the `image-hardening` skill covers keeping build secrets out of layers.
- Scheduled work: cron, systemd timers, CronJobs, scheduled Lambdas, database jobs. These are the classic miss, because a weekly job proves nothing between runs.
- Endpoints you do not deploy to: developer laptops, `~/.aws/credentials`, local `.env` files, shared bastion hosts.
- Third-party integrations configured in someone else's web console — webhooks, SaaS-to-SaaS connectors, status pages, monitoring agents.
- Documentation and tickets: the value in a runbook, a screenshot, an onboarding guide.

Write the list down with an owner per consumer before issuing anything. The owner is who you chase in step 4.

### 2. Issue a second, live credential

Both credentials valid at once is the entire mechanism. Create, do not replace:

```bash
aws iam create-access-key --user-name svc-orders            # AWS allows two per user
gcloud iam service-accounts keys create key.json --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com
az ad app credential reset --id APP_ID --append             # --append keeps the existing secret alive
```

Give the new credential the same permissions, not more. A rotation is a bad moment to change scope: if something breaks you will not know whether it was the value or the policy. Tag or name it so the two are distinguishable in telemetry — `orders-2026-09` beats `orders-new`, which is wrong within a month.

Where the provider genuinely supports only one active credential — a single shared database password, an appliance with one API key, an ageing SaaS product — read the fallbacks in `references/provider-playbooks.md`. In short: put a secret manager or a connection proxy between the consumers and the credential so their restarts stop being coupled to the rotation, or accept a short coordinated restart and schedule it deliberately. A single-credential provider is a design defect to log, not a reason to skip the rotation.

### 3. Distribute

Write the new value into the secret manager as a new version, then let each consumer pick it up. Consumers that read at startup need a restart; consumers that refresh on a timer need one refresh interval to pass.

Distribute to every consumer from step 1 before verifying any of them. Partial distribution followed by disabling is the failure this whole procedure exists to prevent.

Two things go wrong here reliably. Applications cache credentials at process start, so an updated secret with no restart changes nothing — a rolling restart is part of distribution, not an optional extra. And a consumer with the value pinned in an env var baked into an image needs a new image, which is a build and a deploy, not a config change.

### 4. Verify adoption from provider telemetry

Ask the provider which credential each consumer is actually using. Nothing else counts.

| Provider | Telemetry | Granularity and lag | Reading it |
| --- | --- | --- | --- |
| AWS IAM | `aws iam get-access-key-last-used --access-key-id ID` | Timestamps can trail real calls; the account credential report is regenerated at most every four hours | Old key's `LastUsedDate` must stop advancing, not merely be old |
| AWS IAM (fleet view) | `aws iam generate-credential-report` then `get-credential-report` | Up to four hours stale by construction | Use for age and coverage sweeps, not for the final go/no-go |
| GCP service accounts | `gcloud policy-intelligence query-activity --activity-type=serviceAccountKeyLastAuthentication --project=PROJECT` | Daily-ish, populated with a delay | Confirm the old key ID has no recent authentication |
| GCP (authoritative) | `gcloud logging read` filtered on the principal and key ID | Near real time | The reliable source when you need an answer today |
| GitHub PAT / fine-grained token | Last-used date on the token settings page | Day granularity | Cannot prove "unused in the last hour" — pair with the org audit log |
| GitHub org | `gh api /orgs/ORG/audit-log --paginate` | Minutes | The per-actor, per-event ground truth |
| Kubernetes | `kubectl get pods -o json` plus the workload's own auth logs | Immediate | Confirm every pod restarted after the secret version changed |

The lag is the part people skip. If the figure can be four hours stale, waiting three hours and seeing zero usage proves nothing. Wait past the lag *and* past one full cycle of your slowest consumer — a weekly cron job means a week — before step 5.

If the old credential is still being used and nobody can say by what, you have found the consumer that was missing from step 1. That is the inventory working, not the rotation failing.

### 5. Disable the old credential

Disable, do not delete:

```bash
aws iam update-access-key --access-key-id EXAMPLE_OLD_KEY_ID --status Inactive --user-name svc-orders
gcloud iam service-accounts keys disable EXAMPLE_OLD_KEY_ID --iam-account=svc-orders@PROJECT.iam.gserviceaccount.com
```

Disabling is the reversible test of your verification. If something breaks in the next hour, re-enable, find the consumer, and restart at step 3 — cost, a few minutes. The same mistake made with `delete-access-key` costs an incident and, for a GCP key, an unrecoverable private key you can never restore.

Announce the disable window to consumer owners before you do it, not after.

### 6. Bake, then delete

Leave the credential disabled for one full cycle of the longest-period consumer plus a margin. Monthly billing job in the inventory means a month. There is no cost to a disabled credential other than a line in a list.

Then delete it, and delete the copies: old secret-manager versions, the CI variable you replaced, the value in the ticket, the local `.env`. A rotation that leaves a superseded value lying around has moved the problem rather than solved it.

### 7. Record the rotation

One line where credential inventory lives: the credential, the path taken, the new key ID, the date the old one was disabled and deleted, and the consumer that was missing from the inventory. That last field is the one that improves the next rotation.

## Incident rotation: the reordered path

When the credential is exposed, the order changes and so does the standard of proof. Revocation is not a decision to hold a meeting about.

**A. Revoke now.** Disable the credential. If the provider mints derived sessions from it (AWS STS), also invalidate sessions issued before this moment — an attacker holding a twelve-hour session token is unaffected by killing the access key. `references/leak-response.md` has the deny-policy pattern for that.

**B. Scope the exposure.** From audit logs, answer four questions in writing: what did this identity do, from where, between when and when, and was any of it unusual for this identity. The exposure window opens at the earliest possible disclosure — the commit's author date, not the date you found it — and closes at revocation.

**C. Rotate.** Rejoin the planned path at step 2. Consumers are now broken, so this runs under time pressure; that is the cost of the exposure, and it is why the planned path exists.

**D. Hunt for persistence.** A credential that was used is a foothold, and revoking it removes the foothold, not what was built with it. Look for new access keys, users or roles; changed trust policies; new inbound firewall or security-group rules; new deploy keys, SSH keys or OAuth app authorisations; new mail forwarding or filter rules; resources in regions you do not use; and changed billing or notification addresses. The checklist per provider is in `references/leak-response.md`.

**E. Notify.** The credential's owner, your security contact, and the provider — most have a compromised-credential process, and some will waive fraudulent usage charges if you tell them promptly. If customer data was reachable, legal decides on external notification, and the clock started at step B, not at your report.

Write it up afterwards with the `postmortem` skill. The interesting question is rarely "who pushed the key" — it is why a static long-lived credential existed for a workload that could have used federation, and why detection came from where it did.

## What to do instead of rotating

The best rotation is the one you do not have to perform, because the credential expires on its own in an hour.

- **Federate CI to the cloud with OIDC.** GitHub Actions and GitLab CI can exchange a workload identity token for a short-lived cloud role, so no static key exists in CI at all. This deletes an entire class of leak: the CI secret that ends up echoed into a log.
- **Use workload identity in the runtime.** IAM roles for service accounts or EKS Pod Identity, GKE Workload Identity, Azure workload identity, instance profiles. The credential becomes a rotating token the platform manages.
- **Use dynamic credentials for databases.** A secret manager that mints a per-connection database user with a short lease turns rotation into expiry.
- **Scan before the push and in CI.** A pre-commit hook catches the value before it exists in history; a CI scan over full history catches what the hook missed. Provider-side push protection is better than both, because it rejects the push rather than reporting it. Do not stop at the hook — the hook is the control someone bypasses at 6pm on a Friday.
- **Alert on secret age.** The credential report's key-age field, or your secret manager's metadata, feeds one alert: any static credential past policy age. Without it, rotation happens when someone remembers.

Every one of these turns a recurring manual procedure into a property of the platform. Prefer them, and treat a remaining static key as a documented exception with a named owner.

## Cadence

Cadence is a judgement call about blast radius and detection speed, not a calendar habit.

Rotate faster when the credential is long-lived and broadly scoped, when you cannot detect misuse quickly, or when it is held by many humans. Rotate more slowly — and spend the effort on detection instead — when the credential is narrowly scoped, machine-held, and covered by anomaly alerting on the identity. A 90-day cadence with good last-used telemetry and alerting is defensible; a 30-day cadence with no telemetry is ritual, because you would not notice misuse in either window.

Rotate on events regardless of the calendar: departures, vendor breach notices, a consumer being decommissioned, or any change in who holds the value. And treat a rotation that requires a maintenance window as a defect in the credential's design — it is the reason the rotation will be postponed until it is a leak instead.

## Output format

```markdown
## Path
[planned | incident — and the signal that decided it]

## Credential
[what it is, which provider, owner, blast radius in one sentence]

## Exposure window
[incident only: earliest possible disclosure to revocation, and what the identity did in it]

## Consumers
[the list, each with owner and how it receives the secret. Mark any found from access logs but absent from the inventory.]

## Evidence of adoption
[per provider telemetry, with the query and the timestamp. Note the lag you waited past.]

## Old credential
[disabled at: … | delete after: … | deleted at: …]

## Residual risk
[copies not yet destroyed, single-credential consumers, anything unverified]

## Follow-up
[federation or dynamic-credential work this rotation justified, with an owner]
```

## Anti-patterns

**Editing the secret in place.** Every consumer is broken from the moment of the write until its own restart, and there is nothing to roll back to because the old value is gone. It converts a routine operation into a synchronised outage, then teaches the team that rotations are dangerous and should be rare — which is exactly the wrong lesson.

**Deleting the old key before verifying the new one.** Removes the undo at the moment you most need it. The consumer nobody listed always exists, and the only question is whether it fails while the old key is one command from being re-enabled or after it has been destroyed.

**Trusting the inventory doc.** It records the consumers someone thought to write down at a moment that has passed. Provider access logs record the ones that authenticated last week. When the two disagree, the logs are right.

**Rewriting history instead of revoking.** A force-push does not un-publish anything. Forks, pull-request refs, caches and scrapers all keep the object reachable, and public push events are consumed by automation within seconds. Rewriting history is optional hygiene performed after revocation, never in place of it.

**Rotating without scoping the exposure.** You have stopped the credential and learned nothing. If it was used, the attacker's persistence — a second access key, a new inbound rule, a forwarding rule — survives the rotation untouched, and the next alert looks unrelated.

**A rotation that requires a coordinated restart of everything.** The tell is a maintenance window on the plan. It means no dual-credential support and no indirection, so the rotation is expensive, so it is deferred, so the credential ages past every policy. Fix the coupling with a secret manager or a proxy; do not schedule the outage annually.

**Sharing the new value over chat to "unblock" a consumer.** It creates a copy in a system with its own retention, search and export, outside every inventory you will build later. Share the secret-manager reference and let the consumer read it.

## Reference files

- `references/provider-playbooks.md` — read when you know the provider and need the exact commands: dual-credential support per provider, the create/verify/disable/delete sequence for AWS, GCP, Azure, GitHub and Kubernetes, and the fallbacks for credentials that cannot be doubled, including database passwords.
- `references/leak-response.md` — read the moment a credential is believed exposed: the revocation-first timeline, session invalidation, the audit-log queries that scope the exposure window, the per-provider persistence checklist, and what git history rewriting does and does not achieve.
