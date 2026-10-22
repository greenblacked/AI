# Inventory and diff

Read this at steps 2 to 4. The output of this file is three sorted lists of identifiers:
what exists, what is managed, and what is owned by something else. Everything else is
arithmetic on those.

## Contents

- The normalised row
- AWS
- Google Cloud
- Azure
- Extracting identifiers from every state
- Matching the two sides
- Recognising resources another system owns
- The diff

## The normalised row

One tab-separated row per resource, the same columns for every cloud:

```text
cloud  account_or_project  region  type  identifier  tags_or_labels
```

The identifier is the one both sides can produce: an ARN on AWS, the resource path on
Google Cloud, the lower-cased resource ID on Azure. Run discovery with a read-only role.

## AWS

Resource Explorer, per account or across the organisation where multi-account search is set
up, queried in the region holding the aggregator index:

```bash
set -Eeuo pipefail
aws resource-explorer-2 search \
  --query-string "region:eu-west-1 service:ec2" \
  --output json > search.json
jq -r '.Count | "total=\(.TotalResources) complete=\(.Complete)"' search.json
jq -e '.Count.Complete' search.json > /dev/null \
  || { echo "search hit the result cap: slice the query further" >&2; exit 1; }
jq -r '.Resources[] | ["aws", .OwningAccountId, .Region, .ResourceType, .Arn] | @tsv' search.json
```

A search returns a capped number of results; when `Complete` is false, slice the query
further by region, service or `resourcetype:` until it is true. Resource Explorer only
indexes the types it supports and only in regions with an index.

AWS Config, through an aggregator, covers the types its recorders are configured for and
returns each result as a JSON string:

```bash
set -Eeuo pipefail
aws configservice select-aggregate-resource-config \
  --configuration-aggregator-name org-aggregator \
  --expression "SELECT accountId, awsRegion, resourceType, resourceId, arn WHERE resourceType = 'AWS::S3::Bucket'" \
  --output json \
  | jq -r '.Results[] | fromjson | ["aws", .accountId, .awsRegion, .resourceType, (.arn // .resourceId)] | @tsv'
```

Use both where both are available and take the union; each finds things the other misses.

## Google Cloud

Cloud Asset Inventory at organisation scope:

```bash
set -Eeuo pipefail
gcloud asset search-all-resources --scope="organizations/${ORG_ID}" --format=json \
  | jq -r '.[] | ["gcp", .project, .location, .assetType, (.name | sub("^//[^/]+/"; ""))] | @tsv'
```

`.name` is the full resource name, such as
`//compute.googleapis.com/projects/p/zones/z/instances/i`. The `sub` above strips the
`//service.googleapis.com/` prefix, which leaves the `projects/...` path most Google
resources store as their `id` in state. Narrow with `--asset-types` when a single call is
too large.

## Azure

Resource Graph across the subscriptions or management groups the role can read:

```bash
set -Eeuo pipefail
: > azure.tsv
token=""
while :; do
  # order by id keeps the pages stable; without it a page can repeat or skip rows
  az graph query -q "Resources | project id, type, subscriptionId, location | order by id asc" \
    --first 1000 ${token:+--skip-token "$token"} -o json > page.json
  jq -r '.data[] | ["azure", .subscriptionId, .location, .type, (.id | ascii_downcase)] | @tsv' \
    page.json >> azure.tsv
  token="$(jq -r '.skip_token // empty' page.json)"
  [[ -n "$token" ]] || break
done
```

Stopping after the first page would report a thousand resources as the whole estate.

Azure resource IDs are case-insensitive and appear in different cases from different
sources. Lower-case both sides before comparing, or the same resource counts as unmanaged.

## Extracting identifiers from every state

List states from the backends themselves (every key in the state bucket, every workspace
in the remote backend), not from the repositories you know about. Then:

```bash
set -Eeuo pipefail
umask 077
: > managed.tsv
while read -r dir || [[ -n "$dir" ]]; do
  terraform -chdir="$dir" state pull < /dev/null \
    | jq -r '.resources[]? | select(.mode == "managed") | .type as $t | .instances[]
        | [$t, (.attributes.arn // .attributes.self_link // .attributes.id // "")] | @tsv' \
    >> managed.tsv
done < state-roots.txt
```

