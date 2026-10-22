# Pinned set and summary template

## Pinned set by kind of agent

| Kind | Always verbatim |
| --- | --- |
| Support assistant | Customer's stated problem, account and order ids, promises already made, policy exceptions granted |
| Coding agent | Task statement, files changed and why, commands that worked and failed, test names, the user's style rules |
| Research agent | The question, source urls and what each supported, claims rejected and why |
| Planning assistant | Goals, constraints, dates, budget figures, options ruled out and the reason |

## Summary template

```text
Task: <the user's request, quoted>
Constraints and corrections:
- "<exact words>" (turn N)
Decisions:
- <decision> because "<reason as stated>"
Open questions:
- <question> (owner)
State:
- files: <exact paths>
- ids: <exact ids>
- commands: <exact commands>
Done:
- <completed item>
Next step: <one line>
```

Instruct the summariser: copy values exactly, do not merge two corrections into one, do not drop an item because it seems minor, say "unknown" rather than guessing.

## Code check

After summarising, extract the pinned identifiers (paths, ids, versions) from the dropped turns with a regex or from structured state the agent keeps, and confirm each appears in the summary. Missing ones are appended under State. Keep this check in code: it does not depend on the summariser behaving.

## Stubs for cleared tool results

`[search_tickets(query="refund", status="open") -> 37 matches, top: SUP-1042; re-run to fetch]`

A stub names the tool, arguments, outcome and how to recover the content.
