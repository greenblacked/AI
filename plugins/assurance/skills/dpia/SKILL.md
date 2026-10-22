---
name: dpia
description: "Run a data protection impact assessment as a dated, versioned procedure rather than a form filled in after launch: screen against a written trigger list first and record the answer either way, describe every data flow, test necessity and proportionality field by field, list risks to the people whose data it is rather than to the company, give each mitigation a named owner, have a named person with authority accept the residual risk, and re-run when the design changes. Procedure, not legal advice. Use when someone asks whether a feature needs a DPIA or privacy impact assessment, needs one drafted or reviewed, or is launching profiling, monitoring, special-category or large-scale processing. Not for retention, deletion, subject requests or a breach call (data-privacy), an attacker-centred design review (threat-model), or choosing a supplier (vendor-evaluation)."
allowed-tools: Read, Grep, Glob, Write, Edit
---

# Data protection impact assessment

A DPIA is done when there is a dated, versioned document that says whether an assessment
was required and why, describes the processing well enough that someone outside the team
could find the risks in it, shows each data item is needed for a stated purpose, lists the
risks to individuals with likelihood and severity scored separately, gives every
mitigation an owner and a due date, and carries the name of the person who accepted what
is left. It is finished before the processing starts, and the design document links to it
so a change to the design reaches it.

The usual failure is the opposite on every count: written after launch to satisfy a
reviewer, a risk list of fines and headlines, mitigations phrased as "we will encrypt"
with nobody's name against them, and a document nobody opens again until the feature has
changed beyond recognition.

## This is procedure, not legal advice

The term and its minimum contents come from Article 35 of the GDPR, which the UK GDPR
carries in the same form. Other regimes have their own assessments with different
triggers and contents; take those from the authority that binds you, which
`data-privacy`'s first step establishes. Wherever a reading of the law decides the outcome
— whether a trigger applies, whether a lawful basis holds, whether residual risk requires
consulting the supervisory authority — write the question down and route it to the data
protection officer or counsel. This skill gets the facts into a shape they can decide on
quickly; it does not decide for them.

## Hard gates

- Finish before processing begins. An assessment completed after go-live documents a risk
  already taken, and the cheapest mitigations — not collecting a field, not building a
  flow — are no longer available.
- Residual risk is accepted by a named person with authority to stop the processing, not
  by the team that proposed it. The person who wants the feature is the person least able
  to judge what it costs someone else.
- If residual risk to individuals is still high after mitigation, stop and put the prior
  consultation question (Article 36) to the DPO or counsel before launch. Do not settle it
  in the document by rescoring.

## Workflow

### 1. Screen against a written trigger list

Apply the list before writing anything else, and record the result whether the answer is
yes or no, with the date, the criteria considered and who decided. "We looked and it was
not needed" is only provable if it was written at the time.

The list has three layers: the mandatory cases in Article 35(3), your supervisory
authority's published list of processing that requires an assessment, and the nine
criteria from the European guidelines, where meeting two or more means you should assume
one is required. Read [screening](references/screening.md) for all three, the screening
record and worked examples.

Settle scope at the same time. One assessment can cover a set of similar operations with
similar risks, so a product with several features sharing one data flow needs one
document, not one per feature — but each feature must appear in its description, or the
coverage claim is empty.

### 2. Describe the processing

Write the systematic description: what is processed, about whom, from where, for which
purposes, by whom and for how long. Concretely:

- Data categories per field group, marking special-category and criminal-offence data.
- Data subjects, naming any vulnerable group — children, employees, patients, people in
  debt — because the power imbalance changes what counts as fair.
- A flow from collection through storage, processing, every recipient and processor, any
  transfer abroad, and deletion. A risk can only be found where the description says the
  data goes, so a flow that stops at "stored in our database" hides everything after it.
- Volume: number of people and records, and how fast it grows.
- Any new technology in the processing, such as a model making or shaping decisions.

If `data-privacy` has already classified the data, reuse its inventory rather than
re-deriving it. When the source is a bulky schema dump or log sample, hand it to the
`pii-reader` subagent and work from its field list.

