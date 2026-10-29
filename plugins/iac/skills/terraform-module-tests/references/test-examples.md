# Minimal contract tests

## Contents

- [Test a provider-free contract](#test-a-provider-free-contract)
- [Mock a computed value deliberately](#mock-a-computed-value-deliberately)

## Test a provider-free contract

Use these as shapes for the existing module's real interface. The first example needs
Terraform 1.6 or later and no external provider. In a disposable directory, put this HCL
in the root module:

```hcl
terraform {
  required_version = ">= 1.6.0"
}

variable "retention_days" {
  type    = number
  default = 30

  validation {
    condition     = var.retention_days >= 1 && var.retention_days <= 365
    error_message = "retention_days must be between 1 and 365."
  }
}

output "retention_days" {
  value = var.retention_days
}
```

Place the following in `tests/contract.tftest.hcl` relative to that disposable module:

```hcl
run "preserves_default" {
  command = plan

  assert {
    condition     = output.retention_days == 30
    error_message = "The default retention contract changed."
  }
}

run "accepts_upper_boundary" {
  command = plan

  variables {
    retention_days = 365
  }

  assert {
    condition     = output.retention_days == 365
    error_message = "A valid explicit retention value was not preserved."
  }
}

run "rejects_zero" {
  command = plan

  variables {
    retention_days = 0
  }

  expect_failures = [var.retention_days]
}
```

Run the command sequence in the main skill. To prove the first assertion, change only the
default from 30 to 31 in a second disposable copy; the first run must fail for its
retention assertion. A failure to initialize Terraform or parse HCL is not that evidence.

## Mock a computed value deliberately

For an existing module that declares an `aws_s3_bucket.archive` resource, Terraform 1.7
or later can supply a deterministic computed ARN through a test-file mock:

```hcl
mock_provider "aws" {
  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::module-test-archive"
    }
  }
}

run "uses_expected_bucket_contract" {
  command = apply

  assert {
    condition     = aws_s3_bucket.archive.arn == "arn:aws:s3:::module-test-archive"
    error_message = "The expected mocked bucket was not used."
  }
}
```

This fragment requires the existing module's provider requirement, resource and inputs;
it is not a standalone AWS deployment. Apply here materializes mocked computed values.
It is harmless to cloud resources only when every reached provider/resource is mocked
and the inspected configuration has no other execution side effects. Map aliases
explicitly when the module uses them; do not accidentally retain a real default provider.

The ARN assertion demonstrates deterministic mock wiring, not a meaningful business
contract by itself. In the real suite, assert a module output or policy expression that
depends on the ARN and would fail if that expression were wrong. Assert the module's
configured settings separately. A mock returning an ARN says nothing about whether AWS
would accept the resource or its permissions.

Official sources, checked 2026-10-29:

- [Tests](https://developer.hashicorp.com/terraform/language/tests) — run blocks, assertions and `expect_failures`.
- [Mocks](https://developer.hashicorp.com/terraform/language/tests/mocking) — `mock_provider`, `mock_resource` and computed defaults.
