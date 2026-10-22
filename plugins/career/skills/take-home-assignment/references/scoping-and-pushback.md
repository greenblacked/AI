# Scoping and pushback

## Contents

- Questions to send
- Slicing scope
- Tracking time
- Pushing back on a larger task
- What reviewers tend to weigh

## Questions to send

Keep it to seven or fewer, in one message, each answerable in a line. Example opening: "Before I start, a few quick questions so I scope this to what you are looking for." End with the assumption you will make if no answer arrives, and the date you will start.

- What is the time budget, and is it a limit or a guideline?
- What are reviewers weighing: correctness, design, tests, communication?
- Which language, framework and libraries are allowed or expected?
- Is there a deadline for submission, and how should it be delivered?
- Is anything out of scope, such as authentication, a UI or persistence?
- Are assistance or code-generation tools permitted, and should their use be disclosed?
- Will there be a follow-up discussion of the code?

If the answer to the tools question is unclear, follow the stricter reading and say which one you followed in the README.

## Slicing scope

1. List every feature in the brief.
2. Mark the one path that, if it worked, proves the idea.
3. Mark the riskiest or most interesting piece; it carries one of the three decisions.
4. Everything else goes to the cut list unless it takes minutes.

Build the thin path end to end first, then deepen the risky piece. A deep component with no working path fails; a thin working path with one deep piece succeeds.

## Tracking time

Note start and stop times in a scratch file. At half the budget check whether half the core path works. If not, cut now, not at the end.

## Pushing back on a larger task

Example wording:

"Thank you for the update. I can give this the four hours we agreed. I would suggest I deliver the core path and document the rest as follow-ups. Does that work for you?"

If they require more unpaid work, ask whether the extra time is compensated, or decline politely. Keep the tone friendly; it is a negotiation of scope, not of worth.

## What reviewers tend to weigh

Commonly stated criteria, though each company differs and the questions in step 1 should confirm them: whether it runs, whether the code is readable, whether the tests are meaningful, whether trade-offs are acknowledged, and whether the scope was sensible. Many reviewers read the README before the code, so it frames everything that follows.
