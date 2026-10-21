# Planning the session

Read this before scheduling anyone. Everything here is settled before the first tester sits down and none of it can be repaired afterwards.

## Contents

- [The question and the pass line](#the-question-and-the-pass-line)
- [Recruiting and the screener](#recruiting-and-the-screener)
- [Think-aloud against retrospective](#think-aloud-against-retrospective)
- [The record sheet](#the-record-sheet)
- [Running the session](#running-the-session)

## The question and the pass line

A session answers one question, and the question traces to a design goal that already exists in writing. If it does not trace to one, the goal is the missing piece, not the session.

Fill in this block and keep it at the top of the session notes:

```text
Design goal:     the player should <behaviour or understanding>, by <point in the game>
Question:        Can a <target player> <do or understand X> without help?
Build id:        <the exact build under test>
We will see:     <the observable result that means yes>
Or we will see:  <the observable result that means no>
Unclear when:    <what leaves the answer open, and what we do then>
If yes, we:      <the decision>
If no, we:       <the decision>
```

The last two lines are what make a session produce a decision. A question whose every answer leads to the same next step is not worth a session.

Good questions are about behaviour at a named point: whether players find the way out of the first room, whether they understand why they died, whether they reach the second session. Bad ones are about a quality: fun, polish, feel, "is it good". Break a quality down into the behaviour that would show it. "Is the combat satisfying" becomes "do players choose to fight when they could avoid the encounter".

## Recruiting and the screener

Define the target player from the design goal, not from who is available: what they play now, on what platform, how much time they give a game, and how familiar they are with the genre. A test run on genre veterans reports that the game is clear when it is only familiar, and a test run on newcomers reports that a deliberately deep game is confusing.

Screen on recent behaviour, which people can report, rather than taste, which they will bend toward what they think you want:

- Which games have you played in the last month, and about how long per week?
- On which devices do you play?
- Have you played any game from this list? (include the genre's well-known titles and one invented decoy, and drop anyone who claims the decoy)
- Have you seen this game, or know anyone who works on it?

Leave out anyone who works on the game, anyone close to the people who do, and anyone who has already seen the build. Recruit more people than the session needs, since some will not arrive, and keep the extras out of the room rather than adding them to the group, because a group of mixed sizes cannot be compared with the next one.

Tell every tester the same short framing, usually the sentence that would appear on the store page, and that the game is being tested and they are not. Ask permission before recording, and say what the recording is for and who will see it. For testers under the age of majority where you are, consent comes from a parent or guardian; check the rules for your place and platform rather than assuming.

## Think-aloud against retrospective

| | Concurrent think-aloud | Retrospective narration |
| --- | --- | --- |
| How it runs | The tester talks while playing | The tester plays silently; afterwards you replay the recording and ask about moments you marked |
| Best for | Comprehension, intent, slow or turn-based games, puzzles | Timing, pace, difficulty, fast action games |
| What it gives you | The reason at the moment of the action | Natural play and clean timings |
| What it distorts | Speaking competes with playing, so timings stretch and fast play becomes cautious. Talking also pushes people to explain themselves, which can change what they do | The account is rebuilt from memory and tends to be tidier than what happened. The replay is the corrective |
| Extra cost | Needs a prompt when they fall silent, which is a small intrusion | Roughly doubles the session, because you watch it twice |

Choose by the question from step 1. If it concerns time, pace or difficulty, use retrospective. If it concerns why, use think-aloud. If it concerns both, split the testers into two groups of the same kind and say in the notes which group each belongs to.

Two rules that follow. Timings from think-aloud sessions are only comparable with other think-aloud sessions, and a change in method between rounds is a change in the test. And when a think-aloud tester goes quiet, say "keep talking" and nothing else; do not ask what they are thinking, which turns them to look at you.

## The record sheet

One sheet per tester, build id at the top, one line per event, a timestamp that matches the recording. Two columns: what happened, and what it might mean. Fill the second one after the session, never during.

What happened, at minimum:

| Record | Why it matters |
| --- | --- |
| Deaths and failures: where, how many, how each happened | The attempt count is a better measure of difficulty than any answer to "was that hard" |
| Quits: where, and where they say they would have quit at home | The quit point is the nearest thing to retention a single session offers |
| Time to first success at the thing the question names | The one number that compares across testers and across rounds |
| Time stuck, per stuck moment, and how they got unstuck | The unit of confusion |
| Where they look: the screen region, the thing they ignored, the thing they stared at | Shows what the game communicated before they say anything |
| Questions asked aloud, verbatim | Each one is a gap in what the game teaches |
| Features never used, and whether they knew it existed | Separates "not discovered" from "not wanted" |
| Confident mistakes against hesitant ones | A confident mistake is a design problem; a hesitant one is a clarity problem |
| Build faults: crashes, soft-locks, anything the author did not intend | Goes to the bug list in step 7, not into the findings |

Write the observation, not the conclusion. If you catch yourself writing "confused", write what you saw: stopped moving, reread the prompt twice, opened the menu and closed it.

## Running the session

- Play the build yourself start to finish that morning. A crash in the first two minutes costs the session.
- Have a reset: a clean profile or a save state, so every tester starts from the same place.
- Sit beside and slightly behind, out of the eyeline, where you can see hands and screen together; hands show hesitation before anything happens on screen.
- Record the screen and the audio. A face camera is optional.
- Say nothing while they play. When they ask a question, reflect it: "what would you do if I were not here?" Do not demonstrate, defend or promise a later fix.
- End early only if they are distressed or a bug has made the build unrepresentative. Mark that session partial and keep its timings out of the group's.
- Survey first, then interview (see `references/survey.md`), then thank them and stop. Write the three things that surprised you before the next tester arrives.
