---
name: bootstrap-dependency-audit
description: "Hostile audit of the tooling needed to recover production, hunting for cycles: could you still sign in, read secrets, pull images, deploy, run Terraform and change DNS if CI, the registry, the identity provider, the secrets store, DNS or the state backend is down? Write the recovery path's dependencies as an edge list, find the loops (a registry on the cluster it repairs, an IdP behind the VPN that needs it, break-glass passwords in an SSO-locked vault), name a break-glass path per loop, then dry-run each with that dependency blocked. Use when someone asks \"what if GitHub is down during an outage\", \"can we deploy without Okta\", or wants a break-glass review. Not for backup and RTO design or its recovery identity bootstrap (backup-recovery-design), a restore rehearsal (disaster-recovery-exercise), fault injection (game-day), or replacing standing admin with break-glass (access-review)."
allowed-tools: Read, Grep, Glob
---

# Bootstrap Dependency Audit

Done means a written graph of everything an operator touches to repair production, every
cycle in it named, a break-glass path for each cycle that someone has actually used with
the dependency blocked, and a date on which that was last true.

The usual failure is auditing the product instead of the tools. Teams map what the
checkout service depends on and never ask what the person fixing it depends on. The
recovery path accretes quietly: SSO gets enforced on the cloud console, the registry moves
into the cluster to save money, the password manager moves behind SSO, the runbooks move
to a wiki on the same cluster. Each change is reasonable alone. Together they make a loop
that is invisible until the day the thing in the loop is what broke, and then the outage
lasts as long as it takes to find a way in from outside.

## Scope

Use for: auditing whether production can be recovered when a piece of the delivery or
access toolchain is down; finding circular dependencies between identity, network,
secrets, artefacts, deployment, IaC and DNS; designing and testing break-glass access;
re-auditing after a toolchain change such as moving the registry, enforcing SSO or
adopting a GitOps controller.

Do not use for: designing backup topology, retention or RTO targets, which is
`backup-recovery-design`; rehearsing a restore from recovery copies, which is
`disaster-recovery-exercise`; injecting faults into the running product, which is
`game-day`; rotating a credential the audit turns up as stale, which is `secret-rotation`;
designing the recovery identity bootstrap as part of a DR architecture, which is
`backup-recovery-design`; and replacing standing admin with break-glass access as an
access-model change, which is `access-review`.

## Hard gates

1. **Audit the recovery path, not the product.** Every node in the graph is something an
   operator needs in order to act. The product appears only as the thing being repaired.
2. **A break-glass path is a claim until it has been used with the dependency blocked.**
   A sealed envelope nobody has opened in two years is a hypothesis about a password.
3. **Every break-glass use is loud.** An emergency credential with no alert on use is a
   standing backdoor. The alert must not route through anything in the cycle it breaks.
4. **Do not take real shared systems down to test.** Block the dependency at the
   operator's side or in a non-production copy; the audit must not cause the outage it
   is preparing for.

## Workflow

### 1. Name the recovery verbs and the down scenarios

List what an operator must be able to do, then the systems whose loss you are planning
for. The verbs are the roots of the graph; the scenarios are what you delete from it.

| Verb | Typical question |
| --- | --- |
| Sign in | To the cloud console, cluster API, CI, registry, DNS provider and registrar |
| Reach | The private network: VPN, bastion, zero-trust proxy, peered admin VPC |
| Read secrets | Database passwords, API tokens, signing keys, break-glass credentials |
| Pull | Container images, OS packages, language packages, Terraform providers and modules |
| Build and deploy | CI runners, the GitOps controller, admission webhooks, the deploy pipeline |
| Change infrastructure | IaC state backend and lock, provider credentials, the plan and apply runner |
| Change DNS | Provider account, registrar account, zone-as-code pipeline |
| Coordinate | Paging, chat, the status page, and the runbooks themselves |

