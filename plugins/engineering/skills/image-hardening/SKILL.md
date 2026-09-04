---
name: image-hardening
description: "Build or audit hardened container images — base image selection down a scratch, distroless, Chainguard, alpine, slim ladder; digest pinning; multi-stage builds; numeric non-root UIDs; BuildKit secret and cache mounts; exec-form entrypoints; multi-arch buildx; SBOM generation; a vulnerability severity gate people will not bypass; VEX exceptions; cosign signing with admission-time verification; hadolint; and CIS Docker Benchmark plus NIST SP 800-190 as an audit structure. Use this skill whenever the user asks to write, review, shrink, harden, or fix a Dockerfile or Containerfile, choose a base image, pin or bump image digests, set up image scanning, signing or an SBOM, or asks things like \"is this Dockerfile any good\" or \"make my image smaller\". Do not use it for Kubernetes manifest authoring, host or runtime hardening, or CI work that does not produce an image."
allowed-tools: Bash(docker:*), Bash(hadolint:*), Bash(trivy:*), Bash(syft:*), Bash(grype:*), Bash(cosign:*), Read, Grep, Glob
---

# Image Hardening

A hardened image is a small, immutably referenced, reproducibly built artifact that carries no build tooling, no secrets, no shell it does not need, and a signed statement of where it came from — and that keeps being checked after it ships.

The job is hard because almost every failure is invisible at build time. The image runs, the tests pass, and the problems are all latent: a floating tag that silently changed under you, a token sitting in layer 3 that `rm` in layer 7 did not delete, a `USER appuser` that Kubernetes refuses to schedule under `runAsNonRoot`, a `/bin/sh -c` PID 1 that swallows SIGTERM so every rollout takes the full grace period, and a CVE published two weeks after the last build that nobody will ever look at because scanning only runs in CI. Hardening is mostly about closing gaps that will not fail loudly on their own.

## Scope

Use for: writing a new Dockerfile, reviewing or rewriting an existing one, choosing a base image, shrinking an image, setting up build/scan/sign/verify pipelines, or auditing a published image against CIS and NIST guidance.

Do not use for: Kubernetes manifest or Helm authoring, host and kernel hardening, runtime threat detection, or registry administration. Those are adjacent and the reasoning here does not transfer cleanly.

## Workflow

### 1. Declare the mode

Two modes, different artifacts. Say which one is active in the first line of the response, because the user's expectations differ sharply.

| Mode | Trigger | Deliverable |
| --- | --- | --- |
| **Build** | No Dockerfile yet, or a rewrite is wanted | A complete Dockerfile, `.dockerignore`, build command, and CI wiring |
| **Audit** | An existing Dockerfile, image reference, or repository | The ranked findings report in section 9 — do not silently rewrite the file |

"Can you improve this Dockerfile" is audit first, then build the fixed version once the findings are agreed. Rewriting immediately loses the reasoning they actually wanted.

### 2. Descend the base image ladder only as far as the runtime forces you

Stop at the first row the application can actually run on. Each step down adds a package manager, a shell, or a libc — attack surface plus a permanent stream of CVEs to triage.

