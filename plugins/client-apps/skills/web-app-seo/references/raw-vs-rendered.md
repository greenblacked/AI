# Raw versus rendered HTML

Use this when comparing what a crawler receives with what it renders across several templates. The comparison is the evidence every later step rests on, so record it per template rather than per impression.

## The fields to extract

For each sample URL, record these from the raw response and again from the rendered HTML:

| Field | Why it matters |
| --- | --- |
| Final status code and final URL | A `200` on a missing page is a soft 404; an unexpected redirect hides the real target |
| `X-Robots-Tag` header | A `noindex` here overrides anything in the markup and is easy to leak from staging |
| `<title>` | Missing or identical across a template means the title is set late or not at all |
| `<meta name="robots">` | `noindex` in the raw HTML may stop rendering altogether |
| `<link rel="canonical">` | Must exist in the raw HTML and agree with the rendered one |
| Main heading and a unique phrase of body text | Proves the content itself, not only the chrome, is present |
| Count of `<a href>` links | An empty shell has almost none; a page with click-handler navigation has few |
| `hreflang` links | Must be present and identical in both |
| `application/ld+json` blocks | Script-injected structured data must survive rendering |

## Raw fetch

```bash
url="https://example.com/products/123"
curl -sS -L -o raw.html -w '%{http_code} %{url_effective}\n' "$url"
curl -sSIL "$url" | grep -iE '^(HTTP|location|x-robots-tag|link|vary|cache-control)'
```

Extract the fields with a small function so raw and rendered go through the same filter:

```bash
extract() {
  grep -oiE '<title[^>]*>[^<]*</title>' "$1" || true
  grep -oiE '<meta[^>]+name="robots"[^>]*>' "$1" || true
  grep -oiE '<link[^>]+rel="canonical"[^>]*>' "$1" || true
  { grep -oiE '<link[^>]+hreflang[^>]*>' "$1" || true; } | sort
  printf 'a-href count: %s\n' "$(grep -oiE '<a [^>]*href=' "$1" | wc -l)"
  printf 'json-ld blocks: %s\n' "$(grep -oi 'application/ld+json' "$1" | wc -l)"
}
extract raw.html > raw.txt
```

The `|| true` on each line is deliberate: `grep` exits 1 when a tag is absent, which is the very case being looked for, and in a script running under `set -e` the first missing tag would end the function and leave a truncated `raw.txt` for the diff.

Then check the unique phrase directly: `grep -c "the exact product name" raw.html`. Choose a phrase without `&`, `<`, quotes or apostrophes: servers escape those in HTML (`Ben &amp; Jerry&#x27;s`), so a phrase containing one counts 0 on a page that has it. Attribute order varies between frameworks, so if an extraction comes back empty, look at the file before concluding the tag is missing.

## Rendered HTML

In Search Console, open URL Inspection for the URL, choose **Test live URL**, then **View tested page**. Copy the **HTML** tab into `rendered.html` and run the same extraction:

```bash
extract rendered.html > rendered.txt
diff raw.txt rendered.txt
```

The same panel has two more tabs worth reading every time:

- **Screenshot** — an error state, a spinner or a cookie wall covering the content means the crawler saw that, whatever the HTML diff says.
- **More info** — page resources that could not be loaded, with a reason, and JavaScript console messages. A resource marked as blocked by robots.txt is a fix in robots.txt. An "other error" on a resource is not always a problem in itself, because the live test does not fetch everything; treat it as a lead only when the screenshot or HTML is also wrong.

For the version Google stored, use **View crawled page** on the indexed result rather than the live test. A difference between the two means the page has changed since the crawl, or the live fetch and the crawl were served differently.

## Other crawlers and agents

A raw response with no content is invisible to every crawler and link-preview fetcher that does not execute JavaScript, and many do not. If the site varies its response by user agent, `curl -A` with a crawler's agent string shows the variant, but bot protection may block a spoofed crawler agent from your address; that is expected and is not evidence of what the real crawler receives. URL Inspection is fetched by Google and is the authority for Google. For server logs, confirm a request really came from Googlebot with a reverse DNS lookup to `googlebot.com` or `google.com` followed by a forward lookup that returns the same address, or against the IP ranges Google publishes.

## Per-template record

| Template | Sample URL | Raw status | Raw content present | Rendered content present | Canonical raw / rendered | Robots | Links raw / rendered | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| product | /products/123 | 200 | no | yes | none / self | index | 3 / 84 | content needs rendering |
| missing product | /products/999999 | 200 | no | error view | none / none | index | 3 / 12 | soft 404 |
