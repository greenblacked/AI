# The five sources, with fixes

Read this in step 3 to recognise the source and in step 4 for the fix. Examples are React;
the same shape applies to any framework that hydrates.

## Contents

- 1\. Values that differ by when or where render runs
- 2\. Branches on the environment
- 3\. Invalid nesting the parser repairs
- 4\. Extension-injected nodes and attributes
- 5\. Per-request data missing on the client
- The theme flash
- Framework escape hatches

## 1. Values that differ by when or where render runs

```jsx
// Broken: server renders in UTC and its own locale, the browser in the user's.
<span>{new Date(order.createdAt).toLocaleString()}</span>
```

```jsx
// Fixed: both sides format with the same explicit locale and time zone,
// chosen once on the server and passed down as props.
const fmt = new Intl.DateTimeFormat(props.locale, {
  timeZone: props.timeZone,
  dateStyle: 'medium',
  timeStyle: 'short',
});
<span>{fmt.format(new Date(order.createdAt))}</span>
```

The same locale and time zone can still format differently when Node and the browser
ship different ICU data: ICU 72 began putting a narrow no-break space (U+202F) before
`AM` and `PM` in English, while runtimes on other ICU versions, or with that change
patched out, put a plain space, so `3:00 PM` differs by one invisible character. Where the runtimes may differ, format the string once on the server
and pass the string itself for the first render.

If the server cannot know the user's time zone, render a UTC or relative value on both
sides and replace it after mount. For "3 minutes ago" labels, pass the server's `now` in
the payload and compute from it on the first client render; refresh on a timer afterwards.

Random IDs for accessibility attributes: use the framework's stable ID hook (`useId` in
React) rather than a random value, and call it in the same component order on both sides.

## 2. Branches on the environment

```jsx
// Broken: server takes the false branch, the client's first render the true one.
const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
return isMobile ? <MobileNav /> : <DesktopNav />;
```

Fixes, in order of preference:

1. Do it in CSS. Render both navigations and show one with a media query. No JavaScript
   decision, no mismatch, no flash.
2. Decide on the server from something the server knows (a client hint or a stored
   preference cookie) and pass it as a prop.
3. Render the server's choice on both sides first, then switch after mount:

```jsx
const isMobile = useSyncExternalStore(
  subscribeToResize,
  () => window.innerWidth < 768,
  () => false,                 // server snapshot, also used for the hydrating render
);
```

Option 3 still changes the layout after load. It is correct, but the shift counts against
CLS, which is why options 1 and 2 come first.

## 3. Invalid nesting the parser repairs

The HTML parser does not reject invalid markup; it rewrites it. The framework then finds
a different tree from the one it rendered.

| Markup | What the parser produces |
| --- | --- |
| `p` containing `div`, `ul`, `table` or another `p` | The `p` is closed before the block element; the block becomes a sibling and an empty `p` may appear after it |
| `a` containing `a` | The outer link is closed before the inner one |
| `table` containing `tr` directly | A `tbody` is inserted |
| Text directly inside `table` or `tr` | The text is moved before the table |
| `button` containing `button`, `form` containing `form` | The first is closed, or the inner `form` is dropped |

The development build usually warns about the nesting separately from the hydration
error; read the earlier warning first. Rich-text content from a CMS rendered inside a `p`
is a frequent source, because the content itself contains block elements. Render it in a
`div`.

## 4. Extension-injected nodes and attributes

Confirm by reproducing in a clean profile. Then:

- Attributes added to `html` or `body` by a known extension: accept the warning in
  development, or put `suppressHydrationWarning` on that one element if the noise hides
  real errors. It affects only that element's own attributes and text.
- Elements inserted into the body before hydration: React 19 skips unexpected elements in
  `head` and `body`; on React 18, mount the app into a dedicated container element rather
  than `body` so injected siblings fall outside the hydrated tree.
- Translation extensions that rewrite text nodes break hydration and later updates. There
  is no complete fix; `translate="no"` on elements whose text must not be rewritten limits
  the damage.

## 5. Per-request data missing on the client

```jsx
// Broken: the server reads the experiment bucket from a cookie,
// the client reads it from a store that starts empty.
const variant = useExperiment('pricing');   // server: 'b', client first render: 'control'
```

The fix is to serialise every input the server rendered with into the page payload and
initialise the client from it before hydrating: the experiment bucket, feature flags, the
user object, the locale, the currency. Grep the server render path for cookie, header and
user-agent reads, and check each one has a matching entry in the serialised state.

A useful check: the server should be able to render the page from the serialised payload
alone. Any input it reads that is not in the payload is a candidate.

## The theme flash

A dark-mode preference held in `localStorage` cannot be known by the server, so the server
renders light, the client switches to dark, and the user sees a flash. Two correct fixes:

- Store the preference in a cookie as well, so the server renders the right theme.
- Add a small inline script at the top of `head` that reads the preference and sets an
  attribute on `html` before first paint, and put `suppressHydrationWarning` on `html`
  because that one attribute differs by design.

## Framework escape hatches

Each exists for the deliberate, explained case only.

- **React:** `suppressHydrationWarning` on one element; `useSyncExternalStore` with a
  server snapshot; a client-only component loaded without server rendering for content that
  cannot render on a server at all.
- **Vue 3.5 and later:** the `data-allow-mismatch` attribute on one element, optionally
  limited to `text`, `children`, `class`, `style` or `attribute`. Production mismatch
  details can be enabled with the `__VUE_PROD_HYDRATION_MISMATCH_DETAILS__` build flag
  while investigating.
- **Angular:** the `ngSkipHydration` attribute on a component's host element skips
  hydration for that component, which then renders on the client from scratch.
