# Slicing and the dependency graph

Read this at steps 2 and 3, before choosing where to cut. It turns the state's recorded
dependencies into a module-level graph, measures what a proposed boundary costs, and gives
the patterns for replacing a reference that will cross it.

## Contents

- Rolling edges up to modules
- Counting what a boundary cuts
- Finding cycles
- The layer table
- Replacing a cross-stack reference

## Rolling edges up to modules

`edges.tsv` from step 2 has one row per resource dependency: `consumer<TAB>producer`. Both
are resource addresses without instance keys. Collapse each to its top-level module, or to
`root` for resources in the root module:

```bash
set -Eeuo pipefail
top() { awk -F'\t' '{
  for (i = 1; i <= 2; i++) {
    gsub(/\[[^]]*\]/, "", $i);   # module.app["a.b"] must not split on the dot in the key
    split($i, p, ".");
    m[i] = (p[1] == "module") ? "module." p[2] : "root";
  }
  if (m[1] != m[2]) print m[1] "\t" m[2];
}'; }
top < edges.tsv | sort | uniq -c | awk '{ print $1 "\t" $2 "\t" $3 }' \
  | sort -rn > module-edges.tsv
head -40 module-edges.tsv
```

Each line reads as count, consumer module, producer module: that many resource
dependencies run from the first to the second. The heaviest edges are the pairs that most
want to stay together or most need a clean interface between them.

The state's `dependencies` reflect the last apply of each instance. References added in
configuration since then, and references through locals or module outputs, are better seen
in `terraform graph`; use both, and treat an edge in either as real.

## Counting what a boundary cuts

Write the proposed assignment as `module<TAB>stack` in `assignment.tsv`, one line per
top-level module plus `root`, then count the edges that cross stacks and their direction:

```bash
set -Eeuo pipefail
# assignment.tsv: module.network<TAB>foundation, module.orders_db<TAB>data, root<TAB>apps ...
awk -F'\t' 'NR == FNR { s[$1] = $2; next }
  { if (!($2 in s)) u[$2]; if (!($3 in s)) u[$3];
    c = s[$2]; p = s[$3]; if (c != p) t[c " -> " p] += $1 }
  END { for (k in u) print "UNASSIGNED\t" k;
        for (k in t) print t[k] "\t" k }' assignment.tsv module-edges.tsv | sort -rn
```

Each crossing reads consumer stack -> producer stack. A line starting `UNASSIGNED` is a
module missing from `assignment.tsv`: without it both ends read as the empty stack, compare
equal and the edge drops out of the count unreported.

Every crossing listed must point down the layers, and each one is a reference step 4 has
to replace. A crossing that points up, or two stacks with crossings in both directions,
means the assignment is wrong.

If the awk is harder to trust than the count, do the same in a short script in the
language the team reads; the point is a number per crossing, not this particular pipeline.

## Finding cycles

A cycle at module level is usually one resource in the wrong module: a security group rule
defined beside the application that also references the database's group, or an IAM policy
attached in the module that owns the role it references. List every pair of modules that depend on each other directly; longer cycles show up as
an upward crossing in the count above:

```bash
set -Eeuo pipefail
cut -f2,3 module-edges.tsv | sort -u > forward.txt
awk -F'\t' '{ print $2 "\t" $1 }' forward.txt | sort > reverse.txt
comm -12 forward.txt reverse.txt
```

Each pair printed depends on the other. Find the resources responsible with a grep of
`edges.tsv` for both module names, and move the offending resource into the layer it
belongs in, with a `moved` block inside the monolith, before splitting anything.

## The layer table

| Layer | Typical contents | Changes | Why separate |
| --- | --- | --- | --- |
| Foundation | VPCs and subnets, transit and peering, DNS zones, organisation IAM, KMS keys | Rarely | Everything depends on it; its plan should be short and read in full |
| Data | Databases, buckets, queues, caches holding state | Rarely, carefully | The destroy you cannot undo; keep `prevent_destroy` here and nothing else in the plan |
| Platform | Clusters, node groups, shared load balancers, service mesh | Monthly | Shared by many applications, owned by one team |
| Applications | Per-service roles, queues, DNS records, alarms | Daily | High cadence; split per team so one team's plan does not show another's |

Not every estate needs all four. The test is whether one apply in a stack can reach
something its approver should not be able to break.

## Replacing a cross-stack reference

Three patterns, in order of preference:

| Pattern | Example | Use when |
| --- | --- | --- |
| Data source lookup by a stable identifier | `data "aws_vpc" "main" { tags = { Name = "main" } }` | The object has a stable name or tag the consumer can query; no coupling to the producer's state at all |
| Producer publishes, consumer reads | Producer writes the subnet IDs to a parameter store entry; consumer reads it with a data source | The value is not easily queried, or many consumers need the same set |
| `terraform_remote_state` | Consumer reads the producer's outputs | Producer and consumer are owned by the same people; it grants read on the whole state, secrets included |

After replacing a reference inside the monolith, the plan should show only the new data
source reads. A changed attribute on a resource means the lookup returned something else:
a tag matching two VPCs, a parameter written by a different environment. Fix the lookup;
do not apply the change.
