# Design docs and RFCs

## Contents

- When a design doc is the right artefact
- Section-by-section brief (Google shape)
- Cross-cutting concerns checklist
- Degree of constraint
- Lifecycle: when the doc dies
- Alternate shapes: Rust/IETF RFC, Amazon PR/FAQ
- Review mechanics

## When a design doc is the right artefact

A design doc earns its cost when the work is large enough that the wrong shape is
expensive to unwind, several people have to build against the same assumptions, or the
decision spans teams. Below that line an ADR is the right size.

The doc is a thinking tool with a side effect of being documentation. Its highest-value
output is the set of objections it collects before code exists. Write it early, while
changing your mind is still cheap; a doc written when the branch is already open is a
status report.

Typical size: 10-20 pages for a substantial system, 1-3 for a focused one. If it is
under a page, write an ADR instead.

## Section-by-section brief

### Context and scope

Background a reader needs to evaluate the design, stated objectively — the systems that
exist, the constraints already in place, what the current thing does badly. No solution
here, and no advocacy. A reader who disagrees with the context will disagree with
everything downstream, so this section is where you find out early.

Keep it short: a page at most. Link out for detail.

### Goals and non-goals

Goals: the properties the design must have, phrased so that failure is observable. "Serve
[TK: rps] at [TK: p99 target]" is a goal. "Improve performance" is a mood.

**Non-goals are the most valuable section in the document and the most frequently
omitted.** They are not "things we don't care about" — they are things a reasonable
reader would assume are in scope, explicitly ruled out. "Not building multi-region
failover in this phase." "Not migrating the legacy writer." "Not a general-purpose
platform; two known consumers only." Every non-goal you write is a scope argument you do
not have to have in week six, and it is the section reviewers use to calibrate whether
the design is over-built.

### The design

Organise around trade-offs, not around a walkthrough of the happy path. Reviewers can
infer the happy path; what they cannot infer is why you chose the harder option in three
places. For each significant choice, state the alternative you did not take and the
property you were buying.

Include:

- **A system-context diagram.** One box per component, arrows labelled with what flows.
  It orients a reader in fifteen seconds and exposes coupling that prose hides.
- **API shapes**, in enough detail to code against — endpoints or method signatures,
  request and response shapes, error cases, idempotency and retry semantics, versioning.
  Skip generated boilerplate.
- **Data storage**: the model, the engine and why, expected growth rate and resulting
  size at [TK: horizon], retention and deletion policy, indexes and the queries they
  serve, and the migration path including how it is reversed mid-flight.
- **Constraints and their consequences**: latency budgets, quotas, existing contracts,
  the compliance boundary, the team's operational capacity.

### Degree of constraint

State plainly how much freedom the design has, because reviewers judge it against that.
Greenfield with no existing consumers is a different exercise from a system with three
downstream teams, a data model that cannot change, and a vendor contract expiring in
[TK: month]. A design that would be over-engineered on a blank page can be exactly right
when it has to interoperate with two things that cannot move. Say which world you are in.

### Cross-cutting concerns

Walk each one explicitly and write "no impact, because …" where there is none. The
sections people skip are the ones that produce launch blockers.

- **Security**: trust boundaries, authn/authz model, secret handling, threat surface
  introduced.
- **Privacy**: personal data touched, lawful basis, retention, deletion path, data
  residency, who can read it in production.
- **Observability**: the signals that tell you it is working, where they land, and the
  alerts that fire when it is not. If you cannot name the dashboard, you cannot operate it.
- **Reliability and SLO impact**: new dependencies and their published availability, the
  compound effect on the existing SLO, failure modes and blast radius, degradation
  behaviour when a dependency is down.
- **Cost**: infrastructure and licence delta at expected load, and at the growth horizon.
  A number with a source beats an adjective.
- **Compliance and audit**: obligations touched, evidence produced, sign-offs needed.
- **Operability**: who is on call for it, what the runbook covers, how it is deployed and
  rolled back, what routine toil it adds.

### Alternatives considered

For each alternative: what it was, its genuine advantages, and **the specific reason it
was rejected**. Rejection reasons are the section a future reader mines when
circumstances change — "rejected on cost at our volume" becomes a live option again when
volume changes, and that is only visible if the reason was recorded.

A design doc with no rejected alternatives has not made a decision. It has described a
plan, and it invites the whole debate to happen in review comments instead.

Strawmen are worse than nothing: an alternative dismissed in half a line signals that the
evaluation was decorative.

### Rollout and rollback

How it ships: flag, percentage ramp, shadow traffic, dual-write and backfill, cutover.
What is measured at each stage and the threshold that halts the rollout. How it is rolled
back, including the point after which rollback stops being possible — data migrations
usually have one, and naming it is the whole point of the section.

### Open questions

Real unknowns with an owner and a date by which each must close. This section shrinking
over the review period is the signal that the design is converging. Questions still open
at implementation start are risks; move them into the plan rather than deleting them.

## Lifecycle: when the doc dies

Be honest about this. The doc's job ends when implementation starts. It records the
thinking at a point in time, and it should not be maintained as living documentation —
a doc kept "up to date" is usually both trusted and wrong, which is the worst combination
available.

At implementation start, mark it with its status and date, and point onward: the code,
the runbook, the API reference, or the ADR that captured the durable decision. If the
design changes materially during the build, write a short new record explaining the
change rather than rewriting history.

## Alternate shapes

**Rust/IETF-style RFC.** A numbered document in a repository with a review period, public
comment and an explicit accept/reject decision at the end. Sections resemble: summary,
motivation, guide-level explanation, reference-level explanation, drawbacks, rationale and
alternatives, prior art, unresolved questions, future possibilities. Use it when the
audience is broad, the change is a contract others build on, and the review needs to be
open and auditable rather than a meeting.

**Amazon PR/FAQ six-pager.** A mock press release for the finished thing plus an FAQ
split into customer questions and internal questions, six pages hard limit, no slides,
read silently at the start of the meeting. Use it when the reader is non-technical, the
ask is funding or headcount, and the risk is building something nobody wanted. It forces
you to state the customer benefit in plain language before any design exists — which is
also its weakness: it is a poor container for technical trade-offs.

Both are compatible with this skill's rules. Whatever the shape, the artefact type goes
in the first line, unsourced numbers stay as `[TK]`, and rejected alternatives carry
their reasons.

## Review mechanics

Circulate with a deadline and a named list of required reviewers; "feedback welcome"
produces none. Ask for the specific thing you want — an objection to the storage choice
is worth more than a copy-edit. Resolve comments in the doc rather than in a thread that
disappears, and when a review changes the design, update the alternatives section so the
rejected path keeps its reason.
