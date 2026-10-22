# Inventory columns

Read this at step 1, when setting up the sheet.

## Contents

- Columns
- Sources
- Sanity checks

## Columns

| Column | Source |
| --- | --- |
| URL (canonical) | Crawl and sitemap |
| Status code, indexability | Crawl |
| Section | URL path |
| Published, last modified | CMS or page |
| Word count | Crawl |
| Main query | Search Console, top query by clicks for the page |
| Clicks, 12 months | Search Console Performance report, Pages tab, or the Search Analytics API |
| Impressions, 12 months | Search Console |
| Referring domains | Backlink tool |
| Assisted conversions | Analytics, multi-touch or assisted report |
| Internal inbound links | Crawl |
| Decision | Keep, refresh, merge, redirect, remove (410) |
| Rule that decided | 1 to 4 from the skill |
| Target URL | For merge and redirect |

## Sources

Search Console shows a limited number of rows per export in the interface; use the API or a bulk export to get all pages on a large site. Join on the canonical URL, not the requested one, and normalise trailing slashes, case, parameters and protocol before joining.

## Sanity checks

- Total clicks in the sheet should be close to the property total; a large gap means the join lost URLs.
- Pages with referring domains but zero clicks need a human look before any decision.
- Pages that redirect or canonicalise elsewhere do not belong in the list as separate rows.
