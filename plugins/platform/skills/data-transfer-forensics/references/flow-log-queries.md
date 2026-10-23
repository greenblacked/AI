# Flow log collection and queries

Read this in steps 2 to 5. It covers AWS, where the fields are richest; the Google Cloud
and Azure differences are in the fix catalogue. Column names below follow the usual Athena
DDL for flow logs, where each hyphen in a field name becomes an underscore; adjust them to
your table.

## Contents

- Creating the flow logs
- Building the owner map
- Pod address snapshots
- Query: between zones
- Query: NAT gateway processing
- Query: internet egress
- Reconciling against the bill

## Creating the flow logs

```bash
aws ec2 create-flow-logs --resource-type VPC --resource-ids vpc-0abc \
  --traffic-type ALL --max-aggregation-interval 60 \
  --log-destination-type s3 --log-destination arn:aws:s3:::example-flow-logs/prod/ \
  --destination-options FileFormat=parquet,HiveCompatiblePartitions=true,PerHourPartition=true \
  --log-format '${version} ${account-id} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${az-id} ${srcaddr} ${dstaddr} ${pkt-srcaddr} ${pkt-dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status} ${flow-direction} ${traffic-path} ${pkt-src-aws-service} ${pkt-dst-aws-service}'
```

Keep the single quotes: the `${...}` placeholders are for the flow log service, not the
shell. Create the Athena table from the provider's documented DDL for this format, with
partition projection so queries over a week do not scan a year.

Flow logs are billed per gigabyte delivered. Collect a representative window and remove
them, or keep them only on the VPCs that carry the bill line.

## Building the owner map

Export subnets and interfaces, then turn them into two lookup tables with this
standard-library script. Save it outside the export directory and run it with
`python3 -I owner_map.py subnets.json enis.json`; it writes `ip_zone.csv` and
`ip_owner.csv` to the current directory.

```bash
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-0abc > subnets.json
aws ec2 describe-network-interfaces --filters Name=vpc-id,Values=vpc-0abc > enis.json
```

```python
#!/usr/bin/env python3
"""Write ip_zone.csv and ip_owner.csv from describe-subnets and describe-network-interfaces output."""

import csv
import ipaddress
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    subnets = json.load(handle)["Subnets"]
with open(sys.argv[2], encoding="utf-8") as handle:
    interfaces = json.load(handle)["NetworkInterfaces"]

with open("ip_zone.csv", "w", newline="", encoding="utf-8") as out:
    writer = csv.writer(out)
    for subnet in subnets:
        if "CidrBlock" not in subnet:  # IPv6-only subnet: no IPv4 range to map
            continue
        for address in ipaddress.ip_network(subnet["CidrBlock"]).hosts():
            writer.writerow([str(address), subnet["SubnetId"], subnet["AvailabilityZoneId"]])

with open("ip_owner.csv", "w", newline="", encoding="utf-8") as out:
    writer = csv.writer(out)
    for interface in interfaces:
        attachment = interface.get("Attachment") or {}
        owner = attachment.get("InstanceId") or interface.get("Description", "")
        addresses = [entry["PrivateIpAddress"] for entry in interface.get("PrivateIpAddresses", [])]
        for prefix in interface.get("Ipv4Prefixes", []):
            addresses += [str(a) for a in ipaddress.ip_network(prefix["Ipv4Prefix"])]
        for address in addresses:
            writer.writerow(
                [
                    address,
                    interface["NetworkInterfaceId"],
                    interface.get("InterfaceType", ""),
                    owner,
                ]
            )
```

Upload both files to object storage and define tables over them: `ip_zone(ip, subnet_id,
az_id)` and `ip_owner(ip, interface_id, interface_type, owner)`. Map instance IDs to teams
from their tags in a third small table if the instance ID alone is not meaningful.

## Pod address snapshots

Record pod addresses through the whole window, every five minutes, from a machine with
cluster read access:

```bash
kubectl get pods -A -o json \
  | jq -r --arg t "$(date +%s)" '.items[]
      | select(.status.podIP and .spec.hostNetwork != true)
      | [$t, .status.podIP, .metadata.namespace, .metadata.name,
         (.metadata.ownerReferences[0].name // "")] | @csv' >> pod_snapshots.csv
```

