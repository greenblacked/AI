---
name: devrel-impact-review
description: "Decide which developer relations activities (talks, content, workshops, sponsorships, office hours) to continue by their effect on adoption. Give each a trackable path (unique link or code, distinct signup question, dedicated sandbox or event page), count activated developers (first successful use) rather than attendees or views, and compute cost per activated developer including staff time, beside a qualitative column of deals or integrations reported by sales and support. Write the decision rule in advance, review quarterly, drop the weakest two and record what was learned. Use for \"prove developer relations is worth it\", \"quarterly devrel report\", \"is this conference sponsorship worth it\" or \"what should we stop doing\". Not for preparing a talk (conference-talk), channel attribution (attribution-sanity-check), community measures (community-health-review) or updates (status-update)."
allowed-tools: Read, Glob, Grep
---

# DevRel Impact Review

Done means every activity has a trackable path, a cost per activated developer and a qualitative note, the decision rule was written before the numbers arrived, and the weakest two activities were dropped or given a stated reason to stay.

The usual failure is counting reach. Talk attendance, video views and follower growth are easy to report and say nothing about whether anyone built something with the product. A team that cannot show effect keeps every activity, because stopping any of them feels like a loss, and spreads thin across all of them.

## Scope

Use for: a quarterly or ad hoc review of what the developer relations team does and what to stop, and for judging a single sponsorship or event.

Do not use for: preparing a talk (`conference-talk`), checking the truth of marketing channel numbers (`attribution-sanity-check`), measuring forum or chat health (`community-health-review`) or a general leadership update (`status-update`).

## Hard gates

1. The unit is an activated developer: someone who reached first successful use of the product, as the team has defined it. Attendees, views and followers are context, not results.
2. Cost includes staff time, travel and fees. An activity that looks free is paid for in hours.
3. The decision rule is written before the quarter's numbers are looked at.
4. The review ends in a decision: continue, change or stop. A review that only reports is not finished.

## Workflow

### 1. Define activation

Agree with product what first successful use means (first API call that returns a successful response, first deployment, first integration installed). If the product has no such event, the definition is the first piece of work; write it down and keep it fixed for the review. Do not change it mid-quarter to make an activity look better.

### 2. Give every activity a trackable path

Before the activity, attach at least one of: a unique link or short code, a distinct answer on the signup question ("where did you hear about us"), a dedicated sandbox, a quickstart or an event landing page. For a talk, put a unique link or code on the last slide. For a sponsorship, a dedicated landing page and a booth code. Paths overlap and leak; they give a lower bound, not the full truth. Say so in the report. `references/activity-log.md` has the table.

### 3. Count and cost

For each activity record, over the same quarter:

- Reach (attendees, views), as context only.
- Developers who followed the path, and those who activated.
- Total cost: fees, travel, production, and staff hours at a loaded hourly rate agreed with finance.
- Cost per activated developer. If the count is zero, the cost per activated developer is undefined, not zero: record it as "none activated", keep the raw count of zero visible and the total cost beside it, and rank the activity weakest in step 6. Leave it out of the median in step 5, and in the stop rule treat it as above any cost threshold.

Note the sample. Five activations from a workshop is a signal; it is not a rate.

### 4. Add the qualitative column

Ask sales and support, once a quarter and in a fixed format, which deals, integrations or support wins involved developer relations and how. Record names and what happened. This catches the long-cycle effect that activation counts miss, such as a conference conversation that turned into a partner integration six months later. Keep it as a separate column; do not convert it into dollars.

### 5. Apply the pre-written rule

Write the rule at the start of the period, for example: any activity above twice the median cost per activated developer for two quarters in a row stops, unless there is a stated strategic reason. Apply it as written. An exception needs a named reason, such as an anchor event for a new market, and a review date.

### 6. Decide and drop

Rank the activities by cost per activated developer and read the qualitative column beside the ranking. Drop the weakest two or change them, with the reason. With three or fewer activities, apply only the pre-written rule instead of forcing two out. Break ties at the cut using the qualitative column. Spending freed goes to the strongest, or is left unspent; do not spread it across everything again.

### 7. Record what was learned

Log each decision with the data and the reason, so a stopped activity is not reintroduced by a new team member without new evidence. Record what the strongest activities have in common (format, audience, follow-up) and use it next quarter.

## Hand back

The activity table with paths, activated counts, costs and cost per activated developer, the qualitative notes, the rule and how it applied, the two activities dropped or changed, the log entries, and what the paths could not see.

## Anti-patterns

**Reporting attendance.** A packed room that never signs up is worth less than a quiet workshop that produced ten integrations.

**Ignoring staff time.** The cheapest activity on paper is often the most hours.

**Moving the goalposts.** Changing the activation definition or the rule after the numbers arrive turns the review into advocacy.

**Dropping only what is easy.** Stopping the activity nobody on the team likes, instead of the weakest by the rule, wastes the exercise.
