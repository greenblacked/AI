# Error signatures and origin checks

Contents: the strings each engine and bundler produces, how to match them, and the
checks that tell retention, ordering and rewrite problems apart.

## What a missing chunk looks like

| Source | What is reported | Notes |
| --- | --- | --- |
| webpack JavaScript chunk | `ChunkLoadError: Loading chunk 412 failed.` | The error's `name` is `ChunkLoadError`; match on that, not the message |
| webpack CSS chunk (mini-css-extract-plugin) | `Loading CSS chunk 412 failed.` | Often seen alongside the JavaScript one for the same route |
| Native `import()` in Chromium | `TypeError: Failed to fetch dynamically imported module: https://...` | Vite, Rollup and esbuild output use native `import()` |
| Native `import()` in Firefox | `TypeError: error loading dynamically imported module: https://...` | |
| Native `import()` in Safari | `TypeError: Importing a module script failed.` | No URL in the message; correlate by time and build id |
| Vite preload helper | `vite:preloadError` event on `window` | Fired before the import rejects, so it is the earliest hook |
| Module script served as HTML (Chromium) | `Failed to load module script: Expected a JavaScript module script but the server responded with a MIME type of "text/html"` | The single-page fallback answered for a missing file |
| Classic script served as HTML | `Uncaught SyntaxError: Unexpected token '<'` | Same cause, older output format |

Match native `import()` failures with a short list of these message fragments, and only
inside the catch on an `import()` call, so an unrelated `TypeError` elsewhere never
triggers a reload. Record which fragment matched; if one engine's share jumps after a
browser release, the wording changed and the list needs updating.

## Origin checks

Run each against a chunk URL taken from a real error report, not one you constructed.

```bash
# Still served, and with the right type and caching?
curl -sIL https://app.example.com/assets/Settings-3f9a1c.js | grep -iE '^(HTTP|content-type|cache-control|age)'

# Is the HTML itself cached at the edge? A large Age on the document is skew on its own.
curl -sIL https://app.example.com/ | grep -iE '^(HTTP|cache-control|age|etag)'

# Does a file that never existed return a real 404, or the app's HTML?
curl -sL -o /dev/null -w '%{http_code} %{content_type}\n' https://app.example.com/assets/does-not-exist.js
```

Each command follows redirects. The root of an app commonly redirects to a login or
locale path, and some hosts implement the single-page fallback as a redirect to
`/index.html`; without `-L` the document check prints the redirect's headers rather than
the document's, and the missing-file check prints `302` where the browser ends up with
`200 text/html`. With `-I`,
every hop's headers print; read the last block.

| Result | Cause | Fix |
| --- | --- | --- |
| Old chunk `404` | Deploy deleted it | Additive upload, prune by age |
| Old chunk `200 text/html` | Rewrite answers for assets, and the file is gone | Exclude the asset prefix from the rewrite, then fix retention |
| New chunk `404` for seconds after deploy | HTML published before assets | Upload assets first |
| New chunk `404` cached for minutes | CDN cached the early 404 | Upload order, and a short negative-cache time on the asset path |
| Intermittent `404` only during rollout | Assets served from pods of mixed versions | Shared asset storage behind the CDN |
| Document `Age` in the thousands | HTML cached at the edge | `Cache-Control: no-cache` on HTML |

## Pinning a session to its deployment

Some hosting platforms can route an old client's requests to the deployment that served
it, for a configurable period; Vercel calls this Skew Protection. It removes the need
for asset retention on that platform, but not the need for steps 3 to 6: a session older
than the pinning window still fails, and the API compatibility rules still apply to
anything the pinned deployment calls.