| Runtime requirement | Base | What you gain, and the cost of going lower |
| --- | --- | --- |
| Static binary, no TLS, no timezones | `scratch` | Nothing to scan, because there is nothing there. Best possible answer for Go with `CGO_ENABLED=0` and Rust with musl |
| Static binary + outbound TLS, tzdata, a passwd entry | `gcr.io/distroless/static-debian12:nonroot` | ~2 MiB, CA certificates, tzdata, and a nonroot user already at 65532. This is the right default for Go |
| cgo, glibc, libssl, libstdc++ | `gcr.io/distroless/base-debian12:nonroot`, or `cc-debian12:nonroot` when libgcc/libstdc++ are needed | glibc and OpenSSL arrive; so do their CVEs |
| An interpreter | `gcr.io/distroless/python3-debian13`, `nodejs22-debian12`, `java21-debian12` | Interpreter without shell or package manager. Match the build stage's interpreter exactly or compiled extensions break |
| apk-installable dependencies, still no shell wanted | `cgr.dev/chainguard/static`, `cgr.dev/chainguard/wolfi-base` | glibc, fast CVE turnaround, SBOM and signature by default. Older tags move behind a paid tier |
| A shell is genuinely required — entrypoint scripts, in-place debugging | `alpine:3.20` | musl, not glibc: `manylinux` Python wheels do not apply so pip compiles from source, JNI and other glibc-linked `.so` files fail at load, and DNS resolution differs on multi-record responses |
| glibc plus vendor support, FIPS, or a compliance mandate | `debian:12-slim`, `registry.access.redhat.com/ubi9/ubi-minimal` | Support contracts and certified builds. Accept apt/dnf, a shell, and a larger CVE surface as the price |

The anti-pattern to name explicitly when auditing: **a `-slim` tag used as the final stage is not a minimal image**. `python:3.12-slim` still carries apt, dpkg, a shell, and whatever `apt-get install build-essential` put there. Teams routinely claim minimisation because the tag says slim while shipping the entire build toolchain in the runtime layer. Check with `docker run --rm --entrypoint sh IMAGE -c 'command -v gcc apt-get pip npm'` — if any of them answer, the build stage leaked.

### 3. Apply the non-negotiables

Each exists because of a specific failure. Justify it that way rather than asserting it.

**Pin the base by digest.** `FROM debian:12-slim@sha256:...`. A tag is a mutable pointer; the publisher can move `12-slim` to different content and your "reproducible" build silently changes. A digest is a content hash and is the only immutable reference. Keep the tag alongside the digest for human readability. Automate the bumps or the pin rots into a stale, vulnerable base — Renovate's `pinDigests: true` handles Dockerfile `FROM` lines and raises a PR per digest change, which is exactly the review point you want.

**Multi-stage, always.** Not for size — for the guarantee. Compilers, headers, package caches, `.git`, and test fixtures cannot exist in the final image if the final stage starts `FROM` something clean and only receives named `COPY --from=` artifacts. A single-stage build makes that a matter of discipline; multi-stage makes it structural.

**Numeric non-root UID.** Write `USER 65532:65532`, not `USER appuser`. Kubernetes enforces `runAsNonRoot: true` in the kubelet before the container starts, and the only thing it has to work with is the numeric user in the image config — it does not mount and parse `/etc/passwd` to resolve a name. A string username produces `CreateContainerConfigError` with "container has runAsNonRoot and image has non-numeric user, cannot verify user is non-root". This one catches experienced people, because the image runs fine under plain `docker run`. Also set the group, and `chown` anything the process must write.

