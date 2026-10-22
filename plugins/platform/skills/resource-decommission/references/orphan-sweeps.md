# Orphan sweeps

Read this when running the scheduled sweep. Every hit is a candidate for the decommission
workflow, not something to delete from the sweep's output. An unattached disk may be a
deliberately detached recovery copy; a reserved address may be allow-listed by a partner.

## Contents

- AWS
- Google Cloud
- Azure
- Kubernetes
- Turning hits into work

## AWS

Most EC2 inventory is regional, so loop over every enabled region. Assign the region list
on its own line before the loop: `set -e` does not apply to a command substitution in a
`for` word list, so an expired token would print nothing and exit 0, which reads as "no
orphans".

```bash
set -Eeuo pipefail
regions="$(aws ec2 describe-regions --query 'Regions[].RegionName' --output text)"
[ -n "$regions" ] || { echo "no regions returned" >&2; exit 1; }
for r in $regions; do
  echo "== $r unattached volumes"
  aws ec2 describe-volumes --region "$r" --filters Name=status,Values=available \
    --query 'Volumes[].[VolumeId,Size,CreateTime]' --output text
  echo "== $r unassociated elastic IPs"
  aws ec2 describe-addresses --region "$r" \
    --query 'Addresses[?AssociationId==null].[PublicIp,AllocationId]' --output text
  echo "== $r detached network interfaces"
  aws ec2 describe-network-interfaces --region "$r" --filters Name=status,Values=available \
    --query 'NetworkInterfaces[].[NetworkInterfaceId,Description]' --output text
done
```

Snapshots older than a cut-off, and the ones you cannot delete because an image uses them,
for one region at a time:

```bash
set -Eeuo pipefail
r=eu-west-1
aws ec2 describe-snapshots --region "$r" --owner-ids self \
  --query "Snapshots[?StartTime<='2026-01-01'].[SnapshotId,VolumeId,StartTime]" --output text
aws ec2 describe-images --region "$r" --owners self \
  --query 'Images[].BlockDeviceMappings[].Ebs.SnapshotId' --output text
```

A snapshot whose source volume no longer exists is the common orphan; one that backs a
registered image fails to delete until the image is deregistered, and that image is its own
candidate.

Target groups with nothing registered, in the same region:

```bash
set -Eeuo pipefail
tgs="$(aws elbv2 describe-target-groups --region "$r" --query 'TargetGroups[].TargetGroupArn' --output text)"
for tg in $tgs; do
  n="$(aws elbv2 describe-target-health --region "$r" --target-group-arn "$tg" \
        --query 'length(TargetHealthDescriptions)' --output text)"
  if [ "$n" = "0" ]; then
    echo "empty target group: $tg"
  fi
done
```

Then read `RequestCount` or `NewFlowCount` for each load balancer over the window, as in
`usage-evidence.md`. Trusted Advisor's checks for idle load balancers, underutilised EBS
volumes and unassociated Elastic IP addresses cover the same ground where your support
plan includes them.

## Google Cloud

```bash
set -Eeuo pipefail
gcloud compute disks list --project="$project" --filter="-users:*" \
  --format="table(name,zone.basename(),sizeGb,lastDetachTimestamp)"
gcloud compute addresses list --project="$project" --filter="status=RESERVED" \
  --format="table(name,region.basename(),address)"
gcloud compute snapshots list --project="$project" --sort-by=creationTimestamp \
  --format="table(name,sourceDisk.basename(),creationTimestamp)"
gcloud recommender recommendations list --project="$project" --location="$zone" \
  --recommender=google.compute.disk.IdleResourceRecommender
```

`lastDetachTimestamp` dates when a disk lost its last user; a disk that has never been
attached has none. The idle-resource recommenders are a second opinion based on Google's
own usage reading, not evidence for the record on their own.

## Azure

```bash
set -Eeuo pipefail
az disk list --query "[?diskState=='Unattached'].{name:name, rg:resourceGroup, sizeGb:diskSizeGb}" -o table
az network public-ip list \
  --query "[?ipConfiguration==null && natGateway==null].{name:name, rg:resourceGroup, ip:ipAddress}" -o table
az network nic list --query "[?virtualMachine==null && privateEndpoint==null].{name:name, rg:resourceGroup}" -o table
az snapshot list --query "[].{name:name, rg:resourceGroup, created:timeCreated}" -o table
az advisor recommendation list --category Cost -o table
```

Run per subscription. Azure Resource Graph runs the same queries across every
subscription you can read, which suits a scheduled report.

## Kubernetes

Released persistent volumes keep their backing disk when the reclaim policy is `Retain`:

```bash
set -Eeuo pipefail
kubectl get pv -o json | jq -r '
  .items[]
  | select(.status.phase == "Released")
  | [.metadata.name,
     ((.spec.claimRef.namespace // "") + "/" + (.spec.claimRef.name // "")),
     .spec.persistentVolumeReclaimPolicy]
  | @tsv'
```

Services of type `LoadBalancer` hold a cloud load balancer and often an address; one whose
EndpointSlices list no endpoints is serving nothing:

```bash
set -Eeuo pipefail
kubectl get svc -A -o json | jq -r '
  .items[] | select(.spec.type == "LoadBalancer")
  | "\(.metadata.namespace) \(.metadata.name)"' \
  | while read -r ns name; do
      if kubectl get endpointslices -n "$ns" -l "kubernetes.io/service-name=$name" -o json < /dev/null \
          | jq -e '[.items[].endpoints[]?] | length == 0' > /dev/null; then
        echo "no endpoints: $ns/$name"
      fi
    done
```

## Turning hits into work

1. Record each hit with its account or project, region, age and tags.
2. Group by owner tag; a hit with an owner goes to that owner with a date.
3. Hits with no owner go through the decommission workflow from step 1, with the
   announcement and deadline it requires.
4. Count hits by type from month to month. A type that keeps reappearing names a process
   that leaks it (a template without `deleteOnTermination`, a pipeline that never releases
   addresses), and fixing that process is worth more than the sweep.
