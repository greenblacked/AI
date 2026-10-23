# Move mechanics

Read this at step 5, before the first slice. Both mechanisms assume the gates in
`SKILL.md` hold: zero-diff baseline, both states backed up with serial and lineage
recorded, and applies frozen on both stacks for the slice. Commands use `terraform`;
`tofu` takes the same subcommands and flags for everything here.

## Contents

- Choosing per slice
- Removed and import blocks
- Generating import blocks from the backup
- Import ID traps
- State mv between pulled states
- Provider addresses must match
- When a slice goes wrong

## Choosing per slice

| Question | Blocks | Pulled-state `state mv` |
| --- | --- | --- |
| Reviewable before it lands | Yes, both halves appear in a plan | No |
| Needs a correct import ID per resource | Yes | No; the object's recorded attributes move as they are |
| Version floor | Terraform 1.7 or OpenTofu 1.7 for `removed` | Any |
| Good for | Small slices; the data layer; anything someone will want to review | Hundreds of homogeneous resources where ID formats are a minefield |

Tools that wrap multi-state moves in a migration file with a plan step exist; if one is in
use, the gates are unchanged.

## Removed and import blocks

1. In the old root, delete the resource or module blocks for the slice and add one
   `removed` block per top-level address:

   ```hcl
   removed {
     from = module.network
     lifecycle {
       destroy = false
     }
   }
   ```

   `destroy = false` is the whole point; without it the block destroys the objects.

2. Plan the old root. Every resource in the slice should be listed as no longer managed,
   with nothing to add, change or destroy. Apply.
3. In the new root, add the moved configuration and an `imports.tf` generated as below.
4. Plan the new root. The summary must read as imports only, with 0 to add, 0 to change and
   0 to destroy. A proposed change on an imported resource means the configuration does not
   describe the object: fix the configuration, never apply the change as part of the move.
   Apply.
5. Run the gate in `SKILL.md` step 6.

Keep `removed` and `import` blocks until the slice has been applied in every environment,
then delete them in a separate change.

## Generating import blocks from the backup

The backup from gate 2 holds every instance's address and recorded attributes. Generate
blocks for one module from it rather than typing IDs:

```bash
set -Eeuo pipefail
umask 077
mod="module.network"
state="$work/monolith-before.tfstate"

# Matches the module itself, its children, and an indexed instance such as module.network["eu"]
select_slice='def inmod($m): (. // "") | (. == $m or startswith($m + ".") or startswith($m + "["));
  .resources[] | select(.mode == "managed" and (.module | inmod($mod)))'

jq -r --arg mod "$mod" "$select_slice"'
  | . as $r | .instances[]
  | ($r.module + "." + $r.type + "." + $r.name
     + (if .index_key == null then ""
        elif (.index_key | type) == "number" then "[\(.index_key)]"
        else "[\(.index_key | tojson)]" end)) as $to
  | (.attributes.id // error("no id attribute for \($to)")) as $id
  | "import {\n  to = \($to)\n  id = \($id | tojson)\n}\n"' "$state" > imports.tf

expected="$(jq --arg mod "$mod" "[$select_slice"' | .instances | length] | add // 0' "$state")"
actual="$(grep -c '^import {' imports.tf || true)"
[[ "$expected" -gt 0 && "$expected" == "$actual" ]] \
  || { echo "expected $expected import blocks, wrote $actual" >&2; exit 1; }
```

The script fails when the count differs from the number of instances in the slice, and
`jq` stops with an error naming any instance that has no `id` attribute; the earlier form
wrote `id = "null"` for it and skipped a module with an index such as `module.network["eu"]`
without a word. Delete `imports.tf` after a failed run. Two edits usually follow:

- If the new root calls the module under a different name, or the slice moves from a
  nested module to the root, rewrite each `to` to the new address.
- Check every resource type against the ID traps below; `.attributes.id` is the import ID
  for many types and not for others.

## Import ID traps

The import ID is whatever the resource's own import documentation says, and the `id`
attribute in state is whatever the provider chose to store. They often agree; when they do
not, the import either fails or adopts the wrong object under the right address.

