# Interview bank: senior infrastructure and platform loops

## Contents

- How to run a rehearsal
- Behavioural questions: delivery and technical judgement
- Behavioural questions: conflict, influence and people
- Leadership-loop questions
- The follow-ups each answer invites
- System-design prompts for infrastructure
- System-design rubric
- Incident and debugging rounds
- Questions worth asking the interviewer
- Salary and offer conversations, verbatim lines

## How to run a rehearsal

One question per message. Let the user answer in full before saying anything. Then give
feedback in this order: what the answer proved, the specific defect, the follow-up a real
interviewer would now ask. Defects worth naming explicitly, because they are the common ones:

- No result. The story ends when the work ends rather than when something changed.
- "We" throughout, so the user's own contribution is invisible.
- Three minutes of setup before the first action.
- No tail — no reflection on what would be done differently.
- Answering the question they wish had been asked.

Do not grade generously. "That was good" costs the user the real loop.

## Behavioural: delivery and technical judgement

1. Walk me through the most complex migration you have owned end to end.
2. Tell me about a time you chose the boring technology over the interesting one.
3. Describe a system you designed that did not survive contact with production.
4. Tell me about a technical decision you made with insufficient data. How did you bound the risk?
5. What is the largest amount of technical debt you have deliberately taken on, and how did you pay it back?
6. Tell me about a time you had to say no to a deadline.
7. Describe how you reduced toil for a team. How did you know it worked?
8. Tell me about a project you cancelled or stopped. Who decided, and how?
9. What did you build that people did not adopt, and why not?
10. Tell me about a time you were wrong about a piece of architecture.
11. How have you handled a dependency on a team that would not prioritise you?
12. Describe the worst on-call rotation you have been part of and what you changed about it.

## Behavioural: conflict, influence and people

1. Tell me about a disagreement with a senior engineer where you did not get your way.
2. Describe a time you had to convince a sceptical team to adopt something.
3. Tell me about feedback you received that you initially rejected.
4. Describe a situation where you had to work with someone you found difficult.
5. Tell me about a time you escalated. What did you try first?
6. How have you handled a peer who was blocking a decision by not deciding?
7. Describe a time you had to deliver bad news to a stakeholder.
8. Tell me about a time you changed your mind because of someone more junior.

## Leadership-loop questions

1. How do you decide what a platform team should build next?
2. Tell me about someone you managed who was underperforming. What happened?
3. How do you set direction when the strategy above you is unclear?
4. Describe how you have run an incident review that changed behaviour rather than producing a document.
5. How do you measure whether a platform team is succeeding?
6. Tell me about a hire you got wrong.
7. How do you balance hands-on work against leading, and how has that split moved?
8. Describe how you introduced a practice across teams you did not own.
9. What is your approach to on-call fairness and compensation?
10. How do you decide what to standardise and what to leave to teams?
11. Tell me about a time you had to reduce scope or headcount.
12. How do you keep technical credibility while spending less time in the code?
13. For AI enablement specifically: how did you decide what to roll out, and how did you handle the engineers who did not want it?

## The follow-ups each answer invites

The tail is where senior loops are won or lost. Prepare for these, because they are asked
every time:

| The answer given | The follow-up | What is being tested |
| --- | --- | --- |
| A successful migration | "What would you do differently?" | Reflection and honest assessment |
| A metric | "How was it measured, and by whom?" | Whether the number is real |
| "I convinced them" | "What was their strongest argument?" | Whether the disagreement was understood |
| A failure | "What did you notice too late?" | Self-awareness without self-flagellation |
| A design decision | "What did you give up to get that?" | Trade-off literacy |
| "The team adopted it" | "Who did not, and why?" | Honesty about partial success |
| A leadership story | "What did the person say afterwards?" | Whether the outcome was actually checked |

## System-design prompts for infrastructure

Pick one and run the full loop, 35-45 minutes, interrupting as an interviewer would:

1. Design the deployment platform for 200 services across three regions.
2. Design a multi-tenant Kubernetes offering with hard isolation between tenants.
3. Design CI for a monorepo where a full build takes 90 minutes.
4. Design secrets management for an organisation moving off long-lived cloud keys.
5. Design an observability stack under a fixed budget, with retention as an explicit trade-off.
6. Design a zero-downtime migration of a stateful primary database to another provider.
7. Design an autoscaling strategy for a workload that blocks on a slow third-party API.
8. Design a disaster-recovery plan with a four-hour RTO and a fifteen-minute RPO, and say what it costs.
9. Design the rollout mechanism for a change that cannot be canary-tested.
10. Design the ingestion path for an internal AI assistant over private company documents, with access control preserved.

## System-design rubric

Score the rehearsal on these, and say which one was weakest:

- **Requirements before architecture.** Scale, latency, consistency, budget, compliance,
  team size. A candidate who draws boxes in the first two minutes has skipped the job.
- **Explicit non-goals.** Naming what the design does not solve is a senior signal.
- **Failure modes volunteered, not extracted.** What happens when this component dies, when
  the network partitions, when the dependency is slow rather than down.
- **Blast radius and rollback.** How a bad change is detected and undone, and how big the
  worst case is.
- **Operability.** Who runs it, what pages, what the runbook says, what it costs per month.
  Infrastructure loops weight this heavily and candidates consistently underweight it.
- **The 10x question.** What breaks first at ten times the load, and what the fix would be.
- **Trade-offs stated as trade-offs.** Every "we would use X" needs "which costs us Y".

## Incident and debugging rounds

Common shape: "Deploys are fine, but p99 latency tripled at 14:00 and error rate is flat.
Go." What is being assessed is method, not the answer.

- State the hypothesis space before touching anything: recent change, dependency, resource
  exhaustion, traffic shift, noisy neighbour, expiry (certificates, tokens, disk).
- Say what signal would discriminate between hypotheses before asking for it.
- Distinguish mitigation from diagnosis, and say which one you are doing. Senior candidates
  mitigate first and say so.
- Say when you would call for help, and who.
- Close with what you would change so this class of incident does not recur.

## Questions worth asking the interviewer

Aim for the ones whose answers cannot be rehearsed by the interviewer:

- What does the on-call rotation look like this month — how many pages, and at what hours?
- How often do you deploy, and who presses the button?
- What was the last significant incident, and what actually changed afterwards?
- Where do technical decisions get written down, and can you show me an example?
- What is the split between platform work and product support requests for this team?
- Why is this role open?
- What does success look like at ninety days for whoever takes it?
- What is the thing about working here that people find hardest?
- How much of the team's time goes to keeping the lights on versus new capability?
- Who would I be disagreeing with most often, and about what?

Listen for hesitation and for answers phrased as intentions ("we are moving toward…") rather
than facts. A team that cannot name its deploy frequency does not deploy often.

## Salary and offer conversations, verbatim lines

Useful phrasings, said plainly and then followed by silence:

- Asked for expectations early: "What is the band for this level? I would rather calibrate to
  your range than guess at it."
- Pushed a second time: "Based on the market for this scope in [city], I am looking at
  [range]. Where does that sit against your band?"
- Receiving an offer: "Thank you — I would like a couple of days with it. Can you send the
  full package in writing, including [equity terms / bonus structure / on-call arrangement]?"
- The consolidated ask: "I am ready to sign. Two things would make it straightforward:
  base at [number], because [reason], and the level at [X] given the scope we discussed."
- Closing: "If we can agree those, I will accept today."

Do not reference a competing offer that does not exist, do not negotiate over three separate
messages, and do not name a number the user would refuse if it were accepted immediately.
