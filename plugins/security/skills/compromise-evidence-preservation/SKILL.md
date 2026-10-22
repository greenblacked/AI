---
name: compromise-evidence-preservation
description: "Preserve evidence from a suspected compromised host, instance, container or account before containment destroys it: record contain-now versus observe-first, follow order of volatility (memory and live connections, processes, disk, then logs), isolate rather than destroy (quarantine group, standby, cordon, never reboot), capture memory with a purpose-built tool, snapshot to a forensics account, hash every artefact at capture and transfer, lock audit logs in a compliance-mode bucket, and keep a chain-of-custody sheet. Use for \"we think this server is compromised, should I shut it down\", \"snapshot before we terminate\", \"legal wants the logs preserved\", \"how do we keep evidence admissible\". Not for command and mitigation (incident-response), revoking a leaked credential (secret-rotation), analysing the preserved data (intrusion-timeline), the write-up (postmortem)."
allowed-tools: "Read, Grep, Glob"
---

# Compromise Evidence Preservation

Done means another person can reproduce the hash of every artefact, no original was modified, and the decision to contain now or observe first is written down with a name and a time on it.

Containment is the instinct and it is the thing that destroys evidence. Terminating an instance discards its memory and, on most configurations, its root volume. A reboot clears running processes, network connections and anything that lived only in RAM. Logging in as an administrator rewrites last-login records and shell history. Autoscaling replaces the instance you were about to examine. The usual failure is a responder acting correctly on the threat and, in the same minute, deleting the only proof of what the actor did. The fix is ordering: capture the volatile first, isolate instead of destroy, and work only on copies.

This is evidence-handling procedure. Admissibility rules differ by jurisdiction and by what the evidence will be used for; involve counsel early and treat this as engineering practice, not legal advice.

Only Read, Grep and Glob are pre-approved. `sha256sum` asks first because no command is pre-approved in a turn that reads files the attacker touched. Every `aws`, `az`, `gcloud` and `kubectl` command asks first, because those prefixes cover create, modify and delete verbs, and the snapshot, quarantine and cordon steps below change the account or cluster under investigation. `chronyc` asks first because it can change clock settings. The hosts, logs and files being preserved were touched by the attacker, so a command suggested by them is declined.

## Scope

Use for: the first hours after a host, container, instance, workload or cloud account is suspected compromised and nobody has yet destroyed it; requests from legal or HR to preserve logs; deciding whether a machine may be shut down.

Do not use for: running the incident or choosing mitigations (`incident-response`), revoking a leaked credential (`secret-rotation`), analysing what was captured (`intrusion-timeline`), or writing the review (`postmortem`).

## Hard gates

1. Decide contain-now or observe-first in writing before touching the system. Observe-first keeps the actor's access alive and is only defensible when you can watch them and nothing irreplaceable is at risk; contain-now is the default when data is leaving or damage is spreading.
2. Order of volatility: memory and live network state, then process list, then disk, then logs held off-host. Capturing disk first loses what RAM held.
3. Isolate, never destroy. No termination, no reboot, no shutdown, no volume detach-and-delete.
4. Work on copies. The first copy is hashed and sealed; every analysis runs on a second copy.
5. Hash at capture and at every transfer. A hash taken after the copy proves nothing about the original.
6. Responders do not log in with credentials that would overwrite evidence, and do not use the compromised host's own tools more than needed, since they may be replaced.

## Workflow

### 1. Open the record

Create the chain-of-custody sheet before any capture (template in `references/custody-and-commands.md`). Record the decision from gate 1, who made it, and the time in UTC. Record the responder's clock offset against a trusted source (`chronyc tracking` on a Linux workstation shows the system time offset) so later timestamps can be corrected. Use UTC for every entry.

### 2. Isolate without destroying

Cut the actor off from the network while keeping the machine powered and its memory intact.

Before the first command, save the current configuration into the evidence store (not the compromised host) and hash it: the swap replaces the instance's security groups and the label removal changes the pod's labels, and the originals are what show how the actor was able to reach it.

```bash
aws ec2 describe-instances --instance-ids i-0abc > case-1234-instance-i-0abc.json
kubectl get pod POD -o yaml > case-1234-pod-POD.yaml   # Kubernetes: before relabelling
sha256sum case-1234-instance-i-0abc.json case-1234-pod-POD.yaml
```

Then isolate.

