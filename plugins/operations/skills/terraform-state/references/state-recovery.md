# Recovering state

Read this when state is corrupt, truncated or rolled back, when it is gone entirely, when
an apply was killed part way through, or straight after breaking a lock that a live
process might have been holding.

## Contents

- Stop first
- Work out which failure you have
- Get a known-good copy back
- Pushing a state back
- Rebuilding state that is genuinely gone
- After a killed apply
- Proving you are finished

## Stop first

Every recovery is made worse by a second apply. Announce that the workspace is frozen,
and if the pipeline applies on merge, disable it before doing anything else — an automated
apply against a half-recovered state destroys the resources the state has forgotten.

Take a copy of the damaged state before you repair it. A corrupt state still contains the
resource ids you are about to need, and the repair is easier to check when you can diff
against what you started with.

```bash
set -Eeuo pipefail
umask 077
work="$(mktemp -d)"
terraform state pull > "$work/damaged.tfstate" || echo "pull failed; fall back to the backend copy"
```

## Work out which failure you have

| Symptom | What happened | Path |
| --- | --- | --- |
| `state snapshot was created by Terraform vX, which is newer than current` | Someone applied with a newer binary | Match the binary version; do not downgrade the state |
| `Failed to load state: unexpected end of JSON input` | Write was truncated | Restore from a backend version |
| Plan wants to create everything | Empty or replaced state, or the wrong backend key | Check the backend configuration before concluding it is lost |
| Plan wants to create some things that exist | Partial write, or an apply killed mid-flight | Re-import the missing resources |
| A push refused because the lineage does not match | The state you hold is from a different history | Do not force; find out which lineage is live |
| Serial went backwards | A restore overwrote later applies | Recover the newer version first, then decide |

Lineage is a random id generated when a state is first created and carried through every
later write. Two files with different lineages are two different histories, not two
versions of one, and reconciling them by force means one set of resources stops being
managed.

## Get a known-good copy back

Object versioning on the backend bucket is what makes this a five-minute job rather than a
rebuild, which is the argument for enabling it before you need it.

- **S3**: list object versions for the state key and download the last one whose size and
  timestamp look right.
- **GCS**: object versioning lists generations for the same object.
- **Azure**: blob snapshots, or soft delete if it was removed rather than overwritten.
- **HCP Terraform and Terraform Enterprise**: the workspace keeps a state version history
  with the run that produced each, which also tells you which apply did the damage.
- **Local**: `terraform.tfstate.backup` beside the state file is the previous version and
  only the previous one.

Download into the temporary directory, not over the top of the live file, and read the
serial before you trust it:

```bash
set -Eeuo pipefail
jq -r '"serial=\(.serial) lineage=\(.lineage) version=\(.version) resources=\(.resources | length)"' "$work/candidate.tfstate"
```

## Pushing a state back

`terraform state push` refuses two things by design: a differing lineage, and a serial
lower than the one already in the backend. Both refusals mean you are about to lose
writes, so treat them as questions rather than obstacles. `-force` exists and is almost
never the right answer; when it genuinely is, take a copy of what you are overwriting
first.

```bash
set -Eeuo pipefail
terraform state push "$work/candidate.tfstate"
terraform plan -detailed-exitcode
```

A restored state is one serial behind whatever applied after it, so expect the plan to
show the difference. Read that plan as the list of what the lost writes did, and decide
per resource whether to re-apply or re-import it.

## Rebuilding state that is genuinely gone

With no recoverable copy, the state is rebuilt by adopting the live infrastructure back.
It is slow and it is survivable, and it is the reason the import path is worth knowing
before you need it.

1. Inventory what exists, from the provider rather than from memory: the console, a
   resource-group or tag query, or the cloud provider's own export.
2. Write `import` blocks for the resources the configuration already describes, in
   dependency order — networks and identities before the things that reference them.
3. Plan after each batch. An import that is followed by a proposed destroy means the
   address does not match the object.
4. Anything the configuration does not describe stays out until someone decides it should
   be managed. Importing an object to make an inventory tidy is how a resource nobody
   understands acquires a destroy path.

## After a killed apply

An apply that was interrupted may have created objects it never recorded, and the state
may still carry a lock. Once the lock is clear:

```bash
set -Eeuo pipefail
terraform plan -refresh-only
```

Read it for resources that exist in the cloud and not in state — those are the orphans the
interrupted apply created. Adopt them with `import` rather than letting the next apply
create duplicates, which is what a create-then-collide cycle produces on resources whose
names are unique.

## Proving you are finished

The recovery is complete when `terraform plan -detailed-exitcode` exits 0, the resource
count matches the inventory you started from, and a colleague has read the plan that got
you there. Keep the damaged copy until the next apply has succeeded; it is the only record
of what the failure looked like.
