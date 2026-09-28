---
name: schema-design
description: "Design the tables for a new feature before any migration exists: write the queries the schema must serve first, with expected cardinalities, then choose keys, constraints and types that are expensive to reverse later — tenancy in every unique key, a foreign-key index on every referencing column, timestamptz over timestamp, integer minor units over float for money, and a considered default on soft delete. Use whenever someone asks how to model these tables, whether to use a UUID or a bigint key, whether to soft-delete, or how to represent a many-to-many relationship, before a single CREATE TABLE is written. Not for shipping a change to a schema that already exists in production (db-migration), tuning a slow query after the fact (sql-performance), or designing the HTTP or RPC interface in front of the tables (api-design)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(psql:*), Bash(mysql:*)
---

# Schema Design

A schema is finished when every query it has to serve is named and measured against it, every constraint that can be pushed into the database has been, and every type decision was made on purpose rather than inherited from an ORM default.

The job is hard because the mistakes are the ones nobody notices until the table is full. A primary-key choice that felt like a coin flip on day one becomes the column every foreign key in the system points at, and changing it later means rewriting every one of them under load. A missing index on a foreign-key column is invisible until the table storing the child grows past what fits in cache, at which point every delete on the parent does a sequential scan of the child to check for orphans. A soft-delete column added without its matching unique index lets someone "delete" a row and then collide with it the moment a new one is created with the same natural key. None of these show up in review of the DDL; they show up months later, in production, as an incident that traces back to one line nobody thought was a decision.

## Scope

Use for: modelling the tables for a new feature or service before any migration ships — choosing primary keys, foreign keys, constraints, types, and whether a table is ever soft-deleted; deciding between a join table and a native array or JSON column for a many-to-many relationship; sizing indexes against the queries that will actually run.

Do not use for: changing a schema that already exists in production, which needs a release sequence, not a design decision — that is `db-migration`. Tuning a query against an existing table, which is `sql-performance`; decide the index here, tune the plan there. Designing the API surface callers see, which is `api-design` — model the tables from the tasks first, but the endpoints and the tables are two different artefacts. Choosing a database engine, ORM or framework, which this skill assumes is already settled.

## Hard gates

1. No `CREATE TABLE` before the query list exists. A schema designed before anyone wrote down what it has to answer is a guess with a name.
2. Every foreign-key column carries an index on that column, verified against the live schema rather than assumed from either engine's reputation.
3. Soft delete is a whole-table decision, never a column added quietly to one migration: it comes with a partial unique index on every column that was previously unique, and a purge policy with a named owner.
4. Every type in the table below is chosen once, deliberately, and written down — never left to the ORM's default.

## Workflow

### 1. Write the query list before any DDL

List every read and write path the schema has to serve, in plain language, with its expected cardinality and access shape: a point lookup by id, a range scan by time, an aggregate over a tenant. Name which table or tables each query touches.

This list is what step 6 tests against, and it is what makes step 2's key choice a decision rather than a habit. A schema with no query list is a set of nouns with no evidence anyone thought about how they get read.

### 2. Choose the primary-key strategy once, per table

Default to a `bigint` identity column. It is the smallest thing that sorts and indexes well, and every join against it is a plain integer comparison.

Reach for a different strategy only when the query list from step 1 actually needs it: a client-generated identifier because the row can be created offline, or a key that has to merge cleanly across systems that do not share a sequence. When one of those applies, use a scheme that sorts close to insertion order rather than a fully random one — a fully random primary key scatters every insert across the whole index, which is expensive on a b-tree and thrashes the buffer cache once the table is larger than memory. Verify the exact generator your database version actually offers before committing to a function name; this is the kind of detail that changes between releases, and a schema is a bad place to have guessed at it.

Whatever is chosen, write it down as the table's one key strategy. "Decide at write time" is not a decision, it is next month's inconsistency.

### 3. Push constraints into the database

Constraints in the application are advice; constraints in the schema are guarantees. For every table:

- `NOT NULL` by default. A nullable column is a decision, not the absence of one.
- `CHECK` for a value range you already know, so a bad row cannot exist even briefly.
- `UNIQUE` for real uniqueness, including the tenant column in every unique index that must be scoped per tenant, so a write that forgets the `WHERE` clause still cannot collide two tenants on the same value. That constraint is write-side only — it is not read isolation, which needs its own boundary; see `references/tenancy-and-soft-delete.md`.
- A foreign key for every reference, and an index on that same column. Look up an index on that column directly against the live schema (`\d+ <table>` in Postgres, `SHOW CREATE TABLE` or the information schema in MySQL) rather than assuming either engine adds one for you — a foreign key without a matching index turns every delete on the parent, or update of the referenced key, into a full scan of the child while it checks for dependents.

