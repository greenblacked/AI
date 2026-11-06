# Unmapped page review

Every current docs page that no drift-map entry names, with a decision. Fill in one row per
page and delete the guidance in brackets.

## Scope

- Docs root: [path]
- Drift map and revision: [path and commit]
- Reviewed by: [person or team]
- Review date: [date]

## Pages

| Page | Why no entry names it | Decision | Owner | Next review |
| --- | --- | --- | --- | --- |
| [path] | [conceptual and slow to rot / behaviour the map missed / dead / generated] | [dated / mapped / deleted / excluded] | [person or team] | [date] |

## Decisions

| Decision | Count | What happens |
| --- | --- | --- |
| Dated | [n] | `owner` and `last_reviewed` added to front matter, with a review interval |
| Mapped | [n] | Entry added to the drift map in the same change |
| Deleted | [n] | Removed through the pruning workflow of `technical-docs` |
| Excluded | [n] | Generated from the source of truth, so it cannot drift; the reason is written here |

## Undocumented surface

Identifiers the regeneration found on no page. Hand each list to the owner of the feature.

| Identifier | Kind | Owner |
| --- | --- | --- |
| [identifier] | [config / cli-flag / env / endpoint / flag / metric] | [person or team] |
