# Search recipes

Reference for steps 2 to 4 of the workflow.

## Contents

- [Unaccented search](#unaccented-search)
- [Trigger-maintained vector on a large live table](#trigger-maintained-vector-on-a-large-live-table)
- [Phrase and prefix queries](#phrase-and-prefix-queries)
- [Choosing a configuration](#choosing-a-configuration)
- [Checking the plan](#checking-the-plan)

## Unaccented search

`unaccent()` is not marked immutable, so it cannot sit directly inside a generated column
or an expression index. Build a text-search configuration that applies the unaccent
dictionary during parsing instead:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE TEXT SEARCH CONFIGURATION english_unaccent (COPY = english);
ALTER TEXT SEARCH CONFIGURATION english_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, english_stem;
```

Use `'english_unaccent'` in both `to_tsvector` and `websearch_to_tsquery`. A
mismatched configuration between the stored vector and the query is the usual cause of "it
matches in one place and not the other": it shows up as missing or wrong matches, not as
a slow plan.

## Trigger-maintained vector on a large live table

When the table is too large to rewrite for a generated column:

```sql
ALTER TABLE articles ADD COLUMN search tsvector;

CREATE FUNCTION articles_search_update() RETURNS trigger AS $$
BEGIN
  NEW.search :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.body,  '')), 'B');
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER articles_search_trg
  BEFORE INSERT OR UPDATE OF title, body ON articles
  FOR EACH ROW EXECUTE FUNCTION articles_search_update();
```

Backfill existing rows in batches of a few thousand with an update on a key range, commit
between batches, then build the GIN index with `CREATE INDEX CONCURRENTLY`. A failed
concurrent build leaves an invalid index; drop it before retrying.

## Phrase and prefix queries

- `websearch_to_tsquery('english', '"red shoes" -sandals')` matches the phrase and
  excludes the term.
- `phraseto_tsquery` builds a phrase query from plain text using the followed-by
  operator `<->`.
- A prefix match needs `to_tsquery('english', 'sho:*')`. That function raises on bad
  syntax, so build the string only from sanitised tokens (letters and digits) in
  application code.

## Choosing a configuration

| Content | Configuration | Reason |
| --- | --- | --- |
| English prose | `english` | Stemming and stop words help recall |
| Names, SKUs, codes, tags | `simple` | No stemming, no stop-word removal |
| Another language | The matching built-in (`german`, `french`, ...) | Check `\dF` for what the server ships |
| Mixed languages in one column | Store the language per row and use the `regconfig` column in `to_tsvector` | One configuration cannot stem both |

## Checking the plan

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM articles
WHERE search @@ websearch_to_tsquery('english', 'postgres replication');
```

Expect a `Bitmap Index Scan` on the GIN index followed by a `Bitmap Heap Scan`. A
`Seq Scan` means the index is invalid or the planner judged the term too common for the
index to help. With a stored vector column, a different configuration in the query still
uses the GIN index and returns wrong or missing matches instead. Only an expression index
such as `to_tsvector('english', body)` needs the query's configuration to match the
indexed expression to be used at all.
