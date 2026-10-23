---
name: risk-acceptance-register
description: "Record knowingly accepted risk so the acceptance expires instead of becoming permanent: each entry states the risk, the compensating control and how it is verified, an accountable owner above the engineer who proposed it, and an expiry date; every tool-level suppression points to an entry; owners are reminded 30 days before expiry; an expired entry counts as an open finding; and the register is the one place auditors and security review read. Use when a team is shipping with a known gap, wants to suppress or waive a finding, needs an exception to a security policy, or asks \"who signs off on this risk\", \"can we accept this for now\", or \"why are these ignores still here\". Not for deciding which dependency alerts matter (dependency-triage), recording a design choice (decision-record), finding the threats in a design (threat-model), or collecting audit evidence (control-evidence)."
allowed-tools: "Read, Grep, Glob"
---

# Risk Acceptance Register

Done means every known gap the organisation is living with has one register entry with a named accountable owner, a compensating control someone has checked, and a date on which it stops being accepted — and that every suppression in every scanner points to one of those entries, so nothing is quietly ignored outside the register.

The usual failure is that acceptance is permanent by default. An engineer adds an ignore line to make the build pass, writes "accepted risk" in the pull request, and the decision outlives the people, the architecture and the compensating control that justified it. Three years later an auditor asks who accepted it, and the answer is a commit by someone who left. The second failure is the wrong owner: the person proposing the acceptance approves it, so the register records convenience rather than a decision by someone with the authority and budget to fix the gap.

## Scope

Use for: a finding that will not be fixed before release; a waiver or exception to a security standard or policy; a scanner suppression of a true positive; a gap a threat model or penetration test named and the business chose to carry; setting up or cleaning up the register itself.

Do not use for: working a queue of dependency alerts into decisions (`dependency-triage`; the alerts it decides to carry are entered here); recording why an architecture was chosen (`decision-record`); identifying threats in a design (`threat-model`); collecting evidence for an audit (`control-evidence`, which reads this register).

## Hard gates

1. **Acceptance is of a real risk.** A false positive is not accepted; it is closed with the evidence that shows it does not apply. Mixing the two inflates the register and hides the entries that matter.
2. **The accountable owner sits above the proposer** and owns the budget or roadmap that could fix the gap. Self-approval is not acceptance.
3. **Every entry expires.** There is no permanent acceptance. Renewal is a new decision with fresh evidence, not an extension of the date.
4. **Expired means open.** An entry past its date is reported as an open finding at its original severity, in the same report as findings nobody accepted.
5. **No suppression without an entry.** A scanner ignore, a lint disable or a policy exemption that names no register id is itself a finding.

## Workflow

### 1. Decide it is an acceptance

Before writing anything, classify the item:

| Situation | Path |
| --- | --- |
| The finding does not apply (unreachable code, test-only dependency, wrong version match) | Close as false positive with the evidence; no register entry |
| It applies and will be fixed before the release | Fix it; no register entry |
| It applies, a fix is planned but will land after release | Register entry, expiry at the planned fix date plus a short margin |
| It applies and the business chooses to carry it | Register entry, expiry at the policy maximum for its severity |
| It applies and someone else carries it (insurer, vendor contract) | Transfer: register entry recording the transfer and its evidence |

### 2. Write the entry

Each entry records, at minimum:

- **Risk statement** in the form "if this happens, this is the consequence, to whom". "CVE-2026-1234 in libfoo" is a finding id, not a risk.
- **Source**: the finding id, scanner or report, and the affected assets.
- **Severity** on the same scale as the source, so expired entries can be counted alongside unaccepted findings.
- **Compensating control**, and how it is verified: what someone would check, and when it was last checked. A control nobody can verify is a hope.
- **Proposer** and **accountable owner**, by name.
- **Approval date**, **expiry date**, and the **reason** the gap is not being closed now.
- **Exit condition**: what would close the entry early — the upstream fix, the migration, the contract change.

`references/register-schema.md` has the field table, a YAML example, the approval matrix by severity and suggested maximum terms. Read it when setting the register up or writing the first entry.

### 3. Get the right approval

Apply the approval matrix. Higher severity needs a more senior owner and a shorter term. Approval is recorded where it can be audited later: a reviewed pull request to the register file, or the approval step in a tracking tool, not a chat message.

The owner should be able to answer, unprompted: what the gap is, what covers it in the meantime, and what it would cost to close. If they cannot, they are signing rather than accepting.

### 4. Tie every suppression to an entry

Wherever a tool can ignore a finding, the ignore carries the register id and, where the tool supports it, the same expiry date. Snyk's `.snyk` policy and Trivy's ignore file both accept an expiry on an ignore entry; use it, so the scanner itself starts failing when the acceptance lapses. Tools without native expiry (most linters, many policy engines, GitHub alert dismissals) get the register id in the comment or dismissal reason.

Then add a CI check that reads every suppression in the repository, extracts the register id, and fails when the id is missing, unknown or expired. `references/register-schema.md` describes the check. This is what turns the register from a document into a control.

### 5. Re-surface before expiry

A scheduled job notifies the accountable owner 30 days before an entry expires, and again on the day. The owner chooses: fix, renew with a new approval (which resets `approved_on`, so the term is counted from the renewal) and fresh evidence that the compensating control still works, or let it lapse into an open finding.

Renewal limits matter. Repeated renewal is a decision to carry the risk indefinitely, made in instalments. Escalate the renewal that goes past the limit in the approval matrix's last column one level up (for a high finding, which allows one renewal, the third term).

### 6. Report expired entries as open findings

Every security or risk report counts expired acceptances as open findings at their original severity. If the dashboard shows them separately, or as "accepted (expired)", nobody acts on them; the point of expiry is that the acceptance stops protecting the finding from the report.

### 7. Make it the single source

Auditors, security review, the threat model's "not mitigating" list and the vulnerability backlog all read this register and nothing else. If a second list exists (a spreadsheet in a security folder, a tracker label), migrate it and delete it. ISO 27001 clause 6.1.3 expects risk owners to approve the treatment plan and accept residual risk; this register, with its approvals, is that record.

Review the whole register quarterly with the security lead: entries per owner, renewals, entries whose compensating control has not been re-checked, and entries whose exit condition has already happened but nobody closed.

## What to hand back

- The entry or entries written, each with owner, compensating control, expiry and approval record.
- The suppressions changed to carry register ids, and any found with none.
- The expiry check: whether it exists in CI, and what it currently fails on.
- Entries expiring in the next 30 days, by owner.

## Anti-patterns

**The ignore line as the acceptance.** It lives in a config file nobody reads, has no owner and no date, and survives every reorganisation. The ignore line points to the acceptance; it is not the acceptance.

**The proposer approves.** The engineer who wants the release to ship signs off the risk of shipping it. Route approval upward, to the person who would have to explain the incident.

**A compensating control nobody checks.** "Protected by the WAF" was true when written. Record how it is verified and re-verify on renewal.

**Expiry as a formality.** The date passes, the entry is quietly extended a year, and the report never changes. Expired means open, renewal means a new decision.

**Two registers.** The audit one and the engineering one diverge within a quarter, and each is wrong about the other's entries.

## Reference files

- `references/register-schema.md` — read when setting the register up or writing an entry: field definitions, a YAML entry, the approval matrix by severity with suggested maximum terms, and the CI expiry check.
