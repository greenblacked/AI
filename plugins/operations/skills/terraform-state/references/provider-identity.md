# Provider identity diagnostic

## Contents

- [Build the isolated configuration](#build-the-isolated-configuration)
- [Run without touching the backend](#run-without-touching-the-backend)

Use before the first state pull and repeat before each mutation. This is a temporary
read-only Terraform configuration, not an edit to the live root module. It exercises the
provider configuration and credential chain that the operation will use, including each
alias. A provider identity must match the independently trusted target record.

## Build the isolated configuration

In a restricted temporary directory, create a diagnostic root with only the original
`required_providers` constraints, the same dependency lockfile, provider blocks and
their referenced variables and values. Preserve aliases, assume-role/impersonation,
environment, credential injection, and provider version. Resolve expressions supplied
by the original module faithfully; if they depend on resources or cannot be reproduced,
stop. Do not copy backend, `cloud` block, resources, modules, or state; inspect the
backend selector separately in the live configuration. Do not paste credentials into
diagnostic HCL or logs. If credentials are available only in remote execution, run the
diagnostic there under the same identity or stop.

Before initialization or planning, inspect the documentation for the pinned provider
version for configuration-time effects. AzureRM can automatically register Azure
Resource Providers during provider configuration, even in a plan. Disable that effect
in **each diagnostic AzureRM provider block**: use
`resource_provider_registrations = "none"` and
`resource_providers_to_register = []` where the pinned version supports them, or the
legacy `skip_provider_registration = true` where that is the documented option. This
registration opt-out is the only permitted difference from the real provider settings;
it must not change tenant, subscription, identity, aliases, or credential source. If the
pinned version's opt-out is unknown, rejected, or cannot be shown to prevent writes,
stop before running the diagnostic. Apply the same read-only scrutiny to other provider
families: `init` and data reads are safe here only when their actual provider behaviour
is known not to mutate external state. A Terraform plan is not inherently side-effect
free at provider initialization.

Add one data block and a narrow output per relevant provider configuration. For aliases,
set `provider = aws.NAME`, `google.NAME`, or `azurerm.NAME` in each data block. These
examples show a default provider; duplicate for every alias and give each block and
output a distinct label.

```hcl
data "aws_caller_identity" "check" {}
output "aws_account" { value = data.aws_caller_identity.check.account_id }

data "google_client_config" "check" {}
output "google_project" { value = data.google_client_config.check.project }

data "azurerm_client_config" "check" {}
output "azure_target" {
  value = {
    tenant_id       = data.azurerm_client_config.check.tenant_id
    subscription_id = data.azurerm_client_config.check.subscription_id
    object_id       = data.azurerm_client_config.check.object_id
  }
}
```

Include only the provider families actually configured. AWS's caller identity returns
the effective account. Google client config reports the configured project, not proof
of the token principal or an impersonated service account's authority; verify the
impersonation target and effective credential chain independently. Azure client config
reports provider tenant, subscription and object ID; check all applicable values. A
provider family without an adequate read-only identity source requires another trusted
method, not a guess from a CLI default.

## Run without touching the backend

Initialize the isolated directory with backend disabled and the existing lockfile in
read-only mode, then plan its data-only configuration. Supply the same nonsecret
variable inputs and credential environment as the intended operation. Run from that
directory (or use Terraform's `-chdir=DIR` global option):

```bash
set -Eeuo pipefail
umask 077
terraform init -backend=false -lockfile=readonly -input=false
terraform plan -input=false -out=identity.tfplan
terraform show -json identity.tfplan | jq -e '.planned_values.outputs |
  if type == "object" and length > 0 and
     all(.[]; .sensitive != true and
       (.value | if type == "string" then length > 0
                 elif type == "object" then length > 0 and
                   all(.[]; type == "string" and length > 0)
                 else false end))
  then with_entries(.value = .value.value)
  else error("identity unavailable or sensitive") end'
```

The saved plan may contain secrets even if the filtered output does not. Restrict its
permissions and location, do not print raw JSON or tokens, and remove it after comparing
only nonsecret target IDs with the trusted record. Verify the complete expected output
set for every provider and alias; the filter cannot know which aliases were omitted.
A data read deferred until apply,
unknown/null output, provider error, alias mismatch, or incomplete identity is a failed
gate; never apply this diagnostic or use it to change live state. `init -backend=false`
does not make the live configuration safe to plan, which is why this root has no backend
or managed resources. Rebuild and rerun after any provider, variable, credential, or
execution-context change.

Primary references: Terraform [provider aliases](https://developer.hashicorp.com/terraform/language/block/provider),
[backend-disabled init](https://developer.hashicorp.com/terraform/cli/commands/init),
[data-source timing](https://developer.hashicorp.com/terraform/language/data-sources),
and provider docs for [AWS caller identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity),
[Google client config](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/client_config),
and [Azure client config](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/client_config).
For AzureRM registration settings, consult the [pinned provider's documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
and [4.0 upgrade guide](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/4.0-upgrade-guide).
