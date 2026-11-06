---
paths:
  - "**/backend.tf"
  - "**/*.tfbackend"
  - "**/.terraform.lock.hcl"
  - ".github/workflows/*terraform*.yml"
  - ".github/workflows/*tofu*.yml"
---

# Terraform apply handoff

Apply changes only through the handoff below; each line says why, so a change that breaks
one is a decision rather than a drift.

- Apply only the saved plan a trusted run produced, with an approval bound to its digest. An approval of text, or of a replan, authorises nothing that ran.
- Never run an unqualified `apply` or pass `-auto-approve`; the plan it builds was never reviewed.
- Never fetch a plan by display name or "latest". Identify it by producing run, digest and artifact identifier.
- Keep a plan or plan JSON out of pull request comments and public logs; it carries resource values.
- Apply under the state queue keyed by backend and state selector, so two writers cannot race.
- Treat a new plan, a changed input, a dependency or lock-file change, or any state write since the plan as invalidating the approval; require a new review.
- Prove it with the approval record for the apply, filled in from `apply-approval-record.md`.
