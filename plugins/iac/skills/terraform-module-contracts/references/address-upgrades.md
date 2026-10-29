# Preserve the address upgrade path

Terraform identifies a managed instance by its address in state. Renaming code without
declaring the move can therefore produce a destroy/create pair. Terraform 1.1 and later
supports module refactoring with `moved` blocks; confirm the module's minimum version
before using them.

For a rename within the module:

```hcl
moved {
  from = aws_s3_bucket.logs
  to   = aws_s3_bucket.archive
}
```

For an instance whose old index is known to represent the stable key `audit`:

```hcl
moved {
  from = aws_s3_bucket.archive[0]
  to   = aws_s3_bucket.archive["audit"]
}
```

The second mapping is valid only when index zero had that meaning for every supported
caller. If consumers supplied different list orders, there is no universal map from index
to key. Retain the old address scheme, require caller-specific migration, or make the
breaking boundary explicit. Do not auto-generate mappings from a newly sorted list.

## Rehearse an upgrade, not a fresh install

1. Pick a disposable account and unique names, confirm identity, and use an isolated
   state. Review the old module and provider initialization before executing it.
2. Apply the supported old release with representative inputs after approval. Record
   created resource identifiers and old addresses.
3. Change only the module source/version and migration-required caller inputs. Keep the
   same test state and provider selections, initialize, and save an upgrade plan.
4. Inspect moved addresses and all managed-resource actions. A pure address refactor
   should not mutate the remote objects. Do not apply an unexplained replacement.
5. After approval, apply the exact reviewed plan, confirm remote identifiers stayed the
   same, then verify a normal plan has no remaining changes. Clean up the disposable
   resources through their owning configuration and retain cleanup evidence.

Never reuse this test state's saved plan in another environment. A plan belongs to its
configuration, inputs, provider selection, state and target account.

## Keep the history consumers need

If a resource moves from `a` to `b` and later from `b` to `c`, preserve the chain of moved
blocks so consumers can upgrade from either earlier address. Removing a moved block is a
breaking change for callers still on the old address. The fact that the module author's
own environments upgraded is insufficient for a public or cross-team module.

Moved blocks address identity, not behavior. Changing a resource argument can still
force replacement after its address has moved. A resource-type change is especially
provider-specific; do not promise cross-type moves without documentation and a rehearsal
for the exact provider versions involved.

Official source, checked 2026-10-29:

- [Refactor modules](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) — moved addresses, instance keys, move chains and the breaking effect of removing moved blocks.