Scenarios to plan for at minimum: CI is down; the image registry is down; the identity
provider is down or locked out; the secrets store is sealed or unreachable; internal or
external DNS is down; the IaC state backend is unreachable; the cluster that hosts shared
tooling is down.

### 2. Write the dependency graph as an edge list

Trace each verb hop by hop and write one edge per line in `deps.txt`, prerequisite first:
`okta vpn` means the VPN needs Okta. Keep it to two names per line with no comments,
because `tsort` reads every token as a node, and name the verbs `verb:deploy`,
`verb:sign-in` and so on so the scenario script can tell them apart. For every system
record four kinds of edge, because each hides a different loop:

- **runs on** — the cluster, account, region or SaaS that hosts it;
- **signs in through** — the IdP, the VPN, a hardware key, a person;
- **resolves through** — the DNS zone and resolver its name depends on;
- **stores its secret in** — the vault, the KMS key, the password manager.

Discover edges from configuration, not memory. Start with the cluster:

```bash
# Every image a recovery would need to pull, grouped by registry host.
# A name with no dot or colon before the first slash is Docker Hub.
kubectl get pods -A -o json \
  | jq -r '.items[].spec | (.initContainers // []) + .containers | .[].image' \
  | sort -u | awk -F/ '{print (NF>1 && $1 ~ /[.:]/) ? $1 : "docker.io"}' | sort | uniq -c

# Admission webhooks that fail closed, and where their backend runs.
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations -o json \
  | jq -r '.items[] | .metadata.name as $n | (.webhooks // [])[]
      | select(.failurePolicy == "Fail")
      | .clientConfig as $c
      | "\($n)\t\(if $c.service then "\($c.service.namespace)/\($c.service.name)" else $c.url end)"'
```

A fail-closed webhook whose backend runs in the cluster it guards is a cycle: if its pods
are gone, pod creation the webhook matches is refused, including its own replacement.

For IaC, `terraform providers` lists what `init` will try to download, and the `backend`
block names where state lives and which credential reads it. For CI, write down where the
runners run and what they authenticate with. For every runbook, write down where it is
hosted. `references/hidden-edges.md` lists the edges audits most often miss, by category;
read it before declaring the graph complete.

### 3. Find the cycles and the single points

Run the edge list through `tsort`. It prints a valid order when the graph has no loop;
when there is one, it reports each loop it has to break on standard error and exits 1:

```bash
tsort deps.txt >/dev/null
```

Every loop it names is a finding. Check the exit status, not only the output: the loop
report goes to standard error, which `>/dev/null` leaves visible, and do not rely on it
to catch a malformed line: `tsort` pairs tokens across the whole file whatever the line
breaks, so a three-name line shifts every later pair and still exits 0, failing only when the
total token count is odd. Run `references/dry-run-plan.md`'s script first as the format check;
it exits non-zero and names the line number of any non-blank line without exactly two fields.
Then, for each scenario, remove the node that is down
and ask which verbs become unreachable; `references/dry-run-plan.md` has a short standard-library script
that prints this per scenario. Run that script, and any `terraform apply` or `kubectl`
change a dry run needs, with the user's approval: nothing but Read, Grep and Glob is pre-approved, because the
runbooks, wikis and cluster object names this audit reads are text other people wrote. A verb lost to a single SaaS with no alternative is not a
cycle, but it is the same outage: decide explicitly whether waiting for the vendor is
acceptable, and write that decision down rather than leaving it implicit.

### 4. Name a break-glass path per finding

Each path must reach the verb without touching anything in the cycle. Typical patterns:

