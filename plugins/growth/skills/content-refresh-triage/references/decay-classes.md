# Decay classes

## Contents

- Evidence per class
- The position curve
- Control design

## Evidence per class

| Class | Test | Evidence that confirms it |
| --- | --- | --- |
| Technical | URL Inspection on the page, a crawl, the release log | A noindex, a different canonical, a redirect, a 4xx or 5xx, a robots.txt block; date matches the drop |
| Seasonality | Overlay last year's same weeks | The same shape and a similar relative drop a year ago |
| Sibling page | Page-and-query export for the top queries | The ranking URL for the query changed to another of your pages |
| Lost link | Link data or internal link crawl | A referrer was removed, redirected or its anchor changed on the date of the drop |
| SERP feature | Search the head queries in a clean browser | A new element above the result; position unchanged; CTR fell across all queries |
| Intent shift | Read the current top ten | Their format or angle differs from the page (guide against comparison, tool against article) |
| Stale facts | Read the page against the sources | Out-of-date numbers, versions, prices, screenshots, dead steps |
| CTR shortfall | The position curve below | Position and impressions held, clicks under the curve |

Check classes in the order given and stop at the first that fits. A technical fault explains a drop on its own; do not stack a second explanation onto it.

## The position curve

From a quarter of stable pages, group queries by rounded average position and compute total clicks over total impressions for each position. That is the site's own CTR at each position. A page is a CTR candidate when its CTR at its position is well below the curve. Use the site's curve and not a published industry curve, because snippets, brand strength and SERP layout differ by site.

## Control design

1. List candidate pages and bucket them by position band and impressions.
2. Within each bucket, assign alternate pages to change and to hold.
3. Change only the title and meta description on the first group; log the date.
4. After two to four weeks compare clicks per impression for each group over equal dates.
5. If the changed group beats the control, roll the pattern to the held group. If not, revert and record the failed wording.