### 3. Test necessity and proportionality

For each purpose, name the lawful basis; for legitimate interests, attach the balancing
record. Then go field by field and ask whether the purpose fails without it, and whether
less would do: an aggregate instead of a row, a pseudonym instead of an identifier, a
shorter retention, a coarser location, processing on the device instead of the server.

Cover the rest of the checklist in the template: purpose limitation, accuracy, how people
are told, how they exercise their rights — including human review where a decision is
automated — processor contracts and the transfer mechanism.

The output is a list of what was removed or reduced, with the reason. A necessity test
that removes nothing was usually not done; it was asserted.

### 4. List the risks to individuals

Phrase every risk as harm to a person: "an employee's sick-leave pattern is visible to
their line manager", not "regulatory fine" or "reputational damage". The assessment is of
risk to people's rights and freedoms; the company's exposure follows from those, and a
register of company risks produces mitigations that protect the company — a disclaimer, a
consent banner — rather than the person.

Look for harm from two sources. The data going wrong: illegitimate access, unwanted
modification, loss. And the processing working as designed: discrimination from a score,
a chilling effect from monitoring, a decision someone cannot contest, a purpose that
quietly widens, re-identification from a join. The second source is the one engineering
teams miss, because nothing has to fail for it to happen.

Score likelihood and severity separately on the scale in the template, and keep both in
the register. Multiplying them into one number turns a remote but severe harm into a
medium one, which is the case the assessment exists to surface. If a threat model exists
for the same system, import its relevant threats as sources of the first kind rather than
redoing that analysis here.

### 5. Mitigate, with an owner per measure

For each risk: the measure, a named owner, a due date or the launch it gates, and the
evidence that it is done — a merged change, a configuration, a signed contract. A
mitigation with no owner is an intention, and intentions are what the first audit finds
still open.

Prefer measures in this order: remove the data or the flow, then reduce it, then guard
it, then tell people about it. Notice and consent come last because they move the risk to
the individual instead of lowering it. Rescore each risk after its measures and record
both scores.

### 6. Get the residual risk accepted

The accepting person signs with their name, role and the date, against the residual
scores, not the inherent ones. Where a DPO is designated, seek their advice and record it
verbatim; if it is not followed, record why. Record whether you sought the views of the
people affected or their representatives, and if not, why not. Any residual risk still
scored high goes to the prior-consultation question in the hard gates before anything
ships.

### 7. Store it, version it, and wire the re-trigger

Store the assessment where design documents live, with a version number, the date, the
author, the approvers and a change log. Link it from the design document and the feature
specification, so anyone changing the design passes it.

Write the re-trigger list into the document itself: a new data category, a new purpose,
a new recipient or processor, a new transfer destination, a new group of people (children
especially), a step change in scale, a new technology in the decision path, or a longer
retention. Add one question to the design review or pull request template — does this
change anything on the linked assessment's re-trigger list — because a re-trigger that
depends on someone remembering the document exists will not fire. A calendar review date
is the backstop, not the mechanism.

## What people do instead, and why it fails

**Filling in the template top to bottom after the build.** Every section is answered with
what was built, so necessity always holds and nothing is ever removed.

**Treating consent as the mitigation.** It changes who carries the risk, not its size,
and for employees or anyone else who cannot freely refuse it is rarely a valid basis
anyway.

**One assessment for the whole company.** It cannot describe any flow concretely enough
to find a risk in it, so it finds none.

**Copying the risk register from the last assessment.** The risks of the last feature are
listed and the risks of this one are not, and the document looks complete.

## Hand back

Read [the template](references/dpia-template.md) when writing the document; it holds the
section order, the scoring scale, the risk register and the sign-off block. Return:

- **Screening record** — required or not, the criteria met, date, decider.
- **The assessment** — in the template's shape, versioned, with its location.
- **Removed or reduced** — what the necessity test cut, and why.
- **Residual risks** — each with its score, and who accepted it.
- **Open questions** — every point routed to the DPO or counsel, including any prior
  consultation question.
- **Re-trigger list** — as written into the document, and where the design review asks it.
