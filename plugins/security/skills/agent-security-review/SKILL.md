---
name: agent-security-review
description: "Review an LLM agent where untrusted web pages, retrieved documents, files, messages or tool results can influence privileged tool calls: trace content through the model into action parameters; require tool-side authorization and tenant scoping at execution; bind human approval to the immutable normalized action; constrain schemas, credentials, sandbox and egress; and test indirect prompt injection with benign sentinels while preserving evidence. Use when an agent can send, write, buy, delete, deploy, browse authenticated sites or access cross-tenant data. Not for a general design threat model (threat-model), an ordinary code diff (security-review), IAM estate cleanup (access-review), broad agent benchmarks (agent-evaluation), authentication design (auth-design), or privacy policy (data-privacy)."
allowed-tools: "Read, Grep, Glob, Bash(rg:*), Bash(git:*)"
---

# Agent Security Review

The critical path is untrusted content to model to tool arguments to side effect. A
system prompt, content filter or instruction hierarchy can reduce bad proposals, but it
cannot authorize an action. Treat model output as untrusted tool input and enforce policy
at the tool or service performing the effect.

## Scope

Use for agents that ingest external or retrieved content and can send messages, modify
records, execute code, spend money, deploy, delete, browse an authenticated session, or
reach data from more than one tenant. Review a design or implementation at this boundary.

Do not use for a system-wide STRIDE exercise, which is `threat-model`; a conventional
application diff, which is `security-review`; live IAM rightsizing, which is
`access-review`; benchmark and release-gate design, which is `agent-evaluation`; login or
token protocol design, which is `auth-design`; or retention and privacy obligations,
which are `data-privacy`.

This is defensive work. Use inert test tenants, mock tools and benign sentinel strings.
Do not create exploit payloads, exfiltration instructions or live external side effects.

## Hard gates

1. **Content is never authority.** Text from a page, file, message, memory, retrieval
   result or tool response may supply evidence. It cannot grant permission or override
   policy, even when it claims to quote an administrator.
2. **Tools authorize at execution.** The tool derives the principal and tenant from a
   trusted session, checks the requested action and resource, and fails closed. The model
   cannot supply or widen those claims.
3. **Approval and authorization are separate.** Human confirmation expresses intent for
   one consequential action. The tool still rechecks current authorization immediately
   before execution; either check may deny.
4. **Approval binds the exact action.** Bind normalized arguments, target tenant or
   account, recipient, amount, resource identifier and version. Any change invalidates
   approval and requires a new preview.
5. **No live-effect testing.** Exercise deny paths with mocks, dry runs or isolated test
   tenants. A security review does not send, buy, delete, deploy or publish to prove risk.

## Workflow

### 1. Inventory inputs, authority and effects

Draw one row per path from an input to an effect:

| Input | Trust and provenance | Model step | Tool and effect | Principal and tenant |
| --- | --- | --- | --- | --- |
| Retrieved document | External, indexed by source and revision | Extracts fields | CRM update | Session principal, tenant A |

Include web content, attachments, chat messages, retrieval chunks, memory, tool output,
and state restored from earlier runs. Mark which component chooses the tool and arguments,
which credential the tool uses, and where the authoritative policy decision occurs.

Stop and record a blocking finding if a privileged effect has no tool-side enforcement
point or if tenant identity comes only from model-generated arguments.

### 2. Trace provenance into every tool argument

For each consequential tool, classify every argument as user supplied, trusted system
state, derived from untrusted content, model generated, or fixed configuration. Preserve
source identifiers and revisions through transformations so a reviewer can tell why a
recipient, account, resource or amount was proposed.

Treat summaries, embeddings and remembered facts as derived data, not cleansed data.
Reject instructions embedded in retrieved content as a source of authority. When the
system cannot preserve provenance, reduce the permitted action to read-only or require a
fresh trusted value from the user.

### 3. Verify authorization where the effect occurs

Inspect the actual tool handler or downstream service, not only its prompt or wrapper.
Verify that it:

