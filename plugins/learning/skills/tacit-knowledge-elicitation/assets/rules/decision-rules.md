---
paths:
  - "**/interviews/**/*.md"
---

# Decision rules from expert interviews

Loads when a file under an interviews directory is read or edited. A rule is only useful to the
next person if they can apply it to a case that does not quite match.

- Write each rule as "If X, look at Y first because Z". X is something a person can observe,
  Y is a named place or action, and Z is the reason; without Z the rule is a note only its
  author can use.
- Keep an exception on the line after the rule it qualifies, so it is not read as a separate
  rule.
- Mark each rule with the case it came from and the artefact that shows it.
- Keep facts about the system out of the rule sheet; they belong in the documentation.
- Keep the recording and transcript apart from the rule sheet and say where they are stored.
- Run the sheet past a second person on a case the interviews did not use, using the
  `tacit-knowledge-elicitation` skill, and record what they got wrong in
  `decision-rule-sheet.md`.
