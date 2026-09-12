---
paths:
  - ".github/workflows/**"
---

# Changing a workflow

`AGENTS.md` is the authority; this is the part of it that applies to the file you just
opened. Every item here is something zizmor, actionlint or the permissions audit will
fail the build for, and each exists because the failure is otherwise silent.

- **Plan mode first**, for the same reason as the validator: these decide whether every
  other change merges.
- **Pin every action to a full-length commit SHA**, commented with the exact release tag
  that SHA belongs to — `# v7.0.1`, never `# v7`. The SHA is what makes it immutable; the
  comment is what lets Dependabot bump it. A major-version comment goes stale the moment
  upstream moves the floating tag.
- **Set a top-level `permissions:` block.** An absent one inherits the repository default,
  which is usually write access to everything.
- **Set `timeout-minutes:` on every job.** Without one a hung job runs to the six-hour
  platform default, which reads as slow CI rather than broken CI.
- **`persist-credentials: false` on every checkout.** Nothing here pushes from CI.
- **`set -Eeuo pipefail` in every inline `run:` block.** actionlint runs shellcheck over
  them in CI, and nothing else does: `scripts/check_shell.py` reads shipped scripts and
  fenced Markdown blocks, never a workflow.
- **Never pipe a downloaded script into a shell.** Fetch at a pinned version and check it
  against a recorded digest.
- **A cancelled job counts as a failure to the aggregate.** That is deliberate: a required
  check that was cancelled is not a check that passed.

`workflow_dispatch` defaults do not apply to a `schedule` run — every input arrives empty,
so give any cron-triggered job explicit fallbacks.
