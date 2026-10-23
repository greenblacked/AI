---
name: web-app-seo
description: "Make a JavaScript-rendered site indexable: fetch each template without JavaScript first and compare it with the rendered HTML from Search Console's URL Inspection, then fix in order - rendering mode, status codes and soft 404s, canonicals, truthful sitemap lastmod, reciprocal hreflang, valid structured data - with a crawl policy for faceted URLs and an indexing watch after every migration. Use when \"Google isn't indexing our SPA\", \"only the homepage shows up in search\", \"duplicate pages in search\", \"Search Console says soft 404\", \"Google chose a different canonical\" or search traffic fell after a site move. Not for building or auditing a whole site (website-builder), page wording (content-design), navigation and taxonomy (information-architecture), field Core Web Vitals (web-vitals-triage), or a server-client render mismatch (hydration-mismatch-hunt)."
allowed-tools: "Read, Grep, Glob"
---

# Web App SEO

Done means every template meant to rank returns its main content, title, canonical, links and status code in the HTML a crawler receives, Search Console's Page indexing report shows the intended URLs indexed per template, and the last migration has been watched until the indexed count recovered.

The usual failure is working from the top of the stack: rewriting titles, adding schema and resubmitting the sitemap while the crawler receives an empty shell, a `200` for a page that does not exist, or a canonical that points somewhere else. Every later fix is wasted until the earlier layer is right, so this skill works bottom-up in a fixed order and refuses to judge the result by a `site:` search, which is an estimate and not an index count.

## Scope

Use for a single-page or hybrid-rendered app that search engines index badly: pages missing from the index, duplicates, soft 404s, canonical overrides, broken locale targeting, invalid rich results, crawl waste on filter URLs, and the indexing drop after a domain, URL or framework migration.

Leave elsewhere: building the site or auditing it across performance, security and accessibility (`website-builder`); the wording on the page (`content-design`); deciding the navigation and taxonomy (`information-architecture`); field Core Web Vitals (`web-vitals-triage`); a server render that differs from the client's first render (`hydration-mismatch-hunt`).

## Gates

1. No fix before the raw-versus-rendered comparison exists for every affected template. The comparison decides which step below is the real problem.
2. Fix in the order of the workflow. A canonical on a soft-404 page, or hreflang between pages Google cannot render, changes nothing.
3. Judge by Search Console: URL Inspection for a single URL, the Page indexing report per template and per sitemap for the whole. Allow for recrawl; a fix is not proven by the next live test alone.

## Workflow

### 1. Inventory templates and sample URLs

Group URLs by template: home, category, product or article, search results, filtered listings, locale variants, user profiles. For each template pick two or three real URLs, including one deep in the hierarchy and one created recently. Export the Page indexing report's example URLs for each exclusion reason and note which templates dominate each reason. A problem that sits in one template is a code problem; one spread across all of them is usually robots, rendering or a platform setting.

### 2. Compare what the crawler receives with what it renders

Fetch each sample without JavaScript and record the status and the parts that matter:

```bash
curl -sS -o raw.html -w '%{http_code} %{url_effective}\n' -L "https://example.com/products/123"
curl -sSIL "https://example.com/products/123"   # X-Robots-Tag, Link, Location, Cache-Control
```

The header fetch follows redirects too and prints every hop: an `X-Robots-Tag` on the
final page is invisible in the headers of a redirect in front of it. The pages fetched
here carry text other people wrote, so the skill pre-approves only reading;
the user approves each `curl`, each `diff` and each edit.

Then open URL Inspection for the same URL, run **Test live URL**, and use **View tested page** for the rendered HTML, the screenshot and the list of resources that could not be loaded. **View crawled page** on the indexed result shows what Google actually stored. Compare title, meta robots, canonical, the main heading and body text, internal links, hreflang and JSON-LD across the three.

| Raw HTML | Rendered HTML | Meaning | Go to |
| --- | --- | --- | --- |
| Has content and links | Same | Rendering is not the problem | Step 4 |
| Empty shell | Has content | Depends on rendering: Google gets there late, many other crawlers and link previews never do | Step 3 |
| Empty shell | Still empty or an error state | A blocked script or API, a JavaScript error, content that waits for a click or scroll, or an API failing for the crawler | Step 3, then the resources list |
| Has `noindex` | Content, `noindex` removed by script | Google may skip rendering a `noindex` page, so the script never runs for it | Step 3 |

`references/raw-vs-rendered.md` has the full per-template checklist, a scripted extraction of the fields above, and what to read in the resources and console panels. Read it when more than one template is affected or the difference is not obvious by eye.

### 3. Fix the rendering mode

Serve indexable templates as server-rendered or statically generated HTML; keep client-only rendering for signed-in screens nobody searches for. Dynamic rendering, serving crawlers a separate pre-rendered copy, is described by Google as a workaround rather than a long-term solution, and it doubles the surface where the two copies drift.

Whatever the mode, check these in the rendered output:

