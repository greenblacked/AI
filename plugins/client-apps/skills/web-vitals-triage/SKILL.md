---
name: web-vitals-triage
description: "Find why a Core Web Vital is poor for real users and fix the part that dominates: refuse lab scores until p75 field data is split by device and URL group, pull attribution (the LCP element and its four sub-parts, the slow interaction's target with its input delay, processing and presentation phases, the node that shifted), change only the dominant sub-part, and judge the fix on the 28-day field window rather than a Lighthouse re-run. Use when someone says \"Lighthouse is green but Search Console says poor\", \"INP is 400ms on mobile\", \"our LCP fails Core Web Vitals\", \"CLS keeps flagging the product page\" or \"CrUX says we are slow\". Not for building or auditing a whole site (website-builder), a slow function or server endpoint (profiling), or back-button navigations that reload (bfcache-eligibility)."
allowed-tools: "Read, Grep, Glob"
---

# Web Vitals Triage

Done means you can name the metric, the device class and the URL group that fail at the 75th percentile, the one sub-part or phase that holds most of that time, the change aimed at it, and the date the field data will show whether it worked.

The usual failure is optimising the lab. Someone runs Lighthouse, gets 95, ships three "performance fixes" it suggested, and Search Console still reports the same URLs as poor a month later. Lighthouse measures one cold load on an emulated phone with no interactions, no consent banner, no logged-in state and no third-party tag that fires on scroll; the field measures real visits, at the 75th percentile, over 28 days. The two disagree routinely, and when they do the field is the one Google ranks on and users feel. The second failure is fixing everything at once: a poor LCP is almost always one sub-part out of four, and a change aimed at the other three moves nothing while costing a release.

## Scope

Use for: a poor or needs-improvement LCP, INP or CLS in Search Console, PageSpeed Insights, CrUX or your own real-user monitoring; a lab score that disagrees with field data; choosing which of several suggested fixes is worth doing; proving a fix landed.

Do not use for: building a site or a broad audit across accessibility, security and SEO (`website-builder`); a slow server handler or function where the time is inside your own process (`profiling`) — come back here only if TTFB is the dominant LCP sub-part and you need to know how much it must drop; back and forward navigations that reload instead of restoring (`bfcache-eligibility`), although a better restore rate does improve field vitals.

## Thresholds

All three are judged at the 75th percentile of page views, separately for phones and desktops.

| Metric | Good | Poor | What it measures |
| --- | --- | --- | --- |
| LCP | 2.5 s or less | over 4.0 s | Render time of the largest image or text block in the viewport |
| INP | 200 ms or less | over 500 ms | Close to the worst interaction latency on the page, from input to next paint |
| CLS | 0.1 or less | over 0.25 | The largest burst of unexpected layout shift in a session window |

## Workflow

### 1. Get field data before reading a lab score

Do not open Lighthouse yet. Collect the p75 for the failing metric from the field, split two ways:

- **By device class.** Phone and desktop are scored separately and usually fail for different reasons. A desktop pass hides a phone fail in any blended number.
- **By URL group.** A route template (`/product/:id`), not individual URLs, and not the origin. Search Console already groups similar URLs; your own monitoring should group by route. One template almost always carries most of the failing traffic.

Sources, in order of preference: your own real-user monitoring with attribution (step 2 needs it); the CrUX API or CrUX History API for the URL or origin; Search Console's Core Web Vitals report for which groups fail. `references/field-data.md` has the CrUX queries, a minimal attribution snippet if you have no monitoring, and the reasons lab and field disagree.

If a URL has too little traffic for CrUX, PageSpeed Insights falls back to origin-level data and the CrUX API returns a 404 for that URL. Say so rather than presenting an origin number as the page's.

Gate: write down metric, device, group and p75 before going further. If nobody can produce a field number at all, the first deliverable is the monitoring, not a fix.

### 2. Pull attribution for the failing group

A p75 tells you that a page is slow, not why. Attribution splits the time into parts, and the parts decide the fix.

**LCP** is four sub-parts that sum to the total:

| Sub-part | From | To | Rough healthy share |
| --- | --- | --- | --- |
| Time to first byte | Navigation start | First byte of HTML | about 40% |
| Resource load delay | TTFB | LCP resource starts loading | under 10% |
| Resource load duration | Load start | Load end | about 40% |
| Element render delay | Load end | LCP element painted | under 10% |

