---
applyTo: "**"
---
<!-- source: REVIEW.md sha256: 0b214196e51588649e716b6afb94231222a1c4fd5c9f3c02bdc675e55c72e38b -->

# When reviewing a pull request

`AGENTS.md`'s Review guidelines section has the triggers and the comment format. This file
redefines severity and states what to skip. Mark every comment with one of three severity
markers: 🔴 Important, 🟡 Nit, 🟣 Pre-existing.

## Severity for this repository

🔴 Important (blocks merge) is:

- a validator rule weakened, bypassed or given a silent exemption;
- a dangling pointer: a `references/`, `scripts/` or `assets/` path named in prose that does not
  exist;
- a workflow missing a `permissions:` block, an action not pinned to a commit SHA, or
  user-controlled data reaching a `${{ }}` expression;
- a skill's `description` edited to make a check pass rather than because it changed for its own
  reason;
- a false statement of fact or law in documentation;
- a distributed artefact missing its licence notice;
- a secret;
- tool attribution in a commit, PR body or file.

A violation of `AGENTS.md`'s Boundaries is always 🔴 Important, even where it would otherwise
read as a nit.

🟡 Nit (not blocking) is everything else worth a comment. Cap nits at about five per review;
past that, name the pattern once and stop repeating it.

🟣 Pre-existing (never blocking) is a defect the diff did not introduce.

## Skip

Do not flag: generated or built output (`dist/`); a deliberately invalid skill, workflow or file
that a test constructs to exercise a rule; a case under `.claude/agents/benchmarks/`, whose
`change.patch` is a deliberately defective patch used to test the reviewer; and style a linter
already owns.

Full rules: `REVIEW.md`, and the Review guidelines section of `AGENTS.md`.
