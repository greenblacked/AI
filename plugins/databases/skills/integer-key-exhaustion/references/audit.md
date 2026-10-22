# Audit queries

Read this when you need the MySQL audit, the column-type listing for PostgreSQL, or the type maxima.

## Maxima

| Type | Maximum |
| --- | --- |
| MySQL `MEDIUMINT` signed / unsigned | 8,388,607 / 16,777,215 |
| `INT` / PostgreSQL `integer` signed | 2,147,483,647 |
| MySQL `INT UNSIGNED` | 4,294,967,295 |
| `BIGINT` signed | 9,223,372,036,854,775,807 |

## PostgreSQL integer key columns

```sql
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE data_type IN ('integer', 'smallint')
  AND (column_default LIKE 'nextval%' OR is_identity = 'YES')
ORDER BY 1, 2;
```

Foreign-key columns do not carry a default, so list them separately:

```sql
SELECT c.conrelid::regclass AS child, a.attname, format_type(a.atttypid, a.atttypmod) AS child_type,
       c.confrelid::regclass AS parent
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
WHERE c.contype = 'f' AND a.atttypid = 'int4'::regtype;
```

## MySQL

```sql
SET SESSION information_schema_stats_expiry = 0;
SELECT t.table_schema, t.table_name, c.column_name, c.column_type, t.auto_increment,
       CASE
         WHEN c.column_type LIKE 'tinyint%unsigned%' THEN 255
         WHEN c.column_type LIKE 'tinyint%' THEN 127
         WHEN c.column_type LIKE 'smallint%unsigned%' THEN 65535
         WHEN c.column_type LIKE 'smallint%' THEN 32767
         WHEN c.column_type LIKE 'mediumint%unsigned%' THEN 16777215
         WHEN c.column_type LIKE 'mediumint%' THEN 8388607
         WHEN c.column_type LIKE 'int%unsigned%' THEN 4294967295
         WHEN c.column_type LIKE 'int%' THEN 2147483647
       END AS max_value
FROM information_schema.tables t
JOIN information_schema.columns c USING (table_schema, table_name)
WHERE c.extra LIKE '%auto_increment%' AND t.auto_increment IS NOT NULL
ORDER BY t.auto_increment / max_value DESC;
```

Rows with no `max_value` are `bigint`. In MySQL, `AUTO_INCREMENT` resets to the largest stored value on restart for versions before 8.0, so read it before a restart changes the picture.

## Growth sampling

Record `(now(), last_value)` for each hot sequence twice, a week apart, in a scratch table. Daily growth is the difference divided by days elapsed. Re-sample after any launch that changes traffic.

## Stopgap commands

```sql
-- PostgreSQL: continue from the negative end
ALTER SEQUENCE orders_id_seq START WITH -2147483648 MINVALUE -2147483648 MAXVALUE -1 RESTART WITH -2147483648;
-- MySQL: double the range (COPY blocks writes; run via an online schema-change tool or a
-- replica switchover, and change foreign-key child columns in the same plan)
ALTER TABLE orders MODIFY id INT UNSIGNED NOT NULL AUTO_INCREMENT;
```

Both are temporary. The negative restart yields about 2.1 billion new ids, from -2147483648 up to -1, and stops being safe at zero only if existing ids start at 1: set `MAXVALUE -1` on the sequence so it errors rather than colliding, and check that no existing id is already negative.
