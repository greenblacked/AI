---
name: hydration-mismatch-hunt
description: "Find why server-rendered HTML and the first client render disagree, and fix the cause rather than the warning: diff the raw server HTML from curl against the parsed DOM and the first client render, never the final DOM, then check the five usual sources (time, randomness or locale read during render; typeof window branches; invalid nesting the HTML parser repairs; nodes injected by browser extensions; per-request data the client never receives) and move the value into serialised props or an effect. Use when someone says \"Hydration failed because the initial UI does not match\", \"text content did not match\", \"the page flashes then changes\", \"Minified React error 418\" or \"hydration errors only in production\". Not for a client bug with no server render (debugging), pages search engines miss (web-app-seo), or stale responses overwriting newer ones (async-ui-races)."
allowed-tools: "Read, Grep, Glob"
---

# Hydration Mismatch Hunt

Done means you can show the exact node or attribute where the server HTML and the first client render differ, name which input produced the difference, move that input so both sides render the same thing, and show the warning gone in a development build with the same request headers that produced it.

Hydration attaches client code to HTML the server already rendered, and it assumes the client's first render produces the same tree. When it does not, React 18 throws away the server HTML for the nearest Suspense boundary or the whole root and renders it again on the client — the visible flash, the lost LCP, and in production a minified error number nobody reads. The usual mistake is looking at the final DOM in the Elements panel: by then the client has already re-rendered, and what you see is the client's version, which looks correct. The second mistake is reaching for `suppressHydrationWarning`, which silences one level of text or attributes and leaves the mismatch, the re-render and the cost in place.

## Scope

Use for: hydration errors and warnings in React, Next.js, Remix, Vue, Nuxt, Svelte, Angular or any framework that hydrates server HTML; minified hydration errors in production; content that flashes and changes right after load; errors that appear only in one locale, timezone, browser or for logged-in users.

Do not use for: a client-side bug in an app with no server render, or a mismatch already traced to a logic error unrelated to rendering (`debugging`); search engines not seeing content (`web-app-seo`); an older response overwriting a newer one after interaction (`async-ui-races`).

## Workflow

### 1. Capture the error as the framework reports it

Production builds hide the detail. React 18 reports minified errors 418 and 425 for a mismatch and 423 when it falls back to rendering the whole root on the client. Reproduce against a development build on the same route and with the same request inputs; if it reproduces only in a production build, run that build locally with the production environment's time zone and locale.

Record:

- the full message and the component stack — React 18 development builds name the expected and found element or text, React 19 prints a diff of server and client, and Vue names the mismatched node;
- the request inputs that reproduce it: URL, cookies, `Accept-Language`, logged-in or not, the experiment bucket;
- whether it reproduces in a clean browser profile with extensions disabled.

If it disappears with extensions disabled, skip to source 4 in step 3.

### 2. Diff three versions, not two

Collect three representations of the same page and compare them in order. Each difference between adjacent pairs points to a different class of cause.

1. **Raw server HTML**, fetched with the same inputs the browser sent:

   ```bash
   curl -sS -L 'http://localhost:3000/pricing' \
     -H 'Accept-Language: de-DE,de;q=0.9' \
     -H 'Cookie: session=...; exp_bucket=b' \
     -o server.html -w '%{http_code} %{url_effective}\n'
   ```

   `-L` matters here: a locale-aware router commonly answers `Accept-Language: de` with a
   redirect to `/de/pricing`, and without it `server.html` holds the redirect body instead
   of the page. Check the printed status is `200` and the final URL is the one the browser
   ended on. The skill does not pre-approve `curl`, since the HTML it fetches can carry
   CMS and user-written text; the user approves each fetch.

2. **Parsed DOM before any script runs.** Paste the HTML through the browser's parser in any page's console — `new DOMParser().parseFromString(html, 'text/html').documentElement.outerHTML` — or load the page with JavaScript disabled in DevTools and inspect it. This is what the client actually hydrates against. Compare it with version 1 as an element tree, not as text: re-serialising always changes quoting, entity escaping, `<br />` to `<br>` and whitespace without any repair, so a text diff flags valid HTML. `DOMParser` also parses with scripting off, so `noscript` contents appear as elements there and not in the page being hydrated; ignore differences inside `noscript`.

3. **First client render.** The development build's warning or diff, or a breakpoint in the framework's recoverable-error hook, gives the client's version of the mismatched subtree. With React 19, `hydrateRoot` accepts an `onRecoverableError` option whose second argument carries the component stack.

