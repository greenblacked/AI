---
name: authorization-design
description: "Design or review application authorization: who may perform which action on which resource, in which tenant and under what conditions. Use when defining RBAC, ABAC or ReBAC; building a permission matrix or policy engine; preventing IDOR/BOLA and cross-tenant access; placing server-side checks on routes, jobs, lists, exports and bulk operations; handling authorization caches, revocation latency, visibility, rollout or policy tests; or asking whether a user may read, edit, approve or administer an object. Not for proving identity or session safety (auth-design), cleaning up existing IAM grants (access-review), reviewing an ordinary code diff (security-review), agent tool approvals (agent-security-review), HTTP response shape (api-design), or generic cache architecture (application-caching)."
allowed-tools: "Read, Grep, Glob, Write, Edit"
---

# Authorization Design

A sound authorization design makes every protected operation answer the same explicit
question from trusted context, denies anything outside the policy, and changes access
without leaving stale decisions behind.

Authorization failures hide in paths that look secondary: list filters, exports,
background jobs, object identifiers and cached decisions. A correct role diagram is not
enough if one route trusts a tenant from the request body or a worker executes yesterday's
permission. Treat policy, enforcement, freshness and evidence as one design.

## Scope

Use for: application permissions, tenant isolation, ownership checks, RBAC, ABAC, ReBAC,
policy matrices, policy engines, object visibility, IDOR or BOLA prevention, enforcement
placement, authorization decision caching, revocation behavior, rollout and tests.

Do not use for: establishing identity, login, tokens or sessions, which is `auth-design`;
inventorying and reducing grants already held in IAM or cloud estates, which is
`access-review`; reviewing an ordinary change, which is `security-review`; approving
agent tool actions, which is `agent-security-review`; choosing HTTP status codes, which
is `api-design`; or designing a general-purpose cache, which is `application-caching`.

## Hard gates

1. **Default deny.** An absent rule, unknown action, missing attribute or policy error
   produces no grant. Define degraded behavior per operation; there is no universal
   authorization fail-open mode.
2. **Trusted subject and scope context.** Derive the principal from verified server-side
   authentication context. Resolve effective identity and applicable tenant, public,
   collaboration or delegated scope on the server; never accept them as authoritative
   merely because the client supplied them.
3. **Server-side enforcement on every path.** UI hiding is useful presentation, not a
   control. Check direct reads, mutations, lists, searches, counts, bulk actions, exports,
   subscriptions and background work.
4. **Resource facts are verified.** Load ownership, tenant, state and relevant attributes
   from an authoritative source. Do not compare two attacker-controlled arguments and
   call the result authorization.
5. **Execution uses current authority.** Recheck at execution time for queued, approved or
   delayed work. Bind the decision to the resource version and mutation atomically where
   practical; record any residual time-of-check/time-of-use window.

## Workflow

### 1. Inventory the decision vocabulary

List principals, resources, actions, tenants and environmental conditions before naming
roles. Use product verbs and resource boundaries rather than controller names.

| Dimension | Questions to answer |
| --- | --- |
| Principal | Human, service, delegated actor or support impersonator? Which identity is effective? |
| Resource | What object or collection is protected? Who owns it? Which tenant contains it? |
| Action | Read, list, create, edit, delete, approve, share, export or administer? |
| Relationship | Owner, member, manager, parent, collaborator or delegated agent? |
| Condition | Resource state, assurance level, time, network, purpose or approval present? |

Include collection operations explicitly. “Read invoice” does not automatically define
whether a caller may list invoices, see a count, search by customer or export a CSV.

### 2. Choose the policy model from actual variation

Use the smallest model that expresses the decisions without duplicating policy in code.

| Need | Starting model | Warning signal |
| --- | --- | --- |
| Stable job functions with common permissions | RBAC | A new role appears for every exception or tenant |
| Decisions depend on subject, resource or environment facts | ABAC | Attributes have unclear owners or stale update paths |
| Sharing, hierarchy, ownership or delegation dominates | ReBAC | Relationship traversal has no depth or cycle boundary |
| Several of these are real | Deliberate hybrid | The same rule is implemented independently in each model |

Do not pick a model because it is fashionable. State which requirement each mechanism
serves and which component owns the source attributes or relationships.

### 3. Write the default-deny policy matrix

Create one row per meaningful principal or condition, resource and action. Start with
deny, then add narrow grants and named constraints. Use
`references/policy-matrix.md` when drafting or reviewing the matrix.

For every grant, record:

- trusted inputs and their authoritative source;
- tenant and ownership constraint;
- resource states in which the action is valid;
- whether the action is delegable and who may delegate it;
- visibility when denied: reveal existence, conceal it, or return a filtered collection;
- policy owner and the reason the grant exists.

Make precedence explicit. If denies override grants, say so. If a specific grant can
override a broad deny, name the narrow exception rather than relying on rule order.

### 4. Establish the authorization context

Build a server-side context from verified identity and current application data. It
should distinguish the authenticated principal, effective principal during delegation or
impersonation, tenant memberships, assurance level and policy generation.

Resolve tenant from the protected resource or a server-owned routing boundary, then
verify an applicable grant: tenant membership, an explicit public rule, cross-tenant
collaboration or resource-scoped delegation. A tenant ID in a path, header, token custom
claim or request body is a lookup hint until the server validates it.

Load resource ownership and state by an identifier scoped to the validated tenant. A
query shaped as `tenant = validated_target_tenant AND id = requested_id` excludes
objects outside the validated target tenant before finer policy runs.

### 5. Put enforcement at every entry point

Centralize the decision function, but keep calls visible near each operation. Pass the
principal, action, resource facts and context; avoid helpers such as `isAdmin()` that
silently acquire unrelated meanings.

Cover each path:

