---
name: access-review
description: "Review who and what can do what, and reduce it toward least privilege without breaking production: choose between a scheduled review of the whole estate and a targeted reduction of one identity, inventory humans, service accounts, workload identities, CI/CD and third-party grants, judge on last-accessed evidence rather than stated intent over a window long enough to contain the quarterly job, then propose, run in audit-only mode, alert on would-have-denied, enforce and keep the alert. Use this skill whenever someone is doing an access or permissions review, an IAM or RBAC least-privilege cleanup, a user-access certification for an audit, or an offboarding or role-change sweep, or asks \"who has admin\", \"can we drop this wildcard\", or \"does this service account still need full s3 access\". Not for rotating or containing a leaked credential, designing an authentication system, reviewing a Terraform diff, or hardening a container image."
allowed-tools: "Bash(aws:*), Bash(gcloud:*), Bash(az:*), Bash(gh:*), Bash(kubectl:*), Bash(jq:*), Read, Grep, Glob, Write"
---

# Access Review

A finished access review is one where a named person can say, for every identity that still holds a permission, what it used that permission for in the last measured window — and where the things that could not answer that have actually been removed, not listed.

Permissions accumulate in one direction. Someone is granted admin at 2am to unblock an incident and still has it three years later, because the ticket to remove it was never written and nobody wants to be the person who breaks the next incident response. A service account gets `s3:*` because the exact action was unknown at the time, and nobody came back once it was known. A vendor integration from a trial that ended in 2023 still holds a token with organisation-wide read. Every one of those was reasonable at the moment it happened, and none of them has an owner whose job is to undo it. Then the naive fix makes it worse: revoke broadly, watch production break, get told to restore everything, and conclude that access reviews are dangerous. After that the estate only grows, and the blast radius of any one compromised credential stays enormous. The way out is not courage, it is evidence and a rehearsal — judge on what was actually used, and run every reduction in an audit-only mode that reports what it *would* have denied before anything is denied at all.

## Scope

Use for: a scheduled or compliance-driven review of an existing estate; a targeted least-privilege reduction of one role, policy or service account; an offboarding, transfer or contractor-ending sweep; finding unused identities, wildcard policies, standing admin and privilege-escalation paths so they can be closed; setting up break-glass properly; deciding a review cadence a team will sustain.

Do not use for: rotating, revoking or containing a credential that has leaked (that is `secret-rotation`), designing an authentication or authorisation system, reviewing an infrastructure-as-code diff (that is `iac-review`), hardening a container image (that is `image-hardening`), or anything intended to obtain or test access you were not granted. This is defensive procedure. Describing an escalation path so it can be found and closed is the entire point; producing steps to exploit one is not, and this skill does not do it.

## Hard gates

1. **Evidence, not intent.** A policy says what is permitted; access logs say what was used. Judge on the second. The first is a record of what somebody once thought might be needed.
2. **Audit mode before enforcement.** Every reduction runs first in a mode that reports what it would have denied, for a full measurement window, with an alert on would-have-denied events. Skipping this step is why teams try once, cause an outage, and stop.
3. **The window must contain the periodic work.** Thirty days of evidence against a quarterly reconciliation job proves the job is unused right up until the quarter turns.
4. **Service accounts are in scope.** A review of humans only leaves the majority of the estate untouched, and machine identities are both more numerous and more broadly scoped.
5. **A review that ends in a spreadsheet has not happened.** The output is revocations with dates, or a written, owned exception. Nothing else counts.
6. **Break-glass is never revoked on usage evidence.** It is meant to be unused. It is governed by alerting and after-the-fact review instead.

## Workflow

### 0. Choose the entry path

The two jobs share a method and differ in where they start and what done means. Decide out loud before beginning.