### 4. Decide soft delete once, for the whole table

Pick hard delete by default. Reach for soft delete only when retention, undo or an audit trail genuinely requires it, and then apply it to the whole table rather than one feature's rows within it.

A soft-deleted table needs a `deleted_at` timestamp, a partial unique index on every column that used to be unique — `UNIQUE (email) WHERE deleted_at IS NULL`, not a plain unique index that now blocks the next signup with the same address — and a purge policy with a stated retention period and a named owner. A soft-delete column with no partial index is a promise the schema does not keep: the "same" logical row collides with itself the first time someone deletes and recreates it.

### 5. Make every type decision on purpose

| Value | Default | Why |
| --- | --- | --- |
| A point in time | A timezone-aware timestamp type, never a naive one | A naive timestamp is only correct for readers in one timezone, and the bug is invisible until a second one exists |
| Money | An integer count of the minor unit, or a fixed-point numeric type | A float rounds, and the error compounds with every transaction until an audit finds it |
| A value that may need to be retired without a migration | A lookup table with a foreign key | Removing a value from a native enum type is a schema change on some engines and unavailable on others; a lookup table is a row deletion |
| Free text with no real business bound | A plain unbounded text type | An arbitrary length cap that is not a business rule is a future migration waiting to happen |

Read `references/type-defaults.md` before finalising a type for money, a timestamp, an identifier or an enumerable value — it has the full table, what each default protects against, and what to verify against the target engine's current documentation before relying on a specific function or feature name.

### 6. Prove the schema against the query list

Populate each table at a volume that resembles production, then run every query from step 1 through `EXPLAIN` on the target engine and read the plan. A sequential scan over a table sized for production is not deferred to "add an index later" — either add the index now, while the cost of being wrong is a design conversation, or write down explicitly why the scan is acceptable at the sizes this table will reach.

### 7. Hand off

Once the schema is agreed and nothing has shipped yet, hand the DDL to `db-migration` for the actual release sequencing against a live database. Hand any query from step 6 that still needs work beyond an index — a rewrite, a materialised view, a cache — to `sql-performance`. Hand the interface callers will actually see to `api-design`; the tables and the endpoints are designed from the same task list but are not the same artefact.

## Multi-tenancy and soft delete together

The two interact in a way that is easy to miss: a partial unique index that scopes on `deleted_at IS NULL` also has to include the tenant column, or one tenant's soft-deleted row can block another tenant's insert. Read `references/tenancy-and-soft-delete.md` when the schema is both multi-tenant and soft-deleted — it works through the combined index and a purge-policy template.

## Anti-patterns

**Choosing the primary key by convention instead of by access pattern.** A team default of "always UUID" or "always identity" avoids a decision in the design meeting and creates one in production, when insert locality or a cross-system merge turns out to matter and the key type cannot change without rewriting every foreign key pointing at it.

**A soft-delete column with no partial unique index.** The schema looks complete and passes every test until someone actually deletes and recreates a row, at which point the "unique" constraint collides with a row that was supposed to be gone.

**Trusting the ORM's default type for money or time.** A float column for a price is a rounding bug waiting for enough transactions to surface it. A naive timestamp is a bug waiting for a user, or a deploy, in a second timezone.

**Skipping step 6 because the table is empty in development.** A schema that looks fine against a thousand rows says nothing about the plan it will produce at ten million; the sequential scan that is instant today is the on-call page next year.

## Output format

Report a schema design in this shape, one section per table:

```markdown
## Queries
[Every read and write path, cardinality, access shape, which table(s) it touches.]

## DDL
[The CREATE TABLE statement, with every constraint inline.]

## Key strategy
[What was chosen, and why — never "decide later".]

## Type decisions
[One line per non-default type choice, naming what it protects against.]

## EXPLAIN results
[Each query from step 1 against production-sized data, and the verdict.]

## Handoff
[What goes to db-migration, what goes to sql-performance, what goes to api-design.]
```

## Reference files

- `references/type-defaults.md` — read when choosing a concrete type for money, a point in time, an identifier or a value that might be retired: the full table of defaults, what each protects against, and what to verify against the target engine's current documentation before relying on a specific function or feature name.
- `references/tenancy-and-soft-delete.md` — read when the schema is multi-tenant, soft-deleted, or both: the combined partial-unique-index pattern, a purge-policy template, and why a uniqueness constraint closes the write side of tenant isolation but is not read isolation on its own.
