# Register schema, approvals and the expiry check

## Contents

- [Where the register lives](#where-the-register-lives)
- [Fields](#fields)
- [Example entry](#example-entry)
- [Approval matrix and maximum terms](#approval-matrix-and-maximum-terms)
- [Suppression convention](#suppression-convention)
- [The CI expiry check](#the-ci-expiry-check)
- [The reminder job](#the-reminder-job)

## Where the register lives

A YAML file in a repository that CI can read, changed only through reviewed pull requests, works for most engineering organisations: the approval is the pull request review, the history is the git log, and the expiry check runs beside the code that carries the suppressions. A governance tool works too, provided CI can query it; a register CI cannot read cannot fail a build.

Protect the file with a code-owners rule naming the security team, so an entry cannot merge without someone outside the proposing team seeing it.

## Fields

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | Stable, never reused: `RA-2026-007` |
| `title` | yes | One line a non-specialist understands |
| `risk` | yes | If this happens, this is the consequence, to whom |
| `source` | yes | Finding ids, scanner, report or threat-model reference |
| `assets` | yes | Services, repositories or systems affected |
| `severity` | yes | Same scale as the source finding |
| `treatment` | yes | `accept`, `accept-until-fix` or `transfer` |
| `compensating_control` | yes | What reduces likelihood or impact meanwhile |
| `control_verification` | yes | How it is checked, by whom, and the last date it was |
| `reason` | yes | Why the gap is not being closed now |
| `exit_condition` | yes | What closes the entry early |
| `proposer` | yes | The person asking |
| `owner` | yes | The accountable person, above the proposer |
| `approved_on` | yes | ISO date of the current approval; a renewal sets it to the date the renewal was approved |
| `expires_on` | yes | ISO date, within the maximum term for the severity |
| `renewals` | yes | Count, starting at 0; each renewal adds one, links its approval, and resets `approved_on` and `expires_on` |
| `status` | yes | `active`, `closed` (fixed or exit condition met), `expired` |

## Example entry

```yaml
- id: RA-2026-007
  title: Legacy export endpoint still accepts TLS 1.1 from one partner
  risk: >-
    If the partner's connection is downgraded and intercepted, order exports for that
    partner's customers could be read in transit.
  source: [pentest-2026-q2-F4]
  assets: [orders-export-gateway]
  severity: medium
  treatment: accept-until-fix
  compensating_control: >-
    TLS 1.1 allowed only from the partner's two published egress addresses; all other
    clients require TLS 1.2 or later.
  control_verification: >-
    Gateway configuration test in CI asserts the allowlist; last checked 2026-09-30 by the
    platform on-call engineer.
  reason: Partner's client upgrade is scheduled for their December release.
  exit_condition: Partner confirms TLS 1.2 in production; allowlist entry removed.
  proposer: integrations team lead
  owner: head of platform engineering
  approved_on: 2026-10-01
  expires_on: 2026-12-31
  renewals: 0
  status: active
```

Names in a real register are people, not roles; roles are used here only as placeholders.

## Approval matrix and maximum terms

The numbers are a starting point to adapt and write into policy, not a standard. What matters is that the matrix exists, is written down, and shortens the term as severity rises.

| Severity | Accountable owner at least | Maximum term per approval | Renewals before escalation |
| --- | --- | --- | --- |
| Critical | Executive owner of security (for example the CISO) and the business owner of the asset | 30 days | 0: a second term goes to the executive team |
| High | Director over the affected service | 90 days | 1 |
| Medium | Engineering manager over the affected service, not the proposer's peer | 180 days | 2 |
| Low | Engineering manager | 365 days | 2 |

A critical finding that is exploited in the wild (listed in CISA's Known Exploited Vulnerabilities catalogue, for instance) usually should not be accepted at all; say so in policy rather than leaving it to the approver.

## Suppression convention

Every suppression carries the register id in a fixed form the check can find, for example `risk:RA-2026-007`:

- A Bandit or Semgrep inline ignore (`# nosec`, `# nosemgrep`) with the id in the same comment.
- A Checkov skip comment, whose free-text reason field holds the id.
- A line in a Trivy ignore file or an entry in a Snyk policy file, with the expiry set to the register's `expires_on` and the id in the comment or reason.
- A GitHub code-scanning or Dependabot alert dismissal, with the id in the dismissal comment.

## The CI expiry check

The check has three parts. Write it in whatever language the repository already uses for tooling, and give it a test of its failure path.

1. **Collect suppressions.** Search the tree for each suppression marker the repository's tools use (the list above), and record file, line and any `risk:RA-…` id on the line or the line above.
2. **Load the register** and index entries by id.
3. **Fail** when a suppression has no id, an id not in the register, an id whose entry is `closed`, or an id whose `expires_on` is before today. An entry is valid through its `expires_on` date inclusive, which is why the reminder also fires on that day. Also fail on an entry whose `expires_on` is later than `approved_on` plus the maximum term for its severity (a renewal resets `approved_on` to the renewal's approval date, so a valid renewal is measured from that date and not from the original approval; an entry renewed without that reset fails this check), or whose `renewals` exceeds the matrix limit without a linked escalation approval; otherwise the term limits are policy text that nothing enforces. Print each with file and line (or register id) so the fix is obvious.

Warn, without failing, when an active entry has no suppression pointing at it — either the finding was fixed and the entry should close, or the suppression is missing its id.

Run it on every pull request and on a daily schedule on the default branch, because an expiry happens on a date, not on a commit.

For alert dismissals held by a platform rather than in the tree, run the same comparison on the schedule against the platform's API export, and report rather than fail.

## The reminder job

Daily, select active entries whose `expires_on` is 30 days away or today, and notify each owner directly — a message to a person, or a ticket assigned to them, not a post to a shared channel. Include the entry, the compensating control's last verification date and the three choices: fix, renew with fresh approval, or let it lapse into an open finding.
