# Upgrade runbook

Read this before running the baseline against more than one environment, and when a
backup has to be restored after an apply.

## Contents

- Layout the loop assumes
- Baseline and backups
- Reading a saved plan as JSON
- Post-upgrade plan loop
- Restoring after an apply
- Handling the working files

## Layout the loop assumes

The examples assume one root module per environment under `envs/<name>/`. With workspaces
instead, replace `-chdir="envs/$env"` with a single directory and run
`terraform workspace select "$env"` at the top of each iteration. Order the list from the
least important environment to production; the loop stops at the first one that is not
clean, which is the point.

## Baseline and backups

Run on the old version, before any constraint changes.

```bash
set -Eeuo pipefail
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$HOME/iac-upgrade-backups/$stamp"
mkdir -p "$backup"

for env in dev staging prod; do
  terraform -chdir="envs/$env" init -input=false
  terraform -chdir="envs/$env" state pull > "$backup/$env.tfstate"
  jq -r --arg env "$env" '"\($env) serial=\(.serial) lineage=\(.lineage) version=\(.terraform_version)"' \
    "$backup/$env.tfstate"
  rc=0
  terraform -chdir="envs/$env" plan -input=false -detailed-exitcode -out=baseline.tfplan || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "$env: baseline is not clean (exit $rc); resolve before upgrading" >&2
    exit 1
  fi
done
```

Record each serial and lineage in the upgrade record. They identify exactly which state a
restore would put back, and a lineage that differs from the record means you are looking
at a different state than you think.

The backups are credential files: state carries provider-returned passwords and keys in
plaintext. Keep them somewhere with the same access controls as the backend, not in a
shared temporary directory, a ticket or a chat.

## Reading a saved plan as JSON

```bash
set -Eeuo pipefail
umask 077
terraform -chdir="envs/$env" show -json upgrade.tfplan > "$backup/$env.plan.json"
jq -r '
  .resource_changes[]?
  | select(.change.actions != ["no-op"] and .change.actions != ["read"])
  | "\(.change.actions | join("+"))\t\(.address)"
' "$backup/$env.plan.json"
jq -r '.resource_drift[]? | "drift\t\(.address)"' "$backup/$env.plan.json"
```

`delete+create` or `create+delete` is a replacement; read those first. `resource_drift`
lists objects changed outside Terraform since the last apply. Drift appearing only after
the upgrade usually means the new provider reads an attribute differently, which
`plan-diff-triage.md` covers.

To see which attributes changed on one address:

```bash
set -Eeuo pipefail
jq --arg a 'azurerm_storage_account.logs' '
  .resource_changes[] | select(.address == $a)
  | {actions: .change.actions, replace_paths: .change.replace_paths,
     before: .change.before, after: .change.after}
' "$backup/$env.plan.json"
```

`replace_paths` names the attributes forcing a replacement, which is usually the fastest
route to the upgrade-guide entry responsible.

## Post-upgrade plan loop

The same loop as the baseline, on the new version, saving plans for triage rather than
stopping at the first diff:

```bash
set -Eeuo pipefail
umask 077
for env in dev staging prod; do
  terraform -chdir="envs/$env" init -input=false
  rc=0
  terraform -chdir="envs/$env" plan -input=false -detailed-exitcode -out=upgrade.tfplan || rc=$?
  echo "$env: exit $rc"
done
```

Plan only. Applying happens one environment at a time, after each environment's diff has
been triaged and its predecessor has run a full cycle.

## Restoring after an apply

Use this only when the new version has written a state and you have decided to go back.
Everything applied to that state since the backup was taken is lost from the record, so
check for applies after the backup first and reconcile them by hand afterwards.

1. Stop every pipeline that can apply to this state.
2. Put the old binary and the old lock file back (revert the upgrade commit).
3. Push the backup. `state push` refuses a state whose serial is lower than the current
   one, and the restored backup always is, so `-force` is required here and only here:

   ```bash
   set -Eeuo pipefail
   terraform -chdir="envs/$env" init -input=false
   terraform -chdir="envs/$env" state push -force "$backup/$env.tfstate"
   terraform -chdir="envs/$env" plan -input=false -detailed-exitcode
   ```

4. The plan should be empty, apart from anything applied after the backup. Those objects
   now exist in the cloud but not in state; adopt them with `terraform-state`'s import
   procedure rather than letting the next apply create duplicates.

If the backend keeps object versions, restoring the pre-upgrade version through the
backend is equivalent, but confirm it is the same serial and lineage as the record first.

## Handling the working files

Delete `*.tfplan` and `*.plan.json` when the upgrade closes; a saved plan contains the
same secrets as state. Keep the state backups until production has run on the new version
for a full cycle, then delete them under the same controls they were stored under.
