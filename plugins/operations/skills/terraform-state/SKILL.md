---
name: terraform-state
description: "Execute a Terraform or OpenTofu state operation that has already been decided: import an existing resource, move or rename one after a refactor, drop one from state without destroying it, reconcile drift, recover a lost or corrupted state file, clear a stuck lock, or separate state per environment and backend. Takes a backup first and prefers the reviewable import, moved and removed blocks over the state subcommands. Use whenever someone says \"terraform wants to destroy and recreate everything\", \"I renamed a module and now the plan is wrong\", \"how do I import existing resources\", \"state is locked\", or \"accept the console change into state so the plan stops fighting it\". Do not use it to review a plan, a PR or a proposed state move, which is iac-review, to write a new module (code-scaffold), to plan a platform move (plan-platform-migration), or to rotate a credential (secret-rotation)."
allowed-tools: Bash(terraform:*), Bash(tofu:*), Bash(jq:*), Bash(git:*), Read, Write, Edit, Grep, Glob
---

# Terraform State

A state operation is finished when the plan is empty, nothing in the cloud was created or
destroyed on the way, and the state you started from is still recoverable.

State is the only record binding an address in the configuration to a real object, and
the `terraform state` subcommands write it immediately — outside the plan, outside
review, outside version control, with no undo beyond a copy you took first. That is why
the damage here is almost always self-inflicted by someone trying to make a frightening
plan smaller. `state rm` on the resource Terraform wants to destroy leaves a live object
nobody manages and a name collision on the next create. A `state mv` with the wrong index
binds an address to another instance's object, and the next apply reconfigures the wrong
machine. Neither command fails at the time; both surface an apply later, when whoever ran
them has moved on. Everything below is arranged so that the mutation happens in a form
somebody can read before it lands.

## Scope

Use for: executing a state operation that has already been decided — adopting an existing
resource with `import`, moving or renaming after a refactor, dropping a resource from
state without destroying it, reconciling drift once a plan has shown it, recovering a
corrupted, partially applied or lost state file, clearing a stuck lock, and backend,
remote state, workspace and per-environment separation, including what follows from state
holding secrets in plaintext.

Do not use for:

- **Reviewing a proposed change, a plan, or a pull request.** That is `iac-review`, which
  reads plan JSON and excludes authoring, and which already treats drift and state moves
  as findings. The boundary is the decision: `iac-review` judges whether the move is
  right, this skill carries it out afterwards. If nobody has reviewed the plan yet, stop
  and hand it there first.
- **Writing a new module or a first configuration.** That is `code-scaffold`. This skill
  edits configuration only to add a `moved`, `import` or `removed` block, and never
  authors the resources themselves.
- **Moving a platform between providers, clusters or CI systems.** That is
  `plan-platform-migration`. This skill owns individual state operations inside a move
  that has already been planned.
- **Rotating a credential.** That is `secret-rotation`, including the credential you found
  sitting in a state file.

## Hard gates

Breaking one of these does not slow the operation down, it makes it unrecoverable.

1. **Capture the state before any mutation.** `terraform state pull` is the one backup
   that works on every backend and does not depend on the backend's own versioning being
   enabled, configured for the right retention, or readable by you. Take it every time,
   including for an operation you have performed a hundred times.
2. **Prefer the form that appears in a plan.** `moved`, `import` and `removed` blocks are
   configuration: they are reviewed, applied inside the normal plan and apply, recorded
   in git, and replayed identically in every environment. The CLI equivalents happen at
   once, on one machine, with no record anywhere. Drop to the CLI only when the version
   in use predates the block, and say so when you do.
3. **One address at a time, with a plan between each.** A batch of state moves produces a
   plan diff nobody can attribute to a particular move, which is exactly the situation in
   which a wrong move gets applied.
4. **Keep state out of terminals, transcripts and logs.** `state pull`, `show -json` and a
   saved plan file all contain provider-returned passwords, private keys and connection
   strings in plaintext. Redirect them to a file with restricted permissions; do not cat
   them, do not paste them into a ticket, and delete the working copies when you are done.
5. **Do not disable locking to get past a lock.** `-lock=false` against a backend someone
   else is applying to is how two runs write the same state and one set of writes
   disappears. Establish who holds the lock first.

## Which form you have

Verify the version in the environment that will apply, not the one on your laptop:
`terraform version`. OpenTofu forked before Terraform 1.6 shipped, so read the table above
rather than assuming parity at any given version.

