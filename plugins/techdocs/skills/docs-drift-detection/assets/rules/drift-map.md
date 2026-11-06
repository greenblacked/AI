---
paths:
  - "**/drift-map.yaml"
---

# Drift map

Loads when a drift map is read or edited. The map is exactly as good as its entries, and a
check that fires on every pull request gets muted.

- Every `ignore` entry carries a non-empty `reason`. Without one, the next person
  regenerating the map cannot tell a judgement from an omission and adds the identifier back.
- Map only distinctive identifiers: `storage.timeout`, not `timeout`. A generic key matches
  pages with nothing to do with the change.
- Put changelogs, migration guides and docs for older major versions under `historical`, not
  under an entry's `pages`.
- Every page named in the map must exist. A dangling entry checks its identifiers against
  nothing and the check keeps passing.
- Build and prune the map with the `docs-drift-detection` skill, and record each unmapped
  page in its `unmapped-page-review.md` template.