| | Estate review | Targeted reduction |
| --- | --- | --- |
| Trigger | Cadence, an audit, an incident, a reorganisation | One over-broad role, one service account, one finding |
| Starts from | The full identity inventory, breadth first | The identity's own policy and usage, depth first |
| Ends when | Every identity has a decision — keep, reduce, remove, or an owned exception with a date | The identity's policy is enforced at the reduced scope with the alert still in place |
| Biggest risk | Breadth without depth: a complete spreadsheet, no revocations | Depth without breadth: one immaculate role beside two hundred untouched ones |
| Typical span | Weeks, with a measurement window inside it | Days, plus the audit-mode window |

An estate review that finds a serious escalation path should spawn a targeted reduction for it rather than swallowing it — the escalation path has a different urgency from the rest of the sweep.

### 1. Inventory every identity, not just the ones with a person attached

Enumerate from the provider, then reconcile against what people believe. The gap between the two lists is most of the finding.

- **Human identities** in the identity provider, plus anything with a local login that bypasses it — a cloud console user with a password, a database user, a legacy admin panel account, an appliance's local account.
- **Service accounts and machine users**, including ones created by a tool and never registered anywhere a human reads.
- **Workload identities**: instance profiles and roles, Kubernetes service accounts and their role bindings, federated workload identity for pods.
- **CI/CD identities**: pipeline roles, deploy keys, repository and organisation secrets that hold cloud credentials, self-hosted runner identities, and the OIDC trust relationships that let a pipeline assume a role.
- **Third-party and OAuth grants**: SaaS-to-SaaS integrations, marketplace apps, GitHub Apps and their permission sets, browser extensions with organisation-wide scopes, anything holding a webhook with write access.
- **Break-glass accounts**, listed deliberately and separately so nothing else in this procedure treats them as unused.
- **The ones nobody remembers**: a departed employee's personal access tokens, a vendor integration from a trial, a role trusted by an account you no longer work with, a key created for a migration that finished.

```bash
# AWS: every user, role and their attached policies (illustrative account id)
aws iam list-users --query 'Users[].{user:UserName,created:CreateDate,pwLastUsed:PasswordLastUsed}'
aws iam list-roles --query 'Roles[].{role:RoleName,trust:AssumeRolePolicyDocument}'

# GCP: every service account in a project, and who can impersonate them
gcloud iam service-accounts list --project=example-project
gcloud projects get-iam-policy example-project --format=json | jq '.bindings[]'

# Kubernetes: bindings that grant cluster-admin
kubectl get clusterrolebindings -o json \
  | jq -r '.items[] | select(.roleRef.name=="cluster-admin") | .metadata.name'

# GitHub: organisation members and their role, plus installed apps
gh api /orgs/example-org/members --paginate
gh api /orgs/example-org/installations --paginate
```

Record an owner per identity as you go. An identity with no owner is itself a finding, and it is the one most likely to be safe to remove.

### 2. Gather evidence of what is actually used

Two categories of source, and you want both.

**Provider-computed last-accessed data** is cheap and coarse: it tells you a service or permission has not been touched in the window, which is enough to propose a reduction.

```bash
# AWS: which services this role has actually reached, and when
aws iam generate-service-last-accessed-details --arn arn:aws:iam::111122223333:role/example-orders-role
aws iam get-service-last-accessed-details --job-id JOB_ID_EXAMPLE

# AWS: unused access findings across the estate
aws accessanalyzer list-findings-v2 --analyzer-arn ANALYZER_ARN_EXAMPLE

# GCP: recommendations to shrink over-granted roles, computed from 90 days of usage
gcloud recommender recommendations list \
  --project=example-project --location=global \
  --recommender=google.iam.policy.Recommender --format=json
```

**Raw audit logs** are the authority when you need to know exactly which action, by which principal, from where: CloudTrail, GCP Cloud Audit Logs, Entra sign-in and audit logs, the Kubernetes audit log, the GitHub organisation audit log, and the application's own authorisation decisions if it makes them.

Two lags decide whether your evidence means anything:

- **Telemetry delay.** Last-accessed data is computed periodically and can trail real use by hours. Judging "unused" from a report generated an hour ago tells you about a window that ended before that.
- **Periodicity.** The rare job is the one that breaks. A quarterly close, an annual certificate renewal, a disaster-recovery drill, a yearly audit export — all invisible in a thirty-day window and all real. Set the window from the longest genuine cycle you can identify, and where you cannot afford to wait, note the risk explicitly and lean harder on audit mode.

