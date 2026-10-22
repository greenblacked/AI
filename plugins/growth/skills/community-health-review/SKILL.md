---
name: community-health-review
description: "Review whether a forum, Discord, Slack or support community is healthy and growing sustainably with a short fixed monthly set: time to first response, share of questions answered within 24 hours and ever, new members who post within 14 days, contributor concentration (flag when the top five write most answers) and returning members at 30 and 90 days. Read a sample of unanswered threads each month to find why, fix the largest gap with one action (staff rota, pinned guides, welcome flow, recognising repeat helpers) and report the outcome next month. Member count is not a target. Use for \"is our community working\", \"nobody answers questions in the forum\", \"our Discord is quiet\" or \"report on community for leadership\". Not for rules and enforcement (community-moderation-policy), open source newcomers (contributor-funnel), staff attrition (retention-review) or updates (status-update)."
allowed-tools: Read, Glob, Grep
---

# Community Health Review

Done means a small fixed set of measures is reported monthly with the method written down, the largest gap has one action with an owner, and the next review says whether that action moved the number.

The usual failure is reporting what is easy to count. Member totals and messages per day rise while questions sit unanswered and five people do all the helping. Leadership sees growth; members see an empty room, and the helpers burn out without anyone noticing.

## Scope

Use for: a public or customer community on a forum, chat server or similar, and a request to judge it or report on it.

Do not use for: writing or enforcing rules (`community-moderation-policy`), the path from newcomer to code contributor (`contributor-funnel`), staff attrition (`retention-review`) or a general leadership update (`status-update`).

## Hard gates

1. The measures are fixed before reading the numbers, and defined in writing so next month's figure means the same thing.
2. Every number states its period and sample size. A community with 12 questions a month has stories, not rates.
3. Read real threads each month. Metrics find where to look; the threads say why.
4. One action per month on the largest gap, with an owner.

## Workflow

### 1. Define the measures

Use `references/measures.md` to fix the definitions. The set is:

1. Time to first response on new questions (median and 90th percentile), counted from the question to the first reply by anyone other than the author. Questions never answered count as still waiting at the end of the month and longer than every answered one, so unanswered questions raise the figures instead of dropping out.
2. Share of questions answered within 24 hours, and share ever answered. Count a question as answered when someone other than the author posts an accepted or clearly helpful reply; use that one definition for both shares.
3. New members who post within 14 days of joining, out of those who joined.
4. Contributors by activity share: how many people wrote the answers, and whether the top five account for most of them.
5. Returning members: those active in a given month who are active again 30 and 90 days later.

Decide what counts as a question (a post tagged or phrased as one) and exclude spam, bot posts and staff announcements. Write the rule down.

### 2. Pull the data

Export from the platform's analytics or API, or from a manual sample if neither exists. Use a full month. Record the number of questions, posts, new members and active members, so ratios can be checked against their denominators.

### 3. Compute and compare

Compute the five measures for the month and compare with the previous month and with the same month a year ago if it exists. Mark each figure with its sample. Note in particular whether the top five answerers wrote most of the answers: if so, the community depends on a few people, whatever its size.

### 4. Read the unanswered threads

Take a sample of unanswered questions (twenty, or all if fewer) and read them. Classify each by cause: unclear question, already answered in the docs, outside the community's scope, niche topic nobody knows, posted in the wrong place, nobody saw it. Count the causes. This turns "response time is slow" into a fixable thing. Do the same for a small sample of new members who never posted, if the platform shows their path.

### 5. Choose one action

Pick the action that addresses the largest cause, for example:

- Staff answer rota for first response, when most unanswered questions are answerable but unseen.
- Pinned guides and a better docs link, when many are already documented.
- A welcome flow that asks new members to introduce themselves or ask their first question, when few new members post.
- Recognition and a lightweight route for repeat helpers (a role, early access, a direct line to the team), when the top five carry the load.

State the expected effect on a named measure and the date of review. One action keeps cause and effect readable.

### 6. Report

Report the five measures, the cause counts, the action and last month's action outcome. Keep member count and messages per day, if leadership wants them, as context lines after the health measures and not as targets: they can rise while the community gets worse.

### 7. Review the outcome next month

Check whether the targeted measure moved. If it did not, say so and look again at the threads before adding actions.

## Hand back

The month's measures with samples, the unanswered-thread causes, the single action with owner and review date, last month's outcome, and the definitions used. State what the platform could not export and was estimated.

## Anti-patterns

**Targeting message volume.** People then post filler and the helpers' work is invisible.

**Average response time.** One question answered after a month drags it; use the median and a 24-hour share.

**Five actions at once.** The next month's number cannot say which worked.

**Reviewing without reading.** A dashboard cannot tell an unanswerable question from an ignored one.
