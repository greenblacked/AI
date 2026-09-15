---
name: docker-compose
description: "Compose several containers into one working environment for local development and CI: gate every depends_on edge on a healthcheck condition, since service_started means started, not ready; design the check and its start_period; service discovery by name, container port versus published port; named volumes versus bind mounts and their permission traps; layering .env, environment and env_file; profiles for optional services; digest pinning against drift. Use whenever someone says \"my app starts before the database is ready\", \"containers cannot reach each other\", \"works on my machine but not in CI\", \"how do I keep secrets out of my compose file\", or \"why is node_modules empty in the container\". Not for the image itself (image-hardening), a Kubernetes workload's requests, limits or probes (k8s-workloads), pipeline structure (ci-pipeline-design), or generating YAML (code-scaffold)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(docker:*), Bash(jq:*)
---

# Compose Environments

A Compose environment is right when a developer who has never seen the repository can clone it, run one command against an empty Docker, and get a working system on the first attempt — and the same file, unchanged, brings the same system up inside CI.

The job is hard because almost every defect here is a race that usually wins. `depends_on` orders startup, so on a warm machine where the database container starts in 300ms the application connects and everybody concludes the file is correct. The same file on a cold CI runner pulling images, or on a laptop after `docker compose down -v`, gives the database eight seconds to initialise and the application exits before it ever gets a connection. The report that comes back is never "there is a readiness race"; it is "works on the second run", "works on my machine but not in CI", or "flaky integration tests". The rest of the failure modes have the same shape. A bind mount that behaves one way on a developer's Docker Desktop and another way on a Linux runner. A `ports:` entry that makes a service reachable from the host and changes nothing at all about whether two containers can reach each other. A named volume that outlives every attempt to fix what is inside it, because `down` does not remove it. None of these produce an error message that names its own cause.

## Scope

Use for: composing several containers into one working environment for local development or for CI; dependency and readiness ordering; healthcheck design; networks and what is reachable from where; volume and bind-mount choices; layering `.env`, `environment` and `env_file`; profiles for optional services; pinning so a shared file does not drift between developers; and deciding what belongs in the Compose file at all.

Do not use for:

- The image itself — base image choice, multi-stage builds, shrinking, non-root UIDs, scanning, SBOMs, signing, the CIS benchmark. That is `image-hardening`. This skill treats an image as an opaque reference it pins and runs; it never writes or audits a Dockerfile.
- A Kubernetes workload's contract — requests and limits, QoS, liveness and readiness probes, PodDisruptionBudgets, rollout strategy. That is `k8s-workloads`. A Compose healthcheck and a Kubernetes probe answer superficially similar questions with different consequences, and Compose is not a rehearsal for a cluster.
- The structure of a CI pipeline — which checks block a merge, the stage graph, cache keys, matrix strategy, promoting one artefact. That is `ci-pipeline-design`. Compose used *as* a job's service dependency is in scope here; where that job sits in the graph is not.
- Generating a project, a chart, a service skeleton or a YAML file from a description. That is `code-scaffold`. The work here is topology and readiness semantics — which service may start when, what can reach what, what survives a restart. That reasoning is what remains true after the YAML is regenerated.

Testcontainers is the honest alternative for one of these jobs and not the other. When the containers exist only to serve a test suite, are owned by that suite, and should be created and destroyed inside it — per test class, with the port allocated dynamically so parallel runs cannot collide — Testcontainers is the better tool and this skill should say so rather than reproduce it in YAML. Compose is right when the same environment is the thing developers run all day *and* the thing CI brings up, because then one file is the shared definition and the alternative is two definitions that drift.

Two spelling notes that date a file immediately. The top-level `version` key is obsolete: the Compose Specification keeps it only for backward compatibility, Compose warns when it is present, and it does not select a schema — Compose prefers the most recent schema it implements regardless of what the key says. Delete it. And the command is `docker compose`, the Go plugin; the hyphenated `docker-compose` is the Python v1 implementation, which is deprecated and no longer maintained. A file opening with `version: "3.8"` and instructions that say `docker-compose up` are a reliable signal that the rest of the example predates `service_healthy` too.

## Workflow

### 1. Make every dependency edge a readiness condition before tuning anything else

This is the gate. Do not adjust a healthcheck interval, add a retry loop to the application, or debug a connection error until every edge in the file has an explicit condition and every target of a `service_healthy` edge has a healthcheck. The race this closes is the direct cause of most of the symptoms people arrive with, and every later step assumes it is shut.