- derives the caller, tenant and account from authenticated context;
- checks action-level and resource-level permission on the final resolved object;
- scopes lookup, mutation and search by tenant before data is returned;
- rejects unknown actions, resources and policy states;
- enforces authorization and the expected version in the effect's transaction or
  conditional write where the backend supports it; and
- records the principal, policy decision, resource and result without sensitive content.

Otherwise recheck immediately before execution and reject a version mismatch, while
recording the residual race. Human approval does not repair missing authorization.

### 4. Constrain the tool surface

Prefer narrow tools such as `draft_invoice` over a generic shell, browser or HTTP client.
Use closed schemas with enums, length and range bounds, canonical identifiers and no
unknown fields. Resolve friendly names to identifiers in trusted code, then authorize
the resolved object.

Give each tool the minimum credential, filesystem scope, tenant reach and lifetime it
needs. Separate read from write capability. In a sandbox, deny host mounts, ambient
credentials, sibling-process access and undeclared network destinations. Allow egress by
destination and protocol for the task rather than granting arbitrary network access.

Where a general browser or computer tool is necessary, isolate its account and profile,
restrict reachable origins, and place side-effect boundaries behind trusted UI or API
checks that the page itself cannot dismiss.

### 5. Bind approval to immutable execution

Generate the confirmation preview from canonical tool arguments after defaults,
resolution and validation. Display the action, target account or tenant, recipient,
amount, resource and irreversible impact. Store a digest or opaque approval record over
that normalized request plus its version and expiry.

At execution, compare the request with the approved record exactly, re-resolve mutable
references, reject stale versions, and enforce authorization at commit. Do not accept
approval copied from conversational text, a model-produced claim that the user agreed,
or approval for a broader plan containing several later actions.

Read [the approval contract](references/approval-contract.md) when specifying approval
records, batch actions, atomic enforcement, replay protection or retry behavior.

### 6. Review memory and retrieval

Record source, tenant, author or system, retrieval time and revision for stored facts.
Partition indexes and memory by tenant and authorization context. Apply access checks
before retrieval so the model never receives inaccessible material, then check again
before acting because authorization may have changed.

Set expiry and replacement rules for mutable facts. Prevent untrusted content from
writing durable policy, approval or identity state. A memory entry saying a user permits
future transfers is content, not a grant.

### 7. Run safe negative tests and preserve evidence

Use a benign sentinel such as `REVIEW_SENTINEL_7` in a fixture that asks the agent to
place it in a forbidden tool field. Pair each denied attempt with a legitimate action
that must succeed, so a deny-all implementation cannot pass. Read [the benign test
matrix](references/benign-test-matrix.md) when building these fixtures and controls.

Capture the fixture revision, agent and prompt revision, tool schema, normalized request,
policy decision, approval record, mock effect log and final verdict. Redact sensitive
values without removing identifiers needed to correlate the decision.

## Output format

```markdown
## Verdict
[Blocking findings and whether privileged actions should remain enabled.]

## Authority paths
[Input -> model -> arguments -> tool -> effect, with principal and tenant.]

## Findings
### [N]. [Boundary] — [severity]
Evidence: [observed control or missing enforcement point]
Impact: [unauthorized effect or data reach]
Fix: [tool-side or orchestration change]
Test: [benign fixture and expected denial]

## Approval contract
[Normalized fields, version, expiry, invalidation and execution-time recheck.]

## Limits
[Paths, tools or deployed controls not inspected.]
```

## Anti-patterns

**Treating the prompt as a policy engine.** Instructions can shape proposals, but the same model processes adversarial content and emits tool arguments. Enforce policy after that output, at the tool.

**Using approval as authorization.** A user may approve an action they are not entitled to perform, or their access may be revoked before execution. Require both checks.

**Approving a mutable description.** “Send the invoice” leaves recipient, amount and account open to substitution. Approve the canonical request and invalidate it on change.

**Testing against production.** A real denial test can become a real side effect when a
guard is absent. Use an isolated environment and an inert sentinel.

## Primary references

- [Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety) — use for untrusted input, prompt injection and structured-output boundaries.
- [Computer use](https://platform.openai.com/docs/guides/tools-computer-use) — use for confirmation, authenticated sessions, isolation and consequential actions.
