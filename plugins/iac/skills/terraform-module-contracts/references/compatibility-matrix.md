# Classify the contract a caller actually uses

Use a row per change. Record the old value or shape, new value or shape, affected callers,
compatibility decision, proving fixture, and migration action. Unknown consumers are an
explicit coverage gap, not evidence that nobody depends on the old behavior.

| Surface | Easy-to-miss break | Useful fixture |
| --- | --- | --- |
| Input | Optional becomes required; null or an empty collection gains new meaning | Old caller with omitted, null and empty values separately |
| Default | Existing caller silently changes retention, exposure, size or region | Caller that omits the input, comparing expected behavior |
| Validation | Previously accepted input now fails | A concrete old accepted value plus the intended new rejection |
| Output | String becomes object, key disappears, sensitivity changes | Small caller that consumes the old output expression |
| Provider | New required alias or stricter compatible-version range | Caller passing the prior provider mapping |
| Address | Resource label, nested path or instance key changes | Upgrade from old resources in the same disposable state |

An optional attribute with a default can make an additive input change compatible, but
check how explicit null is handled. Do not infer null behavior from a type declaration
alone. Terraform's `nullable` and default rules are part of the interface.

Prefer an output exposing the intended public contract over passing an entire provider
resource object through. Adding provider-computed fields to a public output makes the
provider schema an accidental consumer interface. Mark sensitive outputs correctly, but
do not describe the sensitive flag as encryption or removal from state.

## Provider requirements and configurations are different

A reusable child module declares `required_providers`, including source and the minimum
version containing its features. The caller configures credentials, endpoints and
regions. Requirements are not inherited from a parent; default provider configurations
can be inherited, while aliased configurations must be passed explicitly.

For a module already requiring a replica provider, the two sides look like this:

```hcl
# Child module requirement.
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.replica]
    }
  }
}

# Existing caller mapping, beside its configured aws and aws.replica providers.
module "storage" {
  source = "./modules/storage"
  providers = {
    aws         = aws
    aws.replica = aws.replica
  }
}
```

This illustrates the mapping only; retain the real module's justified version constraint
and inputs. Adding `aws.replica` to a previously single-provider module is a caller
contract change. Check every supported calling pattern rather than assuming inheritance
supplies the alias.

## Evidence and limits

Formatting and validation are necessary but do not exercise API permissions, remote
service behavior, or upgrades from old state. Mocked tests cover expressions and interface
branches; an isolated integration rehearsal covers provider behavior and cleanup. Record
these as separate results, not one green “module works” claim.

Official sources, checked 2026-10-29:

- [Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers) — requirements, root configurations and aliases.
- [Input variables](https://developer.hashicorp.com/terraform/language/values/variables) — defaults, nullable inputs and validation.
- [Sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data) — redaction and state exposure.
