# Tenancy and soft delete

Read this when the schema is multi-tenant, soft-deleted, or both — the two interact in a way that is easy to design correctly for one and get wrong the moment the other is added.

## Contents

- [Isolation as a constraint](#isolation-as-a-constraint)
- [The partial-unique-index pattern](#the-partial-unique-index-pattern)
- [Combining tenancy and soft delete](#combining-tenancy-and-soft-delete)
- [A purge-policy template](#a-purge-policy-template)

## Isolation as a constraint

A `WHERE tenant_id = ?` clause that every query is supposed to include is a convention, and a convention is exactly as reliable as the discipline of everyone who ever writes a query against the table. Putting the tenant column into the schema's own constraints closes the write side of that gap: a bug that forgets the clause on an insert or update cannot collide two tenants' rows on the same unique value, because the constraint spans `tenant_id` too. It does nothing for the read side — a `SELECT` that forgets the same clause still returns every tenant's rows, constraint or no constraint, because a unique or foreign-key constraint has no opinion about what a query is allowed to return. Read isolation needs an actual read boundary: PostgreSQL row-level security, a tenant-scoped view, or enforcement verified in the data-access layer that no query path can bypass — named specifically to what the engine in use actually supports, not asserted as a byproduct of the schema's write-side constraints.

Concretely: every column that must be unique per tenant gets a composite unique constraint that includes `tenant_id`, not a bare unique constraint on the business column alone. `UNIQUE (tenant_id, email)`, not `UNIQUE (email)` — the second makes email globally unique across every tenant in the system, which is very often not what anyone intended and is the kind of mistake that only shows up once two tenants' users collide.

## The partial-unique-index pattern

A soft-deleted table needs its uniqueness constraints rewritten as partial indexes scoped to live rows, because a plain unique constraint keeps counting a "deleted" row as occupying its value:

```sql
-- Plain unique constraint: blocks a new signup with a previously "deleted" email forever.
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);

-- Partial unique index: only live rows compete for uniqueness.
CREATE UNIQUE INDEX users_email_live_key ON users (email) WHERE deleted_at IS NULL;
```

MySQL has no partial index; the equivalent is a generated column that collapses every soft-deleted row to a single shared placeholder value, with the unique constraint on the generated column instead of the original:

```sql
ALTER TABLE users
  ADD COLUMN email_live VARCHAR(255)
    GENERATED ALWAYS AS (IF(deleted_at IS NULL, email, NULL)) STORED,
  ADD UNIQUE KEY users_email_live_key (email_live);
```

`NULL` in a unique index does not conflict with another `NULL` in either engine, which is exactly the property this pattern relies on: every soft-deleted row's generated column value is indistinguishable from every other, and none of them collide.

## Combining tenancy and soft delete

When both apply, the tenant column belongs inside the partial index alongside the business column, not layered on separately:

```sql
CREATE UNIQUE INDEX users_tenant_email_live_key
  ON users (tenant_id, email)
  WHERE deleted_at IS NULL;
```

Missing the tenant column here reintroduces the cross-tenant collision from the isolation section above, except now only among live rows — a subtler bug, because it passes every test that does not specifically soft-delete a row in one tenant and then create a matching one in another.

## A purge-policy template

A soft-delete column with no stated purge policy accumulates rows forever, which is itself a decision nobody made on purpose. State, for every soft-deleted table:

```markdown
## Purge policy: <table>

Retention period: [how long a soft-deleted row is kept before it is eligible for purge]
Purge mechanism: [a scheduled job, a manual runbook step, a database-native TTL feature]
Owner: [the team or role accountable for the job actually running]
Escalation: [what happens, and who is paged, if the purge job stops running]
```

A retention period with no named owner is not a policy — it is a row count someone will eventually have to explain during an audit or a storage incident.
