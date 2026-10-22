# Cache keys and purges

Read this when normalising the cache key, wiring surrogate keys or cache tags, choosing a
purge method, and measuring offload from logs.

## Contents

- How the key is built, per CDN
- Tracking parameters to strip
- Surrogate keys and cache tags
- Purge decision table
- Measuring offload from logs

## How the key is built, per CDN

| CDN | Where the key is defined | The trap |
| --- | --- | --- |
| CloudFront | The cache policy lists which query strings, headers and cookies enter the key; the origin request policy lists what is forwarded to the origin without entering the key | Anything in the origin request policy but not the cache policy reaches the origin unkeyed. If the origin varies its response on it, the first requester decides what everyone gets |
| Cloudflare | Default key is the URL including the full query string; Cache Rules can customise query, header, cookie and host components | HTML is not cached by default; a rule that makes everything eligible also makes signed-in pages eligible unless the origin marks them `private` |
| Fastly | `vcl_hash` (or the equivalent in Compute) builds the key, usually from URL and host; `Vary` adds variants | Normalising the URL in `vcl_recv` changes the key and what the origin receives; strip parameters there, not after the hash |

On every CDN, compare two lists for each path pattern: what the origin reads from the
request, and what the key contains. Every item on the first list that is missing from the
second is either harmless (the origin ignores it for this path) or a defect.

## Tracking parameters to strip

Strip, when not used by the application itself: `utm_source`, `utm_medium`,
`utm_campaign`, `utm_term`, `utm_content`, `gclid`, `gbraid`, `wbraid`, `fbclid`,
`msclkid`, `mc_cid`, `mc_eid`, `_ga`, `_gl`. Check the analytics setup before stripping
from the request forwarded to the origin: some server-side analytics read them there.
Stripping them from the key while still forwarding them is the safe middle, provided the
origin does not change the response body on them.

Sort the remaining parameters, so `?a=1&b=2` and `?b=2&a=1` share an entry, and drop empty
values where the application treats them as absent.

## Surrogate keys and cache tags

The origin labels each response with the content it contains; a publish event purges by
label.

| CDN | Response header | Notes |
| --- | --- | --- |
| Fastly | `Surrogate-Key: product-123 category-9` | Space-separated; stripped before delivery to the client. Supports soft purge |
| Cloudflare | `Cache-Tag: product-123,category-9` | Comma-separated; stripped before delivery |
| Akamai | `Edge-Cache-Tag: product-123,category-9` | Comma-separated |
| CloudFront | No tag purge | Invalidate by path; use versioned URLs for anything that changes often |

Design the labels from the content model: one per entity a response renders (the product,
each product in a listing, the category, the author), plus one per template so a template
change can purge every page that uses it. A listing page carrying fifty product keys is
correct; it is what makes an edit to any of those products update the listing.

Check the vendor's limits on header length and keys per response before tagging large
listings, and on purge-request rate before wiring a bulk import to fire one purge per row;
batch keys per request instead.

## Purge decision table

| Change | Method | Why |
| --- | --- | --- |
| Deploy with fingerprinted assets | None for assets; purge the HTML paths or template key | Old asset URLs stay valid for pages still holding them |
| A content edit | Soft purge by the entity's key | Updates every page rendering it without a burst of full fetches |
| A template or layout change | Purge by template key | Bounded to pages using it |
| Wrong content cached under a correct key | Purge by key or path, then fix the header that let it happen | The purge alone will recur |
| Account data cached in a shared entry | Purge the affected paths, set `no-store` at the origin, open an incident | Security first, tuning later |
| Cache poisoned through an unkeyed input | Fix the key or stop forwarding the input, then purge-all with origin capacity checked | Purging first leaves the hole open |

## Measuring offload from logs

Compute from two sources over the same window and content class:

- edge requests and bytes from the CDN's access logs or analytics (CloudFront standard logs
  carry the result type in `x-edge-result-type` and bytes in `sc-bytes`);
- origin requests and bytes from the origin's load balancer or web server logs, filtered to
  requests arriving from the CDN.

```text
request_offload = 1 - origin_requests / edge_requests
byte_offload    = 1 - origin_bytes_sent / edge_bytes_sent
```

Rank URLs by origin bytes, not by miss count: one uncached video segment pattern outweighs
thousands of missed icons. Report both offload figures per class, with the window length
and whether it contained a full weekly cycle.
