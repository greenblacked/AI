---
paths:
  - ".github/workflows/*.yml"
  - ".github/workflows/*.yaml"
---

# Untrusted workflow input

Loads when a GitHub Actions workflow is read or edited. A workflow that looks correct can
still hand a stranger a shell, so the questions below are about what an outsider controls.

- A value an outsider controls reaches a `run:` or `script:` block only through an `env:`
  variable, read as `"$VAR"` in the shell. That covers the pull request title, body and head
  branch, an issue or comment or review body, a commit message and `github.head_ref`.
  Interpolating the expression into the block splices the value into the command text before
  the shell parses it, and quoting around it does not help.
- A job on `pull_request_target`, `workflow_run` or `issue_comment` holds the base
  repository's token and secrets, so it never checks out or runs the pull request's head, and
  never runs an artefact a fork produced.
- Set a top-level `permissions:` block, read-only by default, and widen it on the one job that
  needs more. `id-token: write` belongs only on the job that exchanges the token.
- Pin every `uses:` to a full commit SHA with the release tag in a trailing comment.
- When the change touches a trigger, a checkout or a token grant, trace each untrusted field
  to the step that expands it with the `pipeline-hardening` skill, and record the result in
  its `pipeline-change-record.md` template.
