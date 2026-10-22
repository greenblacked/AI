# Policy engines

Read this at steps 1, 2 and 5. Flags and value names below change between releases;
confirm each against the version you run before scripting it.

## Contents

- [Native NetworkPolicy semantics that catch people out](#native-networkpolicy-semantics-that-catch-people-out)
- [Cilium](#cilium)
- [Calico](#calico)
- [Explicit deny and what it does to rollback](#explicit-deny-and-what-it-does-to-rollback)

## Native NetworkPolicy semantics that catch people out

- **Additive, allow-only.** A pod is isolated for ingress as soon as any policy that
  lists `Ingress` in `policyTypes` selects it, and likewise for egress. After that, traffic
  is allowed only if some policy allows it. There is no deny rule and no ordering.
- **`policyTypes` defaults.** Omitted, it is `Ingress` always, plus `Egress` only if the
  policy has egress rules. A "deny all egress" written without `policyTypes: [Egress]`
  isolates nothing.
- **AND versus OR in `from` and `to`.** `namespaceSelector` and `podSelector` in the *same*
  list element mean both must match. As *separate* elements they mean either. One
  misplaced hyphen turns "the monitoring pods in the monitoring namespace" into "every pod
  in the monitoring namespace, or any pod anywhere labelled monitoring".
- **Namespace names.** Every namespace carries `kubernetes.io/metadata.name` set to its
  name, so a `namespaceSelector` can match by name without adding labels.
- **Ports after translation.** Rules match the destination pod's port, after Service
  address translation.
- **`ipBlock` and address rewriting.** Traffic arriving through a load balancer may carry
  a node or load-balancer address rather than the client's, depending on
  `externalTrafficPolicy` and the provider. Do not rely on `ipBlock` for pod-to-pod
  traffic; pod addresses change.
- **Host-network pods** are not reliably selected by NetworkPolicy; treat their traffic
  as outside its control.
- **Existing connections.** Whether a newly applied policy cuts connections that are
  already open depends on the plugin. Test it before relying on it either way.

## Cilium

**Audit mode.** Cluster-wide through the Helm value `policyAuditMode`, or per endpoint
from inside an agent pod (the in-agent CLI is `cilium-dbg` on recent releases, `cilium`
on older ones):

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=Enabled
```

In audit mode, traffic that policy would drop is forwarded and reported with verdict
`AUDIT`.

**Hubble.**

```bash
cilium hubble port-forward &
hubble observe --namespace "$NS" --verdict AUDIT --since 1h
hubble observe --namespace "$NS" --verdict DROPPED --follow
hubble observe --to-namespace "$NS" --port 8080 -o json
```

The relay's buffer covers recent flows only. For a business-cycle observation, enable
Hubble's flow export to a file or your log pipeline and aggregate there.

**What CiliumNetworkPolicy adds.**

- `toEntities: [kube-apiserver]` allows egress to the API server without tracking its
  addresses — better than an `ipBlock` on managed clusters where those addresses move.
- `fromEntities: [host]` allows traffic from the local node, such as kubelet probes, where
  your configuration does not already allow it.
- `toFQDNs` allows egress by DNS name, but only learns addresses from lookups that pass
  through Cilium's DNS proxy. The DNS allow must carry an L7 DNS rule (`rules: dns:` with
  a `matchPattern`), or `toFQDNs` silently allows nothing.

## Calico

Calico evaluates Kubernetes NetworkPolicy alongside its own `NetworkPolicy` and
`GlobalNetworkPolicy` resources, in `order` (lower first). Rule actions are `Allow`,
`Deny`, `Log` and `Pass`; `Log` records the packet and continues to the next rule.

**Log-and-allow catch-all.** With the native or Calico policies from step 4 applied, add
a policy that is evaluated after them and logs then allows whatever they did not allow.
Anything it logs is exactly what enforcement would drop.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: zz-audit-catch-all
spec:
  order: 10000
  namespaceSelector: kubernetes.io/metadata.name == 'payments'
  types:
    - Ingress
    - Egress
  ingress:
    - action: Log
    - action: Allow
  egress:
    - action: Log
    - action: Allow
```

```bash
calicoctl apply -f zz-audit-catch-all.yaml
```

`Log` writes to the node's kernel log. Enforcing the namespace is then deleting this one
object.

**Staged policies.** Editions that provide staged policy types evaluate a policy and
report what it would do without enforcing it. Use them where available instead of the
catch-all.

## Explicit deny and what it does to rollback

| Engine | Explicit deny | Effect on the allow-all overlay rollback |
| --- | --- | --- |
| Native NetworkPolicy | None | Overlay restores all traffic |
| Cilium | `ingressDeny` and `egressDeny` | Deny wins over any allow; the overlay does not restore denied traffic |
| Calico | `action: Deny`, ordered | A `Deny` evaluated before the overlay still applies |

Where any explicit deny exists, the rollback is deleting the rollout's objects by label,
not adding an overlay. The delete must name every kind the rollout created, since a
`networkpolicies.networking.k8s.io` delete leaves the others enforced:

```bash
kubectl delete networkpolicies.networking.k8s.io,ciliumnetworkpolicies.cilium.io -n "$NS" -l rollout=netpol-v1
kubectl delete ciliumclusterwidenetworkpolicies.cilium.io -l rollout=netpol-v1
kubectl delete networkpolicies.projectcalico.org -n "$NS" -l rollout=netpol-v1
kubectl delete globalnetworkpolicies.projectcalico.org -l rollout=netpol-v1
```

Run only the lines for the engine in use, with the Calico API server installed; without it
use `calicoctl delete` on the same kinds. Rehearse the set in the scratch namespace.