- Links are `<a href="/path">` elements. A click handler on a `div` or a button is not a link to a crawler.
- Routes use the History API. Google does not treat a `#/fragment` as a separate URL.
- Content does not wait for a click, a hover or a scroll event. Lazy loading through `IntersectionObserver` or `loading="lazy"` works; loading on a scroll handler does not.
- robots.txt does not disallow the scripts, styles or API paths the page needs to render.
- `noindex` is decided on the server. Adding it with JavaScript works; removing it with JavaScript does not.

### 4. Make status codes tell the truth

A catch-all route that answers `200` for every path turns missing products, deleted articles and typos into soft 404s, and Google learns to distrust the template. The server has to know the entity does not exist: return `404` or `410` from the server for unknown routes and deleted records. Where only the client can know, either redirect with JavaScript to a URL the server answers with `404`, or add `<meta name="robots" content="noindex">` on the error view. Use server-side `301` or `308` for moves; JavaScript redirects are followed, but later and less reliably.

Look at the screenshot in **View tested page** for each soft-404 example. A page that renders an error because its data API failed or rate-limited the crawler looks like a soft 404 too, and the fix there is the API, not the router.

### 5. Settle canonicals

Each indexable page carries one absolute `rel="canonical"` in the raw HTML, pointing at a URL that returns `200`, is indexable, and is not a redirect. Do not change it with JavaScript; if a script must set it, it must agree with the raw HTML.

Google treats the canonical as a hint. "Duplicate, Google chose different canonical than user" means other signals outvoted the tag: internal links, the sitemap, redirects or hreflang pointing at another variant. Fix the signals together — one form for trailing slash, case, protocol and host — rather than restating the tag.

### 6. Make the sitemap truthful

List only canonical, `200`, indexable URLs. Set `lastmod` from the content's real last significant change, not from the build or deploy time; Google uses it only when it is consistently accurate, and ignores `changefreq` and `priority`. A single file holds at most 50,000 URLs and 50 MB uncompressed, so split with a sitemap index. Split by template as well: the Page indexing report filters by submitted sitemap, which turns "some pages are not indexed" into "40 percent of product pages are not indexed".

### 7. Make hreflang reciprocal

Each locale variant lists every alternate including itself, every alternate links back, and every target is the canonical, `200` version of that locale. Codes are ISO 639-1 language with an optional ISO 3166-1 alpha-2 region; add `x-default` for the selector or fallback page. A canonical that points across locales cancels the alternate. Declare hreflang in one place — HTML head, HTTP header or sitemap — so the three cannot disagree, and check reciprocity with a script over the sitemap rather than by sampling.

### 8. Validate structured data

Use JSON-LD that describes what is visible on the page. Check each template in the Rich Results Test for Google's features and the Schema Markup Validator for schema.org syntax, confirm the JSON-LD is present in the rendered HTML from step 2 if a script injects it, and watch the matching enhancement reports in Search Console after deploy.

### 9. Write a policy for faceted and parameter URLs

Filters, sorts, pagination and tracking parameters can create more URLs than the site has products. Search Console's URL Parameters tool has been retired, so the policy has to live in the site itself. For each parameter decide one of: indexable with its own canonical and a place in the sitemap; crawlable but canonicalised to the base listing; or kept out of the crawl with a robots.txt disallow. Do not combine a disallow with `noindex` or a canonical, because a disallowed URL is never fetched and neither is seen. Emit parameters in a stable order, keep session and tracking identifiers out of crawlable links, and return `404` for filter combinations with no results.

### 10. Treat every migration as an indexing event

A domain move, a URL scheme change and a rewrite onto a new framework all count. Before launch, collect every old URL from sitemaps, logs and a Search Console export, write a one-to-one `301` map, test the whole list with curl, and rerun step 2 against staging. Ship canonicals, sitemaps and hreflang pointing at the new URLs in the same release, keep the redirects for at least a year, and use the Change of Address tool for a domain change. Afterwards watch Page indexing per template and per sitemap, and the Crawl stats report, until the indexed count is back.

`references/indexing-statuses.md` maps each Page indexing reason to its usual cause in a JavaScript app, the check that confirms it and the fix, and holds the parameter-policy and migration checklists. Read it when working through an exclusion report or planning a migration.

## Output format

- The template table: template, sample URLs, raw versus rendered result, status code, canonical, indexing status.
- The first broken layer per template and the fix made or proposed, in workflow order.
- The parameter policy, if facets were in scope.
- What to watch in Search Console, which sitemap filter to use, and when to look again.
- Anything left: templates not sampled, crawlers other than Google not checked, redirects with a known expiry.

## Reference files

- `references/raw-vs-rendered.md` — read when comparing raw and rendered HTML across several templates: the per-template checklist, curl and diff commands, and how to read URL Inspection's resources and console output.
- `references/indexing-statuses.md` — read when working through a Page indexing report or planning a migration: each status with cause, check and fix, the parameter-policy table and the migration checklist.
