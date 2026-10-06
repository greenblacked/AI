# Usability test kit

Read this while planning and running a round, at steps 2 to 6 of `SKILL.md`.

## Contents

- Screener
- Task-writing rules, with examples
- Session script
- Think-aloud practice task
- SUS form and scoring
- Findings log

## Screener

Screen on behaviour, since that is what predicts how someone uses the product. Ask four or five questions, none of which reveals the right answer.

1. What do you do for work, and how often do you do the task this product supports?
2. Which tools do you use for it today?
3. When did you last do it, and what happened?
4. Do you, or does anyone close to you, work on or for this product or a competitor? (Exclude.)
5. Can you take part at the time and on the device we need, and can we record the screen and your voice for the team's notes only?

Recruit one or two more than the plan needs, because someone will not turn up. If you have distinct user groups, screen for the group and keep the counts per group as step 2 of `SKILL.md` gives them.

## Task-writing rules, with examples

1. State a goal in the user's situation, not an action in the interface.
2. Do not use a label, menu name, icon name or page title that appears in the product.
3. Give only the information the user would already have: names, dates, amounts. Put it on a card, not in your head.
4. Make the end state observable, so you can tell whether it was reached without asking.
5. Write the success criterion, the partial credit and the stop rule (a time limit, or three failed attempts) before the first session.
6. Put the primary task first. Keep the number of tasks small enough that no one hurries.

| Poor | Why | Better |
| --- | --- | --- |
| Click Account, then Billing, and update your card. | Names the path. | Your card expires next month. Make sure the next payment will go through. |
| Find the pricing page. | Names the page. | You are deciding whether the team plan is affordable for six people. Find out what it would cost. |
| Use the search to find a red jacket. | Names the feature and gives the answer. | You need a jacket for the rain. Find one you would consider buying. |
| Check whether the form is easy. | Asks for an opinion, not a goal. | Register your team for the event on 12 June. |

Example record for one task:

```text
Task 3: Your Friday appointment needs to move to the following week. Do that.
Start state: signed in, one booked appointment on Friday.
Success: new date shown on the confirmation, old date released.
Partial: new booking made, old booking left in place.
Stop: five minutes, or the participant says they would give up.
```

## Session script

Read the introduction as written, so every participant hears the same thing.

Introduction.

"Thanks for coming. We are testing the product, not you, so you cannot do anything wrong. If something is confusing, that is useful for us to know. I will give you some tasks to do. Please think aloud as you go: say what you are looking at, what you expect and what you are thinking, including when you are unsure. I will not be able to help or answer questions during the tasks, because I want to see what you would do on your own, but I will answer anything afterwards. You can stop at any time. Is it all right if we record the screen and your voice? The recording is only for our notes."

Then, in order:

1. Consent signed or recorded. Start recording.
2. Two or three background questions about how they do the task today.
3. Think-aloud practice (below).
4. Tasks, one at a time. Hand over the card, read it aloud, say "begin when you are ready".
5. After each task, one question: "How did that go?" Then move on.
6. The SUS form, immediately after the last task.
7. Short debrief: what was hardest, what was easiest, what they would change. This is where the discussion goes, after the scores.
8. Thank them, and pay or reward as promised.

Moderator rules during tasks:

- Do not explain, hint or confirm. Do not say "good" or "right".
- Silence is fine. Count to ten before you say anything.
- If the participant goes quiet, say "keep talking" or "what are you thinking now?".
- If they ask a question, return it: "What would you expect?" or "What would you do if I were not here?".
- If they stop being able to continue, ask once whether they would give up, note it as a failure and move to the next task.
- Note what they do and say. Interpretations go in a separate column.

## Think-aloud practice task

Use something unrelated to the product, so they learn the habit before it matters: "Using this recipe site, find how long a lasagne takes, and tell me what you are thinking as you go." Let them try for a minute. If they are silent, prompt with "keep talking" and then stop prompting.

## SUS form and scoring

Give each participant the ten statements, each answered on a scale from 1 (strongly disagree) to 5 (strongly agree). Replace "system" with the product name if you wish.

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

Scoring, per participant:

- Each odd-numbered item contributes its score minus 1.
- Each even-numbered item contributes 5 minus its score.
- Add the ten contributions and multiply the sum by 2.5. The result is from 0 to 100.

Worked example. A participant answers items 1 to 10 as 5, 2, 4, 1, 4, 2, 5, 1, 4, 2. The odd items (5, 4, 4, 5, 4) contribute 4, 3, 3, 4, 3, which is 17. The even items (2, 1, 2, 1, 2) contribute 3, 4, 3, 4, 3, which is 17. The sum is 34 and 34 times 2.5 is 85.

Average the participants' scores for the round. The average SUS score is 68, and a score under 51 is roughly in the bottom 15 percent (source: <https://measuringu.com/sus/>). SUS is a 0 to 100 score and not a percentage. With five participants, use it to see whether a fix round moved the number in the right direction, not to claim a ranking.

## Findings log

One row per distinct problem, filled in after each round.

| ID | Problem (what happened) | Participants | Evidence (quote or timestamp) | Cause | Severity 0 to 4 | Smallest fix | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | Four of five did not find where to change the date | P1, P2, P4, P5 | P2 at 06:12, "where would a date even be" | The date is behind the appointment title, which does not look clickable | 3 | Add an explicit Change date control on the appointment card | To fix |

Severity guide: 0 not a usability problem at all, 1 cosmetic problem only, 2 minor (low priority), 3 major (high priority), 4 catastrophe (imperative to fix before release). Severity combines frequency, impact and persistence: how many people met it, how much it hurt, and whether they could get past it once they knew.

Fix the 3s and 4s, then run the next round and mark each row Fixed, Still happening or Replaced by a new problem.
