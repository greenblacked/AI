# Artefact catalogue

The controls that appear in nearly every SOC 2 and ISO 27001 scope, with the artefact that proves each, where it lives, an example of collecting it, and the reason auditors most often send it back. Organisation, repository and account names are placeholders. Keep the exact command or query beside every export you hand over; that is the provenance the auditor tests.

## Contents

- [Change management](#change-management)
- [Logical access: joiners, movers, leavers](#logical-access-joiners-movers-leavers)
- [Access reviews](#access-reviews)
- [Backups and restore tests](#backups-and-restore-tests)
- [Vulnerability management](#vulnerability-management)
- [Logging and monitoring](#logging-and-monitoring)
- [Policies, training and screening](#policies-training-and-screening)
- [ISO 27001 Annex A pointers](#iso-27001-annex-a-pointers)

## Change management

**Control claim.** Every production change is reviewed and approved by someone other than its author before deployment.

| Item | Detail |
| --- | --- |
| Primary artefact | Merged pull requests for the period, each with its approving review and the deploy that shipped it |
| Configuration artefact | Branch protection or ruleset on the production branch, with its change history |
| Population source | Deploy log or cloud audit trail, reconciled against merged pull requests |
| Common rejection | The approver is the author, or the deploy happened before the approval timestamp |

```bash
# Merged pull requests in the period (the search API returns at most 1,000 results; split the range if you exceed it)
gh api -X GET search/issues --paginate \
  -f q='repo:example-org/example-repo is:pr is:merged merged:2026-01-01..2026-06-30' \
  --jq '.items[] | [.number, .user.login, .closed_at] | @tsv'

# Reviews on one sampled pull request
gh api /repos/example-org/example-repo/pulls/1234/reviews \
  --jq '.[] | [.user.login, .state, .submitted_at] | @tsv'

# Current branch protection and rulesets (requires admin on the repository)
gh api /repos/example-org/example-repo/branches/main/protection
gh api /repos/example-org/example-repo/rulesets
```

Branch protection read today shows today. For the period, keep the configuration in code or export it monthly so a change mid-period is visible.

## Logical access: joiners, movers, leavers

**Control claim.** Access is granted on an approved request, changed on a role change, and removed within a stated time after departure.

| Item | Detail |
| --- | --- |
| Primary artefact | Identity-provider lifecycle events for the period (activations, deactivations, group changes) |
| Population source | HR system hires, transfers and terminations — not the identity provider |
| Reconciliation | Each termination matched to a deactivation, with the gap in hours or days |
| Common rejection | Termination date and deactivation date differ by more than the policy allows, or the leaver kept a local account outside single sign-on |

Examples of where the events live:

- Okta: the System Log API, `GET /api/v1/logs` with `since`, `until` and a filter on event types such as `user.lifecycle.deactivate`.
- Microsoft Entra ID: Microsoft Graph `GET /auditLogs/directoryAudits` filtered by activity and date.
- AWS IAM users outside single sign-on: the credential report.

```bash
aws iam generate-credential-report --query State --output text
# repeat until the state is COMPLETE; get-credential-report can return a stale report meanwhile
aws iam get-credential-report --query Content --output text | base64 -d > credential-report-2026-06-30.csv
```

Accounts that bypass single sign-on (database users, a console password, an appliance's local admin) are where leavers survive. List them per system and include them in the reconciliation.

## Access reviews

**Control claim.** Access to in-scope systems is reviewed at a stated frequency and inappropriate access is removed.

| Item | Detail |
| --- | --- |
| Primary artefact | The review record per system: the access list as reviewed, the reviewer, the decision per account, the date |
| Follow-through artefact | The removal events for every account marked "remove", dated after the review |
| Common rejection | The list reviewed was not complete (generated without provenance), or removals marked in the review never happened |

Performing the review is `access-review`'s job. The evidence point is that the list's generation, the decisions and the removals are each kept.

## Backups and restore tests

**Control claim.** Backups run on schedule, failures are followed up, and restores are tested at a stated frequency.

```bash
aws backup list-backup-jobs \
  --by-created-after 2026-01-01T00:00:00Z --by-created-before 2026-07-01T00:00:00Z \
  --query 'BackupJobs[].[BackupJobId,ResourceArn,State,CreationDate]' --output text
aws backup list-restore-jobs \
  --by-created-after 2026-01-01T00:00:00Z --by-created-before 2026-07-01T00:00:00Z \
  --query 'RestoreJobs[].[RestoreJobId,Status,CreationDate]' --output text
```

| Item | Detail |
| --- | --- |
| Common rejection | Failed jobs with no ticket showing follow-up; a restore test that is a console screenshot with no record of what was verified after the restore |

## Vulnerability management

**Control claim.** Findings are remediated within deadlines set by severity, or formally accepted.

| Item | Detail |
| --- | --- |
| Primary artefact | Scanner export of findings opened and closed in the period, with first-seen and resolved dates |
| Exceptions artefact | Register entries for findings past deadline that were accepted (see `risk-acceptance-register`) |
| Common rejection | Severity deadlines in the policy that no report measures; suppressions with no approval or expiry |

## Logging and monitoring

**Control claim.** Security-relevant events are logged, retained and reviewed, and alerts are triaged.

```bash
aws cloudtrail describe-trails
aws cloudtrail get-trail-status --name example-org-trail
```

| Item | Detail |
| --- | --- |
| Primary artefact | Logging configuration and retention settings, plus a sample of alerts with their triage tickets |
| Common rejection | Retention shorter than policy states; alerts with no evidence anyone looked |

## Policies, training and screening

| Control | Artefact | Common rejection |
| --- | --- | --- |
| Policies approved and reviewed | Policy documents with version history and approver | Last approval outside the stated cycle |
| Security awareness training | Training platform completion export for the period, reconciled against headcount | New joiners who never completed it |
| Background screening | HR record of completed screening per new joiner, reconciled against hires | Contractors outside the HR system |

## ISO 27001 Annex A pointers

The 2022 revision of Annex A has 93 controls in four themes: organisational, people, physical and technological. Controls that map to the sections above include 5.15 Access control, 5.18 Access rights, 8.13 Information backup, 8.8 Management of technical vulnerabilities, 8.15 Logging, 8.16 Monitoring activities and 8.32 Change management. Check numbering against your own Statement of Applicability rather than this list; it is the document the auditor holds you to.
