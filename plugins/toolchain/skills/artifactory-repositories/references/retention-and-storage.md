# Retention and storage

Read when writing a cleanup policy, building an AQL selection, or explaining why disk
usage did not fall after a delete. Cleanup features, trash-can behaviour and garbage
collection scheduling differ by version and licence tier; check the official docs for
the pinned version first and record it.

## Contents

- Choose what to keep
- Select with AQL, dry run first
- Why space does not return
- Growth signals

## Choose what to keep

| Class | Typical rule | Select on |
| --- | --- | --- |
| Snapshots and dev builds | keep the newest N or newer than a number of days | created, repo, name pattern |
| Staging candidates | keep what was promoted or is newer than a window | property `status`, created |
| Releases | keep, remove only by a reviewed decision | explicit list |
| Remote cache | let the unused-artifact setting expire it | the repository's own setting |
| Docker development tags | keep newest N tags per image | path, created |

Anything referenced by a running environment is exempt. Find those references from
the deployment records or the manifests, not from Artifactory, which cannot see them.
Mark promoted artifacts with a property at promotion so a policy can exclude them
instead of guessing from age.

## Select with AQL, dry run first

AQL is a query over items and their properties. Write the selection as a query, run it
and read the output before any delete. The shape (confirm field names against the docs):

```text
items.find({
  "repo": "maven-dev-local",
  "created": {"$before": "30d"},
  "@status": {"$ne": "promoted"}
}).include("repo", "path", "name", "created", "size")
```

Run it through the CLI search or the AQL REST endpoint, check the count and the
largest and oldest rows, and compare with the repository's total. Then delete with the
CLI's dry-run flag first (`jf rt delete --dry-run` with the same spec) and only after
reading the list run it without. Keep the spec file in version control with the
review that approved it. Run it against local repositories, not a virtual repository.

If the licence includes the built-in cleanup or retention policies, prefer them for
the standing rules and keep AQL for one-off investigations; either way a policy has a
preview or dry-run mode in current releases, which should be confirmed.

## Why space does not return

1. Deleting an artifact removes the reference. Binaries are stored by checksum and
   shared, so a file is removable only when no artifact references it.
2. If the trash can is enabled, deleted items wait there for its retention period
   and still occupy the filestore.
3. Garbage collection removes unreferenced binaries on its schedule or when run by
   an administrator; check when it last ran and what it reported.
4. Docker layers are shared across images and tags, so deleting one tag frees only
   its unique layers.
5. A filesystem or object-store filestore may free space late; check the underlying
   volume, not only the Artifactory storage summary.

To explain a full disk: read the storage summary (it may need a recalculation before
the numbers are current), rank repositories by size, then rank by artifact count in
the largest, and check the trash can and the garbage collection history before
choosing anything to delete.

## Growth signals

- A development repository with no retention rule.
- Docker repositories with a tag per commit.
- A remote repository with a long or disabled unused-artifact period.
- Build info for builds whose artifacts are long gone; the build-info retention
  setting is separate from artifact retention, check the documentation.
- A filestore volume and a database that are sized by a one-time guess.
