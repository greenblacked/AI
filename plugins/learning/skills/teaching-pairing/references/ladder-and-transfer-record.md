# Ladder and transfer record

## Contents

- Session plan
- Ladder by situation
- Transfer record

## Session plan

```text
Learner / teacher:       
Topic:                   
Target ability:          (what the learner can do alone afterwards)
Session task:            (small, finishable in one session, one step beyond current)
Transfer task:           (similar, small, to be done alone within 48 hours)
Date and length:         (90 minutes at most; break planned, one of them read-only)
```

## Ladder by situation

Rung 1 is a question, rung 2 a hint, rung 3 showing a small piece and handing the keyboard back. Count ten before each climb.

| Situation | Rung 1: question | Rung 2: hint | Rung 3: show |
| --- | --- | --- | --- |
| Error message not understood | What is the first line of the error saying was expected? | The cause is usually near the last line of your own code in the trace | Read one trace aloud, then ask them to read the next |
| Does not know where to start | What is the smallest thing that would tell us whether the request arrives? | Start from where the request enters the code | Open the entry point, then have them follow the call |
| Tests failing, no idea why | What did you expect this test to see, and what did it see? | Print or inspect the value just before the assertion | Add one log line together and run it |
| Guessing at changes | What do you think this change will do? | Make one change at a time and run after each | Revert and redo one step slowly |
| Unfamiliar tool or command | Where could we find out what this does? | Try the help output, or the project docs | Show the lookup, not the answer |
| Right answer by luck | How would we know this is right and not just passing? | Think of an input that would break it | Write one such input together |

Keep a count of rung-3 moments; each is a gap to put in the record.

## Transfer record

```text
Transfer task:                 
Done on / within 48 hours:     yes | no
Done alone:                    yes | partly | no
Unaided:                       (what they did without help)
Needed help with:              (what, after what they tried first, and what kind of help)
Rung-3 moments from the session:   
Next practice item:            
Consecutive solo transfers passed on this topic: 0 | 1 | 2
Decision:                      keep pairing on this gap | stop, topic closed after two solo passes
```

A transfer passes when the learner finishes a similar task alone at an acceptable standard and asks nobody for help, including after the 30-minute blocked limit. Asking for help is a fail for that transfer, though the record still notes what was tried first. Two consecutive passes close the topic.
