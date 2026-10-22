---
name: inherited-team-audit
description: "Run the first 30 days of taking over an existing team or a departing manager's reports — change nothing structural and say so on day one, hold a 1:1 with every report using the same five written questions, read two quarters of postmortems, review comments and plans, sit with upstream and downstream teams, then write a one-page findings memo separating inherited commitments, risks and preferences, share it before acting, and pick at most two changes with an owner, a date and a visible win by day 60. Use for \"I just became manager of this team\", \"I inherited a team from a departing lead\", \"what should I change first in my new org\", \"my predecessor left a mess\". Not for a new engineer's start (onboarding-plan), individual performance (growth-review), the meeting system you may install later (design-team-cadence), metrics-based rhythm assessment (delivery-review), or reading the code you inherited (codebase-orientation)."
allowed-tools: Read, Grep, Glob
---

# Inherited Team Audit

A takeover is done well when, at day 30, every report has been heard on the same questions, you can name what you inherited in three separate kinds, the team has seen your findings before you act on them, and no more than two changes are under way.

The usual failure is acting early to show leadership. The new manager sees something wrong in week one, fixes it, and discovers in week six that it was a deliberate compromise with another team. The second failure is silence: a new manager who observes without speaking leaves the team to guess, and people read a lack of statements as either approval or a coming purge. Both are avoided by saying on day one what you are doing and for how long.

## Scope

Use for: taking over a team from a departing or promoted manager; inheriting reports after a reorganisation; stepping into an existing group from outside; deciding what to change first.

Do not use for: a new engineer's first weeks (`onboarding-plan`); judging one person's performance (`growth-review`); installing the meeting system (`design-team-cadence`); assessing delivery with metrics (`delivery-review`); or reading the code the team owns (`codebase-orientation`).

## Workflow

### 1. Day one: announce the freeze

Tell the team in writing and in person: for the first 30 days you will change nothing structural (no reporting lines, ownership, priorities, process or rituals), you will listen, and you will share what you learn before you act on it. Name the date of the findings memo. Handle urgent operational problems as they arise, and say that exception too.

The statement matters because silence is read as a message. Without it, people interpret the absence of change as approval, and the first change as a break from it.

### 2. Hold a 1:1 with every report

Hold one with every person, within the first two weeks, using the same five questions, written down and sent in advance so people can think:

1. What is working well that I should not break?
2. What is broken or slowing you down?
3. What would you stop doing if you could?
4. What do you need from me?
5. Is there a promise, arrangement or deadline I may not know about?

Fix the wording across everyone. Answers from different people are only comparable if the questions were the same. Take notes during the meeting and send the person a short summary of what you heard so they can correct it. `references/one-to-one-questions.md` has the follow-up prompts and a note template.

Also meet the people the team's reports have asked you to meet, and any skip-level reports if the structure has them. Do not ask people to compare colleagues.

### 3. Read the record

Read the last two quarters of postmortems, code or design review comments, plan documents, roadmaps and the previous manager's handover notes if any. These show what the team commits to, what has gone wrong repeatedly, and what the team argues about. Note patterns, not people: a recurring failure that appears in three postmortems matters more than the worst single one.

Do not treat the handover note as complete. A departing manager records what they remember, which excludes what they stopped noticing.

### 4. Meet the neighbours

Sit with the team's upstream (who feeds it work, who it depends on) and downstream (who relies on it) groups. Ask each what they get from the team, what they wish were different and what has been promised to them. Neighbours often hold commitments the team has forgotten, and the best account of the team's reputation.

### 5. Write the findings memo

One page, in three sections that must stay separate, since each calls for a different response. `references/findings-memo.md` has the template and examples.

- **Inherited commitments.** Promises already made to others: dates, support levels, interfaces, hiring offers, favours. Honour them, or renegotiate them explicitly with the other party. Do not quietly drop one.
- **Inherited risks.** Single points of failure (one person who understands a system), unowned systems, expiring certificates or contracts. Each gets an owner and a decision date, even if the decision is to accept it. The shared memo never carries unaddressed performance problems; step 6 says where they go.
- **Inherited preferences.** How things were done: meeting habits, branch strategy, tooling, naming. These are yours to change or keep. Do not treat them as problems because they differ from the last team you led.

Write what you saw and the evidence, and mark what you do not yet know. A memo that is certain about everything after thirty days is overconfident.

### 6. Share it before acting

Share the memo with the team before making any change. Walk through it, ask what is wrong or missing, and amend it. This gives the team a chance to correct misreadings (the cost of which is highest early), and shows that the freeze produced something. Share a version with your manager as well, since they may hold context on risks or commitments you cannot see.

Keep performance problems out of the shared memo entirely. Put them in a separate private note seen only by you and your manager, and handle them with `performance-improvement-plan` or `difficult-conversation` as the case requires. On a small team even an unnamed concern identifies the person.

### 7. Choose at most two changes

From the memo pick at most two changes. Choose by effect and evidence: one the team asked for in the 1:1s and one that reduces an inherited risk is a good pair. For each, write the owner, the date, what will be different, and a first visible win by day 60, something the team can see without being told.

Say what you chose and what you are deliberately not changing yet. A list of changes you left alone, and why, is part of what makes the next ones believable. Review progress at day 60 and day 90.

## Hand back

A day-one message, the five questions and the notes from each 1:1, the one-page memo, the shared version, the two changes with owners, dates and day-60 wins, and the list of things deliberately left alone.

## Anti-patterns

**Fixing something in week one.** The change meets the first problem you see, which is often someone else's deliberate trade-off. Wait until you can tell the difference.

**Different questions for different people.** The answers cannot be compared, and people notice who got asked what.

**Mixing commitments, risks and preferences.** A preference gets defended like a promise, or a risk gets dismissed as "how they did it".

**Disparaging the predecessor.** Even a justified criticism makes the team defend the previous manager and you. Describe the state, not the person.

**Changing five things at day 31.** The team cannot absorb that many, and none of them gets a visible win.

**Hiding the memo.** Findings kept private make the team feel assessed instead of consulted.

## Reference files

- `references/one-to-one-questions.md` — read before the first 1:1: the five questions with follow-up prompts, how to run the meeting and a note template.
- `references/findings-memo.md` — read at step 5 and step 7: the one-page memo template with the three sections, what to record under each, and how to choose and write the two changes.
