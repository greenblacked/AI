# Interview kit

## Contents

- Case selection sheet
- Interview script
- Probes for stuck moments
- Rule template and examples
- Verification scoring sheet

## Case selection sheet

| Case | Date | Type (common, rare, surprise) | Cost of the failure | Artefacts on hand | Others who were there |
| --- | --- | --- | --- | --- | --- |

Choose cases that differ in type. A set of three similar outages produces three versions of the same rule. Prefer cases that cost the most, and include one where the first diagnosis was wrong, since that is where the expert's corrective instincts show.

## Interview script

Before: send the case and the artefacts a day ahead so the expert can refresh. Agree the recording and who may hear it.

1. Open (5 minutes). "Walk me through the last time this broke. Start from when you first heard about it." Do not interrupt; note the places where the story speeds up or skips.
2. Slow replay (30 minutes). Go back through the story one step at a time with the artefacts open. At each step ask the four questions from the main procedure.
3. Counterfactuals (7 minutes). "If the graph had looked different here, what would you have done?" "What would a new person have done?" "Who would you have called, and what would you have asked them?"
4. Close (3 minutes). "What did we not cover that matters in a case like this?" Book the follow-up to review the written rules.

## Probes for stuck moments

- "Which screen were you on when you decided that?"
- "What number were you comparing it to?"
- "How do you know that is normal for this system?"
- "When did you last see it look like that, and what was it?"
- "If I had to do this step without you, what is the mistake I would make?"
- "Is there anything you stopped doing because it never helped?"

Avoid "why did you do that", which sounds like an accusation. Use "what made that the first thing to check".

## Rule template and examples

```text
Rule:       If <observable>, look at <place or action> first, because <reason>.
Unless:     <exception that changes the action>
Source:     <case and date>
Artefacts:  <dashboard, query, ticket, log>
Confidence: (seen once | seen several times | expert's general experience)
Checked by: <second person and date>
```

Examples, illustrative:

- If the nightly batch finishes later than usual and the downstream report is short, look at the upstream extract's row count first, because a partial extract completes quickly and produces no error. Unless the extract job itself shows a failure, in which case follow the retry procedure.
- If latency rises on only one tenant, look at that tenant's largest recent import first, because one large import can saturate the shared queue without raising overall load.

A rule such as "check the logs" fails the template: no observable, no place and no reason.

## Verification scoring sheet

| Held-out case | Second person's first check | Expert's first check | Match | Cause of difference (missing rule, vague trigger, missing reason) | Sheet fix |
| --- | --- | --- | --- | --- | --- |

A match for the wrong reason counts as a gap: ask the second person why, and compare with the written reason.
