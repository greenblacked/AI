# The drift map

Read this when building or reviewing the map from documented surface to pages. The map is
the whole mechanism: the checks in CI are a few lines of set arithmetic over it, and they
are exactly as good as its entries.

## Contents

- [File format](#file-format)
- [Extracting identifiers per kind](#extracting-identifiers-per-kind)
- [Forms an identifier takes in prose](#forms-an-identifier-takes-in-prose)
- [Pruning candidates](#pruning-candidates)
- [Scheduled regeneration](#scheduled-regeneration)

## File format

One file, in the repository where the code changes are made, owned in `CODEOWNERS` by the
team that owns the docs. YAML keeps it reviewable in a diff:

```yaml
docs_root: docs/
historical:              # pages that may name removed identifiers on purpose
  - CHANGELOG.md
  - docs/migrations/**
  - docs/v1/**
identifiers:
  - id: storage.retention_days
    kind: config
    forms: [storage.retention_days, retention_days, APP_STORAGE_RETENTION_DAYS]
    pages:
      - docs/configuration/storage.md
      - docs/guides/data-lifecycle.md
  - id: --dry-run
    kind: cli-flag
    forms: [--dry-run]
    pages:
      - docs/cli/migrate.md
paths:                   # behaviour no single identifier names
  - glob: src/retry/**
    pages:
      - docs/concepts/retries.md
ignore:
  - id: timeout
    reason: generic; mapped as storage.timeout and http.timeout instead
```

Every `ignore` entry carries a reason, so the next person regenerating the map does not
re-add it, and so a reviewer can tell a judgement from an omission.

## Extracting identifiers per kind

Read each list from the definition, so the inventory is the code's own view of its surface.

| Kind | Where to read it | Notes |
| --- | --- | --- |
| Config key | JSON Schema `properties`, walked recursively; a settings class's generated schema (for example pydantic's `model_json_schema()`) | Emit the dotted path; record the env var form if the loader derives one |
| CLI flag | The parser object: click's `Command.params` and each parameter's `opts`; cobra's `Flags().VisitAll` on each command; argparse has no public listing, so read the `--help` output of each subcommand | Include subcommand names; record hidden or deprecated flags separately |
| Environment variable | The read calls: `os.getenv`, `os.environ[...]`, `process.env.X`, `std::env::var`, `os.Getenv` | A grep for the call is acceptable here because the pattern is the definition |
| HTTP endpoint | The keys of the OpenAPI document's `paths` object | Map path templates; pages usually show the template, not an example ID |
| Feature flag | The flag registry or flag-service export | Only flags users or operators can set |
| Metric or event | The instrumentation registry or the metric declarations | Only names someone outside the team queries |

Skip internal function and class names unless the docs are an SDK reference. Those pages
are best generated from the code, at which point drift is impossible and they need no map.

## Forms an identifier takes in prose

A fixed-string search for the canonical form misses the page that writes it another way.
Record each form the docs actually use:

- **Nested config.** `storage.retention_days` appears in a YAML example as `retention_days:`
  under `storage:`. Search the leaf as well, and accept a leaf match only on pages that
  also name the parent section, or only when the leaf is distinctive on its own.
- **Derived environment variables.** A loader that maps `storage.retention_days` to
  `APP_STORAGE_RETENTION_DAYS` makes that a form of the same identifier.
- **Flag spellings.** `--dry-run` and its short form `-n`; map the short form only when it is
  distinctive, because a two-character string matches everywhere.
- **Endpoint templates.** `/v2/invoices/{id}` in the spec may appear as `/v2/invoices/:id` or
  with a sample ID in prose.

## Pruning candidates

Generation proposes; a person decides. Walk the candidates with these rules, in order:

1. **Historical page?** Changelogs, migration guides, release notes, docs for an older major
   version. Add the page to `historical`, not to the entry.
2. **Generic identifier?** If the term would plausibly appear on a page for an unrelated
   reason, map the qualified form or a path, or add it to `ignore` with the reason.
3. **Incidental mention?** A page listing every config key in a big table is a reference
   page and should map; a tutorial that mentions the key once in passing should also map,
   because it goes just as false. Keep both.
4. **Generated page?** If the page is generated from the same source of truth, it cannot
   drift; exclude it and say so.

Sample twenty entries after pruning and open each page. If more than a couple are false
matches, the distinctiveness rule is too loose and the pull request comment will be
ignored.

## Scheduled regeneration

Run generation weekly, compare with the committed map, and open a change containing:

- new identifiers with candidate pages, for a person to prune;
- pages that no longer contain an identifier mapped to them, to drop;
- identifiers mapped to no page, reported as undocumented surface rather than added.

The same job fails when any page named in the map does not exist. A deleted or moved page
left in the map means its identifiers are checked against nothing, and the check keeps
passing.
