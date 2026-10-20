# The post-session survey

Read this at step 5, before writing the survey or reading its answers.

## Contents

- [What the survey is for](#what-the-survey-is-for)
- [Rules](#rules)
- [Item types](#item-types)
- [A starting set](#a-starting-set)
- [Reading the answers](#reading-the-answers)

## What the survey is for

The record sheet says what players did. The survey says what they believe happened, which is a different thing and sometimes the opposite: players who died eleven times may rate the difficulty as fair, and players who breezed through may report that they were confused. Both facts are findings. Keep the survey short, because a tester who is tired of answering will pick the middle of every scale.

It exists to be compared across testers and across rounds. That is why the items are fixed.

## Rules

- **Same items, same order, same wording, same anchors every round.** Change one word and the comparison with the previous round no longer holds. If an item turns out to be poor, replace it and say in the notes that rounds before and after are not comparable on that item.
- **Give it before any conversation.** The interview's questions teach the tester what you care about, and the survey then measures what you taught them.
- **One idea per item.** "The tutorial was clear and short" is two items and cannot be answered by someone who found it clear and long.
- **Label every point of the scale in words.** "Strongly disagree" to "strongly agree" with the middle labelled as neither. A scale with only the ends labelled is read differently by each person.
- **Use the same scale for most items.** A single agreement scale is quick to answer and quick to compare. Mix in at most one or two other kinds.
- **Keep the target in the item.** Ask about the thing the question from step 1 names, not about the game in general. A general item gets a general answer that decides nothing.
- **Use positive and negative wording in turn** for items that measure the same thing, so a tester who agrees with everything shows up as inconsistent rather than as satisfied.
- **No leading wording.** "How much did you enjoy the exciting boss fight" has made its mind up.
- **Optional free text is limited to two items:** the most confusing or annoying moment, and what the game is about in their own words. Free text beyond that is an interview done badly on paper.
- **Do not collect more than you can use.** Every item should map to the question or to a decision. An item with no decision behind it is cut.

If a claim has to hold up outside the team, such as a report to a publisher or a comparison with other games, use a published questionnaire with its wording unchanged instead of writing items. Check its licence and its stated scoring before using it. For internal rounds, a short set written to your question is the better tool, because it is about your game.

## Item types

| Type | Looks like | Use for |
| --- | --- | --- |
| Agreement | "I understood why I failed each time I died." Strongly disagree to strongly agree | Comprehension, fairness, clarity |
| Frequency | "How often did you feel unsure what to do next?" Never, rarely, sometimes, often, always | Friction, pacing |
| Unaided recall | "What happens to your shield when you stop taking damage?" with a short free answer, or balanced options that include "I don't know" | Whether a specific piece of knowledge was acquired |
| Choice | "Where would you have stopped playing at home?" with named points from the build | Quit point, as a check against what you observed |
| Free text | "What was the most confusing moment?" | A pointer for the interview, not data |

The recall type has a use that scales cannot match: it tests whether a fact reached the player. Ask it without stating the answer, because "Did you know the shield recharges?" teaches the mechanic in the act of asking, and a tester who never learned it can simply agree. Reveal the answer in the interview, after the survey. Pair the answer with what you recorded. A tester who describes the recharge correctly and never used it is a different finding from one who could not say.

## A starting set

Edit this to the question; do not use it as it stands. Every item has an anchor to the design goal in the session block.

```text
Agreement (strongly disagree ... strongly agree)
1. I knew what I was supposed to do in the first level.
2. When I failed, I understood why.
3. There were moments I did not know what the game wanted from me.   (reverse)
4. The challenge felt fair.
5. I would keep playing if this were my own copy.

Knowledge (unaided recall; reveal the answer only in the interview)
6. What happens when <the situation that triggers the mechanic under test>?

Free text (optional)
7. What was the most confusing or annoying moment?
8. Describe this game to a friend in a sentence.
```

Item 5 asks about stated intent, which is a weak predictor of what people do. It is a prompt to compare with where they quit, not a figure to report.

## Reading the answers

With a handful of testers the survey cannot support an average or a percentage. Read it as a list.

- Put each item's answers side by side, one mark per tester. A cluster at one end is a finding. A spread is a difference between testers, and the record sheet usually explains it.
- Compare each answer with the behaviour you recorded. A tester who agrees that they understood why they died, and died to the same enemy five times, is telling you what they believe, which is the problem.
- Item 3 is reverse-worded so a tester cannot agree all the way down the list on autopilot, but it is not the opposite of item 1: item 1 covers the first level and item 3 the whole session. Agreeing with both is a consistent answer (they understood the start and lost the thread later) and a finding to place on the record sheet, not a sign of inattention, so do not discount their other answers on it.
- Between rounds, compare the same item's marks. A move of one or two marks is a hint; the claim rests on what the record sheet shows.
- Send questions about how common something is to telemetry, which has the volume the survey lacks.
