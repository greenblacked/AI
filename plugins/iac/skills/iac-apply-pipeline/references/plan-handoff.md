# Saved-plan handoff contract

Use this contract to design the boundary between a trusted plan job and an apply job.
The evidence record is a pipeline design recommendation, not a Terraform file format.

## Evidence the consumer must match

| Field | Producer records | Consumer verifies |
| --- | --- | --- |
| Source | Repository identity, reviewed immutable commit, root module | Trusted change record identifies that source |
| Producer | Workflow identity/revision, run and job IDs, successful result | CI's trusted records, not fields asserted only inside the artifact |
| Plan | Immutable artifact ID, cryptographic digest, creation time | Downloaded bytes match the accepted artifact |
| Target | Backend location, state selector, workspace, provider accounts and aliases | The intended target and effective credentials agree |
| Execution | Engine/version, runner OS/architecture, dependency selections, module revisions | Same compatible runtime and exact resolved dependencies |
| Inputs | Non-secret input identities, versions and protected fingerprints | Accepted inputs have not been silently substituted |
| Acceptance | Reviewer verdict, approver identity, accepted plan tuple, expiry | Approval is current and covers these bytes and this target |
| Serialization | Canonical state queue key and reservation | This run owns the right to proceed |

Do not publish raw secrets or unsalted hashes of low-entropy secret values as input
fingerprints. Record a secret-manager version identifier where possible; keep any
sensitive comparison evidence inside the protected boundary. Authentication tokens
may rotate between jobs; effective identity must remain the intended one.

## Engine behavior that shapes the contract

Terraform's [plan command](https://developer.hashicorp.com/terraform/cli/commands/plan)
distinguishes speculative output from a saved plan made with `-out`. A saved plan
contains configuration, planned values and inputs, including sensitive data in cleartext.
`-detailed-exitcode` returns 0 for no changes, 1 for failure and 2 for changes.
Capture the status without allowing shell fail-fast handling to misclassify 2; preserve
all other failures. Keep locking enabled and select a bounded `-lock-timeout`.

The [apply command](https://developer.hashicorp.com/terraform/cli/commands/apply)
does not prompt when passed a saved plan. Without that argument it plans again;
`-auto-approve` would skip the new plan's prompt. Neither form reconstructs the
external approval record. Refuse an apply path that can fall back to an unqualified
apply after an artifact lookup fails.

The [automation guide](https://developer.hashicorp.com/terraform/tutorials/automation/automate-terraform)
requires care when plan and apply run on different machines: preserve required files,
absolute paths, OS/architecture and provider binaries. Use a controlled execution
image and verified workspace bundle, or demonstrate an equivalent reconstruction.
Do not assume a fresh checkout plus a saved plan carries generated local files.
Terraform cannot establish that different planning and applying credentials name the
same cloud account; the pipeline must verify it. Keep any workspace bundle containing
`.terraform` private and reject untrusted archives before extraction or execution.

The [backend documentation](https://developer.hashicorp.com/terraform/language/backend)
explains that saved plans capture backend configuration and apply uses that captured
configuration. Changing the apply job's local backend settings is not a retargeting
mechanism. Hardcoded backend credentials can enter plans and `.terraform`; use the
backend's supported environment-based authentication instead.

[State locking](https://developer.hashicorp.com/terraform/language/state/locking)
depends on backend support. A lock failure is a stop, not a reason to disable locking.
The CI queue covers a wider lifecycle than an engine lock: it associates review with
the pending operation, while the backend protects concurrent state writes. Neither
prevents someone changing cloud objects through another API.

Check [initialization behavior](https://developer.hashicorp.com/terraform/cli/commands/init)
for the pinned CLI before implementing reconstruction. A normal deployment must not
silently update the dependency lock file or migrate a backend. Keep upgrades and
backend moves as separately reviewed changes.

## Engine boundary

[OpenTofu's plan reference](https://opentofu.org/docs/cli/commands/plan/) also documents
saved plans and detailed exit codes. That does not establish binary interchange,
provider compatibility, backend feature parity or identical test syntax with Terraform.
Check each selected engine's versioned documentation and exercise the handoff on the
actual runner before claiming support. Record an untested engine as unsupported by
this pipeline until verified, rather than replacing the executable name and assuming it.
