---
name: usability-test-plan
description: "Plan and run a small usability test with real people: the question and the decision it feeds, who to recruit and how many, neutral task wording, a think-aloud script, the measures (task success, time, System Usability Scale), and turning observations into severity-rated fixes before the next round. Use for planning and running a usability test with users. Casual asks include \"how do I test this with users\", \"how many users do I need\", \"write me tasks for a usability test\", \"we want to watch five people try our prototype\", \"how do I score SUS\" or \"what do I do with the notes from these sessions\". Not for an expert review of a screen without participants (ui-ux-review), a WCAG audit (accessibility-audit), tokens and themes (design-system), designing a hiring interview loop (hiring-loop) or preparing for a job interview (job-search)."
allowed-tools: "Read, Write, Edit, Grep, Glob"
---

# Usability Test Plan

A usability test is finished when a decision has changed because of what real people did, every problem found has a severity and a fix, and the fixes have been tried on the next small round.

Tests go wrong before anyone sits down. The question is vague, so the findings do not decide anything. The participants are colleagues who already know the product. The tasks name the buttons ("click Settings and turn on notifications"), so the test measures whether people can follow instructions. The moderator explains, hints and reassures, and the participant stops thinking aloud and starts guessing what the moderator wants. And the notes become a long list nobody ranks, so a round of five sessions leads to no change. This skill fixes the order: decide, recruit a small group, write neutral tasks, stay quiet, rate and fix, then test again.

## Scope

Use for: planning a qualitative test of a prototype or product with five or so participants; planning a quantitative study; writing tasks and a moderator script; choosing and scoring measures; turning session notes into a ranked list of fixes.

Do not use for: an expert review of a screen with no participants, which is `ui-ux-review`; a WCAG audit, which is `accessibility-audit`; token and theme work, which is `design-system`; designing a hiring loop, which is `hiring-loop`; preparing for a job interview, which is `job-search`.

## Workflow

### 1. Write the question and the decision

State what you want to learn and what will change depending on the answer, in two sentences. "Can new users find and finish a booking, and if not, where does it break, so we can decide what to rebuild before launch" is a test. "See what people think" is not, and a test with no decision attached can be skipped. Decide whether it is qualitative (find problems, small numbers) or quantitative (measure, large numbers), because the sample sizes differ.

### 2. Size and recruit the sample

For a qualitative test, five participants per round is the working default. Nielsen Norman Group's analysis (Nielsen and Landauer) finds about 85 percent of usability problems with five users, with best results from no more than five and as many small rounds as you can afford. The formula holds only for comparable users. When distinct user groups behave differently, test three or four per group for two groups, and three per group for three or more. For a quantitative study, NN/g recommends about 40 participants.

Recruit people who resemble the real users, through a short screener on the behaviours that matter (what they do, how often, with which tools), not on demographics alone. Colleagues who built the product, and friends who want to be kind, are not representative. Recruit one or two spares, since someone will not turn up. The rest is in `references/test-kit.md`.

### 3. Write tasks the way a user would say the goal

A task is a goal with a scenario, in the user's words, that does not name interface labels, menus or steps. Write "You want your Friday appointment moved to the following week" and not "Use the Reschedule button". Order them with the primary task first, because fatigue and learning effects hit the last ones. Write the success criterion for each task before the first session, including what counts as partial success. Fewer tasks done well beat many done in a rush. The rules and worked examples are in `references/test-kit.md`.

### 4. Choose the measures

| Measure | What it tells you | Notes |
| --- | --- | --- |
| Task success | Whether they got it done | Define success, partial success and failure in advance. |
| Time on task | How long | Meaningful in numbers; with five people treat it as a flag, not a result. |
| Observed problems | Where and why it broke | The main output of a qualitative round. |
| System Usability Scale (SUS) | An overall perceived-usability score from 0 to 100 | Give it right after the tasks and before the discussion. |

SUS has ten items on a five-point scale. Odd-numbered items contribute their score minus 1, even-numbered items contribute 5 minus their score, and the sum multiplied by 2.5 gives a score from 0 to 100. The average is 68, and a score below 51 is roughly the bottom 15 percent (source: https://measuringu.com/sus/). The form and a worked score are in `references/test-kit.md`. With five participants, read SUS as a sanity check and not as a benchmark you can compare.

### 5. Think aloud, and keep quiet

Use the think-aloud method: representative users, representative tasks, and let the users do the talking (Nielsen, "Thinking Aloud: The #1 Usability Tool", https://www.nngroup.com/articles/thinking-aloud-the-1-usability-tool/). The moderator's job is to shut up and let the user talk. Do not explain the interface, answer "is this right", hint, or fill a silence. When the participant goes quiet, say "keep talking" or "what are you thinking now". When they ask a question, turn it back: "what would you expect?". Practise think-aloud on a trivial task first. The script is in `references/test-kit.md`.

### 6. Pilot, then run

Run one pilot session, with a colleague or the first participant treated as a trial, to find a task that is ambiguous, a prototype that breaks, or a recording that fails. Fix those before the real round. In each session use one moderator and one person taking notes, record with consent, and write down what the participant did and said, kept apart from your interpretation. Do not change the prototype between sessions in a round unless it is broken so that no task can be tried.

### 7. Rate, fix and test again

After the round, list each distinct problem once, with the participants who met it, a short quote or timestamp, and the cause. Rate each from 0 to 4: 0 not a usability problem, 1 cosmetic only, 2 minor (low priority), 3 major (high priority), 4 catastrophe, imperative to fix before release. Severity combines frequency, impact and persistence (https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/). Write the smallest fix next to each one. Fix the 3s and 4s, then run the next small round with new participants to see whether the fixes worked and what they exposed. One big test hides the problems it never gets to; several small ones find more.

### 8. Report the decision, not the diary

Open with the question from step 1 and the answer. Then the ranked problems with their fixes, then SUS and success if you measured them, then who took part and what was not tested. Keep raw notes as an appendix.

## Anti-patterns

**Testing with the team.** They know where things are. Their success tells you nothing.

**Naming the interface in the task.** If the task contains the label, you are testing reading.

**Helping.** Each hint is a failure you did not record and a result you cannot trust.

**One large test at the end.** A large qualitative test keeps rediscovering the same few problems. Five, fix, five more.

**A pile of notes with no severity.** Nothing is fixed because nothing is ranked.

**Quoting a SUS score from five people as a number to beat.** It is a signal for this round, not a benchmark.

## References

- `references/test-kit.md`: read at steps 2 to 6 for the screener, the task-writing rules with examples, the moderator script and think-aloud practice, the SUS form and scoring example, and a findings log.
