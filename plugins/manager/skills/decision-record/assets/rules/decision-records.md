---
paths:
  - "docs/decisions/**/*.md"
  - "docs/adr/**/*.md"
---

# Decision records

Loads when an architecture decision record is read or edited. The record is read months
later by someone who was not in the room, so what it must carry is the choice, what lost
and why, and how anyone would find out it was wrong.

- Label the type and the status in the first lines: `status:` in the front matter, and the
  record's kind (decision, recommendation, status or FYI) in the title or first sentence.
- List at least two options under `## Considered Options`. Do nothing counts, and is often
  the honest runner-up. A record naming one option documents a conclusion, not a decision.
- Give every option that was not chosen a specific reason it was rejected, in the
  `## Pros and Cons of the Options` entry or beside the outcome.
- State reversibility: type-2, cheap to undo, or type-1, one-way, with what undoing costs.
- Name a mechanism under `### Confirmation`: a check, where it lives, and an owner with a
  date. If none is agreed, write `[TK: no verification mechanism agreed]` and leave it
  visible.
- Write `[TK: ...]` for any figure, date or name the author did not supply, and name the
  source of every impact claim.
- An accepted record is not edited to change the decision. Write a new one, set the old
  status to `superseded by ADR-NNNN` and link both ways.
- Keep named individuals' performance out of the record.
- Drafting or reviewing one is the `decision-record` skill; start from its
  `adr-template.md`.
