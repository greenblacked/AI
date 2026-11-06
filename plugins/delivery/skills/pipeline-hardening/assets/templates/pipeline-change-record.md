# Pipeline change record

One change to one workflow. Fill in every field from the workflow file and the audit before
writing the verdict; delete the guidance in brackets.

## Change

- Workflow file and pull request: [path, number]
- What changes and why: [one or two sentences]
- Reviewer who traced the fields: [name]

## Triggers

| Trigger | Who can fire it | Untrusted fields it carries |
| --- | --- | --- |
| [pull_request / pull_request_target / workflow_run / issue_comment / ...] | [anyone / write access / ...] | [title, branch, body, ...] |

## Jobs

| Job | Token scope | Secrets and OIDC reach | Runs code the pull request controls |
| --- | --- | --- | --- |
| [job id] | [permissions as granted] | [secrets read, id-token yes or no] | [yes or no, and which step] |

## Findings

One row per finding, the most credential exposure and the most directly reachable field first.

| Finding | Trigger | Untrusted field | Step | Credential live | Fix |
| --- | --- | --- | --- | --- | --- |
| [what an attacker gets] | [trigger] | [the field] | [file:line] | [token scope / secret / OIDC / none] | [the specific change] |

## Untrusted fields and their env variables

| Field | Step that expands it | `env:` variable carrying it |
| --- | --- | --- |
| [github.event... field] | [file:line] | [NAME, read as "$NAME"] |

## Pins

- Actions pinned to a full SHA with the release tag in a comment: [all / list the exceptions]
- Tools fetched in a step, with the pinned version and recorded digest: [list, or none]

## zizmor

Command run: [exact invocation]. Judge each finding.

| Finding | Judgement | Reason |
| --- | --- | --- |
| [rule and location] | [reachable / not reachable / accepted] | [one sentence, and the owner if accepted] |

## Live-run evidence

[A `pull_request_target` or `workflow_run` change needs a real run before merge: the run
URL, the trigger used, and what the job could and could not read. Write "not applicable" for
a change that touches neither.]

## Verdict

[Safe to merge / merge after the listed fixes / do not merge], and who owns anything accepted.
