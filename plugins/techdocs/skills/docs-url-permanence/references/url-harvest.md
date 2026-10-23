# Harvesting the URLs that matter

Read this at step 1. Each source finds links the others miss, so run all of them and
union the results; the cost of a skipped source is a 404 stream after launch.
Replace `docs.example.com` and `your-org` throughout.

## Contents

- [Search console](#search-console)
- [Access and CDN logs](#access-and-cdn-logs)
- [Links inside the product](#links-inside-the-product)
- [READMEs and samples across the organisation](#readmes-and-samples-across-the-organisation)
- [Historical captures](#historical-captures)
- [The old sitemap and build output](#the-old-sitemap-and-build-output)
- [Normalise, union and rank](#normalise-union-and-rank)

## Search console

In Google Search Console, open the Performance report, select the Pages tab, set the date
range to the longest available (the report keeps about sixteen months), and export. The
interface export stops at 1,000 rows; for a larger site, page through the Search Analytics
API with the `page` dimension instead. Do the same in any other search console the site is
registered with. Save as `harvest/search.csv` with columns `url,clicks,impressions`.

Pages with clicks are the ones whose ranking the move puts at risk; pages with
impressions but no clicks still tell you the URL is indexed.

## Access and CDN logs

A year of logs catches seasonal pages and links from annual events. For the combined log
format, the request, status and referrer sit in fixed quoted fields:

```bash
# Paths that returned 200, with hit counts. zcat -f reads plain and rotated .gz logs alike;
# awk on a .gz file reads compressed bytes, matches nothing and says nothing.
zcat -f access.log* \
  | awk -F'"' '{split($2, r, " "); split($3, s, " "); if (s[1] == 200) print r[2]}' \
  | sort | uniq -c | sort -rn > harvest/log-paths.txt

# External referrers per path: the inbound links you cannot edit
zcat -f access.log* \
  | awk -F'"' '{split($2, r, " "); split($3, s, " ");
  if (s[1] == 200 && $4 != "-" && $4 !~ /docs\.example\.com/) print r[2] "\t" $4}' \
  | sort | uniq -c | sort -rn > harvest/referrers.txt
```

A CDN's log export uses its own field layout; read the provider's schema rather than
assuming the combined format. Strip query strings that are pure tracking (`utm_*`) during
normalisation, not here, so the raw counts stay inspectable.

## Links inside the product

These are the highest-value rows: they sit in binaries and installed packages that a docs
redeploy cannot change. Search every product repository, including old release branches
that customers still run:

```bash
rg --no-filename -o "https?://docs\.example\.com[^\s\"'<>)\]]*" \
  | sort | uniq -c | sort -rn > harvest/product-links.txt
```

Include CLI help text, error messages, UI strings, SDK docstrings, generated client
libraries, email and notification templates, and the marketing site. Keep the fragment on
these rows: an error message linking to `#proxy-settings` is an anchor the new page must
keep.

## READMEs and samples across the organisation

```bash
gh search code "docs.example.com" --owner your-org --limit 1000 \
  --json repository,path,url > harvest/org-code.json
```

The code search API returns at most 1,000 results per query; when the count reaches that,
split the query by repository or by path prefix. Add partner integration guides and
marketplace listings you know about by hand — they will not appear in your organisation's
search.

## Historical captures

The Internet Archive's CDX index lists URLs the site served at any point, including pages
renamed long before your logs begin:

```bash
curl -fsSLG 'https://web.archive.org/cdx/search/cdx' \
  --data-urlencode 'url=docs.example.com/*' \
  -d 'fl=original' -d 'collapse=urlkey' -d 'filter=statuscode:200' \
  > harvest/archive.txt
```

Treat these as candidates. A URL that only the archive knows about and that has no
referrers and no search impressions can take a pattern rule instead of a hand-checked row.

## The old sitemap and build output

```bash
curl -fsSL https://docs.example.com/sitemap.xml \
  | rg -o '<loc>[^<]+' | sed 's/<loc>//' > harvest/sitemap.txt
```

If the sitemap is an index, its `<loc>` entries are child sitemap files, not pages: fetch each child and extract from those. Also list every HTML file in the last build of the old site. This is the baseline set;
everything else adds to it.

## Normalise, union and rank

Normalise to path plus meaningful query string, keep fragments in a separate column, drop
tracking parameters, and keep case as served (many hosts treat paths case-sensitively).
Then rank by inbound value:

| Tier | Source | Mapping effort |
| --- | --- | --- |
| 1 | Product links | Hand-checked row, anchor verified |
| 2 | Search clicks | Hand-checked row |
| 3 | External referrers | Hand-checked row for the top of the list, pattern rule below |
| 4 | Everything else | Pattern rule, verified by the replay |

```python
#!/usr/bin/env python3
"""Union harvested URLs into old-urls.csv: path,fragment,tier,sources."""

import csv
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit

TRACKING = ("utm_", "gclid", "fbclid")
rows = {}


def add(raw, source, tier):
    parts = urlsplit(raw.strip() if "://" in raw else "https://x" + raw.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.startswith(TRACKING)
    ]
    path = parts.path or "/"
    if query:
        path += "?" + urlencode(query)
    key = (path, parts.fragment)
    tier_now, sources = rows.get(key, (9, set()))
    rows[key] = (min(tier_now, tier), sources | {source})


for spec in sys.argv[1:]:  # file:tier:label, one URL or path per line
    name, tier, label = spec.split(":")
    with open(name, encoding="utf-8") as fh:
        for line in fh:
            token = line.split()[-1] if line.split() else ""
            if token:
                add(token, label, int(tier))

with open("old-urls.csv", "w", newline="", encoding="utf-8") as out:
    w = csv.writer(out)
    w.writerow(["path", "fragment", "tier", "sources"])
    for (path, frag), (tier, src) in sorted(rows.items(), key=lambda r: (r[1][0], r[0])):
        w.writerow([path, frag, tier, ";".join(sorted(src))])
```

A path appears once per distinct fragment, and its tier is the lowest among its rows. Prepare each input as one URL or path per line. The last whitespace-separated token is
taken, so `uniq -c` output such as `log-paths.txt` works directly, but cut the path column
out of `referrers.txt`, the URL column out of the search export and the `url` field out of
the code-search JSON first, writing the results to `harvest/search.txt` and
`harvest/referred.txt`. Then run, for example,
`python3 union.py harvest/product-links.txt:1:product harvest/search.txt:2:search
harvest/referred.txt:3:referrer harvest/sitemap.txt:4:sitemap`.
