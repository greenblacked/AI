# Page indexing statuses, parameter policy and migrations

## Contents

- Statuses: cause, check and fix
- Parameter policy
- Migration checklist

Use this with an export from Search Console's Page indexing report. Filter the report by submitted sitemap first, so each status can be read per template.

## Statuses: cause, check and fix

| Status | Usual cause in a JavaScript app | Check | Fix |
| --- | --- | --- | --- |
| Soft 404 | Catch-all route answers `200` for missing records; or the data API failed for the crawler and the page rendered an error | curl the example for its status; read the URL Inspection screenshot | Server `404`/`410` for missing records; fix or allow the API; `noindex` on client-only error views |
| Crawled - currently not indexed | Rendered page is thin or near-identical to its siblings; content arrives after an interaction | Rendered HTML for the unique phrase; compare two siblings | Server-render the content; make the page distinct or stop it being crawlable |
| Discovered - currently not indexed | Crawl spent on parameter and facet URLs; slow or erroring server | Crawl stats report: response time, status mix, file types; count of parameter URLs discovered | Parameter policy below; fix server response time |
| Duplicate without user-selected canonical | No canonical in the raw HTML, or it is set only by script | `extract` on raw HTML | Absolute self-canonical in the server response |
| Duplicate, Google chose different canonical than user | Internal links, sitemap, redirects or hreflang point at another variant | Compare the declared canonical with the one URL Inspection reports Google selected; grep internal links for the other form | Make every signal agree on one form of slash, case, host and protocol |
| Alternate page with proper canonical tag | Working as intended for variants | Only act if this page should rank on its own | Give it a self-canonical, or leave it |
| Excluded by 'noindex' tag | Staging `noindex` or `X-Robots-Tag` leaked to production; script-added `noindex` on a valid view | `curl -sSI` for the header; raw HTML for the meta tag | Decide `noindex` on the server per environment; remove from valid views |
| Blocked by robots.txt | A disallow rule wider than intended | The robots.txt report in Search Console; the rule that matched | Narrow the rule; use `noindex` instead if the page must be fetched to be dropped |
| Indexed, though blocked by robots.txt | URL is linked from elsewhere but cannot be fetched, so `noindex` is never seen | Same | Allow the fetch and serve `noindex`, or accept it |
| Page with redirect | Old URLs after a move; links or sitemap still use them | grep sitemaps and templates for old URLs | Point links and the sitemap at the final URL |
| Not found (404) | Deleted records; broken internal links | Where the URL is linked from (URL Inspection referring page) | Fine for deleted content; fix the link if internal |
| Server error (5xx) | Server rendering failing or timing out under crawler load | Server logs filtered to verified Googlebot; crawl stats | Fix the render path; cache rendered output |
| Redirect error | Chains, loops, or a redirect target that is too long | `curl -sSIL` and count the hops | One hop from old to final |
| Blocked due to access forbidden (403) or unauthorized request (401) | Bot protection, a firewall rule or an auth wall blocking the crawler | Logs for verified Googlebot requests and their status | Allow verified crawlers; keep private pages out of links and sitemaps |

A status that is expected for a URL is not a defect. Read each one against what that template is meant to do before fixing it.

## Parameter policy

Write one row per parameter the site generates, and keep the table next to the routing code so a new filter cannot ship without a row.

| Parameter | Example | Changes content? | Decision | Mechanism |
| --- | --- | --- | --- | --- |
| `category` | `/shoes?category=running` | Yes, a distinct listing people search for | Indexable | Promote to a path, self-canonical, in sitemap |
| `colour`, `size` | `?colour=red&size=9` | Narrows a listing | Not crawled | robots.txt disallow on the pattern; links may still exist |
| `sort` | `?sort=price_asc` | Reorders only | Crawlable, canonical to base | Canonical to the unsorted listing |
| `page` | `?page=3` | Next slice | Crawlable, self-canonical | Plain `<a href>` to each page; do not canonical every page to page 1 |
| `utm_*`, `ref`, session ids | `?utm_source=mail` | No | Kept out of crawlable links | Strip in internal links; canonical to the clean URL |

Rules that hold whatever the table says:

- A disallowed URL is never fetched, so its canonical and `noindex` are never seen. Choose one mechanism per parameter.
- Emit parameters in one stable order so the same filter combination has one URL.
- Return `404` for a filter combination with no results rather than an empty listing with `200`.

## Migration checklist

Before launch:

- [ ] Every old URL collected from sitemaps, server logs, analytics landing pages and a Page indexing export.
- [ ] A one-to-one map from old to new, with no chains, tested by fetching every old URL and checking for a single `301` or `308` to a `200`.
- [ ] Step 2 of the skill rerun on staging for every template, raw and rendered.
- [ ] Canonicals, sitemaps, hreflang and internal links already pointing at the new URLs.
- [ ] Staging `noindex` and any staging robots.txt rule confirmed absent from the production build.

At launch:

- [ ] New sitemaps submitted; old sitemaps kept available for a while so the old URLs are recrawled and the redirects seen.
- [ ] For a domain move, the Change of Address tool used on the old property.

Afterwards:

- [ ] Page indexing watched per sitemap: indexed count, Soft 404, Page with redirect, Not found.
- [ ] Crawl stats watched for a rise in errors or response time.
- [ ] Redirects kept for at least a year, with an owner and a date before anyone removes them.
