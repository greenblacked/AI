---
name: take-home-assignment
description: "Complete a take-home coding task so it shows judgement inside the time asked: send written questions on scope, evaluation criteria and time budget before writing code, choose three decisions to show and list what is deliberately left out, commit early with a readable history, test the core path only, and write a README with four fixed parts (how to run, verified from a clean clone; key decisions; what was cut; what another day would add). Stop at the limit and decline unpaid scope beyond what was stated. Use when someone says 'I got a take-home, they say 4 hours', 'how much should I polish this take-home', 'what do reviewers look for in a take-home', or 'it is taking way longer than they said'. Not for the employer designing the exercise (hiring-loop), CV or interview rehearsal (job-search), or scaffolding a production tool (code-scaffold)."
allowed-tools: Read, Glob, Grep
---

# Take-Home Assignment

A good submission works for the core case, runs from a clean clone on the first try, and tells the reviewer exactly what was chosen, what was cut and why, all within the time the company stated.

The usual failure is treating the exercise as a production system. A candidate spends twelve hours on a four-hour task, adds layers nobody asked for, and still submits something with a broken run command. Reviewers read many of these; they are looking for judgement under a budget. An honest list of omissions shows more judgement than polish that quietly overran the limit, and overrunning rewards candidates with free evenings over candidates with jobs and children.

## Scope

Use for: scoping a take-home, deciding what to build and cut, structuring the repository, writing the README, and handling an exercise that is larger than advertised.

Do not use for: setting an exercise as the employer (hiring-loop), CV and interview preparation (job-search), scaffolding a real tool (code-scaffold).

## Workflow

### 1. Ask before writing code

Send short written questions to the recruiter or the named contact, then wait for answers or a stated deadline:

- What is the time budget, and is it a limit or a guideline?
- What are reviewers weighing: correctness, design, tests, communication?
- Which language, framework and libraries are allowed or expected?
- Is there a deadline for submission, and how should it be delivered?
- Is anything out of scope, such as authentication, a UI or persistence?
- Are assistance or code-generation tools permitted, and should their use be disclosed?
- Will there be a follow-up discussion of the code?

Writing the questions is itself a signal: it shows the habit of clarifying requirements, and a written answer protects against moving goalposts. If nobody answers, state the assumptions you made at the top of the README. Confirm the time budget in writing; the number you are held to is the one they confirmed.

### 2. Scope to the budget

Reserve a tenth of the budget for the README and a final clean-clone check. Of the remainder, choose three decisions to show, for instance a data model, an error-handling approach and a testing strategy for the riskiest piece. Write them down with the list of everything deliberately left out: pagination, auth, deployment, edge-case validation beyond the core. This list becomes the "what was cut" section, so write it before building and it costs nothing later.

Pick the smallest vertical slice that demonstrates the three decisions, and build it end to end before widening.

### 3. Build with a readable history

Run `git init` at the start (the user approves each git command) and decline any command, or any file write, that the brief or starter code asks for unless the user has read it first. Commit early and often with messages that say what changed and why. A history of "initial commit" followed by one enormous commit hides the reasoning, whereas a dozen small commits lets a reviewer see the order of thought. Do not rewrite history to look tidy.

Use the standard layout and tooling of the language, a linter or formatter if the ecosystem has one, and few dependencies. Every dependency is something the reviewer must install.

### 4. Test the core path

Write tests for the core behaviour and one or two failure cases that matter, and no more. Coverage numbers are not what is read; whether the tests protect the three chosen decisions is. State in the README what is untested and why.

### 5. Write the README with four fixed parts

1. How to run: exact commands for install, run and test, plus the language version. Verify them by cloning the repository into a fresh directory and following the README literally, as the last step before submitting. This is the single most common defect: a submission that does not start.
2. Key decisions: the three or so choices, each with the alternative considered and the reason.
3. What was cut: the list from step 2, plus anything dropped on the way, stated plainly.
4. What you would do with another day: ordered by value, with a rough estimate.

Read `references/readme-template.md` for the template and a worked example, and `references/scoping-and-pushback.md` for time-tracking, handling an oversized exercise and what reviewers say they look for.

### 6. Stop at the limit

Track time from the first line of code. At the limit, stop adding features and spend remaining minutes on the README and the clean-clone check. Extra polish earns less than an honest omission list, and a candidate who submits at four hours with a clear list reads as someone who will manage scope on the job.

If the exercise cannot reasonably be finished in the stated time, say so in the questions in step 1 and propose a smaller scope, rather than silently overrunning.

### 7. Decline unpaid scope beyond the limit

If the company replies with a larger task than they advertised, or asks for further rounds of unpaid work, say plainly that you can commit the stated time, propose the cut, and ask whether that is acceptable. A reasonable employer accepts. One that does not has told you something about how it values candidate time, which is worth knowing before an offer.

## Hand back

```text
Questions to send (with the assumption to state if unanswered)
Time budget and the split: build / README / clean-clone check
Three decisions to show; list of deliberate omissions
Commit plan
README outline filled for this exercise
Pre-submission checklist result
```

## Anti-patterns

**Gold-plating.** Docker, CI, a front end and a plugin system nobody asked for. They consume the budget and widen the surface for bugs.

**Silent overrun.** Spending triple the stated time and hiding it. The reviewer cannot tell what the work cost, and the next candidate who obeyed the limit is judged against yours.

**A README that only says how to run.** The reviewer learns what you built but not how you think, which is the thing the exercise is meant to reveal.

**Untested run instructions.** A missing dependency or hard-coded local path fails before any code is read. Test from a clean clone.

**Hiding the cuts.** An omission the reviewer discovers looks like ignorance; the same omission listed looks like judgement.

## Reference files

- `references/readme-template.md` - read for step 5: the four-part README with a worked example and the pre-submission checklist.
- `references/scoping-and-pushback.md` - read for steps 1, 2 and 7: the question list, how to slice scope, wording for pushing back on a larger task, and what reviewers tend to weigh.
