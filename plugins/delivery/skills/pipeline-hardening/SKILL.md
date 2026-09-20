---
name: pipeline-hardening
description: "Harden or audit a CI workflow, GitHub Actions first, GitLab CI too: untrusted PR title, branch, comment or fork code reaching a run: step; pull_request_target, workflow_run or issue_comment plus checkout of untrusted code; token/secret reach per job; actions/tools pinned to a SHA, tag recorded; OIDC over long-lived keys, subject-claim gated; cache/artefact poisoning across the fork boundary; provenance checked at consumption; zizmor findings judged, not counted. Use for \"is our github actions workflow safe\", \"can a fork PR steal our secrets\", \"should we pin actions to a sha\", \"audit our CI for injection\", \"do we need pull_request_target\", \"move CI off aws keys to oidc\". Not for speed (ci-pipeline-design), red CI (ci-triage), diffs (security-review), images (image-hardening), leaked keys (secret-rotation), IAM (access-review), new workflows (code-scaffold)."
allowed-tools: "Bash(zizmor:*), Bash(actionlint:*), Bash(gh:*), Bash(git:*), Bash(jq:*), Bash(rg:*), Read, Grep, Glob, Edit, Write"
---

# Pipeline Hardening

A hardened workflow is one where every value an attacker can influence — a PR title, a branch name, an issue or comment body, a commit message, the contents of a fork's own repository — has been traced to the step that expands it, and every job that touches a credential either cannot also run untrusted code or has been proven not to.

The job is adversarial in a way most CI review is not. `ci-pipeline-design` optimises a workflow for structure and speed on the assumption that everyone running it is trying to ship; this skill assumes the opposite — that the next pull request is trying to take the repository over — and reads the same YAML for what it lets a stranger do rather than what it lets a teammate do. The failure mode is specific and repeats across almost every real incident: a workflow interpolates an attacker-controlled string directly into a shell command instead of passing it through an environment variable, or it runs on `pull_request_target` — which carries a write-scoped token and full secret access — and then checks out the fork's own head commit, executing the attacker's code with the base repository's credentials. Both defects are invisible to a reviewer reading for correctness, because the YAML is syntactically fine and the exploit is in what GitHub does with it, not in what the file says.

## Scope

Use for: auditing or hardening a workflow definition that already exists — GitHub Actions first, GitLab CI where the equivalent construct exists; deciding whether `pull_request_target`, `workflow_run` or `issue_comment` is safe as used; tracing untrusted input to the step that expands it; reviewing token permissions and secret reach per job; checking that actions and fetched tools are pinned to a SHA with the release tag recorded; moving a pipeline off long-lived cloud keys onto OIDC; reviewing cache and artefact handling across the fork boundary; judging a zizmor report.

Do not use for: pipeline structure, caching strategy and wall-clock speed on a workflow nobody is attacking — `ci-pipeline-design`; a pipeline that is red right now — `ci-triage`; the application code in a diff — `security-review`; the container image the pipeline builds — `image-hardening`; a credential that has already leaked — `secret-rotation`; a live cloud or identity estate — `access-review`; writing a new workflow file from a description — `code-scaffold`.

## Workflow

### 1. Enumerate every trigger and what it carries

Before reading a single step, list every `on:` trigger in the file and the attacker-controlled fields each one hands the workflow. A trigger nobody names is a trigger nobody has reasoned about.

```bash
rg -n '^on:|pull_request|pull_request_target|workflow_run|issue_comment|workflow_dispatch|push:' .github/workflows/*.yml
```

| Event | Who can cause it | Untrusted fields it carries |
| --- | --- | --- |
| `pull_request` | Anyone who can open a PR, including a fork | title, body, branch name, head SHA, files changed |
| `pull_request_target` | Same, but runs with the base repo's token and secrets | same fields, plus whatever the checked-out ref resolves to |
| `issue_comment` | Anyone who can comment | comment body, and on a PR thread the PR's own untrusted fields |
| `workflow_run` | Triggered by a prior run completing | the triggering workflow's name and conclusion; artefacts from that run |
| `push` (tags, branches) | Anyone with push access, or a fork's own branches for some events | branch or tag name |
| `workflow_dispatch` | Anyone with write access who fills the form | the `inputs:` values, free text unless constrained by `type` and `options` |

