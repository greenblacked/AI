# Search Console pulls

## Contents

- Choosing windows
- Exporting
- Joining and ranking
- Caveats

## Choosing windows

Use three equal-length windows: the latest 28 complete days, the 28 days before that, and the same dates one year earlier. Align on weekday where you can, since a window that holds an extra weekend differs for most B2B sites. Search Console retains about 16 months, so run the year-ago pull early; it ages out.

## Exporting

The Performance report exports to a spreadsheet or CSV from the interface, and the Search Analytics query in the API returns up to 25,000 rows per request with paging. Request dimensions `page` and `query` separately as well as together: the page-only totals include queries Google hides for privacy, which the page-and-query rows do not, so the two never sum to the same number.

A request body for the API looks like this:

```json
{
  "startDate": "2026-09-01",
  "endDate": "2026-09-28",
  "dimensions": ["page"],
  "rowLimit": 25000,
  "startRow": 0
}
```

Run it once per window and once more with `["page", "query"]`. Keep the three files side by side under dated names.

## Joining and ranking

Full-outer-join on the page URL after normalising, treating a URL missing from a window as zero clicks and impressions; an inner join drops pages that were noindexed, removed or redirected, which are the biggest losers. List those vanished URLs as a technical-check group. Normalise by: strip fragments and tracking parameters, and pick one form of trailing slash and host. Compute for each page:

- clicks lost versus the prior window, and versus last year;
- impressions change and average position change;
- CTR change.

Sort by clicks lost. Cut at the pages explaining about 80 per cent of the summed losses on losing pages only, not the net site change, which gaining pages would shrink. Then join the page-and-query file to find the top queries per page; a page that lost one head query behaves differently from one that lost many tail queries.

## Caveats

- The final days of a window can be incomplete; end on a day you are sure is complete.
- Average position is an impression-weighted mean across queries and devices. A rise in impressions from new low-ranking queries can lower it without any loss of rank on the old ones; check the head queries separately.
- Anonymised queries are in the page totals and absent from query rows.
- A site migration changes URLs; map old to new before joining or every page looks lost.
- Branded and non-branded queries behave differently. Split them if the brand name is in many queries.
