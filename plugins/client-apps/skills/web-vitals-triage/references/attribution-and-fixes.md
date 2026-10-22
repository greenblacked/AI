# Attribution to fix

Read this in step 3, once the dominant sub-part or phase is named. Each section lists what
moves that part, what looks relevant and does not, and how to see the move in a trace.

Confirm each change with a DevTools Performance recording of the failing page on a
throttled CPU (4x or 6x slowdown) and network. The Performance panel's live metrics view
shows LCP, INP and CLS as you load and interact, and a recorded trace's insights break LCP
into its sub-parts and a slow interaction into its phases. That is the lab check that the
part you aimed at moved.

## LCP

| Dominant part | Moves it | Does not move it |
| --- | --- | --- |
| TTFB | Cache the HTML at the CDN edge; remove redirect hops (`http` to `https`, apex to `www`, trailing slash); stream the head of the document before slow data is ready; make the handler faster (`profiling`) | Image compression, preloads, anything in the front-end bundle |
| Resource load delay | The LCP image as an `img` in the server HTML rather than a CSS background or a node rendered by JavaScript; no `loading="lazy"` on it; `fetchpriority="high"`; a `link rel="preload"` only when the resource cannot be in the HTML (a background image, a font for a text LCP) | Making the image smaller; it is not loading yet |
| Resource load duration | The right intrinsic size via `srcset` and `sizes`; AVIF or WebP; serving from the same origin or a preconnected one; fewer competing high-priority requests in the first second | Preloading it harder; it is already loading |
| Element render delay | Removing render-blocking CSS and synchronous scripts from the head; removing anti-flicker snippets that hide the page until an experiment loads; server-rendering the LCP element instead of waiting for hydration; `font-display` and a preloaded font for a text LCP | Faster image delivery; the image is already there |

Check the LCP element itself before fixing anything. A cookie banner, a chat widget's
greeting, or a placeholder skeleton can be the LCP element, and the fix is then to make
that element smaller than the content or to stop it rendering first.

## INP

| Dominant phase | Moves it | Does not move it |
| --- | --- | --- |
| Input delay | Breaking long tasks with a yield to the main thread (`scheduler.yield()` where supported, a `setTimeout` continuation otherwise); deferring third-party scripts until after load or interaction; hydrating less, or later, for content below the fold | Making the handler faster; it has not started yet |
| Processing duration | Doing the visible update first and deferring analytics, persistence and non-visible state until after the next paint; avoiding reading layout after writing it in a loop; in React, marking non-urgent updates as a transition | Code splitting; the handler's code is already loaded |
| Presentation delay | Fewer DOM nodes touched per update; `content-visibility: auto` for long off-screen sections; avoiding style changes on a high-level element that invalidate the whole tree; virtualising long lists | Optimising the handler's JavaScript |

Read the Long Animation Frame entries for the slow interaction: they list each script that
ran in the frame, its source URL and how long it took. A third-party script in that list
is a finding to take to whoever added the tag, not a micro-optimisation to attempt in your
own code.

`loadState` matters. An interaction that is slow only while the page is still loading is
an input-delay problem caused by load work, and the fix is to load less before the page is
interactive, not to speed up the handler.

## CLS

| Cause of the largest shift | Fix |
| --- | --- |
| Image or video without dimensions | `width` and `height` attributes, or CSS `aspect-ratio` |
| Ad, embed or iframe that arrives late | A container with a reserved minimum height for the most common size |
| Consent banner or promotion pushing content down | Overlay it rather than inserting it in flow, or render it on the server so it is present from the first paint |
| Web font swap changing line lengths | A fallback font with matched metrics (`size-adjust`, `ascent-override`), or `font-display: optional` |
| Content inserted above what the user is reading after load | Insert below, or only in response to a user action; shifts within 500 ms of a user input are excluded from CLS |
| Animation of `top`, `left`, `height` or `width` | Animate `transform` instead; it does not move layout |

The shifting node in attribution is the one that moved, which is often not the one that
caused it. Look at what was inserted or resized directly above it at that timestamp.

## When the dominant part will not move

- TTFB dominated by a slow handler: that work belongs to `profiling`. Come back with the
  target number the handler must reach for LCP to pass.
- Input delay dominated by a third-party tag nobody will remove: write down the cost in
  milliseconds at p75 and hand it to whoever owns the tag. That is a finished result.
- A fix that moves the sub-part in the lab but not in the field after two weeks of your own
  monitoring: the lab page is not the field page. Recheck the LCP element and the
  interaction target from field attribution before trying another change.
