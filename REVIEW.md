# Review instructions

For Claude Code's managed GitHub code review only. `AGENTS.md`'s Review guidelines
section has the triggers and the comment format; this file only redefines severity and
states what to skip, as short as it can be — length here dilutes it.

## Severity, redefined for this repository

🔴 Important (blocks merge) is:

- a validator rule weakened, bypassed or given a silent exemption;
- a dangling pointer — a `references/`, `scripts/` or `assets/` path named in prose that
  does not exist;
- a workflow missing a `permissions:` block, an action not pinned to a commit SHA, or
  user-controlled data reaching a `${{ }}` expression;
- a skill's `description` edited to make a check pass rather than because it changed for
  its own reason;
- a false statement of fact or law in documentation;
- a distributed artefact missing its licence notice;
- a secret;
- tool attribution in a commit, PR body or file.

A violation of `AGENTS.md`'s or `CLAUDE.md`'s Boundaries is always 🔴 Important, even
where it would otherwise read as a nit.

🟡 Nit (not blocking) is everything else worth a comment. Cap nits at about five per
review; past that, name the pattern once and stop repeating it.

🟣 Pre-existing (never blocking) is a defect the diff did not introduce.

## Skip

Do not flag: generated or built output (`dist/`); fixtures under `tests/` recorded
deliberately wrong to exercise a rule; and style a linter already owns.
