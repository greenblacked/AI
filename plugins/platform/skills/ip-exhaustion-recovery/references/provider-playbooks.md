# Provider playbooks

Read this in steps 3 to 5, once the ceiling is named. Each section gives the commands, the
arithmetic that has to change with them, and what the change does to routing. Confirm each
setting against the CNI or provider version you run; defaults move between releases.

## Contents

- AWS VPC CNI settings
- Maximum pods per node on AWS
- AWS secondary CIDR with custom networking
- AWS prefix delegation
- Orphaned interfaces
- GKE pod ranges
- AKS
- Overlapping ranges

## AWS VPC CNI settings

| Variable | Effect | Use when |
| --- | --- | --- |
| `WARM_ENI_TARGET` | Spare interfaces kept attached per node; the default of 1 holds a whole interface's addresses idle | Leave at default only when the subnet has room to spare |
| `WARM_IP_TARGET` | Spare addresses kept per node | The subnet is tight and pod churn per node is modest |
| `MINIMUM_IP_TARGET` | Floor of addresses per node, allocated up front | Paired with `WARM_IP_TARGET`, set near the typical pod count per node |
| `ENABLE_PREFIX_DELEGATION` | Assign /28 prefixes to interface slots | The ceiling is pods per node, not subnet space |
| `WARM_PREFIX_TARGET` | Spare prefixes per node in prefix mode | Prefix mode with a tight subnet |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | Pods take addresses from the subnet named in the node's `ENIConfig` | Pods move to a secondary range |
| `ENI_CONFIG_LABEL_DEF` | Node label used to pick the `ENIConfig` | Set to `topology.kubernetes.io/zone` with one `ENIConfig` per zone |

Read the current values before changing them:

```bash
kubectl get daemonset aws-node -n kube-system \
  -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
```

Self-managed CNI:

```bash
kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5 MINIMUM_IP_TARGET=15
```

EKS managed add-on, so an add-on update does not revert the change:

```bash
aws eks update-addon --cluster-name prod --addon-name vpc-cni \
  --configuration-values '{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"15"}}'
```

The numbers above are placeholders. Set `MINIMUM_IP_TARGET` near the usual number of pods
per node and `WARM_IP_TARGET` near the number that start on one node in a deploy burst.

## Maximum pods per node on AWS

Look up the instance's limits:

```bash
aws ec2 describe-instance-types --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.[MaximumNetworkInterfaces,Ipv4AddressesPerInterface]'
```

With N interfaces and A addresses per interface:

| Mode | Maximum pods |
| --- | --- |
| Default | N × (A − 1) + 2 |
| Custom networking (primary interface not used for pods) | (N − 1) × (A − 1) + 2 |
| Prefix delegation | N × (A − 1) × 16 + 2, then capped by AWS's guidance of 110 for instances under 30 vCPUs and 250 otherwise |

For an m5.large (3 interfaces, 10 addresses each) that is 29 by default and 20 with custom
networking. A node group that keeps the default figure after custom networking advertises
pods it cannot address, and those pods sit in `ContainerCreating`.

## AWS secondary CIDR with custom networking

1. Associate the range and create one pod subnet per zone:

   ```bash
   aws ec2 associate-vpc-cidr-block --vpc-id vpc-0abc --cidr-block 100.64.0.0/16
   aws ec2 create-subnet --vpc-id vpc-0abc --availability-zone eu-west-1a \
     --cidr-block 100.64.0.0/19
   ```

2. Associate each new subnet with the same route table as the node subnet in its zone, so
   pod egress follows the same NAT path.
3. Create one `ENIConfig` per zone, named after the zone:

   ```yaml
   apiVersion: crd.k8s.amazonaws.com/v1alpha1
   kind: ENIConfig
   metadata:
     name: eu-west-1a
   spec:
     subnet: subnet-0pods1a
     securityGroups:
       - sg-0nodes
   ```

4. Enable custom networking on the CNI:

   ```bash
   kubectl set env daemonset aws-node -n kube-system \
     AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
     ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
   ```