**No secrets in any layer.** `ARG` and `ENV` values are recorded in the image history and readable by anyone who can pull the image: `docker history --no-trunc IMAGE`. Layers are immutable and additive, so `RUN rm /tmp/token` in a later layer does not remove the bytes from the earlier one — it only hides them from the merged filesystem view. `docker save` and any layer extractor recovers them. The only correct mechanism is a BuildKit secret mount, which exposes the value to one `RUN` and never writes it to a layer:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,mode=0400 npm ci --omit=dev
# built with: docker buildx build --secret id=npmrc,src="$HOME/.npmrc" .
```

For private Git dependencies use `RUN --mount=type=ssh` with `docker buildx build --ssh default`. Note that `--provenance=mode=max` records build arguments in the provenance attestation, so an `ARG` holding a secret leaks a second time even if you never inspect history.

**Layer order follows change frequency.** Copy dependency manifests, install, then copy source. `COPY . .` before the install step invalidates the dependency layer on every source edit, turning a 5-second rebuild into a 5-minute one. Add `--mount=type=cache` for the package manager and compiler caches so even a genuine invalidation is cheap.

**A real `.dockerignore`.** It filters the build context before the daemon or BuildKit ever sees it, which means an excluded file cannot bust a layer cache, cannot be swept into a `COPY . .`, and does not get uploaded. Without it, `.git` alone can add hundreds of megabytes to the context and change the `COPY . .` layer hash on every commit.

```gitignore
.git
.github
**/node_modules
**/__pycache__
.venv
dist/
build/
target/
.terraform
*.tfstate*
.env
.env.*
*.pem
*.key
id_rsa*
.aws
.npmrc
Dockerfile*
.dockerignore
docker-compose*.yml
```

Excluding the Dockerfiles matters too: BuildKit reads them out of band, so they are not needed in the context, and leaving them in means every Dockerfile edit invalidates the `COPY . .` layer.

**Exec-form `ENTRYPOINT`.** `ENTRYPOINT ["/usr/local/bin/app"]`, never `ENTRYPOINT /usr/local/bin/app`. Shell form wraps the command in `/bin/sh -c`, making the shell PID 1. A non-interactive `sh` does not forward signals to its child, so `SIGTERM` from a `docker stop` or a pod deletion is swallowed, the process never begins a graceful shutdown, and every rollout waits out `terminationGracePeriodSeconds` before a `SIGKILL`. A rolling update of 50 pods with a 30-second grace period becomes 25 minutes of unnecessary connection resets.

**`HEALTHCHECK` targets Docker, Compose, Swarm, and ECS. Kubernetes ignores it entirely.** There is no code path in the kubelet that reads it; health is decided by liveness, readiness, and startup probes in the pod spec. Include `HEALTHCHECK` when the image is deployed by Compose or ECS, omit it for Kubernetes-only images, and never treat it as a substitute for probes. The common failure is shipping both, then debugging why a wedged pod is never restarted.

**OCI labels**, so a running image can be traced back to source without asking anyone. Set `org.opencontainers.image.source`, `.revision`, `.created`, `.version`, and `.licenses` — see the `LABEL` block in section 4. `.source` is also what links a GitHub Container Registry package to its repository; in CI, `docker/metadata-action` emits the whole set.

### 4. Write the Dockerfile

Reference implementation for a Go service. Everything here is load-bearing; read `references/dockerfile-patterns.md` for the Python, Node, and cross-compilation variants and for the reasoning behind each mount.

```dockerfile
# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM golang:1.23-bookworm@sha256:BUILDER_DIGEST AS build
WORKDIR /src
ENV CGO_ENABLED=0
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

Two values must be filled in: `BUILDER_DIGEST` and `RUNTIME_DIGEST`. Resolve them once with `docker buildx imagetools inspect gcr.io/distroless/static-debian12:nonroot --format '{{.Manifest.Digest}}'` and let Renovate maintain them after that. `-trimpath` strips absolute build paths, which both aids reproducibility and stops leaking the builder's directory layout; `-ldflags="-s -w"` drops the symbol table and DWARF data.

### 5. Build and publish

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --provenance=mode=max \
  --sbom=true \
  --cache-from type=gha \
  --cache-to type=gha,mode=max \
  --build-arg VERSION="$(git describe --tags --always)" \
  --build-arg REVISION="$(git rev-parse HEAD)" \
  --build-arg CREATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -t ghcr.io/OWNER/REPO:"$TAG" --push .

