# Pre-publish checklist and release day

Read this at step 7 of the workflow, and again when a published release has to be yanked or
amended. Every item is verified against the repository and the artefact, not from memory.

## Contents

- [The checklist, with a verification for each item](#the-checklist-with-a-verification-for-each-item)
- [Release-day sequence](#release-day-sequence)
- [When the release is already published and wrong](#when-the-release-is-already-published-and-wrong)

## The checklist, with a verification for each item

| Item | Verification | Why it stops the publish |
| --- | --- | --- |
| Version bumped everywhere it appears | Search the tree for the previous version string; manifest, lockfile, vendored copies, container labels and generated files all have to agree | A version that disagrees with itself makes every support conversation start with establishing what the user is running |
| Tag exists and points at the built commit | `git rev-parse v2.4.0^{commit}` compared with the revision the build recorded | A tag that points elsewhere makes every future range derivation wrong and unreproducible |
| Tag has never been moved or recreated | `git tag -v` where tags are signed, or the tag's creation record in the forge | A moved tag returns different content to different people depending on when they fetched |
| The artefact is the tested one | Compare the digest or checksum of the promoted artefact with the one the test run recorded | A rebuild between test and publish ships something that was never tested |
| Every breaking change carries its migration | Read the Action required section against the range, entry by entry | A reader who knows they are affected and not what to do delays the upgrade indefinitely |
| Migration read by someone who did not write it | A named reviewer on the notes, not only on the code | The author cannot see the step they performed from memory and omitted |
| Rollback stated | The Upgrade section names the previous version and says whether downgrade is supported | Silence is read as yes, and acted on during an incident |
| Irreversibility named where it exists | Check for schema contraction, format changes and one-way external effects in the range | This is the single most valuable sentence in the document when it applies |
| Minimum versions and dependency floors stated | Diff the manifest's engine and dependency constraints against the previous tag | An upgrade that fails on an unchanged deployment needs to fail for a stated reason |
| Security fixes carry severity and affected versions | Each security entry has both | An operator must be able to judge urgency without reading the diff |
| Range reconciled against the deploy record | Compare tags with what production actually received, including maintenance branches | Hotfixes shipped from another branch are otherwise reported as new |
| Links resolve, nothing references a reverted change | Follow every link; check the range for reverts | A note describing a change that was backed out is worse than no note |

## Release-day sequence

Order matters because each step makes the next one verifiable.

1. Freeze the range. Nothing further merges into the release branch; late changes go to
   the next version rather than into the artefact that was tested.
2. Build once. Record the digest. Everything downstream refers to this digest.
3. Run the full test suite against that artefact, not against a source tree.
4. Bump the version, commit, and tag that commit. The tag is created once and never moved.
5. Write and review the notes against the frozen range.
6. Publish the artefact by promoting the digest, not by rebuilding.
7. Publish the notes at the same time as the artefact. Notes that arrive later are read by
   nobody, because the upgrade has already happened or already failed.
8. Watch the first upgrades. The rollback stated in the notes is now the plan, so confirm
   somebody is positioned to execute it.

## When the release is already published and wrong

- **Do not move the tag and do not re-upload the artefact.** Both leave two different
  things sharing one version, which is worse than the original defect and unfixable
  afterwards.
- **Yank or deprecate the version** where the registry supports it, so new consumers do
  not pick it up, and existing pinned consumers keep resolving.
- **Ship a new patch version** with the fix, and a note in the new release naming the
  version that was withdrawn and why.
- **Amend the notes in place only for factual corrections** — a wrong link, a missing
  migration step, an omitted affected version. Record that the document was amended and
  when, because readers who acted on the earlier text need to know it changed.
- **Announce through the channel the affected readers use**, not only in the notes. A
  correction that lives solely in the document is invisible to everyone who already read
  it.
