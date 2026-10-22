# Triaging a post-upgrade plan diff

Read this when the plan after a version change is not empty. Every line gets a cause from
the table and a decision before anything is applied. A line whose cause you cannot name
is not applied; it is investigated until it has one.

## Causes and decisions

| What the plan shows | Likely cause | Decision |
| --- | --- | --- |
| In-place update setting an attribute you never wrote to a new value | The provider changed that argument's default | Pin the old value explicitly in configuration, or accept the new default as its own reviewed change after the upgrade lands |
| Replacement (`delete+create`) on a resource nobody edited, with `replace_paths` naming one attribute | A changed default on an attribute that forces replacement, or a changed normalisation of its value | Pin the old value; if the provider no longer accepts it, stop and take the replacement to `iac-review` as a decision, not as upgrade fallout |
| A resource type disappears and a similarly named one is created | The resource was renamed in this major version | A `moved` block across types where the provider supports it (Terraform 1.8 or later and a provider that implements the move); otherwise `removed` with `destroy = false` on the old address and `import` on the new one, through `terraform-state` |
| New resources to create for settings that used to be arguments on one resource | The provider split a resource into several, as the AWS provider 4.0 did with most `aws_s3_bucket` arguments | `import` blocks for each new resource against the existing object, so the plan shows imports, not creates |
| Updates that only reorder a list, change case, or add or remove a trailing character | The new provider normalises the value differently from the old | Confirm with a refresh-only plan; if it is representation only, accept it with `apply -refresh-only` and match the configuration to the new form |
| Changes to computed attributes, or entries under `resource_drift` that were not there before | The new provider reads more of the object or reads it differently | Same as the row above; a refresh-only apply records it without touching the object |
| Error at plan time naming an unsupported argument | The argument was removed | Should have been caught in the deprecation pass; apply the replacement from the upgrade guide on the old version if it supports it, or in the upgrade change if not |
| Changes to data sources (`read`) only | Data sources are read during plan; not a change to anything | No action, but check a data source whose result feeds a resource argument |
| A diff only in one environment | Drift or unapplied work in that environment, not the upgrade | Back out the upgrade there, clean the baseline, retry |

## Refresh-only, deliberately

A refresh-only plan updates state to what the cloud reports and changes nothing in the
cloud. It is the right tool when the provider's new reading of an object is accurate and
the object should not move:

```bash
set -Eeuo pipefail
terraform plan -refresh-only -input=false -out=refresh.tfplan
terraform show -json refresh.tfplan | jq -r '.resource_drift[]? | .address'
terraform apply refresh.tfplan
```

Read every address before applying. Accepting a value into state that the configuration
contradicts only defers the change to the next normal apply, so match the configuration
to the accepted value in the same change.

## Questions before calling a diff harmless

- Does any line touch a database, a disk, a key, a bucket policy, a network rule or an
  identity grant? Those are never noise; each gets its own review.
- Does the upgrade guide mention this resource at all? If it does not and the line is a
  replacement, the cause is probably not the upgrade.
- Does the same line appear in every environment? A cause that is really the upgrade
  shows up everywhere the resource exists.
- Would you approve this line if a colleague had written it by hand? If not, it does not
  become acceptable because a version bump wrote it.
