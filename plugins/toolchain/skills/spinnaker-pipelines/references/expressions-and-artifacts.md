# Expressions and artifacts

Read this when an artifact does not resolve, a manifest deploys with a literal `${...}`
in it, or a stage reads a value from another stage. Names and behaviour here are the
usual shape; confirm them in the official docs for the pinned Spinnaker release, since the
expression helpers, artifact types and the evaluate-variables stage have changed
across releases.

## Expected artifacts

An expected artifact has a match and a fallback policy.

| Field | What it does | Why it matters |
| --- | --- | --- |
| `matchArtifact` | Type, name and any type-specific fields (a Docker image name, a Git file path and branch, a GCS or S3 object path) | Narrow enough that two artifacts cannot both match; a regex on the name is the usual cause of the wrong one winning |
| `useDefaultArtifact` with `defaultArtifact` | Fall back to a fixed artifact when nothing matches | Hides a broken trigger; use for manual runs |
| `usePriorArtifact` | Take the artifact from the last execution of the pipeline | Right for a rollback pipeline, wrong for a forward deploy |
| `displayName` | Label in the UI | Not an identity; two artifacts can share one |

How an expected artifact gets a value, in practice: from the trigger (a Docker registry
trigger, a Git trigger, a Jenkins build's artifacts, a webhook's `artifacts` field), from
an earlier stage's output (a bake produces a rendered manifest artifact), from the
default, or from a prior execution. A stage that needs it lists it as an input artifact
or binds it by id. If the id changes after an edit (re-creating the artifact in the UI
mints a new one), every stage that referenced the old id now references nothing; diff
the pipeline JSON after editing artifacts.

Image references in a manifest are replaced by the bound image artifact only when the
stage is configured to bind artifacts and the manifest's image name matches the artifact
name. A deployed `:latest` after a successful run often means the binding never matched,
not that the deploy ignored it. Read the deployed manifest in the execution details.

## Triggers

- Docker registry trigger: set the registry, repository and a tag regex. Check the
  registry polling interval and that the account can list the repository. A tag
  that already exists and is pushed again may not fire.
- Git trigger: a webhook from the host to Echo; the branch and path filters decide what
  fires. Missing deliveries are a webhook or ingress problem before they are a pipeline
  problem; check the source host's delivery log.
- Pipeline trigger: starts on another pipeline's completion with a status filter; the
  parent's artifacts flow through only if declared.
- Cron trigger: evaluated in a time zone set by the installation; check which, and
  expect daylight-saving shifts to move a run.
- Webhook, pubsub and Jenkins triggers: the payload is attacker-influenced data when the
  sender is not fully trusted. Do not interpolate payload strings into a manifest or
  a command without constraining them.

Automatic triggers run with the pipeline's run-as user or service account, if one is set.
A pipeline that works when run manually and fails when triggered is usually a missing
service account permission on the account, application or role.

## Reading values with SpEL

- Pipeline parameters: `${parameters.name}`. Trigger fields: `${trigger.tag}` for
  a Docker trigger, `${trigger.buildNumber}` for a Jenkins one; the available fields
  depend on the trigger type, so print `${trigger}` in an Evaluate Variables stage once
  to see them.
- Another stage's output: `${#stage('Bake manifest')['outputs']['artifacts']}`. The
  lookup is by the stage's name, not its reference id; renaming the stage breaks it, and
  a name that matches no stage fails the lookup. A stage that has not run yet has no
  outputs, so a value read from a stage on a branch that was skipped is empty.
- Manual Judgment result: `${#judgment('Approve')}`, and the chosen option from
  judgment inputs. Check the helper name for the pinned release.
- Helpers such as `#toJson`, `#readJson`, `#toInt` and `#fromUrl` exist for conversion
  and fetching; confirm each one's exact name, and treat `#fromUrl` as a network call that
  runs with the orchestrator's reach.
- Conditional stages: a stage's conditional-execution expression is evaluated true or
  false; a failed evaluation is not the same as false. Test both branches.

## Traps

- A failed expression usually leaves the original `${...}` text in place and records an
  error in the context, and the stage may succeed. Read the evaluated stage context
  after every change. If the release offers an option to fail the stage on an expression
  error, turn it on for deploy stages.
- Values are evaluated when the stage starts, not when the pipeline starts. A value that
  depends on a stage that finishes later is empty.
- Quoting: inside a SpEL string use single quotes; a `$` in a shell command or a Helm
  template that is not meant for Spinnaker must be escaped or kept out of the
  stage fields that are evaluated, or it is parsed as an expression. Check the docs for the
  escape form.
- A manifest field that must be a number or a boolean receives a string if the
  expression returns one; convert explicitly.
- Lists and maps from `#stage()` are copies of the stage context at evaluation time and
  can be large; do not paste a whole context into an annotation or label.
- Do not put secrets in expressions, pipeline parameters or bake overrides. They are
  stored with the execution and visible to anyone who can view it.
