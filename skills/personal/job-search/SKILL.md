---
name: job-search
description: Tailor a CV, write a cover note and prepare for interviews from the user's real history as a senior infrastructure, platform or engineering-leadership candidate — reading a job description for what it is really hiring to solve, rewriting experience as outcome-first bullets, and rehearsing STAR, system-design and leadership answers. Use this skill whenever the user pastes a job description or job link, asks to tailor, rewrite, review or shorten a CV or resume, wants a cover letter or cover note, is preparing for an interview or hiring loop, wants a system-design or behavioural rehearsal, asks how to explain a gap, a layoff or a career change, or asks how to handle salary and an offer. Casual phrasings count — "is this CV any good", "help me apply for this one", "grill me on this role". Not for writing job descriptions as a hiring manager, performance reviews or promotion packets, and never for inventing experience the user does not have.
---

# Job Search

A good application selects true things from a real history and puts them where the reader will actually look. Nothing in it would surprise a former manager asked about it.

Tailoring means selection and evidence, not embellishment. The pressure runs the other way at every step: the job description lists a technology the user touched once, a bullet would land harder with a number nobody measured, an interview answer would be tidier if the outcome had been cleaner. Each of those invents a liability. A fabricated CV fails at the reference check; a fabricated interview answer fails at the follow-up question, which in a senior loop is always asked. The other failure is subtler — a CV written in a voice the candidate cannot sustain in the room, which reads well and then collapses in the first thirty seconds of conversation.

## The evidence rule

Never assert an achievement, a metric, a date, a job title or a technology the user has not confirmed in this conversation or in a document they supplied. Where a number would strengthen a bullet and none was supplied, write the literal placeholder `[TK: metric]` in the draft and list every placeholder at the end of the output with the specific question that fills it — "roughly what did the build time drop to?" beats "add metrics here". Never fill a placeholder with a plausible guess, an industry benchmark, or a rounded version of something adjacent. If the user cannot recall a number, rewrite the bullet to lead with the mechanism instead of deleting the achievement.

## Scope

Use for: reading a job description, rewriting experience bullets, assembling or trimming a tailored CV, writing a cover note, interview rehearsal (behavioural, system design, leadership), offer and negotiation questions, and framing gaps or a layoff.

Do not use for: writing job descriptions from the hiring side, performance or promotion documents, or generating a work history the user has not lived.

## Workflow 1: Read the job description properly

1. **Split the requirements list into three buckets.** Hard requirements repeat: they appear in the title, in the responsibilities *and* in the requirements list, or they are gated by compliance or a visa. Wish-list items appear once, usually in a run of comma-separated technologies. Noise is the boilerplate every JD in the category carries.
2. **Name the two or three things this role is being hired to solve.** Read the responsibilities as symptoms. "Improve developer experience" plus "reduce deploy friction" plus a recent funding round usually means the platform team is behind the product team and someone has to industrialise it. Write the hypothesis in one sentence, because it drives the CV selection, the cover note's third paragraph, and the questions asked at the end of the interview.
3. **Check the scoping signals** before spending an evening on the application.

   | Signal in the JD | Reading | Action |
   | --- | --- | --- |
   | Fifteen-plus named technologies, no depth anywhere | The team does not know what it needs | Apply if interested, but probe ownership in screening |
   | "Wear many hats", "startup mentality", first infra hire | One person carrying an org's platform | Ask who is on call and what happens when they are away |
   | Both "hands-on" and "lead a team of 8" | Two jobs, one salary | Ask directly what the split is expected to be |
   | Title says lead, responsibilities are all delivery | No real scope | Deprioritise unless the pay is the point |
   | Specific problem stated with its constraints | Someone senior wrote this | Prioritise; tailor hard |
   | No salary band and no level named | Late-stage surprises | Ask for the band before the second interview |

4. **Map the user's history against the hard requirements only.** Where there is a genuine gap, say so plainly and decide whether the adjacent experience is honest to present. Do not paper over a gap with a wish-list match.

## Workflow 2: Rewrite experience as outcome-first bullets

Each bullet is action, mechanism, result — the outcome first when the outcome is strong, the mechanism first when the number is missing. Read `references/cv-patterns.md` for the full pattern set and worked examples.

