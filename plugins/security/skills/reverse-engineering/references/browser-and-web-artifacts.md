# Browser and web application artifacts

Read this when the target is a live web application, or a JavaScript bundle served by one,
rather than a file you were handed. Gate 1 still applies first: have the authorisation and
scope written down before the first request. A one-time read of a page you are allowed to
use is different from running an automated collector against someone's production service,
which is a terms-of-service question this file does not clear — see that scope, not just the
technical one, before anything below.

The commands below are verified against a small HTTP server built for this file (Python's
own `http.server`), serving an `index.html`, a minified `app.min.js` with a `checkLicense`
function compared against a fixed string, and its source map.

## Response headers are the cheapest signal, same role as a linked library

```bash
curl -sI https://example.test/
```

On the test server this printed `Server: SimpleHTTP/0.6 Python/3.11.15` among the usual
headers — on a real target this is where a framework, a CDN, a load balancer or a version
number shows up, the same role `readelf -d`'s `NEEDED` entries play for a native binary: a
fact about what the target is built on, read before anything else.

## A minified bundle is the shipped artifact; read it before running it

```bash
curl -s https://example.test/app.min.js
```

On the test server this returned the whole file as text: `function c(k){return
k==="DEMO-1234"}window.checkLicense=c;` followed by a `//# sourceMappingURL=` comment. A
minified bundle is a native binary's rough equivalent for a web app — the thing that actually
ships — and reading it this way is static analysis, the same step as `strings` or a
disassembler, with the same gate 5 rule: a comparison value visible in the source is a lead
to where the check lives, reported as "a comparison against a fixed value", not as the value
itself, unless you are in that gate's stated exception.

## A source map can recover close-to-original structure

```bash
curl -s https://example.test/app.min.js | grep -o 'sourceMappingURL=.*'
curl -s https://example.test/app.min.js.map
```

The comment at the end of a minified file names where its source map lives, if one was
shipped; fetching it is a second request to the same read-only path. On the test server this
returned the map's JSON, naming the original source file and the fixed compression format
`mappings` uses to connect minified positions back to it. A real build often does not deploy
a map to production on purpose — it can be the one thing standing between "minified" and
"as readable as the source", which is itself worth noting as a finding if a target you
expected to protect this way shipped one anyway. A missing map (a 404 on the path the comment
names) is a normal, confirming result, not an error to work around.

## What this does not cover

Reading a page's own rendered DOM and its JavaScript's live behaviour through a real
browser's developer tools (the network panel, breakpoints in the sources panel, the console)
is the dynamic half of this target type, the same role gate 3's breakpoint and trace play for
a native binary. That workflow was not exercised with real browser automation for this
skill; use your browser's own developer tools documentation for the current steps, and keep
gate 1's authorisation and the ToS caution above in force while you do.
