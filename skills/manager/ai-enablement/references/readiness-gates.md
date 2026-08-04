# Readiness gates for AI-assisted engineering

## Contents

- [How to use these](#how-to-use-these)
- [Gate 1: data handling](#gate-1-data-handling)
- [Gate 2: secrets and code exfiltration](#gate-2-secrets-and-code-exfiltration)
- [Gate 3: licensing and provenance](#gate-3-licensing-and-provenance)
- [Gate 4: review standard](#gate-4-review-standard)
- [Gate 5: logging and auditability](#gate-5-logging-and-auditability)
- [Gate 6: procurement and cost visibility](#gate-6-procurement-and-cost-visibility)
- [Assessing a gate](#assessing-a-gate)
- [When a gate is absent](#when-a-gate-is-absent)

## How to use these

Six gates. Assess each as **met**, **partial** or **absent**, with the evidence that
justifies the rating — a document, a config, a scan result, not an assurance in a
meeting. Gates apply proportionally: a two-person pilot on a public repository needs
gate 1 and gate 4 settled and can carry known gaps elsewhere. Anything past a pilot
needs all six.

The rating is only useful with the exposure attached. "Gate 3 absent" is not
actionable; "no stated position on generated-code provenance, and we ship a product
under a licence with attribution obligations" is.

## Gate 1: data handling

**Covers:** what may and may not be sent to a model.

Be specific about categories rather than writing "be careful with sensitive data",
which nobody can apply at the moment of decision:

- Customer data, including production database contents and support attachments.
- Personal data, and which regimes apply to it.
- Regulated data — payment, health, or anything under a sector regime.
- Third-party confidential material received under NDA.
- Production credentials, tokens and certificates — covered again in gate 2 because
  it is the failure with the shortest path to an incident.

Also state what is explicitly permitted. A policy that only prohibits produces
paralysis and, worse, drives usage into personal accounts where you cannot see it.
"Source code from repositories in group X, using approved tool Y, may be sent" is
what makes the policy usable.

Reachability matters as much as content. The policy must be findable from the tools
people use — linked in the repo, in the tool's onboarding, in `AGENTS.md`. A policy
living in a wiki nobody opens is absent in practice, whatever its rating on paper.

**Assess by:** reading the actual document; asking three engineers at random what
they believe the rule is. Divergent answers mean partial at best.

## Gate 2: secrets and code exfiltration

**Covers:** preventing credentials and proprietary code leaving through the tooling.

- Secret scanning on the paths agents read and write, including pre-commit where
  agents commit. Agents read broadly; a `.env` that a human would never open gets
  read.
- A stated position on which repositories may be sent to which providers. Where
  code is under a customer contract restricting third-party disclosure, this is a
  contractual question, not an engineering preference.
- Vendor retention and training terms confirmed per tool, in writing, at the tier
  actually purchased. Terms differ between free, pro and enterprise tiers of the
  same product, and the difference is usually exactly this.
- Shadow usage addressed rather than prohibited. It exists because the approved
  path is missing or worse; closing the gap is more effective than a ban, and a ban
  simply moves the usage out of view.

**Assess by:** scan configuration in CI; the vendor's data-processing terms for the
purchased tier; a straight question about personal-account usage asked with no
consequence attached.

## Gate 3: licensing and provenance

**Covers:** the organisation's position on generated code.

- A stated position on whether generated code is acceptable in the product, and any
  exclusions — for example, code shipped to customers under specific licence terms.
- Provenance filtering or attribution features enabled where the tools offer them.
- A rule for generated code that closely reproduces a known source: it is reviewed
  and attributed like any third-party code, through whatever process already exists
  for vendored dependencies.
- Where legal counsel has given a position, it is written down and linked. Where
  they have not, that is the finding — an unasked question is a gap, and it is a
  cheap one to close.

**Assess by:** the written position and its date; the tools' provenance settings.

## Gate 4: review standard

**Covers:** accountability for merged code. This is the load-bearing gate.

The standard, stated plainly:

> A human is accountable for every merged change, regardless of who or what wrote
> it. The reviewer's obligation is unchanged by the origin of the code: they must
> understand what it does, why it is correct, and what happens when it fails. "It
> was generated" is not a mitigating explanation for a defect, and it is not a
> reason to review more lightly. The engineer who opens the pull request is
> responsible for its contents, whether they typed them or not.

What this rules out, explicitly, because each has been observed in practice:

- Merging a change the author cannot explain.
- A relaxed review threshold for generated code because "it is only boilerplate".
- Auto-merge on generated changes without the standard required review.
- Treating an agent's own review as a substitute for human review rather than an
  input to it.

This gate is the dependency for rung 3 of the enablement ladder. Agents with write
access are safe precisely because the merge path enforces this standard on them
exactly as on a human. Where the standard is unstated, the merge path enforces
nothing and the ladder stops at rung 2.

**Assess by:** whether it is written down and where; branch protection settings;
whether any generated-change path bypasses required review.

## Gate 5: logging and auditability

**Covers:** knowing what happened, needed the first time something goes wrong.

For any agent with write access — to repositories, infrastructure, or ticketing:

- A record of what ran, against what, at whose request, and what changed.
- Attribution on commits and pull requests that identifies both the agent and the
  requesting human. An agent identity with no linked human is an accountability gap
  that gate 4 cannot close.
- Retention long enough to support an incident investigation weeks later.
- Distinct credentials per agent, scoped to what it needs, revocable independently.
  A shared service account used by several agents makes attribution impossible at
  precisely the moment it matters.

**Assess by:** looking at a recent agent-authored change and tracing it end to end.
If the trace breaks anywhere, the gate is partial.

## Gate 6: procurement and cost visibility

**Covers:** knowing what this costs and who owns the number.

- Per-team cost, visible to that team, with a trend rather than a point.
- A named owner of the total. Not a committee.
- Awareness of the pricing model, particularly usage-priced agent tooling, where
  cost scales with adoption. A successful rollout produces a surprising month-three
  bill; the surprise is avoidable and the cost usually is not the problem.
- Seat reclamation for unused licences, reviewed on a schedule. This also produces
  the retained-usage data the assessment needs, which is why it is worth doing even
  when the money is trivial.
- A stated cost-per-team ceiling that triggers a review rather than a hard stop.

**Assess by:** whether anyone can state last month's spend per team without
opening a support ticket.

## Assessing a gate

| Rating | Means |
| --- | --- |
| Met | Written, current, enforced by a mechanism rather than by intention, and known to the people it governs |
| Partial | Exists but is unenforced, out of date, or unknown to practitioners |
| Absent | Nothing written, or a verbal understanding only |

A gate enforced by a mechanism outranks one enforced by a document. Branch
protection is a met review gate; a wiki page saying reviews are required is partial.

## When a gate is absent

Do not stop the programme. Scope it to what the missing gate permits, and put
closing the gate on the critical path with an owner and a date.

| Absent gate | Safe scope until closed |
| --- | --- |
| Data handling | Public or non-sensitive repositories only |
| Secrets / exfiltration | No agent write access; no repositories under customer confidentiality terms |
| Licensing | No generated code in customer-shipped components |
| Review standard | Rung 1 and 2 only — no agent with write access |
| Logging | No agent write access outside a sandbox |
| Cost visibility | Fixed-seat tools only; no usage-priced agents |

Record the scope limit and its expiry date in the plan. An indefinite limitation
with no owner becomes the permanent shape of the programme.
