# Interview and gate kit

## Contents

- [Interview script](#interview-script)
- [Transaction trace table](#transaction-trace-table)
- [Constraint register](#constraint-register)
- [Day-10 scoring sheet](#day-10-scoring-sheet)

## Interview script

Send the flow page and the traced transaction the day before. Open with: "Please correct this
before I ask anything." Then the fixed questions:

1. What fails most often, and how do you find out it failed?
2. Which rule does everyone forget until it bites?
3. Who gets called when the main flow breaks, and what do they do first?
4. What would a newcomer assume that is wrong?
5. Which number do you watch every day, and what is a bad value?

Follow-ups that earn their time: "Can you show me the last time?", "Who else would say
something different?", "What is written down and what is only known?". Close with "Who should
I talk to next?" and record the name. Write answers in a table with one row per interviewee so
disagreements are visible.

| Interviewee seat | Fails most | Forgotten rule | First call | Newcomer error | Daily number |
| --- | --- | --- | --- | --- | --- |

## Transaction trace table

| Step | System or party | Timestamp | Who holds the money or goods | State name used here | Could it have failed here? |
| --- | --- | --- | --- | --- | --- |

Fill one table for the success path and one for the exception path. Rows where the state name
differs between systems are the integration problems of the future; flag them.

## Constraint register

| Constraint | Source document and clause | Forbids or forces | Tempting design it rules out | Confirmed in writing? |
| --- | --- | --- | --- | --- |

A row with "no" in the last column goes to whoever owns compliance before anyone designs
against it. This register is orientation, not legal advice.

## Day-10 scoring sheet

- Wrong-beliefs list: count, and for each the step that would have caught it.
- Five-minute explanation: given to an outsider first, to check it is understandable, then to
  an expert. Record each correction the expert makes, verbatim.
- Pass: three corrections or fewer. Fail: repeat the originating step, then redo only the
  explanation, with a different expert if one is available.
- Ranked question list: question, cost of a wrong answer (high, medium, low), who can answer.
