# Configuration, secrets and reproducibility

Read this at step 6 when a variable is not the value you expected, at step 7 when deciding between a profile and an override file, and at step 8 when pinning what the file resolves to.

## Contents

- [The two things called .env](#the-two-things-called-env)
- [Precedence, worked through a conflict](#precedence-worked-through-a-conflict)
- [Printing the answer instead of reasoning about it](#printing-the-answer-instead-of-reasoning-about-it)
- [Secrets](#secrets)
- [Override files and how they merge](#override-files-and-how-they-merge)
- [Profiles: what activates what](#profiles-what-activates-what)
- [Digest pinning as a committed artefact](#digest-pinning-as-a-committed-artefact)
- [What does not belong in the file](#what-does-not-belong-in-the-file)

## The two things called .env

These are separate mechanisms that happen to share a filename, and confusing them accounts for most of the time people lose here.

**Interpolation.** The `.env` file beside the Compose file supplies values for `${VAR}` references *in the Compose file itself* — an image tag, a port number, a uid. It is read by Compose, not by the container. Selected with `--env-file`, and the file must be present unless the entry is marked optional.

**Container environment.** Files listed under a service's `env_file`, and the `environment` mapping, set variables *inside the container*. They are not available for interpolation in the Compose file.

A value needed in both places has to be stated in both places. The commonest form is an image tag used in `image:` and also passed to the application:

```yaml
services:
  api:
    image: "example/api:${API_TAG}"
    environment:
      API_TAG: "${API_TAG}"
```

Two `.env` files can be read when `--env-file` is not set. Compose loads one from the project directory, and if that file sets `COMPOSE_FILE` to a path in a different directory, it loads a second `.env` from that directory at lower precedence.

Relative paths in `env_file` resolve from the Compose file's parent directory. An absolute path makes the file non-portable, and Compose warns about it. `required: false` on an `env_file` entry lets a missing file be ignored silently, which is how a developer-local overlay stays optional:

```yaml
    env_file:
      - path: ./defaults.env
      - path: ./local.env
        required: false
```

Later files in the list win over earlier ones, which is why the optional local overlay goes last.

## Precedence, worked through a conflict

Highest to lowest, as Compose documents it:

| Rank | Source |
| --- | --- |
| 1 | `docker compose run -e VAR=...` on the command line |
| 2 | `environment` or `env_file` whose value is interpolated from the shell or from an environment file |
| 3 | The `environment` attribute in the Compose file |
| 4 | The `env_file` attribute in the Compose file |
| 5 | `ENV` in the image |

The `environment` attribute beats `env_file` even when its value is empty or undefined, which is the rule that surprises people: an `environment` entry written as a bare key with no value does not fall through to the env file, it unsets the variable.

Worked example. `webapp.env` contains `NODE_ENV=test`, the service lists it under `env_file` and also sets `NODE_ENV=production` under `environment`. The container sees `production`, because rank 3 beats rank 4. Add `API_TAG` to the shell and write `environment: {API_TAG: "${API_TAG}"}` and the shell value wins at rank 2 over anything in an env file.

`ARG` and `ENV` in the Dockerfile only take effect when there is no Compose entry for that variable at all.

## Printing the answer instead of reasoning about it

```bash
set -Eeuo pipefail

# The fully resolved model: interpolation done, files merged, short forms expanded.
docker compose config

# The variables Compose used for interpolation. A different set from what the
# container sees, and the distinction is the whole of the section above.
docker compose config --environment

# Every variable the model references, with its default. Useful for writing
# .env.example without missing one.
docker compose config --variables

# What one service will actually see. Choose a service with no secrets.
docker compose run --rm --no-deps web env | sort
```

`--no-deps` matters on that last one: without it the command starts the whole dependency graph to answer a question about a variable.

## Secrets

The committed Compose file and a committed `.env` are both in the repository history forever, so the rule is that neither ever holds a credential that works against anything real.

- Commit `.env.example` with every key present and no real value. Gitignore `.env`. Do this on the first commit, before there is anything worth protecting, because retrofitting it means the value is already in the history.
- Make the development credentials in the Compose file obviously fake, so nobody has to check whether they are live and nobody is tempted to point the file at staging "just for a minute".
- Use the top-level `secrets` element for anything genuinely sensitive. A secret sourced from `file:` or `environment:` is mounted into the container at `/run/secrets/<name>` rather than placed in the process environment, which `docker inspect` prints and which crash reporters and child processes inherit.

```yaml
services:
  api:
    image: example/api
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    environment: DB_PASSWORD
```

The `environment:` source reads the value from the shell at up time, so nothing is written to a file in the working tree. The `file:` source reads it from a path, which is fine for a developer-local file and not for one that is committed. `external: true` refers to a secret already registered with the engine.

Never put a credential in `command:` or in a healthcheck `test:`. Both are printed by `docker ps` and by `docker compose config`, so the value is readable by anything on the machine and lands in CI logs whenever somebody debugs the file.

## Override files and how they merge

Compose reads `compose.yaml` and, if present, `compose.override.yaml` automatically. `compose.yaml` is the preferred name; `docker-compose.yml` is supported for backward compatibility. More files, or differently named ones, come from `-f` in order, or from `COMPOSE_FILE`.

The merge rules are specified, and knowing them prevents the two common surprises:

| Shape | Merge behaviour |
| --- | --- |
| Mapping | Missing keys added, conflicting keys taken from the later file |
| Sequence | Appended, not replaced |
| `command`, `entrypoint`, `healthcheck.test` | Replaced by the later file, despite being sequences |
| `ports`, `volumes`, `secrets`, `configs` | Merged on a unique key — `target` for volumes, secrets and configs, and the ip/target/published/protocol tuple for ports — so entries sharing that key merge rather than accumulate |

The appended-sequence rule is what makes an override file unable to *remove* something by restating a shorter list. That is what `!reset` is for, and `!override` replaces a sequence instead of appending to it:

```yaml
services:
  api:
    ports: !reset []
    environment:
      DEBUG: !reset null
```

Relative paths resolve from the first Compose file's parent directory, which matters when an override lives in another folder.

Use override files, not profiles, to express a different configuration of the same services: a dev overlay that adds bind mounts and published ports on top of a base that has neither.

## Profiles: what activates what

- A service with no `profiles` key always starts.
- A service with one starts only when that profile is enabled, by `--profile` or by `COMPOSE_PROFILES`.
- Naming a service directly on the command line starts it regardless of its profile, along with anything in its `depends_on`.
- `--profile "*"` enables all of them.
- `docker compose --profile debug down` stops services in `debug` *and* services with no profile. Plain `down` stops only the unprofiled ones, which is why a profiled service can appear to survive a teardown.

The rule that catches people: a dependency that is itself behind a *different* profile is not activated for you. It must be in the same profile, be unprofiled, or be started separately.

```yaml
services:
  api:
    image: example/api
  mailhog:
    image: example/mailhog
    profiles: ["dev-tools"]
  seed:
    image: example/api
    command: ["./manage", "seed"]
    profiles: ["seed"]
    depends_on:
      db:
        condition: service_healthy
```

`db` above is deliberately unprofiled, so `docker compose run --rm seed` works without anyone having to know which profile to enable first.

Profiles answer "should this service run at all". They do not answer "what should this service's configuration be" — that is an override file.

## Digest pinning as a committed artefact

`image: postgres:16` is mutable. Compose does not re-pull a tag it already has locally, so two developers who first ran `up` a month apart are running different bytes with no way to notice, and CI — which pulls fresh — is running a third thing.

Pin by digest and keep the tag for readability: `postgres:16@sha256:...`. Generate the digests rather than transcribing them:

```bash
set -Eeuo pipefail

# The resolved model with every tag replaced by its digest, for inspection.
docker compose config --resolve-image-digests

# An override file containing the digests, to commit beside compose.yaml and
# regenerate deliberately when bumping.
docker compose config --lock-image-digests --output compose.lock.yaml
```

Committing the lock file as a separate artefact keeps the main file readable and makes a version bump a visible diff with a date attached, rather than a silent drift. Regenerating it is a deliberate act — the same shape as a dependency lockfile, and for the same reason.

`pull_policy` controls when Compose fetches: `always` re-pulls on every up, `missing` is the default, `never` fails rather than reaching the network. Digest pinning makes `always` nearly free, since the digest either matches what is local or it does not.

Reproducibility of images you *build* — build arguments, cache mounts, multi-stage layout, provenance and SBOMs — belongs to `image-hardening`. This file's job ends at pinning the reference.

## What does not belong in the file

`deploy:` describes a Swarm deployment. Compose honours a small part of it — some resource fields — and ignores the rest, so replica counts, placement constraints and rolling-update parameters in a dev Compose file describe an environment nobody runs and nothing validates. They are not a draft of a Kubernetes manifest either; the fields do not correspond, and the reasoning that produces a resource request, a probe or a PodDisruptionBudget is `k8s-workloads`, measured against a cluster rather than transcribed from here.

There is a second reason, independent of which fields are honoured. The same Compose file does not carry the same startup semantics under every runner. `depends_on` and its conditions are Compose concepts, applied by `docker compose up`; what any other tool does with the same file when it consumes it is that tool's business, and the conditions are the first thing to be dropped. So a graph that comes up correctly here is not evidence that the ordering holds anywhere else. Startup correctness in a real deployment has to be enforced by the runtime that actually runs it, or by the application tolerating a dependency that is not there yet.

The test for whether something belongs: does its value depend on knowing what production looks like? Replica counts, memory ceilings derived from production load, real hostnames and real credentials all do, and none of them belong. Which services exist, what each needs in order to be ready, what can reach what, and what persists across a restart do not, and all of them do.
