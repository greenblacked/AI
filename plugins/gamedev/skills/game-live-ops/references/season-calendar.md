# The season and content calendar

Read this at step 2, before any content or event is committed to a date. Everything here is about building a calendar that holds up under the lead times the team does not control, rather than one that assumes everything ships on the day it was hoped for.

## Contents

- [What the calendar has to fix](#what-the-calendar-has-to-fix)
- [Cadence patterns by game type](#cadence-patterns-by-game-type)
- [Sizing the lead-time buffer](#sizing-the-lead-time-buffer)
- [A worked calendar](#a-worked-calendar)
- [What breaks a calendar](#what-breaks-a-calendar)

## What the calendar has to fix

Before writing dates, fix three things in one sitting:

- **Season length.** How long one season runs, end to end, and what marks its close — a new season starting, a leaderboard reset, a narrative beat.
- **Content-drop cadence.** How often something new lands inside the season — weekly, biweekly, monthly — and what class of thing lands on each cadence (a cosmetic drop is cheap and frequent; a new mode or map is expensive and rare).
- **What "done" commits to.** For each planned drop, the minimum it has to include to ship on its date, written before production starts on it, so a drop running behind has an honest scope to cut rather than a vague deadline to blow through.

## Cadence patterns by game type

| Game type | Typical cadence shape | The lead-time risk to plan around |
| --- | --- | --- |
| Competitive multiplayer / live service | A season of weeks to a few months, with smaller content drops inside it and a balance-tuning window on its own schedule | Certification lead time on every console patch; check each platform holder's current turnaround and plan the calendar around it |
| Mobile F2P | Frequent, often weekly, event-driven drops layered on a longer season arc | Store review turnaround, which is real and easy to forget when a team is used to instant web deploys; check each store's current review times |
| Narrative / episodic | Chapter or episode releases on a much longer cadence, often months apart | Content production lead time dwarfs certification here; the calendar risk is mostly internal |
| Co-op / PvE live service | Content drops paired with difficulty or seasonal challenge resets | Balance tuning for new content needs its own evidence window before the next drop lands on top of it |

Read these as starting shapes, not fixed rules — the actual cadence a specific game can sustain is a capacity question the team has direct evidence for, from how the last few drops actually went.

## Sizing the lead-time buffer

For any drop that touches a build requiring platform review, work backward the same way `game-certification` does for a first submission: the drop's target date, minus the storefront's release lead time, minus review turnaround times one plus however many resubmissions are budgeted, minus a final QA pass. That gives the date content actually has to be locked for that drop — not the date it is hoped to be locked.

Write the content-lock date for every drop that needs one onto the calendar itself, not just the ship date. A calendar that only shows ship dates hides the date that actually constrains production, and content-lock dates are what production plans against.

## A worked calendar

A competitive multiplayer game running eight-week seasons, biweekly content drops, and console certification with a two-week review turnaround and one budgeted resubmission:

```text
Week 0   Season opens. New content from the previous cycle goes live.
Week 2   Drop 1 (cosmetic pack, no cert-blocking content) — content lock week 1.
Week 4   Drop 2 (new mode, requires cert) — content lock week 0, because
         2-week review × (1 + 1 resubmission) = 4 weeks of buffer needed.
Week 6   Drop 3 (balance patch, evidence gathered from weeks 4-6) — content
         lock week 5, one week of QA behind the balance decision.
Week 8   Season closes, leaderboard resets, next season's Week 0 content locks
         two weeks earlier still, because it has to be ready to go live same day.
```

The mode drop in week 4 is the one that surprises teams: a four-week buffer inside an eight-week season leaves only the season's first half to actually build it, which is the argument for planning a season's calendar before the season before it closes rather than during it.

## What breaks a calendar

A calendar most often breaks in one of three ways, all avoidable at the planning stage rather than the execution stage:

- **No buffer for certification**, discovered when a drop that needed platform review is ready on the day it needs to ship rather than the day it needed to be locked.
- **A drop's "done" scope invented under deadline pressure** rather than fixed when the calendar was written, so a slipping drop either ships broken or ships late with no honest record of what was cut and why.
- **Events and drops scheduled with no relation to the tuning window a balance change needs** — a new mode dropping the same week its own balance evidence is still being gathered means the first reading of the new content and the first reading of the tuning pass are tangled together, and neither can be attributed cleanly.