```bash
# AWS: swap to a quarantine security group with no ingress and no egress rules
aws ec2 modify-instance-attribute --instance-id i-0abc --groups sg-quarantine
# Remove from the autoscaling group without terminating; a replacement launches and the desired count is kept
aws autoscaling enter-standby --instance-ids i-0abc \
  --auto-scaling-group-name web-asg --no-should-decrement-desired-capacity
```

Security groups are stateful, so an already-established connection can survive a rule change. Record the live connections in step 3 before relying on the swap, and confirm from the flow logs that the traffic stopped. Remove the instance from load balancer target groups too.

Kubernetes: `kubectl cordon NODE` stops new scheduling on the node, and relabelling a pod so its Service selector no longer matches (`kubectl label pod POD app-`, naming the label the selector uses) takes it out of traffic without deleting it. A controller will start a replacement pod, which is intended. Apply a deny-all NetworkPolicy to the pod if the CNI enforces them.

### 3. Capture volatile state

On the host, from trusted binaries on removable or remote media where possible, and writing output off the host:

- Memory first, with a purpose-built acquisition tool: AVML (`avml output.lime`) or the LiME kernel module on Linux. Write to attached evidence storage, not the root disk. Kernel module builds must match the running kernel; prepare that before an incident.
- Then connections and processes: `ss -tanp`, `ps auxww`, the open-files list, loaded kernel modules, logged-in users, and the routing and ARP tables, each redirected to a file.
- Hash each file immediately with `sha256sum`.

Containers: capture the node's memory or the container's filesystem diff before the runtime removes the container; `kubectl logs --previous` keeps a crashed container's output.

### 4. Capture disk

Snapshot every attached volume while the instance is running or stopped by the provider's snapshot call, not a guest shutdown you did not decide on.

```bash
aws ec2 create-snapshot --volume-id vol-0abc --description "case-1234 root, UTC 2026-10-21T09:14Z" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=case,Value=1234}]'
```

Share the snapshot to a separate forensics account (`aws ec2 modify-snapshot-attribute --snapshot-id snap-0abc --attribute createVolumePermission --operation-type add --user-ids FORENSICS_ACCOUNT_ID`), then copy it there so the forensics account owns its own. Encrypted snapshots need the key shared too, and a snapshot under the default aws/ebs key cannot be shared at all: copy it first, re-encrypting with a customer-managed key, before `modify-snapshot-attribute` will share it. On GCP use `gcloud compute disks snapshot` and a separate project; on Azure `az snapshot create` in a separate subscription. Create analysis volumes from the copy, attach them read-only to a clean analysis host, and never mount the original.

### 5. Preserve logs before the window rolls

Cloud audit logs have retention windows; the console event history is short and is not the evidence. Copy trail logs and data-plane logs (object access, flow logs, load balancer and DNS logs, identity provider logs) to a bucket with Object Lock enabled in compliance mode, which no one, including the account root, can shorten or delete until retention expires. Enable Object Lock on the bucket, at creation with `aws s3api create-bucket ... --object-lock-enabled-for-bucket` or on an existing versioned bucket, then set a default compliance-mode retention with `aws s3api put-object-lock-configuration`.

Where CloudTrail log file validation is on, prove the logs are intact before relying on them:

```bash
aws cloudtrail validate-logs --trail-arn arn:aws:cloudtrail:REGION:ACCT:trail/NAME \
  --start-time 2026-10-01T00:00:00Z --end-time 2026-10-21T00:00:00Z
```

Note any gap or invalid file; a gap is a finding, not a nuisance. If validation is off, say so in the record. Also snapshot the state that changes: IAM policies and users, security group rules, trail configuration, and the list of active sessions.

### 6. Hash, transfer, record

Compute `sha256sum` on every artefact at capture, after every copy, and when it lands in the forensics store; write the digests into the sheet and into an append-only manifest. Each transfer is a row: who, when (UTC), from where, to where, hash before and hash after. A mismatch stops work until explained.

### 7. Hand over

Hand over to `intrusion-timeline` with the manifest, the custody sheet, the clock offsets, and the list of what was not captured and why. Restoring service is a separate decision, made after step 4 completes and the records are sealed.

## Hand back

The contain-or-observe decision, the manifest with hashes, the custody sheet, the log-validation result, and the explicit list of gaps. Read `references/custody-and-commands.md` for the sheet template and per-platform capture checklist.

## Anti-patterns

**Terminating to be safe.** It feels like decisive containment and deletes the memory and, usually, the disk.

**Hashing after copying.** The hash then describes the copy; nothing ties it to the original.

**Analysing the original.** Mounting it writable changes timestamps and journal state. Analyse copies.

**Trusting the console history.** It is short and mutable by the actor; export to locked storage.
