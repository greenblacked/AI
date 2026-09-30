# Agent enhancement decisions

This pass studies design patterns in
[`alirezarezvani/claude-skills`](https://github.com/alirezarezvani/claude-skills/tree/19392f7a08264ed00486a251f5b2098321771f94)
at revision `19392f7a08264ed00486a251f5b2098321771f94`, against this repository's
base `45aa3c6fc1477e83d8ef32e5124496e54ed4ef3a`. It is a targeted comparison, not
an audit of that entire repository. No source code, skill text, templates, hooks or
installation machinery are imported, and none of its scripts are executed.

## Selected changes

| Pattern studied | Local decision | Evidence to check |
| --- | --- | --- |
| Explicit phase routing and short phase handoffs | Clarify an essential missing outcome before dependent dispatch; return decisions, artifact pointers and unresolved prerequisites | `agent-orchestration` and its delegation contract; inspect raw evidence before releasing dependants |
| Paired baseline and with-skill evaluation | Bind routing comparisons to the same case population and run settings; do not display misleading deltas | Trigger harness tests cover compatible and incompatible baselines |
| Concrete output artifacts and self-verification | Ask skill review to verify the promised result and completion evidence, including conflicts when composing procedures | `skill-reviewer` examines the procedure, not just its valid frontmatter |

The first pattern comes from the pinned
[orchestrator](https://github.com/alirezarezvani/claude-skills/blob/19392f7a08264ed00486a251f5b2098321771f94/agent-launcher/skills/agent-launcher-orchestrator/SKILL.md)
and [composition guide](https://github.com/alirezarezvani/claude-skills/blob/19392f7a08264ed00486a251f5b2098321771f94/orchestration/ORCHESTRATION.md).
The latter two come from the pinned
[production pipeline](https://github.com/alirezarezvani/claude-skills/blob/19392f7a08264ed00486a251f5b2098321771f94/SKILL_PIPELINE.md)
and [authoring standard](https://github.com/alirezarezvani/claude-skills/blob/19392f7a08264ed00486a251f5b2098321771f94/SKILL-AUTHORING-STANDARD.md).
The implementation follows local contracts rather than their wording or schemas.

## Patterns not adopted

Keep our existing exclusive scopes, attempt identities, quiescence checks, trusted
capture and fresh combined review. A persona or phase label provides none of those
guarantees. Loading several skills does not prove their instructions are compatible.
Resolve material conflicts under current user authority and repository instructions.

Do not import universal quality percentages, mandatory agent/command pairs, automatic
description rewrites, recurring deployment hooks or runtime mirror trees. They do not
prove a local improvement. Sampled routing remains optional and separate from
deterministic CI. A declared model alias is not a pinned resolved model snapshot.

## Next priorities

1. Add an interactive boundary to the recovery mock: accept one candidate request,
   return its adapter-owned observation, then accept the next request. Preserve the
   existing bulk replay interface. Test adaptive retries, stale callbacks, explicit
   completion, candidate limits and evaluator interruption before connecting a host.
2. Evaluate workflow efficacy separately from routing. Use representative task fixtures,
   deterministic result and constraint checks, a sealed holdout and repeated paired
   trials. Keep expected outcomes and capture outside candidate write scope. Unit tests
   and synthetic controls do not measure model performance.
3. If unattended execution is requested, define continuing authorization and revocation
   per run before adding a scheduler. Specify duplicate-delivery handling, target scope,
   expiry and in-flight fencing; test those rules without real external effects.
4. Add a runtime-specific adapter only for a demonstrated discovery or dispatch gap.
   Verify that runtime's enforced versus advisory restrictions and installation behavior
   instead of deriving support from a generic compatibility label.

These are follow-up design priorities, not permission to run models, install hooks,
schedule work, deploy, or change an external system.
