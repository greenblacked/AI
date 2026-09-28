---
paths:
  - ".github/workflows/**"
---

# Changing a workflow

`AGENTS.md` is the authority; this is the part of it that applies to the file you just
opened. The permissions audit fails the build for the top-level `permissions:` block,
`timeout-minutes`, `persist-credentials: false`, and a pin that is not forty hex
characters; zizmor's `ref-version-mismatch` audit fails it separately when a pin's
trailing comment names a tag the SHA does not actually correspond to, which is the other
half of the SHA-pinning rule the permissions audit's own character count cannot see.
`check_workflows.py`'s aggregate check together with `check_job_results.py` fails it for
a job that would let a cancellation through as a pass rather than a failure. No gate
catches the rest: plan mode first, because it is a habit of the person editing rather
than a property of the file itself; `set -Eeuo pipefail`, which `check_workflows.py`
requires only inside the aggregate's own helper step, not every `run:` block; never
piping a downloaded script into a shell; and the live run the last bullet asks for,
because no offline gate reads a permission against what the API enforces.

- **Plan mode first, in the main conversation before delegating; a subagent working from
  a settled brief never enters it** — for the same reason as the validator: these decide
  whether every other change merges.
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
- **A workflow `permissions:` change, a new API write in a shipped script, or a
  `workflow_run`/`schedule`/`pull_request_target` trigger needs a live run before
  merge**, or a named run right after merge for a default-branch-only trigger, a push
  trigger filtered to `main`, or a tag trigger — `AGENTS.md`'s Triggers table.

`workflow_dispatch` defaults do not apply to a `schedule` run — every input arrives empty,
so give any cron-triggered job explicit fallbacks.
