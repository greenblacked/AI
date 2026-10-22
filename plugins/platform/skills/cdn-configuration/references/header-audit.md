# Header audit

Read this when auditing what the origin and the CDN actually send, when setting the
per-class headers, and when verifying a change.

## Contents

- The request loop
- Reading the cache-status header
- Defect checklist
- Header values per content class
- Verifying a change

## The request loop

Pick five to ten URLs per content class from the top-by-origin-bytes list, not from
memory. Request each through the CDN twice and once directly from the origin (through a
host override or the origin's own hostname, from a network allowed to reach it):

```bash
# ORIGIN_IP is the origin's address; urls.txt holds https URLs on one host, HOST
fields='cache-control|vary|set-cookie|age|etag|last-modified|cdn-cache-control|surrogate-control|x-cache|cf-cache-status|content-type'
while read -r url; do
  echo "== $url (CDN, first request)"
  curl -sS -o /dev/null -D - "$url" </dev/null | grep -iE "^(HTTP/|($fields):)"
  echo "== $url (CDN, second request)"
  curl -sS -o /dev/null -D - "$url" </dev/null | grep -iE '^(HTTP/|(age|x-cache|cf-cache-status):)'
  echo "== $url (origin)"
  curl -sS -o /dev/null -D - --resolve "$HOST:443:$ORIGIN_IP" "$url" </dev/null | grep -iE "^(HTTP/|($fields):)"
done < urls.txt
```

`curl` does not follow redirects. A `301` or `302` on the `HTTP/` line means the headers
above are the redirect's, not the page's: put the final URL in `urls.txt`, or add `-L` and
read the last block. The `</dev/null` keeps `curl` from consuming the URL list on its
standard input.

`-D -` writes the response headers to standard output while `-o /dev/null` discards the
body; a `HEAD` request (`-I`) is not equivalent, because some origins and rules treat
`HEAD` differently from `GET`. Repeat the loop with a logged-in session cookie on the paths
that have a signed-in variant, from a test account, to confirm those responses are marked
`private` or `no-store`.

## Reading the cache-status header

| CDN | Header | Values worth knowing |
| --- | --- | --- |
| CloudFront | `X-Cache` | `Hit from cloudfront`, `RefreshHit from cloudfront` (revalidated with the origin), `Miss from cloudfront`, `Error from cloudfront` |
| Cloudflare | `CF-Cache-Status` | `HIT`, `MISS`, `EXPIRED`, `STALE`, `UPDATING`, `REVALIDATED`, `BYPASS` (origin or rule said not to cache), `DYNAMIC` (not eligible for cache under current rules) |
| Fastly | `X-Cache`, `X-Cache-Hits`, `X-Served-By` | With shielding, two comma-separated entries: shield then edge; `MISS, HIT` means the edge hit |

`Age` is the number of seconds the object has been in a shared cache. An `Age` that never
rises on a class you meant to cache means it is not being cached, whatever the status
header says. On Cloudflare, `DYNAMIC` on HTML is the default outcome without a cache rule
making HTML eligible; it is not a fault in the origin headers.

## Defect checklist

Per URL sampled, mark each that applies:

- [ ] No `Cache-Control` at all
- [ ] `Vary` lists `Cookie`, `User-Agent`, or a header the response does not actually vary on
- [ ] `Set-Cookie` present on a response meant to be shared
- [ ] `private` or `no-store` on a public asset
- [ ] `max-age` longer than an hour on a URL without a content hash
- [ ] HTML with no `stale-while-revalidate` or `stale-if-error`
- [ ] Session-dependent response without `private` or `no-store`
- [ ] Response differs between two requests that the cache key treats as the same
- [ ] Edge rule overriding the origin header, with no recorded reason

The second-to-last item is the one that matters most for safety: request the same URL with
and without a header or cookie the key ignores, and compare the bodies.

## Header values per content class

```text
Fingerprinted asset     Cache-Control: public, max-age=31536000, immutable
Unversioned media       Cache-Control: public, max-age=3600, s-maxage=86400
                        Surrogate-Key / Cache-Tag: <content ids>
HTML (anonymous)        Cache-Control: public, max-age=0, s-maxage=60, stale-while-revalidate=300, stale-if-error=86400
Signed-in HTML or API   Cache-Control: private, no-store
Public API read         Cache-Control: public, s-maxage=30, stale-while-revalidate=30
                        ETag: <validator>
Not found               Cache-Control: public, max-age=60
Server error            Cache-Control: no-store
```

The numbers are starting points. Derive the HTML `s-maxage` from how stale a page may be
after an edit when no purge fires: that is the bound the business is agreeing to.
`stale-while-revalidate` and `stale-if-error` are defined in RFC 5861; the major CDNs
honour them, but confirm for yours and for the specific product tier before relying on
`stale-if-error` as outage cover.

`immutable` tells browsers not to revalidate on reload. It is only safe on URLs whose
content can never change, which is what the content hash guarantees.

## Verifying a change

1. Run the request loop on the changed class: the first request is a miss, the second a
   hit with a rising `Age`.
2. Edit one piece of content and fire its purge; confirm the next request misses or
   revalidates and returns the new content within the expected time.
3. On paths with a signed-in variant, confirm that a signed-in request is never a hit and
   that the anonymous response after it contains no account data.
4. After a full traffic cycle, recompute offload by requests and bytes for the class and
   compare with the baseline.
