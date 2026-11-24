# DevOps: start here

A DevOps or platform engineer's week crosses eight plugins here: `platform` for clusters,
identity and cloud estates, `operations` for live systems and incidents, `delivery` for
pipelines and releases, `security` for hardening and review, `linux` for the host
underneath, `observability` for alerts and telemetry, `iac` for Terraform modules and
apply pipelines, and `devtools` for git recovery, build caching and dependency resolution. This page maps everyday
tasks to the skill that owns them, and says what installing them together costs, because
that cost is the decision that matters most.

## Install and use

For Claude Code, register the marketplace and install the plugins you will use. A focused
starting set for platform work:

```text
/plugin marketplace add greenblacked/AI
/plugin install platform@greenblacked-ai
/plugin install operations@greenblacked-ai
/plugin install delivery@greenblacked-ai
/plugin install security@greenblacked-ai
/reload-plugins
```

Add `linux`, `observability` and `iac` when your work reaches them, and `devtools` when
build speed, git history or dependency resolution is a regular cost. Then describe the
task in ordinary language: "pods are Pending after the node pool change", "our GitHub
Actions workflow checks out fork code under `pull_request_target`", or "this Terraform
state has 4000 resources and plans take half an hour". The description that matches is
loaded; you do not name the skill.

For Codex and other assistants, follow [Using the skills](using.md). Native skill loading
and permissions differ by host, and an exported procedure does not confer authority to
change a cluster or a cloud account.

### What installing them together costs

Every description a plugin ships stays in context for the whole session, and the runtime
caps that listing at about 1% of the context window, roughly 8,000 characters on a 200k
window. Past the cap it drops the descriptions of the skills you use least, which leaves
them invocable by name and stops them being chosen on their own. `make validate` prints
the per-plugin totals; as of 2026-11 the plugins on this page measure:

| Plugin | Description characters |
| --- | --- |
| `security` | 27,493 |
| `platform` | 19,280 |
| `linux` | 18,278 |
| `observability` | 17,057 |
| `operations` | 16,667 |
| `delivery` | 10,550 |
| `devtools` | 8,601 |
| `iac` | 2,321 |

The first four recommended plugins, `platform`, `operations`, `delivery` and `security`,
total 73,990 characters. All seven without `devtools` total 111,646 characters, about
fourteen times the 8,000-character default and about 24,100 tokens at this library's
measured 4.63 characters per token, or roughly 12% of a 200k window. Adding `devtools`
makes 120,247 characters, about fifteen times the default and roughly 26,000 tokens,
about 13% of the window.

Two consequences follow. With the default budget, most of those descriptions would be
dropped and most of these skills could only be reached by name, so raise the budget in
`~/.claude/settings.json` when you install more than one:

```json
{ "skillListingBudgetFraction": 0.2 }
```

