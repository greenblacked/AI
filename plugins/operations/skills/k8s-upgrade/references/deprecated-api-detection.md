# Deprecated and removed API detection

Read this at step 2, before scheduling the control-plane upgrade. The goal is a list of
every deprecated or removed API still being requested against the live cluster, each
with an owner and a merged fix, or a confirmed explanation for why it is stale.

## Contents

- [The metric](#the-metric)
- [The audit-log fallback](#the-audit-log-fallback)
- [kubent and pluto as a second opinion](#kubent-and-pluto-as-a-second-opinion)
- [Reading a provider's removal notes](#reading-a-providers-removal-notes)

## The metric

`kube-apiserver` exposes `apiserver_requested_deprecated_apis`, a Prometheus gauge in the
`apiserver` subsystem. Its labels name the group, version, resource and the release that
removes it:

```promql
apiserver_requested_deprecated_apis{removed_release="1.29"}
```

That query alone answers "what breaks at the target version." To see who is actually
calling it, cross-reference with the audit log or with `apiserver_request_total` sliced
by `group`, `version` and `resource`, filtered to the same deprecated combinations, over
a window long enough to catch a weekly batch job or month-end report that only runs
rarely.

Treat a non-zero reading as real until proven otherwise. A workload that ran once during
the scrape window and never again can still be a live dependency — check its schedule
before writing it off as stale.

## The audit-log fallback

Clusters that do not retain metrics long enough (a short Prometheus retention window, or
no metrics pipeline at all) can grep the audit log directly for the same group/version
combinations:

```bash
jq -r 'select(.objectRef.apiGroup == "extensions" and .objectRef.apiVersion == "v1beta1") | "\(.requestReceivedTimestamp) \(.user.username) \(.verb) \(.objectRef.namespace)/\(.objectRef.name // "-")"' audit.log
```

The audit log is authoritative for who made the request — `user.username` names the
service account or human, which is the fastest way to find an owner. It costs more to
query at scale than the metric, so use it as a fallback rather than the default source
when metrics are available.

## kubent and pluto as a second opinion

`kubent` (kube-no-trouble) reads objects directly from the live cluster and recovers each
one's original `apiVersion` from the `kubectl.kubernetes.io/last-applied-configuration`
annotation that `kubectl apply` sets when the object is applied. `pluto` covers both a
live cluster and static manifests or Helm releases you point it at. Run either for a
second opinion after the live-traffic query, never before it and never as a replacement
for it:

```bash
kubent --helm3 --context "$CONTEXT"
pluto detect-helm --output wide
pluto detect-files -d ./manifests
```

Both tools share the same blind spot: an object an operator or controller created
directly — never through `kubectl apply` and never shipped in a Helm release — carries no
`last-applied-configuration` annotation and no entry in git or a release for either tool
to read, so it is invisible to both. A clean result from both proves only that the
tracked surface is clean — it says nothing about what a controller created on its own.

## Reading a provider's removal notes

Each managed provider (EKS, GKE, AKS) publishes per-version release notes listing what
that specific minor removes, in addition to the upstream Kubernetes deprecation guide.
Read both: the upstream guide is the authoritative removal schedule, but a provider's
managed add-ons (its CNI, its ingress controller, its CSI driver) sometimes drop support
for an API ahead of or behind the upstream schedule, and that gap is exactly what a
provider's own notes exist to surface.
