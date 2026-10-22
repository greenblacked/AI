# Channel rules and checks

## Contents

- Reading what was published
- Comparing against the tested build
- Marking a bad version
- Idempotent re-run patterns
- A worked example

## Reading what was published

```bash
npm view pkg versions --json                 # is the version there
npm view pkg@1.2.3 dist.integrity dist.shasum
git ls-remote --tags origin v1.2.3           # empty output means no tag on the remote
gh release view v1.2.3                       # errors if there is no release
docker buildx imagetools inspect repo/name:1.2.3   # digest and platforms
go list -m -versions example.com/module      # versions the proxy knows
```

For PyPI, the project's JSON page at `https://pypi.org/pypi/NAME/VERSION/json` lists each uploaded file with its `digests`. Reading it is a request you make, not something to script blindly into a decision.

## Comparing against the tested build

Keep the artefact CI built and tested (the workflow's uploaded artefact or the local `dist/`). Hash it and compare with what the registry reports.

```bash
npm pack --pack-destination /tmp/check pkg@1.2.3   # downloads the published tarball
sha256sum /tmp/check/*.tgz dist/*.tgz
pip download pkg==1.2.3 --no-deps -d /tmp/check
```

A tarball rebuilt on another machine often differs in file order or timestamps even from identical source; a mismatch is a prompt to look, and the registry integrity value from the tested build's own publish log is the better comparison when it exists. If the build is not reproducible, compare the file lists and contents with `diff -r` on the unpacked trees instead of the archive hash.

## Marking a bad version

| Registry | Action | Effect |
| --- | --- | --- |
| npm | `npm deprecate pkg@1.2.3 "reason, use 1.2.4"` | Warning on install; still installable |
| crates.io | `cargo yank --version 1.2.3` (`--undo` reverses) | Excluded from new resolution; lockfiles still work |
| PyPI | Yank the release on the project's management page | Skipped by installers unless pinned exactly |
| Go | `retract v1.2.3 // reason` in a later version's go.mod | Tooling warns and `go get` avoids it |
| Maven Central | None; publish a fixed version and document | Old version stays resolvable |
| Container image | Publish a fixed tag; note the bad digest in the release | Old digest remains pullable |

Give a reason that names the fixed version, since the deprecation text is what a user reads.

## Idempotent re-run patterns

- Before publish: query the registry for the version and skip when present and the digest matches.
- `twine upload --skip-existing dist/*` skips files already on the index.
- Tag creation: check `git ls-remote --tags origin` first; create only when absent and never force.
- GitHub release: view first; use the edit form when it exists.
- Container push by version tag only after confirming the tag is unused, or push by digest and tag separately.

## A worked example

A workflow ran: tests, npm publish (succeeded), push tag (failed on a protected-ref rule), GitHub release (skipped).

1. Inventory: npm has 2.4.0, no tag, no release.
2. Digest: the published tarball's integrity matches the CI artefact.
3. Decision: finish. The tag step is idempotent and the artefact is the tested one.
4. Find the built commit from the workflow run, tag exactly that commit, create the release against the tag.
5. Pipeline: move the tag creation before publish, and make publish check for an existing version.