Read the differences:

| Differs between | Means |
| --- | --- |
| 1 and 2 | The HTML is invalid and the parser repaired it (source 3) |
| 2 with extensions on and 2 with extensions off | An extension changed the DOM before hydration (source 4) |
| 2 and 3 | The server and client rendered different trees from different inputs (sources 1, 2 and 5) |

Gate: name the first differing node and its component before editing anything. If the stack is missing, bisect: replace half of the suspect subtree with a static placeholder and see whether the error stays.

### 3. Match it to one of the five sources

`references/sources-and-fixes.md` has a worked fix for each. In the order to check:

1. **Values that differ by when or where render runs.** `Date.now()`, `new Date()`, `Math.random()`, `crypto.randomUUID()`, `toLocaleString()` and `Intl` formatting without an explicit locale and time zone. The server is usually UTC and one locale; the browser is neither. Errors that appear "only in production" are most often this, because the development server runs in the developer's own time zone.
2. **Branches on the environment.** `typeof window !== 'undefined'`, `localStorage`, `matchMedia`, `navigator.userAgent` or a screen width read during render. The server takes one branch and the client takes the other on its first render.
3. **Invalid nesting.** A `div` inside a `p`, a `p` inside a `p`, an `a` inside an `a`, a `tr` directly in a `table` without `tbody`, a `button` inside a `button`, a `form` inside a `form`. The parser rewrites the DOM, and the framework finds nodes where it expected others.
4. **Extension-injected nodes and attributes.** Password managers, grammar checkers, translators and ad blockers add attributes to `html` or `body` or insert elements. React 19 tolerates unexpected elements in `head` and `body` better than React 18; attribute changes on the root still warn.
5. **Per-request data missing on the client.** The server read a cookie, header, user-agent, geolocation, feature flag or experiment bucket and rendered with it, but did not serialise it into the payload the client renders from, so the client renders the default.

### 4. Fix by moving the value, not by hiding the warning

The rule for every source: the server and the client must render the first pass from the same inputs.

- A value that must be the same on both sides — a timestamp, a seed, the locale, the time zone, the user's flags — is decided once on the server and passed to the client as serialised props or loader data.
- A value only the client can know — window size, local storage, the user's real time zone when the server cannot know it — is rendered as a stable placeholder on both sides and filled in after mount, in an effect or through `useSyncExternalStore` with a `getServerSnapshot` that returns the placeholder.
- Invalid nesting is fixed in the markup.
- Extension noise is confirmed as such and left alone, or narrowed to the one attribute concerned.

`suppressHydrationWarning` is acceptable in exactly one shape: one element whose text or attribute is known to differ, deliberately, such as a theme attribute set on `html` by an inline script before paint, or a rendered timestamp. It is never the fix for a mismatch you have not explained.

### 5. Prove it

Rerun with the same request inputs that reproduced the error, plus one other locale and time zone, logged in and logged out. Check the development console is clean and, in production, that the minified error count in your error tracker drops after release. Add the reproducing inputs to a test that renders the route on the server and hydrates it in a browser test, so the next timestamp in render is caught before release.

## Anti-patterns

**Inspecting the final DOM.** The client has already re-rendered. It shows you the client's version and hides the server's.

**Disabling server rendering for the component.** A dynamic import with server rendering turned off removes the error by removing the content from the HTML, which costs LCP and indexing. It is right only for components that are genuinely client-only, such as a map or a chart.

**Formatting dates in render without a fixed locale and time zone.** Node and the browser each pick their own defaults.

**Flash fixes with `opacity: 0` until hydration.** Hides the flash, delays every paint, and leaves the mismatch.

**Blaming extensions without testing.** Disable them and reproduce before accepting that explanation; it is the most comfortable diagnosis and frequently wrong.

## Output format

```markdown
## Error
[Framework message or minified code, route, request inputs that reproduce it.]

## First difference
[The node or attribute, server value versus client value, the component, and which pair of the three versions differed.]

## Source
[Which of the five, and the line that reads the differing input.]

## Fix
[Where the value now comes from on each side; any suppressHydrationWarning left and why.]

## Proof
[Inputs retested, console clean, error-tracker count before and after, test added.]
```

## Reference files

- `references/sources-and-fixes.md` — read in step 3 and step 4: each of the five sources with a broken and a fixed example, the theme-flash pattern, framework-specific escape hatches in Vue and Angular, and the parser repairs that most often cause mismatches.
