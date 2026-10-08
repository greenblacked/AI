---
applyTo: "plugins/**/SKILL.md,plugins/**/evals/*.json"
---
<!-- source: .claude/rules/skills.md sha256: e58d29e92b1b2363be9d72699723b1949eaef39068f073c0fca8417544ef9ffb -->

# Writing or editing a skill

`AGENTS.md` is the authority and `docs/writing-skills.md` has the full contract. The key
rules, kept inline because a reviewer may not follow links:

- Six frontmatter keys and no seventh: `name`, `description`, `license`, `allowed-tools`,
  `metadata`, `compatibility`. The skill upload route rejects any other key, and every skill
  must survive `make package`. `when_to_use` belongs in `description`.
- `name` equals the directory name. Two skills sharing a name silently replace each other.
- The description is the only text loaded before the skill fires. Keep it within 500 to 900
  characters, name the circumstances in the words someone would actually type, and say what the
  skill is not for, naming the neighbour that owns that instead. Never edit it just to make a
  check pass.
- A path named in prose must exist. The validator fails on a pointer to nothing.
- Twenty eval queries, ten a side, with `"expected"` on every negative that has an obvious owner.
- Every command printed must run. Execute it; `scripts/check_shell.py` only proves it parses.

`make catalogue` fails on a new skill for the missing README row and may fail on the plugin's
listing ceiling. Add the row, then raise the ceiling with
`scripts/check_listing_budget.py --update` and say why, or split the plugin.

Full rules: `.claude/rules/skills.md` and `docs/writing-skills.md`.
