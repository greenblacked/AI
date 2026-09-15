# Resource addresses

Read this when an address involves an index, a `for_each` key, a module path or a provider
alias, or when a `moved` or `import` block matches nothing and the error says the address
is not in the configuration or not in the state.

## Contents

- The grammar
- Indexes and keys
- Quoting on the command line
- Addresses inside blocks
- Finding the address you actually want
- Provider addresses

## The grammar

An address is a dot-separated path from the root module to one instance:

```text
module.MODULE_NAME[MODULE_INDEX].TYPE.NAME[INSTANCE_KEY]
```

Every segment before `TYPE` is a module call, not a directory. A module at
`modules/network` called as `module.vpc` is addressed `module.vpc`, and the directory name
appears nowhere. Nested calls chain: `module.platform.module.vpc.aws_subnet.private`.

Data sources take a `data.` prefix: `data.aws_ami.base`, and inside a module
`module.vpc.data.aws_availability_zones.all`.

## Indexes and keys

`count` produces integer indexes, `for_each` produces string keys, and they are not
interchangeable:

```text
aws_instance.web[0]       # count
aws_instance.web["blue"]  # for_each
aws_instance.web          # every instance of the resource, in commands that accept it
```

The bare address matches all instances in `state list`, `state rm` and `state mv`, which
is the quiet way to move more than you meant. When a resource has instances, name the
instance.

Switching a resource from `count` to `for_each` is the common case: each instance needs
its own `moved` block, because the mapping from index to key is yours to state and
Terraform cannot guess it.

```hcl
moved {
  from = aws_instance.web[0]
  to   = aws_instance.web["blue"]
}
```

## Quoting on the command line

Brackets are shell globs and double quotes are shell syntax, so an unquoted address is
rewritten before Terraform ever sees it. Single-quote the whole address:

```bash
set -Eeuo pipefail
terraform state mv 'aws_instance.web[0]' 'aws_instance.web["blue"]'
terraform state show 'module.vpc.aws_subnet.private["eu-west-1a"]'
```

A key containing a slash, a space or a colon is still one key: quote it in HCL and leave
it inside the single quotes on the shell. If the key itself contains a single quote, put
the address in a file and use the `moved` block instead — that is the case the CLI does
not make safe.

## Addresses inside blocks

`from` and `to` in a `moved` or `removed` block, and `to` in an `import` block, are static
addresses. They take no interpolation, no variables and no functions. The `import` block's
`id` is different: from Terraform 1.6 it accepts an expression as long as the value is a
string known at plan time, and from 1.7 an `import` block can carry `for_each` to expand
over a map of ids.

A `moved` block whose `from` is still present in the configuration is an error, not a
no-op. The pair describes a rename, so the old address has to be gone.

## Finding the address you actually want

```bash
set -Eeuo pipefail
terraform state list | grep -F 'aws_instance'
terraform state list 'module.vpc'          # everything under one module call
terraform show -json | jq -r '.values.root_module | .. | .address? // empty'
```

`terraform state show ADDRESS` prints the recorded attributes, which is the fastest way to
confirm you have the right object before moving it — and it prints secrets, so redirect it
to a file with a restrictive umask rather than reading it in a shared terminal.

## Provider addresses

Instances record which provider configuration manages them. Renaming a provider alias, or
moving to a fork such as OpenTofu's registry namespace, leaves the old provider address in
state and produces an error about a provider that is no longer in the configuration. The
fix is `terraform state replace-provider OLD NEW`, which rewrites those bindings and
nothing else. It lists the instances it will change and waits for confirmation, so read
that list rather than passing `-auto-approve`:

```bash
set -Eeuo pipefail
terraform state replace-provider 'registry.terraform.io/-/aws' 'registry.terraform.io/hashicorp/aws'
```
