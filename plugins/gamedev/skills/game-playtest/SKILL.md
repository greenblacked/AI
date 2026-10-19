---
name: game-playtest
description: "Run a game playtest so it ends in decisions rather than opinions: write one question per session tied to a design goal, recruit the target player instead of friends, observe in silence and record behaviour (deaths, quits, time to first success, where they look) before asking, choose think-aloud or retrospective narration knowing what each distorts, follow with a short survey on fixed scales, separate bugs from design findings, triage bugs by severity and reproducibility into the tracker with repro steps and build id, and turn findings into a short ranked change list with the metric that would show each fix worked. Use whenever someone is planning, running or writing up a playtest, a demo-day session or a closed alpha. Not for win-rate tuning (game-balance), level layout (game-level-design), concept go or no-go (game-greenlight), or usability tests of product UI (usability-test-plan)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Game Playtest

A playtest is finished when the question written before it has an answer, every problem seen is either a filed bug or a ranked design change, and each change names the measurement that will show whether it worked.

Most playtests fail before the first tester sits down. The question is "is it fun?", so nothing the session produces can decide anything. The testers are friends, who are kind and who already know what the game is meant to be. The observer talks, so the session measures how well the observer explains. The notes mix what happened with what it meant, and bugs with design problems, and the pile that comes out is read once, remembered selectively and acted on by whoever argues best. This skill puts the order right: question, right people, silent observation, behaviour before opinion, sorted findings, a short ranked list with a prediction attached.

## Scope

Use for: planning a playtest session or a round of them, choosing and screening testers, deciding what to record, choosing think-aloud or retrospective narration, writing the post-session survey, sorting what came out into bugs and design findings, filing the bugs, and writing the ranked change list that the next round tests.

Do not use for:

- Tuning numbers from win rates, pick rates or attempt counts. A handful of testers cannot separate a small difference from noise; that is `game-balance`, which also takes the findings of a session that point at a number.
- Laying out or re-pacing a level. Watching people fail to find the exit is a playtest finding; moving the exit is `game-level-design`.
- Deciding whether a concept is worth building, or what a prototype must prove. That is `game-greenlight`, and its criteria come before any session.
- Usability tests of product UI: settings, accounts, checkout, a storefront, a launcher. The boundary is what friction means. In a game, difficulty, confusion and failure are sometimes the intended experience, so task success is the wrong measure of in-play behaviour; in a product screen the user has a goal outside the interface and friction is a defect. Use `usability-test-plan` for the second, and this skill for what happens while the game is being played. A game's menus and settings screens belong to the second even inside a game.
- Finding the cause of a crash. A tester's report starts a bug; `debugging` finishes it.

## Workflow

### 1. Write one question and the result that would change the plan

State the design goal the session serves, the single question under it, and what you will do under each answer. "Do first-time players discover that the shield recharges, without being told, in the first level?" is a session. "Is it fun?" is not, and a session built on it can only produce opinions.

Write the pass line before the first tester arrives: what you will see if the answer is yes, what if no, and what counts as unclear. A line drawn after the recordings exist is drawn around the outcome you already prefer. Do not add a second question to use the tester's time; each one changes what you can say to them and what you watch for.

Read `references/session-plan.md` for the question template, the screener and the record sheet.

### 2. Recruit the target player, not friends

Write down who the game is for: the genre they play now, the platform, how much time they give a game. Recruit people who match, and screen on what they did recently ("which games have you played in the last month, and for how long") rather than on whether they like games. Friends, family and colleagues are kind and informed, and kindness is the one signal a playtest cannot use. For a first-session question every tester is single use, so spend them deliberately.

Run a small group, fix, and run another small group on the same script: the second group is the only thing that tests the fixes. Recruit past the number you need, because some will not arrive.

### 3. Choose think-aloud or retrospective before the session, not during it

Asking players to talk while they play changes how they play: speaking competes with playing for attention, so timings stretch and fast games get played more cautiously. Narrating afterwards leaves play natural but the account is reconstructed from memory and tends to be tidier than what happened.

Default for a question about timing, pace or difficulty: silent play, then replay the recording and ask the tester about moments you marked. Use concurrent think-aloud for slow, deliberate games and for questions about comprehension and intent, and accept that its timings are only comparable with other think-aloud sessions. Never mix the two inside one group. The comparison of the two methods is in `references/session-plan.md`.

