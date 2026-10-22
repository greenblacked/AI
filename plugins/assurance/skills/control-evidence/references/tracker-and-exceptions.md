# Tracker and exception notes

## Request tracker columns

| Column | What goes in it |
| --- | --- |
| Request id | The auditor's own reference, unchanged, so both sides can talk about the same row |
| Control id | Your register's id; several requests can point at one control |
| Request text | The auditor's words, verbatim — paraphrase is where the wrong artefact gets sent |
| Period covered | The dates the evidence must span |
| Artefact | File name in the evidence store, with collection date |
| Provenance | The query, report or API call that produced it, who ran it and when |
| Owner | One person |
| Due date | The date agreed with the auditor, not the date it would be nice |
| Status | See below |
| Follow-up | Every question the auditor sends back, dated, with the answer |

## Status flow

`open` → `collecting` → `internal review` → `submitted` → `accepted`, with `follow-up` returning a row to `collecting`.

Internal review is a second person checking that the artefact answers the request, covers the full period, contains nothing out of scope, and has its provenance attached. It catches the screenshot of the wrong account before the auditor does.

Report the tracker weekly during fieldwork by owner: open rows, overdue rows, and rows on their second follow-up. A row on its third follow-up usually means the control does not work the way the narrative says, and is worth a conversation with the control owner rather than another export.

## Exception note template

File one the day a self-test or reconciliation finds a failed item.

```markdown
## Exception CE-2026-014

- Control: CHG-01, production changes approved by someone other than the author
- Found: 2026-04-09, internal quarterly self-test, sample of 25 from 1,412 merged pull requests
- What failed: pull request 3311 merged with an approval from its own author's second account
- Population impact: searched the full population for the same pattern; 1 further instance (pull request 3290)
- Root cause: a personal second account held write access and review rights on the repository
- Remediation: second accounts removed from the organisation on 2026-04-10; ruleset now requires approval from a member of the reviewers team
- Compensating control in the gap: deploy alerts were reviewed daily by the on-call engineer; both changes inspected after the fact and found benign
- Fixed on: 2026-04-10
- Owner: named control owner
- Accepted rather than fixed: no (if yes, link the risk register entry)
```

Search the whole population for the same failure before writing the note. One instance in a sample usually means more in the population, and the auditor will ask how many.
