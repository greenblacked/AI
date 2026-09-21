# Policy matrix guide

Use this worksheet to turn product behavior into reviewable authorization rules. The
approach follows the OWASP Authorization Cheat Sheet's deny-by-default, every-request and
unit/integration-testing guidance, and NIST SP 800-162's definition of attribute-based
access control.

Sources:

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [NIST SP 800-162, Guide to Attribute Based Access Control](https://csrc.nist.gov/pubs/sp/800/162/upd2/final)

## Inventory worksheet

| Principal | Resource | Action | Tenant boundary | Required relationship or attributes | Visibility on deny |
| --- | --- | --- | --- | --- | --- |
| Member | Project | Read | Same tenant | Active membership | Conceal private project |
| Owner | Project | Delete | Same tenant | Owner and project not locked | Reveal with denial |
| Billing service | Invoice | Export | Same tenant | Workload identity and export purpose | Audit-only detail |

Replace examples with product nouns. Split read, list, count and export because their data
shapes and leak risks differ. Split create from edit because create has no existing owner
yet. Split approve from edit when separation of duties matters.

## Model selection questions

Choose RBAC when stable job functions account for most decisions and exceptions remain
rare. Choose ABAC when current subject, resource or environmental attributes materially
change the result. Choose ReBAC when ownership, sharing, group membership, hierarchy or
delegation is the product model. A hybrid is justified when each part answers a different
question; document that division.

For every attribute or relationship, name:

- its authoritative store and owner;
- who can change it and through which authorized action;
- its update and propagation latency;
- its policy meaning, allowed values and missing-value behavior;
- its generation or version for cache invalidation.

## Rule worksheet

Write each rule as a complete decision:

```text
principal kind + action + resource kind
ALLOW only when tenant, relationship, state and environmental conditions all hold
otherwise DENY; denied requests use the named visibility policy
```

Then record precedence. Deny-overrides is easy to explain, but an emergency deny may need
to sit outside ordinary policy versions so rollback cannot remove it. If an exception
overrides a deny, identify the exact exception and expiry rather than depending on file or
rule order.

## Review questions

- Does every allowed row name a business reason and owner?
- Are tenant and ownership facts loaded from authoritative data?
- Are collection queries constrained before totals and rows are produced?
- Can a principal change an attribute used to authorize itself?
- Do delegation and impersonation retain both authenticated and effective identities?
- Is missing data denied, or covered by a narrower independently verifiable public rule?
- Is existence concealed or revealed consistently across read, list and timing behavior?
- Are resource state transitions protected as actions, rather than inferred from edit?
