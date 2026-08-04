# Migration Transition Patterns

Use this reference after the migration inventory identifies durable state, writers,
consumers, and available traffic controls.

## Contents

- [Pattern selection](#pattern-selection)
- [State authority](#state-authority)
- [Compatibility](#compatibility)
- [Traffic patterns](#traffic-patterns)
- [Data patterns](#data-patterns)
- [Wave design](#wave-design)
- [Pattern failure modes](#pattern-failure-modes)

## Pattern selection

Choose based on the hardest-to-reverse property, not the most visible component.

| Hard property | Prefer | Avoid by default |
| --- | --- | --- |
| Stateful writes | Single writer plus replication | Symmetric dual-write |
| Contract incompatibility | Versioned adapter or facade | Coordinated consumer rewrite |
| Unknown target behavior | Shadow or mirrored reads | Immediate authoritative traffic |
| Large independent population | Representative waves | Random percentage with no cohorts |
| Hard atomic boundary | Short freeze and explicit switch | Pretending an atomic switch is gradual |
| Long coexistence | Strangler with retirement milestones | Permanent compatibility layer |

## State authority

At every phase, write down which system is authoritative for each entity and operation.
“Both” is incomplete until conflict semantics exist.

| Mode | Authority | Required proof |
| --- | --- | --- |
| Copy then switch | Source until cutover | Complete copy, delta capture, final checksum |
| Continuous replication | Source writer, target follower | Lag bound, replay, ordering, deletion behavior |
| Dual-read | Source or target by declared precedence | Difference rate and sampled explanation |
| Dual-write | Named primary plus reconciliation | Idempotency key, retry semantics, conflict queue |
| Target authoritative | Target | Reverse replication or declared no-return point |

Define reconciliation at the business-object level. Row counts can match while balances,
permissions, ordering, or derived state differ. Use domain invariants such as “every paid
invoice has exactly one ledger entry” rather than only storage-level checksums.

## Compatibility

Prefer additive change before subtractive change:

1. Add a new field, endpoint, event version, identity claim, or route while the old one
   continues to work.
2. Move producers or consumers independently.
3. Measure remaining old-path traffic.
4. Reject new old-format creation.
5. Remove old support after observed usage reaches the agreed threshold.

For APIs and events, distinguish tolerant readers from silent data loss. Ignoring an
unknown field is compatible only if that field is not required for correct behavior.

Use a compatibility facade when consumers cannot migrate together. Give it an owner,
traffic metric, removal threshold, and deadline when it is introduced; otherwise it is a
new permanent platform.

## Traffic patterns

### Shadow

Copy requests to the target but discard target responses. Use it to compare correctness,
latency, dependency calls, and capacity without user impact. Scrub or authorize sensitive
data first, and prevent shadow writes unless they go to disposable state.

### Canary

Route a small, identifiable production cohort to the target. Choose cohorts that expose
real diversity but cap damage: internal users, one tenant, one cell, or a low-risk region.
Percentages alone are weak when one tenant carries half the traffic.

### Blue-green

Prepare a complete target and switch routing. It simplifies rollback for stateless paths
but does not solve state rollback. If both colors share a database, the database contract
must remain compatible across the switch.

### Strangler

Put a stable facade in front of old and new implementations and move routes or domains
incrementally. Track the fraction still served by the old path. Remove the facade or
declare it permanent once the last route moves.

## Data patterns

### Bulk copy plus change capture

Take a consistent snapshot, copy it, stream subsequent mutations, validate lag and
reconciliation, briefly freeze or fence writes, apply the tail, then change authority.
Record how deletes and schema changes travel; these are the usual silent gaps.

### Backfill through the application contract

Use when business validation matters more than raw throughput. It is slower but exercises
the same invariants as live writes. Rate-limit it and tag backfill traffic so alerts and
cost can distinguish it.

### Dual-write

Use only when the coexistence window cannot be avoided. Define:

- one idempotency key across both writes;
- which write happens first and what a partial failure means;
- retry ownership and maximum retry age;
- conflict detection and the authoritative winner;
- a reconciliation queue visible to operators;
- an exit date and the evidence required to stop dual-writing.

## Wave design

A useful wave is operationally representative and small enough to recover. Sequence by
learning value before volume:

1. A cooperative low-risk cohort that exercises the full path.
2. A cohort with a distinct dependency or data shape.
3. A normal high-volume cohort.
4. The hardest regulated, stateful, or latency-sensitive cohort.

Do not leave every difficult tenant until the final wave; that creates a second migration
after the team has already declared success.

## Pattern failure modes

| Failure | Detection | Response |
| --- | --- | --- |
| Replication lag grows | Lag age and queue depth | Stop new waves; scale or reduce source rate |
| Shadow output differs | Domain-level comparison | Classify expected vs defect before canary |
| Canary looks healthy globally | Cohort-specific SLI | Make routing cohort a mandatory metric label |
| Rollback loses target writes | Reverse-path rehearsal | Fence writes or reconcile before routing back |
| Compatibility layer grows | Old-path traffic and code ownership | Stop adding features; set retirement gate |
| Cost doubles indefinitely | Cost by old/new path | Treat maximum coexistence duration as a gate |
