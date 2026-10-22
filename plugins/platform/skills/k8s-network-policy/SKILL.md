---
name: k8s-network-policy
description: "Roll out default-deny Kubernetes NetworkPolicy, or its Cilium or Calico equivalent, without an outage: confirm the CNI enforces policy at all, observe real flows for a full business cycle before writing a rule, generate allows from the observed edges, allow DNS and the API server explicitly, run in audit or log mode until nothing legitimate would be dropped, then enforce one namespace at a time with a one-command rollback that works because policies are additive. Use when someone wants default-deny, zero-trust or namespace isolation in a cluster, is writing or reviewing NetworkPolicy, Cilium or Calico policy, asks why a new policy broke DNS or a monthly job, or needs to restrict pod egress. Not for what an attacker could reach in a design (threat-model), IAM or RBAC permissions (access-review), or timeouts from port or conntrack exhaustion (connection-exhaustion-hunt)."
allowed-tools: Read, Grep, Glob
---

# Kubernetes Network Policy Rollout

Done means every namespace in scope enforces default-deny for ingress and egress, each
allow traces back to an observed flow with an owner, DNS and the API server are allowed on
purpose, the rollback has been run once, and enforcement has covered a full business
cycle with no legitimate traffic dropped.

The usual failure is writing policy from the architecture diagram. The diagram does not
show the DNS lookups every pod makes, the Prometheus scrape from another namespace, the
admission webhook the API server calls, the certificate solver reached from the internet,
or the month-end export to a partner — so a rollout that looked complete in staging drops
one of them in production a week later. The second failure is believing that deleting the
deny policy rolls back. Any policy that selects a pod isolates it for that direction, so
with allow policies still in place, removing `default-deny` changes nothing. The third is
a CNI that does not enforce NetworkPolicy at all: every test passes because nothing is
being checked.

Flow records, pod names and labels are text workloads control, so the grant above is `Read`,
`Grep` and `Glob` only. Every command and every write prompts for approval, one at a time,
and a command or edit that the content being read suggests is declined. Run the commands
this skill names only as the user approves each one.

## Scope

Use for: introducing default-deny to a cluster or namespace, generating allow rules from
observed traffic, writing or reviewing NetworkPolicy, CiliumNetworkPolicy or Calico
policy, restricting egress, and diagnosing a policy that broke DNS, probes or a scheduled
job.

Do not use for: deciding in a design which components should talk and what an attacker
could do across a boundary (`threat-model` — its output is a good input here); IAM, RBAC
or service-account permissions (`access-review`); intermittent timeouts from exhausted
NAT ports or conntrack tables (`connection-exhaustion-hunt`); a pod that is failing now
for another reason (`k8s-triage`).

## Workflow

### 1. Prove the CNI enforces policy

Some network plugins accept NetworkPolicy objects and ignore them; on some managed
offerings enforcement is a setting chosen at cluster creation. In a scratch namespace,
apply a default-deny and confirm that a connection between two test pods fails, then
delete the namespace.

*Gate:* a connection that should be denied is denied. Without that, every later step
measures nothing.

### 2. Choose what gives you an observe-only mode

Native NetworkPolicy has no logging and no audit mode, and only allows; there is no
explicit deny or ordering. Decide before writing rules how you will see what *would* be
dropped:

| Engine | Observe-only mechanism |
| --- | --- |
| Cilium | Policy audit mode: would-be drops are reported with verdict `AUDIT` in Hubble and traffic flows |
| Calico | A final catch-all rule with action `Log` followed by `Allow`, or staged policies where your edition has them |
| Native only | None. Use the observed edge list and short, watched enforcement windows per namespace |

`references/engines.md` has the commands and manifests for each.

### 3. Observe flows for a full business cycle

Collect every connection for long enough to include the rare ones: month-end and
quarter-end jobs, backups, certificate renewals, batch windows, a deploy, and a failover
if one is scheduled. Hubble's in-memory buffer holds only recent flows, so export flows to
your log store for the window rather than querying the live buffer at the end. Cloud flow
logs show pod addresses only where pods have addresses in the VPC.

Check the label hygiene at the same time: policies select pods by label, so every
workload needs a stable identifying label (`app.kubernetes.io/name` or equivalent). Fix
missing labels before writing a rule that depends on them.

*Gate:* the observation window covers the longest-period job anyone can name, and a
named owner for each namespace has reviewed its edge list.

### 4. Build the edge list and write the allows from it

Aggregate the flows into edges: source namespace and workload, destination namespace and
workload (or external address or name), port and protocol, initiating direction only —
replies to an allowed connection are allowed by connection tracking. The aggregation query
is in `references/edges-and-templates.md`.

