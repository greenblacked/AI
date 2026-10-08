---
applyTo: "src/skillcheck/**,tests/**"
---
<!-- source: .claude/rules/validator.md sha256: 11eeb0f1213e5861bcb0cba5a96357d626311d2ce9c60620bc82154409bc2aca -->

# Changing the validator

`AGENTS.md` is the authority. This package decides whether every other change may merge, so a
mistake here costs more than it looks. The key rules, kept inline because a reviewer may not
follow links:

- Agree the approach before editing: a change here is planned first, not discovered while typing.
- No third-party imports. CI runs the validator on Python 3.10 through 3.13 with nothing
  installed, and the whole pipeline rests on that.
- A rule change with no test change is almost always missing a case. Write the case in the same
  commit.
- Do not soften a rule to unblock a change: no error downgraded to a warning, no threshold
  lowered, no test assertion loosened, and never a skill's `description` edited to make a check
  pass. If the check is wrong, fix the check and its test, and say that is what was done.
- A fixture changed to satisfy a new rule is how that rule gets defanged. If a fixture has to
  change, ask whether it was the pattern the rule exists to discourage, and say so in the commit.

`frontmatter.py` parses, `rules.py` decides, `cli.py` reports. Run `make validate` and
`make test` before stopping.

Full rules: `.claude/rules/validator.md`.
