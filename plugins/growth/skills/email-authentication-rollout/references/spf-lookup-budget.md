# SPF lookup budget

Read this at step 5 when the record is near or over the limit, or before flattening anything.

## Contents

- What counts
- Counting method
- Reducing the count
- Flattening checklist

## What counts

Terms that cause a DNS query count toward the limit of ten: `include`, `a`, `mx`, `ptr`, `exists` and the `redirect` modifier. Counts accumulate through nested includes. `ip4`, `ip6` and `all` do not count. An `mx` term counts as one toward the ten; the address lookups for its MX hosts fall under a separate limit of ten per `mx` term and do not count toward the ten (RFC 7208 section 4.6.4). More than two void lookups (queries returning no data) also produce a permerror. Avoid `ptr`: it is discouraged and slow.

## Counting method

```bash
dig +short TXT example.com | grep 'v=spf1'
dig +short TXT _spf.vendor.example   # repeat for each include, recursively
```

Write the tree down with a count at each node and total it. A checker tool is fine for a second opinion, but the written tree is what you keep with the change.

## Reducing the count

1. Delete includes for platforms that no longer send; the reports show which still do.
2. Move each stream to its own subdomain with its own short record, so the root record carries only what the root sends.
3. Replace `a` and `mx` with the ip4 ranges they resolve to when those are yours and stable.
4. Prefer DKIM alignment for third-party platforms and drop their SPF include entirely when their return-path is on their own domain.

## Flattening checklist

- The provider publishes fixed ranges, or a stable include you can resolve.
- Something regenerates the record on a schedule and alerts on a change in the source.
- The flattened record stays under the 255-character string limit per string (split into several strings) and the DNS response stays small enough to avoid truncation.
- You can roll back to the include form in one change.
