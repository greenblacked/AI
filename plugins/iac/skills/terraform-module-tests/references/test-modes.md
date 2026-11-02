# Choose the evidence the test can produce

| Mode | Proves | Does not prove |
| --- | --- | --- |
| `terraform validate` | Configuration syntax, internal references and consistency | Runtime input combinations or a deployable cloud change |
| Test with `command = plan`, real providers | Plan-known expressions and custom conditions | Apply-time computed values, cloud creation or absence of API access |
| Test with mocked providers | Configuration branches and assertions with controlled provider values | Provider API semantics, permissions or actual service constraints |
| Test with `command = apply`, real providers | Behavior that requires disposable real resources | Production account correctness or successful cleanup without inspecting it |

Terraform tests are available from 1.6; mocking is available from 1.7. Consult the pinned
version's documentation for newer test attributes rather than copying examples from the
latest version. A mock still uses provider schemas, so provider packages may need to be
installed. A mock does not make arbitrary configuration, provisioners or external tools
safe to execute.

## Selection is an execution boundary

`terraform test -filter=tests/contract.tftest.hcl` selects that test file. The filter takes
a filename, not the name of a run block. Multiple filters can select multiple files.
Review every run in every selected file; a setup run can apply real infrastructure even
when the final assertion run uses plan.

`-test-directory` changes the additional search directory. Terraform still discovers
test files in the root module directory, so directory layout alone must not be the guard
between uncredentialed PR checks and integration credentials.

## Expected failures have a narrow meaning

Use `expect_failures` to name a custom condition whose failure is the intended behavior,
such as `var.retention_days`. With a plan-known validation, choose `command = plan`.
An apply run expecting a failure can itself fail when the condition fails during the
preceding plan, because Terraform never reaches the expected operation.

Unknown values also matter. A plan assertion cannot prove a value that will only be
known after apply. Either assert a plan-known property, supply deterministic mock values,
or use a real integration test. Do not weaken the assertion merely to obtain a pass.

## Cleanup is a result

Tests use separate state, initially empty and held in memory, rather than the module's
normal backend state. Terraform attempts to destroy created resources after a test file.
Setup modules and later runs can have dependent state; keep the dependency graph simple
and inspect cleanup order for the exact suite. Report resources Terraform says it could
not destroy, even when the behavioral assertions passed.

Keep test logs private when they include resource identifiers, configuration or state.
Preserve any recovery state or instructions Terraform emits after a failure according to
the team's secret-handling policy. Use the recorded test resources and the dedicated
account for recovery; do not assume a normal module destroy targets the test resources.

Official sources, checked 2026-10-29:

- [Test language](https://developer.hashicorp.com/terraform/language/tests) — version boundary, run defaults, assertions and expected failures.
- [Provider mocking](https://developer.hashicorp.com/terraform/language/tests/mocking) — mocked schemas, computed values and real/mock provider mappings.
- [Test command](https://developer.hashicorp.com/terraform/cli/commands/test) — file filters, root discovery, separate state and cleanup diagnostics.