docker buildx imagetools inspect ghcr.io/OWNER/REPO:"$TAG" --format '{{ json .SBOM }}'
docker buildx imagetools inspect ghcr.io/OWNER/REPO:"$TAG" --format '{{ json .Provenance }}'
```

Be precise about what this buys. `--provenance=mode=max` from a hosted builder produces provenance shaped like SLSA Build L2: signed, non-forgeable by the build steps themselves, listing materials and parameters. It is not L3. **L3 additionally requires the build platform to keep provenance signing keys inaccessible to user-defined build steps and to isolate builds from one another** — properties of the platform, not of a buildx flag. In practice that means the `slsa-framework/slsa-github-generator` reusable workflows or a hardened, isolated self-hosted builder. Claiming L3 on the strength of a flag is a claim an auditor will reject.

Multi-arch has a trap: on a single-arch runner, buildx uses QEMU emulation for the foreign platform. For compiled languages that is 10-20x slower, and emulation has historically produced subtly wrong binaries in code paths using less common instructions or threading primitives. Prefer native runners per architecture with a merge step, or cross-compile — `FROM --platform=$BUILDPLATFORM` on the build stage with `GOARCH=$TARGETARCH` runs the compiler natively and emits the target binary, as in section 4. Emulation is acceptable for interpreted stacks with no native extensions.

### 6. Generate an SBOM, then scan and gate

```bash
syft ghcr.io/OWNER/REPO:"$TAG" -o cyclonedx-json=sbom.cdx.json -o syft-json=sbom.syft.json
grype sbom:./sbom.syft.json --fail-on high --only-fixed
trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
  --scanners vuln,secret,misconfig --format sarif -o trivy.sarif ghcr.io/OWNER/REPO:"$TAG"
```

Two SBOM formats because they serve different consumers: CycloneDX for attestation and anything downstream, syft-json for rescanning later without re-pulling the image. The gate policy below is the part that decides whether any of this survives contact with a delivery team, so argue it rather than asserting it:

| Finding | PR gate | Release gate | Why |
| --- | --- | --- | --- |
| CRITICAL with a fix | block | block | Actionable now; a version bump closes it |
| HIGH with a fix | warn | block | Blocking every PR on this produces bypass culture; blocking a release does not |
| CRITICAL or HIGH, no fix available | warn and track | warn and track | Blocking on something nobody can fix teaches people the gate is noise |
| MEDIUM with a fix | warn | warn | Sweep these on a schedule, not per commit |
| LOW, or MEDIUM with no fix | report only | report only | Never gate on these |
| Secret detected | block | block | Zero false-negative tolerance; rotate the credential, do not just rebuild |
| Missing or unverifiable signature | not applicable | block | The release gate is where provenance is enforced |

Two gates at different strictness is the whole design. The PR gate blocks only on fixable CRITICAL so it is fast and almost never wrong; the release gate adds fixable HIGH, the secret scan, and a required signature. **A gate that blocks constantly gets bypassed within a month, and a bypassed gate is worse than no gate** because it manufactures evidence of control that does not exist.

Exceptions are data with an expiry date, never a permanent global allowlist. A blanket `--ignore-unfixed` in the pipeline config is the same mistake with better manners: it silently suppresses the next unfixable critical too. Use `.trivyignore.yaml` with `expired_at:` per CVE so the suppression self-expires and comes back as a finding, and use VEX for the case it is designed for — "we ship the vulnerable package but never reach the vulnerable function" — because that is an assertion about your software, not a suppression of the scanner:

```yaml
vulnerabilities:
  - id: CVE-2024-12345
    statement: "Reachable only via the admin CLI, which is not built into this image."
    expired_at: 2026-09-30
```

`.trivyignore.yaml` is still flagged experimental and must be passed explicitly with `--ignorefile .trivyignore.yaml`. VEX documents go in with `trivy image --vex ./vex.openvex.json`, and every statement carries a justification code such as `vulnerable_code_not_in_execute_path`. Full worked examples in `references/supply-chain.md`.

**Then scan the published image again on a schedule.** This is the gap nearly everyone has. A CVE disclosed the day after a build affects an image that no pipeline will ever look at again, because scanning is wired to the build. Run a nightly job over the tags actually deployed — or over the stored syft-json SBOMs, which is cheaper and works for images already evicted from the builder — and route findings to whoever is on call, not to a dashboard. Build-time-only scanning is the number one real-world failure in this whole area.

### 7. Sign, and verify with a pinned identity

```bash
cosign sign --yes ghcr.io/OWNER/REPO@"$DIGEST"
cosign attest --yes --predicate sbom.cdx.json --type cyclonedx ghcr.io/OWNER/REPO@"$DIGEST"
```

Keyless signing takes the CI job's OIDC token, exchanges it at Fulcio for a short-lived certificate binding the workflow's identity, and logs the signature in the Rekor transparency log — no key to store, rotate, or leak. Verification is where this is usually undone: a bare `cosign verify` proves only that *somebody* signed the image, and anyone with a GitHub account can sign anything. Pin who:

```bash
cosign verify \
  --certificate-identity-regexp '^https://github\.com/OWNER/REPO/\.github/workflows/release\.yml@refs/tags/' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/OWNER/REPO@"$DIGEST"
