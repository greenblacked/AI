---
paths:
  - "**/churn/**/*.csv"
---

# Churn coding

Loads when a churn coding sheet is read or edited. A coded reason is a claim about why an
account left, and a claim needs something a second reader can check.

- Every row with a primary code carries quoted evidence in `Key evidence`: a line from a
  cancellation note, ticket or success note, with its ticket or note reference. A summary
  in your own words is not evidence.
- The dropdown answer is recorded in its own column and never decides the code. "Too
  expensive" with a ticket thread about a missing integration is a missing-capability row.
- Use only the codes in the period's codebook. If none fits, leave the code blank and say
  why in the evidence cell rather than coining a new code mid-sample.
- Redact emails, phone numbers and personal names in quoted lines.
- Size the codes with the `churn-analysis` skill, and give the readout in its
  `churn-readout.md` template.