`references/evidence-queries.md` has the per-provider commands, what each telemetry source can and cannot prove, and its lag. Read it when gathering evidence rather than deciding what to do with it.

### 3. Classify every finding before proposing anything

Work the whole inventory through one table so the decisions are consistent and reviewable, rather than argued one at a time.

| Signal | Classification | Action |
| --- | --- | --- |
| Permission granted, never used in a window covering the periodic work | Over-grant | Remove the permission from the policy. Audit mode first; low risk once the window is honest. |
| Identity with no authentication at all in the window | Dormant identity | Disable, do not delete. Re-enable is seconds; recreate is an outage plus lost history. Delete after a bake period. |
| Wildcard action or resource (`*:*`, `s3:*`, `resource: *`) | Structural over-grant | Replace with the observed action set plus a documented margin. This is the highest-value change per hour spent. |
| Role that can modify its own policy, attach policies, pass a stronger role, or mint credentials for one | Escalation path | Treat as effectively holding the stronger permission. Close it, or add a condition and an alert. Higher urgency than any unused permission. |
| Human with standing administrative access | Standing admin | Move to just-in-time elevation with an approval and an expiry. Where that is impossible, make it break-glass with alerting. |
| Third-party or OAuth grant with no named internal owner | Unowned external access | Revoke unless an owner claims it this week. A trial that ended is the common case. |
| Cross-account trust or third-party role with no external id and no condition | Weak trust boundary | Add the external id and conditions, or remove the trust. Confused-deputy exposure is the risk being closed. |
| Human who left the organisation, with any credential still live | Departed human | Immediate, out of band from the review cadence. Tokens and keys are `secret-rotation`'s job once identified. |
| Human who changed teams, holding the previous team's access | Mover | Remove the access the previous role needed. The single most-missed case in every estate. |
| Service account with no owner and no usage | Orphaned service account | Disable, wait a full cycle, then delete with the trail recorded. |
| Long-lived static key where federation is available | Credential design defect | Migrate to OIDC or workload identity; the permission review and the credential change are separate pieces of work. |
| Permission attached directly to a user rather than a group or role | Unmanageable grant | Move it to a group or role so the next review reads ten rows instead of four hundred. |
| Break-glass account, unused | Working as designed | Leave it. Verify the alert on its use fires, and that its last use was reviewed. |

### 4. Propose the reduced policy from observed usage plus a margin

Build the candidate policy from the actions the evidence shows, then widen deliberately where narrowness would be brittle. A policy generated purely from thirty days of logs and applied without thought is the same mistake as a wildcard, in the other direction — it breaks the first time a legitimate but infrequent code path runs.

```bash
# AWS: generate a candidate policy from CloudTrail history for one identity
aws accessanalyzer start-policy-generation \
  --policy-generation-details principalArn=arn:aws:iam::111122223333:role/example-orders-role \
  --cloud-trail-details 'trails=[{cloudTrailArn=TRAIL_ARN_EXAMPLE,allRegions=true}],accessRole=ARN_EXAMPLE,startTime=2026-06-01T00:00:00Z'
```

Then read the result rather than applying it. Group related actions the workload plainly needs even if only one was seen; scope resources to a prefix or a tag condition rather than to the exact object names observed; keep the deny statements someone added deliberately. Note every widening and why, because that note is what the next reviewer needs.

### 5. Run it in audit mode, and alert on would-have-denied

This is the step that makes the whole procedure safe, and it is the one that gets skipped.

Where the platform has a genuine dry-run or audit-only mode, use it. Where it does not, build the equivalent: apply the reduced policy to a non-production copy of the workload, or attach the narrow policy alongside the broad one and alert on any action the narrow one would not have allowed.

