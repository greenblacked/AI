# Report noise and third-party scripts

Contents: what to drop before triage, what an unexplained report may mean, and how
common third-party integrations fit a nonce policy.

## Drop before triage

| Pattern | Why it is noise |
| --- | --- |
| `source-file` or blocked URL that is, or starts with, `chrome-extension`, `moz-extension`, `safari-web-extension` or `safari-extension` | A browser extension injecting into the page; not your code and not fixable by you |
| A blocked URL on a domain nobody in the team recognises, from a handful of clients | Usually adware or an injecting proxy on the user's machine; worth a count, not a fix |
| Reports from the same client in bursts of hundreds | A broken extension or a scanner; rate-limit per client |
| `about:blank` or `blob:` sources tied to one browser version | Often an engine quirk; check whether that version's share is meaningful before acting |

A filter for the extension case, in each format:

```bash
jq -c 'select([."csp-report"."source-file", ."csp-report"."blocked-uri"] | map(. // "") | any(test("^(chrome-extension|moz-extension|safari-web-extension|safari-extension)(:|$)")) | not)' csp-legacy.ndjson > csp-legacy.filtered.ndjson
jq -c 'map(select([.body.sourceFile, .body.blockedURL] | map(. // "") | any(test("^(chrome-extension|moz-extension|safari-web-extension|safari-extension)(:|$)")) | not))' csp-reporting.ndjson > csp-reporting.filtered.ndjson
```

The pattern accepts the bare scheme as well as a full URL. Browsers report a URL whose
scheme is not HTTP(S) as its scheme alone, so a report from an extension usually reads
`"blocked-uri": "chrome-extension"` with no colon, and a pattern that requires
`chrome-extension:` keeps exactly the reports it was written to drop.

Keep the count of what was dropped. A sudden rise in "unknown domain" reports on one
page can be an injection that the policy is now blocking, which is the policy doing its
job; route that to `security-review` rather than allow-listing the domain.

## Third-party integrations

| Integration | How it fits |
| --- | --- |
| Tag manager loader | Put the nonce on the loader script; `'strict-dynamic'` trusts what it adds with `createElement`. Inline custom HTML it injects needs the vendor's nonce support configured; check the vendor's CSP documentation |
| Analytics and pixels | Script loads are covered by the loader's trust. Beacons use `img-src` and `connect-src`, which the starting policy leaves open |
| Chat, support and survey widgets | Usually a loader script plus an iframe; nonce the loader, and add `frame-src` only when the stricter policy restricts frames |
| Payment and identity iframes | Leave them to their own origin's policy; if `frame-src` is restricted later, list the provider's documented origins |
| A/B testing that rewrites the page | Often relies on inline script or `eval`; measure it in report-only and decide with its owner whether it stays |
| Embeds that use `document.write` | Not trusted under `'strict-dynamic'`; replace the embed or load it in an iframe |

For each integration, the owner signs off on the report-only result before its page
group is enforced. A vendor whose script only works with `'unsafe-inline'` or
`'unsafe-eval'` is a decision for the owner, recorded with a reason and a review date,
not a default added for everyone.
