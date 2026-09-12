## What this changes, and why

<!-- One paragraph. The diff says what; say why. -->

## Review checklist

Confirm each of these, and say honestly if one does not hold.

- [ ] `make validate` exits 0
- [ ] `make catalogue` exits 0 — listing ceilings, and the README against the tree
- [ ] `make test` passes
- [ ] Every `references/`, `scripts/` or `assets/` path named in prose exists
- [ ] Any new skill sits inside `plugins/<name>/skills/` and has an eval set
- [ ] No secrets, tokens or personal data added
- [ ] Commit messages carry no tool attribution

`ci` and `security` both have to be green before merge.