Docker's own documentation states the limit in one sentence: "On startup, Compose does not wait until a container is 'ready', only until it's running." That is what the short list form and `condition: service_started` both mean. Running is not listening, is not finished initialising, is not migrated. There is no implicit readiness probe anywhere in Compose — `service_healthy` is satisfied by a `healthcheck` the dependency defines and by nothing else, so an edge pointing at a service with no healthcheck is a configuration error rather than a weaker guarantee.

Enumerate the edges from the resolved model rather than by reading the file, because `docker compose config` expands short notation into canonical form and shows you what Compose actually believes:

```bash
set -Eeuo pipefail

# Every dependency edge, with the condition Compose resolved it to. Anything
# printing service_started is an ordering hint, not a readiness guarantee.
docker compose config --format json \
  | jq -r '.services | to_entries[] as $s
      | ($s.value.depends_on // {}) | to_entries[]
      | "\($s.key) -> \(.key): \(.value.condition)"'

# Services that cannot satisfy a service_healthy edge, because they have no
# healthcheck or the image's healthcheck is disabled.
docker compose config --format json \
  | jq -r '.services | to_entries[]
      | select(.value.healthcheck == null or .value.healthcheck.disable == true)
      | "no healthcheck: \(.key)"'
```

Then give each edge the condition that matches what the dependent actually needs:

| Condition | What it proves | Use it when |
| --- | --- | --- |
| `service_started` | The container was created and started | The dependent tolerates the dependency being absent for a while — a sidecar, a log shipper, a cache the code treats as optional |
| `service_healthy` | The dependency's healthcheck has passed | The dependent will fail or misbehave if the dependency is not serving. This is the default answer for a database, a broker or an internal API |
| `service_completed_successfully` | The dependency ran to completion with exit code zero | A one-shot: a migration, a fixture loader, a bucket-creation step. This is the condition people do not know exists, and it is what removes `sleep 10` from entrypoints |

Two options on the long form are worth knowing, both with version floors worth stating because a file using them silently does nothing on an older Compose. `restart: true` (Compose v2.17.0 and later) restarts the dependent after Compose updates or restarts the dependency; without it, restarting the database leaves the application holding a pool of dead connections and the symptom is errors that outlive the restart that caused them. `required: false` (v2.20.0 and later, default `true`) downgrades a missing dependency to a warning, which is the honest way to depend on a service that lives behind a profile.

`references/readiness.md` has the condition semantics in full, healthcheck commands for each common dependency class with the caveat that applies to each, and the one-shot migration pattern. Read it at steps 1 to 3.

### 2. Write the healthcheck against what the dependent needs, not what the process is doing

A healthcheck that a dependency can pass before it is usable is worse than no healthcheck, because it converts a visible race into an invisible one that now has a green tick next to it.

The concrete trap is Postgres. The official image's entrypoint starts a temporary server with `listen_addresses` empty — reachable only over the Unix socket — runs everything in the init directory against it, stops it, and only then starts the real server. A healthcheck of `pg_isready -U postgres` connects over that same Unix socket, so it can report ready during the init window, before the port the application uses is listening at all. The fix is to make the check traverse the path the dependent will use: TCP, with credentials, running a trivial query.

Three questions decide the check:

1. **Does it use the same transport as the dependent?** A check over a Unix socket says nothing about a TCP listener. A check on `localhost` inside the container says nothing about the bridge network.
2. **Does it prove the work is done, or that the process is alive?** A broker accepting connections before its topics exist, a database serving before migrations run, a web service answering `/` from a static handler while its connection pool is still empty — all pass a naive check.
3. **Is the check cheap?** It runs forever, on an interval, on every developer's laptop. A check that opens a new connection and runs a real query is fine; one that runs a full table scan competes with the startup it is measuring.

Prefer a check that needs no extra tooling in the image. If the image has no client binary, the honest options are a small dependent service whose entrypoint waits, or `service_started` plus retry in the application — not a check that always passes.

### 3. Derive the interval, retries and start period from the service, not from an example

The defaults are inherited from the `HEALTHCHECK` instruction: `interval` 30s, `timeout` 30s, `start_period` 0s, `start_interval` 5s, `retries` 3. There is no correct number to copy; there is an arithmetic that produces one.

**Set `start_period`, and the reason is latency as much as correctness.** It defaults to zero, meaning there is no start period at all, and that single default is a standing tax on every bring-up. `start_interval` is a separate and much shorter poll period that applies *only during the start period* — but with no start period declared, it never applies, so checks run at `interval`. A database that is genuinely serving two seconds after start is therefore first *checked* at thirty seconds, and every service gated on `service_healthy` behind it sits idle for the difference. Nothing is broken and nothing logs anything; the environment is simply slow to come up, on every developer's machine and in every CI job, and it presents as a Compose problem rather than as a field nobody set. Declaring `start_period: 30s` with `start_interval: 1s` turns that thirty seconds into roughly two.