| Form | What it does | Available from |
| --- | --- | --- |
| `moved` block | Re-binds an address without destroying the object, inside a plan | Terraform 1.1, OpenTofu 1.6 |
| `import` block | Adopts an existing object, shown in the plan before it lands | Terraform 1.5, OpenTofu 1.6 |
| `plan -generate-config-out=FILE` | Writes draft HCL for resources named in `import` blocks | Terraform 1.5, OpenTofu 1.6 |
| `import` with an expression `id` | The id may reference another resource attribute known at plan time | Terraform 1.6 |
| `import` with `for_each` | Bulk adoption from a map | Terraform 1.7, OpenTofu 1.7 |
| `removed` block | Drops a resource or module from state without destroying it | Terraform 1.7, OpenTofu 1.7 |
| `apply -refresh-only` | Writes detected drift to state as a reviewable plan | Terraform 0.15.4 |
| S3 backend `use_lockfile` | Locks without a DynamoDB table | Terraform 1.10, general in 1.11 |

Below those versions the fallbacks are `terraform state mv`, `terraform import` and
`terraform state rm`, which mutate immediately. Gate 1 is the only thing standing behind
them.

## Workflow

### 1. Fix the ground truth before touching anything

```bash
set -Eeuo pipefail
umask 077
work="$(mktemp -d)"
terraform version
terraform state pull > "$work/before.tfstate"
jq -r '"serial=\(.serial) lineage=\(.lineage) resources=\(.resources | length)"' "$work/before.tfstate"
terraform state list > "$work/addresses.txt"
```

Record the serial and lineage. They are how you later prove which state you started from,
and a lineage that changes underneath you means you are pointed at a different state than
you think. `umask 077` is not decoration: `before.tfstate` is a credential file.

### 2. Classify what you are looking at

| What you are seeing | What it actually is | Go to |
| --- | --- | --- |
| Plan destroys and recreates everything after a rename or module extraction | Addresses changed, objects did not | Step 4 |
| `Error: resource already exists` on apply, or a plan proposing to create something you can see in the console | The object exists, state does not know it | Step 3 |
| Plan shows changes nobody wrote | Someone changed the cloud by hand | Step 6 |
| A resource has to leave this configuration but keep running | Ownership is moving | Step 5 |
| `Error acquiring the state lock` | A live run, or a dead one that left a lock | Step 7 |
| State is truncated, empty, rolled back, or an apply was killed mid-flight | Lost or inconsistent state | `references/state-recovery.md` |
| Plan says `# forces replacement` on one resource and the configuration changed | Not a state problem at all | `iac-review` |

That last row is the common misdiagnosis. A replacement caused by an immutable attribute
is a configuration decision to review, and reaching for `state rm` to silence it converts
a reviewable replacement into an orphaned resource.

### 3. Adopt an existing resource

Write the `import` block first and let the plan tell you whether you are right.

```hcl
import {
  to = aws_s3_bucket.assets
  id = "example-assets-bucket"
}
```

```bash
set -Eeuo pipefail
terraform plan -generate-config-out=generated.tf   # only for resources with no config yet
terraform plan                                     # read it: import only, no create, no destroy
terraform apply
```

Generated configuration is a draft, not an answer — it carries every attribute the
provider returned, including defaults you do not want pinned and values that belong in
variables. Edit it down before applying.

The id format is provider-specific and is the most common way to import the wrong object
under the right address: check the resource's own import documentation rather than
guessing from the console URL. A plan that proposes to destroy what you just imported
means the configuration at that address does not describe that object.

Below Terraform 1.5, write the resource block by hand and run
`terraform import aws_s3_bucket.assets example-assets-bucket`. It mutates state with no
plan and no review, so take the backup in step 1 first.

### 4. Move or rename

```hcl
moved {
  from = aws_instance.web
  to   = module.frontend.aws_instance.web
}
```

`moved` handles resources, module calls, and the index change when a `count` becomes a
`for_each` (`from = aws_instance.web[0]`, `to = aws_instance.web["a"]`). Keep the block
after the apply. Every state that still holds the old address needs to see it, and those
are applied on different days — for a module other teams consume, keep it for at least a
major version. Deleting it the same afternoon is what turns one team's refactor into
another team's destroy.

The CLI fallback, for versions below 1.1 or for a move between two different states:

```bash
set -Eeuo pipefail
terraform state mv -dry-run 'module.old.aws_instance.web[0]' 'module.new.aws_instance.web["a"]'
terraform state mv 'module.old.aws_instance.web[0]' 'module.new.aws_instance.web["a"]'
```

Single-quote every address. Unquoted brackets and `for_each` keys are eaten by the shell,
and the resulting address matches nothing or, worse, something else.
`references/address-syntax.md` has the quoting and index rules; read it when an address
contains a key, an index or a module path, or when a block is not matching what you
expect.

### 5. Remove without destroying

Delete the `resource` block, then record the removal:

```hcl
removed {
  from = aws_iam_role.legacy

  lifecycle {
    destroy = false
  }
}
```