| Before | After |
| --- | --- |
| Responsible for the CI/CD pipeline | Cut CI feedback time from 45 to 9 minutes by splitting a monolithic pipeline into cached, parallel stages, unblocking [TK: number] daily merges |
| Migrated infrastructure to Kubernetes | Migrated 40 services from VMs to EKS with zero customer-facing downtime, retiring [TK: metric] of legacy VM spend |
| Worked on improving system reliability | Reduced Sev-2 incidents by [TK: metric] over two quarters by adding backpressure at the ingest layer and moving alerting from host metrics to SLOs |
| Managed cloud costs | Cut monthly AWS spend 31% (roughly $[TK: metric]/yr) via committed-use coverage and killing idle non-prod, without a single capacity incident |

Rules that make the difference: verbs that survive scrutiny (built, migrated, cut, automated, led — not "helped with", "was involved in"), the mechanism named specifically enough that an engineer believes it, and one bullet per achievement rather than a paragraph containing three. Six to eight bullets for the current role, three to four for the one before, one or two beyond five years back.

## Workflow 3: Assemble the tailored CV

Keep one master document containing every role, every bullet, every project — never a dozen divergent CVs. A tailored CV is a *selection* from the master plus reordering, and the master is the only file that gets edited when a new achievement lands.

Per application: reorder the skills line to mirror the JD's true overlaps, promote the two or three bullets that speak to the hypothesis from Workflow 1, demote or cut the rest, and rewrite the summary in two lines aimed at this role. Everything shown must exist in the master; if a tailored bullet is worth writing, it belongs back in the master afterwards.

Structure, ATS realities and length norms are in `references/cv-patterns.md`. The short version: one column, plain headings, no tables or graphics carrying content in the parsed layout, dates as MM/YYYY, two pages for a senior infrastructure candidate. Mirror the JD's vocabulary only where it is already true of the user — "EKS" instead of "Kubernetes on AWS" is fine; adding Terraform because the JD asks for it is not.

## Workflow 4: The cover note

Three short paragraphs, under 200 words, no letterhead theatre and no restating the CV.

1. **Why this role.** One specific reason tied to what the company actually does or the problem in the JD. If nothing specific can be said, the application probably should not be sent.
2. **The single most relevant piece of evidence.** One achievement, with its number, that maps onto the hypothesis from Workflow 1. One, not three.
3. **What you would work on first.** Two sentences of concrete opinion about the first ninety days, offered as a hypothesis rather than a verdict. This paragraph is what separates a cover note from a formality, and it is the one hiring managers quote back.

## Workflow 5: Interview preparation

1. **Build the story inventory first.** Six to eight real stories from the user's history — a migration, an incident, a disagreement with a peer or a manager, an underperformer, a project that failed, a decision made without enough data, a thing they shipped that they would build differently now. Everything else is retrieval from this set.
2. **Shape each into STAR with the tail.** Situation and task short, action detailed and first-person ("I", not "we", when it was the user), result quantified where a real number exists. Then the tail senior loops actually probe: what would you do differently, what did it cost, what did you learn that changed your next decision. An answer without the tail reads as unreflective at this level.
3. **Rehearse system design as a loop**, not a lecture: clarify requirements and scale, state constraints and non-goals, sketch the components, then attack your own design — failure modes, blast radius, what breaks at 10x, what you would monitor, and the operational cost of running it. Infrastructure rounds reward the operability discussion far more than the box diagram. Prompts and evaluation rubric are in `references/interview-bank.md`.
4. **Drill the behavioural and leadership set** from `references/interview-bank.md`, one question at a time, with honest feedback: name the specific weakness (no result, buried the conflict, "we" throughout, three minutes of setup) rather than grading it as fine.
5. **Prepare the questions to ask.** The ones that reveal how the team really works: what does on-call look like this month, how often do you deploy and who presses the button, what was the last incident and what changed after it, where are technical decisions written down, what does the first ninety days look like for whoever takes this, why is the role open.

Rehearse the shape and the evidence, not the wording. Word-perfect answers sound rehearsed, and the interviewer's next question moves off-script anyway.