```

Enforce it at admission — Sigstore Policy Controller, Kyverno `verifyImages`, or Connaisseur — with the same identity constraints in the policy. Signing without admission-time verification is theatre: it produces an artifact nobody checks. `gh attestation verify oci://ghcr.io/OWNER/REPO@$DIGEST --repo OWNER/REPO` is the GitHub-native equivalent when `actions/attest-build-provenance` produced the attestation.

### 8. Lint

```bash
hadolint --failure-threshold warning Dockerfile
```

The rules worth knowing by ID, because they map to real incidents rather than style: **DL3002** last user should not be root; **DL3006** and **DL3007** untagged and `latest` base images; **DL3008**, **DL3013**, **DL3016**, **DL3018** unpinned package versions for apt, pip, npm, apk; **DL3009** apt lists left behind; **DL3015** missing `--no-install-recommends`; **DL3020** `ADD` where `COPY` belongs, since `ADD` silently fetches URLs and auto-extracts archives; **DL3025** shell-form `CMD`/`ENTRYPOINT`, the signal-handling bug above; **DL3026** base image from a registry outside `trustedRegistries`; **DL3042** pip without `--no-cache-dir`; **DL3057** missing `HEALTHCHECK`, ignored by default and worth enabling only for non-Kubernetes images; **DL3064** potentially sensitive data in `ARG` or `ENV`; **DL3046** `useradd` without `-l` at a high UID, which writes a sparse `/var/log/lastlog` that some layer packers materialise into a multi-gigabyte image. Complement hadolint with `dockle` for image-level checks it cannot see (setuid binaries, `/etc/shadow` contents, CIS mappings) and `docker scout cves` where Docker Hub is already in the toolchain.

### 9. Audit against the standards, then report

Use the standards as a checklist, not a recitation. **CIS Docker Benchmark section 4** is the image section: create a non-root user, use trusted base images, install no unnecessary packages, scan and rebuild to pick up patches, add `HEALTHCHECK` where the orchestrator honours it, never use update instructions such as `apt-get update` alone in a `RUN`, remove setuid and setgid bits, prefer `COPY` over `ADD`, store no secrets, and install only verified packages. `docker-bench-security` automates the host-side portion.

**NIST SP 800-190** gives the better structure for the report, because it separates risks by tier — image, registry, orchestrator, container, host OS — and stops an audit from collapsing into a CVE count. Its image-tier taxonomy is: vulnerabilities in the included components, image configuration defects, embedded malware, embedded clear-text secrets, and use of untrusted images. The line worth putting in front of a skeptic who wants to see a green scan and stop: an image whose every component is fully patched can still be badly configured, and that configuration raises risk on its own — so CVE count is not a hardening metric.

Also confirm the image can satisfy the Kubernetes `restricted` Pod Security Standard, since that is where a hardening effort usually gets tested for real:

| `restricted` requires | The image must |
| --- | --- |
| `runAsNonRoot: true` | Carry a numeric non-root `USER` |
| `allowPrivilegeEscalation: false` | Depend on no setuid binary |
| `capabilities.drop: ["ALL"]` | Bind only ports above 1023, since `NET_BIND_SERVICE` is gone |
| `seccompProfile: RuntimeDefault` | Use no syscall blocked by the default profile |
| Restricted volume types | Write only to mounted paths; pairs with `readOnlyRootFilesystem` |

