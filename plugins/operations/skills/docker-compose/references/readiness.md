# Readiness: dependency conditions and healthcheck design

Read this at step 1 when converting dependency edges into conditions, at step 2 when writing the check itself, and at step 3 when choosing the numbers.

## Contents

- [The three conditions in full](#the-three-conditions-in-full)
- [What a healthcheck has to prove](#what-a-healthcheck-has-to-prove)
- [Checks by dependency class](#checks-by-dependency-class)
- [Images with no client binary](#images-with-no-client-binary)
- [Sizing start_period, interval and retries](#sizing-start_period-interval-and-retries)
- [The one-shot: migrations and seed data](#the-one-shot-migrations-and-seed-data)
- [Reading health state back](#reading-health-state-back)

## The three conditions in full

The Compose Specification defines exactly three values for `depends_on[].condition`.

| Condition | Compose waits for | Fails the bring-up when |
| --- | --- | --- |
| `service_started` | The container to be created and started. Equivalent to the short list form | Never, unless the container cannot be created |
| `service_healthy` | The dependency's healthcheck to report healthy | The dependency goes unhealthy, or never becomes healthy inside `--wait-timeout` |
| `service_completed_successfully` | The dependency's container to exit with status zero | The dependency exits non-zero |

Docker's documentation is blunt about the first row: "On startup, Compose does not wait until a container is 'ready', only until it's running." There is no implicit readiness probe. `service_healthy` is defined entirely by the `healthcheck` the dependency declares, so an edge pointing at a service without one cannot be satisfied — that is a configuration error, not a weaker guarantee.

`service_completed_successfully` is the condition most people do not know exists, and it is the correct one for a migration or seed container that has to run to completion before anything else starts.

Two additional fields on the long form, each with a version floor. A file that uses one on an older Compose gets no error and no behaviour:

- `restart: true`, Compose v2.17.0 and later. Restarts this service after Compose updates or restarts the dependency. It applies to an explicit Compose operation, not to the container runtime restarting a dead container. Without it, restarting the database leaves the application holding a pool of connections to a container that no longer exists, and the errors outlive the restart that caused them.
- `required: false`, Compose v2.20.0 and later, default `true`. Downgrades an absent dependency from an error to a warning. This is the correct way to depend on a service that lives behind a profile.

The short form and the long form are the same object after normalisation, which is why `docker compose config` is the honest way to audit a file: a short list prints as `condition: service_started`, stated rather than implied.

```yaml
services:
  api:
    image: example/api
    depends_on:
      db:
        condition: service_healthy
        restart: true
      migrate:
        condition: service_completed_successfully
      otel-collector:
        condition: service_started
        required: false
```

## What a healthcheck has to prove

Compose's `healthcheck` takes the same fields and defaults as the `HEALTHCHECK` Dockerfile instruction, and overrides whatever the image set. The container's health starts at `starting`, becomes `healthy` on the first passing check, and becomes `unhealthy` after `retries` consecutive failures outside the start period.

`test` is either a string — equivalent to `CMD-SHELL` with that string — or a list whose first element is `CMD`, `CMD-SHELL` or `NONE`. `CMD` runs the binary directly with no shell, so no pipes, no `||`, no variable expansion. `CMD-SHELL` runs it through the container's default shell, which is what you want for anything with a fallback exit or an environment variable in it. `disable: true` or `test: ["NONE"]` turns off a check the image declared.

Three properties separate a check that means something from one that does not.

**Same transport as the dependent.** A check that reaches the service over a Unix socket, or over `localhost` inside the container, proves nothing about the TCP listener on the bridge network that the dependent will use. This is not hypothetical: it is the Postgres failure below.

**Proves the work is done.** Accepting a connection is not the same as being usable. A broker with no topics, a database mid-migration and an HTTP service answering from a static route while its pool is empty all accept connections.

**Cheap enough to run forever.** It executes every `interval` on every machine that runs this file. Opening a connection and running a trivial query is fine. Anything that scans, locks or allocates competes with the startup it is supposed to be measuring, and does so most on the slow cold start where it matters.

## Checks by dependency class

These are shapes, not values to copy. The numbers in your file come from the arithmetic below, measured on the slowest machine that runs the environment.

**Postgres.** Docker's own startup-order documentation uses `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}`, and that is fine once initialisation is finished. The gap is during initialisation. The official image's entrypoint starts a temporary server with `listen_addresses` set to empty — Unix socket only — runs everything in `/docker-entrypoint-initdb.d` against it, stops it, then starts the real server. `pg_isready` with no host connects over that same socket, so on a first bring-up with an empty volume and slow init scripts it can report ready while nothing is listening on the port at all. Force the check down the path the dependent will use — TCP, with credentials, running a query:

```yaml
    healthcheck:
      test: ["CMD-SHELL", "psql -h 127.0.0.1 -U $$POSTGRES_USER -d $$POSTGRES_DB -c 'select 1' || exit 1"]
      start_period: 30s
      start_interval: 1s
      interval: 20s
      timeout: 5s
      retries: 3
```

`$$` escapes the dollar so Compose does not interpolate it and the container's shell expands it instead. The check runs inside the container, so `127.0.0.1` here is a TCP connection to the real server rather than the socket, which is exactly the distinction the temporary server hides. The numbers are the arithmetic below applied to one example service, not values to copy.

**MySQL and MariaDB.** The same two-phase init applies. `mysqladmin ping` returns success in states where a query would still fail, so prefer a query through the client with credentials taken from the container's own environment.

**Redis.** `redis-cli ping` is genuinely sufficient for a cache with no persistence: there is no init phase and the reply proves the server loop is running. With an AOF or RDB file to load at startup the server does not accept commands until loading completes, so the same check is still correct — it fails, correctly, until the data is loaded — but the start period has to cover the load time, which scales with the dataset a developer has accumulated.

**An HTTP service you wrote.** Give it an endpoint that is not the application's front page and that checks its own dependencies once rather than on every request. Check it with whatever the image already contains. If neither `curl` nor `wget` is present, adding one to a production image to satisfy a dev healthcheck is a trade `image-hardening` has an opinion about; a language-native one-liner already in the image is usually available and avoids the argument.

**A broker.** Accepting AMQP or Kafka connections and having the topics or exchanges the consumer expects are different events. Where a one-shot creates them, make the consumer depend on that job with `service_completed_successfully` and let the broker's own check stay simple.

## Images with no client binary

There is no honest check available from inside a container that lacks any tool to speak its own protocol. The dishonest options — checking that a PID exists, or `test -f` on a socket path — pass before the service is usable, which is worse than having no check, because it puts a green tick on the race.

Three real options, in order of preference:

1. Add the client to the image, if it is a dev-only image or the client is small. This is a Dockerfile change and belongs to `image-hardening`.
2. Depend with `service_started` and make the dependent retry with a bounded backoff, accepting that the ordering is best-effort. Honest, and correct for anything that must survive the dependency restarting in production anyway.
3. A tiny gate service on the same network whose only job is to poll the dependency and exit zero, with the real dependent using `service_completed_successfully` on it. This moves the check to a container you control, and it costs an extra service in every listing of the environment.

## Sizing start_period, interval and retries

The inherited defaults are `interval` 30s, `timeout` 30s, `start_period` 0s, `start_interval` 5s, `retries` 3.

`start_period` is a grace window, not a delay, and the documented behaviour has two parts. A probe failure during the period is not counted toward the maximum number of retries. And if a check succeeds during the period, the container is considered started, the period is over, and consecutive failures from then on do count. That second property is what makes a generous `start_period` nearly free: a fast machine leaves it after one check.

The default of zero is the expensive one, and the cost is latency rather than correctness. `start_interval` is a separate, shorter poll period that applies only *during* the start period. With no start period declared it never applies, so the first check happens one full `interval` after the container starts. A service that is genuinely serving two seconds in is first checked at thirty, and everything gated on it behind `service_healthy` waits the difference — on every machine, on every run, with nothing logged. `start_period: 30s` with `start_interval: 1s` collapses that to about two seconds.

`start_interval` requires Docker Engine 25.0 or later, and Compose v2.20.2 or later to express it. On anything older it is ignored and the start period polls at `interval`, which is the one situation where a short `interval` is the right answer in spite of everything below.

Set the start period from a measurement of the worst honest cold start — empty volume, image pulled fresh, slowest machine in the team — with headroom, not from an example:

```bash
set -Eeuo pipefail

docker compose down --volumes --remove-orphans
docker compose pull
time docker compose up --wait --wait-timeout 300
```

`interval` and `retries` govern steady state. Detection time for a genuine failure is about `retries * interval`, plus up to `timeout` for a check that hangs rather than fails. Choose the detection time first and factor it: wanting a failure noticed inside a minute with two confirmations before acting gives three retries at twenty seconds.

`timeout` should be longer than the check's normal duration by enough that load does not produce false failures, and short enough that a hung check is caught rather than absorbed. The default of 30s is long for a `select 1`.

A short `interval` with the default `start_period` of zero is the specific combination that breaks CI. The retries are consumed before the service has started, the dependency is marked unhealthy, dependents gated on `service_healthy` are never created, and `up --wait` times out. Docker does not restart the container for being unhealthy — restart policies act on exit — so nothing in the Compose output names health as the cause. Under anything that *does* act on health, the same configuration becomes the restart loop, each cycle starting the slow start again from cold.

## The one-shot: migrations and seed data

`service_completed_successfully` is the condition that removes the wait loops from entrypoints, and it composes with a healthcheck on the thing the one-shot needs:

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "psql -h 127.0.0.1 -U app -d app -c 'select 1' || exit 1"]
      start_period: 30s
      start_interval: 1s
      interval: 20s
      retries: 3

  migrate:
    image: example/api
    command: ["./manage", "migrate"]
    restart: "no"
    depends_on:
      db:
        condition: service_healthy

  api:
    image: example/api
    depends_on:
      migrate:
        condition: service_completed_successfully
```

Two details. `restart: "no"` on the one-shot is worth stating explicitly, because a restart policy inherited from an override file turns a completed job into one that runs repeatedly and never reaches a terminal state. And the migration must be idempotent: the same graph runs on every `up`, including the ones where the volume already exists and every migration has already been applied.

## Reading health state back

When a bring-up fails, the useful output is the health log, not the service's stdout:

```bash
set -Eeuo pipefail

# Status of every container in the project, including health.
docker compose ps --format json | jq -r '"\(.Service): \(.State) \(.Health)"'

# The last checks with their exit codes and output. This is where a check that
# is failing for a boring reason - wrong credentials, missing binary - shows it.
docker inspect --format '{{json .State.Health}}' "$(docker compose ps -q db)" | jq .

# Run the check by hand, exactly as configured, to see the real error.
docker compose exec db sh -c "psql -h 127.0.0.1 -U app -d app -c 'select 1'"
```

A health log of `exec: "curl": executable file not found` is the most common single cause of a check that never passes, and it is invisible unless you look here.
