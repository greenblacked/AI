---
name: jobs-timeline-interview
description: "Reconstruct why recent buyers or switchers chose your product, from first thought to first use, so positioning and roadmap rest on what happened rather than on opinions. Interview only people who bought or switched in the last 90 days; walk the timeline (first thought, passive looking, active looking, deciding, first use) asking for the day, the place and who was there; code the four forces (push, pull, anxiety, habit), each with a verbatim quote, into a force table across six or more interviews. Use when someone asks \"why did customers switch to us\", wants to interview new customers, run a switch or jobs-to-be-done interview, or find what really triggered a purchase. Not for testing whether a problem exists before anyone has bought (problem-validation), watching people use a prototype (usability-test-plan), or finding what customers would pay (pricing-research)."
allowed-tools: Read, Glob, Grep
---

# Jobs Timeline Interview

Done means a force table built from at least six interviews with people who bought or switched in the last 90 days, where every push, pull, anxiety and habit is backed by a verbatim quote tied to a dated moment in that person's timeline, and each finding points at a decision it changes.

The usual failure is asking customers why they bought. People answer with a tidy story assembled afterwards, usually echoing your own marketing: the feature list, the price, "it was easier". The real cause sits earlier and is more mundane, such as a missed deadline, a new boss or a spreadsheet that broke at month end, and it only surfaces when you ask what happened on a particular day. The second failure is interviewing long-time fans, whose memory of the switch has been rewritten by years of use.

## Scope

Use for: understanding what triggers a purchase or a switch, what nearly stopped it, and what the product was hired to replace; feeding positioning, targeting, onboarding and migration work from real buying stories.

Do not use for: testing whether a problem exists before anyone has bought, which is `problem-validation`; watching people attempt tasks in a prototype, which is `usability-test-plan`; setting a price, which is `pricing-research`; sorting incoming feature asks, which is `request-triage`.

## Workflow

### 1. Write down the decision the interviews feed

Name the decision before recruiting: which segment to target, what the homepage leads with, what onboarding must remove, whether to build an importer. Write what finding would change it. Interviews run without a decision produce a deck of quotes that nobody acts on.

### 2. Recruit recent switchers, not fans

Pull the list from billing or the CRM by first paid date, not from the account team's favourites.

- Include only people whose purchase or switch happened in the last 90 days. Past that, recall of the timeline degrades and the marketing story replaces it.
- Talk to the person who made the switch happen, the one who searched, compared and pushed it through. If a user who did not choose it is easier to reach, they answer a different question.
- Mix what they switched from: a competitor, a spreadsheet or manual process, and nothing at all. Each origin produces different habits and anxieties.
- Where you can, add people who trialled and then chose something else. They are where anxiety and habit show most clearly.
- Exclude friends, advisers, staff and anyone sales picked for being positive.

Plan six to ten interviews. Do not stop before six; stop after that once two consecutive interviews add no new force theme. Offer an incentive that does not depend on what they say, and get consent to record and to keep notes, with the right to stop at any point. Recording-consent rules vary by jurisdiction, so check them; this is procedure, not legal advice.

### 3. Run the session as a documentary, not a survey

Forty-five to sixty minutes, two interviewers: one asks, one notes timestamps and quotes. Open by saying there are no right answers and you want the story of how they came to buy, in as much detail as they can remember, including the boring parts.

Anchor on the moment of purchase first, because it is the most memorable point. Then jump back to the first thought and walk forward through the stages in order:

| Stage | What you are after |
| --- | --- |
| First thought | The struggling moment: what happened that made the old way feel not good enough |
| Passive looking | Noticing alternatives without acting: what they saw, heard or were told |
| Active looking | The event that turned noticing into searching; what they compared; time and money spent looking |
| Deciding | What tipped it, who else had to agree, what nearly stopped it |
| First use | The first real use, what they expected, what surprised them, what they did with the old tool |

At every stage, ask for the day, the place, who was there, what they were using and what happened just before. "What day of the week was that?" and "Where were you sitting?" are not small talk; concrete context pulls the real memory out and exposes a rationalised story when the details will not come.

Rules that keep it honest:

- Do not ask "why did you choose us". Ask what happened, then what happened next.
- When they generalise ("we always", "people like us"), bring them back to that one occasion.
- No hypotheticals and no opinions on features. "Would you use" tells you nothing about what they did.
- Play their words back exactly and let silence run. The useful sentence usually comes after a pause.
- Probe contrast: "What else did you look at?", "What nearly stopped you?", "What did you have to give up?"

The question bank by stage, the opening script and the note template are in `references/interview-guide.md`; read it before the first interview.

### 4. Write the timeline and forces within 24 hours

From the recording, not from memory, write each interview up the same or next day:

1. The timeline: dated events from first thought to first use, with the elapsed time between them.
2. The four forces, each with a verbatim quote and its timestamp:
   - **Push** of the current situation: what was going wrong.
   - **Pull** of the new solution: what they imagined life would be like.
   - **Anxiety** about the new: what they feared would go wrong by switching.
   - **Habit** of the present: what kept them on the old way, including "it was good enough".
3. The alternatives they considered, including doing nothing.

A force with no quote is your interpretation, not data; mark it so or drop it. Deidentify: replace names with an interview id and a role, and keep only the context the decision needs.

### 5. Build the force table across interviews

One row per interview, columns for the first-thought trigger, push, pull, anxiety, habit, alternatives and the deciding event. Then cluster each column into themes and count interviews per theme. Report counts as "5 of 8", never as percentages; with eight interviews a percentage claims a precision the sample does not have. A theme seen once is a lead to check in the next interviews, not a finding.

The table layout and coding rules are in `references/interview-guide.md`.

### 6. Turn forces into decisions

Map each strong theme to the lever it moves:

| Force | Lever |
| --- | --- |
| Push | Targeting and messaging: find people at that struggling moment and name it in their words |
| Pull | What the homepage, demo and sales pitch lead with |
| Anxiety | Onboarding, guarantees, trials, proof, migration support |
| Habit | Import tools, templates, integration with the old tool, the cost of switching back |

Every recommendation cites the interview ids behind it. Return to the decision from step 1 and say whether the evidence changes it.

## Output

Hand back:

```markdown
## Decision this feeds
[The decision and what would have changed it.]

## Sample
[Count, recruitment source, switch dates, what they switched from, who was excluded and why.]

## Force table
[One row per interview; then themes with counts, each with one representative quote.]

## Timelines
[The most typical timeline and the most unusual one, with elapsed times.]

## Recommendations
[Each tied to a force theme and the interview ids behind it.]

## Limits
[Segments missing, interviews that were thin, themes seen only once.]
```

## Anti-patterns

**Interviewing the champions.** Long-time advocates tell the story the product team wants to hear. Recruit by first paid date.

**Collecting feature requests.** A switch interview that drifts into "what should we build" has stopped measuring what happened. Note the request, move on, and send it to `request-triage`.

**Coding forces from memory.** Summaries written days later drift toward the interviewer's own hypothesis. Code from the recording, with timestamps.

**Ignoring anxiety and habit.** Teams act on push and pull because they suggest features. The forces against switching usually explain lost trials better, and they are cheaper to fix.

## Reference files

- `references/interview-guide.md` — read before the first interview and again when coding: the opening script, questions for each stage, probing moves, the per-interview note template, and the force table with its coding rules.
