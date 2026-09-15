# Artefact promotion and secret scoping

## Contents

- [Artefact identity](#artefact-identity)
- [The promotion path](#the-promotion-path)
- [Environment gates](#environment-gates)
- [Configuration, which is what makes people rebuild](#configuration-which-is-what-makes-people-rebuild)
- [Secrets per environment](#secrets-per-environment)
- [Retention, and being able to answer what shipped](#retention-and-being-able-to-answer-what-shipped)

## Artefact identity

Promotion only means anything if the thing promoted is identifiable. An artefact needs a
name that cannot refer to two different sets of bytes.

| Artefact | Identity to use | Identity to avoid |
| --- | --- | --- |
| Container image | The manifest digest | Any tag, including a version tag, which can be moved |
| Archive or binary | A checksum recorded at build time and verified before use | The file name |
| Language package | The immutable published version, where the registry forbids re-publishing | A version the registry lets you overwrite |

Tags are labels for humans and are fine for that. Every machine-readable reference in the
promotion path — the deployment manifest, the approval record, the rollback target — uses
the digest or checksum.

## The promotion path

```text
commit ─ build once ─ artefact@digest ─ gate ─ staging ─ gate ─ production
                            │
                            └─ provenance: commit, run id, inputs, builder
```

- One build node. Anything after it that produces bytes is a second build, whatever it
  is called.
- Each environment consumes `artefact@digest`. Promotion updates a pointer and records
  who moved it.
- The provenance record is what answers "what is running in production and which run
  produced it" without an assumption in the middle.
- Verify the digest at deploy time rather than trusting the pointer. A verification step
  that has never failed costs nothing; the one time it fires is the time it mattered.

## Environment gates

The difference between environments should be the gate, not the pipeline. The same jobs
run against each; what varies is what has to be true before the pointer moves.

| Gate | Typical for staging | Typical for production |
| --- | --- | --- |
| Automated checks | Smoke tests after deploy | Smoke tests plus a bake period and error-budget check |
| Human approval | None | A named reviewer group, recorded |
| Time | None | A wait between promotion and full traffic |
| Source restriction | Any branch | The default branch or a tag only |

The rollout mechanics that live behind the production gate — canary percentages, rings,
bake times, automated rollback signals — are `release-strategy`, not this skill. What the
pipeline owns is that the gate exists, that it is enforced by the platform rather than by
convention, and that it refers to the same artefact the earlier gates passed.

## Configuration, which is what makes people rebuild

Almost every rebuild-per-environment pipeline exists because something environment-specific
was compiled in. The usual culprits:

- A build-time constant for an API endpoint or a public key.
- A front-end bundle with the environment baked in at build time by the bundler.
- A base image tag that differs between environments.
- A feature set enabled by a build flag rather than by configuration.

Each has a runtime answer: read the endpoint at startup, serve the configuration to the
front end rather than compiling it in, pin one base image digest for all environments,
move the feature decision to a flag. Where a genuine build-time difference is
unavoidable, treat each variant as its own artefact with its own identity and test each
one, rather than pretending they are the same build.

## Secrets per environment

Scope follows the graph from step 7 of the skill, and environments give a second axis:

- Deployment credentials belong to the deploy job for that environment and nowhere else.
  A staging credential in a job that can also deploy production collapses the separation
  the environments existed to provide.
- Prefer federated short-lived credentials. Where the identity provider supports
  conditions, constrain the trust to the repository, the workflow and the environment, so
  a token minted by another workflow in the same repository is not accepted.
- Where long-lived credentials are unavoidable, they need rotation with a date and an
  owner, because an unrotated credential's blast radius grows silently with the
  repository's contributor list.
- Pass secrets to tools through the environment rather than as command arguments.
  Arguments are visible in process listings and in the diagnostics a tool prints when it
  cannot parse them, and shell tracing in a debug run prints them verbatim.
- Give the environment its own approval requirement where the platform supports one, so
  reading a production secret requires the same approval as deploying.

## Retention, and being able to answer what shipped

Retention windows are a design input because a rollback target that has been garbage
collected is not a rollback target.

- Keep every artefact that reached production for at least as long as you might roll back
  to it, which is longer than the default on most providers.
- Keep pull request build artefacts briefly; they are the bulk of the storage and the
  least useful.
- Record the mapping from deployment to run id somewhere outside the CI provider, because
  log retention and artefact retention expire on different schedules, and the question
  "which run built this" tends to be asked after both.
