---
applyTo: "plugins/**/agents/*.md,.claude/agents/*.md"
---
<!-- source: .claude/rules/agents.md sha256: 56eb645b3b9576f5cf7d8dade92a60f029deb1f480b859d5929d7d20efe7f16e -->

# Writing or editing a subagent

`AGENTS.md` is the authority and `docs/writing-agents.md` has the full contract. The key
rules, kept inline because a reviewer may not follow links:

- The paired skill must claim a different act. The subagent reads or finds; the skill decides.
  A skill whose description claims the same act wins the subagent's queries.
- A low trigger score is a collision, not a short description. Lengthening a description does
  not fix one; the paired skill has to cede the queries.
- The skill body hands off to the subagent by name at the point the material gets bulky.
- Cede in both directions: the subagent's description names the skill that decides, and the
  skill's description names the subagent for the bulk read.
- Do not take a vendor built-in's name (`Explore`).
- Only the fourteen frontmatter keys from the plugins reference are allowed: `name`,
  `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`,
  `background`, `omitClaudeMd`, `isolation`, `color`, `experimental`.
- A reader gets no `Write` and no `Edit`, and says so in `disallowedTools`. A reader granted `Bash` can still write a file, so say this
  in its body; the tool list alone does not stop it.
- A reader of the user's own personal data returns aggregates and quotes, never the material
  back: account, card and policy numbers masked to the last four digits, no copy kept on disk.

Score a changed description before committing, one run at a time:
`scripts/run_trigger_eval.py --agent <path> --runs 3 --jobs 2`, then score the paired skill too.

Full rules: `.claude/rules/agents.md` and `docs/writing-agents.md`.
