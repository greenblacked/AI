# Wiring the gate into CI

Read this when adding the check. The example uses GitHub Actions, a hand-written
`openapi.yaml` at the repository root, release tags of the form `vX.Y.Z` and a
`CHANGELOG.md`. Pin each action to a full commit SHA with its exact release tag in a
comment, and replace the SHAs with the ones your repository already uses.

## Contents

- [The workflow](#the-workflow)
- [Choosing the base in CI](#choosing-the-base-in-ci)
- [The label and migration-entry condition](#the-label-and-migration-entry-condition)
- [Generated specs](#generated-specs)
- [Publishing the findings and the changelog seed](#publishing-the-findings-and-the-changelog-seed)

## The workflow

```yaml
name: api-diff
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
permissions:
  contents: read
jobs:
  diff:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Install oasdiff
        run: |
          set -Eeuo pipefail
          echo "Download the pinned oasdiff release archive, verify its recorded SHA-256, put it on PATH"
      - name: Diff against the last release
        env:
          APPROVED: ${{ contains(github.event.pull_request.labels.*.name, 'semver-major') }}
        run: |
          set -Eeuo pipefail
          if ! base_tag=$(git describe --tags --abbrev=0 --match 'v[0-9]*' HEAD^1 2>/dev/null); then
            echo "No release tag yet, so there is no released contract to break. Breaking-change check skipped." >> "$GITHUB_STEP_SUMMARY"
            exit 0
          fi
          if ! git show "$base_tag:openapi.yaml" > base.yaml 2>/dev/null; then
            echo "openapi.yaml does not exist at $base_tag (new API or moved file). Breaking-change check skipped." >> "$GITHUB_STEP_SUMMARY"
            exit 0
          fi
          {
            echo "## API diff against $base_tag"
            echo '```text'
            oasdiff breaking base.yaml openapi.yaml
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"
          if oasdiff breaking base.yaml openapi.yaml --fail-on ERR > /dev/null; then
            exit 0
          fi
          if [ "$APPROVED" != "true" ]; then
            echo "::error::Breaking API change against $base_tag without the semver-major label"
            exit 1
          fi
          if ! git diff -U0 HEAD^1 HEAD -- CHANGELOG.md | grep '^+.*Migration:' > /dev/null; then
            echo "::error::Breaking API change approved but CHANGELOG.md has no Migration: entry"
            exit 1
          fi
```

The install step is a placeholder on purpose: fetch a pinned release and check it
against a recorded digest, the same way every other tool in the pipeline is installed,
rather than piping an installer into a shell or using a floating container tag.

There is no `paths:` filter. Label changes must re-run the check, which the `labeled` and
`unlabeled` types provide, and when the spec is generated from code a change to any
source file can change the contract.

The label value reaches the script through `env:`, never interpolated into the `run:`
text, so a label name cannot inject shell.

## Choosing the base in CI

With no release tag, or no spec at the last tag, the step above prints a notice to the
step summary and passes. That is deliberate: there is no released contract to break, and a
gate that fails every pull request for that reason gets disabled. It starts enforcing with
the first tag that contains the spec. Move the spec and tag in the same release, and
update the path in the step when the file moves.

On a `pull_request` event the checkout is the merge commit, so `HEAD^1` is the tip of the
base branch and `git describe` from there finds the most recent release tag on that line.
`fetch-depth: 0` is needed so tags and history are present.

That works when releases are tagged on the branch the pull request targets. When releases
are cut from release branches whose tags are not reachable from `main`, take the base
from the published artefact instead: download the spec attached to the latest release, or
read the released version from the deploy record and fetch that tag explicitly. A wrong
base is silent — the gate compares against the wrong contract and passes — so print the
base in the summary, as above, where a reviewer sees it.

For pull requests into a maintenance branch, the same logic finds that line's last
release, which is the correct base for it.

## The label and migration-entry condition

Two separate conditions, because they record different things:

- **`semver-major`** is the versioning decision. Anyone with triage access can apply
  any label, so the label alone cannot say who decided. Pair it with a required review
  from the API owners on `openapi.yaml` through `CODEOWNERS` and branch protection: the
  label records the decision, the required review enforces who made it.
- **The `Migration:` line** in the changelog diff is the evidence that someone wrote down
  what clients must do. Adjust the pattern to the changelog convention in use; a
  fragment-file convention checks for a new file of the breaking type instead.

Keep `WARN` findings visible in the summary. To make them blocking, add a second
comparison with `--fail-on WARN` and require either the label or a short written
decision in the pull request description for each.

## Generated specs

When the spec is generated from code, replace the `git show` step with generation at
both revisions using the same generator version:

```bash
set -Eeuo pipefail
git worktree add ../base "$base_tag"
(cd ../base && make -B openapi.yaml)   # whatever target or command generates the spec
make -B openapi.yaml
oasdiff breaking ../base/openapi.yaml openapi.yaml --fail-on ERR
```

`-B` matters: the file already exists on both sides, and without it `make` reports the
target up to date and leaves the stale committed copy in place, so the gate compares two
old documents and passes.

Add a separate check that regenerates the committed spec and fails on any difference
(`git diff --exit-code -- openapi.yaml`), so the published file can never lag the code.

## Publishing the findings and the changelog seed

The step summary above shows the breaking findings on every run. For the release
changelog, run the full changelog between the last release and the release candidate:

```bash
oasdiff changelog base.yaml openapi.yaml > api-changelog.txt
oasdiff changelog base.yaml openapi.yaml --format json > api-changelog.json
```

Attach the text to the release pull request as the API section's starting point. Every
line becomes an entry rewritten for the reader, and every breaking line must match a
`Migration:` entry already in the changelog. A breaking line with no matching migration
means the gate was bypassed somewhere, which is worth finding before the release rather
than after.
