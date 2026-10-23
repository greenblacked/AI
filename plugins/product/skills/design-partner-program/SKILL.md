---
name: design-partner-program
description: "Run a small cohort of design partners or a customer advisory board that shapes the product without capturing it. Choose five to eight partners for fit to one segment, not logo size; write the give-get (a weekly 30-minute session, real data, a reference at the end, for early access and visible influence); keep a fixed cadence and a shared decision log of what changed because of them; remove a partner after two missed sessions; at the end convert, keep as a reference, or release each one, never leaving them drifting. Use when someone wants to find design partners, set up a customer advisory board, run an early-access cohort, or fix a partner programme gone quiet. Not for a one-off usability study (usability-test-plan), checking whether a problem exists (problem-validation), delivering a service by hand (concierge-mvp), or sorting partner feature asks (request-triage)."
allowed-tools: Read, Glob, Grep
---

# Design Partner Programme

Done means five to eight partners from one segment, each with a written give-get both sides signed, a calendar of sessions that runs on time, a decision log the partners can read that shows what changed because of them, an attendance rule that was applied, and a recorded end state for every partner: converted, kept as a reference, or released.

The usual failure is a programme built from logos. The biggest names are recruited because they look good on a slide, they bring custom requirements nobody else shares, their procurement takes a quarter, and their senior sponsor stops attending by week four. The roadmap bends toward one account, the rest drift, and at the end nobody knows whether any partner is a customer. The second failure is influence that is promised but never shown: partners who cannot see what their time changed stop giving it.

## Scope

Use for: recruiting and running a cohort of design partners who co-design a product or major feature; running a customer advisory board on strategy; repairing a partner programme that has stalled; ending one cleanly.

Do not use for: a one-off study watching people use a prototype, which is `usability-test-plan`; finding out whether a problem exists before anything is built, which is `problem-validation`; serving early customers by hand, which is `concierge-mvp`; deciding what to do with the feature requests partners raise, which is `request-triage`.

## Workflow

### 1. Name the segment, the question and the format

Write one segment ("finance teams of 20 to 200 people closing monthly on spreadsheets"), the question the programme answers ("which workflow do we build first, and does it hold up on real data"), and the term (a fixed number of weeks, commonly a quarter or two). Then pick the format:

| Format | Who attends | Cadence | Use it for |
| --- | --- | --- | --- |
| Design partners | The people who do the job | Weekly, 30 minutes each | Building the product with them on their data |
| Customer advisory board | Senior buyers and leaders | Quarterly group sessions | Direction, priorities, market view |

Running one group as both produces sessions too senior for detail and too detailed for strategy.

### 2. Select for fit, not size

Score candidates against the segment, not their brand:

- Has the problem now and acutely, with a recent example.
- Is in the segment on size, industry and tools.
- Has a named person with time, and a sponsor who agrees to the give-get.
- Will use real data or a real environment, not a demo account.
- Can buy at the end: budget exists or can be found.

Take five to eight. Fewer and one partner's quirks look like a pattern; more and the team cannot keep a weekly cadence with each. No single partner should be large enough that losing them ends the programme. The scorecard is in `references/programme-kit.md`.

### 3. Write the give-get and have both sides sign it

| The partner gives | You give |
| --- | --- |
| A weekly 30-minute session with the person who does the job | Early access to builds before anyone else |
| Real data or a real environment for testing | Influence, shown in the decision log |
| Feedback on each build within an agreed number of days | A direct line to the product team |
| A reference or case study at the end if the product meets the agreed outcome | Pricing at conversion, agreed now and written down |

Write what you do not give: roadmap commitments, custom features, exclusivity, or a date. A partner told "we'll build that for you" has been sold a consulting contract.

Put data access, confidentiality and pre-release terms in a written agreement reviewed by your legal team. This skill describes procedure, not legal advice.

### 4. Fix the cadence before the first session

Book every session for the whole term on day one, at the same weekday and time per partner. Give each partner one owner on your side who attends every session. A cadence negotiated week by week is the first thing a busy partner drops.

### 5. Run sessions on their data and their last real occasion

Each session: what changed since last time (from the log), the build or prototype on their data, and questions about the last time they did the job. Ask what they did, not whether they would use something. Notes go into one shared place the same day, tagged by partner and theme. When a partner asks for a feature, record the job behind it and the partner in the request queue rather than promising anything in the room.

### 6. Keep a decision log the partners can see

One row per decision: date, what changed or was decided not to change, which partners' input drove it, and a link to the evidence. Share it with partners every month. It is the influence half of the give-get made visible; without it, partners see their time disappear and stop attending.

Watch the log for capture. If most changes trace to one partner, check each against the others: a need shared by one of seven is that partner's need, not the segment's.

### 7. Apply the attendance rule

Warn the sponsor at the first missed session that is not rescheduled, so the rule is no surprise. At the second, remove the partner: tell the sponsor why, close the partnership as a release under step 8, and replace them from the waiting list of scored candidates. Why it matters: the programme's findings come from whoever shows up, so a partner who drifts silently skews the sample toward the most available, and the team keeps preparing for sessions that do not happen.

### 8. End every partnership deliberately

At the end of the term, each partner leaves in one of three states:

- **Convert**: a paid contract on the terms agreed in step 3.
- **Keep as a reference**: case study, reference calls or a quote, as agreed.
- **Release**: a written thank-you, what changed because of them, and the return or deletion of their data under the agreement.

Record the state and the date for each. A partner left without an end state keeps using an unsupported pre-release build and remembers the programme as the time you stopped calling.

## Output

```markdown
## Programme
[Segment, question, format, term, dates.]

## Partners
[Per partner: scorecard result, owner, give-get signed date, attendance, end state.]

## Decision log
[Date, change, partners whose input drove it, evidence link.]

## Findings
[What the programme answered, with how many partners each finding rests on.]

## End states
[Converted, references, released, with dates.]
```

## Anti-patterns

**Recruiting by logo.** Large brands bring custom asks and slow procurement. Select on segment fit and a named person with time.

**Promising features to keep partners engaged.** A promise in a session becomes a roadmap commitment nobody approved. Record the job and route it through the request queue.

**Influence nobody can see.** Without a shared decision log, partners cannot tell their time mattered. Show the log monthly.

**Letting the programme fade out.** No end state means no conversions and no references. Close each partnership on a date.

## Reference files

- `references/programme-kit.md` — read when recruiting and at the end of the term: the selection scorecard, a give-get agreement outline, the session agenda, the decision log template, and the exit checklist for each end state.
