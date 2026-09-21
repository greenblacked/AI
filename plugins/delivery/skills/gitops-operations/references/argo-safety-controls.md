# Argo CD Safety Controls

These fields, defaults, phases, and rollback constraints are specific to Argo CD. For Flux, apply the ownership and verification method from the main skill, then verify suspension, pruning, dependency, and remediation behavior against the installed Flux controllers and their version-specific documentation.

## Automation controls

| Control | Default behavior | Review before enabling |
| --- | --- | --- |
| Automated sync | Manual sync is otherwise required | Branch protection, render review, verification, and recovery commit path |
| Prune | Automated sync does not prune by default | Ownership, retention, shared resources, and restore path |
| Self-heal | Disabled by default | Legitimate live writers, emergency procedure, and diff correctness |
| Allow empty | Empty target is protected from automated pruning by default | Generator failure modes and deliberate application retirement |

For an ApplicationSet-managed Application, set automated-sync behavior through the ApplicationSet template or supported ApplicationSet control. Directly toggling the generated Application does not establish durable policy.

Argo CD does not permit rollback while automated sync is enabled. Prefer reverting or forward-fixing Git. A temporary suspension is an incident control with an owner and a precise resumption condition, not a recovery endpoint.

## Phases, waves, and hooks

Argo CD orders phases first, then waves from lower to higher; wave zero is the default and negative waves are allowed. A failed `PreSync` hook stops the sync. `PostSync` runs only after the sync succeeds and resources are Healthy. Use negative waves for prerequisites only when the dependency is real. Resources in the same wave are not a sequential script.

Before adding a hook, answer:

- Is it safe to retry?
- How is success distinguished from a hung job?
- What happens when selective sync skips hooks?
- What cleanup policy applies to completed or failed hook resources?
- Can its side effect be represented as ordinary declarative state instead?

Prune ordering differs from create/update ordering: resources are pruned in reverse wave order, and prune can be deferred until other resources are healthy with the documented prune-last behavior. Review deletion dependencies separately from creation dependencies.

## Recovery gates

Before applying a recovery revision:

1. Identify the last known-good immutable revision.
2. Render it against the current source set; an old application commit may still resolve a newer chart or values dependency.
3. Review removals and immutable-field replacements.
4. Confirm schema and state remain backward-compatible.
5. Decide whether Git revert or forward fix preserves the clearest history.
6. Verify sync, health, and customer behavior after reconciliation.

## Official sources

- [Argo CD: Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD: Sync Phases and Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [Argo CD: Prune Last](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/#prune-last)
