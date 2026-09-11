# Cost attribution

Read this when spend cannot be mapped to a team, service or workload — the tag set worth
mandating, how to enforce it at creation rather than by sweep, the account and project
structure that attributes what tags cannot, the queries that produce a per-owner report,
Kubernetes attribution, and the shared-cost conventions with the arithmetic for each.

## Contents

- The mandatory tag set
- Activating and enforcing tags
- Account and project structure
- Queries that produce the report
- Kubernetes attribution
- Shared cost: pick a convention and write it down
- What stays unattributable

## The mandatory tag set

Four tags carry nearly all the value. More than about six and compliance collapses,
because every additional required tag is another way for a resource to be created wrong.

| Tag | Value shape | Why it earns its place |
| --- | --- | --- |
| `owner` | A team identifier that maps to a real rota, not a person | The question every cost report ends in is "who do I ask about this" |
| `service` | The service or product name as it appears in the service catalogue | Aggregates across accounts and regions; survives reorganisation better than team names |
| `environment` | `prod`, `staging`, `dev`, `sandbox` | Non-production is where the cheap wins are, and you cannot find them without this |
| `cost-centre` | The finance code | Lets the report reconcile against what finance already tracks, which is what makes it believed |

Add `expires` on anything created for an experiment, a load test or a migration. A date
in a tag is the only thing that reliably distinguishes a temporary resource from a
permanent one six months later.

Keep the key spelling identical everywhere. `Owner`, `owner` and `team` are three
separate dimensions in every billing tool, and the split is silent.

## Activating and enforcing tags

Applying a tag to a resource is not the same as making it a billing dimension.

- **AWS**: tags must be activated as cost allocation tags in Billing before they appear
  in Cost Explorer or the Cost and Usage Report, and activation is not retroactive —
  data before it is untagged forever. Activate the tag set on day one of the work.
- **GCP**: labels flow into the billing export; some resource types do not support
  labels, and project structure covers those.
- **Azure**: tags do not inherit from resource group to resource by default. Turn on tag
  inheritance in Cost Management, or the resource-level records stay blank.

Enforce at creation, in this order of effectiveness:

1. **In the IaC module.** A module that takes `owner` and `service` as required variables
   and applies them via `default_tags` at the provider level tags everything it creates,
   including resources nobody remembered.
2. **A policy check in CI.** Terraform plan JSON, Conftest, Checkov or a provider policy
   engine rejecting an untagged resource before it exists.
3. **A preventive control in the cloud** — an SCP, an Azure Policy deny, a GCP
   organisation policy — for the resources created outside CI.
4. **A sweep report** listing untagged resources by account and age. This documents the
   problem; it does not fix it. Use it to measure the first three.

An untagged share that stops falling means enforcement is missing at a creation path
nobody has found yet. Find the path rather than adding another sweep.

## Account and project structure

The boundary that never lies is the account, subscription or project. It attributes:

- Support charges, which are computed on the account's spend.
- Data transfer that has no resource to tag.
- Marketplace and third-party subscriptions.
- Anything created by a person in a hurry with no tags at all.

A workable default is one account per team per environment, under consolidated billing
or a single billing account, with commitments purchased centrally in the management
account so the discount pools across the organisation. The cost of the structure is
identity and networking complexity; the benefit is that attribution is a property of
where the resource lives rather than of whether someone remembered.

## Queries that produce the report

Month over month by service and usage type, which is the query that finds the mover:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-09-01 \
  --granularity MONTHLY \
  --metrics UnblendedCost AmortizedCost \
  --group-by Type=DIMENSION,Key=SERVICE Type=DIMENSION,Key=USAGE_TYPE
```

Spend by owner tag, with the untagged remainder visible rather than filtered away:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-09-01 \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=TAG,Key=owner
```

Untagged spend as a single number, which is the attribution gate:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-09-01 \
  --granularity MONTHLY --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"owner","MatchOptions":["ABSENT"]}}'
