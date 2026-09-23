---
paths:
  - "plugins/**/agents/*.md"
  - ".claude/agents/*.md"
---

# Writing or editing a subagent

`AGENTS.md` is the authority and `docs/writing-agents.md` has the full contract; this is
the part that applies to the file you just opened. Each rule below was measured against
this repository's own subagents, and the numbers live in
[what the scores showed](../../docs/writing-agents.md#what-the-scores-showed) rather than
here, because this file loads every time a subagent is opened and a figure in it would be
read long after it stopped being true.

- **The paired skill must claim a different act.** Where a skill's description claims
  the same act its subagent performs, the subagent loses its queries to the skill, and
  that decided every score measured. The subagent reads or finds; the skill decides.
  `pii-reader` finds personal data in a dump and `data-privacy` decides what to do about
  it, and neither loses queries to the other.
- **A low score is a collision, not a short description.** Lengthening a description was
  tested and did not fix one. If the paired skill's quoted phrasings cover your
  triggering queries, no wording of yours wins them back; the skill has to cede them.
- **The skill body hands off to you by name.** A subagent reached only by routing loses
  to its own skill more often than not. The skill names the subagent at the point the
  material gets bulky, and that line is what makes the subagent run whichever side wins
  the query. Each paired skill here carries one; if you add a pair, that line is the fix
  rather than a rewritten description.
- **Cede in both directions.** Your description names the skill that decides, and the
  skill's description names you for the bulk read. The validator checks that anything
  after `Not for` or `Do not use` names something that exists.
- **Do not take a vendor built-in's name.** `explorer` competes with the built-in
  `Explore` and the eval catalogue cannot see it. A project subagent named exactly
  `Explore` overrides the built-in instead, which is the documented way to win that one.
- **Your description costs nothing against the listing ceiling.** Subagents bill against
  the vendor's separate 15,000-token budget, and this repository uses a small fraction of
  it. Keeping a description artificially short buys nothing.
- **Fourteen frontmatter keys, from the plugins reference.** `name`, `description`,
  `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`,
  `background`, `omitClaudeMd`, `isolation`, `color`, `experimental`. The sub-agents
  page lists more; only the plugins reference is scoped to what survives being
  shipped. `initialPrompt` was accepted here once and is not on it.
- **Readers get no `Write` and no `Edit`**, and say so in `disallowedTools` where a
  reader will see it. `incident-scribe` carried `Write` in both lists; the denylist
  quietly won and the file said otherwise.
- **A reader of the user's own personal data returns aggregates and quotes, never the
  material back.** `statement-reader` and `terms-reader` mask an account, card or policy
  number to its last four digits, name what they are returning rather than the address,
  date of birth or full number sitting next to it, and write nothing to disk — the whole
  point of delegating the read is that the raw document stays out of the caller's context,
  and a summary that repeats it back or saves a copy undoes that.

Score it before you commit, one run at a time: `scripts/run_trigger_eval.py --agent
<path> --runs 3 --jobs 2`. Several concurrent runs cause the model CLI to time out and
abort mid-scoring. Then score the paired skill too, because a description that scores
well while breaking its neighbour is the defect the pull request gate exists to catch.
