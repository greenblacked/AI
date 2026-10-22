# Fix catalogue

Read this in step 6, once flows are priced and ranked. Each fix names what it costs to run
and what it gives up, because a transfer saving that removes zone independence or breaks a
bucket policy is not a saving. Check every price and default against the provider's
current documentation for your region before quoting a figure.

## Contents

- Fixes by finding
- Load balancers and zones
- Kubernetes routing
- Messaging and data stores
- Google Cloud differences
- Azure differences

## Fixes by finding

| Finding | Fix | Running cost | Degrades or risks | Verify |
| --- | --- | --- | --- | --- |
| Same-region S3 or DynamoDB traffic through a NAT gateway | Gateway endpoint associated with the private route tables | None for gateway endpoints | Bucket policies that allow by source IP stop matching; endpoint policies can restrict access unexpectedly | `NatGateway-Bytes` falls; no access-denied errors in the window |
| Other AWS APIs through a NAT gateway (registry, logs, queues, STS) | Interface endpoints for the heaviest services | Hourly per endpoint per zone plus per-GB processing | One more component per zone; private DNS changes resolution for the whole VPC | Compare the endpoint's charges with the NAT processing it removed |
| Workloads routed to a NAT gateway in another zone | One NAT gateway per zone, each private subnet routed to its own zone's gateway | Hourly charge per extra gateway | None beyond the cost; it also removes a cross-zone failure dependency | Both `NatGateway-Bytes` and `DataTransfer-Regional-Bytes` fall |
| Image pulls from public registries through NAT | Pull-through cache in the private registry, registry endpoints, and the object storage gateway endpoint, since image layers are served from object storage | Cache storage | The cache becomes part of the recovery path | Pull traffic leaves the NAT query |
| Logs, metrics and traces shipped to a vendor over the internet | Compress at the agent, sample high-volume debug logs, or use the vendor's private connectivity if offered | Vendor or endpoint charges for private connectivity | Less detail when sampling | The vendor's address drops out of the internet query |
| Chatty service pair between zones | Zone-local routing (see Kubernetes routing) or co-locating one side per zone | None | Uneven zones receive uneven load | Pair falls out of the zone query |
| Cacheable content served to the internet from origin | CDN in front; for AWS origins, transfer from the origin to CloudFront is not billed as internet egress | CDN charges | Caching correctness and purge discipline | `DataTransfer-Out-Bytes` falls by more than CDN charges rise |
| Uncompressed payloads between services or to clients | gzip, Brotli or zstd at the producer | CPU | Latency on small payloads; check before enabling for everything | Same request count, fewer bytes |
| Full-copy replication between regions | Replicate only what recovery needs, compress, batch | None | Recovery scope must be re-agreed with whoever owns the RPO | Inter-region usage type falls |

## Load balancers and zones

- **Application Load Balancer:** cross-zone balancing is on by default (it can be turned
  off per target group), and AWS does not bill the load balancer's own traffic to targets
  in other zones as transfer. Check the current
  pricing page before relying on that for a decision.
- **Network Load Balancer:** cross-zone balancing is off by default; turning it on bills
  traffic to targets in other zones. Leave it off unless a zone's targets cannot absorb
  that zone's traffic.
- **Kubernetes behind a load balancer:** in instance mode with
  `externalTrafficPolicy: Cluster`, a node can forward a request to a pod in another zone.
  IP-mode targets that send traffic straight to pods, or `externalTrafficPolicy: Local`,
  avoid the extra hop; `Local` concentrates load on nodes that happen to host more pods.

## Kubernetes routing

- `spec.trafficDistribution: PreferClose` on a Service asks the proxy to prefer endpoints
  in the client's zone. Check the field's status for your Kubernetes version.
- On older clusters the `service.kubernetes.io/topology-mode: Auto` annotation enables
  topology-aware routing, which only takes effect when endpoints are spread across zones
  roughly in proportion to capacity. If it silently does nothing, that safeguard is why.
- A service mesh's locality-aware load balancing achieves the same for meshed traffic.
- Every zone-local scheme needs enough replicas in each zone. Spread replicas with
  topology spread constraints before turning it on, or one zone's pods take that zone's
  whole load.

## Messaging and data stores

- **Kafka consumers:** with `broker.rack` set on brokers, `client.rack` set on consumers and
  `replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector` on the
  brokers, consumers fetch from a replica in their own zone. Producers still write to the
  leader, wherever it is.
- **Read replicas and caches:** route each client's reads to a replica or cache node in
  its own zone where the client library supports it. A provider's own replication for a
  multi-zone database is often not billed as transfer; client traffic to a node in
  another zone is. Read the pricing page for the specific service.
- **Object storage in another region:** a bucket in the wrong region turns every read into
  inter-region transfer. Check the bucket region of the top destinations.

## Google Cloud differences

- VPC Flow Logs are sampled at a configurable rate and aggregated over an interval, so
  totals are estimates. Reconcile with the billing export before ranking.
- Records carry instance and zone details for both ends, and for GKE, pod, namespace and
  workload details, which removes most of the owner-map work. Export them to BigQuery with
  a log sink and run the same aggregations there.
- Traffic between zones in a region is billed, and Cloud NAT bills data processed.
- Private Google Access lets instances without external addresses reach Google APIs
  without Cloud NAT, which is the analogue of the gateway endpoint fix.

## Azure differences

- VNet flow logs are the successor to NSG flow logs, which are being retired; use VNet flow
  logs for new collection. Traffic Analytics aggregates them in a Log Analytics workspace.
- Azure NAT Gateway bills data processed. Service endpoints or private endpoints for
  Azure Storage keep that traffic off the NAT path.
- Check current pricing for transfer between availability zones before treating it as the
  driver; Azure's position has differed from AWS's.
