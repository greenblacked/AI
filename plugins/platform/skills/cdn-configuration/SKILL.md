---
name: cdn-configuration
description: "Tune CDN and edge caching for origin offload and safe purges: audit the origin's Cache-Control and Vary before any edge rule, normalise the cache key (strip tracking parameters, allowlist cookies), make fingerprinted assets immutable and HTML short-lived with stale-while-revalidate, shield the origin, purge by surrogate key rather than wildcard, keep authenticated responses out of shared cache, and report origin offload, not hit ratio alone. Use for a low hit rate, a purge that floods the origin, stale pages after a deploy, CloudFront, Cloudflare or Fastly cache rules, or \"a user saw someone else's account page\". Not for in-app or Redis caching (application-caching), building the site (website-builder), sporadic 502s at the load balancer (intermittent-502-hunt), DNS records (dns-operations), certificates (certificate-automation), or a CDN outage happening now (incident-response)."
allowed-tools: Read, Grep, Glob
---

# CDN Configuration

The edge is configured well when the origin's own headers say how long each response may
be cached and by whom, the CDN keys on only what changes the response, a deploy or a
content edit updates exactly the objects it changed within a known time, no response
carrying one user's data is ever served to another, and the team can state what fraction
of requests and bytes the origin no longer serves.

The usual failure is configuring the CDN to compensate for an origin that sends no useful
headers. A rule that caches `*.js` for a day, another that caches HTML for five minutes,
an exception for the account pages, a wildcard purge on every deploy: each patch works
until the first path that matches the wrong rule. The two expensive outcomes are a cache
that serves a logged-in page to strangers, and a purge-all during peak that sends every
request to an origin sized for a tenth of them. Both come from keying and expiring on
guesses rather than on what the origin declared.

## Scope

Use for: auditing and tuning an existing CDN or edge cache (CloudFront, Cloudflare,
Fastly, Akamai, a self-run Varnish or nginx tier); a low hit ratio or high origin load;
stale content after deploys or edits; designing purge and invalidation; investigating a
response served to the wrong user; deciding what may be cached at all.

Do not use for: caching data inside the application or in Redis or Memcached, which is
`application-caching`; building or redesigning the site itself, which is
`website-builder`; sporadic 502 or 504 errors between a load balancer and its targets,
which is `intermittent-502-hunt`; DNS records, delegation and zone hygiene, which is
`dns-operations`; TLS certificate issuance and renewal, which is `certificate-automation`;
finding which workload generates an egress bill line, which is `data-transfer-forensics`;
HTTP API caching semantics such as ETags and conditional requests in a contract, which is
`api-design`.

## Gates

1. **Authenticated or personalised responses stay out of shared cache by default.** The
   origin marks them `private` or `no-store`. A shared-cache entry for such a response is
   allowed only when the cache key includes the identity or the variant deliberately, and
   that exception is written down with its owner.
2. **No change ships without the baseline.** Offload and hit ratio by content class are
   measured before the change and again after a full traffic cycle; a tuning change with no
   before-and-after figure is an opinion.
3. **No purge-all as routine.** A full purge is an incident tool, used with the origin's
   capacity checked first.

## Workflow

No command is pre-approved. The `curl` requests, purges and invalidations below run with the
user's approval: response headers and bodies are text the origin or a visitor controls, and
a `curl` grant can also send data and call a purge API.

### 1. Measure the baseline

From the CDN's logs or analytics, and from the origin's own access logs, record per
content class (fingerprinted assets, images and media, HTML, API, downloads):

- requests and bytes served at the edge;
- requests and bytes that reached the origin, from the origin's logs rather than the CDN's
  idea of a miss, because revalidations, uncacheable passes and shield traffic all reach
  it too;
- origin offload: one minus origin requests over edge requests, and the same for bytes;
- the top URLs by origin bytes and by origin requests.

Report offload rather than hit ratio alone. A hit ratio can rise while origin load stays
flat (more hits on tiny objects, the same misses on large ones), and depending on how the
vendor counts bypassed and uncacheable requests, a site that passes most traffic through
can still show a respectable number.

### 2. Audit the origin's headers before any edge rule

For a sample of URLs in each class, request through the CDN and directly from the origin,
and read `Cache-Control`, `Vary`, `Set-Cookie`, `Age`, `ETag` or `Last-Modified`, and the
CDN's cache-status header. Read `references/header-audit.md` for the request loop, what
each vendor's status header means, and the defect checklist.

The defects that decide most outcomes:

| Finding | Consequence |
| --- | --- |
| No `Cache-Control` | The CDN applies its default or heuristic TTL; behaviour changes when the vendor or the rule order does |
| `Vary: Cookie` or `Vary: User-Agent` | One cache entry per cookie jar or browser build; effectively uncached |
| `Set-Cookie` on a cacheable response | Either the CDN refuses to cache it, or it caches the cookie and hands one session to everyone; find out which yours does |
| `private` on public assets | Uncached at the edge for no reason |
| Long `max-age` on unversioned URLs | Browsers keep stale copies that no CDN purge can reach |

Fix headers at the origin. An edge override is acceptable as a stopgap for an origin you
cannot change, recorded with the reason, because the override is invisible to the next
person reading the application code.

### 3. Set policy per content class

| Class | Origin header | Why |
| --- | --- | --- |
| Fingerprinted assets (hash in the file name) | `public, max-age=31536000, immutable` | The URL changes when the content does, so the object never needs purging |
| Images and media without fingerprints | `public`, browser `max-age` up to an hour, edge `s-maxage` of hours to a day, plus purge by key | Edited in place by a CMS; needs a purge path |
| HTML | `public, s-maxage` of tens of seconds to a few minutes, `stale-while-revalidate`, `stale-if-error`; browser `max-age` short or zero | Freshness after a deploy is bounded by `s-maxage`, and users rarely wait on a revalidation |
| Authenticated or personalised HTML and API | `private, no-store` or `private, no-cache` | Never shared; see step 4 |
| Public API responses | Short `s-maxage` with validators, keyed on the parameters that matter | Offload for read-heavy endpoints without serving stale writes for long |
| Error responses | 404 cached briefly, 5xx not cached, `stale-if-error` on the success responses | A cached 5xx extends an outage past its fix |