- single-object reads and writes;
- list, search and count queries, with authorization expressed in the query or a safe
  post-filter that cannot leak totals, ordering or timing-sensitive presence;
- bulk endpoints, checking every target and defining whether failure is atomic;
- exports and reports, including fields hidden in normal views;
- event subscriptions, webhooks and real-time channels;
- background jobs, retries, scheduled work and administrative consoles;
- indirect access through parent resources, shared links or generated files.

Do not authorize a collection request and assume every returned row is allowed. Do not
fetch an unscoped object, expose whether it exists, and only then reject it.

### 6. Define visibility and failure behavior

Choose an existence policy for each resource class. Concealing existence may require a
not-found response and indistinguishable caller-visible body and latency. Internal audit
records retain the real decision and reason without exposing it to the caller. Revealing
existence can be correct for public identifiers or workflows where requesting access is a
feature. Apply the decision consistently; status-code shape itself belongs to `api-design`.

For unavailable policy services or missing attributes, define the safe result per action.
A public read may have an independently verifiable public rule; an administrative write
normally denies. Document operational recovery rather than inventing a universal fail-open.

### 7. Bind decision and execution

For synchronous mutations, evaluate against current permissions and resource state in the
same transaction or concurrency boundary as the write where possible. Use a resource
version or compare-and-swap condition so an approved draft cannot become a different
object before execution.

For queues and approval workflows, treat enqueue-time authorization as admission only.
At execution, reload the principal's current authority, tenant membership, resource state
and version. Decide what happens if the requester was disabled, access was revoked, the
resource moved tenant or approval expired.

Record both the acting service and the on-behalf-of principal and scope. Revalidate that
delegated authority at execution according to an explicit delegation contract; a worker's
own broad service role must not replace the requester's current authorization.

Where atomicity is impossible, name the residual TOCTOU window, its maximum duration and
the compensating control. “Checked earlier” is not a control.

When policy attributes and business data live in different systems, do not promise a
database transaction can make them atomic. Establish and test a consistency and
revocation bound, or reject the operation when the required version cannot be verified.

### 8. Cache decisions without defeating revocation

Cache only after defining the freshness contract. Include authenticated and effective
principals as policy requires, effective scope, action, resource identity and its
policy-relevant version, policy generation, every dynamic policy input and any
valid-until time in the key. A time-to-live alone does not express revocation.
Expire or re-evaluate no later than the earliest condition deadline, assurance expiry or
freshness deadline, including clock uncertainty; putting the deadline in a key does not
enforce it.

On policy, membership or relationship changes, increment generations or invalidate the
specific decisions. Discover current generations through a proven current read or an
explicit bounded-freshness fence; storing one only in an evictable decision value is not
invalidation. Prevent stale refills from reviving an old grant. State maximum revocation
latency and failure behavior. Negative decisions need a freshness contract too.

Keep generic eviction, capacity and topology work in `application-caching`; this step owns
only authorization correctness and invalidation semantics.

### 9. Test the policy and every enforcement path

Build tests from `references/enforcement-test-cases.md`. Each grant needs a positive case;
each boundary needs negative cases for another owner, another tenant, a lower role,
missing attributes, wrong resource state and revoked access.

Test lists, counts, searches, bulk operations, exports and jobs independently. Include
identifier guessing, mixed-tenant bulk input, stale cache entries, permission changes
between enqueue and execution, and concurrent resource updates.

Record structured decisions with principal, effective principal, tenant, action, resource
type and identifier, outcome, policy version and reason code. Protect the audit trail from
unauthorized reading and avoid copying sensitive resource contents into it.

### 10. Roll out policy changes safely

Run the candidate policy in shadow evaluation while existing enforcement remains active.
Compare decisions, investigate both newly denied and newly allowed cases, and avoid
returning shadow outcomes to callers if doing so changes behavior or leaks policy detail.

Promote by policy version with a tested rollback. Rollback must not regrant access that
was explicitly revoked after the prior version; preserve revocation or emergency-deny
state outside the version being rolled back. Monitor denials, grants on sensitive actions,
policy errors and decision latency after promotion.

## Output format

Produce:

1. the principal/resource/action/tenant inventory;
2. the chosen policy model and why it fits;
3. a default-deny matrix with visibility and precedence;
4. an enforcement map covering synchronous, collection and asynchronous paths;
5. freshness, revocation and failure behavior;
6. positive and negative test cases;
7. rollout, audit and rollback conditions;
8. unresolved TOCTOU windows or assumptions with an owner.

## Anti-patterns

**Role names before decisions.** Starting with `admin`, `editor` and `viewer` hides the
resource and tenant boundaries. Inventory decisions first, then compress stable groups
into roles.

**Client-provided ownership.** Comparing `request.user_id` with `request.owner_id` proves
only that the caller can repeat a value. Load both identity and ownership from trusted
sources.

**One middleware check for a whole router.** A route-level role check misses object state,
ownership and sub-actions, then future endpoints inherit a grant their authors never saw.

**Authorize at enqueue time only.** Delayed work executes after revocation or against a
changed resource. Recheck current authority and version when the effect occurs.

**Cache until TTL.** A five-minute cache creates a five-minute revocation promise whether
or not anyone agreed to it. Key by generations and define failure behavior.

**Shadow mode replacing enforcement.** A candidate policy is evidence, not protection.
Keep existing enforcement active until the candidate is understood and promoted.

## Reference files

- `references/policy-matrix.md` — read when inventorying decisions, selecting RBAC, ABAC
  or ReBAC, and drafting the default-deny matrix with precedence and visibility.
- `references/enforcement-test-cases.md` — read when mapping enforcement points, testing
  tenant and ownership boundaries, or planning shadow rollout, cache invalidation and
  execution-time checks.
