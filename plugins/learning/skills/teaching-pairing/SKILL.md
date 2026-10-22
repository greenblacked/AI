---
name: teaching-pairing
description: "Pair with a junior or newcomer to teach, not to deliver the task through them. The learner drives, always; replace telling with a three-rung ladder of question, hint, then showing, waiting a count of ten before moving up; the learner predicts each run and narrates intent; sessions capped at 90 minutes with a read-only break; close with a transfer check, the learner doing a similar small task alone within 48 hours, recording what they could and could not do unaided; stop pairing on a topic after two solo transfers. Use for \"how do I pair with a new hire without just doing it for them\", \"my pairing sessions end with me typing\", \"teach a colleague this part of the system\". Not for judging a diff (code-review), the long relationship (mentoring-cycle), handing over a duty with gates (shadow-reverse-shadow), the manager's plan (onboarding-plan)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Teaching Pairing

A teaching pair is finished when the learner has done a similar task alone within 48 hours and the pair knows what they could and could not do unaided, not when the task is merged.

The usual failure is that the expert ends up typing. The learner is slower, the expert can see the answer, and taking the keyboard feels like kindness. The ticket closes and the learner has watched someone else work, which teaches little; the next similar ticket comes back to the expert. Everything below protects the learner's hands on the keyboard and the learner's own reasoning.

## Scope

Use for: sessions where one person's purpose is to build another's ability on a part of the system, a tool or a technique.

Do not use for: judging a pull request (`code-review`); the long relationship over months (`mentoring-cycle`); passing a recurring duty such as on-call, with gates and sign-off (`shadow-reverse-shadow`); or the manager's plan for a joiner, including who the buddy is (`onboarding-plan`).

## Workflow

### 1. Pick a task the learner can almost do

Choose a small task, finishable in one session, one step beyond what the learner has done. If it is far beyond, the session becomes a lecture; if it is within reach, it is wasted time. Write down in one line what the learner should be able to do alone afterwards, and the similar task you will use for the transfer check. Decide this before the session.

### 2. Set the rules at the start

Say them aloud: you drive, I navigate; I will ask before I tell; if you are stuck for a while I will give a hint; I will not take the keyboard. Say that questions from me are not a sign you are wrong. The expert's seat is the passenger seat, and the physical arrangement should show it: the learner's machine, the learner's editor and the learner's shortcuts.

### 3. Predict before each run

Before running a test, a command or a deploy, ask the learner what they expect to happen and why. When they are wrong, the gap between the prediction and the result is the lesson, and it is more memorable than any explanation. Ask them to narrate intent while they work ("I am looking in the config because..."), which exposes the model in their head and lets you correct the model, not just the line.

### 4. Climb the ladder, one rung at a time

When the learner stalls, use three rungs in order:

1. **A question.** "What does the error say it wanted?" "Where would that value come from?"
2. **A hint.** Narrow the search without giving the answer: "look at how the other handler registers itself".
3. **Showing.** Only after the first two, and then show a small piece, hand the keyboard straight back and ask them to repeat it in a different place.

Wait a count of ten, silently, before climbing a rung. Ten is a working rule of thumb, not a researched figure. The count feels long and is where most learners find the answer; speaking early takes it from them. Note each time you climbed to rung 3: those are the real gaps, and they go on the record at the end. Read `references/ladder-and-transfer-record.md` for sample questions and hints by situation.

### 5. Time-box and break

Cap a session at 90 minutes. This is a working rule, not a research finding: in practice the driver tires and the learner stops absorbing past about that point. Take a break at about the 45-minute mark if the stall rate rises. Make one break read-only: neither of you touches the code, and the learner summarises in their own words what they did so far. If the summary is thin, that is the next question, and it comes free.

### 6. Close with the transfer check

Before ending, agree the similar small task. Within 48 hours the learner does it alone, with no help from you unless they are blocked for more than 30 minutes, in which case they say what they tried first. Afterwards the pair records, in a few lines: what they did unaided, where they needed help and what kind, and what to practise next. The record is the output of the pairing; the merged change is secondary.

### 7. Stop when two solos pass

Count transfers per topic. When two consecutive solo transfers have passed, stop pairing on that topic and say so; carrying on after that builds dependence. If a transfer fails, pair once more on the specific gap, not on the whole topic, and try another transfer.

## Hand back

The target ability and transfer task chosen before the session; a note of the rung-3 moments; the transfer check result with what the learner did unaided and where they needed help; the next practice item; and whether the topic is now closed (two consecutive solo passes) or open.

## Anti-patterns

- **Taking the keyboard.** The fastest way to teach that you will take it again.
- **Telling first.** The answer given before a struggle is forgotten; one found after is kept.
- **Filling the silence.** Count ten. The silence is thinking.
- **A marathon.** Three hours of pairing produces one good hour.
- **Judging the result instead of the learning.** A merged change with no transfer proves nothing.
- **Never stopping.** Pairing on a mastered topic is a handrail that becomes a crutch.

## Reference files

- `references/ladder-and-transfer-record.md` - read at steps 4 and 6: questions and hints for common stalls, the session plan, and the transfer record template.
