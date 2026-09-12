---
paths:
  - "src/skillcheck/**"
  - "tests/**"
---

# Changing the validator

`AGENTS.md` is the authority; this is the part of it that applies to the file you just
opened, loaded now rather than hoped for.

- **Plan mode first.** This package decides whether every other change is allowed to
  merge, so a mistake here is more expensive than it looks.
- **No third-party imports.** CI runs the validator on Python 3.10 through 3.13 with
  nothing installed, and that guarantee is what the whole pipeline rests on. A dependency
  here breaks it silently on the interpreter you did not test.
- **A rule change with no test change is almost always missing a case.** Write the case in
  the same commit.
- **Do not soften a rule to unblock a change.** Not an error downgraded to a warning, not
  a threshold lowered, not a test assertion loosened, and never a skill's `description`
  edited to make a check pass. If the check is wrong, fix the check and its test, and say
  that is what you did.
- **A fixture changed to satisfy a new rule is how that rule gets defanged.** If a fixture
  has to change, ask whether it was the pattern the rule exists to discourage, and say so
  in the commit either way.

`frontmatter.py` parses, `rules.py` decides, `cli.py` reports. Run `make validate` and
`make test` before you stop.