| Platform | Audit-only mechanism |
| --- | --- |
| AWS | Access Analyzer policy validation and the unused-access analyzer; a canary role holding the reduced policy; CloudTrail as the record of what the narrow policy would have refused |
| GCP | Policy Troubleshooter and the recommender's simulation of a proposed change before applying it |
| Kubernetes | `kubectl auth can-i --list --as=system:serviceaccount:example-ns:example-sa`, plus admission policies in a warn or audit action before enforce |
| Entra ID | Conditional access policies in report-only mode |
| Service mesh, gateways, application authorisation | Almost all have a permissive or shadow mode that logs the decision without enforcing it |

Run it for a full measurement window — the same window length step 2 justified, for the same reason. Route would-have-denied events to a human who can tell a missing permission from an attempt that should be refused, because both look identical in the log and only one is a reason to widen the policy again.

### 6. Enforce, then keep the alert

Enforce when the audit window is clean, or when every would-have-denied event has been explained and folded back into the policy. Then leave the alert on: a denial after enforcement is either a genuine gap you missed or something that should be denied, and both are worth a look. Removing the alert on the day of enforcement discards the only detection you built.

Record the change where the next reviewer will find it — the policy repository, the ticket, the review record — with the evidence window, the audit-mode result, and who approved it. A reduction with no recorded rationale gets reverted after the next incident by somebody who does not know it was deliberate.

### 7. Close the structural patterns, not just the unused permissions

Unused permissions are the volume; the structural patterns are the blast radius. Work them explicitly, because each one looks harmless per line and dangerous only in combination.

- **Wildcards** in action or resource, especially on data stores, identity services and key management.
- **Escalation paths**: an identity that can edit its own or another identity's policy, attach an arbitrary managed policy, pass or assume a stronger role, create credentials for a stronger identity, or approve its own change. Analyse these as reachability — what can this identity become — rather than one permission at a time, which is exactly why they survive line-by-line review.
- **Trust boundaries**: cross-account or third-party roles with no external id, no source-account condition and no scoping to a specific principal.
- **Permanent credentials where federation exists**, particularly CI holding a long-lived cloud key.
- **Standing admin** instead of just-in-time elevation with approval, expiry and an audit trail.
- **Grants attached to users** rather than to groups or roles, which makes the estate unreadable and the next review unaffordable.

`references/escalation-paths.md` has each pattern with what to look for, the conditions that close it, and the queries that surface it across an account. Read it during step 7, and when a finding is about what an identity could become rather than what it did.

### 8. Separation of duties, break-glass, and the joiner-mover-leaver flow

**Separation of duties** applies to a deliberately small number of operations, because applied broadly it is ignored: production data export or bulk customer-data access; changes to audit logging, log retention and the alerting on it; granting administrative access; payment and payout release; deleting backups or changing backup retention; disabling security controls. Two people, enforced by the platform where possible rather than by policy text, and reviewed after the fact where enforcement is impossible.

**Break-glass** is legitimate and needs four properties, or it becomes standing admin with a dramatic name: it exists and is tested, so nobody invents an alternative during an incident; its use pages somebody who is not the user; it is time-bound and elevation expires automatically; and every use is reviewed afterwards with the reason recorded. Never judge it by usage evidence — it is designed to be unused.

**Joiners, movers, leavers.** Joiners get access from a role template rather than by copying a colleague, because copying is how one over-granted account becomes the estate's standard. Leavers are handled out of band and immediately; the review cadence is not the control for a departure. **Movers are the leak nobody handles**: a transfer adds the new team's access and removes none of the old, so the longest-serving people accumulate the broadest access precisely because they have been most useful. Make the transfer trigger a removal review with the old manager as the named owner, and treat the ability to answer "what did this person lose when they moved" as the test of whether the process is real.

### 9. Set a cadence the team will sustain

Cadence is a judgement about blast radius and detection speed, not a number handed down. Reviewing everything quarterly sounds rigorous and turns into a rubber stamp; reviewing the things that matter often, and the rest rarely, actually changes the estate.

