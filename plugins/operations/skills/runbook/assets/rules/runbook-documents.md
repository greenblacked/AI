---
paths:
  - "**/runbooks/**/*.md"
  - "**/*runbook*.md"
---

# Runbook documents

Loads when a runbook is read or edited. The reader is awake at 3am, new to the system and
about to run a command against production, so what the document leaves implicit becomes a guess.

- Open with one sentence on what the symptom means for users, then whether customer comms are
  likely. Put the owner and the last-verified date in the first lines, where no scrolling hides them.
- Make the first step a read-only check that the problem is real and not a monitoring artefact.
  Capture the evidence a fix would destroy before any step that changes state.
- Order mitigations least destructive first. Give each its blast radius and the command that
  undoes it, beside it and not in a later section.
- Add a decision table from observation to conclusion to next step, with a row for "nothing
  matches" that says who to escalate to.
- Use variables set once at the top, never a placeholder inside a command that could be pasted
  as written. Escalate to a role or rota, never a named person.
- Owner is a team or rota. Last verified is the date someone ran the steps, with who and how;
  an edit is not a verification. Record each one with `runbook-verification-record.md` from the
  `runbook` skill's kit, and write the date as `YYYY-MM-DD`.
