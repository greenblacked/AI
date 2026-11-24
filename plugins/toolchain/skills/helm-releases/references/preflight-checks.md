# Pre-flight checks and deploy job

## Contents

Resolve the chart, lint and render, schema validation, diff, a deploy job, what each
check cannot see.

Pin the versions of `helm`, `kubeconform` and the `helm-diff` plugin in the CI image, and
verify downloads against a recorded checksum rather than piping a script into a shell.
Flag names below are for current Helm 3 and should be checked against the pinned one.

## Resolve the chart

```bash
set -Eeuo pipefail
if [[ -n "${CHART_REF:-}" ]]; then
  # A published chart: pull the pinned version once and unpack it into the workspace.
  # CHART_NAME is the chart's name as packaged, the last path element of the reference.
  helm pull "$CHART_REF" --version "$CHART_VERSION" --untar --untardir build
  CHART="build/${CHART_NAME}"
else
  # A chart kept in this repository.
  CHART=./chart
fi
```

Set `CHART_REF` for a published chart; leave it unset for a chart kept in this
repository. Every check below and the deploy use that same `$CHART`, so the gates test
exactly what is installed. Resolve it in the same job as the deploy, or pass the pulled
directory between jobs as an internal artifact. Where the registry and Helm support it,
add `--verify` to the pull.

## Lint and render

```bash
set -Eeuo pipefail
VALUES=(-f values.yaml -f "values-${ENV_NAME}.yaml")
helm lint "$CHART" --strict "${VALUES[@]}"
helm template "$REL" "$CHART" --namespace "$NS" --kube-version "$KUBE_VERSION" \
  --include-crds "${VALUES[@]}" > rendered.yaml
```

`rendered.yaml` holds any Secret the chart renders, so do not upload it as an artifact or
print it, and keep `--debug` or `--dry-run` output out of shared job logs for the same
reason.

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
helm diff upgrade "$REL" "$CHART" --namespace "$NS" "${VALUES[@]}" \
  --detailed-exitcode --context 3 --suppress-secrets || rc=$?
echo "diff exit: ${rc:-0}"
# 0 is no change and 2 is changes; anything else is a plugin or render error
case ${rc:-0} in 0|2) ;; *) exit "$rc" ;; esac
```

With `--detailed-exitcode` the plugin exits non-zero when there are changes, which a
`set -e` job reads as failure; handle the code explicitly as above and read its
documentation for the pinned version. Secret values appear in the diff unless the plugin
is told to suppress them. `--suppress-secrets` hides Secret data, so keep it on by
default in CI: the job log is readable by everyone who can read logs, not only by the
pull request's audience. Check that the pinned plugin version supports the flag. If
someone needs an unsuppressed diff, run it locally or in a job whose logs are
restricted, never in shared CI output.

## Deploy job

```bash
set -Eeuo pipefail
helm upgrade --install "$REL" "$CHART" \
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
