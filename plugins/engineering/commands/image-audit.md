---
description: Audit a container image for base-image currency, non-root execution, secrets in layers, and a defensible vulnerability gate, from the image itself rather than the Dockerfile.
argument-hint: [image reference, ideally by digest]
allowed-tools: Bash(docker:*), Bash(trivy:*), Bash(syft:*), Bash(grype:*), Bash(hadolint:*), Read, Grep
---

Audit the image `$1`. Read the built image, not only the Dockerfile — what shipped is what
matters, and a multi-stage build makes the two diverge in ways that are hard to predict
from the source.

```bash
docker image inspect "$1" --format '{{.Config.User}} {{.Config.Entrypoint}} {{.Os}}/{{.Architecture}}'
docker history --no-trunc "$1"
syft "$1" -o spdx-json > /tmp/sbom.json
trivy image --scanners vuln,secret,misconfig "$1"
```

Report in this order, because it is the order of decreasing certainty that something is
actually wrong:

1. **Secrets in layers.** A credential added and deleted in a later layer is still in the
   image. Treat any hit as leaked and hand off to the `secret-rotation` skill — deleting
   the layer does not revoke anything.
2. **Running as root.** An empty or `0` `User` means root. Report the numeric UID it
   should have, and note that a name rather than a number resolves against a passwd file
   that a distroless base may not have.
3. **Base image currency.** How old, whether it is pinned by digest or by a floating tag,
   and whether a smaller base would remove most of what the scanner is complaining about.
   A tag pin is not a pin: it moves.
4. **Vulnerabilities**, and this is where the judgement is. Do not report a raw count.
   Separate what is reachable from what is merely present, note which findings have a fix
   available, and say what a defensible gate would be — a gate set where the build always
   fails is a gate that gets bypassed within a month, which is strictly worse than a
   looser one that holds.
5. **Provenance.** Whether the image is signed and whether anything actually verifies the
   signature at deploy time. A signature nobody checks is decoration.

Finish with the smallest set of changes that removes the most risk, ordered by effort, and
say plainly which findings you would accept rather than fix.

For the full build-or-audit procedure, use the `image-hardening` skill.
