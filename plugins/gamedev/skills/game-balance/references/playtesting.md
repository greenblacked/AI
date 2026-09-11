# The playtest protocol

Read this before scheduling a session. Half of what decides whether a playtest produces signal is settled before anyone sits down — who was recruited, what they were told, and where the observer sits — and none of it can be repaired afterwards.

## Contents

- [What a playtest is for](#what-a-playtest-is-for)
- [Recruiting](#recruiting)
- [Before they arrive](#before-they-arrive)
- [The room](#the-room)
- [The silence rule](#the-silence-rule)
- [What to record](#what-to-record)
- [The questions afterwards](#the-questions-afterwards)
- [First-session test versus retention test](#first-session-test-versus-retention-test)
- [Turning a session into changes](#turning-a-session-into-changes)
- [What a playtest cannot tell you](#what-a-playtest-cannot-tell-you)

## What a playtest is for

Comprehension, friction and intent. Whether the player understood what to do, where they stopped enjoying it, and what they were trying to achieve when they did the thing the design did not expect. These are questions telemetry cannot answer, because telemetry records the action and not the reason.

It is not for balance numbers. Six people over two hours cannot produce a sample that separates a 55 per cent win rate from a coin, and treating their impressions as balance data is how a niche option gets nerfed because one tester found it annoying.

## Recruiting

Match the tester to the question. A test of the first fifteen minutes needs someone who has never seen the game, and every such person is single use — you cannot test a first session on somebody twice, which makes fresh testers the scarcest resource the project has. Spend them deliberately: no demos to colleagues, no showing it to a friend who might later be a tester.

Recruit against the intended audience, including genre familiarity. Someone who has played forty roguelikes will carry conventions your first-time player does not have, and a test run entirely on genre veterans reports that the game is clear when it is only familiar.

Five testers surface most comprehension problems, and the returns fall off quickly after that, so run five, fix, and run five more rather than ten at once. The second group tests the fixes; the first group cannot.

Avoid friends, family and anyone who has a stake in your feeling good. They will be encouraging, and encouragement is the one signal a playtest cannot use.

## Before they arrive

- Decide the one question this session answers, and write it down. "Do players understand that the shield recharges?" is a session. "Is the game good?" is not.
- Build the thing they will play and play it yourself start to finish that morning. A crash in the first two minutes costs the whole session.
- Have a reset: a save state, a fresh profile, or a script that returns the build to its starting condition between testers.
- Prepare exactly one sentence of framing, usually the sentence that would appear on the store page. Anything more teaches them what you want to find out whether they can work out.
- Tell them what is being tested. The game is being tested, not them, and saying so out loud is what makes them willing to be confused in front of you.
- Ask permission before recording anything, and say what the recording is for and who sees it.

## The room

Sit beside and slightly behind, out of their eyeline and never between them and the screen. If the setup allows, sit where you can see their hands and the screen at once; hands show hesitation several seconds before anything happens on screen.

Record the screen and the audio, including their voice. A face camera is optional and usually not worth the awkwardness it adds. Take timestamped notes by hand as well — the notes are what you read afterwards, and the recording is what you check them against.

Do not demonstrate the controls. If the game needs a person to explain it, that is the finding, and demonstrating it destroys the only chance to observe it.

## The silence rule

Say nothing while they play. This is harder than it sounds and it is the whole method.

When they get stuck, stay silent and time it. When they ask a direct question — "am I supposed to go left here?" — do not answer it. Reflect it back: "what would you do if I were not here?" The shipped game will not answer either, and the thirty seconds they spend working it out is the most valuable data in the session.

Do not defend a design decision, explain what was intended, or mention what a later build will fix. Each of those converts a tester into an audience and ends the useful part of the session.

There is one exception: end it early if they are genuinely distressed, or if a bug has made the build unrepresentative.

## What to record

Timings, because impressions are unreliable and timings are not:

- Time to first input, and time to first deliberate input.
- Time to first failure, and time to the first failure they understood.
- Time to the moment they visibly understand the core mechanic — the change in posture or the "oh" is usually audible.
- Time spent stuck, per stuck moment.
- Total session length, and whether they stopped or were stopped.

Events, verbatim where possible:

- Every question asked aloud, in their words.
- Every point where they did the wrong thing confidently — a confident mistake is a design problem; a hesitant one is a clarity problem.
- Every feature they never used, and whether they knew it existed.
- Every time they laughed, swore, leaned in, or checked their phone.
- The moment they would have stopped playing if they were at home.

Write what they did, not what it means. "Walked past the door three times" is a record; "did not notice the door" is an inference, and separating the two is what lets a second person read your notes.

## The questions afterwards

Ask after they have finished, not during, and anchor every question to a specific moment you watched.

Worth asking:

- "At [moment], what were you trying to do?"
- "What did you expect to happen when you [action]?"
- "When did you first feel like you understood it?"
- "If you were at home, where would you have stopped?"
- "How would you describe this game to a friend?" — the answer tells you what the game communicated, which is rarely what it intended.
- "What was the most annoying part?" — annoyance is reported far more accurately than enjoyment.

Not worth asking:

- "Did you like it?" Politeness makes the answer yes.
- "What should I add?" They will design, badly, and the answer is a feature list rather than a problem.
- "Was that too hard?" It leads, and difficulty is better read from the attempt count you just recorded.
- "Would you buy this?" Stated purchase intent has almost no relationship to purchase.

When a tester proposes a fix, take the complaint and discard the fix. "Make the boss weaker" is a report that the fight was frustrating; the cause could be telegraphing, the camera, or an unexplained damage source, and the number is the least likely of the four to be the problem.

## First-session test versus retention test

| | First-session test | Retention test |
| --- | --- | --- |
| Question | Do they understand it and does it hook | Does the loop survive repetition |
| Tester | Never seen the game, single use | Has played, and agreed to keep playing |
| Length | One sitting, 20 to 60 minutes | Days or weeks, several sessions |
| Observed | In the room, watched | Mostly remote, read from telemetry and a short weekly conversation |
| Metric | Time to the core loop, comprehension, quit point | Whether they came back unprompted, and on which day they stopped |
| Fails when | The game needs explaining | Session two is the same as session one |

The two fail in different places, and a game can pass the first convincingly while failing the second: novelty carries a first session, and nothing carries a fifth. Do not send a reminder during a retention test. An unprompted return is the measurement, and a nudge destroys it.

## Turning a session into changes

After each tester, spend ten minutes writing the three things that most surprised you, before the next session overwrites the memory. After the group of five, count how many testers hit each problem. A problem three of five hit is a design problem; a problem one of five hit is a person, unless it is catastrophic.

Rank by how many testers hit it and how far it was from the intended path, fix the top few, and run the next five on the same script. Changing the script between groups means comparing two different tests.

## What a playtest cannot tell you

- Whether the numbers are balanced. That needs the volume in `references/telemetry.md`.
- Whether players will keep playing for a month. A retention test measures days; the only measurement of a month is a month.
- Whether the game is fun for an audience you did not recruit.
- Whether a problem the tester hit is common. Five people establish that something is possible, not how often it happens.
