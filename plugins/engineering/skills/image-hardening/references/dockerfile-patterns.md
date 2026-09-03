# Dockerfile Patterns

Worked builds and the mount mechanics behind them. Read alongside step 4 of `SKILL.md`.

## Contents

- [Digest resolution](#digest-resolution)
- [Go: static binary on distroless](#go-static-binary-on-distroless)
- [Python: venv on distroless, and the ABI trap](#python-venv-on-distroless-and-the-abi-trap)
- [Node: pnpm/npm on distroless nodejs](#node-pnpmnpm-on-distroless-nodejs)
- [Cache mounts](#cache-mounts)
- [Secret and SSH mounts](#secret-and-ssh-mounts)
- [Multi-arch and cross-compilation](#multi-arch-and-cross-compilation)
- [`.dockerignore` per stack](#dockerignore-per-stack)
- [HEALTHCHECK, for the runtimes that read it](#healthcheck-for-the-runtimes-that-read-it)
- [hadolint configuration](#hadolint-configuration)
- [Verifying the result](#verifying-the-result)

## Digest resolution

Every `FROM` in these examples carries a placeholder digest. Resolve each once:

```bash
docker buildx imagetools inspect gcr.io/distroless/static-debian12:nonroot \
  --format '{{.Manifest.Digest}}'
docker buildx imagetools inspect golang:1.23-bookworm --format '{{.Manifest.Digest}}'
```

Then hand maintenance to Renovate so the pin does not rot:

```json
{
  "extends": ["config:recommended"],
  "docker": { "pinDigests": true },
  "packageRules": [
    { "matchDatasources": ["docker"], "matchUpdateTypes": ["digest"], "automerge": true },
    { "matchDatasources": ["docker"], "matchUpdateTypes": ["major"], "automerge": false }
  ]
}
```

Digest-only bumps are safe to automerge once the release gate is in place; major base bumps are not.

## Go: static binary on distroless

```dockerfile
# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM golang:1.23-bookworm@sha256:BUILDER_DIGEST AS build
WORKDIR /src
ENV CGO_ENABLED=0 GOFLAGS=-mod=readonly
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
ARG TARGETOS TARGETARCH VERSION=dev REVISION=unknown
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build,id=gobuild-${TARGETARCH},sharing=locked \
    GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build \
      -trimpath \
      -ldflags="-s -w -X main.version=${VERSION} -X main.revision=${REVISION}" \
      -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot@sha256:RUNTIME_DIGEST
ARG VERSION=dev REVISION=unknown CREATED
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.licenses="Apache-2.0"
COPY --from=build /out/app /usr/local/bin/app
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/app"]
```

Details that matter:

- `CGO_ENABLED=0` is what makes `static` viable. With cgo on, the binary needs glibc and you must move down to `distroless/base` or `cc`.
- `GOFLAGS=-mod=readonly` makes the build fail rather than silently editing `go.mod`, which would break reproducibility.
- `-trimpath` removes the builder's absolute paths from the binary — both a reproducibility fix and a small information-disclosure fix.
- `EXPOSE 8080`, not 80. Under the Kubernetes `restricted` Pod Security Standard all capabilities are dropped, including `NET_BIND_SERVICE`, so a non-root process cannot bind below 1024.
- If the app needs a writable directory, create it in the build stage and `COPY --from=build --chown=65532:65532`. There is no `mkdir` in a distroless image.
- Drop to `FROM scratch` when you need neither CA certificates nor tzdata. If you need only CA certs, `COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/` and stay on `scratch`.

## Python: venv on distroless, and the ABI trap

The build stage's interpreter must be the same version as the one inside the distroless image, and it must live at the same path, or the venv's `pyvenv.cfg` and compiled extension modules will not load. `gcr.io/distroless/python3-debian13` ships Python 3.13 at `/usr/bin/python`; `python:3.13-slim-trixie` ships it at `/usr/local/bin/python`. Bridge with a symlink.

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.13-slim-trixie@sha256:BUILDER_DIGEST AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install --no-install-recommends --yes gcc libc6-dev && \
    ln -s /usr/local/bin/python /usr/bin/python && \
    /usr/bin/python -m venv /venv
ENV PATH=/venv/bin:$PATH
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --require-hashes -r requirements.txt

FROM gcr.io/distroless/python3-debian13:nonroot@sha256:RUNTIME_DIGEST
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO"
COPY --from=build /venv /venv
COPY --chown=65532:65532 ./app /app
WORKDIR /app
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/venv/bin/python", "-m", "app"]
```

Notes:

- `pip install --require-hashes` with a `requirements.txt` generated by `pip-compile --generate-hashes` (or `uv pip compile --generate-hashes`) is the Python equivalent of a digest pin. Without it, a yanked-and-republished sdist changes what you shipped.
- A pip **cache mount** and `--no-cache-dir` solve the same problem differently. Use the cache mount in a multi-stage build where the venv is copied out; use `--no-cache-dir` (hadolint DL3042) when the install happens in the final stage. Do not do both, and never leave `~/.cache/pip` in a shipped layer.
- The inline `# hadolint ignore=DL3008` is a deliberate, scoped decision, not laziness. Pinning `gcc=4:14.2.0-1` style versions makes the build reproducible but breaks on every Debian point rebuild, and nothing bumps them automatically. In a **builder** stage whose output never ships, the base digest pin already fixes the package set, so the pin buys little. In a **final** stage that ships apt-installed packages, pin them and accept the maintenance. Scope the ignore to the one `RUN`; a repo-wide DL3008 ignore is the anti-pattern.
- If the app needs native wheels that have no manylinux build, this is the point at which alpine costs you an hour per build and a compiler in the image.
- `ENTRYPOINT` uses `/venv/bin/python` explicitly because the distroless image's own entrypoint is `/usr/bin/python`, which is not venv-aware.

Simpler alternative when distroless is not worth the alignment work: keep `python:3.13-slim-trixie` as the final stage, `COPY --from=build /venv /venv`, add `USER 65532:65532`, and accept apt, dpkg, and a shell in the image. That is a legitimate trade; what is not legitimate is calling it minimal.

## Node: pnpm/npm on distroless nodejs

The distroless nodejs images set `ENTRYPOINT ["/nodejs/bin/node"]`, so the final instruction is a `CMD` naming the script, not an `ENTRYPOINT`.

```dockerfile
# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim@sha256:BUILDER_DIGEST AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev

FROM node:22-bookworm-slim@sha256:BUILDER_DIGEST AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

FROM gcr.io/distroless/nodejs22-debian12:nonroot@sha256:RUNTIME_DIGEST
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO"
WORKDIR /app
COPY --from=deps --chown=65532:65532 /app/node_modules ./node_modules
COPY --from=build --chown=65532:65532 /app/dist ./dist
COPY --chown=65532:65532 package.json ./
USER 65532:65532
EXPOSE 8080
CMD ["dist/server.js"]
```

Two dependency stages is deliberate: `deps` produces the production tree that ships, `build` produces the full tree including devDependencies that must not. Installing everything once and pruning afterwards leaves the dev packages in an earlier layer where a scanner will still find them.

`node:22-bookworm-slim` is the builder only. Node's major version in the builder and in the `nodejs22` runtime must match, or native addons compiled against the wrong NODE_MODULE_VERSION fail at `require` time.

## Cache mounts

```dockerfile
RUN --mount=type=cache,target=/root/.cache/go-build,id=gobuild-${TARGETARCH},sharing=locked ...
RUN --mount=type=cache,target=/root/.cache/pip ...
RUN --mount=type=cache,target=/root/.npm ...
RUN --mount=type=cache,target=/root/.cargo/registry ...
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked ...
```

Three things people get wrong:

1. **Cache mount contents are not exported by `--cache-to type=gha` or `type=registry`.** Those export layer cache, which is a different thing. On ephemeral CI runners a `type=cache` mount starts empty every run unless you use a persistent builder, a self-hosted runner with a durable volume, or a cache-restore dance. Layer caching still works and is usually the bigger win.
2. **Give per-architecture `id=`s.** A shared compiler cache across `linux/amd64` and `linux/arm64` builds either thrashes or, worse, is reused incorrectly.
3. **`sharing=locked` for anything not concurrency-safe**, notably apt's lists and lock files. The default `shared` lets parallel stages corrupt each other.

Using an apt cache mount requires disabling Debian's automatic cleanup, otherwise the cache is deleted the moment apt finishes:

```dockerfile
RUN rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
```

## Secret and SSH mounts

```dockerfile
# Secret file, mounted for one RUN, never written to a layer.
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,mode=0400 npm ci --omit=dev

# Default target is /run/secrets/<id> if you omit target=.
RUN --mount=type=secret,id=pypi_token \
    PIP_INDEX_URL="https://__token__:$(cat /run/secrets/pypi_token)@pypi.internal/simple" \
    pip install -r requirements.txt

# Private Git dependencies over SSH.
RUN --mount=type=ssh \
    mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts && \
    go mod download
```

```bash
docker buildx build \
  --secret id=npmrc,src="$HOME/.npmrc" \
  --secret id=pypi_token,env=PYPI_TOKEN \
  --ssh default \
  -t IMAGE .
```

In GitHub Actions with `docker/build-push-action`, the equivalent inputs are `secrets:` and `ssh: default`.

What is still wrong even with a secret mount: writing the secret into a file under the build context, echoing it into a layer (`RUN echo "$TOKEN" > /app/.env`), or passing it as a `--build-arg`. Build args appear in `docker history --no-trunc` and in `--provenance=mode=max` output. Verify with:

```bash
docker history --no-trunc IMAGE | grep -iE 'token|password|secret|key'
docker buildx imagetools inspect IMAGE --format '{{ json .Provenance }}' | grep -i 'args'
```

## Multi-arch and cross-compilation

BuildKit sets `BUILDPLATFORM`/`BUILDOS`/`BUILDARCH` for the machine running the build, and `TARGETPLATFORM`/`TARGETOS`/`TARGETARCH`/`TARGETVARIANT` for the image being produced. Pinning the build stage to `$BUILDPLATFORM` and passing `TARGETARCH` to the compiler means the toolchain runs natively while emitting a foreign binary:

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.23-bookworm@sha256:... AS build
ARG TARGETOS TARGETARCH
RUN GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -o /out/app ./cmd/app
```

Without `--platform=$BUILDPLATFORM`, buildx runs the whole build stage under QEMU for each foreign platform. For compiled languages that is 10-20x slower, and QEMU's instruction coverage is not perfect — it has produced miscompiled output and spurious test failures around atomics, unusual SIMD paths, and 32-bit time handling. Emulation is fine for interpreted stacks with no native extensions.

The fast, correct CI layout for compiled languages is one native runner per architecture producing digest-only pushes, then a manifest merge:

```bash
# job per arch, on a matching runner
docker buildx build --platform linux/amd64 \
  --provenance=mode=max --sbom=true \
  --output type=image,name=ghcr.io/OWNER/REPO,push-by-digest=true,name-canonical=true,push=true .

# merge job
docker buildx imagetools create -t ghcr.io/OWNER/REPO:"$TAG" \
  ghcr.io/OWNER/REPO@sha256:AMD64_DIGEST ghcr.io/OWNER/REPO@sha256:ARM64_DIGEST
```

## `.dockerignore` per stack

Start from the base set in `SKILL.md` and add:

| Stack | Additional entries |
| --- | --- |
| Go | `vendor/` if you do not build with `-mod=vendor`, `*_test.go` fixtures directories, `bin/` |
| Python | `.venv`, `**/__pycache__`, `**/*.pyc`, `.pytest_cache`, `.mypy_cache`, `.tox`, `htmlcov`, `*.egg-info` |
| Node | `**/node_modules`, `.next`, `coverage`, `.turbo`, `.pnpm-store`, `npm-debug.log*` |
| Rust | `target/`, `**/*.rs.bk` |
| Any | `.git`, `.github`, `.env*`, `*.pem`, `*.key`, `id_rsa*`, `.aws`, `.terraform`, `*.tfstate*`, `Dockerfile*`, `docker-compose*.yml` |

Confirm what actually reaches the daemon:

```bash
docker buildx build --no-cache --progress=plain -f /dev/null . 2>&1 | grep 'transferring context'
```

## HEALTHCHECK, for the runtimes that read it

Docker, Compose, Swarm, and ECS act on `HEALTHCHECK`. Kubernetes does not read it at all — use `livenessProbe`, `readinessProbe`, and `startupProbe`. Include it only when a supported runtime is in play:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/app", "healthcheck"]
```

Exec form, and a subcommand of your own binary rather than `curl`, because a distroless image has no curl and adding one to satisfy a healthcheck undoes the base image choice. If the image is Kubernetes-only, omit `HEALTHCHECK` and leave hadolint's DL3057 in its default ignored state.

## hadolint configuration

`.hadolint.yaml` at the repository root:

```yaml
failure-threshold: warning
format: sarif
trustedRegistries:
  - ghcr.io
  - gcr.io
  - cgr.dev
  - registry.access.redhat.com
  - docker.io
override:
  error:
    - DL3002   # last user must not be root
    - DL3025   # exec-form CMD/ENTRYPOINT
    - DL3064   # sensitive data in ARG/ENV
```

Note what is *not* here: a repo-wide `ignored:` list. Suppress DL3008 and friends with an inline `# hadolint ignore=DL3008` on the single `RUN` that needs it, so the exception is visible next to the code it excuses. If a global ignore is genuinely unavoidable, give it a dated comment — an undated ignore is permanent by default, which is how a lint config stops meaning anything.

## Verifying the result

```bash
# No shell, no package manager, no compiler leaked from the build stage.
docker run --rm --entrypoint sh IMAGE -c 'command -v gcc apt-get apk pip npm' || echo "no shell: good"

# Numeric non-root user in the image config.
docker inspect --format '{{.Config.User}}' IMAGE     # expect 65532:65532

# Exec-form entrypoint (a JSON array, not a /bin/sh -c wrapper).
docker inspect --format '{{json .Config.Entrypoint}}' IMAGE

# No setuid/setgid binaries (needed for allowPrivilegeEscalation: false).
docker run --rm --entrypoint sh IMAGE -c 'find / -xdev -perm /6000 -type f' 2>/dev/null

# Nothing sensitive in the build history.
docker history --no-trunc IMAGE

# Layer count and where the bytes went.
dive IMAGE  # or: docker history IMAGE
```

The first command failing with "no such file or directory" is the desired outcome for a distroless image; for images that do have a shell, an empty result from `command -v` is the pass.
