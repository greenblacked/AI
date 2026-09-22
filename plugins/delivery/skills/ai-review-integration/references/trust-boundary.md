# Trust boundary and data policy

## Component boundary

Keep these in infrastructure controlled by the integration owner, outside the target
repository and outside jobs that execute contributor code:

- webhook authentication and replay controls;
- GitLab and model-provider credentials;
- policy, prompt templates, schemas and validators;
- deduplication, run state and audit records;
- publication logic, rollout controls and the kill switch.

Build and deploy controller code, policy and prompts from an authenticated immutable
release owned by the integration team. A SHA proves identity, not trusted provenance;
code at that SHA can still have come from a merge request author. Authenticate the event
producer and any fetched artefact producer as well as checking identifiers.

The target repository, source branch, merge request text, discussions, CI configuration,
job output, generated artefacts and dependencies are contributor-controlled. They may be
review inputs; they cannot configure the controller or confer authority. Do not import a
prompt, policy, schema or executable helper from the reviewed revision.

## Identity and secrets

Use a dedicated identity with access only to selected projects and only the API rights
needed to read merge request material and create or update its own advisory feedback.
The model receives neither the credential nor a general GitLab, shell, browser or network
tool. Separate read and write credentials when the platform and deployment support it so
shadow mode has no write capability.

Enforce a publisher allowlist even when the credential is broader: derive the GitLab
instance, project and merge request from authenticated controller state; permit only the
selected note or discussion methods and endpoints; bound body fields and size; and reject
redirects or destination changes. Model output supplies candidate finding content, never
the host, project, object, HTTP method or arbitrary request fields.

Choose the GitLab API origin from trusted deployment configuration, not webhook fields,
merge request URLs or model output. Validate pagination links as same-origin API URLs
before following them so a forged or compromised response cannot redirect a credential.

Treat forks as hostile tenants. The safe design does not depend on fork pipeline secrets:
the trusted controller fetches review inputs through its own narrowly scoped identity and
never runs source-branch code. Decline the event when project, namespace, target branch
or policy scope cannot be established from authenticated GitLab state.

GitLab documents that a fork merge request pipeline normally uses the fork's resources,
but a parent-project member can trigger a parent pipeline that still uses the fork's CI
configuration while gaining parent resources and the triggerer's permissions. GitLab
warns that malicious fork code can steal those secrets. Protected variables and runners
are unavailable to fork merge requests. See [merge request
pipelines](https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/).

## Data inventory

Before choosing a provider or enabling repositories, record:

| Data | Sent to provider | Stored by controller | Redaction | Retention owner |
| --- | --- | --- | --- | --- |
| Diff hunks | By approved path policy | Hashes or encrypted content only if required | Secrets and prohibited classes | Named role |
| File context | Minimum excerpts | Normally no | Same as source | Named role |
| MR metadata | Minimum identifiers | Run record | Personal data minimised | Named role |
| Model response | Candidate findings | Validated/redacted findings | Secret and unsafe-markup filter | Named role |

Confirm provider region, training use, retention, subprocessors and incident terms rather
than assuming an API tier has the desired policy. Define repository and path exclusions
for regulated, customer, personal, export-controlled and third-party confidential data.

Redaction is defence in depth, not permission to send prohibited data. Run secret
detection before submission and again before logging or publication. Logs retain hashes,
counts, policy decisions and correlation identifiers instead of raw source or prompts.

## Model containment

Construct the review packet in trusted code. Separate controller instructions from
untrusted fields using the provider's structured message boundary, label every source,
and cap each field. Repository instructions to ignore policy, call tools, reveal prompts,
change output format or contact a person are reviewable text, not commands.

Accept only the declared finding schema. A validator, not the model, decides whether a
finding has a real diff anchor, permissible content and sufficient evidence. Publication
renders escaped plain text or a deliberately small markup subset.

## Failure posture

- Authentication ambiguity, version mismatch, prohibited data or validator failure:
  publish nothing from the affected run.
- Partial coverage: follow the declared policy and make the limitation visible.
- Provider outage or budget exhaustion: retry within bounds, then record an unavailable
  advisory result; never block merging unless a separate human-owned policy says so.
- Kill switch: stop new work, revoke write capability, cancel queued publication and
  reconcile any request whose result is unknown.