Load it as `pod_snapshots(seen, ip, namespace, pod, workload)` and derive intervals, so a
reused address is attributed to whichever pod held it at the time:

```sql
CREATE OR REPLACE VIEW pod_intervals AS
SELECT ip, namespace, workload, valid_from,
       least(valid_to, coalesce(lead(valid_from) OVER (PARTITION BY ip ORDER BY valid_from),
                                valid_to)) AS valid_to
FROM (
  SELECT ip, namespace, pod, workload, min(seen) AS valid_from, max(seen) + 300 AS valid_to
  FROM pod_snapshots
  GROUP BY ip, namespace, pod, workload
);
```

The `lead` cuts each interval where the address's next holder first appears, and the joins
below treat an interval as half-open (`start >= valid_from AND start < valid_to`). Without
both, a flow starting exactly at a hand-over, or in the overlap that snapshot jitter
creates, matches two pods and every byte is counted twice.

## Query: between zones

```sql
WITH f AS (
  SELECT srcaddr, dstaddr, dstport, az_id, bytes, "start"
  FROM vpc_flow_logs
  WHERE flow_direction = 'egress' AND action = 'ACCEPT'
  -- add the partition predicate for the window here
)
SELECT
  coalesce(ps.namespace || '/' || ps.workload, src_owner.owner, f.srcaddr) AS source,
  coalesce(pd.namespace || '/' || pd.workload, dst_owner.owner, f.dstaddr) AS destination,
  f.az_id AS source_zone, dz.az_id AS destination_zone, f.dstport,
  round(sum(f.bytes) / 1e9, 1) AS gb
FROM f
JOIN ip_zone dz ON dz.ip = f.dstaddr
LEFT JOIN pod_intervals ps ON ps.ip = f.srcaddr
       AND f."start" >= ps.valid_from AND f."start" < ps.valid_to
LEFT JOIN pod_intervals pd ON pd.ip = f.dstaddr
       AND f."start" >= pd.valid_from AND f."start" < pd.valid_to
LEFT JOIN ip_owner src_owner ON src_owner.ip = f.srcaddr
LEFT JOIN ip_owner dst_owner ON dst_owner.ip = f.dstaddr
WHERE dz.az_id <> f.az_id
GROUP BY 1, 2, 3, 4, 5
ORDER BY gb DESC
LIMIT 50;
```

The inner join on `ip_zone` keeps only destinations inside the VPC; `az_id` on the record
is the zone of the sending interface because only egress records are kept.

That query misses one leg. A workload's upload through a NAT gateway in another zone has
the external address as `dstaddr` on the workload's own egress record, so it never joins
`ip_zone`, yet the bytes cross a zone to reach the gateway. Count that leg from the NAT
interface's ingress records, where `srcaddr` is the workload and `az_id` is the gateway's
zone, and add the result to the zone total:

```sql
SELECT
  coalesce(o.owner, f.srcaddr) AS source, sz.az_id AS source_zone,
  f.az_id AS nat_zone, round(sum(f.bytes) / 1e9, 1) AS gb
FROM vpc_flow_logs f
JOIN ip_zone sz ON sz.ip = f.srcaddr
LEFT JOIN ip_owner o ON o.ip = f.srcaddr
WHERE f.interface_id = 'eni-0natgateway'
  AND f.flow_direction = 'ingress' AND f.action = 'ACCEPT'
  AND sz.az_id <> f.az_id
  -- add the partition predicate for the window here
GROUP BY 1, 2, 3
ORDER BY gb DESC
LIMIT 50;
```

The return leg, the gateway sending the response to the workload, is already in the
first query as an egress record with an in-VPC destination.

## Query: NAT gateway processing

Find the NAT gateway's interface ID first (`aws ec2 describe-nat-gateways`). On that
interface `srcaddr` or `dstaddr` is always the gateway's own address; the original
endpoints are in `pkt_srcaddr` and `pkt_dstaddr`. Every byte is logged twice, once arriving
and once leaving, so keep the egress records only: an upload leaves towards the internet
and a download leaves towards the workload, each byte once. Excluding records that carry
the gateway's own address would exclude all of them and return no rows.

