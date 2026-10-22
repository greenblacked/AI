# Index pruning queries

Read this when you need the full candidate, duplicate, invalid or foreign-key queries, or the MySQL equivalents.

## Unused, with constraint and foreign-key flags (PostgreSQL)

```sql
SELECT s.schemaname, s.relname, s.indexrelname, s.idx_scan,
       pg_relation_size(s.indexrelid) AS bytes,
       i.indisunique, i.indisprimary,
       EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = s.indexrelid) AS backs_constraint
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0
ORDER BY bytes DESC;
```

## Foreign keys with no covering index on the referencing columns

```sql
SELECT c.conrelid::regclass AS child, c.conname, c.conkey
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
      AND (i.indkey::int2[])[0:array_length(c.conkey, 1) - 1] @> c.conkey
  );
```

An index counts as covering when its leading columns include the foreign key columns.

## Exact duplicates

```sql
SELECT indrelid::regclass AS tbl, array_agg(indexrelid::regclass) AS dupes
FROM pg_index
GROUP BY indrelid, indkey, indclass, indcollation, indoption,
         coalesce(pg_get_expr(indpred, indrelid), ''),
         coalesce(pg_get_expr(indexprs, indrelid), '')
HAVING count(*) > 1;
```

For prefix redundancy, compare `indkey` arrays by hand: a candidate is an index whose column list is a leading prefix of another on the same table, with the same predicate and opclasses, and which is not unique.

## Invalid indexes

```sql
SELECT indexrelid::regclass, indrelid::regclass, indisvalid, indisready
FROM pg_index WHERE NOT indisvalid;
```

## Summing across nodes

Export `schemaname, relname, indexrelname, idx_scan` from each node to a table or file and sum by the first three columns. An index absent from a replica's output (not yet created there) counts as zero for that node.

## MySQL 8

```sql
SELECT * FROM sys.schema_unused_indexes;
SELECT * FROM sys.schema_redundant_indexes;
ALTER TABLE t ALTER INDEX idx_name INVISIBLE;
```

The first reads `performance_schema` index usage, which resets on restart: check `SHOW GLOBAL STATUS LIKE 'Uptime'` against the business cycle. An invisible index is still maintained on writes, so the saving arrives only at the drop.
