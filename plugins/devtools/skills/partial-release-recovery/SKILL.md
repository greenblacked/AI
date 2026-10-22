---
name: partial-release-recovery
description: "Recovers a release that stopped halfway, with some artefacts published and others not. Lists each step (registry, tag, GitHub release, image, docs) with its state and whether it can be undone, treats registries as append-only so a bad or half-finished version is rolled forward and the old one marked (npm deprecate, cargo yank, PyPI yank, go.mod retract), finishes idempotent steps only when the digest matches the tested build, then puts the irreversible step last. Use when someone says \"npm publish worked but the tag push failed\", \"pypi says that file already exists\", \"the image went out but the release job died\", \"we published a broken version, can we delete it\" or \"re-run the release workflow safely\". Not for release note content (release-notes), gradual rollout (release-strategy), workflow security (pipeline-hardening), or app store binaries (mobile-release)."
allowed-tools: "Read, Grep, Glob, Edit, Bash(git ls-remote:*), Bash(git tag --list:*), Bash(git log:*), Bash(gh release view:*), Bash(npm view:*), Bash(docker buildx imagetools inspect:*), Bash(go list:*), Bash(sha256sum:*)"
---

# Partial Release Recovery

Done means every release channel is in a known state, the published artefacts are the tested build, the bad or half-finished version is marked so nobody installs it by accident, and the pipeline order has changed so the same failure costs a re-run instead of a version number.

A release is several writes to several systems, and any of them can fail after the earlier ones succeeded. The instinct is to delete what went out and start again, which works for a git tag and almost nothing else. Public registries are append-only in practice, so the real choices are to finish what is missing or to roll forward, and the mistake is to pick by reflex instead of by the state of each channel.

## Scope

Use for: a publish that succeeded while the tag, GitHub release or image push failed (or the reverse), a registry refusing a re-upload, a broken version already published, and a release workflow that must be re-run after a partial run.

Do not use for: what the release notes should say (`release-notes`), staged exposure of a good release to users (`release-strategy`), securing the release workflow itself (`pipeline-hardening`), or store submissions for mobile binaries (`mobile-release`).

## Workflow

### 1. Freeze and inventory

Stop further runs of the release workflow so a retry cannot race your investigation. Then build a table with one row per step, reading the state from the system itself rather than from the job log.

| Step | Check | Undoable? |
| --- | --- | --- |
| Registry package | `npm view pkg@x.y.z` / the project page on the index / the crate page on crates.io / `go list -m -versions` | Rarely; see step 2 |
| Git tag | `git ls-remote --tags origin vx.y.z` | Yes, but see below |
| GitHub release | `gh release view vx.y.z` | Yes |
| Container image | `docker buildx imagetools inspect repo:x.y.z` | Tags are mutable, digests are not |
| Docs site, changelog commit | Look at the site and `git log` | Yes |

For each published artefact, record the digest or checksum. `references/channel-rules.md` has the per-registry facts and the commands to read a published file's hash.

### 2. Know what each registry allows

- **npm.** A published version number cannot be reused, even after `npm unpublish`; unpublish is also limited by age and dependents. Mark a bad version with `npm deprecate pkg@x.y.z "message"` and publish the next patch.
- **PyPI.** A filename once used cannot be uploaded again, even if the file was deleted. Yank a release through the project's management page so installers skip it unless pinned exactly; publish a new version.
- **crates.io.** `cargo yank --version x.y.z` stops new resolutions while keeping existing lockfiles working; it does not delete.
- **Maven Central.** Immutable. Release a new version.
- **Go.** The module proxy keeps what it has fetched. Add a `retract` directive to `go.mod` in a new version and tag that.
- **Container registries.** Tags move. Re-tagging is possible but anyone who pulled by tag has the old image; prefer a new version tag and pin consumers by digest.

The consequence: a bad version cannot be taken back, only superseded and marked.

### 3. Choose per channel: finish or roll forward

Finish a missing step by hand only when all of these hold: the published artefact's digest equals the digest of the build that passed tests, the missing step is idempotent (creating a tag or a GitHub release, uploading a missing file), and the commit to tag is the one actually built. Check the third explicitly; a tag on a later `main` commit publishes source that does not match the artefact.

Roll forward when the published artefact is wrong, differs from the tested build, or its provenance is unclear. Fix, bump the patch, run the whole pipeline, and mark the old version with the deprecate or yank step above. Resist deleting the old git tag: users and lockfiles may reference the commit it points at.

### 4. Complete and verify

Perform the chosen actions, then re-read every row of the inventory and confirm the final state matches intent. Install the published version in a clean directory and run a smoke test against it; the registry listing existing is not evidence that it works.

### 5. Fix the pipeline order

The failure happened because an irreversible step ran before a step that could fail. Reorder:

1. Build and verify (tests, packaging checks such as `twine check`, an install test of the built artefact).
2. Create the tag, which is reversible while unpublished.
3. Publish the irreversible registry step last.
4. Follow-on steps (GitHub release, docs, notifications) must tolerate being re-run.

Make each step safe to repeat: check whether the version already exists before publishing, or use the tool's skip option (`twine upload --skip-existing`). A re-run after a partial failure then converges instead of failing at the first step that already succeeded.

## Hand back

The inventory table with final state, the decision per channel with the digest comparison that justified it, the version marked as bad and how, the commit each tag points at, and the pipeline changes made or proposed.

## Anti-patterns

**Unpublishing to reuse the number.** Registries refuse it, and a window where the artefact vanished breaks installs for dependents.

**Tagging the current head.** The tag must name the commit that was built, or the source and the artefact disagree for ever.

**Re-running the whole workflow blind.** The first step that already succeeded fails, or worse, publishes a second differing artefact under a mutable tag.

**Moving a published git tag.** Anything that fetched the old one keeps it, so two states carry one name.

## Reference files

- `references/channel-rules.md` — read when you need the exact lookup, checksum or yank command for a channel, or the rules for a registry not listed above.
