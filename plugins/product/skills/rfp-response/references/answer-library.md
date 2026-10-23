# Answer library

Read this when building or maintaining the approved-answer library, or when answering a
security questionnaire: what each answer records, how it is kept current, how to word
partial and planned answers, and notes on the standard questionnaires.

## Contents

- Fields every answer carries
- The review cycle
- Wording partial, alternative and planned answers
- Security questionnaires
- Keeping the library small

## Fields every answer carries

| Field | Why |
| --- | --- |
| Question pattern | The canonical form of the question, plus common variants, so search finds it |
| Approved answer | Short form for a matrix cell, long form for narrative |
| Scope | Product, plan, deployment model and region it is true for |
| Evidence | The document that proves it: policy, report section, docs page |
| Owner | A named person, not a team alias, who can re-verify it |
| Last reviewed | Date |
| Review interval | Usually six months for security and product answers, twelve for company facts |
| Restrictions | NDA required, not for public-sector bids, do not use after a stated date |

An answer with no owner is not approved; it is folklore with formatting.

## The review cycle

- When an answer passes its review date, it is flagged and cannot be inserted into a new
  response until its owner re-verifies or edits it.
- Product releases, a new hosting region, a certification renewal, a policy change or a
  security incident trigger an immediate review of the answers they touch, regardless of
  date.
- After each submission, new answers written under deadline are added with an owner and a
  short review interval, because they were written fast.

## Wording partial, alternative and planned answers

**Partially complies.** State what is available today and the limitation in one sentence
each. "Single sign-on via SAML 2.0 is available on the Enterprise plan. SCIM provisioning
is not available; users are provisioned on first login."

**Alternative.** Restate the need, then how it is met. "The requirement is to retain audit
records for seven years. The product retains them for one year; customers export them
daily to their own storage through the audit log API, where retention is under their
control."

**Planned.** Name the capability, give a date range from the product owner, and state the
status of the commitment. "Planned for the first half of next year. This is a current
roadmap intention and not a contractual commitment unless included in the agreement."

**Does not comply.** Say so, and offer the alternative if there is one. Evaluators trust a
response more when it contains honest gaps.

## Security questionnaires

- **Shared Assessments SIG.** A large standard questionnaire used in third-party risk
  programmes, in a full and a shorter "Lite" form. Maintain one completed copy per year
  and per product scope.
- **Cloud Security Alliance CAIQ.** A questionnaire mapped to the CSA Cloud Controls
  Matrix. Providers can publish a completed CAIQ in the CSA STAR registry, which some
  buyers accept in place of their own questionnaire.
- **EDUCAUSE HECVAT.** Used by higher-education institutions to assess vendors' security and privacy.
- **Custom spreadsheets.** Map each question to the library; most are rephrasings of
  questions already answered.

Answer from evidence, not memory. Where a SOC 2 report is the evidence, quote its scope:
which systems, which trust services criteria, which period, and whether there were
exceptions. Where an ISO/IEC 27001 certificate is the evidence, the scope statement and the
statement of applicability decide what it covers. Claiming a scope wider than the report is
a misstatement even if the control exists.

Questions about personal data handling (retention, deletion, sub-processors, breach
notification) are answered with the data protection owner, from the actual retention and
deletion design rather than from the privacy policy.

## Keeping the library small

A library of 2,000 answers that nobody reviews is worse than one of 300 that are current.
Merge duplicates, retire answers that have not been used in a year, and prefer one answer
with variants to several near-copies with different review dates.
