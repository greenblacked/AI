# Edges and policy templates

Read this at steps 4 and 6. Replace the namespace, labels and ports with your own; the
shapes are what matter.

## Contents

- [Aggregating flows into edges](#aggregating-flows-into-edges)
- [default-deny](#default-deny)
- [allow-dns](#allow-dns)
- [API server egress](#api-server-egress)
- [Ingress from another namespace](#ingress-from-another-namespace)
- [One edge](#one-edge)
- [The allow-all rollback overlay](#the-allow-all-rollback-overlay)

## Aggregating flows into edges

From Hubble JSON, one flow per line. Field names differ slightly between Hubble versions
and between `hubble observe -o json` and exported files; check one line of your own output
before trusting the query.

```bash
jq -r 'select(.flow.is_reply != true) | .flow as $f
  | [ ($f.source.namespace // "external"),
      ($f.source.workloads[0].name // $f.source.pod_name // $f.IP.source),
      ($f.destination.namespace // "external"),
      ($f.destination.workloads[0].name // $f.destination.pod_name
         // ($f.destination_names[0] // $f.IP.destination)),
      (($f.l4.TCP.destination_port // $f.l4.UDP.destination_port) | tostring) ]
  | @tsv' flows.json | sort | uniq -c | sort -rn > edges.tsv
```

Each line is one edge with a count. Low-count edges are the ones to ask about: they are
either a rare job that must keep working or something that should not be happening.

## default-deny

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: payments
  labels:
    rollout: netpol-v1
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

## allow-dns

Check the label on your DNS pods first (`kubectl get pods -n kube-system --show-labels`);
`k8s-app: kube-dns` is common but not universal.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: payments
  labels:
    rollout: netpol-v1
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # Only if the cluster runs NodeLocal DNSCache; use the address it listens on.
    - to:
        - ipBlock:
            cidr: 169.254.20.10/32
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

The namespace and pod selectors sit in one list element, so both must match.

## API server egress

Find the addresses and port the API server is actually reached on, after translation:

```bash
kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes \
  -o jsonpath='{range .items[*]}{.endpoints[*].addresses[*]}{" "}{.ports[*].port}{"\n"}{end}'
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-apiserver
  namespace: payments
  labels:
    rollout: netpol-v1
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: payments-operator
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 10.0.0.10/32
      ports:
        - protocol: TCP
          port: 443
```

On managed clusters these addresses can change. Use the control-plane address range the
provider documents, or Cilium's `kube-apiserver` entity, and recheck after control-plane
maintenance.

## Ingress from another namespace

The ingress controller and monitoring scrapes are the usual pair.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress-and-monitoring
  namespace: payments
  labels:
    rollout: netpol-v1
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: payments-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app.kubernetes.io/name: prometheus
      ports:
        - protocol: TCP
          port: metrics
```

Both ports are the destination pod's: 8080 is the container port, not the Service port,
and `metrics` is a named container port on `payments-api`, which policy accepts in place
of a number.

## One edge

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-ledger
  namespace: payments
  labels:
    rollout: netpol-v1
  annotations:
    owner: payments-team
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: payments-api
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: ledger
      ports:
        - protocol: TCP
          port: 5432
```

The matching ingress allow on the `ledger` side is needed too when `ledger` is isolated for
ingress; an edge crossing two isolated pods needs an egress allow on one end and an
ingress allow on the other.

## The allow-all rollback overlay

Applying this restores all traffic in the namespace while every other object stays in
place, because allows are additive. It does not override an explicit deny from Cilium or
Calico.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: emergency-allow-all
  namespace: payments
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - {}
  egress:
    - {}
```

```bash
kubectl apply -f emergency-allow-all.yaml
kubectl delete networkpolicy -n payments emergency-allow-all   # re-enforce
```

It deliberately carries no `rollout` label, so the label delete does not remove it by
accident.