5. Recalculate maximum pods for the node group, then roll nodes. Existing nodes keep their
   current interfaces until replaced.

Routing consequences:

- Pod traffic to addresses inside the VPC keeps the pod address, so security groups and
  network ACLs inside the VPC must admit the new range.
- Pod traffic to addresses outside the VPC's ranges is translated to the node's primary
  address by the CNI by default, so peers and on-premises firewalls keep seeing node-subnet
  addresses. Changing that behaviour exposes the 100.64 range to them; keep it if you can.
- Do not advertise the 100.64 range over peering, transit or VPN. Kept local, the same
  range can be reused in every VPC.

## AWS prefix delegation

- Needs Nitro-based instances and applies to interfaces created after it is enabled; roll
  the nodes.
- Every prefix needs a contiguous, aligned /28 free in the subnet. Reserve space first on a
  busy subnet:

  ```bash
  aws ec2 create-subnet-cidr-reservation --subnet-id subnet-0abc \
    --cidr 10.20.32.0/20 --reservation-type prefix
  ```

- Raise maximum pods per node to the prefix-mode figure, within AWS's cap.
- A node in prefix mode reserves 16 addresses at a time, so on a small subnet it can hold
  more idle addresses than tuned per-address mode. Use `WARM_PREFIX_TARGET`, or
  `WARM_IP_TARGET` and `MINIMUM_IP_TARGET`, which also apply in prefix mode.

## Orphaned interfaces

```bash
aws ec2 describe-network-interfaces --filters Name=status,Values=available \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,SubnetId,InterfaceType,RequesterId,Description]' \
  --output table
```

An `available` interface is attached to nothing. Some are created and managed by a service
and come back if deleted while that service still expects them; confirm the owner from the
requester and description, and delete only those whose owner is gone.

## GKE pod ranges

GKE gives each node a pod range sized to at least twice its maximum pods:

| Maximum pods per node | Range per node |
| --- | --- |
| 8 | /28 |
| 9–16 | /27 |
| 17–32 | /26 |
| 33–64 | /25 |
| 65–110 | /24 |

A /16 pod range at the default 110 pods per node therefore supports 256 nodes, however few
pods each runs. Two levers, both on new node pools because an existing pool's maximum pods
cannot be changed:

- Create pools with a lower `--max-pods-per-node` where the workload never needs 110.
- Add another secondary range to the subnet and create new pools that take pod
  addresses from it:

  ```bash
  gcloud compute networks subnets update nodes-subnet --region europe-west1 \
    --add-secondary-ranges=pods-2=100.64.0.0/16
  gcloud container node-pools create pool-b --cluster prod --region europe-west1 \
    --pod-ipv4-range=pods-2 --max-pods-per-node=32
  ```

GKE accepts several non-RFC 1918 ranges for pods; check the current documented list before
choosing one.

## AKS

- Classic Azure CNI with node-subnet addressing reserves maximum-pods addresses per node in
  the VNet subnet when the node is created, whether or not pods use them. That is the usual
  cause of an exhausted AKS subnet.
- Azure CNI Overlay assigns pod addresses from a private range outside the VNet, so pods no
  longer consume VNet space. An in-place update from classic Azure CNI exists
  (`az aks update --network-plugin-mode overlay --pod-cidr ...`); read the current
  prerequisites and limitations before using it on a production cluster.
- Azure reserves five addresses in every subnet, as AWS does.

## Overlapping ranges

| Option | What it gives | Limits |
| --- | --- | --- |
| PrivateLink (AWS) or Private Service Connect (Google Cloud) | One service published into the other network through an endpoint with a local address | Per service, not per network; connections are initiated by the consumer |
| AWS private NAT gateway in a routable subnet | Workloads in the overlapping range initiate connections to the other side through non-overlapping addresses | Outbound only; inbound needs a load balancer in the routable subnet |
| NAT at an on-premises or cloud edge | Same idea, for hybrid links | Every translated flow loses its original source address in the far side's logs |
| Renumbering | The overlap is gone | A migration; plan it with `plan-platform-migration` |
