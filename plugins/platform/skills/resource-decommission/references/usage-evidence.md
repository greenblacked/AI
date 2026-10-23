# Evidence of no use

Read this before choosing the evidence window. A zero is only evidence when the signal was
being collected for the whole window and would have recorded the caller you are worried
about.

## Contents

- Choosing the window
- Signal per resource type
- Reading a CloudWatch metric over the window
- Azure Monitor and Google Cloud Monitoring
- Identities and keys
- Non-zero readings that are not users

## Choosing the window

Start from the longest periodic job anyone can name: month-end close, quarter-end
reporting, an annual audit export, a yearly certificate or licence renewal. The window
must contain at least one run of it. When nobody can name the cycle, a full calendar month
including a month-end is the minimum, and a quarter-end is better for anything near
finance, billing or reporting.

Then check the signal's retention against that window. If the history is shorter than the
window, the window starts the day you enable the signal, not the day you ask the question.

| Signal | Retention to check |
| --- | --- |
| CloudWatch metrics | One-minute data for 15 days, five-minute for 63 days, one-hour for 455 days; query with a period of an hour or more for long windows |
| Azure Monitor platform metrics | 93 days |
| Google Cloud Monitoring metrics | Varies by metric; check before relying on it |
| CloudTrail management events | 90 days in event history; longer only if a trail delivers them somewhere |
| Flow logs, DNS query logs, access logs, data-event logs | Only what was configured, from the day it was configured |

## Signal per resource type

| Resource | Signal that shows a caller | Notes |
| --- | --- | --- |
| Application Load Balancer | `RequestCount` in `AWS/ApplicationELB`, dimension `LoadBalancer` | Sum per day |
| Network Load Balancer | `NewFlowCount` in `AWS/NetworkELB` | A health checker in front of it still counts |
| Classic Load Balancer | `RequestCount` in `AWS/ELB`, dimension `LoadBalancerName` | |
| RDS or Aurora | `DatabaseConnections` in `AWS/RDS` | Maximum, not average; then name every connecting client from the engine's own session view |
| Lambda | `Invocations` in `AWS/Lambda` | |
| SQS | `NumberOfMessagesSent` and `NumberOfMessagesReceived` in `AWS/SQS` | A queue with receives but no sends has a consumer that will notice |
| DynamoDB | `ConsumedReadCapacityUnits` and `ConsumedWriteCapacityUnits` | |
| NAT gateway | `ActiveConnectionCount` and `BytesOutToDestination` in `AWS/NATGateway` | |
| S3 bucket | CloudTrail data events or server access logs | Neither is on by default; request metrics are opt-in too |
| EC2 instance or anything with a network interface | VPC Flow Logs on its interfaces | CPU and network metrics show activity, not who is calling |
| A hostname | DNS query logs (Route 53 query logging or Resolver query logging) | Shows lookups, which find callers that never reach a metric |
| Kubernetes Service | The ingress controller's or service mesh's request metrics for that Service | Also check the Service's EndpointSlices for whether anything backs it |
| Azure resource | Its Azure Monitor platform metric (for example `TotalRequests` on an Application Gateway) | |
| Google Cloud resource | Its Cloud Monitoring metric (for example `loadbalancing.googleapis.com/https/request_count`) | Data Access audit logs are off by default for most services |

## Reading a CloudWatch metric over the window

```bash
set -Eeuo pipefail
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/example-alb/0123456789abcdef \
  --start-time 2026-07-01T00:00:00Z --end-time 2026-10-01T00:00:00Z \
  --period 86400 --statistics Sum \
  --query 'sort_by(Datapoints, &Timestamp)[].[Timestamp, Sum]' --output text
```

A day with no datapoint is not the same as a day with zero: CloudWatch omits periods with
no data. For a resource that publishes the metric only while active, missing days mean
idle; for one that should always publish, missing days mean the signal was not there.

## Azure Monitor and Google Cloud Monitoring

```bash
set -Eeuo pipefail
az monitor metrics list --resource "$resource_id" \
  --metric TotalRequests --interval P1D --aggregation Total \
  --start-time 2026-07-01T00:00:00Z --end-time 2026-10-01T00:00:00Z -o table
```

For Google Cloud, read the metric over the window in Metrics Explorer or through the
Monitoring API's time series listing; the gcloud CLI manages dashboards and alerting but
is not the tool for reading long series.

## Identities and keys

```bash
set -Eeuo pipefail
aws iam get-role --role-name example-reporting-role --query 'Role.RoleLastUsed'
aws iam get-access-key-last-used --access-key-id "$key_id"
job="$(aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/example-reporting-role --query JobId --output text)"
# The report is built asynchronously; reading it early returns an empty list, which looks
# exactly like "no service used". Wait for COMPLETED and treat anything else as no answer.
while [ "$(aws iam get-service-last-accessed-details --job-id "$job" \
          --query JobStatus --output text)" = "IN_PROGRESS" ]; do sleep 2; done
status="$(aws iam get-service-last-accessed-details --job-id "$job" --query JobStatus --output text)"
[ "$status" = "COMPLETED" ] || { echo "access report $status: no evidence" >&2; exit 1; }
aws iam get-service-last-accessed-details --job-id "$job" \
  --query 'ServicesLastAccessed[?LastAuthenticated!=null].[ServiceNamespace,LastAuthenticated]' \
  --output text
```

IAM tracks role last use over a trailing 400 days; an empty `RoleLastUsed` means no use in
that period, not never. Last-used data lags real activity by hours, so do not read it
minutes after a scream test starts. On Google Cloud, Policy Analyzer's activity analysis
reports when a service account or key last authenticated.

## Non-zero readings that are not users

Name each one rather than rounding it to zero:

- Load balancer and uptime health checks, synthetic monitors.
- Backup agents, snapshot jobs and replication from a primary.
- Monitoring exporters holding a database connection open.
- Security scanners and inventory tools.
- Another environment's configuration still pointing at it by mistake, which is a real
  dependency and goes on the step 2 list.

Once every source is named and none is a user, the reading counts as no use. One you cannot
name is a caller until proved otherwise.
