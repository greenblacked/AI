---
name: decision-record
description: "Produce architecture decision records (MADR 4.x ADRs) and longer design docs / RFCs, choosing between them by stakes and reversibility, and enforcing the structure that makes a decision auditable a year later: labelled artefact type, at least two genuinely considered options with the reason each was rejected, a stated reversibility, sourced impact claims, and a Confirmation section that names a test, fitness function or dashboard. Use this skill whenever the user wants to write, review or supersede an ADR, decision record, design doc, RFC, technical proposal or architecture memo — including casual phrasings like \"write this decision up\", \"we picked Postgres, document it\", \"draft an RFC for the new pipeline\", or \"is this design doc any good\". Do not use it for status reports, project updates or stakeholder comms, and do not use it for anything about a named individual's performance."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Decision Record

A good decision record lets a stranger — or you, eighteen months later — reconstruct what was decided, what was rejected and why, and how anyone would know if it turned out to be wrong. Everything else in the document is decoration.

The job is hard because the failure mode is invisible. Management writing produced with an assistant comes out plausible, well-formatted and unfalsifiable: confident percentages nobody measured, "significant improvement in developer velocity", a scoring table that launders a gut call into arithmetic. It reads better than the honest version and is worth less than nothing, because it spends credibility that gets billed later. So the working assumption of this skill is that the agent supplies structure and pressure, and the human supplies facts. Do not generate content to fill a section. Interrogate for it, and if it is not there, leave the hole visible.

## Scope

Use for: ADRs, design documents, RFCs, technical proposals, decision memos, and reviews or supersessions of any of those.

Do not use for: status reports and stakeholder updates (that is the `status-update` skill), incident write-ups, or anything discussing a named individual's performance — that belongs in a private one-to-one note, not a shared artefact, no matter how relevant it feels to the decision.

## Non-negotiables

These five hold for every artefact this skill produces.

**Never invent a number.** If a metric, date, cost, name or figure was not supplied by the human, write a literal `[TK: p95 latency today]` placeholder and move on. A `[TK]` is a two-minute task for the author. An invented figure is a credibility loss with a long fuse — someone will check it in a review, and everything else in the document becomes suspect at that moment.

**Label the type in the first line.** Decision, recommendation, status, or FYI. Readers senior enough to matter are triaging; ambiguity about which of the four they are holding is the single most common defect in writing aimed at executives, and it costs a round trip every time.

**Every impact claim needs a named source.** A dashboard link, a ticket, a benchmark run, a document. "Cuts build time by 40%" without a link is an opinion wearing a number's clothes.

**Nothing about a named individual's performance goes into a shared artefact.** "The service was under-maintained" is a fact about a system. "X did not maintain it" is a performance conversation that has escaped into a document with a permalink.

**State reversibility.** Cheap and reversible (type-2) decisions get a lightweight record and a fast timebox; expensive and one-way (type-1) decisions earn the full treatment. Running a design review on a reversible decision is theatre, and it teaches the team that the process is ceremonial.

## Workflow

### 1. Classify the decision before choosing a format

| Signal | Classification | Action |
| --- | --- | --- |
| Undo costs hours or days; blast radius is one team | Type-2, reversible | Minimal ADR, decide inside a stated timebox, skip the review |
| Undo costs weeks; touches data, contracts or public APIs | Type-1, one-way | Full ADR, named consulted parties |
| Multi-team, multi-quarter, or a new subsystem | Type-1 with design surface | Design doc, then an ADR per irreversible choice |
| The team already agrees | Any | Minimal ADR — do not manufacture a debate |
| Real disagreement between named people | Any | Full ADR with pros and cons per option |

Write the classification into the document. "This is a reversible choice; we will revisit it after [TK: date] if [TK: signal] does not appear" is a legitimate and complete decision outcome.

### 2. Interrogate before drafting

Ask in one batch, not one question at a time. The minimum set: what problem forced the decision now, what else was seriously considered and why each was dropped, what the decision costs in the bad case, who has to live with it, and how we would find out it was wrong. `references/interrogation.md` has the per-section question bank and the follow-ups that catch a vague answer.

If the human cannot answer "what would make us reverse this", that is worth surfacing before writing anything — it usually means the decision has not actually been made.

### 3. Choose the format

| Situation | Format |
| --- | --- |
| A single choice with a clear winner | Minimal ADR — 4 sections |
| A single choice with live disagreement or a costly loser | Full MADR ADR |
| A system, a migration, or several coupled choices | Design doc, plus an ADR for each one-way door inside it |
| The audience is non-technical and the ask is funding | PR/FAQ six-pager (see `references/design-doc.md`) |

The minimal ADR fits roughly 80% of decisions. Reach for the full form when there is genuine disagreement to record, not to look thorough.

### 4. Write the ADR

Filename: `docs/decisions/NNNN-title-with-dashes.md`, four-digit sequence, lowercase title.