`references/triggers-and-injection.md` has the full table with GitLab CI equivalents, plus every known expansion sink and the safe indirection for each. Read it before step 2.

### 2. Trace each field to where it is expanded

Read every `run:` block, `github-script` step and composite action input that references `github.event.*`, `github.head_ref` or a `workflow_dispatch` input. The question is never whether the value is quoted — it is whether the value becomes **syntax** the interpreter parses rather than a value it receives.

```bash
rg -n '\$\{\{\s*github\.event\.(pull_request|issue|comment)\.' .github/workflows/*.yml
rg -n 'run:\s*\|' -A3 .github/workflows/*.yml
```

A value interpolated directly into a `run:` block is expanded by the shell before the script sees it, so a PR title containing shell metacharacters is not passed as an argument — it is spliced into the command text. The same value read from `env:` and referenced as `"$TITLE"` is a shell argument, not shell syntax, and is safe by construction regardless of its contents. That is the entire fix, and it is why quoting the interpolation does nothing: the substitution already happened before the shell ever saw a quote mark.

**Describe payload shapes in words, never as a working string.** "A PR title containing a command substitution would run during the interpolation, before the step's own commands execute" is the finding. A copy-pasteable payload is not, and this skill will not produce one — the same boundary `security-review` holds for application injection applies to a workflow's own injection surface.

### 3. List the credential live at every step that runs untrusted code

For each job, answer two questions side by side: what can this job read (`GITHUB_TOKEN` scope, repository and organisation secrets, an OIDC token it can request), and does any step in it execute code or a script the pull request author controls — application code, a test suite, a `postinstall` hook, an action from the PR's own `.github/`.

A job that answers yes to both is the finding, regardless of how the credential arrived. `pull_request_target` combined with `actions/checkout` at `github.event.pull_request.head.sha` is the canonical shape, and `actions/checkout` now gates it behind `allow-unsafe-pr-checkout`, which defaults to false — so `rg -n 'allow-unsafe-pr-checkout:\s*true' .github/workflows/*.yml` finds the place someone deliberately opted out. It is not the whole search: `git fetch` of the head ref, `gh pr checkout` and a downloaded artefact all reach the same code without that input, but the same defect exists wherever a `workflow_run` job downloads and runs an artefact a fork produced, or wherever a same-repo `pull_request` job is later given a secret to satisfy a step that did not need it.

### 4. Check every pin

```bash
rg -n '^\s*(- )?uses:\s*\S+@' .github/workflows/*.yml \
  | rg -v '@[0-9a-f]{40}'                                   # a ref that is not a 40-char SHA
rg -n 'curl .*\|\s*(bash|sh)' .github/workflows/*.yml       # fetch-and-pipe-to-shell
```

Every `uses:` needs a full commit SHA with the release tag in a trailing comment — the SHA is what makes it immutable, the comment is what lets Dependabot bump it, and a SHA with no tag comment is a pin nothing will ever update. A tool fetched with `curl` rather than referenced as an action gets the same treatment as far as the mechanism allows: downloaded at a pinned version and checked against a recorded digest before it runs. `curl ... | bash` with no pin and no checksum is a finding on its own, independent of anything else in the file — it hands build authorship to whichever host answers that URL right now.

### 5. Run zizmor and judge every finding

```bash
zizmor --persona=regular --min-severity=medium .
```

That is the exact invocation this repository's own CI runs — read `docs/ci.md` rather than guessing at flags. zizmor looks for four things: template injection into `run:` blocks, over-broad token permissions, unpinned third-party actions, and `pull_request_target` combined with a checkout of untrusted code. Treat its output the way `iac-review` treats a `tfsec` or `checkov` run: as review evidence to be judged, not a count to be minimised. For every finding, decide and record one of:

