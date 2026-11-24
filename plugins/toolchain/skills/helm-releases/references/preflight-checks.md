# Pre-flight checks and deploy job

Contents: lint and render, schema validation, diff, a deploy job, what each check cannot
see.

Pin the versions of `helm`, `kubeconform` and the `helm-diff` plugin in the CI image, and
verify downloads against a recorded checksum rather than piping a script into a shell.
Flag names below are for current Helm 3 and should be checked against the pinned one.

## Lint and render

```bash
set -Eeuo pipefail
VALUES=(-f values.yaml -f "values-${ENV_NAME}.yaml")
helm lint ./chart --strict "${VALUES[@]}"
helm template "$REL" ./chart --namespace "$NS" --kube-version "$KUBE_VERSION" \
  --include-crds "${VALUES[@]}" > rendered.yaml
```

`helm template` does not contact the cluster. `lookup` returns empty, `.Capabilities`
reports defaults unless `--kube-version` and `--api-versions` are given, and `crds/` is
skipped without `--include-crds`. A template that branches on `lookup` therefore renders
differently in CI than in the cluster; check whether the pinned Helm offers a server-side
dry run for that case.

## Schema validation

```bash
set -Eeuo pipefail
kubeconform -strict -summary -kubernetes-version "$KUBE_VERSION" rendered.yaml
```

Without extra schemas, custom resources are skipped or fail. Add a schema location for
the CRDs in use rather than turning on `-ignore-missing-schemas` for everything, which
hides the objects most likely to be wrong. Set `-kubernetes-version` to the cluster's
version, not the newest one.

## Diff

```bash
set -Eeuo pipefail
helm diff upgrade "$REL" ./chart --namespace "$NS" "${VALUES[@]}" \
  --detailed-exitcode --context 3 || rc=$?
echo "diff exit: ${rc:-0}"
# 0 is no change and 2 is changes; anything else is a plugin or render error
case ${rc:-0} in 0|2) ;; *) exit "$rc" ;; esac
```

With `--detailed-exitcode` the plugin exits non-zero when there are changes, which a
`set -e` job reads as failure; handle the code explicitly as above and read its
documentation for the pinned version. Secret values appear in the diff unless the plugin
is told to suppress them, so do not post the raw output to a public pull request.

## Deploy job

```bash
set -Eeuo pipefail
helm upgrade --install "$REL" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$NS" --create-namespace \
  "${VALUES[@]}" \
  --wait --timeout 10m --history-max 5
helm status "$REL" --namespace "$NS"
```

Add `--atomic` only under the conditions in `SKILL.md` step 3. The CI job's own timeout
must exceed `--timeout` plus time for hooks. Key the job's concurrency on release and
namespace so two pipelines never write one release.

## What each check cannot see

| Check | Blind to |
| --- | --- |
| `helm lint` | Whether the objects are valid Kubernetes |
| `helm template` | Cluster state, admission webhooks, `lookup` results |
| `kubeconform` | Admission policy, quota, immutable-field rejections |
| `helm diff` | Live drift (unless enabled), whether the rollout will become ready |
| `--wait` | Whether the application behaves; hand that to `release-strategy` |
