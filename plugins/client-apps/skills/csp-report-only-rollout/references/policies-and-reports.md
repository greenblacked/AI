# Policies, hashes and report queries

Contents: the policy at each phase, computing a hash, the two report formats, and the
grouping queries for two weeks of reports.

## Policy by phase

| Phase | Header | Policy |
| --- | --- | --- |
| Measure | `Content-Security-Policy-Report-Only` | `script-src 'nonce-R' 'strict-dynamic' 'report-sample' https: 'unsafe-inline'; object-src 'none'; base-uri 'none'; report-uri /csp-reports; report-to csp` |
| Enforce a page group | `Content-Security-Policy` | The same text, for that group's paths only |
| Next step, alongside | `Content-Security-Policy-Report-Only` | The enforced text plus the candidate additions, such as `frame-ancestors 'self'; form-action 'self'` or `require-trusted-types-for 'script'` |

`R` is the per-response nonce. For a page served from a shared cache, replace the nonce
with one `'sha256-...'` source per inline script.

The starting policy restricts scripts, plugins and the base URL only. That is
deliberate: those three carry most of the protection against injected script, and
leaving `img-src`, `connect-src` and `style-src` open keeps the first rollout from
breaking analytics beacons and styling. Add those later through the report-only policy.

Directive fallbacks matter when reading reports: `script-src-elem` and `script-src-attr`
fall back to `script-src`, which falls back to `default-src`. `frame-ancestors`,
`form-action` and `base-uri` do not fall back to `default-src`, so a policy that sets
only `default-src` leaves them open.

## Computing a hash

Hash the exact text between the script tags, whitespace included:

```bash
printf '%s' 'window.dataLayer = window.dataLayer || [];' | openssl dgst -sha256 -binary | openssl base64 -A
```

Put the result in the policy as `'sha256-<value>'`. Chromium's console message for a
blocked inline script also prints the hash it expected, which is a quick cross-check.
Any change to the script, including reformatting by a minifier, changes the hash, so
compute hashes in the build, not by hand.

## Report formats

`report-uri` posts one object per violation, with content type `application/csp-report`:

```json
{"csp-report": {"document-uri": "https://www.example.com/pricing", "effective-directive": "script-src-elem", "violated-directive": "script-src-elem", "blocked-uri": "inline", "disposition": "report", "source-file": "https://www.example.com/pricing", "line-number": 42, "script-sample": "window.dataLayer = window.dataLayer || [];", "original-policy": "..."}}
```

The Reporting API (`report-to`) posts an array, with content type
`application/reports+json`:

```json
[{"type": "csp-violation", "url": "https://www.example.com/pricing", "body": {"documentURL": "https://www.example.com/pricing", "effectiveDirective": "script-src-elem", "blockedURL": "inline", "disposition": "report", "sourceFile": "https://www.example.com/pricing", "lineNumber": 42, "columnNumber": 7, "sample": "window.dataLayer = window.dataLayer || [];", "originalPolicy": "..."}}]
```

`blocked-uri` and `blockedURL` read `inline` for an inline script or handler, `eval` for
`eval` and its relatives, and a URL for a blocked file.

## Grouping queries

Store each received body as one line in a file per format, then:

```bash
# report-uri format: directive, blocked source, page, by count
jq -r '."csp-report" | [(."effective-directive" // ."violated-directive"), ((."blocked-uri" // "") | split("?")[0]), ((."document-uri" // "") | split("?")[0])] | @tsv' csp-legacy.ndjson \
  | sort | uniq -c | sort -rn | head -50

# Reporting API format
jq -r '.[] | select(.type == "csp-violation") | .body | [.effectiveDirective, ((.blockedURL // "") | split("?")[0]), ((.documentURL // "") | split("?")[0])] | @tsv' csp-reporting.ndjson \
  | sort | uniq -c | sort -rn | head -50
```

Replace the page column with your page group (by path prefix) once the groups from step
1 exist; per-URL counts hide that one template causes a thousand reports. For `inline`
groups, add the sample to the key to tell the scripts apart.
