# Release states and errors

Contents: release status table, error messages and fixes, rollback limits, hook failures,
adopting existing objects.

Check each command against the pinned Helm version; messages and flags vary between
minor versions.

## Release status table

| Status | Meaning | Usual cause | Recovery |
| --- | --- | --- | --- |
| `deployed` | Current live revision | Normal | None |
| `superseded` | Older revision replaced by a newer one | Normal | A valid rollback target |
| `failed` | The operation returned an error | Timeout, bad manifest, rejected object, failed hook | Read the error, fix, upgrade again; or roll back |
| `pending-install` | First install started, never finished | CI job cancelled or runner killed | Confirm nothing runs, then `helm uninstall`, reinstall |
| `pending-upgrade` | Upgrade started, never finished | Same | Confirm nothing runs, then `helm rollback` to the last good revision |
| `pending-rollback` | Rollback started, never finished | Same | Confirm nothing runs, then roll back again to a good revision |
| `uninstalling` | Uninstall in progress or interrupted | Hook or finalizer stuck | Find the blocking hook or object; retry uninstall |
| `uninstalled` | Removed with `--keep-history` | Intended | Can be rolled back from |

List the pending and failed ones across a cluster with
`helm list --all-namespaces --pending` and `helm list --all-namespaces --failed`.

## Errors

| Message (abridged) | What it means | Fix |
| --- | --- | --- |
| `another operation (install/upgrade/rollback) is in progress` | Newest revision is pending | Prove the writer is dead, then recover as above |
| `has no deployed releases` | Every revision is `failed`, so `upgrade` has nothing to diff against | `helm uninstall` the failed first install, or `rollback` if an earlier good revision exists |
| `cannot reuse a name that is still in use` | `install` on an existing name | Use `upgrade --install`, or choose another name |
| `exists and cannot be imported into the current release: invalid ownership metadata` | An object the chart renders exists but Helm did not create it | See Adopting objects |
| `field is immutable` | The upgrade changes a field Kubernetes forbids changing | Recreate the object deliberately (delete it, or use a new name), after checking data impact |
| `resource mapping not found ... no matches for kind` during upgrade or rollback | The stored manifest uses an API version the cluster no longer serves | Use the `mapkubeapis` plugin, installed at a pinned, reviewed version, or update the record per its docs; plan this before a cluster upgrade (`k8s-upgrade`) |
| `context deadline exceeded` / `timed out waiting for the condition` | `--wait` or a hook exceeded `--timeout` | Find the unready object with `kubectl get` and events, not by raising the timeout first |
| `Request entity too large` or a Secret size error | The release record is too big for the datastore | Shrink values and chart contents; lower `--history-max` |

## Rollback limits

`helm rollback REL REVISION` creates a new revision from the stored manifest of REVISION.
Check `helm history` for the right number: the previous revision is often another `failed`
one. A rollback does not:

- run the reverse of a `pre-upgrade` or `post-upgrade` hook, so a schema migration stays
- restore PVC contents, or recreate a PVC deleted by policy
- touch CRDs in `crds/`
- remove objects a hook created that carry no delete policy

If the failed revision changed data, restore the data by the system's own procedure, then
roll back the manifests.

## Hook failures

A hook Job or Pod that fails fails the whole operation, and Helm waits for it up to
`--timeout`. Hook objects are not tracked as release objects, so `helm uninstall` leaves
them unless a delete policy removes them. Use `helm.sh/hook-delete-policy`:
`before-hook-creation` clears the previous run's object before creating the next,
`hook-succeeded` removes on success, `hook-failed` removes on failure (which also removes
the logs you wanted). Capture hook logs from the pod before the policy deletes it.
Use `helm.sh/hook-weight` to order hooks of the same kind.

## Adopting existing objects

To bring an object created outside Helm under a release, add the labels and annotations
Helm checks, then run the upgrade or install:

```bash
set -Eeuo pipefail
kubectl label "$KIND/$NAME" --namespace "$NS" app.kubernetes.io/managed-by=Helm
kubectl annotate "$KIND/$NAME" --namespace "$NS" \
  meta.helm.sh/release-name="$REL" meta.helm.sh/release-namespace="$NS"
```

To make Helm leave an object behind on uninstall, annotate it in the template with
`helm.sh/resource-policy: keep`.
