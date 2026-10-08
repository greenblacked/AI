---
description: Diagnose one skill in this repository, covering validator findings, eval-set balance, and the description properties that decide whether it ever fires.
argument-hint: skill name, for example ci-triage
agent: agent
---
<!-- source: .claude/commands/skill-doctor.md sha256: ae4c1083ca431eb6aa9bde6f1ff7644c2c363735387b769c8ba8f85bd0e8e051 -->

Diagnose the skill named `${input:skill:skill name}`.

Locate it and run the validator over the tree, then report only the findings whose path is inside
that skill:

```bash
skill='${input:skill:skill name}'
find plugins -type d -name "$skill"
PYTHONPATH=src python3 -m skillcheck . --strict
```

Then report, in this order:

1. Validator findings for this skill, errors before warnings. If there are none, say so plainly
   rather than padding.
2. Description health, since this is the only text loaded before the skill fires and
   under-triggering is the failure mode nobody notices: its length against the 1024 cap, whether it
   carries an explicit "Use this skill when" clause, whether it names the casual phrasings someone
   would actually type, and whether it says what the skill is not for and names the adjacent skill.
3. Eval set: the count and the split, duplicates, and, the part worth real attention, how many
   negatives are drawn from a neighbouring skill rather than from an unrelated domain. A negative
   like "how do I bake bread" proves nothing. Name the sibling each negative is defending against,
   and say which siblings are unrepresented.
4. Collisions: read the descriptions of the other skills in the same plugin and name any whose
   trigger surface overlaps this one. Quote the overlapping phrases.

Finish with the smallest change that would improve triggering, and be specific about what it would
fix. If the answer is that nothing needs changing, say that.

Do not edit the skill. This reports; the author decides.

Full prompt: `.claude/commands/skill-doctor.md`.