Review more often, and in more depth, where the identity is broadly scoped, holds standing privilege, is reachable from outside, can escalate, or touches customer data. Review rarely — annually, or by exception — where the identity is narrow, machine-held, federated with short-lived credentials, and covered by alerting on anomalous use. Then spend the time you saved on continuous signals instead: unused-access findings raised as tickets automatically, an alert on any new wildcard policy or trust-policy change, an alert on break-glass use, and a monthly report of identities with no activity. Continuous detection beats a periodic sweep, and the sweep exists to catch what the detection does not model.

## Output format

Report a review, or one reduction, in this shape:

```markdown
## Path
[estate review | targeted reduction — and what triggered it]

## Identity
[who or what, its owner, and its blast radius in one sentence: what it could reach today]

## What it can do
[the effective permissions, including anything inherited through a group, a role chain or
a trust relationship. Note wildcards explicitly.]

## What it used
[the evidence, the source, the window, and the lag you waited past. Say plainly which
periodic work the window did or did not contain.]

## Proposed reduction
[the narrowed policy, with each deliberate widening beyond observed usage and why.]

## What could break
[named workloads and the periodic jobs. The honest list, including the ones you could not
rule out.]

## Audit-mode window
[mechanism, dates, would-have-denied events and how each was resolved.]

## Decision and owner
[enforced on a date, or an owned exception with an expiry. An exception with no expiry is
a decision not to review it again.]

## Not reduced
[what was left alone and why — including break-glass, which is meant to look unused.]
```

## Anti-patterns

**Revoking on intent instead of evidence.** The policy document and the runbook record what somebody thought was needed at a moment that has passed. Removing a permission because it looks unnecessary, without checking whether it was used, produces exactly the outage that ends access reviews at a company for years afterwards. Last-accessed data first; the document is a hypothesis.

**A thirty-day window against a quarterly job.** The evidence is clean, the reduction is applied, and the quarterly reconciliation fails eleven weeks later — long enough that nobody connects it to the review, so the finding is recorded as a mystery outage and the next reduction is refused. Set the window from the longest real cycle, and where you cannot wait, say so in writing and lean on audit mode.

**Reviewing humans and ignoring service accounts.** Human access certification is what auditors ask for, so it is what gets built, while machine identities are more numerous, more broadly scoped, rarely expire and are frequently shared between workloads. A review that certifies every employee and no service account has certified the smaller half of the estate and reported completeness.

**Wildcards because the exact action was unknown.** `s3:*` was a placeholder written under deadline with every intention of narrowing it later. Nobody comes back, because narrowing it means finding out what it uses, which is the work that was skipped in the first place. Generate the candidate policy from observed usage, widen it deliberately, and write the reason for each widening.

**Standing admin with a good reason.** The reason is always genuine — incident response, an on-call rota, a migration in flight. It is also permanent, because the condition that justified it never formally ends. Time-box the grant so it expires on its own; just-in-time elevation with approval and an audit trail keeps the capability and removes the standing exposure.

**A review that produces a spreadsheet and no revocations.** Every identity is listed, every owner has attested, the auditor is satisfied, and the estate is identical to last quarter. The review has cost weeks and reduced nothing. Count the review by revocations applied and exceptions with expiry dates, and report that number rather than coverage.

**Ignoring the escalation path because each permission looked harmless.** Line-by-line review sees policy edit here, role passing there, key creation somewhere else, and nothing that is obviously admin. In combination they are admin, reachable in a few steps by anyone who compromises the weakest one. Analyse what an identity can become, not only what it can do, and treat any path to a stronger identity as if the stronger identity were already granted.

## Reference files

- `references/evidence-queries.md` — read when gathering evidence: the last-accessed and audit-log queries for AWS, GCP, Entra ID, Kubernetes and GitHub, what each source proves and what it cannot, the reporting lag per source, and how to pick a measurement window that contains the periodic work.
- `references/escalation-paths.md` — read when a finding is about what an identity could become rather than what it did: the escalation and weak-trust patterns described defensively, the conditions and guard rails that close each one, and the queries that surface them across an account.
