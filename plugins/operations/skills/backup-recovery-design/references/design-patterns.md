# Recovery design patterns

Use this reference to turn objectives into a topology and an evidence plan. Product
names do not define a tier; the measured end-to-end recovery path does.

## Tier by business capability

| Tier | Typical protection | Capacity posture | Evidence cadence |
| --- | --- | --- | --- |
| Continuous | Synchronous or near-synchronous replica plus independent point-in-time copies | Hot or warm | Frequent failover and point-in-time restore evidence |
| Rapid | Change-log shipping plus periodic full copy | Warm or pre-provisionable | Production-scale restore each material change or quarter |
| Standard | Periodic incremental and full copies | Cold | Scheduled sample and full restores |
| Archive | Immutable long-retention copies in an isolated domain | Cold, retrieval delay accepted | Media readability and representative restore |

Derive labels from agreed objectives. Do not infer an RPO from backup frequency alone:
completion time, log gaps, upload lag and unusable jobs all change the newest selectable
point. Do not infer an RTO from storage class: provisioning, retrieval, replay, validation
and approval often dominate transfer.

## Copy topology

Use multiple mechanisms when threats differ:

- **Local versions or snapshots** give fast rollback from operator error but usually
  share account, region and administrator risk.
- **Cross-region copies** address a regional failure but may reproduce corruption and
  remain deletable through the same control plane.
- **Isolated immutable copies** address malicious or accidental deletion. Isolation
  includes administrators, keys and policy, not only geography.
- **Logs plus base copies** provide granular points only when logs are continuous from
  the start of the oldest retained base backup through every supported recovery target.
- **Application export** can reduce engine coupling, but increases time and may omit
  engine metadata, permissions or transaction semantics.

Document which threat each copy survives and which common dependencies remain. A “3-2-1”
count is a useful prompt, not proof of administrative or cryptographic independence.

## Timeline budget

Calculate the critical path with measured or explicitly estimated phases:

`disruption-to-detection + detection-to-declaration + authorise + provision + retrieve + restore + replay + reconcile + validate + enable + business acceptance`

Record each component duration rather than adding wall-clock timestamps; parallel phases
overlap. Capture data volume, effective throughput, fixed setup time and concurrency
limits for each phase. Use the slowest dependency path, add decision and retry margin,
and compare the end-to-end duration with RTO. State whether capacity is hot, reserved,
quota-backed or merely expected to be available.

## Acceptance evidence

Existence evidence answers “is there a copy?” Restore evidence answers “can this
capability recover?” Keep both, but do not substitute the first for the second.

An acceptance record identifies the source point, target isolation boundary, versions,
volume, start and finish timestamps, phase timings, integrity queries, business
transactions, security checks, exceptions and approving owner. Store evidence outside
the protected workload so loss of that workload does not erase its recovery history.

Use sampled restores for frequent signal and full production-scale restores for RTO
claims. Sampling can find corrupt objects and missing permissions; it cannot establish
throughput, quota, dependency order or full-dataset integrity.

## Cost decisions

Model retained bytes over time, not only current source size. Include daily change rate,
full-copy cadence, compression, minimum storage duration, operation charges, replication,
retrieval and egress, warm compute, licences, exercises and staff time. Present the
marginal cost and objective improvement together, such as the annual cost of reducing
RTO from eight hours to two. This makes residual risk an owned business decision.
