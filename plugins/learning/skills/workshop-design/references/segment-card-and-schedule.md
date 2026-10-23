# Segment card and schedule

## Contents

- Segment card
- Worked half-day schedule
- Pre-work checklist
- Dry-run stall log

## Segment card

```text
Segment:        (number and name)
Outcome served: (1, 2 or 3)
Task:           (what the pair does, in one or two sentences)
Explanation:    (what is said before, at most ten minutes, or none)
Expected time:  (typical pair)
Slow-pair time: (1.5 times expected)
Closing check:  (command or result)
Stretch tasks:  (tier 1, tier 2, tier 3)
Likely stalls:  (from the dry run)
Helper notes:   (what to hint, what to leave)
```

## Worked half-day schedule

Four hours, three outcomes. No stretch of work longer than 75 minutes without a break.

| Time | Block | Kind | Minutes |
| --- | --- | --- | --- |
| 0:00 | Outcomes, checks, pairing | Talk | 5 |
| 0:05 | Segment 1 task: deploy the sample service | Hands-on | 36 |
| 0:41 | Closing check 1 | Hands-on | 10 |
| 0:51 | Buffer | Buffer | 12 |
| 1:03 | Break | Break | 10 |
| 1:13 | How configuration is resolved | Talk | 5 |
| 1:18 | Segment 2 task: change configuration, redeploy | Hands-on | 36 |
| 1:54 | Closing check 2 | Hands-on | 10 |
| 2:04 | Buffer | Buffer | 14 |
| 2:18 | Break | Break | 10 |
| 2:28 | How it fails | Talk | 5 |
| 2:33 | Segment 3 task: find and fix a seeded fault | Hands-on | 39 |
| 3:12 | Closing check 3 and stretch tasks | Hands-on | 16 |
| 3:28 | Short break | Break | 5 |
| 3:33 | Buffer, questions, publish materials | Buffer | 22 |
| 3:55 | Close: pass counts for each check | Talk | 5 |

Working it out, with each minute counted once. Talk is 5 + 5 + 5 + 5 = 20 minutes. Hands-on is 36 + 10 + 36 + 10 + 39 + 16 = 147 minutes, which is 147 of 240, or 61 per cent, above the 60 per cent floor. Buffer is 12 + 14 + 22 = 48 minutes, which is 20 per cent. Breaks are 10 + 10 + 5 = 25 minutes. The four add to 240. If your own plan misses either percentage, shorten a task or an explanation, not the buffer. Compute your own numbers the same way and report them.

## Pre-work checklist

- Tools and versions listed, with an install command per operating system.
- Accounts and access created, with who to ask when one fails.
- Repository cloned or archive downloaded, with the expected checksum if a download is large.
- One verification command, with the exact expected output.
- Network requirements stated, including any proxy or firewall issue at the venue.
- Fallback environment named and tested.
- A date by which participants reply.

## Dry-run stall log

| Segment | Time stuck | What they did | Cause | Fix in the materials | Re-tested |
| --- | --- | --- | --- | --- | --- |

Fix causes, not symptoms: if the error message is confusing, change the instruction that led to it or the step order, as well as adding a note.
