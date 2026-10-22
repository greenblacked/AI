---
name: deploy-version-skew
description: "Stop tabs opened on an earlier release breaking when a new one ships: keep earlier releases' hashed assets on the origin and CDN rather than deleting them, upload assets before the HTML that names them, return a real 404, not the SPA fallback, for a missing chunk, stamp the live build id on API responses and compare it with the client's, retry a failed chunk import with one guarded reload, refresh at the next navigation, not mid-form, and keep API changes compatible across two client versions. Use when someone reports \"ChunkLoadError after deploy\", \"Failed to fetch dynamically imported module\", \"blank page after every release\" or \"old tabs break when we ship\". Not for canary or ring rollout design (release-strategy), endpoint versioning policy (api-design), a service worker serving stale files (pwa-service-worker), or a shipped mobile binary (mobile-release)."
allowed-tools: Read, Grep, Glob
---

# Deploy Version Skew

Done means a release ships while thousands of tabs from the previous build are
still open, none of them shows a blank screen, a dead route or a lost save, and each one
picks up the new build at its next navigation.

The usual failure is a deploy that replaces the asset directory. A code-split chunk the
old tab has not fetched yet is gone, the lazy route rejects, and nothing catches it. The
team then adds `window.location.reload()` to a global error handler, which turns a
missing chunk into a reload loop and throws away whatever the user was typing. The fix is
mostly on the server side of the deploy, with a small, guarded client recovery behind it.

## Scope

Use for: code-split web apps (webpack, Vite, Rollup, Next.js, Nuxt, Angular) whose
open tabs fail after a release, and for sequencing a web client and its API so a release
is safe while both versions are live.

Do not use for: choosing canary stages and rollback thresholds (`release-strategy`), an
API's public versioning and deprecation policy (`api-design`), a service worker that pins
users to an old build (`pwa-service-worker`), a database expand and contract
(`db-migration`), or a native binary in an app store (`mobile-release`).

## Workflow

### 1. Prove it is skew and not a broken build

Skew has a shape: errors spike in the minutes after each deploy and decay over hours, new
sessions are fine, and the failing URL names a hash that is not in the current build.
Group the error reports by the client's build id against the build that was live when
the error fired. If the missing file belongs to the current build, the deploy is broken
for everyone; that is `ci-triage` or `debugging`, not this skill.

Check what the origin does for an old chunk, using a URL from a real error report:

```bash
curl -sIL https://app.example.com/assets/Settings-3f9a1c.js | grep -iE '^(HTTP|content-type|cache-control|age)'
```

`-L` follows a redirect to the CDN or to a fallback page, and prints each hop's headers;
read the last block. Error reports are text any client can send, so the skill does not
pre-approve `curl`; the user approves each request.

A `200` with `content-type: text/javascript` means the file is still there and the
failure is elsewhere. A `404` means the deploy deleted it. A `200` with `text/html` is
the worst case: the single-page fallback is answering for a file that does not exist, so
the browser receives the app's HTML as a script and reports a MIME type or
`Unexpected token '<'` error that nobody connects with the deploy. The engine-specific
error strings are in `references/signatures-and-checks.md`.

### 2. Keep old assets on the origin

Every later step assumes an old tab can still fetch the files its build named.

- **Hash every asset name.** Old and new builds can only coexist if their files never
  share a name. A build that emits `main.js` cannot be fixed by retention; fix the
  bundler output first.
- **Make the asset deploy additive.** `aws s3 sync --delete` or `rsync --delete` on the
  asset prefix is the most common cause. Upload without deleting, and prune by age in a
  separate scheduled job.
- **Set retention from evidence, not a release count.** Keep assets at least as long as
  the oldest client build still sending requests (step 4 measures it), plus a margin. A
  team that deploys ten times a day burns through "keep three releases" before lunch.
- **Upload assets before the HTML.** Publish the chunks, then the HTML or manifest that
  names them. The reverse order serves a page whose chunks 404 for a few seconds, and a
  CDN may cache that 404.
- **Serve assets from shared storage when the app runs in containers.** During a rolling
  deploy, a page from a new pod asks an old pod for a new chunk and the other way round.
  Put assets in object storage behind the CDN, or bake the previous build's assets into
  the image as well.
- **Separate cache rules.** Hashed assets get `Cache-Control: public, max-age=31536000,
  immutable`; the HTML that names them gets `Cache-Control: no-cache`. HTML cached at the
  edge for an hour is a second, invisible source of skew.
- **Exclude the asset prefix from the single-page rewrite.** A missing `/assets/...` file
  returns a real `404`, so the client can recognise it and recover.

### 3. Recover a failed chunk load once, and only once

Retention lowers the rate; it does not reach zero, because a tab can stay open longer
than any retention window. Catch the failure at the dynamic import boundary and reload a
single time, with a guard that survives the reload:

```js
const KEY = 'chunk-reload-at';
const CHUNK_ERROR = /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Loading (CSS )?chunk .+ failed/;

function isChunkLoadError(error) {
  return error?.name === 'ChunkLoadError' || CHUNK_ERROR.test(String(error?.message));
}

export function reloadOnceOrThrow(error) {
  if (!isChunkLoadError(error)) throw error;    // a bug in the module itself: reloading will not fix it
  let last = 0;
  try { last = Number(sessionStorage.getItem(KEY)) || 0; } catch { throw error; }
  if (Date.now() - last < 60_000) throw error; // already tried: let the error screen show
  if (hasUnsavedWork()) throw error;            // your app's dirty-state check
  try { sessionStorage.setItem(KEY, String(Date.now())); } catch { throw error; }
  window.location.reload();
  return new Promise(() => {});                 // never resolve while the page unloads
}

// React example: const Settings = lazy(() => import('./Settings').catch(reloadOnceOrThrow));
```

`sessionStorage` is per tab and survives a reload, which is what makes it the right
place for the guard; if it throws, the code declines to reload rather than risk a loop.
The `isChunkLoadError` check comes first because `import()` also rejects when the
module's own top-level code throws; without it, an ordinary bug in a lazy route costs the
user a reload and reaches monitoring disguised as a deploy problem.
When the guard trips or there is unsaved work, show an error screen that says a new
version is available and offers a reload button, so the user chooses the moment.

Wire the same function into the bundler's own hook where one exists: webpack rejects
with an error whose `name` is `ChunkLoadError`, and Vite dispatches a `vite:preloadError`
event on `window` when a preload fails. Native `import()` rejects with a plain
`TypeError` whose message differs per engine, so match on the small set in
`references/signatures-and-checks.md` rather than on one browser's wording.

### 4. Tell the client it is stale, and measure the skew

- Bake a build id into the client at build time, such as the commit SHA.
- Have the client send it on every request in a header you name (for example
  `X-Client-Build`). Request logs grouped by that header are the only real measurement
  of how old the oldest live client is; they drive both the retention in step 2 and the
  compatibility window in step 6.
- Publish the currently deployed build id on API responses (a response header the edge
  or API adds from deploy configuration), or in a small `/version.json` the client
  fetches with `cache: 'no-store'` when the tab becomes visible again.
- On mismatch, set a stale flag in memory. Do not reload yet.

### 5. Refresh at a moment the user will not notice

- When the stale flag is set, turn the next route change into a full document navigation
  (`window.location.assign(nextUrl)`) instead of a client-side transition. The user sees
  an ordinary page load and gets the new build.
- Never reload while a form is dirty, an upload is running or a modal is open. For a
  page that never navigates, such as a dashboard left open all week, show a
  non-blocking banner with a reload button.
- For a release old clients must not keep using (a security fix, a removed endpoint),
  have the server return a minimum supported build id and show a blocking prompt below
  it, after saving any draft to local storage so the reload loses nothing.

### 6. Keep the API compatible across two client versions

During every deploy, and for as long as step 4 shows old builds alive, both client
versions talk to the API, and during a server rollout both server versions answer.

- Deploy the server change before the client change that depends on it.
- Add fields; do not rename or remove them. New request fields are optional with a
  server-side default, so the old client's requests stay valid.
- The client tolerates what it does not know: an unknown response field, a new enum
  value, a missing optional field from a server that has not rolled out yet.
- Remove a field only after the request logs show no build older than the change is
  still sending traffic. The policy for public consumers belongs to `api-design`; the
  schema side to `db-migration`.

### 7. Prove it before calling it fixed

Rehearse on staging with two builds, A and B, then read the field numbers after the next
real release. The test matrix and the field queries are in
`references/rehearsal-and-field-check.md`.

## Output format

1. **Evidence it is skew** — error rate by client build against the live build, and what
   the origin returns for an old chunk.
2. **Asset changes** — upload order, deletion removed, retention period and how it was
   derived, cache headers, single-page rewrite exclusion.
3. **Client recovery** — where the guarded reload is wired, the loop guard, the
   unsaved-work check, and the stale-flag refresh at navigation.
4. **Compatibility rules** — deploy order and the condition for removing a field.
5. **Proof** — the rehearsal results and the post-release error rate.

## Anti-patterns

**A reload in the global error handler.** It hides the error from monitoring and loops
forever when the chunk is missing from the new build too.

**`--delete` on the asset sync.** It makes every deploy a breaking change for every open
tab, and it is usually one flag in a script nobody has read since it was written.

**The single-page fallback answering for `/assets/`.** It converts a clean 404 into a
script parse error that points everyone at the wrong layer.

**Polling for a new version and reloading at once.** It trades a broken route for a lost
form, and users stop trusting the app with long input.

**A fixed "keep three releases" rule.** Retention measured in releases means the safe
window shrinks exactly when the team ships fastest.