Also record which element was the LCP and whether it was an image or text. A text LCP has no load delay or duration; the time is TTFB and render delay, usually web fonts or render-blocking CSS and JavaScript.

**INP** is one interaction, broken into three phases: input delay (the main thread was busy when the user acted), processing duration (your event handlers ran), and presentation delay (style, layout and paint of the next frame). Record the interaction's target element, its type and whether the page was still loading. Long Animation Frame entries name the scripts that ran in that frame, including third parties.

**CLS** is attributed to the node that shifted the most in the worst session window, the time of that shift, and whether it happened during load or after.

Gate: the dominant part is named with its share of the p75 before any code changes. If it is less than half and nothing else stands out, say the metric is spread thin and that the fix is several smaller changes, measured one at a time.

### 3. Fix only the dominant part

`references/attribution-and-fixes.md` maps each sub-part and phase to the changes that move it and the ones that look relevant but do not. The short version:

- **TTFB dominates:** the server, CDN or redirects. Cache the HTML at the edge, remove redirect hops, and hand the server work to `profiling` if the handler itself is slow.
- **Load delay dominates:** the browser found the LCP resource late. Put it in the HTML as an `img` element rather than a CSS background or a client-rendered node, remove `loading="lazy"` from it, and give it `fetchpriority="high"`.
- **Load duration dominates:** the resource is too large or competing for bandwidth. Serve the right size and a modern format, and stop lower-priority requests from starting first.
- **Render delay dominates:** the resource arrived and something stopped it painting — render-blocking stylesheets or scripts, an A/B testing snippet that hides the page, client-side rendering, a font.
- **Input delay dominates:** long tasks on the main thread at the moment of input, often hydration or third-party scripts. Break the tasks up and defer what is not needed yet.
- **Processing dominates:** the handler does too much before the next paint. Paint the visible response first and move the rest after it.
- **Presentation dominates:** the frame itself is expensive — a large DOM, forced layouts, style recalculation over thousands of nodes.
- **CLS:** reserve space for whatever arrives late (images, embeds, ads, consent banners), keep font metrics stable across the swap, and animate with `transform` rather than properties that move layout.

Check the change in the lab for the specific sub-part — a DevTools performance trace of that page and interaction, on a throttled CPU — to confirm it moves the part you aimed at. That trace is the check that the change works, not proof that the field has improved.

### 4. Judge in the field, on the field's clock

CrUX and Search Console are rolling 28-day windows. A fix shipped today is fully reflected only after 28 days of traffic have accumulated on it, and moves the number gradually before that.

- Annotate the release date. Compare the failing group's p75 from your own monitoring for the week before and the week after, for the same device class, which shows the effect within days.
- Start Search Console's validation for the group only once your own monitoring shows the p75 inside the threshold; its monitoring period runs for 28 days.
- Read the CrUX History API weekly series for the URL or origin to confirm the trend.

A re-run of Lighthouse showing a better score proves nothing about the field, in either direction.

## Anti-patterns

**Chasing the Lighthouse score.** The performance score is a weighted blend of lab metrics, and INP is not one of them. A 100 can coexist with a poor field INP.

**Averaging.** A mean of 1.8 s can hide a p75 of 3.2 s on phones. Use the percentile the threshold is defined on, per device class.

**Preloading everything.** A preload for the LCP image helps; preloads for five fonts and three scripts compete with it and can make LCP worse.

**Lazy-loading the hero image.** The most common load-delay defect, usually added by a component library default or a blanket image policy.

**Reading one session.** A single slow interaction in your own browser is an anecdote. Find whether the same target and phase dominate the p75 before fixing it.

**Declaring victory after a week of CrUX.** The 28-day window still contains three weeks of the old code.

## Output format

```markdown
## Failing
[Metric, device class, URL group, field p75 and source, date range.]

## Attribution
[Sub-parts or phases with their share of the p75; the LCP element, interaction target or shifting node.]

## Change
[The one change, which part it targets, and the lab trace showing that part moved.]

## Verification
[Release date, real-user before and after for the same group and device, and the date the 28-day window closes.]

## Not done
[Fixes considered and rejected, with the reason: wrong sub-part, too small a share, or lab-only.]
```

## Reference files

- `references/field-data.md` — read in step 1: CrUX API and History API requests, a minimal real-user attribution snippet, how to group by route, and why lab and field disagree.
- `references/attribution-and-fixes.md` — read in step 3: for each LCP sub-part, INP phase and CLS cause, the changes that move it, the ones that do not, and how to confirm the move in a trace.
