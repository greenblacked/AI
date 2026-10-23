---
name: shadow-reverse-shadow
description: "Hand a recurring duty such as releases, deploys, on-call, a monthly close or a vendor relationship to another person safely, by doing rather than telling. Four dated rungs, each with a written gate of three to five observable actions and a count: watch with narration, assist, do-with-watcher (reverse shadow, where the owner only observes and intervenes by an agreed signal), then solo with an escalation path. Defines in advance what fails a run and the rollback, has the learner patch the runbook as they go, and ends with the owner signing the last rung. Use when someone says \"train someone to cover my on-call\", \"I'm going on leave, who can run the release\" or \"cross-train the second person on this\". Not for a new joiner's on-call prerequisites (onboarding-plan), writing the document (runbook), or capturing what an expert knows when no handover is possible (tacit-knowledge-elicitation)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Shadow, Reverse Shadow

A handover is finished when a second person has run the duty alone, to the owner's standard, on real work, and the owner has signed that in writing.

The usual failure is the single walkthrough followed by "ping me if anything breaks". The learner watched one calm run, never touched the controls, and meets the first odd case alone at night. The second failure is "when ready": no rung has a date or a test, so the handover drifts until the owner's leave starts. This procedure replaces both with four rungs, each with a gate you can observe and a date.

## Scope

Use for: a recurring or on-demand duty with real consequences that one person currently holds, where the owner has some weeks and can run the duty alongside the learner.

Do not use for: a new joiner's on-call prerequisites (`onboarding-plan`), writing or fixing the procedure document (`runbook`), or recovering knowledge from an expert who has no time to run the ladder (`tacit-knowledge-elicitation`). A coding session between two developers is not a recurring duty.

## Workflow

### 1. Fix the scope and the dates before the first session

Write down the duty in one paragraph: what it covers, how often it occurs, what a bad outcome costs and who is told when one happens. Work back from the owner's last available day and give every rung a date, with the signing date at least a week before that last day. If the duty only occurs monthly, count occurrences, not weeks: a monthly close with three months of runway has three runs in total, and the plan must say which run belongs to which rung. When the duty occurs too rarely to fit all four rungs, use a rehearsal on a copy or staging environment to stand in for the missing runs and say so in the plan.

Name the learner, the owner and the escalation contact who will exist after the owner leaves. Without a named person, the final rung has nothing to escalate to.

### 2. Define failure and rollback in advance

Write what makes a run fail, and what is done then, before anyone runs anything. Failure is an observable event, not a feeling: a step skipped, a customer-visible error, a wrong figure posted, an action taken outside the stated scope, an escalation that came too late. Write the rollback or the stop condition for each. A learner who does not know the boundary either freezes or improvises; both are avoided by writing it down. Read `references/gates-and-templates.md` for the failure table and the rung-gate template.

### 3. Rung 1, watch

The owner does the duty on real work while narrating what they are looking at and why they chose each action. The learner writes down questions instead of interrupting, then the pair goes through them afterwards. The gate is observable on the learner's side: they can list the steps in order, name the decision points, and say what the owner checked before each risky action. Count one watched run per distinct case, for example a clean run and a run with a known snag.

### 4. Rung 2, assist

The learner holds the controls for the routine parts while the owner keeps the risky ones. Hand over in order of increasing blast radius: read-only checks first, reversible actions next, irreversible actions last. The gate is a count of steps done correctly without a prompt, for example two runs in which the learner completes every routine step unprompted. If the owner has to point at the screen, the step has not passed.

### 5. Rung 3, do-with-watcher (the reverse shadow)

Roles swap: the learner runs the whole duty and the owner observes. Agree an intervention signal beforehand, a word or a message, and what each signal means: "pause" stops the learner to discuss, "take over" returns the controls. The owner does not hint, sigh or reach for the keyboard, since a hint the learner did not earn hides a gap that will reappear in the solo run. Log every intervention. The gate is a count of clean runs: for example two consecutive runs with no intervention and no failure condition from step 2. One intervention resets the count.

### 6. Rung 4, solo with an escalation path

The learner covers the duty alone for a defined window, with the owner reachable under stated terms: who is called, for what, how fast they answer, and what the learner does while waiting. A test of the escalation path itself belongs in the rung: the learner pages or messages the contact once in a drill, before it matters. The gate is the window completed with no failure condition, or a failure handled by the written rollback.

### 7. Let the learner patch the runbook as they go

At every rung the learner edits the procedure document: a missing step, an unclear instruction, a wrong command. Edits made by the person who needed the information are better than edits made by the person who has forgotten what it was like not to know. The owner reviews each edit for correctness, not style. The runbook the learner leaves is evidence for the final sign-off; if it is unchanged, either the document was perfect or the learner was not reading it.

### 8. Sign off

The owner signs the final rung only against the written gate, dated, with the run log attached. If a gate was missed, the rung repeats with a new date; the plan does not slide into "close enough". Tell the people who depend on the duty who now holds it.

## Hand back

The plan: duty paragraph, named people, four rungs each with date, gate (three to five observable actions and a count), failure conditions and rollback; the intervention log; the runbook diff; the dated sign-off. Report which rungs passed on schedule and which were repeated.

## Anti-patterns

- **"When ready".** A rung with no date and no count passes on the owner's mood. Give both.
- **Gates that measure attendance.** "Attended three runs" is not a gate. "Completed the rollback unprompted" is.
- **The owner as safety net.** An owner who quietly fixes things during the reverse shadow means the solo run will fail. Intervene by signal and log it.
- **Only clean runs.** A learner who has never seen the known snag has not been trained for the duty. Include one run with a rehearsed fault.
- **Handing over the duty and the authority separately.** If the learner lacks access, approvals or the right to roll back, the gate cannot be met. Check access before rung 2.

## Reference files

- `references/gates-and-templates.md` - read at steps 2 to 5: the failure-condition table, a gate template with worked examples for on-call and a monthly close, the intervention-log format and the sign-off record.