```sql
SELECT
  CASE WHEN s.ip IS NOT NULL THEN f.pkt_srcaddr ELSE f.pkt_dstaddr END AS workload,
  CASE WHEN s.ip IS NOT NULL THEN f.pkt_dstaddr ELSE f.pkt_srcaddr END AS external,
  CASE WHEN s.ip IS NOT NULL THEN 'upload' ELSE 'download' END AS direction,
  coalesce(f.pkt_dst_aws_service, f.pkt_src_aws_service) AS aws_service,
  round(sum(f.bytes) / 1e9, 1) AS gb
FROM vpc_flow_logs f
LEFT JOIN ip_zone s ON s.ip = f.pkt_srcaddr
LEFT JOIN ip_zone d ON d.ip = f.pkt_dstaddr
WHERE f.interface_id = 'eni-0natgateway'
  AND f.flow_direction = 'egress' AND f.action = 'ACCEPT'
  AND (s.ip IS NULL) <> (d.ip IS NULL)
  -- add the partition predicate for the window here
GROUP BY 1, 2, 3, 4
ORDER BY gb DESC
LIMIT 50;
```

A side that matches `ip_zone` is inside the VPC, whatever its CIDR, so secondary ranges and non-octet-aligned blocks classify correctly; rebuild `ip_zone` if subnets changed in the window. Run `SELECT count(*)` over the same
predicate first: zero rows means the interface ID or the direction filter is wrong, not that
the gateway is idle. A large `aws_service` value such as S3 in the same region is the
gateway endpoint finding. Join `workload` to the owner tables as in the zone query.

## Query: internet egress

```sql
SELECT coalesce(o.owner, f.pkt_srcaddr) AS source, f.dstaddr, f.dstport,
       round(sum(f.bytes) / 1e9, 1) AS gb
FROM vpc_flow_logs f
LEFT JOIN ip_owner o ON o.ip = f.pkt_srcaddr
WHERE f.flow_direction = 'egress' AND f.action = 'ACCEPT'
  AND NOT regexp_like(f.dstaddr, '^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.)')
  AND f.pkt_dst_aws_service IS NULL
  -- add the partition predicate for the window here
GROUP BY 1, 2, 3
ORDER BY gb DESC
LIMIT 50;
```

A NAT gateway is a route target, so a workload's own egress record keeps the real external
address as `dstaddr` and passes the address test; the gateway's interface then logs the
same bytes again. Count the NAT path once: take NAT-routed internet egress from the
gateway interface's egress records only (`interface_id = 'eni-0natgateway'`, attributed by
`pkt_srcaddr`), and leave out workload-interface records from subnets whose default route
is a NAT gateway. Keep workload-interface records only for subnets routed straight to an
internet gateway. The simplest form is to list the NAT-routed subnets from the route tables
and add `AND f.subnet_id NOT IN (...)` to the workload branch, with a second branch over the
gateway interface. Counting both overstates internet egress against the bill, which charges
those bytes once as internet egress and once as NAT processing.

Excluding records with an AWS service destination drops same-region service traffic,
which pays NAT processing but not internet egress. Check the remaining top destinations by
reverse lookup or the provider's published address ranges before concluding they are the
internet: a destination in another region of the same provider bills as inter-region.

## Reconciling against the bill

Sum each class over the same window, scale to a month, and set it beside the bill:

| Class | Flow log figure to compare | Bill quantity |
| --- | --- | --- |
| Between zones | Zone query total, times two | `DataTransfer-Regional-Bytes` |
| NAT processing | NAT query total, both directions | `NatGateway-Bytes` |
| Internet egress | Internet query total | `DataTransfer-Out-Bytes` |

`DataTransfer-Regional-Bytes` also covers other in-region transfer, such as same-region
peering and traffic to public addresses in the same region, so include those flows in the
zone total if the account has them.

Within about a tenth, rank. Outside it, look for VPCs or accounts without flow logs,
traffic from services that bill transfer on their own line, and joins that silently drop
rows, before blaming any flow.
