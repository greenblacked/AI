---
name: reorg-design
description: "Design, sequence and announce a reorganisation or team-boundary change — name the problem current boundaries cause with evidence (cross-team handoffs per project, who edits whose code, ticket wait time) before drawing boxes, design against the work and assign people in a separate pass, test each candidate against the last three or four real projects, decide in a small closed group with a leak plan, brief in strict order (managers, each person 1:1, then everyone), and write a reversal criterion with a 90-day check. Use for \"we need to split the platform team\", \"merge these two teams\", \"how do we announce the new org structure\", \"reorg rumours are spreading\". Not for the recurring meeting system (design-team-cadence), attrition analysis after the fact (retention-review), outage communication (incident-comms), or one person's hard conversation (difficult-conversation)."
allowed-tools: Read, Grep, Glob
---

# Reorg Design

A reorganisation is done well when the new boundaries remove a named, measured cost, every affected person hears their own news from their own manager before anyone else, and a written criterion says what result would reverse it.

The usual failure is starting with the boxes. Someone is unhappy with a team, a diagram appears, people are slotted in, and the announcement explains the diagram. The problem the boundaries were supposed to fix is never stated, so nobody can tell afterwards whether it worked. The second failure is the gap between decision and announcement: rumours fill it, the best people read the silence as a threat, and some start interviewing before they have been told anything.

## Scope

Use for: splitting, merging or re-aiming teams; moving a boundary between two teams; deciding how and in what order to tell people; recovering when rumours have started.

This skill is procedure, not legal advice; consultation and notice duties are covered in step 5.

Do not use for: the recurring meeting system a new structure needs (`design-team-cadence`); analysing departures after the fact (`retention-review`); communicating an outage (`incident-comms`); a single hard conversation with one person (`difficult-conversation`).

## Workflow

### 1. State the problem the boundaries cause

Write one paragraph that names the cost, with a number, before any structure is proposed. "The platform team is too big" is an opinion; "11 of the last 14 projects needed two or more teams to hand work across, and tickets sat a median of six days in another team's queue" is a problem. Pull the evidence from sources that already exist: project plans for handoffs, repository history for who edits whose code, the ticket tracker for time in another team's queue. `references/boundary-evidence.md` has the queries and the counting rules.

If you cannot find a cost, stop. A reorg without one is a rearrangement, and it carries all the costs below for no gain.

### 2. Design against the work, not the people

List the streams of work the group actually does (the product areas, the services, the recurring request types) and draw candidate structures around those streams. Do not put a name on any box in this pass. Names pull the design toward who would be hurt, who is liked and who is owed a promotion, and the structure ends up shaped like the roster instead of the work.

Produce two or three candidates, including "change nothing but fix the interface" (an explicit service agreement, a named intake path). It is the baseline the others have to beat.

### 3. Test each candidate against real projects

Take the three or four most recent significant projects. For each candidate, mark which teams each project would have touched and count how many cross a team boundary. A candidate that does not reduce the count from step 1 does not solve the stated problem, however tidy it looks. Also note what the candidate makes worse: a new boundary usually creates a new handoff somewhere else.

Pick the candidate with the lowest crossing count whose new handoffs are the cheapest. State the runner-up and why it lost.

### 4. Assign people in a separate pass

Only now put names on boxes. Work from skills and ownership of the systems, then from preference, then from what each move costs the person. Check for the quiet damage: the only person who knows a system landing on a team that no longer owns it, a pairing that gets split, a manager given fewer reports than their level assumed, a part-time or remote person left on the edge.

Write down, for each person whose role, manager or team changes, what they would reasonably ask, so the 1:1 in step 6 has answers.

### 5. Decide in a small group, with a leak plan

Before the decision is final or any date is set, check with HR, and legal where needed, whether consultation duties apply: collective consultation on redundancies, works-council consultation in parts of the EU, and changes to contract terms or reporting lines can all make a decide-and-announce-within-days timeline unlawful. Fit the plan below inside what they confirm.

Keep the deciding group to the people who must agree and the managers who must brief, usually four to six. Write the leak plan before the decision: the date of the announcement, what each person in the group says if asked (a prepared holding line that is true, such as "we are looking at how the team is organised and will say more on Thursday"), and what happens if the news escapes early (the announcement moves forward, not backward).

Keep the window between decision and announcement to days. Every extra day adds exposure and nothing else, since the content of the announcement does not improve with waiting.

If rumours have already started, do not deny them. Say that a decision is being made, when people will hear, and who will tell them. A denial that turns out false costs more than the leak.

### 6. Communicate in strict order

The order is fixed, because people judge the reorg by how they heard of it.

1. The affected managers, together, with the full design and the talking points, and time to ask questions.
2. Each affected individual, in a 1:1 with their own manager, before any group message. People whose manager changes also meet the new manager early.
3. The affected teams, together, the same day or the next morning.
4. Everyone else (adjacent teams, stakeholders, the wider organisation).

Hold steps 2 to 4 inside one working day where possible, so nobody carries private knowledge overnight. A person who learns about their own move from a channel post or a colleague will remember that long after the structure has settled. `references/announcement-template.md` has the 1:1 script, the manager briefing and the written announcement.

### 7. Write the announcement

It carries five things, in this order: what is changing, what is not changing (reporting lines, locations, compensation, the product roadmap, whichever apply), why (the cost from step 1, in a sentence with the number), who decides the open questions and by when, and the date the new structure takes effect. Open questions are named as open. Do not fill them with guesses, since a guess that is later reversed reads as a broken promise.

### 8. Write the reversal criterion and hold the review

Before the announcement goes out, write down what would make you undo or amend the design. Tie it to the step 1 measure: for example, cross-team handoffs per project not below the stated target, or regretted attrition in the affected teams above the pre-change baseline by a stated margin.

Put a 90-day review on the calendar with a named owner. Recount the same handoff measure the same way, and add regretted attrition in the affected teams, delivery rate (work completed per week against the earlier baseline) and a short written pulse from each team lead. Expect delivery to dip in the first weeks; decide in advance how large a dip is acceptable so that the review judges the result, not the discomfort. Hold the review even if it feels fine, and publish the outcome to the people affected.

## Hand back

A one-page design record: the problem with its number, the candidates and the crossing counts, the chosen structure, the people assignments (kept separate and restricted), the leak plan, the communication sequence with dates, the announcement draft, the reversal criterion, and the 90-day review date and owner.

## Anti-patterns

**Boxes first.** The structure is drawn, then a problem is found to justify it. Without a prior measure the review has nothing to compare against.

**Designing around the people.** The roster shapes the diagram, so the new boundaries reproduce the old ones with different labels.

**A long window before the announcement.** The decision is made, then held for a month while approvals complete. Every day of it is a day of rumour.

**Announcing to the group first.** Individuals find out their own change in front of colleagues. The 1:1 comes first, always.

**Promising stability that cannot be kept.** "No further changes" in the announcement, followed by a correction three months later, ends trust in the next announcement.

**No reversal criterion.** The change becomes permanent by default, and a design that is not working is defended because undoing it would admit an error.

## Reference files

- `references/boundary-evidence.md` — read at step 1 and step 3: how to count cross-team handoffs, ownership overlap and queue wait from existing data, and how to run the project test.
- `references/announcement-template.md` — read at step 6 and step 7: the manager briefing, the 1:1 script, the written announcement, and the 90-day review agenda.