`s-maxage` governs shared caches and overrides `max-age` there, which is what lets HTML be
cached at the edge for a minute while browsers revalidate. Where the CDN supports a
CDN-specific header (`CDN-Cache-Control`, or `Surrogate-Control` on Fastly), use it to set
edge lifetime without changing browser behaviour.

### 4. Keep authenticated responses safe

Check, on every rule that can cache HTML or API responses:

- the origin sends `private` or `no-store` on anything that depends on the session, and the
  CDN honours it rather than overriding it with a forced TTL;
- caching is decided by the origin's headers, not by the URL's extension, so a path such
  as `/account/settings.css` that the application routes to the account page is not cached
  as a stylesheet (Cloudflare's Cache Deception Armor and equivalent content-type checks
  exist for this);
- no request header the origin uses to build the response is forwarded without being in
  the key: a forwarded, unkeyed `X-Forwarded-Host` that the origin reflects into links
  lets one request decide what everyone else receives;
- where a personalised response is deliberately cached, the key includes the identity or
  the variant, and the exception is listed with an owner.

If a user has already seen another user's data, purge the affected paths, set the origin
to `no-store` on them, and treat it as a security incident with `incident-response`; the
tuning work waits.

### 5. Normalise the cache key

Key on what changes the response and nothing else:

- query string: allowlist the parameters the application reads where the set is known;
  otherwise strip known tracking parameters (`utm_*`, `gclid`, `fbclid` and the rest of
  the campaign set) and sort the remainder;
- cookies: none in the key by default; allowlist the one or two that select a variant
  (language, an experiment bucket) and only on the paths that use them;
- headers: most CDNs normalise `Accept-Encoding` themselves; add a device or language header
  only when the origin genuinely varies on it, and normalise it to a few values first;
- host: one canonical host per cache entry, with redirects for the rest.

Read `references/keys-and-purges.md` for how each major CDN expresses the key and what it
forwards without keying.

### 6. Shield the origin

Enable the CDN's shield or tiered tier (CloudFront Origin Shield, Fastly shielding,
Cloudflare Tiered Cache, Akamai tiered distribution) in the region nearest the origin, so
a miss in one edge location becomes a hit at the shield rather than another origin
request. Confirm request collapsing is on, so a popular object that expires produces one
origin fetch rather than one per waiting client. Re-measure offload afterwards: the shield
is usually the largest single gain for a geographically spread audience.

### 7. Purge by key, version the rest

- Fingerprinted assets are never purged; a deploy publishes new URLs.
- Content edited in place is tagged at the origin with surrogate keys or cache tags (the
  product, the article, the category), and the publish event purges those keys.
- Prefer a soft purge (mark stale, revalidate) where the CDN offers one, so a purge of a
  popular key does not become a burst of full origin fetches.
- CloudFront invalidates by path only, and invalidation paths beyond a monthly allowance
  are charged; lean on versioned URLs there and keep invalidations to the HTML paths that
  changed.
- Purge-all is for a poisoned or leaking cache, after checking the origin can take the
  uncached load or with traffic reduced first.

### 8. Roll out and verify

Change one content class at a time, on a staging distribution or a narrow path first.
Verify with the header audit from step 2 that the status header and `Age` behave as
intended, then let a full traffic cycle (a week for most sites) pass before comparing
offload with the baseline. Keep the CDN configuration in code with plan review, so a rule
change is diffable and revertible like any other change.

## What to hand back

```markdown
## Baseline and result
[Offload by requests and bytes per content class, before and after, with the window.]

## Origin headers
[Defects found per class, what was fixed at the origin, any edge overrides and why.]

## Policy
[The per-class table as deployed.]

## Cache key
[Query, cookie and header rules per path pattern.]

## Safety
[Authenticated paths and their headers, deliberate personalised caching with owners,
forwarded-but-unkeyed headers checked.]

## Purge
[Surrogate keys or tags, who purges what on which event, soft or hard, the purge-all rule.]
```

## Anti-patterns

**Caching by file extension.** It caches whatever the router decides to serve at that
path, including an account page reached through a crafted suffix. Let the origin's
`Cache-Control` decide.

**Reporting hit ratio as the result.** It moves with object mix and with how the vendor
counts uncacheable traffic. Origin requests and bytes are what the change was for.

**A wildcard purge on every deploy.** It throws away every asset that did not change and
sends a synchronised burst of misses to the origin at the moment it is also restarting.

**`Vary: Cookie` to be safe.** It looks cautious and quietly disables the cache, so the
team concludes the CDN does not help and stops measuring.

**Forwarding headers the key does not include.** Whatever the origin does with them
becomes visible to every user who receives that cache entry.

**A long browser `max-age` on unversioned files.** The CDN can be purged; the browsers
cannot, and they keep the old file until it expires.

## Reference files

- `references/header-audit.md` — read at steps 2, 3 and 8: the request loop for auditing
  headers through the CDN and at the origin, what each vendor's cache-status header
  reports, the defect checklist, and exact header values per content class.
- `references/keys-and-purges.md` — read at steps 5 to 7: how CloudFront, Cloudflare and
  Fastly build the cache key and what they forward unkeyed, tracking parameters to strip,
  surrogate-key and tag headers per vendor, the purge decision table, and measuring
  offload from logs.
