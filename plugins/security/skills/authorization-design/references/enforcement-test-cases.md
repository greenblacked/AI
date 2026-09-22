# Enforcement and test cases

Use this catalogue after the policy matrix exists. It checks whether policy survives all
execution paths and state changes rather than only the primary object endpoint.

The OWASP Authorization Cheat Sheet recommends validating permissions on every request
and creating unit and integration tests for authorization logic:
[OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## Enforcement map

| Path | Required check | Common leak |
| --- | --- | --- |
| Object read | Principal, tenant, relationship, state | Identifier guessing reveals another owner |
| List/search | Constrain query to allowed rows | Unauthorized rows, totals or facets leak |
| Count | Apply identical scope to aggregation | Count reveals existence despite hidden rows |
| Bulk mutation | Check every item; define atomicity | One authorized item carries unauthorized ones |
| Export/report | Reapply row and field policy | Hidden fields reappear in CSV or PDF |
| Subscription | Check subscribe and each delivery as needed | Access revoked after channel opens |
| Background job | Recheck current authority at execution | Revoked requester retains delayed effect |
| Generated file | Authorize retrieval and expire capability | Stable URL bypasses source-object policy |

## Minimum test matrix

For each allowed action, test:

1. intended principal, tenant, resource state and relationship succeeds;
2. unauthenticated access follows the matrix: an explicit public grant succeeds and all
   other unresolved principals are denied;
3. an explicit cross-tenant share or delegated resource grant succeeds only for its
   resource and actions; an unrelated tenant principal is denied;
4. same-tenant principal with the wrong owner or relationship is denied according to the
   matrix's reveal-or-conceal policy;
5. lower role, missing attribute and invalid resource state are denied;
6. unknown action and unknown resource type are denied;
7. revoked membership invalidates a warm positive cache entry within the stated bound;
8. a new grant invalidates or ages out a negative decision within the stated bound;
9. policy service or attribute-source failure follows the operation's documented behavior;
10. decision logs contain reason and policy version without sensitive contents.

Cross a time or assurance deadline while policy generation stays unchanged and prove the
cached grant expires by the promised deadline, including clock uncertainty.

## Collection and bulk cases

Seed allowed and forbidden objects that sort adjacent to one another. Assert returned
rows, total counts, cursors, facets and timing-visible branches do not disclose forbidden
objects. Search on a unique value from a forbidden object. Mix tenants and owners in one
bulk request and verify the documented all-or-nothing or per-item result.

## Delayed and concurrent cases

Enqueue while allowed, revoke before execution, and assert the effect does not occur.
Enqueue against version one, mutate the protected fields or tenant before execution, and
assert the version guard stops stale approval. Disable the requester and expire an
approval before retries. Where decision and write cannot be atomic, measure the residual
window and exercise the compensating check.

## Cache and rollout cases

Calculate revocation latency end to end: upstream policy or attribute replication, cached
snapshot age, worker or stream recheck interval, in-flight delivery and clock uncertainty.
A 30-second cache plus a 30-second poll cannot support a 30-second promise. Anchor
freshness to an authoritative snapshot version and its original observation time; a stale
refill must not reset the freshness clock.

Warm a decision under policy generation one, promote generation two, and prove the old
entry cannot grant. Simulate delayed invalidation and policy-service unavailability.
During shadow evaluation, assert existing enforcement remains authoritative. Exercise a
rollback after an emergency revoke and prove rollback does not restore the revoked grant.

Monitor shadow differences in both directions: newly denied cases find compatibility
breaks; newly allowed cases find privilege expansion. Require explanations for both before
promotion.
