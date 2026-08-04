# Evidence and Structure

Use this reference before outlining a technical article. It keeps the draft grounded in
what the author can prove and selects a structure that matches the reader's job.

## Contents

- [Evidence hierarchy](#evidence-hierarchy)
- [Claim ledger](#claim-ledger)
- [Primary structures](#primary-structures)
- [Anonymisation](#anonymisation)
- [Diagrams and code](#diagrams-and-code)
- [Source handling](#source-handling)

## Evidence hierarchy

Prefer evidence in this order for claims about the author's work:

1. raw artefacts: logs, metrics, traces, commits, configuration, tickets and timestamps;
2. contemporaneous notes or decision records;
3. direct recollection with uncertainty stated;
4. inference from the above;
5. general industry knowledge, sourced separately.

Do not use an external benchmark to fill a missing internal measurement. “Teams usually
improve by 30%” cannot establish what this team achieved.

For external technical claims, prefer specifications, official documentation, release
notes, research papers, and original engineering reports. Use secondary explainers for
orientation, then cite the primary source that supports the sentence.

## Claim ledger

Create the ledger before drafting:

| ID | Claim | Observed / sourced / inferred / opinion | Evidence | Confidence | Publication constraint |
| --- | --- | --- | --- | --- | --- |

Every number gets units, population, time window, comparison point, and source. Replace
“latency improved 40%” with the exact percentile, window, traffic slice, before/after values,
and measurement system.

Mark missing evidence as a question someone can answer:

- `[TK: p95 deploy duration for the four weeks before and after, CI dashboard]`
- `[TK: confirm whether customer names may appear, ask legal/comms]`
- `[TK: version where this flag became available, release notes]`

## Primary structures

### Decision article

Use when the reusable value is how a choice was made.

1. Decision and why it mattered.
2. Constraints and invariants.
3. Options genuinely considered.
4. Evidence and trade-offs.
5. Consequences after adoption.
6. Conditions under which another choice wins.

### Migration article

Use when transition mechanics carry the lesson.

1. Result and forcing function.
2. Old state and constraints.
3. Invariants and plan.
4. Compatibility period and cutover.
5. What surprised the team.
6. Evidence after migration.
7. What the reader should reuse.

### Incident lesson

Use when a system mechanism, not the incident chronology, is reusable.

1. Impact and short mechanism.
2. Trigger, contributing conditions and detection.
3. Why existing controls did not stop it.
4. Changes made.
5. Evidence the changes work.
6. Boundary: where the lesson does not transfer.

Keep the full timeline in the postmortem and link it if publishable.

### Tutorial

Use when the reader needs to reproduce an outcome.

1. Finished result and prerequisites.
2. Minimal working path.
3. Verification after each meaningful step.
4. Two or three probable failure modes.
5. Production considerations clearly separated from the tutorial path.

### Investigation

Use when the diagnostic method matters.

1. Symptom and impact.
2. Competing hypotheses.
3. Evidence that eliminated each.
4. Decisive observation.
5. Root mechanism and fix.
6. General diagnostic shortcut.

## Anonymisation

Preserve technical truth while removing identification:

- replace customer and employee names with roles;
- replace exact internal hostnames and URLs with structural descriptions;
- use ranges only when the range still supports the claim;
- remove credentials, tokens, account IDs, private IPs and security-sensitive topology;
- state when values were normalized or details combined.

Do not fabricate a composite incident without saying it is composite. Do not shift dates or
numbers silently if their relationship carries the lesson.

## Diagrams and code

Use a diagram when it explains ownership, data flow, state transition, or sequence better
than prose. Give it one conclusion and label trust boundaries, authority, and direction.

Code should be minimal, runnable, versioned where behavior changes, and safe to copy. Remove
irrelevant production detail but keep error handling that protects the reader from a
dangerous partial result.

## Source handling

Place citations next to the claim they support. Distinguish what the source states from
what the author infers. Quote only when exact wording matters; paraphrase the mechanism.

Record title, author or organization, publication date, URL, access date when useful, and
the exact section supporting the claim. A bibliography assembled after drafting will miss
the source-to-claim relationship.