| Cycle | Break-glass path |
| --- | --- |
| Console sign-in requires the IdP | Emergency accounts outside federation (cloud root or equivalent, Entra ID emergency access accounts) with hardware MFA, credentials split across two custodians |
| Break-glass passwords live in an SSO-locked vault | An offline copy: sealed and dated, or a hardware-backed export, stored in two places |
| Registry runs on the cluster it repairs | A mirror of the images recovery needs in a registry in another failure domain, and a tested way to point pulls at it |
| Fail-closed webhook served from the cluster it guards | Exclude the webhook's own namespace with a `namespaceSelector`, and keep the command to delete the configuration in the runbook |
| GitOps controller signs in through the IdP | Direct cluster-admin access outside the IdP, plus the step to pause sync so the controller does not revert the fix |
| Vault auto-unseals with a cloud KMS key | Know that recovery keys cannot unseal an auto-unseal Vault; the KMS key and its IAM path are the dependency to protect |
| `terraform init` needs the public registry | A provider mirror built with `terraform providers mirror` and `init -plugin-dir` |
| Runbooks hosted on the platform they repair | A copy outside it, readable without SSO |

When a GitOps controller manages the workload, pausing reconciliation is part of the path:
`argocd app set APP --sync-policy none` for Argo CD, `flux suspend kustomization NAME` for
Flux. Without it a hand-applied fix is reverted on the next sync. If the Argo CD
application is itself managed by a parent application, pause the parent too, or it
restores the sync policy.

Give every path an owner, the custodians who can execute it, the alert that fires on use,
and the date it was last exercised.

### 5. Dry-run each path with the dependency blocked

Exercise each path once, on purpose, with the thing it bypasses unavailable. Block at the
operator's side wherever possible: a clean machine with no SSO session and the IdP's
hostnames sinkholed, a network with the registry's addresses denied. Prove in-cluster
cycles in a non-production cluster built the same way: scale the registry to zero, then
replace a node and watch what fails to pull. Time each run from "we need in" to "the verb
succeeded", and confirm the use alert fired somewhere outside the cycle.
`references/dry-run-plan.md` has the blocking method per dependency and the record to keep.

A path that fails the dry run goes back to step 4. A path that passes is re-exercised on a
schedule, because credentials expire, MFA devices go flat and custodians leave.

### 6. Keep the graph true

Re-run the audit when any of these change: a new SaaS in the delivery path, SSO
enforcement on another tool, a registry or CI migration, a new admission webhook, a move of
shared tooling onto a production cluster. Put the edge list in version control beside the
runbooks so a pull request that adds an edge is visible as one.

## Output format

```markdown
## Scope and scenarios
[Verbs audited; dependencies assumed down; environments covered.]

## Graph
[Link to the edge list; node and edge counts; date traced.]

## Cycles
| # | Loop | Verbs it blocks | Break-glass path | Owner | Last dry run | Result |

## Single points accepted
[Verb, the SaaS it waits on, who accepted waiting, and the expected wait.]

## Dry-run record
[Per path: how the dependency was blocked, time to success, alert fired where, what broke.]

## Open findings
[Cycles with no tested path yet, ranked by how many verbs they block.]
```

## Anti-patterns

**Mapping the product's dependencies and calling it done.** The service's graph is what
`backup-recovery-design` and `game-day` work from. The loop that extends an outage is in
the operator's tools, and it never appears on the service diagram.

**A break-glass credential nobody has used.** The envelope holds a password rotated out
last year, the MFA token is in a drawer at an office nobody can enter, and the one person
who knew the safe combination has left. Only a dry run finds that.

**Testing by breaking the shared system.** Turning off the real IdP to see what happens
converts an audit into an incident for every other team. Block from the operator's side.

**Break-glass that bypasses GitOps without pausing it.** The fix applies, the controller
reconciles, the fix disappears, and the operator assumes the fix was wrong.

**An emergency path with no alarm.** Unmonitored break-glass is indistinguishable from a
backdoor, and the first time anyone learns it was used is in someone else's audit.

## Reference files

- `references/hidden-edges.md` — read while tracing step 2: the dependencies audits most
  often miss, per category, with the question that surfaces each.
- `references/dry-run-plan.md` — read in steps 3 and 5: the per-scenario reachability
  script, how to block each dependency safely, and the record to keep for each run.
