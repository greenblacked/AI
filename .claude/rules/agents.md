---
paths:
  - "plugins/**/agents/*.md"
  - ".claude/agents/*.md"
---

# Writing or editing a subagent

`AGENTS.md` is the authority and `docs/writing-agents.md` has the full contract; this is
the part that applies to the file you just opened. Every item here was measured against
this repository's own subagents rather than assumed.

- **The paired skill must claim a different act.** Across the ten shipped subagents, the
  trigger score was decided by this and by nothing else: where the paired skill's
  description claimed the same act the agent scored 60 to 70 percent, and where it
  claimed a different one the agent scored 95 to 100. The agent reads or finds; the
  skill decides. `pii-reader` finds personal data in a dump and `data-privacy` decides
  what to do about it, and neither loses queries to the other.
- **Length is not the lever.** Lengthening one description from 299 to 719 characters
  moved its score from 60 to 70 percent and made recall worse. A low score is a
  collision with the paired skill, not a short description, so padding it is the wrong
  fix and the numbers say so.
- **The skill body hands off to you by name.** A subagent reached only by routing loses
  to its own skill more often than not. The skill names the subagent at the point the
  material gets bulky, and that line is what makes the subagent run whichever side wins
  the query. Read the paired skill and check the line is there.
- **Cede in both directions.** Your description names the skill that decides, and the
  skill's description names you for the bulk read. The validator checks that anything
  after `Not for` or `Do not use` names something that exists.
- **Do not take a vendor built-in's name.** `explorer` competes with the built-in
  `Explore` and the eval catalogue cannot see it. A project subagent named exactly
  `Explore` overrides the built-in instead, which is the documented way to win that one.
- **Your description costs nothing against the listing ceiling.** Subagents bill against
  the vendor's separate 15,000-token budget, of which this repository uses about nine
  percent. Keeping a description artificially short buys nothing.
- **Twelve frontmatter keys, from the plugins reference.** `name`, `description`,
  `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`,
  `background`, `omitClaudeMd`, `isolation`. The sub-agents page lists more; only the
  plugins reference is scoped to what survives being shipped. `color` and
  `initialPrompt` were accepted here once and are not on it.
- **Readers get no `Write` and no `Edit`**, and say so in `disallowedTools` where a
  reader will see it. `incident-scribe` carried `Write` in both lists for months; the
  denylist quietly won and the file said otherwise.

Score it before you commit, one run at a time: `scripts/run_trigger_eval.py --agent
<path> --runs 3 --jobs 2`. Several concurrent runs cause the model CLI to time out and
abort mid-scoring. Then score the paired skill too, because a description that scores
well while breaking its neighbour is the defect the pull request gate exists to catch.
