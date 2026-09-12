---
paths:
  - "plugins/**/SKILL.md"
  - "plugins/**/evals/*.json"
---

# Writing or editing a skill

`AGENTS.md` is the authority and `docs/writing-skills.md` has the full contract; this is
the part that applies to the file you just opened.

- **Six frontmatter keys, and no seventh.** `name`, `description`, `license`,
  `allowed-tools`, `metadata`, `compatibility`. Claude Code accepts more; the Skills API
  upload route rejects every other key with a hard error, and every skill here has to
  survive `make package`. `when_to_use` is the tempting one, and its content belongs in
  `description`.
- **`name` equals the directory name.** Two skills sharing a name silently replace each
  other on install, and every counter still reports success.
- **The description is the only text loaded before the skill fires**, so it decides
  whether the skill is ever used. Write it last. Keep it inside 500–900 characters rather
  than at the 1024 cap, name the circumstances in the words someone would actually type,
  and say what the skill is *not* for, naming the neighbour that owns that instead.
- **If you name a path in prose, create the file.** The validator fails on a pointer to
  nothing, because in production that failure is silent: the model follows the pointer,
  finds nothing, and carries on.
- **Twenty eval queries, ten a side**, and put `"expected"` on every negative with an
  obvious owner. Without it a negative passes when *any* other skill fires, including the
  wrong one, and the routing number has nothing to measure. A query nothing here claims is
  right to leave alone.
- **Every command you print must run.** `scripts/check_shell.py` proves the shell parses;
  it cannot prove a flag exists. Execute it.

`make catalogue` will fail on a new skill twice, both deliberately: no README row yet, and
the plugin's listing pushed past its ceiling. Add the row, then raise the ceiling with
`scripts/check_listing_budget.py --update` and say why, or split the plugin.
