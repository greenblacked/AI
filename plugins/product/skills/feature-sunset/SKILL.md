---
name: feature-sunset
description: "Retire a feature, plan, integration or whole product without stranding the customers who depend on it: pull usage by account before deciding, classify every account as unaffected, replaceable or blocked, set the end date from the slowest-migrating segment rather than engineering convenience, then run the sequence (announce, close to new sign-ups, in-product warning, brown-out windows, read-only, remove) with a gate at each stage, and call it done only when blocked accounts reach zero. Use for \"deprecate this feature\", \"end-of-life the old plan\", \"sunset the legacy app\", \"nobody uses this, can we just delete it\" or \"how long should the deprecation notice be\". Not for moving customers to a new price (price-change-rollout), retiring an API version (api-design), removing a flag from code (feature-flag-lifecycle) or upgrading a dependency you consume (dependency-upgrade)."
allowed-tools: Read, Glob, Grep
---

# Feature Sunset

A sunset is finished when the feature, its data, its code, its documentation, its price-list entry and its support macros are gone, and every account that depended on it has either migrated, accepted a named alternative, or left with a recorded decision — blocked accounts at zero, not "most customers moved".

The usual failure is choosing the date first. Engineering picks the quarter it wants the code gone, the announcement goes out, and only then does someone find the eight enterprise accounts that run their month-end close on it and cannot change before their next audit. The date slips under pressure, which teaches every customer that deprecation dates are negotiable. The second failure is "nobody uses it" based on a usage window too short to see the job that runs once a quarter.

## Scope

Use for: removing a product feature; ending a plan or tier that is no longer sold; shutting down an integration, a legacy app or a whole product; deciding whether something with low usage can simply be deleted; setting a deprecation timeline and its communications.

Do not use for: moving customers to a new price or plan as a pricing change, which is `price-change-rollout`; versioning and retiring an API version as interface design, which is `api-design`; deleting a feature flag from code after a rollout, which is `feature-flag-lifecycle`; upgrading a library or runtime that you consume, which is `dependency-upgrade`; a one-off switchover from one system to another, which is `cutover`; a customer demanding the feature stay on the roadmap, which is `roadmap-disruption-triage` if it reopens the decision.

## Workflow

### 1. Write down why, and what replaces it

State the cost of keeping it (engineering time, on-call load, security surface, licence or infrastructure cost, what it blocks) and what customers should use instead. If there is no replacement, say so plainly; "use nothing" is a legitimate answer but it changes how many accounts are blocked.

### 2. Pull usage by account before deciding

Query usage over a window long enough to catch periodic jobs: at least a full quarter, and thirteen months if the feature could plausibly serve an annual task (audit exports, year-end reports, annual renewals). Count by account, not in aggregate: users, active weeks, last use, plan, revenue, and API or integration calls as well as in-product use. Include data stored in the feature that customers may need to export. An aggregate "2 per cent of users" can be one large customer's entire finance team.

Read `references/usage-and-classification.md` for the query, what to include, and the classification sheet.

### 3. Classify every account

- **Unaffected**: no use in the window and no contract or retention obligation names the feature.
- **Replaceable**: the replacement covers what they actually do with the feature today, checked against their usage, not against the feature list.
- **Blocked**: they use something the replacement lacks, a contract names the feature, or a regulatory or retention obligation depends on data held in it.

For each blocked account, record the specific gap. Each gap then needs one decision: close it in the replacement, offer a workaround or a partner, or accept the loss of that account, named with its revenue and signed off by whoever owns the revenue. Check contracts and order forms for named features and for data-retention commitments; this is procedure, not legal advice, so have legal confirm what the contracts require.

### 4. Set the date from the slowest segment

Estimate migration time per segment: self-serve accounts can often move in days; enterprise accounts may need a change window, a procurement step for a replacement or a partner, or a quiet period around year-end. The end date is the slowest segment's realistic migration time plus the notice, and it must respect every contract that names the feature, either by falling after that commitment ends or through a named, dated extension for that one account. Engineering convenience does not set the date. Once announced, hold it: a date that moves teaches customers to wait for the next one.

### 5. Run the sequence, with a gate at each stage

1. **Announce** — account owners tell blocked and top accounts personally first; then written notice to every affected account with the date, the reason, the replacement and the migration guide; then public documentation and a deprecation notice in the changelog.
2. **Close to new sign-ups** — new accounts and newly upgrading accounts can no longer start using it, so the list stops growing.
3. **In-product warning** — shown to the people who use it, at the point of use, with the date and a link to the guide.
4. **Brown-out windows** — short, announced periods in which the feature is switched off, to surface dependencies nobody declared (scripts, integrations, a team nobody knew about). Each brown-out is followed by a sweep of support tickets and errors for newly discovered users.
5. **Read-only** — no new data; existing data viewable and exportable.
6. **Remove** — the feature, its code, its data under the retention policy after export was offered, its docs, its price-list entry, its billing item and its support macros.

Move to the next stage only when the gate holds: no new blocked accounts discovered at the last stage, and the blocked count falling on plan. Read `references/sunset-sequence.md` for the gates, brown-out design, message templates and the removal checklist.

### 6. Track to zero blocked accounts

Report weekly: accounts per class, blocked accounts with their gap and decision, usage trend, and discoveries from brown-outs. The sunset is done when unresolved blocked accounts reach zero — each migrated, on an accepted alternative, gone with a signed-off decision, or extended to a dated end — and usage in the final window is zero, apart from extended accounts, which run on their own end date with a per-account removal step (switch off the path, delete their data) at that date. Then remove everything in the checklist and watch support tickets and error logs for calls to the removed feature for a few weeks afterwards.

## Output format

```markdown
## Why and replacement
[Cost of keeping it; what replaces it, or that nothing does.]

## Usage
[Window and why; accounts using it, by plan and revenue; API and integration use; stored data.]

## Classification
[Counts per class; blocked accounts with gap and decision; contracts that name the feature.]

## Date
[Slowest segment and its migration estimate; notice; end date.]

## Sequence
[Each stage with its date, gate and owner; brown-out schedule.]

## Tracking
[Weekly report fields; done criteria; removal checklist owner.]
```

## Anti-patterns

**Date first, usage later.** The date then collides with the customers nobody looked for, and slips.

**A usage window shorter than the job.** A quarterly or annual task is invisible in thirty days of data.

**Aggregate usage.** "Two per cent of users" hides which accounts and how much revenue.

**Announcing by changelog alone.** Blocked accounts hear it from their account owner first.

**Skipping brown-outs.** The undeclared integration is found on removal day instead of during a planned window.

**Removing the code but not the price-list entry, the docs or the macros.** The feature keeps being sold and supported after it no longer exists.

## Reference files

- `references/usage-and-classification.md` — read at steps 2 and 3: the usage query, the window choice, the classification sheet and the blocked-gap log.
- `references/sunset-sequence.md` — read at steps 4 to 6: stage gates, brown-out design, message templates, the weekly report and the removal checklist.
