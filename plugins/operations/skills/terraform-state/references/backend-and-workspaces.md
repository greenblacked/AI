# Backends, workspaces and separation

Read this when choosing or changing a backend, splitting one state into several, deciding
between workspaces and a directory per environment, or working out what the backend has to
provide because state holds secrets.

## Contents

- What a backend has to do
- Locking, per backend
- Changing backend without losing state
- Workspaces or directories
- Splitting a state that has grown too big
- Consuming another state's outputs
- Because state holds secrets

## What a backend has to do

Three things, and a backend that does two of them is the reason someone loses a day:

1. **Store the state durably, with versions.** Versioning is what turns a corrupt write
   into a five-minute restore. Enable it on the bucket at creation; enabling it afterwards
   does not help with the write that already happened.
2. **Lock.** Without locking, two concurrent applies both read serial N, both write serial
   N+1, and the second silently discards the first one's resources.
3. **Restrict access to the people allowed to apply.** State is readable credentials; read
   access to the bucket is read access to every password in it.

Bootstrapping the backend is its own small problem: the bucket, table or key that holds
state cannot be managed by the state it holds without a chicken-and-egg step. Create it
out of band, or in a tiny separate configuration whose own state is local and committed
deliberately, and record which.

## Locking, per backend

| Backend | Lock mechanism | Watch for |
| --- | --- | --- |
| `s3` | DynamoDB table, or `use_lockfile` from Terraform 1.10 and generally available in 1.11 | Running with neither locks nothing at all |
| `gcs` | Native, using object preconditions | Nothing extra to provision |
| `azurerm` | Blob lease | A lease survives a killed process until it expires |
| `kubernetes` | Lease object in the namespace | Namespace deletion takes the state with it |
| `pg` | Advisory lock | The lock dies with the session, which is usually what you want |
| `http` | Optional `LOCK` and `UNLOCK` endpoints | Many implementations skip them and report success |
| `local` | File lock | Only against processes on the same machine |
| HCP Terraform, Terraform Enterprise | Run queue | Locking is the queue, so a stuck run blocks the workspace |

## Changing backend without losing state

```bash
set -Eeuo pipefail
umask 077
work="$(mktemp -d)"
terraform state pull > "$work/before-backend-change.tfstate"
terraform init -migrate-state
terraform plan -detailed-exitcode
```

`-migrate-state` copies the existing state into the new backend and prompts before doing
it. `-reconfigure` does the opposite — it discards the association and starts empty, which
is right when you are pointing a working directory at a state that already exists, and is
a way to lose track of a state when you use it by mistake. The plan afterwards has to be
empty; anything else means the migration landed somewhere other than you think.

A backend block takes no variables in Terraform, which is why credentials and per-
environment keys go through partial configuration and `-backend-config=FILE` rather than
interpolation. OpenTofu 1.8 relaxed this and allows variables and locals in backend
configuration, within limits.

## Workspaces or directories

Workspaces give one configuration several states behind one backend, one set of
credentials and one access policy. That makes them right for short-lived parallel copies
of the same thing — a per-branch test stack, an experiment — and wrong for production and
staging, where the point of the separation is that a mistake in one cannot reach the
other. Terraform's and OpenTofu's own documentation says the same: workspaces are not
appropriate for deployments needing separate credentials and access controls.

A directory per environment, each with its own backend key and its own credentials, costs
some duplication and buys the blast radius. Keep the shared parts in modules and let each
environment's root be thin. Where the duplication is genuinely mechanical, generate the
roots rather than templating the backend at runtime.

The tell that a workspace split is wrong: the plan for staging can only be produced by
credentials that could also apply to production.

## Splitting a state that has grown too big

Symptoms are long refreshes, a plan that touches everything because one provider is slow,
and a blast radius wider than any single team. Split along ownership boundaries rather
than technology ones — the network team's state, the platform's, the product's — because
the boundary you want is the one that decides who can break what.

The move itself, per resource, is the remove-then-import order: copy the object's real id
out of the old state, remove it there without destroying, then adopt it in the new
configuration. Two states owning one object is worse than a short gap with no owner,
because either state can destroy it and neither knows the other exists. `terraform state
mv -state-out` can move directly between two local state files, which is useful when both
states are pulled locally, but it does not hold both backend locks; pull, move, push, and
freeze applies on both while you do.

## Consuming another state's outputs

`terraform_remote_state` reads the whole state of the other configuration, which means the
consumer needs read access to a file containing the producer's secrets. Prefer publishing
the handful of values other configurations need to a place with its own access control —
parameter store, secret manager, a data source that queries the resource directly — and
keep `terraform_remote_state` for the cases where the producer and consumer are owned by
the same people.

## Because state holds secrets

Every provider-returned attribute is stored in plaintext, so the backend is a secret store
whether or not anyone treats it as one. What that implies, concretely:

- Encryption at rest on the bucket, and TLS in transit, are table stakes rather than
  hardening. OpenTofu 1.7 adds client-side state encryption, which is the only one of
  these that protects state from whoever can read the bucket.
- Read access to the state is equivalent to read access to the credentials inside it, so
  the read policy is as sensitive as the write policy. Auditing who can read the bucket
  belongs in the same review as who can apply.
- Backups inherit all of the above. A copy in a home directory or a ticket attachment is
  the same disclosure with none of the controls.
- CI needs the backend, so CI credentials reach the secrets in state. Scope the role to
  one key prefix per environment rather than to the bucket.
- Terraform 1.10 ephemeral values and 1.11 write-only arguments keep some inputs out of
  state where providers support them. They narrow the exposure rather than removing it.