`start_period` is a grace window rather than a delay, and two behaviours make a generous one nearly free. Failures inside it are not counted toward the maximum number of retries. And a check that succeeds during it ends it — the container is considered started, and consecutive failures from then on do count. So size it for the worst honest cold start — an empty volume, an image pulled fresh, the slowest machine anyone runs this on — and a fast machine will leave it after one check. Measure it once by timing a cold bring-up rather than guessing.

`start_interval` needs Docker Engine 25.0 or later and Compose v2.20.2 or later. On anything older the field is ignored, the start period polls at `interval`, and the only lever left is `interval` itself — which is the case where a short interval is the right answer despite everything below.

`interval` and `retries` govern steady state, and the product is what matters: a genuine failure is detected in roughly `retries * interval` after it begins, with `timeout` added per hung check. Pick the detection time you want and factor it.

The failure people describe as a restart loop starts here, and the mechanism is worth being precise about. Docker's own restart policies act on container *exit*, not on health, so an unhealthy container is not restarted by Docker. What a short `interval` with `start_period` at its default of zero actually does is exhaust `retries` while the service is still starting: the dependency is marked unhealthy, every `service_healthy` dependent is never created at all, and `docker compose up --wait` eventually times out. The loop appears one layer up, wherever something *does* act on health — an autoheal sidecar, or the same image later run under an orchestrator — which recycles the container before it has ever finished starting, so each restart begins the slow start again from cold. In Compose the visible symptom is a bring-up that hangs and then fails, on CI, having worked locally.

```bash
set -Eeuo pipefail

# Time a genuine cold start: this is the number start_period has to cover.
docker compose down -v --remove-orphans
time docker compose up --wait --wait-timeout 180

# What the check has actually been doing, including its output on failure.
docker inspect --format '{{json .State.Health}}' "$(docker compose ps -q db)" | jq .
```

### 4. Decide reachability deliberately: by name between services, by port from the host

Compose puts every service on one network named after the project and registers each service name in an internal DNS server, so containers reach each other by service name with no configuration. Two consequences are where the confusion lives.

Between services, the address is the *container* port. `ports: "8001:5432"` publishes the database to the host on 8001 and changes nothing for the application container, which still connects to `db:5432`. A `DATABASE_URL` of `postgres://db:8001/app` is a bug that reads as a typo for something correct.

From the host, only what is in `ports:` is reachable, and `localhost` inside a container means that container. Reaching back to the host needs `host.docker.internal`, which on Linux requires an explicit `extra_hosts` entry mapping it to `host-gateway`.

Publish nothing you do not need from the host. Every published port is a service exposed on the developer's machine and, on a shared CI runner, a collision with the job running next to it. Put databases on their own network with `internal: true` when nothing outside needs them.

`network_mode: host` is the sharp edge: it removes port mapping *and* service-name DNS, so a file that worked switches to a mode where half of it silently does not apply.

`references/networking-and-volumes.md` covers multi-network topologies, the container-runner case in CI, cross-project networks, and the whole volume section below. Read it at steps 4 and 5.

### 5. Choose named volume or bind mount by what the data is, and expect the bind mount to behave differently per host

The rule is short. Data the container owns and the host should not read — database files, search indexes, uploaded blobs — is a named volume. Source you are editing and want reflected inside the container immediately is a bind mount. Anything else is usually neither.

Three behaviours cause most of the reported trouble:

**Short-syntax bind mounts create the host path.** The specification is explicit: if the source path does not exist, it is created, for backward compatibility. Created by the daemon, so on Linux it is owned by root, and the symptom is a directory that is empty and that the container cannot write to. A typo in a source path produces a new empty directory rather than an error. The long syntax with `create_host_path: false` turns that into the failure it should have been.

**Bind mount ownership is a host property.** On Linux the host's numeric uid and gid pass straight through, so a container running as uid 1000 cannot write to a directory owned by uid 1001, and running as root leaves root-owned files in the developer's working tree. Docker Desktop's file-sharing layer papers over this. That is exactly the asymmetry behind "works on my machine but not in CI": the laptop is macOS or Windows, the runner is Linux, and the Compose file is identical.

