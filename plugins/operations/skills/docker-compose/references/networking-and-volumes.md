# Networking and storage

Read this at step 4 when deciding what should be reachable from where, and at step 5 when choosing between a named volume and a bind mount.

## Contents

- [The default network](#the-default-network)
- [Container port versus host port](#container-port-versus-host-port)
- [Custom networks and isolation](#custom-networks-and-isolation)
- [Reaching the host, and being reached from it](#reaching-the-host-and-being-reached-from-it)
- [CI, where the job is itself a container](#ci-where-the-job-is-itself-a-container)
- [Joining another project's network](#joining-another-projects-network)
- [Debugging a connection that should work](#debugging-a-connection-that-should-work)
- [Named volume or bind mount](#named-volume-or-bind-mount)
- [Bind mount ownership across host platforms](#bind-mount-ownership-across-host-platforms)
- [The node_modules problem and its three answers](#the-node_modules-problem-and-its-three-answers)
- [Volume lifecycle](#volume-lifecycle)

## The default network

Compose creates one bridge network per project, named `<project>_default`, and attaches every service to it. The project name defaults to the directory name and is overridden by `--project-name` or `COMPOSE_PROJECT_NAME`. Each service registers its name with Docker's embedded DNS, so `db` resolves from any other container in the project with no configuration at all.

Container IP addresses are assigned dynamically and change whenever a container is recreated, so an address that works today is not a thing to record anywhere. Address services by name. When a service is recreated, the name resolves to the new address immediately, but existing connections to the old address are closed and are not re-established for you — reconnection is the application's job, and a connection pool that does not do it turns a recreate into a hang.

## Container port versus host port

`ports: "8001:5432"` maps host port 8001 to container port 5432. Only the host side is affected. Between containers the address is `db:5432` — the container port — whether or not anything is published.

This is the single most common addressing mistake in a Compose file and it does not look like one. `DATABASE_URL=postgres://db:8001/app` is syntactically fine, refers to a real service name, and fails with a connection error that reads like the database is down.

`expose:` documents which container ports a service uses. On a bridge network it grants nothing that the network did not already allow, so it is a comment with schema validation rather than a control.

Publish as little as possible. Every published port is reachable from anything on the developer's machine, and on a shared CI runner two concurrent jobs that both publish 5432 will fight over it — one of them fails to start, with an error about the address being in use that has nothing to do with the change under test. `docker compose exec` gets you into a container without publishing anything.

## Custom networks and isolation

Naming networks explicitly buys one thing worth having: a service can be made unreachable from services that have no business reaching it.

```yaml
services:
  proxy:
    image: example/proxy
    ports: ["8080:8080"]
    networks: [edge]

  api:
    image: example/api
    networks: [edge, data]

  db:
    image: postgres:16
    networks: [data]

networks:
  edge:
  data:
    internal: true
```

`proxy` cannot resolve or reach `db`, because they share no network. `internal: true` additionally removes external connectivity from the `data` network, so nothing on it can reach out to the internet — which is a useful property for a database container and an occasionally surprising one for a service that expected to fetch something at startup.

A service on several networks resolves names on all of them. A name that exists on two networks a container is attached to is ambiguous, which is a reason to keep service names unique across the project even when the networks would allow otherwise.

## Reaching the host, and being reached from it

From the host, only published ports are reachable, at `localhost:<host port>`.

From inside a container, `localhost` is that container. Reaching a process running on the host — a database you already had, a proxy, a language server — uses `host.docker.internal`. On Docker Desktop that name exists already. On Linux it does not, and needs an explicit mapping:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

This asymmetry is worth writing down in the repository, because a file that works unchanged on two developers' laptops and fails on the third is usually this.

`network_mode: host` shares the host's network stack: no port mapping is possible, and service-name DNS does not work. It is right for a tool that genuinely needs to observe host interfaces and wrong for almost everything else, and the way it fails is that half the file quietly stops applying.

## CI, where the job is itself a container

On many CI providers the job runs inside a container. A `ports:` publication then lands on the job container's network namespace rather than on something the test process can reach by `localhost` in the way a laptop would, and the "same" command that works locally fails with connection refused.

The portable answer is to stop crossing the boundary: make the test runner a service in the same Compose project, so it reaches the others by service name over the project network exactly as the application does.

```bash
set -Eeuo pipefail

PROJECT="ci-${BUILD_ID}"
trap 'docker compose --project-name "$PROJECT" down --volumes --remove-orphans' EXIT

docker compose --project-name "$PROJECT" up --wait --wait-timeout 300
docker compose --project-name "$PROJECT" run --rm tests
```

The unique project name is not decoration. Without it, two jobs on the same runner share network and volume names, and the second `down` removes the first job's database underneath it.

## Joining another project's network

Where a second Compose project genuinely has to reach the first — a shared local infrastructure stack, say — declare the existing network as external rather than duplicating services:

```yaml
networks:
  shared:
    name: infra_default
    external: true
```

Compose will not create it and errors if it is absent, which is the correct behaviour: the alternative is a project that silently comes up on an empty network of its own.

## Debugging a connection that should work

```bash
set -Eeuo pipefail

# Which networks exist for this project, and who is on them.
docker compose config --networks
docker network inspect "$(docker compose ps -q api | head -n1)" --format '{{json .}}' | jq . || true

# Does the name resolve from inside the client container? A failure here is a
# network membership problem, not a service problem.
docker compose exec api getent hosts db

# Is the container port open, as opposed to the published one?
docker compose exec api sh -c 'nc -z db 5432 && echo open'
```

Resolution failing means the two services do not share a network. Resolution succeeding with the connection refused means the service is not listening yet, which sends you back to the readiness gate rather than to the network configuration.

## Named volume or bind mount

| Data | Mount | Why |
| --- | --- | --- |
| Database files, indexes, uploaded blobs | Named volume | The container owns the format; the host should not be reading or writing it, and performance on Desktop's file-sharing layer is much worse for a bind mount |
| Source you are editing | Bind mount | Immediate reflection inside the container is the entire point |
| Dependencies installed during the image build | Neither | They belong in the image. Mounting over them is the `node_modules` failure below |
| Config files read at startup | Bind mount, read-only, or a `configs` entry | Small, host-authored, and `:ro` documents that the container does not write them |
| Scratch space | `tmpfs` | Never needs to survive, and keeping it out of the image's writable layer is free |

## Bind mount ownership across host platforms

Short-syntax bind mounts create the host path if it does not exist. The specification states this explicitly, as backward compatibility with legacy `docker-compose`. The consequences are two:

- A typo in a source path produces a new empty directory instead of an error, and the symptom is an empty mount inside the container rather than a message.
- The daemon creates it, so on Linux it is owned by root, and a container running as a non-root user cannot write to it.

The long syntax turns this back into a failure:

```yaml
    volumes:
      - type: bind
        source: ./config
        target: /etc/app
        read_only: true
        bind:
          create_host_path: false
```

Ownership behaviour then differs by host, which is the mechanism behind a large share of "works on my machine":

| Host | Behaviour |
| --- | --- |
| Linux | Host uid and gid pass through unchanged. A container running as uid 1000 cannot write to a directory owned by 1001, and a container running as root leaves root-owned files in the developer's checkout that they then cannot delete without `sudo` |
| macOS, Windows with Docker Desktop | The file-sharing layer maps ownership so that writes generally succeed regardless of the container's uid |

A Compose file developed entirely on Desktop has never exercised the Linux behaviour, and CI is Linux. Either run the container as the host user — passing the uid in through an interpolated variable — or keep written data in named volumes and bind-mount only what the container reads.

## The node_modules problem and its three answers

Bind-mounting the project directory over the image's working directory replaces the installed dependencies with whatever the host has at that path. Two failures follow, and the second is worse:

- The host has no `node_modules`, so the directory inside the container is empty and the process cannot start. Loud, and quickly understood.
- The host has one, installed against the host's platform and architecture. Pure-JavaScript packages work. Anything with a native addon fails at load, or worse, loads and behaves differently — and nothing about the symptom points at the mount.

Three answers, in increasing order of how well they hold up:

1. **Mask the path with a volume.** Adding `- /app/node_modules` after the bind mount shadows it with an anonymous volume seeded from the image. It works immediately, and it goes stale silently the moment the lockfile changes, because the volume is seeded only when it is created. A rebuild does not refresh it; `down -v` does.
2. **Move the modules outside the mounted tree.** Install to a path the bind mount does not cover and point the runtime at it. No masking volume, no staleness, and it requires the runtime to support relocating its module path.
3. **Use `develop.watch`.** Sync source into the running container, ignore the module directory, and rebuild the image when the lockfile changes. This makes a dependency change an image rebuild, which is what it actually is.

```yaml
    develop:
      watch:
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - node_modules/
        - action: rebuild
          path: ./package-lock.json
```

Patterns under `ignore` use `.dockerignore` syntax, and the build context's `.dockerignore` is loaded implicitly before these are appended.

## Volume lifecycle

`docker compose down` removes containers and networks. It does not remove named volumes; `down --volumes` does. Anonymous volumes are removed by `down -v` too, and by `run --rm`.

This is the feature — a dev database that survives a restart — and it is also why a corrupted one survives every attempt to fix it. When a change to an image's initialisation logic appears to have no effect, the first thing to check is whether the volume it writes into predates the change:

```bash
set -Eeuo pipefail

# Volumes this project declares, and when each was actually created.
docker compose config --volumes
docker volume ls --filter "label=com.docker.compose.project=$(basename "$PWD")"

# The reset that makes initialisation run again.
docker compose down --volumes --remove-orphans
```

`nocopy: true` on a named volume mount disables the seeding from image content entirely, which is the right setting when the image's copy at that path is stale by construction and you would rather have an empty directory than a plausible wrong one.