`destroy = false` is the entire point; without it the block destroys the object. The CLI
fallback below Terraform 1.7 is `terraform state rm -dry-run ADDRESS`, read the output,
then the same command without `-dry-run`.

Before removing, copy the object's real identifier out of the state you are about to
leave behind — after the removal, the only place it exists is your backup. When the
resource is being adopted by another state, remove it here first and import it there
second. The alternative order leaves two states believing they own one object, and either
one can destroy it; a short window with no owner cannot.

### 6. Reconcile drift

```bash
set -Eeuo pipefail
umask 077
terraform plan -refresh-only -out=refresh.tfplan
terraform show -json refresh.tfplan > refresh.json
jq -r '.resource_drift[]? | "\(.address)\t\(.change.actions | join(","))"' refresh.json
```

`refresh.json` contains state values; keep it out of CI logs and delete it afterwards.

Decide per resource, not per plan:

| Finding | Decision | Action |
| --- | --- | --- |
| The hand-made change was right and should stay | The cloud wins | `terraform apply -refresh-only`, then bring the configuration up to match |
| The change was accidental or unauthorised | The code wins | Leave state alone and let the next apply revert it — but read that plan first, because reverting is a replacement for some attributes |
| The value is legitimately owned outside Terraform | Neither | Move it to a variable, or `ignore_changes` on that attribute alone |

Accepting drift into state without also updating the configuration is the trap: state now
agrees with the cloud, and the next apply reverts the cloud to the configuration anyway.

`ignore_changes` is for attributes another system genuinely owns — an autoscaler's desired
capacity, tags written by a policy engine. Used more widely it hides the next real drift.
Repeated drift on the same resource is a missing path in the delivery pipeline rather than
a state defect; say so rather than reconciling it a third time.

### 7. Locks

The error names the lock ID, who took it, which operation and when. Establish whether that
process is alive before doing anything: a lock held by a running CI job is working
correctly, and the fix is `-lock-timeout=5m` on the command that keeps losing the race,
not a broken lock.

When the holder is provably dead — the job was cancelled, the machine is gone — take the
ID from the error message and run `terraform force-unlock LOCK_ID`. Then treat the state
as suspect: an apply killed mid-flight can have created objects it never recorded. Go to
`references/state-recovery.md`.

### 8. Close it out

```bash
set -Eeuo pipefail
terraform plan -detailed-exitcode   # 0 no changes, 2 changes pending, 1 error
```

The operation is done when that exits 0. Commit the `moved`, `import` or `removed` block
with the change that caused it, note the serial you started from in the commit or the
ticket, and keep the backup until the backend's own versioning covers the same window.
Delete the working copies of state when you do.

## State holds secrets

Every attribute a provider returns is stored, including generated passwords, private keys
and connection strings, in plaintext. `sensitive = true` hides a value from CLI output and
not from the file. What follows is operational rather than theoretical: the backend needs
encryption at rest and an access policy no wider than the set of people allowed to apply;
backups belong somewhere with those same controls rather than in `/tmp` or an attachment;
state, plan files and `show -json` output never go into a pull request, a ticket or a
chat. A state file that reached somewhere it should not have is a credential disclosure —
hand it to `secret-rotation` and rotate what it contained.

Ephemeral values and resources (Terraform 1.10) and write-only arguments (Terraform 1.11,
where the provider supports them) keep some values out of state; OpenTofu 1.7 encrypts
state client-side. Each narrows the exposure. None removes it.

## Anti-patterns

**Reaching for `state rm` to make a destroy go away.** It removes the record, not the
plan's reason. The object keeps running, nothing manages it, nobody is paying attention to
it, and the next create collides with its name.

**Editing the state JSON by hand.** The format is internal and versioned, and a
hand-edited file that parses is not the same as one Terraform accepts. Every mutation in
this skill has a command or a block that maintains the invariants; `references/state-recovery.md`
covers the one case where a rewrite is genuinely the answer.

**Running an import or a move against the wrong workspace.** `terraform workspace show`
costs nothing and the failure mode is adopting a production object into a staging state.

**Batching a refactor and a resource change in one commit.** When the plan after a `moved`
block is not empty, you need to know whether that is the move or the change. Separate
commits make that a five-second question.

**Treating a clean plan as proof the import was right.** A clean plan says state and
configuration agree. It does not say you imported the object you meant; only the
identifier does.

## References

- `references/address-syntax.md` — read when an address involves an index, a `for_each`
  key, a module path or a provider alias, or when a `moved` or `import` block matches
  nothing.
- `references/state-recovery.md` — read when state is corrupt, truncated, rolled back or
  lost, when an apply was killed part way through, or after force-unlocking one.
- `references/backend-and-workspaces.md` — read when choosing or changing a backend,
  splitting one state into several, or deciding between workspaces and a directory per
  environment.
