# Triggers, untrusted fields and injection sinks

Read this during step 1, to build the trigger table, and step 2, to trace a field to
where it is expanded. Every row pairs a place an attacker can put a value with a place a
workflow might carelessly read it.

## Contents

- [GitHub Actions: attacker-controlled fields by event](#github-actions-attacker-controlled-fields-by-event)
- [Expansion sinks — where a value becomes syntax](#expansion-sinks--where-a-value-becomes-syntax)
- [Safe indirections](#safe-indirections)
- [GitLab CI equivalents](#gitlab-ci-equivalents)

## GitHub Actions: attacker-controlled fields by event

| Event | Attacker-controlled fields | Notes |
| --- | --- | --- |
| `pull_request` | `github.event.pull_request.title`, `.body`, `.head.ref`, `.head.label`, `.head.repo.full_name`, every file path and diff hunk | Read-only token, no secrets, for a fork PR — the fields are still attacker-authored and still reach whatever step interpolates them |
| `pull_request_target` | Same fields as `pull_request` | Runs with the base repository's write-scoped token and full secret access. The trigger itself is not the defect; combining it with a checkout of the fork's head is |
| `issue_comment` | `github.event.comment.body`; on a PR thread, `github.event.issue.pull_request` gives access to the PR's own untrusted fields once resolved | Fires on every comment, including ones from an account with no other access to the repository |
| `issues` | `github.event.issue.title`, `.body` | Anyone who can open an issue, which on a public repository is anyone |
| `workflow_run` | The triggering workflow's `name`, `head_branch`, `head_sha`, and any artefact it produced | Runs in the context of the default branch with its own permissions, so its danger is entirely in what it downloads and trusts from the triggering run |
| `workflow_dispatch` | Every `inputs:` value, as free text unless the input declares `type: choice` with an `options:` list | A `type: string` input with no pattern constraint is exactly as attacker-shaped as a PR title, for whoever has dispatch access |
| `push` | Branch name (`github.ref_name`) and tag name | A branch or tag name is attacker-chosen on any push-capable identity, including a bot with a narrow token |
| `discussion`, `discussion_comment` | Title and body, same shape as `issues` and `issue_comment` | Same treatment |

## Expansion sinks — where a value becomes syntax

| Sink | Why it is dangerous | Example shape |
| --- | --- | --- |
| `run: \|` with a direct `${{ }}` interpolation | The interpolation is substituted into the script text before the shell parses it. Whatever the value contains becomes part of the command line, not an argument to it | `run: echo "Building ${{ github.event.pull_request.title }}"` — the title is spliced into the shell command as text, not passed as data |
| `github-script` with the raw value passed to `eval`, a template string executed as code, or interpolated into a constructed shell command via `exec.exec` | Same class of defect inside JavaScript instead of bash | A comment body built into a string later passed to a shell runner |
| A composite action `input:` that the action's own `run:` step interpolates the same way | The vulnerability moves one hop away from the calling workflow, into an action this repository may not have written | Auditing a workflow that calls a third-party action is incomplete without reading what that action does with its inputs |
| `env:` set from the event payload, later read with unquoted shell expansion (`$VAR` rather than `"$VAR"`) | Unquoted expansion re-introduces word-splitting and globbing even though the substitution itself was safe | `run: echo $TITLE` after `env: TITLE: ${{ ... }}` still breaks if the title contains whitespace-shaped payloads, though not in the same way as direct interpolation |
| A YAML anchor or reusable workflow input that forwards an untrusted value unchanged | The sink is wherever the value is finally interpolated, which can be several files away from where it entered | Trace a `workflow_call` chain to its last consumer before concluding a value is unused |

## Safe indirections

- **Environment variable, then `"$VAR"`.** Set `env: TITLE: ${{ github.event.pull_request.title }}` and reference it in the script as `"$TITLE"`. The interpolation still happens, but into an environment variable assignment rather than into the command text, and the shell then treats the value as data.
- **`workflow_run` consuming an artefact without ever checking out the triggering commit.** The privileged job reads a build output — a test report, a compiled binary — and never runs code from the fork. This is the standard safe pattern for giving a fork PR a privileged review comment or a privileged status check.
- **Gated checkout.** When a job genuinely needs the credential and the code, gate the checkout step itself on `github.event.pull_request.head.repo.full_name == github.repository`, so the privileged path only ever runs same-repository code. This is a narrower fix than avoiding `pull_request_target` entirely, and it is the one a later edit most often silently removes — recheck it on every audit rather than trusting that it was checked once.
- **`actions/github-script` with the value passed as a function argument**, never built into a string that is then evaluated or executed. The script's own parameter binding does the same job an environment variable does in a shell step.

## GitLab CI equivalents

| GitHub Actions concept | GitLab CI equivalent | Difference worth naming |
| --- | --- | --- |
| `pull_request_target` | A pipeline triggered from a merge request targeting a protected branch, with `CI_JOB_TOKEN` or a project access token in scope | GitLab's merge-request pipelines run in the context of the source project by default; the equivalent danger is a protected-branch pipeline rule that still checks out merge request source code with elevated scope |
| `${{ github.event.* }}` interpolation into `run:` | `$CI_MERGE_REQUEST_TITLE`, `$CI_COMMIT_MESSAGE` and similar predefined variables interpolated into a `script:` line | Same defect, same fix: assign to a shell variable and reference it quoted, rather than building the line as a template string |
| Pinning `uses:` to a SHA | Pinning an `include:` to a specific commit SHA of the included project, not a branch | A floating `include:` ref is exactly as mutable as a floating Action tag |
| `id-token: write` for OIDC | GitLab's own OIDC/JWT `id_tokens:` keyword, exchanged with a cloud provider the same way | Scope the audience claim per consumer, not one shared token for every job |
