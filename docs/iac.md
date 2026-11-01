# Infrastructure as code: start here

The `iac` plugin covers evolving a Terraform module's public contract, proving its
behavior and connecting a reviewed plan to the apply that consumes it. It complements
the existing review, state-management and platform skills; it does not relocate them.

## Install and use

For Claude Code, register the marketplace and install the focused plugin:

```text
/plugin marketplace add greenblacked/AI
/plugin install iac@greenblacked-ai
/reload-plugins
```

Then describe the task in ordinary language. For example: "We need to change an
existing module's input shape without breaking its callers", "Write module tests
that catch this invalid combination", or "Our apply job must consume exactly the
Terraform plan the reviewer accepted". These are different jobs with different gates.

For Codex and other assistants, follow [Using the skills](using.md). Native skill
loading, portable files and permissions differ by host; an exported procedure does
not install a cloud credential or confer authority to apply infrastructure.

## Choose the owner

| Task | Skill and plugin | What to bring |
| --- | --- | --- |
| Evolve an existing module's inputs, outputs and compatibility | [terraform-module-contracts](../plugins/iac/skills/terraform-module-contracts/SKILL.md), `iac` | Current interface, representative callers and intended change |
| Test a module's behavior and failure cases | [terraform-module-tests](../plugins/iac/skills/terraform-module-tests/SKILL.md), `iac` | Contract, supported engine versions and test environment constraints |
| Bind plan approval to one apply and serialize writers | [iac-apply-pipeline](../plugins/iac/skills/iac-apply-pipeline/SKILL.md), `iac` | Workflow, state identity, artifact path and approval policy |
| Create a first module or implement a settled workflow | [code-scaffold](../plugins/coding/skills/code-scaffold/SKILL.md), `coding` | Concrete specification and repository conventions |
| Judge whether a proposed change is safe | [iac-review](../plugins/security/skills/iac-review/SKILL.md), `security` | Restricted access to the exact plan and intended target |
| Import, move, repair state or investigate a stuck lock | [terraform-state](../plugins/operations/skills/terraform-state/SKILL.md), `operations` | Verified target, current writer status and recovery context |
| Adopt a hand-built estate | [brownfield-iac-adoption](../plugins/platform/skills/brownfield-iac-adoption/SKILL.md), `platform` | Provider inventory, existing states and ownership boundaries |
| Split an oversized state | [monolith-state-split](../plugins/platform/skills/monolith-state-split/SKILL.md), `platform` | Dependency graph and proposed stack boundaries |
| Upgrade engine or provider versions | [iac-version-upgrade](../plugins/platform/skills/iac-version-upgrade/SKILL.md), `platform` | Current pins, desired versions and affected environments |
| Design general CI stages, caches and required checks | [ci-pipeline-design](../plugins/delivery/skills/ci-pipeline-design/SKILL.md), `delivery` | Run history and pipeline constraints |
| Audit a workflow's attacker reach | [pipeline-hardening](../plugins/delivery/skills/pipeline-hardening/SKILL.md), `delivery` | Workflow events, permissions and artifact consumers |
| Replace static cloud keys with federation | [workload-identity](../plugins/platform/skills/workload-identity/SKILL.md), `platform` | Issuer, audience, exact subjects and intended cloud roles |

Install the neighboring plugin when its skill is needed; installing `iac` does not
pull in the other plugins. Links are routing guidance, not a claim that an absent
skill can run in the current assistant.

## Follow the evidence

For a module change, first identify the interface and callers, then test the promised
behavior, then review a real consumer's plan. A passing module test does not approve
production changes. For a delivery change, establish the saved-plan handoff before
implementing workflow YAML, then exercise its rejection paths in an isolated target.
Pipeline success does not establish that the proposed infrastructure is appropriate;
the plan review remains a separate decision.

An incident may enter this map halfway through. A stuck writer belongs with state
recovery before pipeline redesign. An unwanted replacement belongs with plan review
before an interface refactor. Preserve the evidence from that investigation so the
next skill solves the identified problem rather than repeating discovery.

## Engine and permission limits

These new procedures are Terraform-focused. OpenTofu support must be established for
the exact pinned version, providers and backend; similar command names do not prove
matching test features or saved-plan formats. Do not transfer saved plans between
engines. The individual skills say where engine-specific verification is required.
For a migration, start with `iac-version-upgrade` and its compatibility gates.

Keep plans, state, variable files and test credentials private. Do not paste their raw
contents into a public issue to ask which skill applies. State the target and symptom,
then give the assistant restricted access to the necessary evidence. Planning and
testing can execute provider or module code, and integration tests can create billed
resources. Set target, authorization, cleanup owner and evidence requirements before
running them; report unavailable checks as unverified.
