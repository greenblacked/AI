# Tooling

Read this in steps 2, 5 and 7, when building the inventory, writing the policy check, or
producing an SBOM. Tool flags move between releases; where a command below fails, check
the installed version's `--help` rather than guessing a replacement.

## Contents

- [Whole-artefact inventory: SBOMs](#whole-artefact-inventory-sboms)
- [Finding what no manifest declares](#finding-what-no-manifest-declares)
- [Per-ecosystem tools](#per-ecosystem-tools)
- [Queries over the output](#queries-over-the-output)
- [The policy file](#the-policy-file)
- [Wiring the gate](#wiring-the-gate)

## Whole-artefact inventory: SBOMs

Syft builds an SBOM from a directory, an archive or an image. Scanning a directory reads
lockfiles and manifests; scanning an image reads what is installed in it, operating system
packages included. Scan the artefact you ship, not only the repository it came from.

```bash
syft dir:. -o spdx-json=sbom.spdx.json -o cyclonedx-json=sbom.cdx.json
syft registry.example.com/team/app@sha256:<digest> -o spdx-json=image.spdx.json
```

Trivy reports licences with a category and severity per package. Its built-in categories
are a starting point, not your policy.

```bash
trivy fs --scanners license --format json --output licences-fs.json .
trivy image --scanners license --format json --output licences-image.json registry.example.com/team/app@sha256:<digest>
```

## Finding what no manifest declares

Package managers see only what they installed. Search the tree for licence texts and
headers, excluding installed dependency directories the manifest already covers. The Grep
tool does this without a shell; `rg` is not pre-approved because its `--pre` option runs a
command on every file it reads:

```bash
rg -l -i --hidden -g '!node_modules' -g '!.git' \
  'spdx-license-identifier|copyright \(c\)|permission is hereby granted|licensed under' .
```

Then run ScanCode over each directory that turned up vendored or copied code. It detects
licence texts, headers and copyright statements per file, which is what you need for code
that arrived without metadata.

```bash
scancode --license --copyright --info --json-pp scancode-third-party.json --processes 4 third_party/
```

Look separately for fonts (`*.woff2`, `*.ttf`, `*.otf`), icon sets, images, datasets and
model weights, which neither tool classifies as software. Each needs its licence found and
recorded by hand once, then kept in the inventory.

## Per-ecosystem tools

Each of these reads the installed or resolved dependency tree, so run it after a clean
install from the lockfile, never against a developer's working environment.

**npm.** `license-checker` reads `node_modules`. Install with `npm ci --ignore-scripts` so
no install script runs during an audit, then:

```bash
license-checker --production --json --out licences-npm.json
license-checker --production --onlyAllow 'MIT;ISC;BSD-2-Clause;BSD-3-Clause;Apache-2.0;0BSD'
```

`--production` drops development dependencies, so check separately for any that are
bundled into the output (step 2). pnpm has a built-in `pnpm licenses list` that reads its
own store.

**Python.** `pip-licenses` reports what is installed in the active environment, itself
included. Build a fresh virtual environment, install exactly what the lock resolves, add
`pip-licenses`, and drop its own entries from the result:

```bash
pip-licenses --from=mixed --format=json --with-urls --with-license-file --no-license-path --output-file licences-py.json
```

It reports licence names from package metadata and classifiers, not SPDX identifiers, so
normalise before comparing with the policy. Its `--allow-only` and `--fail-on` options
take semicolon-separated names in that same form.

**Go.** `go-licenses` follows the import graph of the packages you name, so it reports
what is linked into the binary — exactly the shipped scope. It does not see C code pulled
in through cgo; inventory that separately.

```bash
go-licenses report ./... > licences-go.csv
go-licenses check ./... --allowed_licenses=MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC
go-licenses save ./... --save_path=third_party_licences
```

`save` copies licence files and, for licences that require it, the source — a starting
point for the corresponding-source archive.

**Rust.** `cargo-deny` enforces a licence allowlist from `deny.toml`, and `cargo-about`
generates the notices file from a template.

```toml
[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC"]
confidence-threshold = 0.93
```

```bash
cargo deny check licenses
cargo about init
cargo about generate about.hbs > THIRD-PARTY-NOTICES.html
```

Per-crate exceptions go under `[[licenses.exceptions]]`; the key names have changed between
cargo-deny releases, so take them from the documentation for your version.

**JVM.** The Maven licence plugin and Gradle's dependency licence report plugins both
produce a third-party report from the resolved graph. Alternatively run syft on the built
JAR or image, which reads the Maven metadata embedded in the archives.

## Queries over the output

Syft's SPDX output also lists the scanned directory or image itself as a package whose
SPDXID starts with `SPDXRef-DocumentRoot-` and whose declared licence is `NOASSERTION`. It is
not a dependency, so every query below leaves it out; otherwise the unknowns query would fail
on every run and the empty-inventory check could never fail. Check the SPDXIDs in your own
syft output before relying on the prefix.

List every package with its declared and concluded licence from an SPDX SBOM:

```bash
jq -r '.packages[] | select(.SPDXID | startswith("SPDXRef-DocumentRoot-") | not) | [.name, .versionInfo, (.licenseDeclared // "NONE"), (.licenseConcluded // "NONE")] | @tsv' sbom.spdx.json
```

The unknowns that block (step 3). The bare `jq` form below only lists; wired into CI it exits 0
whether or not it prints anything. For the gate, capture the output and fail when it is not
empty:

```bash
out=$(jq -r '.packages[] | select(.SPDXID | startswith("SPDXRef-DocumentRoot-") | not) | select((.licenseDeclared // "NOASSERTION") | IN("NOASSERTION", "NONE")) | "\(.name)@\(.versionInfo)"' sbom.spdx.json) \
  && { test -z "$out" || { printf '%s\n' "$out"; exit 1; }; }
```

Apply the same wrapper to each blocking query below (the allowlist query and the CycloneDX
unknowns query); the listing queries stay bare.

Everything not on a flat allowlist. Compound expressions are reported too, so a person
resolves each `OR` choice once and records it — the conservative failure:

```bash
jq -r --argjson allow '["MIT","ISC","BSD-2-Clause","BSD-3-Clause","Apache-2.0","0BSD"]' \
  '.packages[] | select(.SPDXID | startswith("SPDXRef-DocumentRoot-") | not) | select(.licenseDeclared | IN($allow[]) | not) | "\(.name)@\(.versionInfo)\t\(.licenseDeclared)"' sbom.spdx.json
```

The same listing from a CycloneDX SBOM, where a component's licences may be an id, a name
or an expression:

```bash
jq -r '.components[] | [.name, .version, ([.licenses[]? | .license.id // .license.name // .expression] | join(" | "))] | @tsv' sbom.cdx.json
```

A component with no `licenses` array prints an empty last column; that is an unknown and
blocks like any other. Select them explicitly so the gate does not rely on reading a column:

```bash
jq -r '.components[] | select(([.licenses[]? | .license.id // .license.name // .expression] | length) == 0) | "\(.name)@\(.version)"' sbom.cdx.json
```

Count the packages before trusting an empty result. `jq` prints nothing for an SBOM whose
package list is empty, which is what a scan of the wrong directory or a failed build looks
like, so the gate fails when the inventory has no components at all, not counting the document root:

```bash
test "$(jq '[.packages[] | select(.SPDXID | startswith("SPDXRef-DocumentRoot-") | not)] | length' sbom.spdx.json)" -gt 0
```

## The policy file

Keep one policy in the repository and have every ecosystem check read from it or be
generated from it, so the allowlist cannot drift between languages. A shape that carries
everything step 5 needs:

```yaml
# licence-policy.yaml
allowed: [MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, Zlib, 0BSD]
conditional:
  - licence: LGPL-3.0-only
    modes: [shipped]
    condition: dynamically linked; library source archived per release
  - licence: MPL-2.0
    modes: [browser, shipped]
    condition: source of covered files available, recipients told where
counsel: [AGPL-3.0-only, AGPL-3.0-or-later, BUSL-1.1, SSPL-1.0]
exceptions:
  - package: example-lib
    version: 2.4.1
    licence: GPL-2.0-only
    artefact: api-server
    mode: hosted
    reason: runs only on our servers; never shipped in the on-premises build
    approved_by: <name, role>
    approved_on: 2026-01-15
    review_by: 2026-07-15
```

An exception matches on package name and exact version together. A check that matches on
name alone lets the next release through on an approval that was never given for it.

## Wiring the gate

- Run on changes to lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`,
  `poetry.lock`, `uv.lock`, pinned requirements files, `go.sum`, `Cargo.lock`), to vendored
  directories, and to image definitions; and on every release build regardless of paths.
- Fail closed: a package passes only when its licence is allowed, or conditional for this
  artefact's mode with the condition recorded, or covered by a matching unexpired
  exception; anything else fails the job. An expired exception fails it too, which is how
  review dates get honoured.
- Print the package, version, licence and dependency path for each failure.
- On a release, publish the SBOM and the generated notices file as release assets beside
  the artefact, so the answer to a customer's request is a link to what was built.
- For a front-end bundle, check the built output directory for the licence comments or the
  extracted licence file after the build, since the bundler configuration is not evidence
  that notices survived minification.
