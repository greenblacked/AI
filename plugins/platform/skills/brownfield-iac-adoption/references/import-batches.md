# Import batches

Read this at steps 6 to 8. It covers turning rows of the unmanaged list into import blocks,
cleaning the configuration Terraform generates for them, restructuring into modules
without a diff, and the shape of the coverage report.

## Contents

- Generating import blocks from the inventory
- Checking the import ID per type
- Cleaning generated configuration
- Rewriting into modules
- The coverage report

## Generating import blocks from the inventory

Generate plain `import` blocks, one per resource. `-generate-config-out` writes
configuration for import targets that have no resource block yet; switch to an `import`
block with `for_each` (Terraform 1.7, OpenTofu 1.7) only once the resource blocks exist,
because configuration generation does not handle every `for_each` form.

An example for S3 buckets from the AWS inventory rows, where the import ID is the bucket
name:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
# batch.tsv: rows of inventory.tsv selected for this batch
while IFS=$'\t' read -r _cloud _account _region type arn _tags || [[ -n "${arn:-}" ]]; do
  [[ "$type" == "s3:bucket" ]] || continue
  bucket="${arn#arn:aws:s3:::}"
  name="b_${bucket//[^A-Za-z0-9_]/_}"
  printf 'import {\n  to = aws_s3_bucket.%s\n  id = "%s"\n}\n\n' "$name" "$bucket"
done < batch.tsv > imports.tf
grep -c '^import {' imports.tf
# Two bucket names can sanitise to one address (my-bucket and my_bucket); list any clash
dupes="$(grep '^  to = ' imports.tf | sort | uniq -d)"
[[ -z "$dupes" ]] || { printf 'address clash:\n%s\n' "$dupes" >&2; exit 1; }
```

The `type` value depends on which inventory produced the row; match on what your
inventory file actually contains. Resource names in Terraform must start with a letter or
underscore, hence the prefix. Rename them during the module rewrite, with `moved` blocks.

## Checking the import ID per type

The import ID format is set by each resource's import documentation, and it is the most
common way to adopt the wrong object under the right address. Before generating a whole
batch of one type:

1. Read the import section of that resource's provider documentation.
2. Import one instance, run the plan, and check the plan names the object you meant.
3. Only then generate the rest of that type.

Composite IDs (a role name and a policy ARN joined, a zone ID and a record name joined) are
where guessing from the console fails.

## Cleaning generated configuration

`terraform plan -generate-config-out=generated.tf` refuses to overwrite an existing file,
writes every argument the provider returned, and leaves you a draft. Before the first real
plan:

- [ ] Remove arguments the plan reports as conflicting or computed-only; the error names
      them.
- [ ] Choose one style for rules and attachments. Generated security groups carry inline
      rules; if the estate also uses separate rule resources, the two will fight.
- [ ] Replace literal IDs of resources already imported (VPC, subnet, key, role) with
      references to them.
- [ ] Remove arguments that only restate a provider default you do not mean to pin.
- [ ] Search the file for anything credential-shaped before committing. Generated
      configuration can contain values a reviewer should never see in a repository.
- [ ] For a resource that is really several, such as a bucket with versioning, encryption
      and a policy, add imports for the companion resources in the same batch.

The plan after clean-up must read as imports only, with 0 to add, 0 to change and 0 to
destroy. Any change means the configuration still does not describe the object; edit it
until the change disappears.

## Rewriting into modules

After a batch has been imported and its plan is empty:

```hcl
moved {
  from = aws_s3_bucket.b_acme_logs_prod
  to   = module.logging.aws_s3_bucket.this
}
```

1. Move resources into modules and add a `moved` block for every changed address.
2. Replace repeated literals with variables and remaining literal IDs with references or
   data lookups.
3. Plan. The only acceptable output is moves. An attribute change means the module renders
   something different from what was imported; fix the module, not the object.
4. Keep the `moved` blocks until every environment that held the old addresses has applied.

Keep this in its own commit, separate from the import, so a reviewer can see that one
change adopted objects and the other only renamed addresses.

## The coverage report

Run the inventory, managed-set and diff steps from `references/inventory-and-diff.md` as a
scheduled job with a read-only role. Keep the previous run's `unmanaged.ids` to diff
against. One table per run:

| Account | Inventory | Owned elsewhere | Managed | Unknown | Coverage | New unmanaged since last run |
| --- | --- | --- | --- | --- | --- | --- |
| prod-payments | 1,240 | 310 | 870 | 12 | 93.5% | 3 |
| prod-web | 2,105 | 640 | 1,190 | 140 | 81.2% | 0 |

Coverage is managed over inventory minus owned elsewhere. Alongside the table, list the new
unmanaged resources with their creator from the audit log, and the resource types the
inventory does not cover, so the percentage says what it is a percentage of.

Alert on new unmanaged resources in production accounts. A falling Unknown count and a
zero for new unmanaged are the two numbers that show the estate is actually converging.