`state pull` reads the current workspace only. For a root with several workspaces, repeat
the pull per workspace (`TF_WORKSPACE=name`), or the other workspaces' resources count as
unmanaged.

This job reads every state, and every state holds secrets in plaintext. Run it in a
restricted pipeline whose output is the identifier list only, never the state files.

## Matching the two sides

| Cloud | Inventory gives | State gives | Normalise to |
| --- | --- | --- | --- |
| AWS | ARN | `arn` for most types, otherwise only `id` | ARN; for types without `arn` in state, match the state `id` against the final segment of the inventory ARN |
| Google Cloud | `//service.googleapis.com/projects/...` | `id` as `projects/...`, or `self_link` as a URL | The `projects/...` path |
| Azure | Resource ID | `id`, the resource ID | Lower-cased resource ID |

Some console objects are several Terraform resources. An S3 bucket in the inventory
corresponds to `aws_s3_bucket` plus separate resources for versioning, encryption,
lifecycle, policy and public access block in current AWS provider versions. A matched
bucket can still have unmanaged settings; check those resource types per adopted bucket.

The tail rule can over-match a short id such as `default`; review the AWS rows it matched. Record which match rule each row used. A coverage figure built on a fuzzy match should say
so.

## Recognising resources another system owns

| Sign | Owner |
| --- | --- |
| Tag `aws:cloudformation:stack-name` | A CloudFormation stack |
| Tag `aws:autoscaling:groupName` | An Auto Scaling group; adopt the group, not its instances |
| Tags beginning `kubernetes.io/cluster/`, `elbv2.k8s.aws/`, or a cluster-name tag from the managed Kubernetes service | A Kubernetes controller: load balancers, volumes, security groups it created |
| Default VPC, default security groups, IAM roles under the `/aws-service-role/` path | The provider; leave them, or manage the default VPC explicitly by policy |
| Azure resource groups created for a managed cluster's nodes | The managed Kubernetes service |
| Resources tagged or labelled by another IaC or control-plane tool | That tool |

Keep these as an exclusion list with the owning system per row, checked into the same place
as the report. An exclusion with no named owner is an Unknown in disguise.

## The diff

```bash
set -Eeuo pipefail
# Lower-case Azure resource IDs only: ARNs and Google paths are case-sensitive. A Google
# self_link URL is cut down to its projects/... path so it matches the inventory form.
# Blank lines (a state instance with no identifier) are dropped rather than matched against.
norm() { awk '/^https:\/\/[^\/]*googleapis\.com\/.*projects\// { sub(/^.*\/projects\//, "projects/") }
  /^\/[sS][uU][bB][sS][cC][rR][iI][pP][tT][iI][oO][nN][sS]\// { $0 = tolower($0) } $0 != ""' | sort -u; }
cut -f5 inventory.tsv | norm > inventory.ids
cut -f2 managed.tsv | norm > managed.ids
cut -f1 exclusions.tsv | norm > excluded.ids
# An inventory ARN is managed if state holds it whole, or holds only its final segment
# (the AWS types whose state carries a short id). The tail rule is limited to ARNs.
awk 'NR == FNR { m[$0]; next }
  { t = $0; sub(/.*[\/:]/, "", t)
    if (!($0 in m) && !($0 ~ /^arn:/ && (t in m))) print }' managed.ids inventory.ids > not-managed.ids
comm -23 not-managed.ids excluded.ids > unmanaged.ids
wc -l inventory.ids managed.ids excluded.ids unmanaged.ids
```

Before trusting the Google coverage figure, take one resource you know is managed that
carries a `self_link` (a compute instance, say) and confirm its path is absent from
`unmanaged.ids`. A managed resource listed as unmanaged means the two sides still differ in
form.

Then join `unmanaged.ids` back to `inventory.tsv` for type, account and tags, and classify
each row as SKILL.md step 4 describes.
