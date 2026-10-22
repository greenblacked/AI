---
name: tacit-knowledge-elicitation
description: "Extract what a departing or overloaded expert knows but has never written down, as decision rules rather than a transcript. Asking \"what do you know\" omits the judgement; instead run three recorded 45-minute critical-incident interviews, each built on a real past case, asking what they checked first and why, what a novice would miss and what would have made them change course. Turn answers into rules of the form \"if X, look at Y first because Z\", then verify by giving the rules to a second person to run against a past case and fixing what they get wrong. Use when someone says \"our only DBA is leaving in a month\", \"capture what she knows about the billing batch\" or \"bus factor of one on this system\". Not for writing the document (technical-docs), a procedure for a known failure (runbook), finding single points of knowledge across a team (team-skills-matrix), one incident review (postmortem) or handover by doing (shadow-reverse-shadow)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Tacit Knowledge Elicitation

Elicitation is finished when a second person, given only the decision-rule sheet, handles a past case the way the expert did, and the rules they got wrong have been corrected.

The usual failure is the open question. "Tell me everything you know about the billing batch" produces an organised lecture of what the expert thinks is important, which is the part that was already writable. The judgement lives in what they do first, what they ignore and what makes them change their mind, and they cannot report it in the abstract because it has become automatic. A real past case brings it back, because the expert reconstructs what they did and the gaps show.

## Scope

Use for: an expert leaving, going on leave or overloaded, where the knowledge is judgement about a system or process, and it is mostly in one head.

Do not use for: writing documentation of how a service works (`technical-docs`), a step-by-step procedure for a failure you already understand (`runbook`), a single blameless incident write-up (`postmortem`), or a handover where the expert has time to run the learner through the work (`shadow-reverse-shadow`). Finding who is a single point of failure across a team is a prior step handled by `team-skills-matrix`; this skill starts once one person and one system are named.

## Workflow

### 1. Choose the cases before the interviews

List the past cases to build on: the last three times the system broke, a near miss, a change that went badly, an odd customer request. Ask colleagues and look at tickets, chat history and incident records, so the expert is not choosing the flattering ones. Pick three that differ: a common failure, a rare one, and one where the expert was wrong or surprised. Collect the artefacts for each (ticket, graphs, logs, commit, message thread) and bring them to the session. Read `references/interview-kit.md` for the case selection sheet and question script.

### 2. Run three 45-minute interviews, recorded

One case per session, with the expert's consent to record. Recording keeps the interviewer free to listen and follow up. Open with: "Walk me through the last time this broke." Let the story run, then go through it again slowly, step by step, with the artefacts open. Keep to 45 minutes; fatigue turns precise recall into summary.

At every step ask the same four questions:

1. What did you check first, and why that?
2. What did you ignore, and how did you know you could?
3. What would a novice have missed or got wrong here?
4. What would have made you change course, and what did you see that told you?

Ask for the observable: which graph, which log line, which number. "It felt wrong" is a lead, not an answer; follow with "what did you see that made it feel wrong?"

### 3. Turn answers into decision rules

After each session, extract rules in the form "if X, look at Y first because Z". X must be something a person can observe, Y a concrete place or action, Z the reason, since the reason is what lets the next person recognise a case that does not quite match. Mark each rule with the case it came from and the artefact that shows it. Keep exceptions with the rule they qualify, for example "unless the batch ran late, in which case...". Discard anything that is only a fact about the system; facts belong in the documentation.

Send each rule list back to the expert within two days for correction. They remember what they left out soon after they see it written.

### 4. Verify with a second person

Pick a past case the interviews did not use, and give a colleague the rule sheet and the case artefacts up to the point of the first symptom. Ask them to say what they would check first, and then next, aloud. Compare with what the expert actually did. Every difference is one of three things: a missing rule, a rule with a vague X, or a rule without its reason. Fix the sheet, and run a second held-out case if time permits. If the second person cannot use a rule, the rule is not finished, whatever the expert thinks of it.

### 5. Link rules to artefacts and file them

The output is a decision-rule sheet linked to the artefacts: dashboards, queries, alert names, repositories, tickets. Not a transcript. Keep the recordings and transcript stored separately as source material and say where. Put the sheet where the on-call or maintenance team looks first, and name an owner who keeps it current. A rule that the next case disproves is edited, with the date.

## Hand back

The decision-rule sheet, grouped by symptom, each rule with its observable trigger, first action, reason, source case and artefact link; the list of cases used and the held-out case; the verification result with what the second person got wrong and how the sheet changed; and the open gaps, meaning areas the expert could not or did not cover. State plainly what was not captured.

## Anti-patterns

- **Asking for a brain dump.** It captures the document the expert would have written anyway.
- **Interviewing about a hypothetical.** "What would you do if X broke" gets the textbook answer. Use an incident that happened.
- **Polishing the transcript.** A tidy transcript feels like progress and cannot be used at 3 a.m.
- **Skipping verification.** A rule only the author can apply is a note. Test it on a second person.
- **Capturing everything.** Rank cases by cost of failure and capture the costly ones; the long tail can wait.

## Reference files

- `references/interview-kit.md` - read at steps 1 to 3: the case selection sheet, the interview script with follow-up probes, the rule-writing template with examples, and the verification scoring sheet.
