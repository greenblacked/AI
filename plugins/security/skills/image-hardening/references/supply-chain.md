# Supply Chain: SBOM, Scanning, VEX, Signing, Admission

The machinery behind steps 5 through 7 of `SKILL.md`. Read when wiring the pipeline rather than when writing the Dockerfile.

## Contents

- [SBOM generation](#sbom-generation)
- [Scanners and the flags that matter](#scanners-and-the-flags-that-matter)
- [The gate policy, in CI](#the-gate-policy-in-ci)
- [Exceptions with an expiry](#exceptions-with-an-expiry)
- [VEX: asserting non-exploitability](#vex-asserting-non-exploitability)
- [Continuous re-scanning](#continuous-re-scanning)
- [Signing and attestation](#signing-and-attestation)
- [Verification, with a pinned identity](#verification-with-a-pinned-identity)
- [Admission control](#admission-control)
- [SLSA levels, honestly](#slsa-levels-honestly)
- [What to record for an audit](#what-to-record-for-an-audit)

## SBOM generation

Two paths, and you generally want both.

**In-band, from buildx.** `--sbom=true` attaches an SPDX attestation to the image index at push time, so the SBOM travels with the artifact and cannot be separated from it:

```bash
docker buildx build --sbom=true --provenance=mode=max -t IMAGE --push .
docker buildx imagetools inspect IMAGE --format '{{ json .SBOM }}'
docker buildx imagetools inspect IMAGE --format '{{ json .Provenance }}'
```

**Out-of-band, from syft**, which gives you formats the buildx SBOM generator does not and a file you can archive:

```bash
syft IMAGE -o cyclonedx-json=sbom.cdx.json -o syft-json=sbom.syft.json
```

- **CycloneDX** is what you attest and what downstream consumers, VEX tooling, and most compliance workflows expect.
- **syft-json** is the rescanning format: it preserves syft's full package metadata, so `grype sbom:./sbom.syft.json` months later gives the same results as scanning the image, without pulling anything. Keep it as a build artifact with the same retention as the image.

Buildx's SBOM covers the final image's filesystem, so build-time-only dependencies are absent by design. If an auditor wants them too, either run syft against the named build stage (`docker buildx build --target build --load`, then scan) or opt intermediate stages in with BuildKit's `BUILDKIT_SBOM_SCAN_STAGE` / `BUILDKIT_SBOM_SCAN_CONTEXT` build args — confirm the exact behaviour against your BuildKit version before relying on it.

## Scanners and the flags that matter

```bash
# Grype, against the stored SBOM.
grype sbom:./sbom.syft.json --fail-on high --only-fixed --output sarif --file grype.sarif

# Trivy, against the image, all three scanner families.
trivy image \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --scanners vuln,secret,misconfig \
  --exit-code 1 \
  --format sarif --output trivy.sarif \
  IMAGE
```

- `--only-fixed` (grype) and `--ignore-unfixed` (trivy) restrict the result to vulnerabilities someone can actually act on. Use them **in the gate command**, and run a second, un-gated scan that reports everything so the unfixable set stays visible. A blanket `--ignore-unfixed` as the only scan is how an unfixable critical goes unnoticed for a year.
- `--scanners secret` is not optional. A leaked credential in a layer is a different class of problem from a CVE and needs a block plus a rotation, not a ticket.
- `--scanners misconfig` catches Dockerfile-level defects (root user, `ADD` from a URL, missing `USER`) that a package scanner cannot see.
- SARIF output uploads to GitHub code scanning via `github/codeql-action/upload-sarif`, which puts findings on the PR diff rather than in a job log nobody opens.
- Trivy and grype disagree regularly, because their vulnerability database merges and their package-to-CPE matching differ. Running both and taking the union is defensible; running both and gating on the intersection is not.

## The gate policy, in CI

Two gates, deliberately at different strictness.

```yaml
# .github/workflows/pr.yml — fast, blocks only on fixable CRITICAL
- name: Lint Dockerfile
  run: hadolint --failure-threshold warning Dockerfile

- name: Scan (PR gate)
  run: |
    trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 \
      --scanners vuln,secret,misconfig --ignorefile .trivyignore.yaml \
      --vex ./vex/ "$IMAGE"

- name: Report everything else without blocking
  run: |
    trivy image --severity MEDIUM,HIGH --exit-code 0 \
      --format sarif --output trivy.sarif "$IMAGE"
- uses: github/codeql-action/upload-sarif@v3
  with: { sarif_file: trivy.sarif }
```

```yaml
# .github/workflows/release.yml — fixable HIGH+CRITICAL, secrets, signature
- name: Scan (release gate)
  run: |
    trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
      --scanners vuln,secret,misconfig --ignorefile .trivyignore.yaml \
      --vex ./vex/ "$IMAGE@$DIGEST"

- name: Sign and attest
  env: { COSIGN_YES: "true" }
  run: |
    cosign sign "$IMAGE@$DIGEST"
    cosign attest --predicate sbom.cdx.json --type cyclonedx "$IMAGE@$DIGEST"

- name: Verify what we just published
  run: |
    cosign verify \
      --certificate-identity-regexp "^https://github\.com/${GITHUB_REPOSITORY}/\.github/workflows/release\.yml@refs/tags/" \
      --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
      "$IMAGE@$DIGEST"
```

The release job needs `permissions: { contents: read, packages: write, id-token: write }`; `id-token: write` is what makes keyless signing possible.

Why the asymmetry. A PR gate that blocks on every fixable HIGH fires on base-image CVEs that have nothing to do with the change under review, several times a week. Within a month someone adds a bypass label, and then the gate is decorative — worse than absent, because dashboards now show a control that is not operating. Blocking releases on fixable HIGH is tolerable because releases are less frequent, the fix is usually a base digest bump, and there is a human in the loop already.

## Exceptions with an expiry

`.trivyignore.yaml`, passed explicitly with `--ignorefile` (the YAML form is still marked experimental; the legacy plain-text `.trivyignore` is loaded automatically but supports no expiry, which is exactly the feature you need):

```yaml
vulnerabilities:
  - id: CVE-2024-12345
    statement: "Vulnerable code path is the admin CLI, not built into this image. Tracked in PLAT-4412."
    expired_at: 2026-09-30
  - id: CVE-2024-23456
    purls:
      - "pkg:deb/debian/libssl3"
    statement: "Awaiting Debian 12 security update; no upstream fix as of 2026-08-01."
    expired_at: 2026-08-31

secrets:
  - id: generic-api-key
    paths:
      - "testdata/fixtures/fake-key.txt"
    statement: "Deliberate fixture, not a live credential."
    expired_at: 2027-01-01

misconfigurations:
  - id: AVD-DS-0002
    paths:
      - "test/Dockerfile.debug"
    statement: "Debug image, never published."
    expired_at: 2026-12-31
```

Rules that keep this from decaying into an allowlist:

- Every entry has `expired_at`. Without it the ignore is permanent and nobody revisits it.
- Every entry has `statement` with a reason and a tracking reference. "Accepted risk" alone is not a reason.
- Entries are scoped with `paths` or `purls` where possible, so the suppression cannot silently cover a second occurrence of the same CVE in a different component.
- Expiry is short for "waiting on an upstream fix" (30-60 days) and longer only for a genuine non-exploitability finding — and that case belongs in VEX instead.

Grype's equivalent lives in `.grype.yaml` under `ignore:` and supports matching on vulnerability, package, and fix state, but has no expiry field. If you use grype as the gate, enforce expiry with a small CI check over the file's comments, or keep the expiring exceptions in trivy.

## VEX: asserting non-exploitability

VEX answers a different question from an ignore file. An ignore says "do not show me this". A VEX statement says "we analysed this and our product is not affected, here is the justification" — a claim you publish, that downstream consumers can consume, and that survives a change of scanner.

OpenVEX, keyed by PURL:

```json
{
  "@context": "https://openvex.dev/ns/v0.2.0",
  "@id": "https://example.com/vex/REPO-2026-08-04",
  "author": "Platform Security <security@example.com>",
  "timestamp": "2026-08-04T10:00:00Z",
  "version": 1,
  "statements": [
    {
      "vulnerability": { "name": "CVE-2024-12345" },
      "products": [
        { "@id": "pkg:oci/app@sha256:IMAGE_DIGEST" }
      ],
      "subcomponents": [
        { "@id": "pkg:golang/github.com/example/lib@v1.2.3" }
      ],
      "status": "not_affected",
      "justification": "vulnerable_code_not_in_execute_path",
      "impact_statement": "The affected parser is only reachable from the CLI entrypoint, which this image does not include."
    }
  ]
}
```

```bash
trivy image --vex ./vex/ IMAGE          # a directory of VEX documents
trivy image --vex ./app.openvex.json IMAGE
trivy sbom sbom.cdx.json --vex vex.cdx.json
```

The `not_affected` justification codes are a fixed vocabulary; use the one that is true:

| Justification | Means |
| --- | --- |
| `component_not_present` | The vulnerable component is not in the product at all |
| `vulnerable_code_not_present` | The component is there, the vulnerable code is not (e.g. removed at build) |
| `vulnerable_code_not_in_execute_path` | Present but never called |
| `vulnerable_code_cannot_be_controlled_by_adversary` | Callable, but not with attacker-influenced input |
| `inline_mitigations_already_exist` | A compensating control in the product blocks exploitation |

Other statuses are `affected` (with an `action_statement`), `fixed`, and `under_investigation`. Publishing `under_investigation` promptly is better practice than silence; it is what downstream consumers are actually asking for during an incident.

Trivy also supports CSAF documents (`--vex csaf.json`) and CycloneDX VEX, and can pull VEX from a VEX repository or from an OCI-attached attestation. CycloneDX VEX requires the scan target to be a CycloneDX SBOM; OpenVEX works against any target.

Attach the VEX to the image so consumers get it automatically:

```bash
cosign attest --predicate app.openvex.json --type openvex IMAGE@DIGEST
```

## Continuous re-scanning

The one most teams skip, and the one that catches the most real exposure. Build-time scanning covers the CVEs known at build time; everything disclosed afterwards affects a running image nobody is looking at.

```yaml
# .github/workflows/rescan.yml
on:
  schedule: [{ cron: "0 6 * * *" }]
jobs:
  rescan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Scan every tag currently deployed
        run: |
          set -euo pipefail
          for ref in $(cat deployed-images.txt); do
            trivy image --severity HIGH,CRITICAL --ignore-unfixed \
              --ignorefile .trivyignore.yaml --vex ./vex/ \
              --format json --output "scan-$(echo "$ref" | tr '/:@' '_').json" "$ref" || true
          done
      - name: Page on new fixable findings
        run: ./ci/diff-and-alert.sh   # compares against yesterday, alerts only on new IDs
```

Design points:

- **Scan what is deployed, not what is in the registry.** The list of live digests comes from the cluster (`kubectl get pods -o jsonpath` over `.status.containerStatuses[*].imageID`) or from your deployment records. Scanning 400 abandoned tags produces noise nobody reads.
- **Alert on the delta**, not the total. A daily "you have 37 vulnerabilities" message is ignored within a week; "CVE-2026-XXXX, fixable, appeared today in payments-api" is actioned.
- **Route to on-call**, not to a dashboard or a shared inbox. If the finding cannot page someone, the re-scan is a compliance artifact rather than a control.
- Scanning stored `sbom.syft.json` files with grype is a cheaper variant that also works for images already evicted from the builder cache and for registries you cannot pull from in CI.
- Also re-scan **base images** on a schedule and open a digest-bump PR when a fix lands. Renovate does most of this if the base is digest-pinned.

## Signing and attestation

Keyless, using the CI job's OIDC identity:

```bash
export COSIGN_YES=true
DIGEST=$(docker buildx imagetools inspect "$IMAGE:$TAG" --format '{{.Manifest.Digest}}')

cosign sign "$IMAGE@$DIGEST"
cosign attest --predicate sbom.cdx.json --type cyclonedx "$IMAGE@$DIGEST"
cosign attest --predicate app.openvex.json --type openvex "$IMAGE@$DIGEST"
```

Always sign the **digest**, never the tag. Signing `IMAGE:v1.2.3` binds the signature to whatever that tag pointed at when the command ran; the tag can be moved afterwards and the signature will appear to cover the new content only if verification also resolves through the tag, which is precisely the gap.

For a multi-arch index, `cosign sign` covers the index. Add `--recursive` to additionally sign each per-architecture manifest, which is what admission controllers that resolve to a platform-specific digest will look for.

`--type` accepts `slsaprovenance`, `slsaprovenance1`, `spdx`, `spdxjson`, `cyclonedx`, `vuln`, `openvex`, `link`, `custom`, or a predicate-type URI.

The GitHub-native alternative, which stores the attestation in GitHub rather than the registry:

```yaml
permissions: { id-token: write, attestations: write, contents: read }
steps:
  - uses: actions/attest-build-provenance@v1
    with:
      subject-name: ghcr.io/OWNER/REPO
      subject-digest: ${{ steps.push.outputs.digest }}
      push-to-registry: true
```

```bash
gh attestation verify oci://ghcr.io/OWNER/REPO@"$DIGEST" --repo OWNER/REPO
```

## Verification, with a pinned identity

```bash
cosign verify \
  --certificate-identity-regexp '^https://github\.com/OWNER/REPO/\.github/workflows/release\.yml@refs/tags/v' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/OWNER/REPO@"$DIGEST"

cosign verify-attestation \
  --type cyclonedx \
  --certificate-identity-regexp '^https://github\.com/OWNER/REPO/\.github/workflows/release\.yml@refs/tags/v' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/OWNER/REPO@"$DIGEST"
```

A `cosign verify` without `--certificate-identity`/`--certificate-identity-regexp` and `--certificate-oidc-issuer` is rejected for keyless flows precisely because it would prove nothing: Fulcio issues certificates to any authenticated identity, so "this image is signed" is true of anything an attacker publishes. What you are asserting is "signed by *that* workflow, in *that* repository, on a tag ref, via *that* issuer".

Anchor the regexp with `^` and escape the dots. `--certificate-identity-regexp 'github.com/OWNER/REPO'` matches `evil-github.com/OWNER/REPO-fork` because `.` is a wildcard and the pattern is unanchored — a real and easily-made mistake.

## Admission control

Signing without cluster-side verification produces an artifact nobody checks. Enforce at admission with one of:

**Sigstore Policy Controller:**

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: ghcr-signed-by-release-workflow
spec:
  images:
    - glob: "ghcr.io/OWNER/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subjectRegExp: "^https://github\\.com/OWNER/[^/]+/\\.github/workflows/release\\.yml@refs/tags/v.*$"
        ctlog:
          url: https://rekor.sigstore.dev
```

**Kyverno:**

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-images
spec:
  validationFailureAction: Enforce
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-ghcr
      match:
        any: [{ resources: { kinds: [Pod] } }]
      verifyImages:
        - imageReferences: ["ghcr.io/OWNER/*"]
          mutateDigest: true
          required: true
          attestors:
            - entries:
                - keyless:
                    issuer: https://token.actions.githubusercontent.com
                    subject: "https://github.com/OWNER/*/.github/workflows/release.yml@refs/tags/*"
                    rekor: { url: https://rekor.sigstore.dev }
```

`mutateDigest: true` rewrites the pod spec's tag to the resolved digest, which closes the tag-mutation gap at admission time. **Connaisseur** is the third option, useful when you want a standalone webhook without adopting a general policy engine.

Roll out in audit mode first (`validationFailureAction: Audit`, or Policy Controller's `warn` mode) for at least one full release cycle. An enforcing image policy that misfires blocks every deployment in the namespace, including the one that would fix it.

Pair the signature policy with the `restricted` Pod Security Standard on the namespace, since a verified image running as root is still a verified image running as root:

```bash
kubectl label namespace prod \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest
```

## SLSA levels, honestly

| Level | Requirement | How you get it |
| --- | --- | --- |
| L1 | Provenance exists and is published | `--provenance=mode=min`, any builder |
| L2 | Provenance is generated by a hosted build platform, signed, and not forgeable by the build steps | `--provenance=mode=max` on GitHub-hosted runners or an equivalent hosted builder, or `actions/attest-build-provenance` |
| L3 | L2, plus the platform prevents build steps from accessing provenance signing keys, and isolates runs from one another | `slsa-framework/slsa-github-generator` reusable workflows, or a hardened self-hosted builder with enforced isolation and out-of-band signing |

The distinction that gets misstated: L3's extra requirements are properties of the *build platform*, not of a flag on the build command. A self-hosted runner with a persistent workspace and repository secrets exposed to build steps does not reach L3 no matter what `--provenance` is set to; arguably it does not reach L2 either, since a malicious build step could tamper with the provenance generation. If someone needs a defensible L3 claim, the reusable-workflow route is the practical answer.

Inspect what you actually produced before claiming anything:

```bash
docker buildx imagetools inspect IMAGE --format '{{ json .Provenance }}' | jq '.SLSA.buildType, .SLSA.invocation.configSource'
```

`mode=max` includes the full materials list, build arguments, and source of every step; `mode=min` includes only the build definition and the top-level materials. Use `max` unless a build argument would leak something — and if one would, that is the bug to fix.

## What to record for an audit

Keep these per release, with the same retention as the image itself:

- Image reference **by digest**, plus the git commit it was built from.
- The Dockerfile as built, and the resolved base image digests.
- `sbom.cdx.json` and `sbom.syft.json`.
- Scanner output at gate time, including which findings were suppressed and by which `.trivyignore.yaml` entry or VEX statement.
- The provenance attestation and the verification command that succeeded, with its identity constraints.
- The rescan history for the image, so "when did we learn about this CVE" has an answer.
