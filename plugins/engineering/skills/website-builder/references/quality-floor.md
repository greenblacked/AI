# Quality floor

The bar every build clears before handover, and the baseline an audit measures an
existing site against. Each item is written so it can be checked and reported one by
one. Retrofitting any of it costs several times what building it in costs, which is why
none of it is optional at any tier.

## Contents

- [Design direction](#design-direction)
- [Responsive behaviour](#responsive-behaviour)
- [Accessibility](#accessibility)
- [Performance](#performance)
- [Security headers](#security-headers)
- [SEO and metadata](#seo-and-metadata)
- [The checklist](#the-checklist)

## Design direction

This section carries the aesthetic thinking for step A3. Read it before producing
directions, and again before writing the tokens in step A4.

### Two or three genuinely distinct directions

Three variations on one idea is one direction with three palettes, and the user can feel
it — the choice is fake and they know it. Distinctness comes from varying the axes that
change the *structure* of the page, not the surface:

| Axis | Meaningfully different means |
| --- | --- |
| Typographic voice | Grotesque vs humanist sans vs transitional serif vs monospace-led vs a display face doing the work alone |
| Layout structure | Centred single column vs asymmetric split vs editorial grid with rules vs full-bleed image-first vs dense dashboard-like tiling |
| Colour strategy | Near-monochrome with one accent vs two-tone brand pair vs a light neutral ground with saturated punctuation vs dark ground with luminous type |
| Imagery approach | Photography-led vs illustration vs pure type and rules vs data and diagrams vs no imagery at all |
| Density and rhythm | Generous and slow vs tight and information-dense |

A useful test: write each direction's thesis as one sentence, then swap the subject for a
different business. If the sentence still reads fine, the direction is generic and should
be replaced. "Field-notes precision for people who measure things" belongs to a
particular subject. "Modern and clean with a friendly feel" belongs to nothing.

Ground each direction in something real about the subject — the material it is made of,
the discipline it comes from, the era it belongs to, the physical object it replaces.
That is where a signature element comes from, and the signature is what the site is
remembered by.

### Clichés to avoid by default

These are the tells of a generated site. Each is defensible when the brief asks for it,
and a failure of imagination when it appears because nothing else was considered:

- Cream or off-white background (`#FDFCF8` and neighbours) with an oversized
  high-contrast serif headline and a terracotta or burnt-orange accent.
- A row of exactly three feature cards with an icon, a two-word title and a line of
  filler, sitting under a heading that says "Features".
- Unmotivated gradient blobs, mesh gradients, or a blurred purple-to-blue radial behind
  the hero.
- Glassmorphism applied to elements that are not overlaying anything.
- `01 / 02 / 03` numbering on content that has no order.
- Scroll-triggered fade-up on every element on the page.
- A hero that says what the company does in a sentence that could describe any company,
  above a screenshot in a floating browser chrome mockup.

### Type as a system

Choose a scale and stay on it. Ad-hoc values (`17px` here, `23px` there) are what make a
page feel unresolved even when nothing is obviously wrong.

```css
:root {
  /* 1.25 ratio, clamped for fluid sizing at the top end */
  --step--1: 0.8rem;
  --step-0:  1rem;      /* body */
  --step-1:  1.25rem;
  --step-2:  1.563rem;
  --step-3:  1.953rem;
  --step-4:  clamp(2.44rem, 1.9rem + 2.7vw, 3.815rem);   /* display */

  --leading-tight: 1.1;   /* display */
  --leading-body:  1.55;  /* body, 1.5 minimum */
  --measure: 68ch;        /* 45-75ch keeps long text readable */
}
```

Two families is usually the ceiling: one for display, one for text. A third needs a
reason. Pair by contrast — if the display face is a high-contrast serif, the text face
should not also be, or the page reads as one blurred texture.

### Spacing as a system

Space from one scale, ideally derived from a single base:

```css
:root {
  --space-3xs: 0.25rem; --space-2xs: 0.5rem; --space-xs: 0.75rem;
  --space-s: 1rem; --space-m: 1.5rem; --space-l: 2rem;
  --space-xl: 3rem; --space-2xl: 4.5rem; --space-3xl: 7rem;
}
```

Vertical rhythm between sections is what communicates hierarchy at a glance. If every
gap on the page is the same, the page has no structure regardless of its typography.

### Colour, contrast-checked before it is chosen

Check contrast while picking the palette, not after the build, because a hero colour that
fails at 3.9:1 forces either a redesign or a compromise nobody likes. Work in a
perceptual space (OKLCH) so lightness steps are even, fix the text-on-ground pairs first,
then choose the accent from what is left.

```css
:root {
  --ground:  oklch(98% 0.005 250);
  --ink:     oklch(22% 0.02 250);   /* on --ground: verify ≥ 4.5:1 */
  --muted:   oklch(48% 0.02 250);   /* on --ground: verify ≥ 4.5:1 */
  --accent:  oklch(52% 0.17 25);    /* on --ground and as a boundary: ≥ 3:1 */
  --on-accent: oklch(99% 0 0);      /* on --accent: verify ≥ 4.5:1 */
}
```

Never carry meaning in colour alone — an error field needs an icon or text as well as a
red border, because roughly one in twelve men cannot distinguish it reliably.

## Responsive behaviour

Design for the narrow viewport first and let the layout widen. A layout that only works
above 900px is not "mostly done" — most traffic to most sites is mobile, so it is broken
for the majority of visitors.

Breakpoints belong where the content stops working, not at device names. A practical
starting set:

| Width | What must be true |
| --- | --- |
| 360px | Nothing clipped, no horizontal scroll, tap targets ≥ 44x44px, text ≥ 16px |
| 480px | Single column, stacked navigation, images full-bleed or contained |
| 768px | Two-column layouts become viable; tables may still need to scroll |
| 1024px | Full layout, sidebars, multi-column grids |
| 1440px+ | Content capped by `--measure` or a max width, not stretched edge to edge |

```css
/* prefer intrinsic layout over breakpoints where possible */
.cards { display: grid; gap: var(--space-m);
         grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); }
```

Check these specifically, because they are where narrow layouts actually break: long
unbroken strings (URLs, tokens) overflowing, tables, fixed-width images, position-fixed
headers eating the viewport, and modals taller than the screen with no internal scroll.

```bash
# quick overflow check in the console
[...document.querySelectorAll('*')].filter(e => e.scrollWidth > document.documentElement.clientWidth)
```

## Accessibility

WCAG 2.2 AA is the target. The point is not the certificate — every item below is
something that stops a real person using the site.

### Structure

- One `h1` per page, describing the page. Headings descend without skipping levels;
  `h4` under an `h2` is a structural lie that screen-reader users navigate by.
- Landmarks: `header`, `nav`, `main` (exactly one), `aside`, `footer`. A skip link to
  `#main` as the first focusable element.
- `html lang="en"` — screen readers pick the wrong voice without it.
- Lists are `ul`/`ol`, buttons are `button`, links that navigate are `a` with an `href`.

**A native element beats an ARIA reconstruction of it.** `<button>` gives you focus,
Enter and Space activation, the correct role, and the disabled semantics for free; `<div
role="button" tabindex="0">` gives you the role and a maintenance obligation for
everything else. Reach for ARIA to describe things HTML cannot express, not to rebuild
things it already does.

### Keyboard

- Every interactive element reachable and operable by keyboard, in an order that matches
  the visual order.
- A visible focus ring everywhere. `outline: none` without a replacement is the single
  most common accessibility defect in generated sites.

```css
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

- Dialogs trap focus while open, close on `Escape`, and return focus to the element that
  opened them. `<dialog>` with `showModal()` handles all three; a hand-built overlay
  handles none of them.
- No keyboard trap anywhere else — if focus can enter, it can leave.

### Content

- Every input has a `<label for>` or an `aria-label`. Placeholder text is not a label:
  it disappears on typing and fails contrast in most implementations.
- `alt` text describes the purpose the image serves in context, not the pixels. A logo
  linking home is `alt="Home"`. **Empty `alt=""` is correct** for decoration, spacers,
  and any image whose meaning is already in adjacent text — omitting the attribute makes
  screen readers read the filename instead.
- Link text makes sense alone. "Read more" repeated eleven times is a list of eleven
  identical destinations to anyone tabbing the page.

### Contrast

| Content | Minimum |
| --- | --- |
| Body text | 4.5:1 |
| Large text (≥ 24px, or ≥ 18.66px bold) | 3:1 |
| UI boundaries: input borders, focus rings, icons carrying meaning | 3:1 |

Placeholder text, disabled-looking-but-active controls, and light grey captions are where
this fails in practice.

### Motion and live content

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important;
  }
}
```

Content that changes without a navigation — form errors, toasts, search results, async
status — needs `aria-live="polite"` on a region that exists in the DOM *before* the
content arrives, or nothing is announced. Use `assertive` only for genuine
interruptions.

### Checks

```bash
npx @axe-core/cli https://example.com            # automated pass, ~30% of issues
npx pa11y https://example.com
```

Automated tools catch a minority of real problems. The manual pass is: tab the whole
page start to finish, use it once with the mouse unplugged, and zoom to 200% to confirm
nothing is lost.

## Performance

### Core Web Vitals

| Metric | Good | Needs work | What it measures |
| --- | --- | --- | --- |
| LCP — Largest Contentful Paint | ≤ 2.5s | ≤ 4.0s | When the main content appears |
| CLS — Cumulative Layout Shift | ≤ 0.1 | ≤ 0.25 | How much the layout jumps |
| INP — Interaction to Next Paint | ≤ 200ms | ≤ 500ms | Responsiveness across all interactions |

INP replaced First Input Delay as a Core Web Vital in March 2024. FID only measured the
delay before the *first* interaction was handled; INP measures the full interaction-to-
paint latency across the whole visit, which is why sites that passed FID comfortably can
fail INP. Long tasks on the main thread are the usual cause — break them up, or move the
work off the main thread.

### Images

Unsized images are the main cause of CLS, and oversized images are the main cause of a
slow LCP.

```html
<img src="hero-1200.avif" width="1200" height="675" alt="…"
     fetchpriority="high" decoding="async">
<img src="card.avif" width="640" height="360" alt="…" loading="lazy" decoding="async">
```

- Always set `width` and `height` (or an `aspect-ratio` in CSS) so the box is reserved.
- AVIF or WebP with a fallback; PNG only for genuine transparency at small sizes; SVG for
  logos and icons.
- `loading="lazy"` below the fold, never on the LCP image — lazy-loading the hero delays
  the metric it defines.
- Serve at the size actually rendered, with `srcset` for the range of viewports.

### Fonts

```html
<link rel="preload" href="/fonts/display.woff2" as="font"
      type="font/woff2" crossorigin>
```

```css
@font-face {
  font-family: 'Display'; src: url('/fonts/display.woff2') format('woff2');
  font-display: swap; font-weight: 400 700; /* variable, one file */
}
```

Preload the one font in the LCP element, not all of them — preloading four fonts makes
each of them arrive later. `font-display: swap` shows text immediately in a fallback;
pair it with a metric-compatible fallback stack so the swap does not shift the layout.
Self-host: a third-party font host adds a connection, a DNS lookup and a privacy
question.

### Budget

A realistic floor for a content site, gzipped, on the initial route:

| Resource | Budget |
| --- | --- |
| HTML | ≤ 30 KB |
| CSS | ≤ 50 KB |
| JavaScript | ≤ 100 KB (tier 1-2), ≤ 200 KB (tier 3-4) |
| Fonts | ≤ 150 KB total, ≤ 2 families |
| LCP image | ≤ 200 KB |
| Total initial load | ≤ 500 KB, ≤ 50 requests |

```bash
npx lighthouse https://example.com --preset=desktop --view
npx lighthouse https://example.com --form-factor=mobile --throttling-method=simulate
npx source-map-explorer 'dist/**/*.js'          # what is actually in the bundle
```

Measure mobile with throttling. A desktop score on a fast connection tells you nothing
about the visitor on a mid-range Android phone.

## Security headers

A static site can set most of these, and they cost nothing to add at build time.

```text
Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self';
  script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
Referrer-Policy: strict-origin-when-cross-origin
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

What a `<meta http-equiv>` tag can do: `Content-Security-Policy` only, and only for
directives evaluated after the document starts parsing — `frame-ancestors`,
`report-uri` and sandbox directives are ignored in meta form. Everything else in that
list, including HSTS and `X-Content-Type-Options`, is a response header only; a meta tag
version does nothing. If the host cannot set headers, say so as a limitation rather than
shipping meta tags that look like coverage.

Configure them where the host allows it — `_headers` on Netlify and Cloudflare Pages,
`vercel.json` on Vercel, `add_header` in nginx, a middleware in a server-rendered app.

```bash
curl -sI https://example.com | grep -iE 'content-security|strict-transport|x-content|referrer'
npx observatory-cli example.com     # or check securityheaders.com
```

## SEO and metadata

The basics, done honestly. None of this is a growth tactic; it is the site describing
itself accurately so it can be found and shared.

```html
<title>Page-specific title, 50-60 chars — Site name</title>
<meta name="description" content="What this page is, 120-155 chars, written for a
      human reading a search result.">
<link rel="canonical" href="https://example.com/page">

<meta property="og:title" content="…">
<meta property="og:description" content="…">
<meta property="og:image" content="https://example.com/og.png"><!-- 1200x630, absolute -->
<meta property="og:url" content="https://example.com/page">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
```

Plus `robots.txt` and a `sitemap.xml` that lists real URLs, generated at build time
rather than maintained by hand. Structured data (`Article`, `Product`, `Organization`,
`BreadcrumbList`) only where it describes something that is genuinely on the page —
marking up reviews that do not exist is what gets a site penalized, and it is dishonest
before it is risky.

Every page needs its own title and description. A site where every page shares the home
page's title is invisible in search results and identical in every share preview.

## The checklist

Mark each item `pass`, `fail`, or `not checked — <how to check it>`. Marking something
`pass` that was not actually run is the failure this checklist exists to prevent: it
converts an unknown into a false assurance the user will act on.

```markdown
### Responsive
- [ ] No horizontal scroll at 360px
- [ ] Layout works at 360 / 768 / 1024 / 1440
- [ ] Tap targets ≥ 44x44px; body text ≥ 16px
- [ ] Tables, code blocks and long strings contained

### Accessibility
- [ ] One h1, headings in order, landmarks present, lang set
- [ ] Full keyboard pass; visible :focus-visible ring everywhere
- [ ] Dialogs trap and restore focus, close on Escape
- [ ] Every input labelled; errors linked by aria-describedby
- [ ] alt text correct, decorative images alt=""
- [ ] Contrast 4.5:1 body / 3:1 large and UI boundaries
- [ ] prefers-reduced-motion respected
- [ ] aria-live on async status regions
- [ ] axe / pa11y clean

### Performance
- [ ] LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms (mobile, throttled)
- [ ] Images sized, modern format, lazy below the fold, hero not lazy
- [ ] Fonts self-hosted, font-display: swap, one preload
- [ ] Within budget; no unused framework shipped

### Security
- [ ] CSP, Referrer-Policy, X-Content-Type-Options, HSTS set at the host
- [ ] No secrets in the client bundle
- [ ] External links: rel="noopener"
- [ ] Dependencies audited

### SEO
- [ ] Unique title and description per page
- [ ] Open Graph and Twitter card, absolute image URL
- [ ] Canonical URL, robots.txt, sitemap.xml
- [ ] Structured data honest, or absent

### Build
- [ ] No console errors or warnings
- [ ] No dead links; 404 page exists
- [ ] Production build succeeds from a clean checkout
- [ ] Real content throughout, no placeholders
```
