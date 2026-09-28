# Brief template, worked

Read this when writing the actual text of a brief. It repeats the fixed section shape from `SKILL.md`'s output format, filled in for two small, genuinely bounded tasks — a one-field addition and a one-function bug fix — so the shape is concrete rather than abstract.

## Contents

- [The template](#the-template)
- [Worked example: a one-field addition](#worked-example-a-one-field-addition)
- [Worked example: a one-function bug fix](#worked-example-a-one-function-bug-fix)

## The template

```markdown
## Done-check
[The exact runnable command whose exit code decides "done".]

## Evidence
[The failing test's output, the reproduction, or the bug report — pasted or linked, not summarised.]

## Scope
May edit: [paths]
May not edit: [paths — tests, CI config, lint and coverage thresholds, lockfiles, named explicitly]

## Stop conditions
[What forces the agent to stop and ask rather than proceed.]

## Report format required back
[The exact command and its output, and the list of changed files.]
```

## Worked example: a one-field addition

```markdown
## Done-check
`pytest tests/test_orders.py::test_order_has_gift_wrap_flag -x`

## Evidence
The test above does not exist yet. Write it first: an order created with
`gift_wrap=True` should serialise `"giftWrap": true` in the API response. It should
currently fail with `AttributeError: 'Order' object has no attribute 'gift_wrap'`
once the assertion is added, before any implementation exists.

## Scope
May edit: `app/models/order.py`, `app/serializers/order.py`,
`migrations/` (one new additive migration only), `tests/test_orders.py`.
May not edit: any other test file, `.github/workflows/`, `pyproject.toml`'s
`[tool.coverage]` section, `requirements.lock`.

## Stop conditions
Stop and ask before adding a new dependency, before touching any file outside the
scope above, or if the migration would need to backfill existing rows rather than
add a nullable column with a default.

## Report format required back
The exact `pytest` command and its full output, plus `git diff --stat` against the
base commit.
```

## Worked example: a one-function bug fix

```markdown
## Done-check
`pytest tests/test_pagination.py::test_cursor_survives_concurrent_insert -x`

## Evidence
Reproduction: inserting a row with a timestamp earlier than the current page's
cursor, mid-pagination, causes the next page to skip a row. The test above
encodes this as a failing assertion today; its output is:
`AssertionError: expected 20 unique ids across both pages, got 19`.

## Scope
May edit: `app/pagination.py`, `tests/test_pagination.py` (only to add the
reproduction above, not to relax an existing assertion).
May not edit: any other file under `tests/`, `app/models/`, `.github/workflows/`.

## Stop conditions
Stop and ask if the fix appears to require changing the cursor's encoded fields
rather than the comparison logic — that is a wider change than this brief covers.

## Report format required back
The exact `pytest` command and its full output, plus the list of changed files
from `git diff --name-only`.
```