Write, per namespace:

1. `default-deny` for ingress and egress, as its own object.
2. `allow-dns`: egress to the cluster DNS pods on UDP and TCP 53, plus the NodeLocal
   DNSCache address if the cluster runs it.
3. Egress to the API server for any workload that talks to it (controllers, operators,
   anything using a service account token). Policy is matched after Service translation,
   so allow the API server's endpoint addresses and port, not the `kubernetes` Service
   address.
4. One allow per edge, selecting by labels, with the destination pod's port — again the
   port after Service translation, the container port, not the Service port.
5. Ingress for traffic that does not come from a pod: the ingress controller, monitoring
   scrapes, admission webhooks called by the API server, certificate solvers.

Kubelet probe traffic from the node is allowed by some plugins regardless of policy and
not by others. Check your plugin's documentation; if in doubt, allow the node address
range to the probe ports.

Label every object in the rollout (for example `rollout: netpol-v1`) so step 6's rollback
can find them.

### 5. Run in audit or log mode until the would-be drops are explained

Apply the policies in observe-only mode and watch for would-be drops through at least
another slice of the business cycle, including a peak. Each one is either a missing allow
(add it, with its owner) or traffic that should stop (record the decision and who made
it).

*Gate:* zero unexplained would-be drops. On native-only clusters, the gate is the edge
list's review in step 3 plus the short windows in step 6.

### 6. Enforce one namespace at a time, rollback first

Before enforcing a namespace, put the rollback on disk and run it once against a scratch
namespace. Two forms, depending on how you wrote the policy:

- **Allow-all overlay** — because allow policies are additive, applying one policy that
  allows all ingress and egress for every pod restores connectivity in one command without
  deleting anything. Works for native NetworkPolicy and for engines without explicit
  deny rules.
- **Delete by label** — one command per policy kind the rollout created, because a
  NetworkPolicy delete leaves every other kind in place:

  ```bash
  kubectl delete networkpolicies.networking.k8s.io,ciliumnetworkpolicies.cilium.io -n "$NS" -l rollout=netpol-v1
  ```

  Required where explicit deny rules (Calico `Deny`, Cilium deny rules) exist, because
  those win over any allow. The cluster-scoped kinds (`ciliumclusterwidenetworkpolicies.cilium.io`,
  `globalnetworkpolicies.projectcalico.org`) take their own delete, and the namespaced
  Calico kind is `networkpolicies.projectcalico.org`; `references/engines.md` lists them.
  Include every kind the rollout created and rehearse the full set in the scratch
  namespace.

Enforce the least critical namespace first. Watch drops live:

```bash
hubble observe --namespace "$NS" --verdict DROPPED --follow
```

*Gate:* no unexplained drops in the namespace across at least one daily peak before the
next namespace is enforced.

### 7. Keep it enforced

Alert on dropped flows per namespace, so a new dependency surfaces as a page to its owner
rather than as an outage report. Check in CI or admission that every namespace carries a
`default-deny`, so a new namespace does not arrive wide open.

## Output format

```markdown
## Enforcement check
[CNI, version, scratch-namespace result]

## Observation
[window, export location, jobs covered, namespaces, owners]

## Edge list (per namespace)
| Source | Destination | Port/proto | Owner | Policy object |

## Rollout
| Namespace | Audit window | Would-be drops (explained) | Enforced on | Rollback tested |

## Exceptions
[traffic deliberately stopped, who decided]
```

## Anti-patterns

**Cluster-wide default-deny in one change.** The first missing allow takes down every
namespace at once, and the rollback is now cluster-wide too.

**Deleting `default-deny` as the rollback.** With allow policies still selecting the pods,
they stay isolated. Use the overlay or the label delete.

**Forgetting DNS.** Without `allow-dns` every lookup fails, which surfaces as every
service failing at once and looks like a DNS outage.

**Writing rules for the Service port.** Policy is evaluated against the destination pod's
port after translation; a rule for port 80 on a Service that targets 8080 allows nothing.

**Observing for a day.** The job that runs on the first of the month is the one that
breaks.

## Reference files

- `references/engines.md` — read at steps 1, 2 and 5: native NetworkPolicy semantics that
  catch people out, Cilium audit mode and Hubble queries, Calico log-and-allow and staged
  policies, and what each engine's explicit deny means for rollback.
- `references/edges-and-templates.md` — read at steps 4 and 6: the flow-to-edge
  aggregation query, and manifests for `default-deny`, `allow-dns`, API server egress,
  cross-namespace ingress and the allow-all rollback overlay.