- **Reachable** — an untrusted field genuinely reaches the flagged construct. This is a real finding with the reachable path attached.
- **Not reachable** — the construct exists but nothing untrusted reaches it, and you can say why in one sentence.
- **Accepted, with a reason** — the risk is real and deliberately carried; name the reason and who owns that decision.

An unexplained pass or an unexplained suppression are both failures of this step. A zizmor run with no judgement attached to each line is a report nobody read.

### 6. Move stored keys to OIDC, and gate the trust policy

A stored cloud credential in a CI secret is a static, long-lived key that every run has read access to and that leaks the moment a log line or a compromised dependency exposes it. Where the provider supports federation, replace it: the job exchanges the workflow's own OIDC token for a short-lived role, and there is nothing left in the secret store to steal.

The trust policy is where this is done badly as often as it is skipped. Pin the whole `sub` — repository plus ref or environment — and pin `aud` to the provider's audience string. A wildcard anywhere in the `sub` match is the finding: a policy that accepts `repo:OWNER/REPO:*` trusts every branch and every pull request in that repository, and one that accepts `*` trusts every workflow able to mint a token from that issuer. Repositories created after July 2026 carry immutable identifiers in the claim (`repo:OWNER@ID/REPO@ID:...`), so a policy written against the older shape can silently match nothing. `references/credentials-and-provenance.md` has the exact condition shape per provider.

### 7. Check caches and artefacts across the fork boundary, and provenance at consumption

A cache scope that a fork's pull request can write to and the default branch later reads from is an execution path, not a convenience — poison the cache from an untrusted run and the next trusted run restores it unquestioned. The same holds for an artefact one job produces and a later job or workflow consumes without checking what produced it. Confirm untrusted runs can restore a cache but not save to a scope the default branch reads, and confirm that wherever an artefact crosses that boundary, the consumer verifies where it came from before using it — a build provenance attestation checked against the expected workflow identity, not merely present.

## Output format

```markdown
| Finding | Trigger | Untrusted field | Step | Credential live | Fix |
| --- | --- | --- | --- | --- | --- |
| [what an attacker gets] | [pull_request_target / issue_comment / ...] | [the field] | [file:line] | [token scope / secret / OIDC / none] | [the specific change] |
```

One row per finding, ranked so the row with the most credential exposure and the most directly reachable field comes first. Note explicitly where zizmor flagged something judged not reachable, so the report does not read as if that finding was missed.

## Anti-patterns

**`permissions: read-all` treated as the whole audit.** Scoping the token down is necessary and says nothing about whether an untrusted value reaches a `run:` block, whether `pull_request_target` checks out fork code, or whether a cache crosses the trust boundary. A tight `permissions:` block and an injectable title coexist constantly.

**Quoting treated as an injection defence.** `${{ }}` interpolation happens before the shell parses the line, so a quote mark added around the interpolation is already inside whatever the attacker supplied. The fix is an intermediate environment variable, not a quote.

**A pin with no tag comment.** A bare SHA is immutable but unmaintainable — Dependabot parses the trailing `# v7.0.1` to know what to bump to, and without it the pin rots in place until someone hand-resolves what it was.

**`pull_request_target` "fixed" by an `if:` on the head repository.** It works until a later edit — often one that looks unrelated — drops the condition, and nothing catches it because the workflow still runs and still passes. Prefer removing the trigger's access to the credential entirely over a conditional that has to survive every future edit.

**A signature or attestation nobody verifies.** Signing and attesting cost nothing if the consumer never runs the verification step. Provenance is a control at the point of consumption, not an artefact to have produced.

## Reference files

- `references/triggers-and-injection.md` — read in step 1 and step 2: the full per-event table of attacker-controlled fields for GitHub Actions and GitLab CI, every known expansion sink, and the safe indirection for each.
- `references/credentials-and-provenance.md` — read in step 3 and step 6: `GITHUB_TOKEN` scope reach, OIDC federation and trust-policy conditions for AWS, GCP and Azure, cache scope across the fork boundary, and artefact attestation and verification.
