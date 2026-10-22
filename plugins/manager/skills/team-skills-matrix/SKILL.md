---
name: team-skills-matrix
description: "Find single points of knowledge on a team and plan cross-training. Rows are capabilities taken from the last six months of incidents and the next two quarters of roadmap, scores each person zero to three by observable behaviour, flags any capability with fewer than two people at level two or above, ranks flags by impact times likelihood of absence, and pairs the top three with a named learner, a date and shadow, reverse shadow and solo gates. Rescored quarterly; never an input to reviews or pay. Use for \"what happens if Priya is out\", \"build a skills matrix for the team\", \"we have one person who knows the payments service\". Not for individual evaluation (growth-review), one joiner (onboarding-plan), infrastructure resources (capacity-planning), who might leave (retention-review), or closing one flagged gap (shadow-reverse-shadow, tacit-knowledge-elicitation)."
allowed-tools: Read, Grep, Glob
---

# Team Skills Matrix

A skills matrix is done when the team can name which capabilities would stop if one named person were absent for a month, and has three of them already being closed by a named learner on a dated plan. The output is a small matrix, a short list of flagged gaps and three cross-training pairings, not a grid of everyone's strengths.

The usual failure is a matrix of technology names (Kubernetes, Postgres, React) filled in from self-assessment. It looks complete, shows everybody as competent and misses the thing that actually breaks: the person who alone knows how to do the quarterly billing reconciliation, or what to do when the payments queue backs up at night. Capabilities fail in the specific, and so the rows must be specific, drawn from what has actually gone wrong and what is about to be needed. A second failure is using the matrix on people. The moment it feeds a review it is filled in defensively, and the real single points of knowledge vanish from view.

## Scope

Use for: finding capabilities held by one person or none, planning cross-training for the highest-risk ones, and repeating the exercise each quarter.

Do not use for: evaluating an individual's growth or performance (`growth-review`), onboarding one joiner (`onboarding-plan`), sizing infrastructure (`capacity-planning`), predicting who may leave (`retention-review`), or running the transfer of one flagged gap (`shadow-reverse-shadow`, `tacit-knowledge-elicitation`).

## Workflow

### 1. Say what the matrix is not for

Before collecting anything, tell the team in writing that the matrix is never an input to performance reviews, calibration or pay, and put the same sentence at the top of the document. It is a map of risk to the team, not a rating of people. If you cannot make that promise, do not build the matrix; the answers will be defensive. Keep the file where the team can read all of it.

### 2. Derive the rows from evidence

Build rows as capabilities, phrased as something done: "restore the payments database from backup", "release the mobile app", "debug a failed nightly reconciliation", "negotiate a schema change with the data team". Take them from three sources.

- The last six months of incidents and pages: for each, what capability did the responder use, and who was it?
- The next two quarters of roadmap: what capability will each committed item require that the team does not have in depth?
- Recurring manual operations: releases, rotations of credentials, month-end jobs, customer escalations.

Merge duplicates and aim for 15 to 25 rows. Fewer than that hides risk; more makes the exercise unreadable. A row that no incident, roadmap item or recurring task justifies is left out.

### 3. Score by observable behaviour

Use four levels, defined by what the person has done, not by how they rate themselves.

| Level | Meaning |
| --- | --- |
| 0 | Has never done it |
| 1 | Can do it with help |
| 2 | Does it independently |
| 3 | Can teach it and handle an incident in it |

Score from evidence where it exists (who handled the last three pages, who wrote the last changes in the area) and let each person correct their own row. Calibrate with the team together, in one sitting, so a three means the same thing across rows. `references/scoring-guide.md` has behavioural anchors for a few kinds of capability and a spreadsheet layout.

### 4. Flag the single points

A flag is any capability with fewer than two people at level two or above. Count only people who are actually available: someone planning to leave, on extended leave or about to change teams does not count. In the shared sheet show such a person only as "not counted", with no reason; an unannounced departure, leave or move is never recorded in the shared file, and the lead keeps the reasons privately. Also flag any capability with no available person at level three, since nobody could teach it.

### 5. Rank the flags by risk

Score each flag as impact multiplied by the likelihood that the holder is absent when it is needed. Impact: what stops, for how long, and who is affected (an outage, a missed deadline, a blocked release). Likelihood: the holder's on-call and travel schedule, planned leave, how often the capability is used and the base rate for any one person being unavailable. A rough one-to-three scale on each is enough; the point is order, not precision. Pick the three highest, breaking ties by higher impact first. Resist covering all flags at once, because a plan with twelve pairings completes none.

### 6. Pair each top flag with a learner and a date

For each of the three: the capability, the holder, a named learner (chosen for interest and for scheduling slack, not simply the most junior), a start date, a target date and the target level (usually from zero or one to two). Transfer in stages, shadow, reverse shadow and solo: the learner watches the holder do it, then does it with the holder watching, then does it alone while the holder is reachable. Each stage ends with a gate that the holder and the team lead both judge. Gate 1: the learner has watched at least two real occurrences or faithful drills and can explain each step back. Gates 2 and 3: the learner has done the task, in a real case or a faithful drill, to the standard. Hand the mechanics of one transfer to `shadow-reverse-shadow`; use `tacit-knowledge-elicitation` where the holder's knowledge is mostly unwritten.

Plan the time. A learner with no freed capacity does not learn, and the holder must be given time to teach, so remove something from both calendars.

### 7. Rescore every quarter

Repeat steps 2 to 5 each quarter: rows change as incidents and roadmap change, and scores change as people learn or leave. Report what moved: flags closed, flags opened, and the pairings' progress. A matrix not rescored is out of date within a quarter and creates false comfort. Keep the previous versions to see the trend.

## Output format

```markdown
## Team skills matrix: [team], [quarter]

This document is never an input to performance reviews, calibration or pay.

### Matrix
[Rows: capabilities, with their source (incident, roadmap, recurring). Columns: people. Cells: 0 to 3.]

### Flags
[Capabilities with fewer than two people at level 2 or above, with the risk score.]

### Top three and the plan
[Per flag: holder, learner, start, target date, target level, gates.]

### Last quarter
[Flags closed, opened, pairings that stalled and why.]
```

## Anti-patterns

**Technology names as rows.** "Python" is not a capability; "debug a stuck worker in production" is. Rows from incidents find the real gaps.

**Self-assessment alone.** People under-rate and over-rate in predictable ways. Use evidence and calibrate together.

**The matrix feeds reviews.** Once it does, scores inflate and the single points of knowledge go unreported. State the exclusion and keep to it.

**Counting people who are leaving.** A level-three person with a notice period is a gap that has not yet opened. Treat them as absent.

**Twelve pairings at once.** None finishes. Start the top three and add one when one closes.

**Cross-training without freed time.** The plan is a wish if neither calendar changes. Remove work from the learner and the teacher.

**Documentation as the cure.** A written runbook helps, but a capability is closed when someone else has done it for real, to a gate.

## Reference files

- `references/scoring-guide.md` read when scoring or setting up the sheet: behavioural anchors for the four levels across operations, delivery and domain capabilities, the sheet layout and how to calibrate in one sitting.
- `references/cross-training-plan.md` read when pairing: a plan template with the staged gates, how to choose the learner, and quarterly rescoring notes.
