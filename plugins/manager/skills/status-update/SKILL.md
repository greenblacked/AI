---
name: status-update
description: "Write weekly team status, executive updates and stakeholder comms that lead with the answer — BLUF (status flag, bottom line, ask, by when, since last, next, risks) for reporting, SCQA for persuasion, and never the two mixed. Enforces the discipline that makes an update trustworthy: no invented numbers, every impact claim linked to a dashboard or ticket, honest RAG status, one screen of length, and no people-performance content in a shared artefact. Use this skill whenever the user wants to write, tighten or review a status report, weekly update, project update, exec summary, steering-committee note, stakeholder email, programme roll-up or leadership briefing — including casual phrasings like \"send an update on the migration\", \"what do I tell the CTO\", or \"make this shorter for leadership\". Do not use it for architecture decision records or design docs, or for performance feedback about a named person."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Status Update

A good update answers three questions in the first three lines: are we on track, what could go wrong, and what do you need from the reader. Everything after that is supporting evidence for someone who wants it.

The job is hard because the natural way to write an update is chronological and activity-shaped — what the team did, in the order they did it — and the reader needs the opposite. Worse, an assistant asked to write one will happily produce fluent prose with invented percentages, a green status nobody verified, and an ask buried in paragraph four. That version reads well and is unfalsifiable, which is precisely why it is dangerous: the first time a number is checked and does not hold, every future update from the same author is discounted. So the agent's job here is to impose structure and demand evidence, not to generate content. Where a fact is missing, leave the hole visible.

## Scope

Use for: weekly team status, exec and leadership updates, stakeholder comms, programme roll-ups, steering notes, and tightening or reviewing an existing draft.

Do not use for: decision records and design docs (that is the `decision-record` skill), incident comms during an active incident, or feedback about a named individual. Performance content does not go into an artefact with a distribution list; it goes into a one-to-one.

## Non-negotiables

**Never invent a number.** If a metric, date, name or figure was not supplied, write `[TK: deploys per week, from the DORA dashboard]` and leave it. An update is a credibility instrument; an un-sourced number spends credibility the author will need later.

**Label the type in the first line.** Status, decision, recommendation, or FYI. Executives triage by type before they read; ambiguity about which one this is, is the most common defect in writing aimed at them, and the cost is a round trip.

**Every impact claim carries a named source.** A dashboard link, a ticket, a document. "Reduced onboarding time by half" without a link is a mood.

**Nothing about a named individual's performance.** "The integration slipped two weeks" is a project fact. "It slipped because X was slow" is a performance conversation that has escaped into a forwardable document.

**State reversibility when you are asking for a decision.** A cheap, reversible call deserves a fast timebox and one line, not a review cycle. Saying "this is reversible; if we are wrong we lose two days" is often what unblocks a decision in the meeting.

## Workflow

### 1. Decide which form this is

| The reader needs to | Form | Structure |
| --- | --- | --- |
| Know where things stand | Status | BLUF |
| Approve, fund, or choose | Recommendation | SCQA |
| Be aware, no action | FYI | BLUF, ask = none |
| Both — status and a pitch | Two artefacts | Do not merge them |

Mixing them is the standard failure. A status report that turns into an argument halfway through makes the reader re-read to work out whether they are being informed or sold to, and both jobs fail. If the update contains a genuine pitch, send the status and take the recommendation to its own note or slot.

### 2. Interrogate before drafting

Ask in one batch: what actually changed since last time and where is that visible; what is the single ask, or is there none; what is the date and what happens if it slips; what are the two live risks and who owns each; what is the honest RAG and what would have to be true for it to be green. `references/question-bank.md` has the follow-ups that break vague answers.

Every number the human offers without a link gets one follow-up asking where it is measured. After that, place a `[TK]` rather than pushing again.

### 3. Fill the BLUF template

```markdown
[GREEN | AMBER | RED] · [DECISION NEEDED | FYI] · [Project] · [Date]

**Bottom line:** [One sentence: the outcome, the ask, and the date. If a reader stops
here, they have the whole message.]

**Ask:** [The one decision or resource needed, with who has to give it. Or "None."]

**By when:** [Date] — [what happens if it slips: cost, dependency, or knock-on date]

**Since last:**
- [Outcome, with a number and a link]
- [Outcome, with a number and a link]
- [2-4 bullets, no more. Outcomes, not activity.]

**Next:**
- [Deliverable — owner — date]
- [Deliverable — owner — date]

**Risks:**
- [Risk — mitigation — owner]
- [Risk — mitigation — owner]
- [Top two only. If genuinely green: "None material."]
```

