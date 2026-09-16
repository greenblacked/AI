---
name: threat-model
description: "Model what could go wrong with a design before the code exists — draw the data flows and mark every trust boundary first, because a threat lives where data crosses one; apply STRIDE per crossing rather than per component, which is what stops a quadratic pile of non-findings; write down what you are choosing not to mitigate and get a name against it; and rerun when a boundary moves rather than on a calendar. Use when a feature, service or integration is being designed, when a design document needs its security section, or when someone asks what an attacker could do with this. Not for reviewing a diff (security-review), designing login or tokens (auth-design), IAM permissions (access-review), or a live compromise (secret-rotation)."
allowed-tools: "Read, Grep, Glob, Write, Edit"
---

# Threat modelling a design

A threat model is worth doing when there is still a design to change and no diff to
review. Once code exists, a reviewer walking the diff finds more, faster — that is
`security-review`'s job and it is better at it. What a review cannot do is find the
threat that comes from the shape of the system rather than from a line in it: the queue
nobody authenticates because it is internal, the admin path that skips the gateway, the
service that trusts a header it did not set.

The failure this procedure exists to prevent is a threat model that produces a long list
of generic findings nobody actions. That happens for one reason, and the ordering below
is built around it: people brainstorm threats against a picture before deciding where the
trust changes hands.

## Hard gates

- Do not enumerate a single threat before the boundaries are drawn. A threat against "the
  system" is unactionable by construction; a threat against a named crossing has an owner,
  a mitigation and a test.
- Do not score. No DREAD, no likelihood percentages, no CVSS for a design. A number
  invented from judgement gets quoted later as evidence, and the ranking that matters is
  which crossings are reachable by whom.
- Do not close a threat with "we would notice". Detection is a mitigation only if
  something is actually emitting the signal and someone is actually alerted on it. If
  neither is true, the threat is open and the work is in `instrumentation`.

## Workflow

### 1. Draw the flows, and mark where trust changes hands

Every external entity, process, data store and flow between them. Keep it coarse enough
to fit on one screen; a diagram nobody can hold in their head produces threats nobody can
either.

Then mark the boundaries, which is the step that does the work. A boundary is anywhere
the level of trust changes: browser to server, your service to a third party, tenant to
tenant, unauthenticated to authenticated, one team's service to another's, application to
database, and the deployment pipeline to production. The last two are the ones most often
left out, and both are where the interesting threats live.

Read [drawing the model](references/data-flow-model.md) when the system is large enough
that the scope of the diagram is itself a decision.

### 2. Apply STRIDE per crossing, not per component

For each flow that crosses a boundary, ask the six questions: can an attacker pretend to
be one of the parties (spoofing), change the data in flight (tampering), deny having sent
it (repudiation), read what they should not (information disclosure), stop it working
(denial of service), or gain rights they were not granted (elevation of privilege).

Per crossing rather than per component is the whole discipline. A component has every
category applied to it in the abstract, which generates a quadratic pile of findings that
are all true and none actionable. A crossing has two named parties and a specific payload,
so each answer is either a real threat with an owner or a quick no.

[STRIDE per crossing](references/stride-per-crossing.md) has the question set with what a
useful answer looks like for each, and the crossings where each category usually bites.

### 3. Decide each threat, and write down what you are not doing

Every threat ends in one of four states, and all four are written down: mitigated, with
the control named; transferred, with the party named; accepted, with a person's name
against it and the reason; or eliminated by a design change.

Accepted is the one that matters. A threat model whose output is only the mitigations is
a document that hides its own scope, and the threats somebody decided to live with are
exactly the ones the next reader needs to see. Give each a name and a date, not a team.

### 4. Write the mitigations as testable statements

"Validate input" is not a mitigation. "The queue consumer rejects a message whose tenant
id does not match the signed envelope" is, because someone can write that test. A
mitigation that cannot be tested is a sentiment, and it will be reported as done.

### 5. Rerun when a boundary moves

Not quarterly. A calendar cannot see a new integration, and most of the year nothing has
changed. The triggers are structural: a new external dependency, a new tenant model, a
new admin path, authentication moving, or a service being split or merged. Put the trigger
list in the design document so the next author knows what obliges them to come back.

## What people do instead, and why it fails

**Modelling the whole system every time.** Scope to the change and its neighbours. A
model of everything is written once, is never updated, and is wrong within a quarter.

**Treating the diagram as the deliverable.** The diagram is scaffolding for the boundary
marking. The deliverable is the decided threat list.

**Deferring to the security team to run it.** The people who know where the trust changes
hands are the ones who designed it. A model produced without them finds the threats that
are legible from outside, which are the ones already handled.

**Stopping at the first mitigation.** A boundary usually carries more than one category.
Finding spoofing and moving on leaves the elevation path that made spoofing worth it.

## Output format

**Scope** — what is in the model, and what is explicitly out.

**Boundaries** — each one, and the two parties either side.

**Threats** — per crossing: the category, what it would let an attacker do, and the state
from step 3 with its owner.

**Accepted** — pulled out separately, with a name and a date against each.

**Retrigger** — the structural changes that oblige a rerun.

The four framing questions this follows — what are we building, what can go wrong, what
are we doing about it, did we do a good job — and STRIDE itself are OWASP's, from
[the threat modelling cheat sheet](https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Threat_Modeling_Cheat_Sheet.md).
