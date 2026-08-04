# Policy as code for Terraform review

Two families of check, and conflating them is the usual mistake.

**Source scanners** read `.tf` files. They are fast, need no credentials, and catch misconfiguration — an unencrypted bucket, a security group open to the world, a missing log retention. They cannot see what a change will *do*, because they never see the plan.

**Plan scanners** read `plan.json`. They see actions, `action_reason`, `replace_paths`, drift, and resolved values, so they are the only place a rule like "no stateful destroys without approval" can live.

Run both. Source scanners on every commit, plan scanners on every plan, before the approval step.

## Contents

- [Source scanners](#source-scanners)
- [Conftest and OPA over the plan](#conftest-and-opa-over-the-plan)
- [A worked Rego policy](#a-worked-rego-policy)
- [Sentinel](#sentinel)
- [Infracost](#infracost)
- [Wiring it into CI](#wiring-it-into-ci)

## Source scanners

### tflint

Provider-aware linting: deprecated syntax, invalid instance types, unused declarations, naming conventions.

```bash
tflint --init                       # fetch plugins declared in .tflint.hcl
tflint --recursive --format compact
tflint --recursive --minimum-failure-severity=error   # gate on errors, report warnings
```

```hcl
# .tflint.hcl
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
plugin "aws" {
  enabled = true
  version = "0.32.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
rule "terraform_required_version"   { enabled = true }
rule "terraform_required_providers" { enabled = true }
rule "terraform_module_version"     { enabled = true }   # rejects unpinned module sources
```

`terraform_module_version` is the rule that catches `?ref=main`, which is worth enabling on its own.

### trivy config

Misconfiguration scanning with a large built-in policy set, plus secret detection in the same binary.

```bash
trivy config --severity HIGH,CRITICAL --exit-code 1 .
trivy config --format json --output trivy.json .
trivy config --tf-vars prod.tfvars .        # resolve variables so rules see real values
trivy fs --scanners secret .                # committed credentials
```

Trivy can also read a plan file, which resolves variables and module inputs for you:

```bash
trivy config --file-patterns 'terraformplan:*.json' plan.json
```

### checkov

The widest rule catalogue, and the one that most needs suppression discipline.

```bash
checkov -d . --framework terraform --compact --quiet
checkov -f plan.json --framework terraform_plan --compact
checkov -d . --skip-check CKV_AWS_18 --soft-fail-on CKV_AWS_21
```

Suppress inline and with a reason, so the suppression is reviewable:

```hcl
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:access logging on the log bucket itself would recurse
  bucket = "example-logs"
}
```

A repo-level `--skip-check` list with no comments is how a real finding gets buried. Prefer inline skips.

### terrascan

Useful where you want a second opinion with a different rule set, particularly for Kubernetes and multi-cloud policy.

```bash
terrascan scan -i terraform -d . --severity high
terrascan scan -i terraform -d . -o json > terrascan.json
```

## Conftest and OPA over the plan

This is where the rules that matter live, because they can reason about actions.

```bash
conftest test --policy policy/ --namespace terraform.review plan.json
conftest test --policy policy/ --all-namespaces --output table plan.json
conftest verify --policy policy/          # run the policy unit tests
```

Or with the OPA binary directly, which is easier to embed in a wrapper:

```bash
opa eval --format pretty \
  --data policy/ --input plan.json \
  'data.terraform.review.deny'
```

## A worked Rego policy

`policy/stateful.rego` — deny any destroy or replacement of a resource that holds data.

```rego
package terraform.review

import rego.v1

# Resource types whose loss is not recoverable from configuration alone.
# Extend for your estate; the cost of a false positive is one approval click.
stateful_types := {
 "aws_db_instance",
 "aws_rds_cluster",
 "aws_rds_cluster_instance",
 "aws_s3_bucket",
 "aws_ebs_volume",
 "aws_efs_file_system",
 "aws_kms_key",
 "aws_route53_zone",
 "aws_eip",
 "aws_dynamodb_table",
 "google_sql_database_instance",
 "google_storage_bucket",
 "google_compute_disk",
 "azurerm_managed_disk",
 "azurerm_storage_account",
 "azurerm_mssql_database",
}

# The plan is only reviewable if Terraform itself thinks it can be applied.
deny contains msg if {
 input.errored == true
 msg := "plan errored during planning; it cannot be applied"
}

deny contains msg if {
 input.applyable == false
 msg := "plan is not applyable; fix the plan before requesting approval"
}

warn contains msg if {
 input.complete == false
 msg := "plan is incomplete; a further plan/apply round will be required to converge"
}

# Addresses with a recorded approval. Supplied by the pipeline from a signed
# approval record so that it lands at data.approval.addresses; never written by
# the person submitting the change.
default approved_addresses := []

approved_addresses := data.approval.addresses

# The core rule. ["delete"], ["delete","create"] and ["create","delete"] all
# contain "delete", which is exactly why the schema represents them that way.
deny contains msg if {
 rc := input.resource_changes[_]
 rc.mode == "managed"
 stateful_types[rc.type]
 "delete" in rc.change.actions
 not rc.address in approved_addresses

 msg := sprintf(
  "%s (%s) will be destroyed: actions=%v reason=%q. Requires a named approver and a written recovery plan.",
  [rc.address, rc.type, rc.change.actions, object.get(rc, "action_reason", "unspecified")],
 )
}

# Any destroy at all, stateful or not, is worth surfacing.
warn contains msg if {
 rc := input.resource_changes[_]
 rc.mode == "managed"
 not stateful_types[rc.type]
 "delete" in rc.change.actions
 msg := sprintf("%s will be destroyed (actions=%v)", [rc.address, rc.change.actions])
}

# Drift that this plan will overwrite.
warn contains msg if {
 drifted := {d.address | d := input.resource_drift[_]}
 rc := input.resource_changes[_]
 rc.address in drifted
 rc.change.actions != ["no-op"]
 msg := sprintf("%s drifted outside Terraform and is also being changed by this plan", [rc.address])
}
```

The approval document is external input, which is the whole point — the policy states the fact, the pipeline supplies who approved what:

```json
{"approval": {"addresses": ["aws_db_instance.main"], "approver": "r.okafor", "recovery_plan": "RUN-4471"}}
```

```bash
conftest test --policy policy/ --data approval.json --namespace terraform.review plan.json
```

Check how your runner namespaces `--data` before relying on it — Conftest and `opa eval` derive the path under `data` differently — and assert on it in a test rather than discovering at 2am that every approval silently resolved to the default empty list.

Test the policy like code, because an untested policy that silently matches nothing is worse than no policy:

```rego
# policy/stateful_test.rego
package terraform.review

import rego.v1

test_replace_of_database_is_denied if {
 count(deny) == 1 with input as {
  "resource_changes": [{
   "address": "aws_db_instance.main",
   "mode": "managed",
   "type": "aws_db_instance",
   "action_reason": "replace_because_cannot_update",
   "change": {"actions": ["delete", "create"]},
  }],
 }
}

test_update_of_database_is_allowed if {
 count(deny) == 0 with input as {
  "resource_changes": [{
   "address": "aws_db_instance.main",
   "mode": "managed",
   "type": "aws_db_instance",
   "change": {"actions": ["update"]},
  }],
 }
}
```

```bash
conftest verify --policy policy/
opa test policy/ -v
```

## Sentinel

HCP Terraform's policy engine. The mechanism that matters for review design is the enforcement level, set per policy in the policy set:

| Level | Behaviour | Use for |
| --- | --- | --- |
| `advisory` | Logs the failure, run proceeds | New rules being trialled; anything with a known false-positive rate |
| `soft-mandatory` | Blocks, but a user with override permission can proceed and the override is recorded | Rules with legitimate exceptions — the stateful-destroy gate belongs here, since the override *is* the named approver |
| `hard-mandatory` | Blocks with no override; the run cannot proceed until the plan changes | Non-negotiables: encryption at rest, no public S3, no `0.0.0.0/0` on port 22 |

```hcl
# sentinel.hcl
policy "no-public-buckets" {
  source            = "./policies/no-public-buckets.sentinel"
  enforcement_level = "hard-mandatory"
}

policy "stateful-destroy-requires-approval" {
  source            = "./policies/stateful-destroy.sentinel"
  enforcement_level = "soft-mandatory"
}
```

```python
# policies/stateful-destroy.sentinel
import "tfplan/v2" as tfplan

stateful = ["aws_db_instance", "aws_rds_cluster", "aws_s3_bucket", "aws_kms_key"]

destroying = filter tfplan.resource_changes as _, rc {
 rc.mode is "managed" and
  rc.type in stateful and
  "delete" in rc.change.actions
}

main = rule { length(destroying) is 0 }
```

Ship advisory first, watch it for a fortnight, then promote. A rule that goes straight to hard-mandatory and turns out to be noisy gets disabled entirely, and disabled is worse than advisory.

## Infracost

```bash
infracost breakdown --path . --format json --out-file base.json
infracost diff --path plan.json --compare-to base.json
infracost diff --path plan.json --format json | \
  jq -r '.projects[].diff.totalMonthlyCost'
```

Run it against the same `plan.json` everything else reviewed, not a fresh plan. A `--compare-to` baseline turns "this costs $4,200/month" into "this adds $180/month", which is the number a reviewer can actually act on.

## Wiring it into CI

Order matters. Cheap checks first so a formatting error does not consume a plan slot:

```yaml
- terraform fmt -check -recursive -diff
- terraform init -input=false -lockfile=readonly
- terraform validate
- tflint --recursive --minimum-failure-severity=error
- trivy config --severity HIGH,CRITICAL --exit-code 1 .
- terraform plan -input=false -lock-timeout=120s -out=tfplan
- terraform show -json tfplan > plan.json
- conftest test --policy policy/ --namespace terraform.review plan.json
- checkov -f plan.json --framework terraform_plan --compact
- infracost diff --path plan.json --compare-to base.json
# approval gate here, on the artefacts above
- terraform apply -input=false tfplan
```

Three properties make this a gate rather than theatre:

1. `tfplan` is stored as a pipeline artefact and the apply step consumes *that file*. Re-running `plan` in the apply job means the approval applied to a different change.
2. `init -lockfile=readonly` means a provider bump fails here rather than being absorbed silently.
3. `plan.json` contains plaintext sensitive values. Keep it inside the job's workspace, exclude it from artefact upload or encrypt it, and do not post it to a PR comment. Post the policy output and the cost diff instead — those are derived and safe.