Report findings ranked by exploitability first, then by effort ascending, so the top of the list is what someone can finish this afternoon. Fill in this structure:

```markdown
## Mode
Audit of [image reference or Dockerfile path].

## Subject
- Image: [ref@sha256:...]; base chain [final base -> its base], pinned by [digest | tag | latest]
- Size / layers: [x MiB, n layers]; built [date], [n] days ago

## Findings
| # | Exploitability | Effort | Finding | Location |
|---|---|---|---|---|
| F1 | Remote, unauthenticated | S | [one line] | Dockerfile:14 |

### F1 — [title]
- **Where**: `Dockerfile:14` — `COPY . .`
- **Risk tier** (NIST SP 800-190): image / registry / orchestrator / container / host
- **What happens**: [the concrete failure, not the rule name]
- **Fix**: [the exact replacement line or command]

## Standards checklist
| Control | Status | Evidence |
|---|---|---|
| CIS 4.1 non-root user | pass / fail | `USER 65532:65532` at Dockerfile:22 |
| PSS restricted compatible | pass / fail | [which requirement fails] |

## Not checked
[What could not be verified and what access would be needed — do not leave this implicit.]
```

## Anti-patterns

**Floating tags in `FROM`.** The base changes under you between two builds of the same commit; a build that passed the gate on Monday ships different bytes on Friday, and nothing in your logs explains it.

**`USER appuser` instead of `USER 65532:65532`.** Runs perfectly under Docker, fails to start under `runAsNonRoot: true`, discovered during a production rollout rather than in CI.

**Secrets in `ARG` or `ENV`, "removed" in a later layer.** Recoverable from `docker history --no-trunc` and from the layer tarball by anyone who can pull. The credential is compromised the moment the image is pushed, and rotating it is the only remedy.

**`curl ... | bash` inside a `RUN`.** No pinning, no checksum, no signature, and the fetched content can differ per request. It turns the upstream host into an unreviewed commit author in your build.

**`COPY . .` before installing dependencies.** Every source edit invalidates the dependency layer. Minutes per build, multiplied by every developer and every CI run.

**No `.dockerignore`.** The whole `.git` history, `node_modules`, and any stray `.env` or `*.pem` land in the build context and frequently in the image, while the context hash changes on every commit and destroys layer caching.

**`apt-get upgrade` in the Dockerfile.** The resulting image depends on the day it was built, so the same commit produces different content over time and a rebuild to reproduce an incident gives you a different system. Pin the base by digest and rebuild against a newer base instead.

**Shell-form `ENTRYPOINT`.** PID 1 becomes `/bin/sh -c`, SIGTERM is not forwarded, graceful shutdown never runs, and every deployment burns the full termination grace period.

**Scanning only at build time.** The vulnerability window is the whole life of the deployed image, not the ten minutes of the pipeline. Most exposure is discovered after the build.

**A permanent global `--ignore-unfixed` or a never-expiring allowlist.** Suppresses the finding you have already assessed and, silently, every future one in the same class.

**Signing without admission verification.** Produces a signature nobody checks, plus a slide claiming supply chain security. Verification with an unpinned identity is the same failure wearing a `cosign verify` command.

**Assuming Kubernetes honours `HEALTHCHECK`.** It does not read it. A container that has wedged itself keeps receiving traffic until someone notices, because the probes that would have caught it were never written.

## Reference files

- `references/dockerfile-patterns.md` — read when writing or rewriting a Dockerfile: complete worked builds for Go, Python, and Node, cache and secret and ssh mount recipes, cross-compilation and multi-arch layout, `.dockerignore`, and the hadolint config file.
- `references/supply-chain.md` — read when wiring SBOM generation, scan gates, exceptions, signing, or admission control: the full CI job, `.trivyignore.yaml` and OpenVEX documents, cosign sign/attest/verify, Kyverno and Policy Controller policies, SLSA level requirements, and the continuous rescanning job.
