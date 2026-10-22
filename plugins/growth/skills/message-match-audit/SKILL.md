---
name: message-match-audit
description: "Audit whether a landing page delivers what the ad, email or search result promised: set each traffic source's actual promise (ad text, subject line, query) beside the page's first screen and compare words, offer, price or claim and next step; run a five-second test with five people outside the team; count competing actions, remove navigation on campaign pages, require visible proof for every claim; fix the largest mismatch per source, one page per audience, and re-measure conversion per source after a full week. Use for \"high click-through, no conversions\", \"review this landing page\" or \"bounce rate on campaign traffic is 80%\". Not for interface microcopy (content-design), usability of a product screen (ui-ux-review), building the page (website-builder) or a lost organic ranking (content-refresh-triage)."
allowed-tools: Read, Grep, Glob
---

# Message Match Audit

Done means each paid or campaign traffic source has a recorded promise, the first screen of its landing page has been compared with that promise, the biggest mismatch for each source is fixed, and conversion per source is re-measured over a full week.

The usual failure is judging the page in isolation, as a design to be improved, when the visitor arrives carrying a specific expectation from the ad, subject line or query. A page can look polished and still lose the visitor in two seconds because it does not say the thing they just clicked on.

## Scope

Use for: campaign, paid or email traffic that clicks but does not convert, a review of a landing page, high bounce on campaign traffic.

Do not use for: interface microcopy inside a product (`content-design`), why users drop off inside a product screen (`ui-ux-review`), building the page (`website-builder`), or an organic traffic decline (`content-refresh-triage`).

## Hard gates

1. Audit per source. A page serving three audiences with one headline is three mismatches to measure, not one.
2. The first screen is the unit under test: what shows before any scrolling on a phone and on a desktop.
3. One change per source per measurement window, so the effect can be attributed.
4. Do not count the team's own opinion of the page. Use people who have not seen it.

## Workflow

### 1. Collect each source's promise

For every source sending traffic, record exactly what the visitor saw before clicking: the ad headline and description, the email subject and preheader, the search query and result snippet. Take screenshots or copy the text with the date. Group sources that make the same promise.

### 2. Put promise beside first screen

For each source, take a first-screen screenshot at phone and desktop widths and compare line by line: the same key words, the same offer, the same price or claim, the same next step. Mark each as match, partial or mismatch. Common mismatches: the ad names a product and the page leads with the company; the ad quotes a price or discount the page omits; the ad says "free trial" and the page says "contact sales"; a different image or audience. Read `references/audit-sheet.md` for the sheet.

### 3. Run a five-second test

Show the first screen for five seconds to five people outside the team, then hide it and ask three questions: what is this, who is it for, what would you do next. Record the answers verbatim. If the answers do not name the promised offer, the match fails whatever the comparison said. Five people will not give a statistic; they will expose the large problems.

### 4. Count actions and clear the page

Count the things a visitor can click or fill on the first screen. A campaign page needs one primary action; remove the site navigation and footer links that lead elsewhere. Require proof for every claim shown: a number with its source, a named customer, a screenshot of the product. A claim with no visible support reads as marketing and is skipped.

### 5. Fix the largest mismatch per source

Rank mismatches by how many visitors they touch times how large the gap is. For each source, change only the biggest. Where audiences differ, build one page per audience rather than a compromise headline. Hand the build to whoever owns the page.

### 6. Re-measure

After the change, measure conversion per source for a full week at least, so weekday and weekend behaviour are both in. Compare with the prior full week of the same source, noting any budget, creative or seasonality changes. If volume is too low for a firm conclusion, record the direction and keep watching rather than declaring a win.

## What to hand back

```markdown
## Promise vs page
[Per source: promise, first-screen reading, verdict.]

## Five-second results
[Answers verbatim, count who understood.]

## Fixes
[Largest mismatch per source, owner, date.]

## Measurement plan
[Metric per source, window, baseline.]
```

## Anti-patterns

**Redesigning the page.** A new visual style does not fix an ad that promised something else.

**One page for all sources.** Averaging three promises satisfies none.

**Testing with colleagues.** They know the product, so they pass the test.

**Declaring a win on a day.** One good day is noise; wait a full week.

## Reference files

- `references/audit-sheet.md` — read at steps 2 and 3: the comparison sheet, the five-second test script and the proof checklist.
