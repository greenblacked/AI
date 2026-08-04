# CV patterns for senior infrastructure and platform roles

## Contents

- Bullet anatomy
- Patterns by achievement type, with before and after
- Verbs and constructions
- Section order and what goes in each
- ATS mechanics without superstition
- Length norms
- Awkward history: contracting, short tenures, side projects
- Master-document mechanics

## Bullet anatomy

Three parts, in whichever order carries the most weight:

- **Outcome** — what changed for the business, the users or the team.
- **Mechanism** — what was actually done, specific enough that an engineer believes it.
- **Scale** — the number that makes it real: services, engineers, requests, euros, minutes.

Lead with the outcome when the number is strong. Lead with the mechanism when there is no
number, because "Rebuilt the release pipeline around immutable artefacts and staged rollouts"
is credible on its own, while "Improved releases" is not. Every bullet should survive the
question "how do you know?"

## Patterns by achievement type

**Migration.** From-state, to-state, what did not break.

- Before: "Led migration to Kubernetes."
- After: "Migrated 40 services from EC2 to EKS over two quarters with zero customer-facing
  downtime, using a dual-run cutover per service and automated rollback on SLO breach."
- The credibility carrier is "how did you avoid breaking it", not the destination technology.

**CI/CD rebuild.** Time saved, per what unit, and who felt it.

- Before: "Responsible for Jenkins and GitHub Actions pipelines."
- After: "Cut CI feedback from 45 to 9 minutes for [TK: metric] engineers by splitting a
  monolithic pipeline into cached parallel stages and moving integration tests to a
  post-merge gate."

**Reliability and incidents.** Class of incident removed, not tickets closed.

- Before: "Improved system stability and monitoring."
- After: "Cut Sev-2 incidents from 11 to 3 per quarter by adding backpressure at ingest and
  replacing host-metric alerts with SLO burn-rate alerts, reducing paging volume [TK: metric]."
- Reliability bullets are stronger when they name the class of failure that stopped happening.

**Cost.** Absolute and relative, plus the thing that did not get worse.

- Before: "Optimised cloud costs."
- After: "Reduced monthly AWS spend 31% (about $[TK: metric]/yr) through committed-use
  coverage, right-sizing and automatic non-prod shutdown, with no change to p99 latency."

**Platform and developer experience.** Adoption is the evidence.

- Before: "Built internal developer platform."
- After: "Shipped a self-service service template and paved-road pipeline adopted by
  [TK: metric] of teams in six months, cutting new-service setup from two weeks to one day."
- An internal platform with no adoption number reads as a project, not an outcome.

**Security and compliance.** Say what the audit or the control actually required.

- Before: "Worked on SOC 2 compliance."
- After: "Took the platform through first SOC 2 Type II with no infrastructure findings,
  by codifying access review, log retention and change control in Terraform and CI gates."

**Leadership.** Scope, and what got better because of a decision, not headcount alone.

- Before: "Managed a team of six engineers."
- After: "Grew a platform team from 3 to 6, introduced a rotating on-call with a documented
  escalation path, and cut out-of-hours pages [TK: metric] in two quarters."
- Before: "Led AI enablement initiatives."
- After: "Ran AI enablement for [TK: metric] engineers: chose the tooling, wrote the usage
  and data-handling guardrails with legal, and drove weekly active use to [TK: metric]."

## Verbs and constructions

| Use | Avoid | Why |
| --- | --- | --- |
| Built, migrated, cut, automated, standardised, led, negotiated | Helped with, was involved in, participated in, assisted | Weak verbs describe proximity to work, not ownership |
| "I led" in the summary, plain past tense in bullets | "Responsible for", "duties included" | Job-description language describes the role, not the person |
| "We" only where the credit is genuinely shared | "We" for everything | Interviewers probe for the candidate's own contribution |
| Concrete nouns: EKS, Terraform, Argo CD, GitHub Actions | "Cloud technologies", "modern tooling" | Vague nouns are unverifiable and read as padding |

Two credible bullets beat six vague ones. If an achievement cannot be made specific, it is
probably a responsibility, and responsibilities belong in one line of role context at most.