That value covers all eight plugins on the 8,000-character basis with headroom; `0.16` is
the least two-decimal value that holds them (`0.15` allows 120,000 characters, just short of 120,247), and the figure the repository prints for the whole marketplace
is in [the README](../README.md#install). And a raised budget is spent, not free: the
listing then occupies a double-digit share of every session's context. Install the four
core plugins first, add another only when its skills fire for real work, and uninstall one
you have not used in a month. The totals move as skills are added, so rerun `make
validate` in a checkout rather than trusting the figures above after a release.

## Choose the owner

| Task | Skill and plugin | What to bring |
| --- | --- | --- |
| Pods crash, stay Pending or fail after a deploy | [k8s-triage](../plugins/operations/skills/k8s-triage/SKILL.md), `operations` | Events, pod status and the time of the last change |
| Write or review workload manifests, limits and probes | [k8s-workloads](../plugins/operations/skills/k8s-workloads/SKILL.md), `operations` | Manifests and the service's traffic shape |
| Upgrade a cluster and find removed API calls | [k8s-upgrade](../plugins/operations/skills/k8s-upgrade/SKILL.md), `operations` | Current and target versions, add-ons and node pools |
| Roll out default-deny network policy | [k8s-network-policy](../plugins/platform/skills/k8s-network-policy/SKILL.md), `platform` | CNI, namespaces and a window of observed flows |
| Replace static cloud keys with workload identity | [workload-identity](../plugins/platform/skills/workload-identity/SKILL.md), `platform` | Issuer, audience, exact subjects and intended roles |
| Move a node pool to spot capacity | [spot-readiness](../plugins/platform/skills/spot-readiness/SKILL.md), `platform` | Workload list with recovery times and the interruption notice |
| kubectl is slow or the API server throttles | [apiserver-pressure](../plugins/platform/skills/apiserver-pressure/SKILL.md), `platform` | Request metrics by verb and resource, audit log access |
| Persistent volumes, snapshots and storage classes | [k8s-storage](../plugins/platform/skills/k8s-storage/SKILL.md), `platform` | Storage classes, claims and the failure seen |
| Terraform state is locked, drifted or needs an import | [terraform-state](../plugins/operations/skills/terraform-state/SKILL.md), `operations` | Verified target, writer status and recovery context |
| Split an oversized state | [monolith-state-split](../plugins/platform/skills/monolith-state-split/SKILL.md), `platform` | Dependency graph and proposed stack boundaries |
| Adopt a hand-built estate | [brownfield-iac-adoption](../plugins/platform/skills/brownfield-iac-adoption/SKILL.md), `platform` | Provider inventory access and existing states |
| Upgrade Terraform or a provider major version | [iac-version-upgrade](../plugins/platform/skills/iac-version-upgrade/SKILL.md), `platform` | Current pins, desired versions and affected environments |
| Change a shared module without breaking callers | [terraform-module-contracts](../plugins/iac/skills/terraform-module-contracts/SKILL.md), `iac` | Current interface, representative callers and the intended change |
| Test a module's behavior | [terraform-module-tests](../plugins/iac/skills/terraform-module-tests/SKILL.md), `iac` | Contract and supported engine versions |
| Apply exactly the plan a reviewer accepted | [iac-apply-pipeline](../plugins/iac/skills/iac-apply-pipeline/SKILL.md), `iac` | Workflow, state identity and approval policy |
| Judge whether a Terraform plan is safe | [iac-review](../plugins/security/skills/iac-review/SKILL.md), `security` | The plan JSON and the intended target |
| Design CI stages, caches and required checks | [ci-pipeline-design](../plugins/delivery/skills/ci-pipeline-design/SKILL.md), `delivery` | Run history and pipeline constraints |
| Work out why CI is red | [ci-triage](../plugins/operations/skills/ci-triage/SKILL.md), `operations` | The failing run and recent merges |
| Audit a workflow's attacker reach | [pipeline-hardening](../plugins/delivery/skills/pipeline-hardening/SKILL.md), `delivery` | Workflow events, permissions and artifact consumers |
| Choose a rollout and rollback strategy | [release-strategy](../plugins/delivery/skills/release-strategy/SKILL.md), `delivery` | Service risk, traffic and rollback cost |
| Operate a GitOps controller | [gitops-operations](../plugins/delivery/skills/gitops-operations/SKILL.md), `delivery` | Controller state and the out-of-sync resources |
| Harden a container image | [image-hardening](../plugins/security/skills/image-hardening/SKILL.md), `security` | The Dockerfile and the scanner findings |
| Harden a Linux host | [host-hardening](../plugins/security/skills/host-hardening/SKILL.md), `security` | Distribution, access model and a rollback path |
| Rotate a leaked or aging secret | [secret-rotation](../plugins/security/skills/secret-rotation/SKILL.md), `security` | Where the secret is used and who holds it |
| Issue and renew certificates automatically | [certificate-automation](../plugins/security/skills/certificate-automation/SKILL.md), `security` | Issuers, endpoints and renewal ownership |
| Run a live incident | [incident-response](../plugins/operations/skills/incident-response/SKILL.md), `operations` | Symptoms, severity and who is on the call |
| Design alerts that page for the right reasons | [alert-design](../plugins/operations/skills/alert-design/SKILL.md), `operations` | SLOs, current alerts and paging history |
| Test an alert rule against history | [alert-backtest](../plugins/observability/skills/alert-backtest/SKILL.md), `observability` | The rule, metric history and the incident list |
| Cut log volume and its cost | [log-volume-reduction](../plugins/observability/skills/log-volume-reduction/SKILL.md), `observability` | Volume by source and the bill or limit |
| Find why a metric is missing | [missing-metrics-hunt](../plugins/observability/skills/missing-metrics-hunt/SKILL.md), `observability` | The metric, the graph gap or flatline, and when it began |
| Review a collector pipeline | [otel-collector-pipeline-review](../plugins/observability/skills/otel-collector-pipeline-review/SKILL.md), `observability` | Collector configuration and drop metrics |
| DNS resolution fails on a host | [dns-resolution-debugging](../plugins/linux/skills/dns-resolution-debugging/SKILL.md), `linux` | The name, the resolver in use and the failing host |
| DNS records, zones and delegation | [dns-operations](../plugins/platform/skills/dns-operations/SKILL.md), `platform` | Zone configuration and the change planned |
| A TLS handshake fails | [tls-handshake-debugging](../plugins/linux/skills/tls-handshake-debugging/SKILL.md), `linux` | Client, server and the exact error |
| Trust an internal CA in every runtime | [private-ca-trust-distribution](../plugins/linux/skills/private-ca-trust-distribution/SKILL.md), `linux` | The root certificate and the runtimes affected |
| SSH login fails or hangs | [ssh-access-debugging](../plugins/linux/skills/ssh-access-debugging/SKILL.md), `linux` | Client verbose output and server logs |
| A firewall drops traffic | [firewall-rule-tracing](../plugins/linux/skills/firewall-rule-tracing/SKILL.md), `linux` | Source, destination, port and the rule set |
| A systemd unit fails | [systemd-unit-failure](../plugins/linux/skills/systemd-unit-failure/SKILL.md), `linux` | Unit file and journal output |
| Disk full or a process killed for memory | [disk-full-triage](../plugins/linux/skills/disk-full-triage/SKILL.md) and [oom-kill-forensics](../plugins/linux/skills/oom-kill-forensics/SKILL.md), `linux` | Filesystem usage, kernel log and cgroup limits |
| The cloud bill rose | [cost-review](../plugins/operations/skills/cost-review/SKILL.md), `operations` | Billing export and recent changes |
| Network transfer charges are unexplained | [data-transfer-forensics](../plugins/platform/skills/data-transfer-forensics/SKILL.md), `platform` | Billing line items and flow data |
| Decide on a savings plan or commitment | [commitment-planning](../plugins/platform/skills/commitment-planning/SKILL.md), `platform` | Usage history and migration plans |
| Recover a lost branch or rewritten history | [git-history-recovery](../plugins/devtools/skills/git-history-recovery/SKILL.md), `devtools` | Reflog access and what was lost |
| Find why the build cache misses | [build-cache-miss-hunt](../plugins/devtools/skills/build-cache-miss-hunt/SKILL.md), `devtools` | Two build logs with differing cache outcomes |

Install the neighboring plugin when its skill is needed; installing one does not pull in
the others. A link is routing guidance, not a claim that an absent skill can run in the
current assistant. For Terraform work in particular, [Infrastructure as code: start
here](iac.md) goes deeper than the rows above.

## Notes

Triage comes before design. A paging incident belongs with `incident-response` and
`k8s-triage` until it is mitigated; alert tuning, hardening and cost work wait for the
post-incident review. Preserve the evidence from that first skill so the next one solves
the identified problem rather than repeating discovery.

Several tasks have two plausible owners. A workflow that leaks a secret is first a
`secret-rotation` problem and then a `pipeline-hardening` one. A Terraform plan that
replaces a database is first an `iac-review` decision, then a state or module question.
Say which stage you are in and the matching description is chosen.

Keep plans, state, kubeconfigs, audit logs and credentials private. Do not paste their raw
contents into a public issue to ask which skill applies; state the target and symptom,
then give the assistant restricted access to the evidence it needs. Report checks you could
not run as unverified rather than assuming they pass.
