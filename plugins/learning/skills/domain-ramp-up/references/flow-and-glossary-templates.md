# Flow and glossary templates

## Contents

- [The one-page flow](#the-one-page-flow)
- [Glossary entry](#glossary-entry)
- [Confusable pairs](#confusable-pairs)

## The one-page flow

One page means one page. If it needs two, the domain has two flows; draw them separately and
say how they connect.

| Question | What to write |
| --- | --- |
| Who are the parties? | Five to eight boxes, named by role, not by company |
| What moves between them? | Money, goods, a message, a record; label each arrow with the artefact |
| Who can say no? | A marker on every hop where a party can reject, hold or reverse |
| How long does each hop take? | Elapsed time, from the real system, not the brochure |
| Where can it be undone? | Refund, return, recall, reversal, write-off windows |
| What data does each party keep? | One line each; this is where integrations get hard later |

Check the page by pointing at an arrow and asking what happens if the receiving party refuses.
If you cannot answer, that arrow is a question for the list.

## Glossary entry

```text
Term:        chargeback
Means:       a card issuer reverses a settled payment after the cardholder disputes it
Example:     dispute row 4471, amount 129.00, reason code "goods not received", opened 12 days after capture
Owned by:    issuer (initiates), acquirer (relays), merchant (answers)
Heard in:    Tuesday risk meeting, slide 3
```

The example record is the point. A definition can be repeated without being understood; a row
with real field values forces the question of which field means what.

Selection rule for the 30: first the terms naming a hop or an artefact on the flow page, then
terms heard in meetings, then nothing else. Drop a term you cannot attach to an example.

## Confusable pairs

Collect three, with the practical test that separates them.

| Pair | The difference in one line | Test |
| --- | --- | --- |
| Term A versus term B | What each one is | A question whose answer differs |

Ask people which words they see swapped in tickets and meetings. A pair that nobody confuses
is not worth a slot.