Rules the template does not enforce on its own: bullets under **Since last** describe what is now true, not what the team did — "checkout p95 down to 240ms ([dashboard])" rather than "worked on latency". Each **Next** bullet has a named owner and a real date; "ongoing" is not a date. **Risks** on a green project says "none material" rather than padding with two invented worries, because padded risk sections train the reader to skip the section that matters when it is real.

`assets/bluf-template.md` is the copyable version.

### 4. For a persuasive update, use SCQA

Minto's structure, in order:

- **Situation** — stable context the reader already agrees with. One or two sentences. If they could argue with it, it is not situation.
- **Complication** — what changed and why the situation no longer holds. This is the engine of the whole document.
- **Question** — the question the complication raises. Usually left implicit; write it out only when the reader might frame it differently than you do.
- **Answer** — the recommendation first, then the supporting arguments grouped so they do not overlap and together cover the case. Each group is itself answer-first.

The discipline that makes SCQA work is that no supporting argument appears before the recommendation. If the reader has to assemble the conclusion themselves, half of them will assemble a different one. `assets/scqa-template.md` has the fill-in form and a worked example.

### 5. Cut to length

An exec update that does not fit on one screen will be skimmed, and skimming reads the first three lines. So the first three lines have to carry the entire message — treat everything below them as optional detail that a curious reader may open.

Practical cuts, in the order to make them: remove activity that produced no outcome; collapse anything the reader cannot act on into a single line; move detail into a linked appendix rather than deleting it; drop adjectives on numbers, since the number is the argument. Aim for 150-200 words for an exec update, one page for a weekly team status.

Length is a proxy for thinking. A three-page update usually means the author has not decided what matters.

### 6. Set the RAG status honestly

| Status | Means | Requires |
| --- | --- | --- |
| Green | On track; no help needed | Nothing |
| Amber | At risk; a specific thing must change | The specific thing, an owner, a date |
| Red | Will miss unless scope, date or resource moves | The ask, and the date it must land by |

A project that is green until the week it goes red was never really green — the status was a mood, not information. Amber is information, not failure; it is the mechanism by which a reader can still help. Once a team learns that amber triggers an interrogation, every project stays green until it cannot, and the reporting system stops working.

Test each green: what would have to be true for this to be amber, and do I know it is not? If the answer requires a number nobody has, the status is amber with a `[TK]` attached.

### 7. One set of facts, three audiences

The same underlying facts, re-cut for what each reader can act on — never a different set of facts. Contradictory versions surface in the same meeting eventually, and that is unrecoverable.

- **Team**: detail and mechanism. What is blocked, who owns what, what changed in the plan.
- **Peer leaders**: interfaces and dependencies. What you need from them, what you owe them, what has moved on the shared timeline.
- **Executives**: outcome, risk, ask. Three lines, then supporting detail.

`references/audience-variants.md` has one week's facts written all three ways, plus the translation rules.

## Anti-patterns

**Leading with activity.** "We held four workshops and closed 23 tickets" reports effort. The reader wants the outcome and the ask; effort is only interesting when it explains a variance.

**The buried ask.** A decision request in paragraph four gets read after the decision window closed. If there is an ask, it goes in the first two lines and it names who must act.

**Green until red.** Covered above, and worth repeating because it is the most expensive habit in status reporting: it removes the reader's only opportunity to help.

**Padded risks.** Two invented risks on a healthy project teach the reader that the risk section is filler, so the real one gets skipped.

**Unsourced numbers.** "Improved throughput by 30%" with no link is the sentence that gets checked in the one meeting where it matters.

**Adjectives doing a number's job.** "Significant progress", "substantially improved", "much faster". Either the number exists and belongs in the sentence, or it does not and a `[TK]` belongs there.

**Status and pitch in one document.** The reader cannot tell whether they are being informed or sold to, so they do neither.

**A framework laundering a judgement call.** A weighted score assembled after the decision, or a RAG derived from a formula nobody believes. If it was judgement, say so and name whose.

**People-performance content in a shared update.** It is forwardable, permanent, and it converts a project report into an HR artefact.

## Reference files

- `references/question-bank.md` — read before drafting: what to ask the human, the follow-ups that break vague answers, and how to turn a non-answer into a useful `[TK]`.
- `references/audience-variants.md` — read when the same update goes to more than one audience: one week's facts written for team, peer leaders and executives, with the rules for re-cutting without changing the facts.

## Assets

- `assets/bluf-template.md` — the copyable BLUF status template with fill-in guidance.
- `assets/scqa-template.md` — the SCQA recommendation template and a worked example.