### 4. Observe silently and record behaviour before asking

Say nothing while they play. When they are stuck, time it. When they ask whether they are doing it right, ask what they would do if you were not there. Do not defend, explain or demonstrate. End early only for distress, or when a bug has made the build unrepresentative, and mark that session partial.

Record what happened, in one column, and what you think it meant, in another, filled in later. The minimum behaviour set: deaths and failures with where and how often, quits and the point they would have quit at home, time to first success, time stuck per stuck moment, where they look (the screen region, or the thing they walked past), questions asked aloud verbatim, features never used and whether they knew it existed. Timestamp every line against the recording and write the build id at the top. "Walked past the door three times" is a record; "did not notice the door" is an inference, and only the first can be checked by a second person.

### 5. Ask afterwards: a fixed-scale survey, then questions tied to moments

Give the survey before any conversation, so the conversation does not shape the answers. Keep it short, with the same items, order and scale anchors every round so rounds can be compared, and tie each item to the question from step 1. Then interview, anchoring each question to a moment you saw: "at the second door, what were you trying to do?" Do not ask "did you like it", "would you buy it" or "what should I add". When a tester proposes a fix, keep the complaint and discard the fix.

Read `references/survey.md` for the item types, the wording rules and how to read five or six sets of answers without pretending they are statistics.

### 6. Separate bugs from design findings

Apply one test to everything that went wrong: did the build do what its author intended? If not, it is a bug. If it did, and the player was confused, bored or stopped, it is a design finding. The two go to different places and are judged differently, and mixing them is how a tracker fills with "players find the tutorial unclear" while real crashes wait. A bug that only matters because it exposed a design weakness gets filed as a bug and cross-referenced from the finding. When it is unclear which it is, record it as a finding; a design problem mislabelled as a bug gets fixed by patching the symptom.

### 7. Triage bugs into the tracker with enough to reproduce

Rate each bug on two axes, severity and reproducibility, and file it the same day with the build id, the platform, the starting state, numbered steps, expected against actual, how often it happened (x of y attempts, not "sometimes"), and the recording timestamp. Search for a duplicate first and add the new evidence to it. A bug seen once is filed as unconfirmed with its evidence, not dropped; a crash, soft-lock or lost save is filed whatever its reproducibility, because it is the one thing a tester cannot work around.

Read `references/triage-and-ranking.md` for the severity scale, the matrix and the bug template.

### 8. Rank the design changes and attach the metric

After the group, count how many testers hit each design finding and what it cost them: a quit or a block outranks an annoyance. A problem several testers hit is a design problem; a problem one tester hit is a person, unless it is catastrophic. Write a list of a few changes, ordered by how many were affected, how severe the consequence was and how cheap the fix is. For each, write the cause you suspect, the change, and the metric from step 4 that would move and in which direction, with the threshold agreed before the next round. Then run the next group on the same script. Changing the script between groups means comparing two different tests.

Read `references/triage-and-ranking.md` for the ranked-list format and how to choose the metric.

## Anti-patterns

**A playtest with friends and a general question.** It feels productive because everyone is pleased, and it produces nothing to act on. The fix is the question in step 1 and the recruit in step 2, not more testers.

**Helping when the tester is stuck.** The time they spend struggling is the finding, and a hint turns the session into a demonstration of the observer. Time it instead.

**Asking before watching.** Opinions asked first are rewritten by the questions that follow, and what was recorded of behaviour is what survives. Record, then survey, then interview.

**One list for everything.** Bugs, design findings and feature requests in one document get ranked by whoever is loudest. Sort them in step 6 and rank only the design findings in step 8.

**A ranked list with no prediction.** A change with no metric attached cannot be shown to have failed, so it stays forever. Name the number that should move before the fix ships.

**Reading five testers as a rate.** Five people show that a problem is possible, not how often it happens. Use counts of testers, never percentages, and send questions about frequency to telemetry.

## References

- `references/session-plan.md` — read at step 1 to write the question and pass line, at step 2 for the screener and at steps 3 and 4 for the think-aloud comparison and the record sheet.
- `references/survey.md` — read at step 5 before writing the survey or reading its answers.
- `references/triage-and-ranking.md` — read at steps 6 to 8 when sorting findings, filing bugs and writing the ranked change list.
