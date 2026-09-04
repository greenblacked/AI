# Plan JSON: schema and jq cookbook

Everything here operates on `plan.json`, produced by:

```bash
terraform plan -input=false -lock-timeout=120s -out=tfplan
terraform show -json tfplan > plan.json
```

`terraform show -json` on a saved plan file is the only supported way to get a stable machine-readable view. Parsing plan text is not a supported interface and breaks between minor versions.

## Contents

- [Top-level plan fields](#top-level-plan-fields)
- [resource_changes entries](#resource_changes-entries)
- [The change representation](#the-change-representation)
- [action_reason values](#action_reason-values)
- [jq cookbook](#jq-cookbook)
- [A single review script](#a-single-review-script)
- [Known discrepancies](#known-discrepancies)

## Top-level plan fields

| Field | Meaning |
| --- | --- |
| `format_version` | Schema version of this document. Check it before assuming field presence |
| `terraform_version` | The binary that produced the plan. Compare against `required_version` |
| `prior_state` | State the config is being applied to, in the state representation |
| `applyable` | It would make sense for a wrapping automation to apply this plan, possibly after asking a human for approval. Automation should use this as its primary condition, since the exact definition may change in future versions |
| `complete` | Terraform expects the actual state to match the desired state after applying. An incomplete plan needs at least one further plan/apply round; automation should either start another round automatically or tell the operator to |
| `errored` | Planning failed. An errored plan cannot be applied, though the actions planned before the failure can help explain the error |
| `configuration` | The configuration being applied, including `module_calls` and provider configs |
| `planned_values` | Known-so-far outcome in the values representation; unknown values omitted |
| `proposed_unknown` | Same shape, with each leaf replaced by whether it is known |
| `variables` | Every variable value fed to this plan |
| `resource_changes` | One entry per resource instance object, including no-ops |
| `resource_drift` | Changes detected between the most recent refresh and the prior saved state. Same object structure as `resource_changes` |
| `relevant_attributes` | `{resource, attribute}` pairs naming every source contributing to changes in this plan. Filter `resource_drift` against it to find which external changes actually affected the result |
| `output_changes` | Planned changes to root module outputs |
| `checks` | Pre/postcondition results known at plan time. Documented as experimental |

`applyable`, `complete`, and `errored` were added in Terraform 1.8. On older binaries they are absent, so query them with `// "n/a"` rather than assuming `false`.

## resource_changes entries

| Field | Meaning |
| --- | --- |
| `address` | Full absolute address of the instance object |
| `previous_address` | Present only when the address changed since the last run, e.g. via a `moved` block. This is how a rename is distinguished from a destroy plus a create |
| `module_address` | Module portion of the address; omitted in the root module |
| `mode` | `managed` or `data`. Filter on this — data source reads are not changes to your infrastructure |
| `type`, `name`, `index` | Resource type, local name, and `count`/`for_each` key |
| `deposed` | An opaque key. Present when the action applies to a *deposed* object rather than the current one — the leftover from a `create_before_destroy` replacement whose destroy step did not complete. `address` plus `deposed` is unique within a plan |
| `change` | The change representation, below |
| `action_reason` | Optional extra context for why these actions were chosen. Omitted when there is nothing special to say |

## The change representation

| Field | Meaning |
| --- | --- |
| `actions` | Exactly one of `["no-op"]`, `["create"]`, `["read"]`, `["update"]`, `["delete","create"]`, `["create","delete"]`, `["delete"]` |
| `before` / `after` | Object values either side of the action. `before` is unset for create, `after` for delete. `after` is incomplete when values are not known until apply |
| `after_unknown` | Same shape as `after`, unknown leaves replaced with `true`, known leaves omitted. Combine with `after` to reconstruct the full post-apply value |
| `before_sensitive` / `after_sensitive` | Same shape, sensitive leaves replaced with `true`, non-sensitive leaves omitted. Combine with `before`/`after` to avoid displaying secrets |
| `replace_paths` | Array of paths into the object that caused the action to be a replace. Each path is an array of string or number steps. Omitted when the action is not a replace, or when no path caused it (a tainted object, for instance) |
| `importing` | Present only when this object is being imported as part of the change. Contains `id`, the import ID |

The two replace forms are represented as ordered pairs specifically so that a caller can scan the array for `"delete"` and recognise all three situations in which the object goes away. Write `select(.change.actions | index("delete"))`, not a regex over a rendered string.

`["delete","create"]` is destroy-then-create: there is a window with no resource. `["create","delete"]` is `create_before_destroy`: no window, but the resource must tolerate two of itself existing at once, which name-unique resources do not.

## action_reason values

`replace_because_tainted`, `replace_because_cannot_update`, `replace_by_request`, `delete_because_no_resource_config`, `delete_because_no_module`, `delete_because_wrong_repetition`, `delete_because_count_index`, `delete_because_each_key`, `read_because_config_unknown`, `read_because_dependency_pending`.

The docs describe these as display hints whose set may grow, and instruct consumers to be prepared for unrecognised reasons and treat them as unspecified. In review terms: an unknown reason on a deletion is not a pass, it is a question.

## jq cookbook

### Plan-level gate

```bash
jq -r 'def f(k): if has(k) then (.[k]|tostring) else "n/a" end;
       "applyable=\(f("applyable")) complete=\(f("complete")) errored=\(f("errored")) tf=\(.terraform_version)"' plan.json

# Exit non-zero if this plan should not be applied; passes on pre-1.8 binaries
# where the flags are absent rather than false.
jq -e '(if has("applyable") then .applyable == true else true end)
       and (if has("errored") then .errored != true else true end)' plan.json > /dev/null
```

These three are booleans, so query them with `has()`. jq's `//` operator treats `false` as empty, which means `.complete // "n/a"` silently converts "this plan will not converge" into "unknown" — the exact failure the flag exists to prevent.

`terraform plan -detailed-exitcode` gives the complementary signal without JSON: `0` empty diff, `1` error, `2` changes present.

### Action histogram

```bash
jq -r '.resource_changes[] | select(.change.actions != ["no-op"])
       | .change.actions | join("+")' plan.json | sort | uniq -c | sort -rn
```

Split by module to see which team owns the blast radius:

```bash
jq -r '.resource_changes[] | select(.change.actions != ["no-op"])
       | [(.module_address // "root"), (.change.actions|join("+"))] | @tsv' plan.json \
  | sort | uniq -c | sort -rn
```

### Everything being deleted

```bash
jq -r '.resource_changes[]
       | select(.mode == "managed")
       | select(.change.actions | index("delete"))
       | [(.change.actions|join("+")), .address, (.action_reason // "no_reason_given")]
       | @tsv' plan.json | column -t
```

Count only, for a summary line:

```bash
jq '[.resource_changes[] | select(.change.actions | index("delete"))] | length' plan.json
```

### Replacements and the attributes that forced them

```bash
jq -r '.resource_changes[] | select(.change.replace_paths != null)
       | .address as $a | .change.replace_paths[]
       | [$a, (map(tostring)|join("."))] | @tsv' plan.json | column -t
```

To see the actual before/after of the forcing attribute:

```bash
jq -r '.resource_changes[] | select(.change.replace_paths != null)
       | . as $rc | .change.replace_paths[] as $p
       | [$rc.address,
          ($p|map(tostring)|join(".")),
          ($rc.change.before  | getpath($p) | tostring),
          ($rc.change.after   | getpath($p) | tostring)] | @tsv' plan.json
```

`getpath` fails on paths that do not exist in `before` for a create; guard with `try ... catch "n/a"` when running across a mixed plan.

### Stateful destroy tripwire

```bash
STATEFUL='db_instance|rds_cluster|s3_bucket|ebs_volume|disk|kms_key|dns_zone|eip|efs_file_system|sql_database_instance|storage_bucket'

jq -r --arg re "$STATEFUL" '
  .resource_changes[]
  | select(.mode == "managed")
  | select(.change.actions | index("delete"))
  | select(.type | test($re))
  | [.address, .type, (.change.actions|join("+")), (.action_reason // "-")]
  | @tsv' plan.json | column -t
```

Extend the regex for your estate rather than trusting it as complete. Anything holding data you cannot regenerate from code belongs in it: message queues with durable state, container registries, secret stores, stateful sets' persistent volume claims.

### Drift

```bash
# What changed outside Terraform
jq -r '.resource_drift[]? | [.address, (.change.actions|join(","))] | @tsv' plan.json

# Which attributes actually feed this plan's result
jq -r '.relevant_attributes[]? | [.resource, (.attribute|tostring)] | @tsv' plan.json

# Drifted resources that are also being changed by this plan
jq -r '[.resource_drift[]?.address] as $d
       | .resource_changes[]
       | select(.address as $a | $d | index($a))
       | select(.change.actions != ["no-op"])
       | [.address, (.change.actions|join("+"))] | @tsv' plan.json
```

The third query is the interesting one: a resource that both drifted and is being modified is where a console change is about to be silently reverted, or where two systems are fighting over ownership.

### Address changes, imports, deposed objects

```bash
# moved blocks
jq -r '.resource_changes[] | select(.previous_address)
       | [.previous_address, "->", .address, (.change.actions|join(","))] | @tsv' plan.json

# import blocks
jq -r '.resource_changes[] | select(.change.importing)
       | [.address, .change.importing.id] | @tsv' plan.json

# leftovers from a failed create_before_destroy
jq -r '.resource_changes[] | select(.deposed)
       | [.address, .deposed, (.change.actions|join(","))] | @tsv' plan.json
```

A `moved` block that shows anything other than `no-op` or `update` is not a pure rename — Terraform is moving the address *and* changing the object. Review both halves.

### Sensitive values

```bash
# Every sensitive attribute path in the post-apply values
jq -r '.resource_changes[] as $rc | ($rc.change.after_sensitive // {})
       | paths(. == true) as $p
       | [$rc.address, ($p|map(tostring)|join("."))] | @tsv' plan.json

# Sensitive root outputs
jq -r '(.output_changes // {}) | to_entries[] | (.value.change // .value) as $c
       | select($c.after_sensitive == true or $c.before_sensitive == true)
       | [.key, ($c.actions|join(","))] | @tsv' plan.json

# Outputs declared sensitive in the planned values
jq -r '.planned_values.outputs // {} | to_entries[]
       | select(.value.sensitive) | .key' plan.json
```

These tell you what Terraform will redact from output. They do not tell you what is absent from state — nothing does, because a sensitive value is present in state in plaintext by definition. The only way to keep a value out of state is `ephemeral` (variables and blocks, 1.10+) or a write-only resource argument (1.11+).

Because `plan.json` contains those plaintext values, the file is itself a secret. Generate it into a directory that is gitignored and cleaned up, and do not attach it to a PR comment.

### Provider and version surface

```bash
jq -r '.configuration.provider_config | to_entries[]
       | [.key, (.value.version_constraint // "unconstrained")] | @tsv' plan.json

jq -r '.configuration.root_module.module_calls // {} | to_entries[]
       | [.key, (.value.source // "?"), (.value.version_constraint // "unpinned")] | @tsv' plan.json
```

`unpinned` in the third column, or a `source` ending in `?ref=main`, is a finding on its own.

## A single review script

```bash
#!/usr/bin/env bash
set -euo pipefail

PLAN_JSON="${1:?usage: review.sh plan.json}"
STATEFUL='db_instance|rds_cluster|s3_bucket|ebs_volume|disk|kms_key|dns_zone|eip|efs_file_system|sql_database_instance|storage_bucket'

echo "== plan flags"
jq -r 'def f(k): if has(k) then (.[k]|tostring) else "n/a" end;
       "applyable=\(f("applyable")) complete=\(f("complete")) errored=\(f("errored"))"' "$PLAN_JSON"

echo "== actions"
jq -r '.resource_changes[] | select(.change.actions != ["no-op"]) | .change.actions | join("+")' \
  "$PLAN_JSON" | sort | uniq -c | sort -rn

echo "== deletions"
jq -r '.resource_changes[] | select(.change.actions | index("delete"))
       | [(.change.actions|join("+")), .address, (.action_reason // "-")] | @tsv' "$PLAN_JSON"

echo "== drift"
jq -r '.resource_drift[]? | [.address, (.change.actions|join(","))] | @tsv' "$PLAN_JSON"

echo "== stateful tripwire"
hits=$(jq -r --arg re "$STATEFUL" '
  .resource_changes[] | select(.mode=="managed")
  | select(.change.actions | index("delete")) | select(.type | test($re))
  | .address' "$PLAN_JSON")

if [[ -n "$hits" ]]; then
  printf '%s\n' "$hits"
  echo "BLOCKED: stateful destroy requires a named approver and a written recovery plan" >&2
  exit 3
fi
echo "none"
```

Exit code 3 distinguishes "policy blocked this" from a generic failure, so a pipeline can route it to an approval step rather than a build-failure alert.

## Known discrepancies

- The documented shape of `output_changes` nests the change under a `change` key. Real Terraform output places the change representation fields directly on each output entry. The cookbook query above accepts both via `(.value.change // .value)`.
- `checks` is documented as experimental and its details may change even in minor releases. Do not build a hard gate on it.
- `format_version` has been `1.x` for a long time; new fields appear without a major bump, so probe for a field's presence rather than inferring it from the version.