## Workflow 6: Negotiation, stated plainly

- **Know the band before the conversation.** Public levelling data, the recruiter's own stated range, and pay-transparency postings for the same level and city. Enter with a number derived from evidence, not from what the current salary happens to be.
- **Do not anchor first if it can be avoided.** "What is the band for this level?" is a normal question and asking it costs nothing. If pressed twice, give a researched range with its reason, and make the bottom of the range a number that would still be accepted.
- **Negotiate the package.** Base, bonus, equity and its strike or vesting terms, sign-on, start date, notice buyout, remote and travel expectations, on-call compensation, title and level, learning budget. Level is the highest-leverage item and the hardest to change later.
- **One consolidated ask, not a drip.** Send everything at once, in writing, with a short reason for each item.
- **Get it in writing before resigning.** A verbal offer is a plan. The signed offer letter with the agreed numbers is the job.
- Never invent a competing offer. It is checkable, it is a common bluff, and it ends the relationship badly.

## Awkward facts

A gap, a layoff, or a career change is fine and needs one calm sentence, in the user's own voice, followed by moving on. "I was in the 2025 platform-org layoff; I took two months to finish an AI-enablement project I had been putting off, and I have been interviewing since October." No apology, no over-explaining, no defensive framing — length signals discomfort more than the fact ever does. For a career change, lead with the transferable evidence and name the deliberate reason for the move in one line.

## Standard output format: tailored CV section

```text
## Selection rationale
Role is hiring to solve: [one sentence hypothesis from Workflow 1]
Promoted: [bullets moved up and why] · Cut: [what was dropped and why]

## Senior Platform Engineer — Company (MM/YYYY - MM/YYYY)
- [outcome-first bullet, metric present]
- [outcome-first bullet, metric present]
- [bullet with [TK: metric] placeholder]

## Placeholders to fill
- [TK: metric] in bullet 3 — roughly how many services were on the old pipeline?
- [TK: metric] in bullet 5 — what did the monthly spend drop to?

## Not claimed
- JD asks for Go service development; nothing in your history supports it. Left out.
```

## Standard output format: interview-prep pack

```text
## The role's real problem
[one or two sentences]

## Your three strongest stories for this loop
1. [story] → maps to [requirement], tail: [what you would do differently]

## Likely questions, with the evidence to reach for
- [question] → [story], watch for: [the follow-up they will ask]

## System design: likely prompts
- [prompt] → constraints to raise first, failure modes to volunteer

## Gaps to handle
- [requirement not met] → honest framing in one sentence

## Questions to ask them
- [question] → what the answer tells you
```

## Anti-patterns

- **Inventing a metric.** The number that makes a bullet land is the number that gets probed in the interview. `[TK: metric]` costs one message; a fabricated 40% costs the offer.
- **Keyword-stuffing.** Skills sections listing thirty technologies read as noise to the human and buy nothing from the parser. Every listed technology is fair game for a question.
- **Responsibilities instead of outcomes.** "Responsible for the Kubernetes platform" describes a job that existed, not a person who changed anything. At senior level this is the single most common reason a CV reads as junior.
- **One generic CV for everything.** It is optimised for no reader, and it signals that the applicant did not spend twenty minutes on the JD.
- **A dozen divergent CVs.** The opposite failure: master document plus per-application selection, or the achievements diverge and none of them stay current.
- **Rehearsing to a script.** Memorised answers sound memorised, and they break as soon as the interviewer asks the second question. Rehearse the story and the tail, not the sentences.
- **Writing in a voice the candidate cannot sustain.** If a bullet or a cover note uses vocabulary the user would not say aloud, rewrite it in theirs. The room is the reference check for the document.

## Reference files

- `references/cv-patterns.md` — read for Workflows 2 and 3: bullet patterns by achievement type, before/after examples for infrastructure work, CV section order for a senior or lead candidate, ATS mechanics without superstition, length norms, and what to do with contracting, short tenures and side projects.
- `references/interview-bank.md` — read for Workflow 5: the behavioural and leadership question bank a senior loop draws from, system-design prompts for infrastructure topics with an evaluation rubric, the follow-up questions each answer invites, and the questions worth asking the interviewer.
