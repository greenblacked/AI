---
applyTo: ".github/workflows/**"
---
<!-- source: .claude/rules/workflows.md sha256: 9ad8be77d50d95a314885d78efa8ff7cdcd72f7284ff61c5500519abb810a0fe -->

# Changing a workflow

`AGENTS.md` is the authority. Workflows decide whether every other change merges and run with
real credentials. The key rules, kept inline because a reviewer may not follow links:

- Agree the approach before editing, as for the validator.
- Pin every action to a full-length commit SHA, commented with the exact release tag that SHA
  belongs to (`# v7.0.1`, never `# v7`).
- Set a top-level `permissions:` block; an absent one inherits the repository default.
- Set `timeout-minutes:` on every job.
- `persist-credentials: false` on every checkout.
- `set -Eeuo pipefail` in every inline `run:` block.
- Never pipe a downloaded script into a shell; fetch at a pinned version and check a recorded
  digest.
- A cancelled job counts as a failure to the aggregate, deliberately.
- A workflow `permissions:` change, a new API write in a shipped script, or a
  `workflow_run`, `schedule` or `pull_request_target` trigger needs a live run before merge, or a
  named run right after merge for a default-branch-only trigger, a push trigger filtered to
  `main`, or a tag trigger (`AGENTS.md`, Triggers table).
- `workflow_dispatch` defaults do not apply to a `schedule` run: give any cron-triggered job
  explicit fallbacks.

Full rules: `.claude/rules/workflows.md`.
