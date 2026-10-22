---
name: campaign-tagging-standard
description: "Create and enforce a UTM naming standard so campaign data stays usable: lowercase only, source and medium drawn from a closed list enforced by a dropdown or validated link-builder sheet, campaign names that encode date and objective, content for the creative variant, and no tags on internal links because they overwrite the true source. Normalise parameters at the redirect edge, map the closed list onto the analytics channel grouping, audit the source and medium export monthly with an owner per fix, and keep a dated change log. Use for \"our UTMs are a mess\", \"set up a naming convention\", \"newsletter shows up as three sources\" or \"link builder for the team\". Not for auditing the conclusions drawn from the data (attribution-sanity-check), checking an email before it sends (campaign-preflight) or why mail lands in spam (deliverability-triage)."
allowed-tools: Read, Glob, Grep
---

# Campaign Tagging Standard

Done means one page defines every allowed tag value, a team member cannot build a link outside it without noticing, the analytics channel report matches the standard, and a monthly audit names an owner for each deviation.

The usual failure is a free-text field. One person types `Newsletter`, another `newsletter`, a third `email-newsletter`, and the report shows three sources that are one. Analytics tools treat values as case-sensitive strings, so the damage is permanent for the rows already collected; only prevention works.

## Scope

Use for: defining the standard, building the link builder, normalising at the edge, and auditing compliance.

Do not use for: judging whether the numbers support a budget decision (`attribution-sanity-check`), the pre-send gate on a bulk email (`campaign-preflight`) or deliverability problems (`deliverability-triage`).

## Hard gates

1. The closed lists exist before any link is built. A list that grows by whoever needs a value first is a free-text field with extra steps.
2. No tracking parameters on links between pages of your own site or app.
3. One owner for the standard and one for the list of allowed values; changes go through them.

## Workflow

### 1. Inventory what is already in the data

Export the source and medium table for the last quarter from the analytics tool and list every distinct value with its sessions. Group near-duplicates (case, hyphen versus underscore, plural). This shows the real channels in use, which is the starting point for the closed list, and it gives a baseline to measure the audit against. `references/standard-template.md` has the layout for the result.

### 2. Write the one-page standard

- Lowercase only, no spaces; choose underscore or hyphen once and say which; the date prefix in `utm_campaign` keeps its hyphens as a stated exception.
- `utm_source`: where the click comes from (the sender or site), from a closed list.
- `utm_medium`: the type of channel, from a closed list. Choose values that the analytics default channel grouping classifies correctly, and confirm that against the tool's current documentation instead of assuming it.
- `utm_campaign`: encodes the objective and the start date, for example `2026-03_trial_launch`. Date first sorts well and makes stale campaigns obvious.
- `utm_content`: the creative or placement variant (`hero_blue`, `footer_link`). Use `utm_term` only for paid search keywords.
- Every campaign has a row in a campaign register with an owner, so a campaign value can be traced to a person.

### 3. Make the wrong value hard to type

Build the link builder as a sheet or form where source and medium are dropdowns fed from the closed lists, the campaign name is assembled from date and objective fields, and a formula lowercases and URL-encodes the result. Add a validation column that flags any value outside the list. Provide the sheet to everyone who tags; a standard held only in a document is not followed.

### 4. Keep internal links clean

A tagged internal link overwrites the original source of the visit and, depending on the tool, starts a new session. The newsletter that sent a reader to the site then gets no credit for the purchase, and the report credits an internal banner. Use event tracking or a separate internal-promotion parameter for banners and cross-links, never the campaign parameters.

### 5. Normalise at the edge

Where redirects or a link shortener sit in front of the site, lowercase and normalise the tracking parameter values at that layer, and nothing more. Do not strip values that are not on the list: stripped visits arrive as direct or referral traffic and the monthly audit can no longer see them. Either pass them through, or rewrite the value to a fixed sentinel (for example `utm_medium=unlisted`) and log the original value, so step 7 can still find and trace them. This protects against links made outside the builder (partners, old posts). Test with a mixed-case link and an unknown medium and look at what lands in analytics. The edge change belongs to whoever owns the redirect layer; hand them the exact rules.

### 6. Map the lists onto the channel grouping

For each allowed source and medium pair, record which channel it should land in. Check a test visit per pair appears in that channel in the report. Anything falling to "unassigned" or "other" is a gap in the list or the grouping, to be fixed in one place.

### 7. Audit monthly

Export the source and medium table, filter out the allowed pairs, and list what is left with sessions and landing pages. Assign each leftover an owner and a fix: add a legitimate new value to the list (through the owner), correct the source link, or add an edge rule. Re-run next month; the leftover count should fall. `references/audit-checklist.md` has the steps.

### 8. Log changes

Every change to a list or rule gets a dated line: what, why, who approved. When a value is retired, report history under the old name stays as is, and the log is how a reader finds out that two names are one.

## Hand back

The one-page standard, the closed lists with channel mapping, the link-builder layout, edge rules for the redirect owner, the first audit with owners per deviation, and the change log. State which channels you could not test.

## Anti-patterns

**Retroactive clean-up in the report only.** A filter that merges values hides the mess in one view and leaves every other report wrong.

**Campaign names with free text.** `spring-sale-final-v2` sorts to nothing and cannot be joined to spend data.

**A medium for each team's taste.** Five mediums that mean "email" split a channel across reports.

**Leaving organic social links untagged.** Untagged links are the next failure; make the builder easier than guessing.