Optional YAML frontmatter, all keys optional:

```yaml
status: proposed | rejected | accepted | deprecated | superseded by ADR-0012
date: 2026-08-04
decision-makers: [names]
consulted: [names or teams]
informed: [names or teams]
```

MADR 4.x section order:

- `## Context and Problem Statement` — the forcing function, in two or three sentences. Why now.
- `## Decision Drivers` — the constraints that actually discriminate between options. Drop any driver that every option satisfies equally; it is not a driver.
- `## Considered Options` — a flat list, two minimum.
- `## Decision Outcome` — "Chosen option: X, because …". One sentence tying back to the drivers.
  - `### Consequences` — good / bad / neutral bullets. A record with no bad consequences has not been thought about.
  - `### Confirmation` — how compliance and correctness get checked.
- `## Pros and Cons of the Options` — per option, in the full form only.
- `## More Information` — links, related ADRs, the supersession trail.

The minimal variant keeps Context and Problem Statement, Considered Options, Decision Outcome, Consequences.

Copy `assets/adr-template.md` for the full form or `assets/adr-template-minimal.md` for the short one, then fill it. Do not retype the structure from memory.

### 5. Enforce the three rules teams break

**At least two options, each with the reason it was rejected.** A record naming one option is a rationalisation with a filename. If the human offers only one, ask what the do-nothing option costs — that is always available and is frequently the honest runner-up.

**Confirmation must name a mechanism.** A fitness function, an automated test, an architecture lint rule, a dashboard panel, or a scheduled review with a named owner and date. "We will review this later" is where every team cheats, and it is how an ADR becomes archaeology. If no mechanism exists, write `Confirmation: [TK: no verification mechanism agreed]` and let that be visible.

**An accepted ADR is immutable.** Fixing typos is fine; changing the decision is not. To change it, write a new record, set the old one's status to `superseded by ADR-NNNN`, and link back from the new record to the old. The value of the corpus is that it shows how thinking changed over time; editing history destroys exactly that.

### 6. Design docs

For anything with a design surface rather than a single choice, use the Google design-doc shape: context and scope, goals and non-goals, the design itself organised around trade-offs, cross-cutting concerns, alternatives considered with rejection reasons, rollout and rollback, open questions. `references/design-doc.md` has the full section-by-section brief, the degree-of-constraint question, the honest lifecycle, and the RFC and PR/FAQ alternates. Read it before drafting one.

Two things carry most of the value and are the two most often skipped: **non-goals**, which is what stops scope creep six weeks in, and **alternatives considered with the reason each was rejected** — a design doc with no rejected alternatives has not made a decision, it has described a plan.

## Tooling

`adr-tools` gives you `adr new "Use Postgres for the event store"` and `adr new -s 9 "..."` to create a record that supersedes number 9, wiring the status and back-link automatically. `log4brains` publishes the `docs/decisions/` directory as a searchable static site and has an `init` command that adapts to an existing set of records. Either is better than a wiki page, because the records live beside the code and move with it.

## Anti-patterns

**Activity in place of a decision.** "We evaluated three vendors over four workshops" tells the reader what the team did. What was chosen, what it costs, and who has to change — that is the artefact.

**The retrospective ADR.** A record written after the build to justify what already shipped. It is detectable: the rejected options are strawmen and the consequences are all good. If a record is genuinely retrospective, say so in the first line — an honest "documenting a decision made in Q1" is useful; a fake deliberation is not.

**One option and a conclusion.** Documents the outcome and destroys the reasoning, which was the only durable part.

**Scoring-matrix laundering.** Weights chosen after the winner is known, producing arithmetic that confirms the intuition. If it was a judgement call, write "this was a judgement call, based on [TK: whose experience with what]". That is defensible. A rigged matrix is not, and a reviewer will spot it.

**Consequences that are all good.** Every real decision costs something. A record with no bad or neutral bullets is marketing.

**"We will review it later" as Confirmation.** No owner, no date, no mechanism, no review.

**A design doc maintained as living documentation.** Its job ends when implementation starts. Keeping it in sync forever guarantees it is trusted and wrong. Mark it superseded and point at the code, the runbook, or a newer ADR.

**People-performance content in a shared artefact.** It follows the person around, and it turns a technical document into an HR object.

## Reference files

- `references/interrogation.md` — read before drafting anything: the per-section question bank, the follow-ups that break a vague answer, and how to convert a non-answer into a `[TK]`.
- `references/design-doc.md` — read when the artefact is a design doc or RFC rather than an ADR: full Google-style section brief, cross-cutting concerns checklist, lifecycle, and the Rust/IETF RFC and Amazon PR/FAQ alternates.

## Assets

- `assets/adr-template.md` — the full MADR 4.x fill-in template.
- `assets/adr-template-minimal.md` — the four-section variant that fits most decisions.