## Section order

For a senior or lead infrastructure candidate:

1. **Name and contact** — email, phone, city and country, LinkedIn, GitHub, personal site.
   No photo, no date of birth, no marital status, no full postal address.
2. **Summary** — two or three lines, rewritten per application. What the user is, the domain,
   the scale they operate at, and the thing they are moving toward. No adjectives that cannot
   be evidenced ("passionate", "results-driven").
3. **Skills** — three or four grouped lines (cloud and orchestration; IaC and CI/CD;
   observability; languages). Ordered to mirror the JD's true overlaps. Nothing listed that
   the user would not answer questions about.
4. **Experience** — reverse chronological. Company, title, dates as MM/YYYY, one line of
   context for the company if it is not well known ("Series B fintech, 200 engineers"), then
   bullets. Six to eight for the current role, three to four for the previous, one or two
   beyond five years back.
5. **Selected projects or open source** — only if it carries evidence the roles do not.
6. **Education and certifications** — one line each. Certifications that are current and
   relevant (CKA, AWS, security). Graduation dates optional beyond ten years.

Everything else — interests, references available on request, skill rating bars — is filler.
Rating bars are actively harmful: nobody agrees what four out of five stars means.

## ATS mechanics without superstition

What genuinely matters for the parse:

- One column. Two-column layouts are the most common cause of scrambled parses, because the
  extractor reads left to right across both columns.
- Standard headings the parser recognises: Experience, Skills, Education. Not "Where I've
  Made an Impact".
- No content inside tables, text boxes, headers or footers. Contact details in a header are
  the classic way to submit a CV with no email address on it.
- Dates in a consistent MM/YYYY format, with the month present. Year-only ranges get read as
  gaps by some parsers.
- Submit a text-based PDF unless the posting asks for .docx. A PDF exported from a design
  tool as an image parses to nothing.
- Standard fonts, real bullet characters, no icons carrying meaning (a phone glyph with no
  label loses the phone number).

What is superstition: white-text keyword stuffing (it is detected and it is a rejection),
third-party "ATS score" tools, believing a specific keyword count matters, and rewriting a CV
to please a parser at the cost of the human reader. The parse gets the CV into the database;
a human decides. Mirror the JD's exact vocabulary only where it is already true — "EKS" rather
than "managed Kubernetes on AWS" if that is what they call it.

## Length norms

- Senior IC or lead with 8-15 years: two pages. One page forces the removal of the evidence
  that makes seniority visible.
- Fifteen-plus years or a genuinely large leadership scope: three pages maximum, and only if
  the third page carries achievements rather than an inventory of old roles.
- Early roles compress hard: after ten years, a line each ("Systems Engineer, Company,
  2012-2015") is enough.
- If a page is over by three lines, cut the weakest bullet rather than shrinking the font
  below 10pt or the margins below 1.5cm.

## Awkward history

- **Contracting.** Group under one heading ("Independent Platform Consultant, 2021-2023")
  with client engagements as sub-entries. A list of eight short jobs reads as instability;
  one consultancy heading reads as a business.
- **Short tenure.** Keep it if the work is relevant, add the reason in three words where it
  is external ("company acquired", "fixed-term contract", "role eliminated"). Do not hide it;
  a gap in the timeline invites worse assumptions than the truth.
- **Gaps.** Show them as dates rather than stretching the surrounding roles to cover them.
  Falsified dates fail employment verification, which is the one check almost every employer
  actually runs.
- **Side projects.** Include only where they evidence something the paid roles do not — a
  language, a scale, a domain. A personal site and a public CV repo are worth linking when
  they are maintained; a stale repo is a liability.

## Master-document mechanics

Keep `cv-master.md` with every role, every bullet ever written, and a metrics block recording
each confirmed number with its source and date. Tailoring copies a selection out of it; new
achievements go in as they happen, while the numbers are still knowable. Any bullet written
for a specific application, once the user confirms it is accurate, goes back into the master.
The failure mode this prevents: reconstructing a number two years later from memory, which is
how honest people end up with a CV they cannot defend.
