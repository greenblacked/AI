# Runbook verification record

One record per verification of one runbook, whether a game day, a walkthrough in staging or a
real incident. It backs the runbook's Last verified line: copy the date from here, and do not
move that date for an edit. Delete the guidance in brackets.

## Runbook

- Runbook title and path: [title, repository path]
- Owner (team or rota): [name]
- Alerts that link here: [alert names]

## Verification

- Date: [YYYY-MM-DD]
- How: [game day / walkthrough in staging / real incident / dry read only]
- Who ran it: [rota or role; the newest person on the rota is the most useful]
- Environment: [staging, production, a replica, and what differed from production]

## Steps run

| Step | Command run | Expected output | Actual output | Result |
| --- | --- | --- | --- | --- |
| [1. Confirm it is real] | [command] | [what the runbook says to expect] | [what appeared] | [matched / differed / not run] |
| [5. Mitigation, and its undo] | [command] | [expected] | [actual] | [matched / differed / not run] |

## Decision table

- Rows exercised: [row numbers, and the observation that selected each]
- Rows not exercised: [row numbers, and why they could not be]
- Did the "nothing matches" row get a real escalation contact: [yes / no, and who answered]

## Findings

- What failed or was ambiguous: [command, step, missing access, stale link]
- Links opened from outside the affected system: [which, and which failed]
- Changes made to the runbook: [what, and the commit or page version]

## Result

- Verdict: [verified / verified with fixes / not verified]
- Last verified date to write in the runbook: [YYYY-MM-DD, or "unchanged" when not verified]
- Next verification due: [YYYY-MM-DD, and what triggers it sooner]