```

GCP, from the BigQuery billing export, which is the only source with full detail:

```sql
SELECT
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'owner'), 'UNATTRIBUTED') AS owner,
  service.description AS service,
  sku.description     AS sku,
  ROUND(SUM(cost), 2) AS cost
FROM `billing.gcp_billing_export_v1_XXXXXX`
WHERE DATE(usage_start_time) BETWEEN '2026-08-01' AND '2026-08-31'
GROUP BY owner, service, sku
ORDER BY cost DESC
LIMIT 50
```

Add credits explicitly when reconciling against an invoice — summing `cost` alone
overstates what was actually paid, because credits sit in a repeated field of their own.

Azure:

```bash
az costmanagement query --type ActualCost --timeframe MonthToDate \
  --scope "/subscriptions/SUBSCRIPTION_ID" \
  --dataset-grouping name=ResourceGroupName type=Dimension
```

## Kubernetes attribution

A cluster is one line on the bill. OpenCost (the CNCF project) and Kubecost apportion
node cost across pods by their resource requests and actual usage over time, then let
you aggregate by namespace, label, controller or any other dimension.

```bash
kubectl port-forward --namespace opencost service/opencost 9003 &
curl -sG 'http://localhost:9003/allocation/compute' \
  --data-urlencode 'window=30d' \
  --data-urlencode 'aggregate=namespace' \
  --data-urlencode 'accumulate=true' | jq '.data'
```

Three things to know before quoting the numbers:

- **Requests are the unit of cost**, because requests are what the scheduler reserved and
  therefore what prevented another workload from using the node. A pod requesting 4 CPU
  and using 0.2 costs the 4. This is the correct incentive and it surprises people.
- **Idle cost is real and belongs somewhere.** The gap between node capacity and the sum
  of requests is either charged back proportionally, or held in a platform bucket. Both
  are defensible; state which one the report uses, because the difference between them
  can be a third of the cluster.
- **Shared resources inside the cluster** — the ingress controller, the logging agent,
  the service mesh sidecars — follow the shared-cost convention below, not the namespace
  they happen to run in.

## Shared cost: pick a convention and write it down

A shared cluster, a shared database, a NAT gateway, the observability stack, the CI
fleet. Any split is a convention rather than a measurement, and the honest framing is
that you are choosing which distortion to accept.

| Convention | How it works | Distortion it accepts | Fits when |
| --- | --- | --- | --- |
| Even split | Divide by number of teams | Punishes small consumers, subsidises large ones | The shared thing is a fixed platform cost and consumption barely varies |
| Proportional to a usage metric | Split by requests, storage, queries, build minutes | The metric is chosen arbitrarily and drives gaming of that metric | Consumption varies widely and a defensible metric exists |
| Proportional to attributed spend | Split by each team's directly attributed cost | Assumes shared usage tracks direct usage, which is often false for platform tooling | You need something quick and nobody is disputing it yet |
| Unallocated platform bucket | Charge nobody; report as platform cost | Nobody optimises it except the platform team | The platform team genuinely owns the decisions that move it |

Worked example, a 12,000 per month shared cluster with 30% idle:

- Even split across 6 teams: 2,000 each. A team running two small cron jobs pays the same
  as the team running the main API, and will say so at the first review.
- Proportional to CPU requests, idle charged back proportionally: the API team at 55% of
  requests pays 6,600, cron team at 2% pays 240.
- Proportional to CPU requests, idle held centrally: the same ratios applied to 8,400 of
  used capacity, with 3,600 reported as platform headroom — which makes the idle visible
  as a number the platform team owns, and is usually the most useful split.

Whichever you pick: write it in the header of the report, keep it stable for at least a
year, and re-open it only with the same deliberation as changing an SLO.

## What stays unattributable

Some spend has no honest owner: enterprise support, the organisation's baseline logging,
a security tool mandated centrally, the cost of the accounts themselves. Report it as a
named line rather than spreading it thinly to make the columns add up. A visible
platform line invites the right question — is this worth what it costs — while a
smeared one only produces arguments about the smear.