**A named volume seeds from the image only when it is first created.** After that it is authoritative. Change the Dockerfile, rebuild, and the old contents are still there — and `docker compose down` does not remove named volumes. Only `down -v` does. This is both why a dev database survives a restart and why five attempts to fix a corrupt one all fail.

The `node_modules` case is the canonical instance. Bind-mounting the project directory replaces the image's installed modules with the host's, which are either absent — so the directory reads as empty inside the container — or built against the host's platform and architecture, so anything with a native addon breaks in a way that has nothing to do with the code. Masking the path with a separate volume works and goes stale the moment the lockfile changes. `develop.watch` with a `sync` action that ignores the module directory and a `rebuild` action on the lockfile is the better shape, because it makes the dependency change an image rebuild rather than a mount.

### 6. Separate the two things called environment, and keep real secrets out of the committed file

`.env` and `env_file` are different mechanisms that share a word, and conflating them is the most common configuration bug here. The `.env` file beside the Compose file supplies values for `${VAR}` *interpolation in the Compose file itself*. Files named under `env_file` set variables *inside the container* and are not interpolated into the Compose file at all. A variable that needs to do both has to appear in both places.

Precedence, highest to lowest, as Compose documents it: `docker compose run -e` on the command line; a value interpolated from the shell or an environment file into `environment` or `env_file`; the `environment` attribute; the `env_file` attribute; and last, `ENV` in the image. Within `env_file`, a later file in the list wins over an earlier one. Stop reasoning about it and print it when a value is not what you expect:

```bash
set -Eeuo pipefail

# The resolved model, after interpolation and file merging.
docker compose config

# What Compose used for interpolation, which is a different set of variables
# from what ends up inside the container.
docker compose config --environment

# What one service will actually see. Use a service with no secrets in it.
docker compose run --rm --no-deps web env | sort
```

For secrets: commit a `.env.example` with every key and no real value, gitignore `.env`, and make the dev credentials in the Compose file obviously fake so nobody mistakes the file for one that could point at something real. Where a value genuinely is sensitive, use the top-level `secrets` element with a `file:` or `environment:` source so it arrives in the container as a file under `/run/secrets` rather than in the process environment, which `docker inspect` prints to anyone on the machine. Never put a credential in a `command:` or a healthcheck `test:`, both of which are visible in `docker ps` output and in the resolved config.

### 7. Use profiles for services that are optional, not for services that belong to another environment

A service with no `profiles` key always starts. A service with one starts only when that profile is enabled by `--profile` or `COMPOSE_PROFILES`, or when it is named directly on the command line — in which case Compose starts it and its `depends_on` dependencies regardless of the profile. `--profile "*"` enables everything.

The trap is documented and still catches people: a dependency that is itself behind a *different* profile is not pulled in. It has to be in the same profile, unprofiled, or started separately.

Profiles are right for a debugging UI, an observability stack, a seed job, the one heavy service most contributors never need. They are the wrong tool for modelling dev versus staging versus production, because a profile does not change a service's configuration — it only decides whether it runs. Layered files with `-f` are what change configuration.

### 8. Pin what the file resolves to, or it is not the same environment twice

`image: postgres:16` is a moving reference. Two developers who ran `docker compose up` a month apart are running different bytes, and neither has any way to notice, because Compose does not re-pull a tag it already has locally. The same divergence between a laptop and a CI runner is a whole category of "works on my machine".

Pin by digest. Keep the readable tag for humans and let the digest carry the identity — `postgres:16@sha256:...` — and generate it rather than transcribing it:

```bash
set -Eeuo pipefail

# The resolved model with every tag replaced by its digest.
docker compose config --resolve-image-digests

# An override file containing only the digests, to commit beside the main file.
docker compose --file compose.yaml config --lock-image-digests
```

Reproducibility of images you *build* — build arguments, layer caching, multi-stage, provenance — is `image-hardening`'s ground, not this skill's.

### 9. Keep deployment configuration out of the file

`deploy:` describes a Swarm deployment. Compose honours a small part of it and ignores the rest, so a dev Compose file carrying replica counts, placement constraints and rolling-update parameters describes an environment that nobody runs and that nothing validates. It is not a Kubernetes manifest in waiting either: the fields do not correspond, and the reasoning that sets a Kubernetes request or a PodDisruptionBudget is `k8s-workloads`, done against the cluster and not against this file.

What belongs here is the topology — which services exist, what each needs to be ready, what can reach what, what persists. What does not belong is anything whose value depends on a production environment: real credentials, replica counts, resource ceilings derived from production load, hostnames of real systems.

