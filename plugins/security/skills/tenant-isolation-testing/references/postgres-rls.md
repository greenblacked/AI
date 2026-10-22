# Postgres row-level security checks

Read this when the tenant boundary uses row-level security, or when someone says "we use RLS, is that enough". These are test and audit queries for a non-production environment.

## What bypasses a policy

- The table owner, unless the table is altered with `FORCE ROW LEVEL SECURITY`.
- Superusers.
- Any role with the `BYPASSRLS` attribute.
- Views created by an owner and read by others run with the owner's rights unless defined with `security_invoker` (PostgreSQL 15 and later); check how your version treats them.

Policies are also silently absent when row security is not enabled on the table at all.

## Audit the catalogue

```sql
-- every table, whether RLS is on and forced, and who owns it
SELECT n.nspname, c.relname, c.relrowsecurity AS rls_enabled,
       c.relforcerowsecurity AS rls_forced, pg_get_userbyid(c.relowner) AS owner
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p') AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY 1, 2;

-- roles that can skip policies
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles
WHERE rolsuper OR rolbypassrls;

-- the policies themselves
SELECT schemaname, tablename, policyname, cmd, qual, with_check
FROM pg_policies ORDER BY 1, 2, 3;
```

A tenant-scoped table with `rls_enabled` false, or with the application role as owner and `rls_forced` false, is a finding without running any request. Check that the application role is not in the second query.

## Safe tenant setting

Set the tenant inside the transaction so it cannot outlive it:

```sql
BEGIN;
SELECT set_config('app.tenant_id', $1, true);   -- true = local to this transaction
-- queries
COMMIT;
```

`SET LOCAL app.tenant_id = '...'` has the same scope. A plain `SET` or `set_config(..., false)` lasts for the session and survives into the next borrower of a pooled connection.

## Policy that denies when unset

```sql
CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
```

`current_setting(name, true)` returns NULL if the setting never existed on this connection, and an empty string if it was set earlier and reset, so the `NULLIF` makes both cases NULL; comparing to NULL matches no rows. Without it, the empty string fails the cast with an error, which tempts someone to add a fallback that matches every row; a NULL that matches nothing is the safe default.

## Test cases

1. Connect as the application role. `SELECT count(*) FROM orders` with no tenant set returns 0.
2. Set tenant A, read B's known id: zero rows. Insert a row with B's `tenant_id`: rejected by `WITH CHECK`.
3. On one pooled connection run request A then request B; B must not see A's rows and must not inherit A's setting.
4. Run the same read as the owner role and confirm whether it bypasses; the answer must match `relforcerowsecurity`.
5. Run a migration or job role and confirm that if it bypasses policy on purpose, the job code scopes by tenant explicitly and has its own case.