| Shape of the trap | Examples | What to do |
| --- | --- | --- |
| `id` is synthetic, import wants a composite | AWS IAM policy attachments, AWS security group rules | Build the ID from other attributes per the import documentation, or move these with `state mv` |
| `id` is a full path, import accepts several forms | Google resources (`projects/.../...`) | The stored path is usually accepted; confirm on one resource first |
| `id` is the cloud resource ID | Azure resources | Usually correct as is; Azure IDs are case-insensitive, so do not "fix" the case |
| Resource has no standalone import | Some association and attachment types | Move with `state mv`, or recreate deliberately as a reviewed change |

For each resource type in the slice, import one instance first and read the plan before
generating the rest.

## State mv between pulled states

`state mv` with `-state` and `-state-out` works on local files only, so pull both states,
move in a scratch directory with no backend configured, and push back.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
OLD_DIR="${1:?old root directory}"
NEW_DIR="${2:?new root directory, already initialised against its backend}"
SLICE="$(readlink -f "${3:?file of addresses, one per line, or 'from<TAB>to' pairs}")"  # absolute: the script cd's

scratch="$(mktemp -d)"
terraform -chdir="$OLD_DIR" state pull > "$scratch/old.tfstate"
terraform -chdir="$NEW_DIR" state pull > "$scratch/new.tfstate"
[[ -s "$scratch/new.tfstate" ]] || rm -f "$scratch/new.tfstate"   # brand-new stack
cp "$scratch/old.tfstate" "$scratch/old.before.tfstate"
[[ -f "$scratch/new.tfstate" ]] && cp "$scratch/new.tfstate" "$scratch/new.before.tfstate"

cd "$scratch"
while IFS=$'\t' read -r from to || [[ -n "$from" ]]; do
  [[ -n "$from" ]] || continue
  to="${to:-$from}"
  terraform state mv -dry-run -state=old.tfstate -state-out=new.tfstate "$from" "$to" < /dev/null
  terraform state mv -state=old.tfstate -state-out=new.tfstate "$from" "$to" < /dev/null
done < "$SLICE"

echo "scratch: $scratch"
```

The slice file is tab-separated, not space-separated, because an address can contain a space
inside a `for_each` key (`aws_x.y["a b"]`); the loop also keeps a last line with no trailing
newline. `SLICE` is made absolute before the `cd`, or a relative path stops resolving.

Then, in this order, matching gate 5:

1. `terraform -chdir="$OLD_DIR" state push "$scratch/old.tfstate"`
2. `terraform -chdir="$NEW_DIR" state push "$scratch/new.tfstate"`
3. Commit the configuration move: the blocks leave the old root and arrive in the new one.
4. Run the gate in `SKILL.md` step 6.

`state push` refuses a file whose lineage differs from the remote or whose serial is not
newer. If it refuses, someone wrote to that state during the freeze. Stop, find out what
they wrote, and redo the slice from fresh pulls. Do not reach for `-force`; it is the flag
that discards their write.

Delete the scratch directory once both plans are clean and the backups are stored with the
same access controls as live state. Every file in it is a credential file.

## Provider addresses must match

State records each resource's provider configuration address, including any alias, such as
`provider["registry.terraform.io/hashicorp/aws"].us_east_1`. The new root must declare the
same provider and alias, or its plan fails asking for a provider configuration that is not
present. `terraform state replace-provider` changes the provider source, not the alias, so
keep alias names identical across the split, or use blocks for resources whose alias has
to change.

## When a slice goes wrong

- **Old plan fails on a reference to an undeclared resource.** A cross-boundary reference
  was missed in step 4. Replace it with a data lookup in the old root; nothing in state
  needs to change.
- **Either plan wants to create something.** Configuration stayed behind, or arrived,
  without its state. Move the block to the root whose state holds the object.
- **New plan wants to destroy something.** State arrived without its configuration, or at
  a different address. Add the configuration or a `moved` block in the new root.
- **Either plan wants to replace something.** The configuration in the new root differs
  from the old in an attribute that forces replacement. Diff the two blocks; it is almost
  always a default that the old root set through a variable.
- **Both states list the same address.** Stop all applies and remove it from whichever
  state the slice plan says should not hold it, using `removed` with `destroy = false` or
  `state rm`, with a fresh backup first.
