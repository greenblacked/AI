---
name: docs-drift-detection
description: "Find which documentation pages a code change makes false, before it merges. Build a reviewed map, kept in the repository, from code paths, config keys, CLI flags, environment variables and endpoints to the pages that name them; have CI list the affected pages on every pull request touching mapped code, and fail it when a removed identifier is still documented; give pages that map to no code a review date or delete them; track the share of mapped-code changes that also touched docs. Use whenever someone says \"our docs keep going stale after code changes\", \"which pages does this PR affect\", \"nobody remembers to update the docs\" or \"the docs still mention a flag we deleted\". Not for writing or pruning a page (technical-docs), the changelog for a release (release-notes), or readers who cannot find a page (docs-search-vocabulary)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Docs Drift Detection

This is done when the repository holds a reviewed map from the documented surface of the code to the pages that describe it, every pull request touching mapped code is told which pages to check, a pull request that deletes or renames a documented identifier cannot merge while a current page still names it, every unmapped page has an owner and a review date, and the doc-touch rate is measured on a fixed cadence.

The usual failure is relying on memory and a checkbox. A pull request template asks "did you update the docs?", the author ticks it because they cannot know which of four hundred pages mention the flag they renamed, and the page goes on describing the old flag for a year. Nobody is careless: the information needed to answer the question was never in front of them. The second failure is the opposite: a check so noisy, because it matched `timeout` on every page, that everyone learns to ignore it in a week.

## Scope

Use for docs that live beside code, or in a separate repository that documents it, where the question is which pages a change has made untrue. Writing the corrected page or pruning a documentation set belongs to `technical-docs`; the release changelog belongs to `release-notes`; readers failing to find a page that exists belongs to `docs-search-vocabulary`. Error codes and their pages have their own two-way gate in `error-catalogue`, and API contract breaks are caught from the spec by `openapi-diff-gate`; reuse their outputs rather than mapping the same identifiers twice. Snippets that stop compiling are `code-sample-testing`'s, and stale images are `screenshot-rot`'s.

## Workflow

### 1. List the documented surface from its source of truth

Docs describe the public surface, not every function. Take each identifier from the place that defines it, so the list cannot disagree with the code:

| Kind | Source of truth | Example identifier |
| --- | --- | --- |
| Config key | The config schema or settings class | `storage.retention_days` |
| CLI flag and subcommand | The argument parser definition | `--dry-run`, `app migrate` |
| Environment variable | The reads in code, or the documented env list | `APP_LOG_LEVEL` |
| HTTP endpoint | The OpenAPI document's paths | `/v2/invoices/{id}` |
| Feature flag | The flag registry | `new_billing_ui` |
| Metric, event or log field others query | The instrumentation registry | `http_server_duration_seconds` |

Extract each list with a script that reads the definition, not with a grep over the whole codebase: a grep finds the identifier in tests and comments too, and cannot tell the definition of `--force` from a string that happens to contain it.

### 2. Generate candidate mappings, then prune them by hand

For each identifier, search the current docs tree for it as a fixed string and record the pages that contain it. That is a literal, case-sensitive search over the docs directory, such as `rg -F -l -e '<identifier>' docs/`, where `-e` keeps an identifier starting with `--` from being read as an option.

Then review the candidates before committing anything. Two rules decide whether the check is trusted or muted:

- **Map only distinctive identifiers.** `retention_days` is distinctive; `timeout`, `name` and `--verbose` match pages that have nothing to do with the change. Map a generic key by its qualified form (`storage.timeout`) or by a code path, or leave it out.
- **Map only pages that describe the current version.** Changelogs, migration guides and versioned docs for older releases mention removed identifiers on purpose. List them as historical in the map so the checks skip them.

Add path mappings for behaviour no identifier names: the page explaining the retry algorithm maps to the module that implements it.

### 3. Commit the map as a reviewed file

Keep the map in the repository where the code changes are made, with an owning team in `CODEOWNERS`. Each entry names the identifier or path glob, its kind, and the pages. A scheduled job regenerates candidates and opens a change when they differ, so new identifiers get mapped and pages that stop naming an identifier drop out. The same job fails when the map names a page that no longer exists: a map with dangling entries silently stops checking those identifiers. `references/drift-map.md` has the file format, the extraction approach per kind, and the pruning rules in full.

The regeneration also yields a by-product worth reporting on its own: identifiers that appear on no page at all are undocumented surface.

### 4. Tell each pull request which pages it affects

On every pull request, intersect the changed files and the changed identifiers with the map, drop pages the pull request already edits, and post the remainder as one comment, updated on each push rather than added again. Include, per page, the identifier that caused the match, so the author can judge it in seconds.

This check informs and does not block. A changed config parser does not prove a page is wrong, and a blocking check with that much uncertainty gets waived by reflex.

### 5. Block only on certainty

One case is certain: an identifier present in the base branch's source of truth and absent from the head's, still named on a current (non-historical) page. That page is now false. Fail the check, and name the page and line. A rename is the same case, because the old name has left the source of truth.

Allow an explicit, recorded override, such as a label applied by the map's owners, for the rare deliberate case: a flag removed in code but still accepted with a deprecation warning, documented as such. `references/ci-check.md` has the workflow, its permissions, and what changes when pull requests come from forks.

### 6. Give unmapped pages an owner and a date

List every current page with no map entry. Each is either conceptual and slow to rot (give it an owner and a `last_reviewed` date in its front matter, with a review interval) or describes behaviour the map missed (add the mapping) or is dead (delete it, through `technical-docs`'s pruning). An unmapped page with no date is the one that will be wrong next and nothing will say so.

### 7. Measure the doc-touch rate

Over a fixed window, take the merged changes that touched mapped code and report three numbers: the share that also changed a mapped page, the share that carried the override, and the share that did neither. The third is the drift you can see; a rising override share is drift being waved through. Count the code and docs halves from the default branch's history, and the overrides from merged pull requests carrying the label; `references/ci-check.md` has both queries.

## What to hand back

- The surface inventory per kind, with counts and the extraction method for each.
- The committed map, the historical-page list, and the owner in `CODEOWNERS`.
- The pull request check and the blocking check, with a link to one run of each.
- The unmapped-page list with the decision for each: dated, mapped, or deleted.
- The undocumented-surface list, handed to the owners of those features.
- The doc-touch rate baseline, with window and method, and when it will be measured again.

## Anti-patterns

**A checkbox in the pull request template.** The author cannot answer it, so it is ticked. Put the page list in front of them instead.

**Mapping every identifier the grep finds.** Generic names flood every pull request with false pages, and the comment is ignored within a week, true matches included.

**Blocking on "touched mapped code".** A change to the code a page describes is a reason to look, not proof the page is wrong. Block only when the identifier left the source of truth.

**Treating the changelog as drift.** Historical pages mention removed things by design; without a historical list the blocking check fires on every deprecation.

**A map nobody regenerates.** New flags never get mapped and pages that were rewritten keep stale entries; the check quietly covers less each month while still passing.

**Reporting only the touch rate.** A high rate achieved through overrides is the problem, relabelled.

## Reference files

- `references/drift-map.md` — read when building or reviewing the map: the file format, how to extract each kind of identifier from its source of truth, the distinctiveness and historical-page rules, and the scheduled regeneration.
- `references/ci-check.md` — read when wiring the pull request comment and the blocking check into CI: the job outline, token permissions, fork pull requests, the override, and the doc-touch rate query over git history.
