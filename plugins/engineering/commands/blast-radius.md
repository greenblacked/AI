---
description: Report what a Terraform or OpenTofu apply will actually destroy and replace, destroys first, from the plan JSON rather than the plan text.
argument-hint: [path to tfplan or plan.json]
allowed-tools: Bash(terraform:*), Bash(tofu:*), Bash(jq:*), Read, Glob
---

Read the plan at `$1` and report its blast radius. The point of reading the JSON rather
than the terminal output is that `terraform plan` prints changes in alphabetical order,
so a destroy sits wherever the resource name puts it and gets skimmed past.

If `$1` is a binary plan file, convert it first:

```bash
terraform show -json "$1" > /tmp/plan.json
```

Then work through `.resource_changes[]` in this order, because it is the order of
decreasing recoverability:

1. **delete** — every resource being destroyed, with its address and type. For each,
   say whether the data is recoverable and from where.
2. **replace** — `["create","delete"]` or `["delete","create"]`. Report the address and
   the specific attribute forcing it, from `.change.before` versus `.change.after` and
   the provider's known force-new attributes. A replacement nobody expected is almost
   always a diff in a field that reads as cosmetic.
3. **update** — group by type and count. Call out only those touching identity,
   networking, IAM, or anything with a downtime characteristic.
4. **create** — a count is enough unless something is expensive or exposed.

A useful starting query:

```bash
jq -r '.resource_changes[]
  | select(.change.actions | inside(["delete"]) or contains(["delete"]))
  | "\(.change.actions | join(",")) \(.address)"' /tmp/plan.json | sort
```

Also flag, because these are what turn a plan review into an incident:

- a `delete` on anything stateful — database, volume, bucket, snapshot
- a replacement of a resource other things depend on, since the dependents churn too
- changes to state itself: `moved` blocks, imports, or a plan produced with `-refresh=false`
- any value in the plan that looks like a credential, since plan JSON is often pasted
  into a pull request

Finish with a one-line verdict: safe to apply, safe with a named precondition, or do not
apply, and say what you would want to see before changing that answer. Do not run
`terraform apply`.

For the full review procedure rather than this one file, use the `iac-review` skill.