The deeper reason not to treat this file as a deployment artefact is that the same Compose file does not carry the same startup semantics under every runner. `depends_on` is a Compose concept, honoured by `docker compose up` on one machine; what another tool does with the same file when it consumes it is that tool's business, and the conditions are the first thing to be dropped. So a correctly ordered graph here is not evidence that the ordering survives anywhere else. Anything whose correctness depends on start order in a real deployment needs that order enforced by the runtime that actually runs it, or by the application tolerating the dependency being absent.

### 10. Rehearse the cold start, because it is the only run that resembles CI

Everything above is verified by one command, and it is not the one people run:

```bash
set -Eeuo pipefail

# The state a new developer and every CI job start from. Nothing that "works on
# the second run" survives this.
docker compose down --volumes --remove-orphans
docker compose up --wait --wait-timeout 300

# The CI shape: a unique project name so concurrent jobs on a shared runner do
# not collide on network and volume names, and a non-zero exit when the graph
# never becomes healthy.
docker compose --project-name "ci-${BUILD_ID}" up --wait --wait-timeout 300
docker compose --project-name "ci-${BUILD_ID}" run --rm tests
docker compose --project-name "ci-${BUILD_ID}" down --volumes --remove-orphans
```

`--wait` is what turns a readiness bug into a failed command instead of a failed test suite: it waits for every service to be running or healthy and exits non-zero on timeout. A CI job that runs `up -d` and then immediately runs tests has reintroduced the step 1 race at the top level.

`references/config-and-reproducibility.md` has the full precedence table with a worked example, override-file merge semantics, the secrets patterns, and the digest workflow. Read it at steps 6 to 8.

## Reference files

- `references/readiness.md` — the three `depends_on` conditions with what each proves, healthcheck commands for Postgres, MySQL, Redis, an HTTP service, a broker and an image with no client binary, each with its caveat; the start-period and retry arithmetic worked through; the one-shot migration pattern; and how to read health state back. Read it at steps 1 to 3.
- `references/networking-and-volumes.md` — the default network and its naming, multi-network topologies with `internal`, reaching the host and being reached from it, the CI case where the job itself is a container, cross-project networks; then the volume decision table, bind-mount ownership per host platform, the `node_modules` variants with their trade-offs, and volume lifecycle. Read it at steps 4 and 5.
- `references/config-and-reproducibility.md` — the two meanings of `.env`, the precedence order worked through a concrete conflict, override files and how `-f` merges lists against maps, profile activation rules, secrets, and digest pinning as a committed artefact. Read it at steps 6 to 8.

## Anti-patterns

**A `sleep` in an entrypoint, or a retry loop added to the application, to fix a startup race.** Both work often enough to survive review and neither closes the race; the sleep is tuned to one machine and the retry loop hides the condition it is compensating for. A retry loop is good engineering for a dependency that can fail at any time in production. It is not a substitute for a readiness edge, and adding it first means the file's dependency graph is never corrected.

**`depends_on` with no condition against a database.** The most common defect in this file, and the reason "works on the second run" is a recognised phrase. It is invisible on any machine with a warm image cache and an existing volume, which is every machine where anybody tests the change.

**Leaving `start_period` at its default because nothing is failing.** Nothing is. The environment simply takes an extra `interval` to come up than it needs to, every time, for every developer and every CI job, and because no error is produced the cost is never attributed to the field that caused it. This is the cheapest minute per day anyone will find in a Compose file.

**A healthcheck copied from a blog post, interval and all.** The interval and retries encode somebody else's detection requirement and the start period encodes their hardware. `pg_isready` copied without the TCP and query arguments is the specific case that passes during the init window and certifies a database that is not yet accepting connections.

**Publishing every service to the host so it is easy to poke at.** It exposes the whole environment on the developer's machine, guarantees port collisions between concurrent CI jobs, and teaches everybody to address services by `localhost:PORT`, which is the addressing that does not work between containers. `docker compose exec` reaches into a container without publishing anything.

**Bind-mounting the project directory and expecting the image's dependencies to survive.** The mount replaces them. The empty `node_modules` is the visible version; the dangerous version is a native module built for the host's architecture that loads and misbehaves.

**A committed `.env` with real credentials, because it started as dev-only.** The file is created honestly with a dev password, gains a staging entry, and is in the history from the first commit. Commit `.env.example` and gitignore the real one from the start, before there is anything worth protecting in it.

**Carrying `version: "3.8"` at the top of the file.** Harmless in itself — Compose warns and ignores it — but it is a marker that the file was copied from something written before `service_healthy` and `service_completed_successfully` existed, and the dependency conditions below it usually confirm that.
