"""The look of the catalogue site: one stylesheet and two small inline scripts.

The layout follows the owner's design, written out as plain CSS rather than the utility
classes it was first drafted in, so the site builds with the standard library alone and
needs no asset pipeline. Colour lives in five variables; the night and console themes
only reassign them, which is why no page carries a second copy of its rules.

Three themes exist: day, night, and a console theme ("reactor") the visitor switches on
by hand. With nothing stored the clock decides between day and night, 20:00 to 06:00 in
the visitor's own time.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NamedTuple

# The two typefaces are served from the site itself, so a visitor makes no request to a font
# host. Each file is the `latin` subset Google Fonts serves for its family, one variable
# font covering every weight the page uses, stored under scripts/site_assets/fonts/ and
# copied to /fonts/ by the build. Its name carries a short hash of its bytes, which is what
# makes the year-long immutable cache in `_headers` safe: a changed font is a new URL.
FONT_DIR = Path(__file__).resolve().parent / "site_assets" / "fonts"
FONT_URL_PREFIX = "/fonts/"
# unicode-range as Google Fonts publishes it for the latin subset, so a character outside
# it falls back exactly as it did when the fonts came from Google.
_LATIN_RANGE = (
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, "
    "U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, "
    "U+FEFF, U+FFFD"
)


def _hashed(source: str) -> str:
    """The built name of a file in ``FONT_DIR``: its stem, a content hash, its suffix."""
    path = FONT_DIR / source
    # This runs at import, before build() can check anything, so a missing font has to be
    # refused here in the same words build() uses rather than surface as a traceback.
    try:
        data = path.read_bytes()
    except OSError as error:
        raise SystemExit(f"cannot read the site font file {source}: {error}") from error
    digest = hashlib.sha256(data).hexdigest()[:10]
    return f"{path.stem}.{digest}{path.suffix}"


SANS_FILE = _hashed("instrument-sans-latin.woff2")
SERIF_FILE = _hashed("newsreader-latin.woff2")
SANS_LICENCE = _hashed("OFL-instrument-sans.txt")
SERIF_LICENCE = _hashed("OFL-newsreader.txt")
# Every file under /fonts/ in the built site, as built name -> source name. The licences
# are here because the OFL requires the text to travel with the fonts.
FONT_ASSETS = {
    SANS_FILE: "instrument-sans-latin.woff2",
    SERIF_FILE: "newsreader-latin.woff2",
    SANS_LICENCE: "OFL-instrument-sans.txt",
    SERIF_LICENCE: "OFL-newsreader.txt",
}
# Absolute paths, because the 404 page is served from whatever address was asked for.
SANS_URL = FONT_URL_PREFIX + SANS_FILE
SERIF_URL = FONT_URL_PREFIX + SERIF_FILE

FONT_FACES = f"""
/* Instrument Sans, Copyright 2022 The Instrument Sans Project Authors. SIL Open Font
   License 1.1: {FONT_URL_PREFIX}{SANS_LICENCE} */
@font-face {{
  font-family: "Instrument Sans";
  font-style: normal;
  font-weight: 400 700;
  font-display: swap;
  src: url({SANS_URL}) format("woff2");
  unicode-range: {_LATIN_RANGE};
}}
/* Newsreader, Copyright 2020 The Newsreader Project Authors. SIL Open Font License 1.1:
   {FONT_URL_PREFIX}{SERIF_LICENCE} */
@font-face {{
  font-family: "Newsreader";
  font-style: normal;
  font-weight: 200 800;
  font-display: swap;
  src: url({SERIF_URL}) format("woff2");
  unicode-range: {_LATIN_RANGE};
}}
"""

CSS = """@@FONT_FACES@@
:root {
  --bg: #f4f1ea;
  --ink: #141413;
  --muted: #5e5a54;
  --line: #e3ddd3;
  --card: #ebe6dc;
  --glass-tint: rgba(235, 230, 220, 0.62);
  --glass-edge: rgba(255, 255, 255, 0.85);
  --glass-sheen: rgba(255, 255, 255, 0.45);
  --glass-shadow: rgba(20, 20, 19, 0.12);
  --font-sans: "Instrument Sans", ui-sans-serif, system-ui, sans-serif;
  --font-serif: "Newsreader", "Iowan Old Style", Palatino, Georgia, serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  color-scheme: light;
}
html[data-theme="night"] {
  --bg: #000000;
  --ink: #f3efe6;
  --muted: #a39e94;
  --line: #2a2724;
  --card: #141413;
  --glass-tint: rgba(36, 34, 31, 0.58);
  --glass-edge: rgba(255, 255, 255, 0.22);
  --glass-sheen: rgba(255, 255, 255, 0.08);
  --glass-shadow: rgba(0, 0, 0, 0.6);
  color-scheme: dark;
}
html[data-theme="reactor"] {
  --bg: #070807;
  --ink: #d2f07a;
  --muted: #8aa36a;
  --line: #24321c;
  --card: #10170e;
  --glass-tint: rgba(22, 34, 18, 0.6);
  --glass-edge: rgba(210, 240, 122, 0.28);
  --glass-sheen: rgba(210, 240, 122, 0.07);
  --glass-shadow: rgba(0, 0, 0, 0.6);
  color-scheme: dark;
}

*, ::before, ::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  border: 0 solid var(--line);
}
[hidden] { display: none !important; }
html {
  background: var(--bg);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  -webkit-text-size-adjust: 100%;
}
body {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 1.0625rem;
  line-height: 1.5;
}
h1, h2, h3, h4, h5, h6 { font-size: inherit; font-weight: inherit; }
a { color: inherit; text-decoration: inherit; }
ul, ol { list-style: none; }
svg { display: block; }
button, input {
  font: inherit;
  color: inherit;
  background: none;
  border-radius: 0;
  text-align: left;
}
button:not(:disabled) { cursor: pointer; }
input[type="search"] { -webkit-appearance: none; appearance: none; }
::placeholder { color: var(--muted); opacity: 1; }
table { border-collapse: collapse; }
code, pre { font-family: var(--font-mono); font-size: 1em; }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 3px; }
main { flex: 1; }

html[data-theme="reactor"] body {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background-image:
    linear-gradient(rgba(210, 240, 122, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(210, 240, 122, 0.045) 1px, transparent 1px);
  background-size: 56px 56px;
}
html[data-theme="reactor"] h1, html[data-theme="reactor"] h2 {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight: 500;
  letter-spacing: -0.04em;
}
html[data-theme="reactor"] .card {
  border-radius: 0;
  box-shadow: inset 0 0 0 1px var(--line);
}
html[data-theme="reactor"]::before {
  content: "";
  pointer-events: none;
  position: fixed;
  inset: 0;
  z-index: 40;
  background: repeating-linear-gradient(
    to bottom, transparent 0, transparent 2px, rgba(0, 0, 0, 0.16) 3px
  );
}
@media (prefers-reduced-motion: no-preference) {
  a, button {
    transition: color 160ms ease, background-color 160ms ease, opacity 160ms ease;
  }
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.skip:focus {
  position: fixed;
  left: 1rem;
  top: 1rem;
  z-index: 20;
  width: auto;
  height: auto;
  margin: 0;
  overflow: visible;
  clip-path: none;
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* Header: sticky, hides while scrolling down. */
.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.site-header.away { transform: translateY(-100%); }
@media (prefers-reduced-motion: no-preference) {
  .site-header { transition: transform 200ms; }
}
.bar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 4rem;
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1.25rem;
}
.bar nav {
  display: none;
  align-items: center;
  gap: 1.5rem;
  font-size: 0.875rem;
  line-height: 1.4286;
}
@media (min-width: 64rem) {
  .bar nav { display: flex; }
}
.bar nav a, .foot nav a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
}
.bar nav a:hover, .foot nav a:hover { color: var(--muted); }
a[aria-current="page"] { text-decoration: underline; text-underline-offset: 4px; }
#home {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  min-width: 2.75rem;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  line-height: 1.4286;
  font-weight: 500;
  letter-spacing: 0.1em;
}
.tools { margin-left: auto; display: flex; align-items: center; }
.tool {
  display: inline-flex;
  min-width: 2.75rem;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
}
#console-theme { color: var(--muted); }
#console-theme[aria-pressed="true"] { color: var(--ink); }
#console-theme svg { width: 1rem; height: 1rem; }
.track {
  display: flex;
  align-items: center;
  width: 3.25rem;
  height: 2rem;
  padding: 0.25rem;
  border-radius: 999px;
  background: #cfc8bc;
  box-shadow: inset 0 1px 2px rgba(20, 20, 19, 0.18);
}
html[data-theme="night"] .track { background: var(--ink); }
html[data-theme="reactor"] .track { background: #1c2816; }
.knob {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  box-shadow: 0 1px 2px rgba(20, 20, 19, 0.35), 0 2px 6px rgba(20, 20, 19, 0.2);
}
html[data-theme="night"] .knob {
  transform: translateX(1.25rem);
  background: var(--bg);
  color: var(--ink);
}
/* Sun and moon share the knob's centre; one is shown, the other turned away and faded,
   so the switch can turn one into the other rather than swap them. */
.knob svg { position: absolute; width: 0.875rem; height: 0.875rem; }
.moon { opacity: 0; transform: rotate(-90deg) scale(0.4); }
html[data-theme="night"] .moon { opacity: 1; transform: none; }
html[data-theme="night"] .sun { opacity: 0; transform: rotate(90deg) scale(0.4); }
@media (prefers-reduced-motion: no-preference) {
  .track { transition: background-color 600ms cubic-bezier(0.45, 0, 0.2, 1); }
  .knob {
    transition: transform 600ms cubic-bezier(0.45, 0, 0.2, 1),
      background-color 600ms ease, color 600ms ease;
  }
  .knob svg { transition: opacity 400ms ease, transform 600ms cubic-bezier(0.45, 0, 0.2, 1); }
}

/* Footer. */
.site-footer {
  border-top: 1px solid var(--line);
  /* Room below the last line, so the footer can scroll clear of To top. */
  padding-bottom: 4rem;
}
.foot {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 72rem;
  margin: 0 auto;
  padding: 2.5rem 1.25rem;
  font-size: 0.875rem;
  line-height: 1.4286;
}
.foot .mark { font-weight: 500; letter-spacing: 0.1em; }
.foot .tag { margin-top: 0.5rem; max-width: 24rem; color: var(--muted); }
.foot .credit { margin-top: 0.75rem; color: var(--muted); }
.foot .credit a { color: var(--ink); text-decoration: underline; text-underline-offset: 4px; }
.foot nav { display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; }
@media (min-width: 40rem) {
  .foot { flex-direction: row; align-items: flex-end; justify-content: space-between; }
}

/* The index. */
.wrap { max-width: 72rem; margin: 0 auto; padding: 0 1.25rem; }
.hero { display: grid; gap: 2.5rem; padding-top: 4rem; padding-bottom: 2rem; }
.hero h1 {
  font-size: 3rem;
  line-height: 1.05;
  font-weight: 500;
  letter-spacing: -0.025em;
  text-wrap: balance;
}
.hero h1 span {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 8px;
}
.lede {
  font-size: 1.125rem;
  line-height: 1.5556;
  text-wrap: pretty;
  color: var(--muted);
}
.small { font-size: 0.875rem; line-height: 1.4286; color: var(--muted); }
.counts { margin-top: 1.5rem; }
.pill {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  margin-top: 2rem;
  padding: 0 1rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  font-size: 0.875rem;
  line-height: 1.4286;
  white-space: nowrap;
}
.pill:hover { opacity: 0.8; }
@media (min-width: 40rem) {
  .hero { padding-top: 6rem; }
  .hero h1 { font-size: 3.75rem; }
}
@media (min-width: 64rem) {
  .hero { grid-template-columns: repeat(12, minmax(0, 1fr)); align-items: end; gap: 4rem; }
  .hero h1 { grid-column: span 7; }
  .hero .side { grid-column: span 5; }
}
.listing { padding-bottom: 5rem; }
.card {
  border-radius: 1.5rem;
  background: var(--card);
  padding: 2.5rem 1.5rem;
}
.card p {
  max-width: 48rem;
  font-family: var(--font-serif);
  font-size: 1.875rem;
  line-height: 1.375;
  text-wrap: balance;
}
@media (min-width: 40rem) {
  .card { padding: 3.5rem 2.5rem; }
  .card p { font-size: 2.25rem; }
}
.finder {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 3.5rem;
}
.finder label { display: block; width: 100%; max-width: 28rem; }
.finder input {
  width: 100%;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  font-size: 1rem;
  line-height: 1.5;
  outline: none;
}
@media (min-width: 40rem) {
  .finder { flex-direction: row; align-items: flex-end; justify-content: space-between; }
}
.none { margin-top: 4rem; font-size: 1.125rem; line-height: 1.5556; color: var(--muted); }
#list { margin-top: 1.5rem; }
.plugin { padding: 2rem 0; border-top: 1px solid var(--line); }
.plugin .row { display: flex; flex-direction: column; gap: 0.5rem; }
.plugin h2 {
  font-size: 1.875rem;
  line-height: 1.2;
  font-weight: 500;
  letter-spacing: -0.025em;
}
.plugin h2 a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  text-decoration: underline;
  text-decoration-color: transparent;
  text-underline-offset: 4px;
}
.plugin h2 a:hover { text-decoration-color: currentColor; }
.plugin .blurb { margin-top: 0.75rem; max-width: 42rem; text-wrap: pretty; color: var(--muted); }
.plugin .hits { margin-top: 1rem; }
@media (min-width: 40rem) {
  .plugin .row { flex-direction: row; align-items: baseline; justify-content: space-between; }
}

/* Plugin, skill and the other pages. */
.page { width: 100%; max-width: 72rem; margin: 0 auto; padding: 3rem 1.25rem; }
.page.narrow { max-width: 48rem; }
@media (min-width: 40rem) {
  .page { padding-top: 4rem; padding-bottom: 4rem; }
}
.crumbs a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  text-decoration: underline;
  text-underline-offset: 4px;
}
/* Back and To top: Material Design 3's button with a leading icon (full pill, 1.125rem
   icon, 14px medium label, 44px target, state layers of the label colour at 8% on
   hover and 12% pressed), made of Liquid Glass: a translucent tint that blurs and
   saturates what is behind it, a bright specular edge along the top, a soft sheen, a
   hairline rim and a floating shadow. Pressed, it gives a little. */
.back {
  position: relative;
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1.25rem 0 1rem;
  border-radius: 999px;
  background-color: var(--glass-tint);
  background-image: linear-gradient(180deg, var(--glass-sheen), transparent 65%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  backdrop-filter: blur(16px) saturate(180%);
  box-shadow: inset 0 1px 0 0 var(--glass-edge),
    inset 0 0 0 1px color-mix(in srgb, var(--ink) 10%, transparent),
    0 1px 2px var(--glass-shadow), 0 6px 16px -4px var(--glass-shadow);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 0.875rem;
  line-height: 1.4286;
  font-weight: 500;
  letter-spacing: 0.00625rem;
  text-decoration: none;
  white-space: nowrap;
}
.back svg { width: 1.125rem; height: 1.125rem; flex: none; }
.back:hover {
  background-image: linear-gradient(180deg, var(--glass-sheen), transparent 65%),
    linear-gradient(color-mix(in srgb, var(--ink) 8%, transparent),
      color-mix(in srgb, var(--ink) 8%, transparent));
}
.back:active {
  background-image: linear-gradient(180deg, var(--glass-sheen), transparent 65%),
    linear-gradient(color-mix(in srgb, var(--ink) 12%, transparent),
      color-mix(in srgb, var(--ink) 12%, transparent));
}
@media (prefers-reduced-motion: no-preference) {
  .back { transition: transform 120ms ease, box-shadow 120ms ease; }
  .back:active { transform: scale(0.97); }
}
.back + .crumbs { margin-top: 1rem; }
/* The bar Back moves into once the page has scrolled past its own Back: a
   top app bar on the solid page colour, so text scrolls under it and never shows
   behind a button. It sits below the header while the header shows, and at the top when the
   header has slid away. Hidden, and out of the tab order, until then. */
.dock {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9;
  border-bottom: 1px solid var(--line);
  background: var(--bg);
  visibility: hidden;
  opacity: 0;
  transform: translateY(-0.5rem);
  pointer-events: none;
}
.site-header:not(.away) ~ .dock { top: calc(4rem + 1px); }
.dock.on { visibility: visible; opacity: 1; transform: none; pointer-events: auto; }
@media (prefers-reduced-motion: no-preference) {
  .dock {
    transition: opacity 150ms ease, transform 150ms ease, top 200ms ease,
      visibility 0s linear 150ms;
  }
  .dock.on { transition: opacity 150ms ease, transform 150ms ease, top 200ms ease; }
}
.dock-in {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 72rem;
  margin: 0 auto;
  padding: 0.5rem max(1.25rem, env(safe-area-inset-right)) 0.5rem
    max(1.25rem, env(safe-area-inset-left));
}
/* To top floats at the bottom right: Material's place for a page's one floating
   action, and the one place Liquid Glass is meant for, a control over the content.
   Round with only the arrow on a narrow screen, where the column is all text, and
   labelled once the margin beside the 72rem column can hold the label. Its tint is
   denser than Back's, because it sits over running text rather than the solid bar,
   and glyphs showing through compete with the arrow. Hidden, and out of the tab
   order, until the script shows it. */
.fab {
  position: fixed;
  right: max(1rem, env(safe-area-inset-right));
  bottom: max(1rem, env(safe-area-inset-bottom));
  z-index: 9;
  justify-content: center;
  background-color: color-mix(in srgb, var(--glass-tint) 55%, var(--bg));
  width: 3rem;
  min-height: 3rem;
  padding: 0;
  visibility: hidden;
  opacity: 0;
  transform: translateY(0.5rem);
  pointer-events: none;
}
.fab span { display: none; }
.fab.on { visibility: visible; opacity: 1; transform: none; pointer-events: auto; }
@media (prefers-reduced-motion: no-preference) {
  .fab {
    transition: opacity 150ms ease, transform 150ms ease, box-shadow 120ms ease,
      visibility 0s linear 150ms;
  }
  .fab.on { transition: opacity 150ms ease, transform 150ms ease, box-shadow 120ms ease; }
  .fab.on:active { transform: scale(0.97); }
}
@media (min-width: 40rem) {
  .fab {
    right: max(1.5rem, env(safe-area-inset-right));
    bottom: max(1.5rem, env(safe-area-inset-bottom));
  }
}
@media (min-width: 90rem) {
  .fab { width: auto; padding: 0 1.25rem 0 1rem; }
  .fab span { display: inline; }
}
/* A jump to a heading (an in-page link, a shared deep link, the finder) lands below
   both bars rather than under them. A jump upwards brings the header back with the
   bar stacked beneath it: 4rem and a border, then 0.5rem, a 2.75rem button, 0.5rem and
   a border, 7.875rem in all, so 8.5rem leaves a gap. Zero specificity, so a rule that
   sets its own margin wins. */
:where([id]) { scroll-margin-top: 8.5rem; }
.crumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  margin-bottom: 2rem;
  font-size: 0.875rem;
  line-height: 1.4286;
}
.crumbs a.quiet { color: var(--muted); }
.title-xl {
  max-width: 48rem;
  margin-top: 1.5rem;
  font-size: 3rem;
  line-height: 1;
  font-weight: 500;
  letter-spacing: -0.025em;
  text-wrap: balance;
}
@media (min-width: 40rem) {
  .title-xl { font-size: 3.75rem; }
}
.title {
  font-size: 2.25rem;
  line-height: 1.1111;
  font-weight: 500;
  letter-spacing: -0.025em;
  text-wrap: balance;
}
.page .lede { max-width: 42rem; margin-top: 1.5rem; }
.page-body { margin-top: 2.5rem; }
.back + .title { margin-top: 1.5rem; }
.title + .lede { margin-top: 1rem; }
.page .small.count { margin-top: 1rem; }
.install { max-width: 42rem; margin-top: 2rem; }
.install pre {
  padding: 1rem 1.15rem;
  overflow-x: auto;
  background: var(--card);
  border-radius: 1rem;
  font-size: 0.875rem;
}
.skills { display: grid; margin-top: 1.5rem; }
.skills li { border-bottom: 1px solid var(--line); }
.skills a { display: flex; width: 100%; min-height: 2.75rem; align-items: center; }
.skills a:hover { color: var(--muted); }
@media (min-width: 40rem) {
  .skills { grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 3rem; }
}
.page .finder { margin-top: 3rem; }

/* Rendered Markdown. */
.prose-lab {
  font-family: var(--font-serif);
  font-size: 1.2rem;
  line-height: 1.55;
  color: var(--ink);
}
.prose-lab h1, .prose-lab h2, .prose-lab h3 {
  font-family: var(--font-sans);
  font-weight: 500;
  letter-spacing: -0.02em;
  text-wrap: balance;
  line-height: 1.15;
}
.prose-lab h1 {
  font-family: var(--font-serif);
  font-size: 2.75rem;
  font-weight: 450;
  margin: 0 0 1.25rem;
}
.prose-lab h2 {
  font-size: 1.5rem;
  margin: 2.5rem 0 0.75rem;
}
.prose-lab h3 {
  font-size: 1.15rem;
  margin: 1.75rem 0 0.5rem;
}
.prose-lab p {
  margin: 0 0 1rem;
  text-wrap: pretty;
}
.prose-lab ul, .prose-lab ol {
  margin: 0 0 1.25rem;
  padding-left: 1.25rem;
}
.prose-lab li {
  margin: 0.35rem 0;
}
.prose-lab a {
  color: var(--ink);
  text-decoration: underline;
  text-underline-offset: 0.15em;
  /* A bare address is one unbreakable word; in the real serif it ran 22 px past a 360 px
     screen, which the fallback font hid. */
  overflow-wrap: anywhere;
}
.prose-lab code {
  font-family: var(--font-sans);
  font-size: 0.86em;
  background: var(--card);
  padding: 0.08em 0.35em;
  border-radius: 0.3rem;
}
/* A path, a flag or an identifier in running text has no break opportunity of its own,
   so on a phone one long one pushed the whole page wider than the screen. It may break
   anywhere; a code block keeps its lines and scrolls inside its own box instead. */
.prose-lab :not(pre) > code { overflow-wrap: anywhere; }
.prose-lab pre {
  margin: 0 0 1.25rem;
  padding: 1rem 1.15rem;
  overflow-x: auto;
  background: var(--card);
  border-radius: 1rem;
}
.prose-lab pre code {
  background: none;
  padding: 0;
}
.prose-lab blockquote {
  margin: 0 0 1.25rem;
  padding-left: 1rem;
  border-left: 2px solid var(--ink);
  color: var(--muted);
}
.prose-lab hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 2rem 0;
}
.prose-lab .table-wrap {
  margin: 0 0 1.5rem;
  overflow-x: auto;
}
.prose-lab table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.45;
}
.prose-lab th, .prose-lab td {
  border-bottom: 1px solid var(--line);
  padding: 0.7rem 1rem 0.7rem 0;
  text-align: left;
  vertical-align: top;
}
.prose-lab th {
  font-weight: 500;
}
/* Additions the design's own list does not cover: the reset above removes bullets and
   the monospace of code blocks, and the pages here use both. */
.prose-lab ul { list-style: disc; }
.prose-lab ol { list-style: decimal; }
.prose-lab pre code { font-family: var(--font-mono); font-size: 0.875rem; }
.prose-lab a.pill { color: var(--bg); text-decoration: none; font-family: var(--font-sans); }
.prose-lab .actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0 0 1.5rem; }
.prose-lab .actions .pill { margin-top: 0; }
.prose-lab .lead {
  font-family: var(--font-sans);
  font-size: 1.0625rem;
  line-height: 1.5;
  color: var(--muted);
}
.prose-lab .al-r { text-align: right; }
.prose-lab .al-c { text-align: center; }
.prose-lab td.num, .prose-lab th.num { text-align: right; font-variant-numeric: tabular-nums; }
.prose-lab .say { color: var(--muted); }
/* The FAMILY pages are hand-drawn: a stage timeline whose stages open, a profile picker,
   a checklist and profile cards, rather than the generated prose-and-table layout every
   other page uses. Scoped to .family-*. */
.family-section { margin-top: 3rem; }
.family-section h2 {
  font-family: var(--font-sans);
  font-size: 1.5rem;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 0.75rem;
}
.family-section > p { max-width: 42rem; margin: 0 0 1rem; color: var(--muted); }
.family-section a, .family-example a {
  color: var(--ink);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}
.family-section code, .family-example code {
  font-family: var(--font-mono);
  font-size: 0.86em;
  background: var(--card);
  padding: 0.08em 0.35em;
  border-radius: 0.3rem;
}
.family-section .install { margin-top: 1rem; }
.family-section .finder { margin-top: 1.5rem; }
.family-section #list { margin-top: 1rem; }
.family-agents { list-style: none; display: grid; gap: 0; }
.family-agents li { padding: 0.75rem 0; border-bottom: 1px solid var(--line); }
.picker {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem 1rem;
  margin: 1.5rem 0 0.5rem;
}
.picker fieldset { min-width: 0; }
.picker legend { padding: 0; margin-bottom: 0.5rem; font-size: 0.95rem; color: var(--muted); }
.picker .chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.75rem;
  padding: 0 1rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  cursor: pointer;
}
.chip input { width: 1.1rem; height: 1.1rem; accent-color: var(--ink); }
.chip:has(input:checked) { border-color: var(--ink); background: var(--card); }
.chip:has(input:focus-visible) { outline: 2px solid var(--ink); outline-offset: 3px; }
.chip input:focus-visible { outline: none; }
.family-reset {
  min-height: 2.75rem;
  padding: 0 1.1rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
}
.family-reset:hover { border-color: var(--ink); }
.family-flow .start { display: none; max-width: 42rem; margin: 0.75rem 0 0; color: var(--muted); }
.family-flow .start strong { color: var(--ink); font-weight: 600; }
.family-stages { list-style: none; margin: 1.5rem 0 0; padding: 0; }
.family-stages > li { border-top: 1px solid var(--line); }
.family-stages > li:last-child { border-bottom: 1px solid var(--line); }
.family-stages > li {
  --bar: var(--stage);
  --barw: 3px;
  --letter: var(--stage);
  --name: var(--ink);
  --tint: transparent;
}
.family-stages details { background: var(--tint); border-radius: 0.5rem; }
.family-stages summary {
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr) 1.5rem;
  grid-template-rows: auto auto;
  gap: 0 1rem;
  align-items: start;
  min-height: 2.75rem;
  padding: 1rem 0;
  cursor: pointer;
  list-style: none;
}
.family-stages summary::-webkit-details-marker { display: none; }
.family-stages summary:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
.family-stages .letter {
  grid-row: 1 / span 2;
  font-family: var(--font-mono);
  font-size: 1.375rem;
  font-weight: 600;
  line-height: 1.15;
  color: var(--letter);
}
.family-stages h3 {
  margin: 0 0 0.25rem;
  font-family: var(--font-sans);
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--name);
}
.family-stages .line {
  grid-column: 2;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--muted);
}
.family-stages .chev {
  grid-column: 3;
  grid-row: 1 / span 2;
  width: 0.6rem;
  height: 0.6rem;
  margin-top: 0.4rem;
  border-right: 2px solid var(--muted);
  border-bottom: 2px solid var(--muted);
  transform: rotate(45deg);
}
.family-stages details[open] .chev { transform: rotate(-135deg); margin-top: 0.7rem; }
/* An open stage is marked in its own colour: a thicker bar and a faint tint, so the one
   being read stands out from the five that are not. A picked profile's rules come later
   and are more specific, so they still win for the stages that profile owns. */
.family-stages > li:has(> details[open]) {
  --barw: 5px;
  --tint: color-mix(in srgb, var(--stage) 6%, transparent);
}
.family-stages .more {
  padding: 0 0 1rem 3.5rem;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.5;
}
.family-stages .facts > div, .family-stages .routes > div {
  display: flex;
  flex-wrap: wrap;
  gap: 0 0.75rem;
  padding: 0.25rem 0;
}
.family-stages dt { min-width: 7.5rem; color: var(--muted); }
.family-stages .routes dt { min-width: 9.5rem; }
.family-stages dd { flex: 1 1 12rem; min-width: 0; }
.family-stages .routes-head { margin: 0.75rem 0 0.25rem; color: var(--muted); }
.family-stages .note {
  display: none;
  padding: 0 0 0.75rem 3.5rem;
  font-family: var(--font-sans);
  font-size: 0.9rem;
  color: var(--muted);
}
.family-checks { list-style: none; margin: 0.5rem 0 1rem; padding: 0; }
.family-checks li { border-bottom: 1px solid var(--line); }
.family-checks .check {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 2.75rem;
  padding: 0.35rem 0;
  cursor: pointer;
}
.family-checks input { flex: none; width: 1.25rem; height: 1.25rem; accent-color: var(--stage); }
.family-checks .k { font-weight: 600; color: var(--stage); }
.family-example .example-stage {
  margin-top: 2.5rem;
  padding-left: 1rem;
  border-left: 3px solid var(--stage);
}
.family-example h2 {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin: 0 0 0.5rem;
  font-family: var(--font-sans);
  font-size: 1.5rem;
  font-weight: 500;
}
.family-example h2 .letter { font-family: var(--font-mono); font-weight: 600; color: var(--stage); }
.family-example p { margin: 0 0 0.75rem; }
.family-example .ran { color: var(--muted); }
.family-profiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 1rem;
  margin: 0 0 2rem;
  padding: 0;
  list-style: none;
}
.family-profiles > li {
  border: 1px solid var(--line);
  border-radius: 0.75rem;
  padding: 1rem;
}
.family-profiles h3 {
  margin: 0 0 0.35rem;
  font-family: var(--font-sans);
  font-size: 1rem;
  font-weight: 600;
}
.family-profiles p {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--muted);
}
/* Each FAMILY stage owns a colour, so the typed word, the timeline and the stage letters
   read as one sequence. Day values hold 4.5:1 against --bg; night lifts them for black;
   the console theme stays one colour, which is its whole point. */
:root {
  --stage-f: #b42318;
  --stage-a: #a14a06;
  --stage-m: #25713a;
  --stage-i: #0b6680;
  --stage-l: #3348c2;
  --stage-y: #7a35b5;
}
html[data-theme="night"] {
  --stage-f: #ff8a7a;
  --stage-a: #ffae5c;
  --stage-m: #6fd38a;
  --stage-i: #5ccbe6;
  --stage-l: #93a8ff;
  --stage-y: #c79cff;
}
html[data-theme="reactor"] {
  --stage-f: var(--ink);
  --stage-a: var(--ink);
  --stage-m: var(--ink);
  --stage-i: var(--ink);
  --stage-l: var(--ink);
  --stage-y: var(--ink);
}
.stage-f { --stage: var(--stage-f); }
.stage-a { --stage: var(--stage-a); }
.stage-m { --stage: var(--stage-m); }
.stage-i { --stage: var(--stage-i); }
.stage-l { --stage: var(--stage-l); }
.stage-y { --stage: var(--stage-y); }
.family-word {
  font-size: clamp(3rem, 13vw, 6rem);
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
.family-word .fl { display: inline-block; color: var(--stage); }
.family-word .fl .fk { display: inline-block; font-weight: inherit; }
.family-word .fl .fd { display: inline-block; font-style: normal; color: var(--ink); }
.family-word .caret {
  display: inline-block;
  width: 0.08em;
  height: 0.8em;
  margin-left: 0.06em;
  vertical-align: -0.02em;
  background: var(--ink);
  opacity: 0;
}
.family-link { margin-top: 1rem; font-size: 1rem; }
.family-link a {
  color: var(--ink);
  text-decoration: underline;
  text-underline-offset: 0.2em;
}
.family-stages > li { position: relative; }
.family-stages > li::before {
  content: "";
  position: absolute;
  left: -0.75rem;
  top: 1rem;
  bottom: 1rem;
  width: var(--barw);
  border-radius: 3px;
  background: var(--bar);
}
/* Picking a profile highlights the stages it owns and mutes the rest. Muting changes
   colour and not opacity, so the text left over still holds its contrast. A stage a
   profile only pushes into keeps its normal look and gains a line of its own. */
@@PROFILE_RULES@@
@media (prefers-reduced-motion: no-preference) {
  .family-word .fl .fk, .family-word .fl .fd {
    max-width: 0;
    opacity: 0;
    overflow: hidden;
    vertical-align: bottom;
    animation: family-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) forwards;
  }
  .family-word .fl:nth-child(1) .fk { animation-delay: 0.2s; }
  .family-word .fl:nth-child(1) .fd { animation-delay: 0.38s; }
  .family-word .fl:nth-child(2) .fk { animation-delay: 0.56s; }
  .family-word .fl:nth-child(2) .fd { animation-delay: 0.74s; }
  .family-word .fl:nth-child(3) .fk { animation-delay: 0.92s; }
  .family-word .fl:nth-child(3) .fd { animation-delay: 1.1s; }
  .family-word .fl:nth-child(4) .fk { animation-delay: 1.28s; }
  .family-word .fl:nth-child(4) .fd { animation-delay: 1.46s; }
  .family-word .fl:nth-child(5) .fk { animation-delay: 1.64s; }
  .family-word .fl:nth-child(5) .fd { animation-delay: 1.82s; }
  .family-word .fl:nth-child(6) .fk { animation-delay: 2s; }
  .family-word .fl:nth-child(6) .fd { animation-delay: 2.18s; }
  .family-word .caret { animation: family-caret 0.9s steps(1) 0s 4; }
  .family-word + .lede, .family-stages > li {
    opacity: 0;
    animation: family-rise 0.6s ease-out forwards;
  }
  .family-word + .lede { animation-delay: 2.4s; }
  .family-stages > li:nth-child(1) { animation-delay: 2.55s; }
  .family-stages > li:nth-child(2) { animation-delay: 2.65s; }
  .family-stages > li:nth-child(3) { animation-delay: 2.75s; }
  .family-stages > li:nth-child(4) { animation-delay: 2.85s; }
  .family-stages > li:nth-child(5) { animation-delay: 2.95s; }
  .family-stages > li:nth-child(6) { animation-delay: 3.05s; }
  /* A row is focusable before its rise begins; focus must never land on an invisible control.
     An important opacity outranks the animation without touching it: changing `animation`
     on focus and back on blur would restart the rise, and the row would vanish for a second. */
  .family-stages > li:focus-within { opacity: 1 !important; }
  /* Opening a stage. Only what is inside the row moves, never the row itself, so the
     entrance above cannot replay. The panel grows to its height where the browser can
     animate to auto (::details-content and interpolate-size); elsewhere those rules are
     ignored and it opens at once, with the rows below still fading in. */
  .family-stages { interpolate-size: allow-keywords; }
  .family-stages details::details-content {
    height: 0;
    overflow: clip;
    transition: height 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), content-visibility 0.4s allow-discrete;
  }
  .family-stages details[open]::details-content { height: auto; }
  .family-stages details { transition: background-color 0.35s ease; }
  .family-stages > li::before { transition: width 0.3s ease, background-color 0.3s ease; }
  .family-stages .chev {
    transition: transform 0.35s cubic-bezier(0.2, 0.9, 0.25, 1.2), margin-top 0.35s ease;
  }
  .family-stages details[open] .letter {
    transform-origin: 30% 60%;
    animation: family-pop 0.45s cubic-bezier(0.2, 0.9, 0.25, 1.4);
  }
  .family-stages details[open] .facts > div,
  .family-stages details[open] .routes-head,
  .family-stages details[open] .routes > div {
    animation: family-open 0.4s ease-out both;
  }
  .family-stages details[open] .facts > div:nth-child(2) { animation-delay: 0.05s; }
  .family-stages details[open] .facts > div:nth-child(3) { animation-delay: 0.1s; }
  .family-stages details[open] .routes-head { animation-delay: 0.15s; }
  .family-stages details[open] .routes > div:nth-child(1) { animation-delay: 0.2s; }
  .family-stages details[open] .routes > div:nth-child(2) { animation-delay: 0.25s; }
  .family-stages details[open] .routes > div:nth-child(3) { animation-delay: 0.3s; }
  .family-stages details[open] .routes > div:nth-child(n + 4) { animation-delay: 0.35s; }
}
@keyframes family-open {
  from { opacity: 0; transform: translateY(-0.4rem); }
  to { opacity: 1; transform: none; }
}
@keyframes family-pop {
  0% { transform: none; }
  40% { transform: scale(1.35); }
  100% { transform: none; }
}
@keyframes family-key {
  0% { max-width: 0; opacity: 0; transform: translateY(0.18em) scale(1.6); }
  1% { max-width: 1em; }
  100% { max-width: 1em; opacity: 1; transform: none; }
}
@keyframes family-caret {
  0% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes family-rise {
  from { opacity: 0; transform: translateY(0.5rem); }
  to { opacity: 1; transform: none; }
}
"""

PROFILES = ("solo", "developer", "qa", "team")


def _profile_rules() -> str:
    """The CSS for the profile picker, one block per profile.

    ``:has()`` reads the checked radio, so no script is involved. An attribute selector
    cannot compare a radio's value with a list on another element, so the four blocks
    are written out rather than looped over in the stylesheet.
    """
    rules = []
    for profile in PROFILES:
        on = f'.family-flow:has(input[value="{profile}"]:checked)'
        rules.append(
            f'{on} .start[data-for="{profile}"] {{ display: block; }}\n'
            f'{on} .family-stages > li[data-own~="{profile}"] {{\n'
            "  --barw: 6px;\n"
            "  --tint: color-mix(in srgb, var(--stage) 8%, transparent);\n"
            "}\n"
            f'{on} .family-stages > li:not([data-own~="{profile}"])'
            f':not([data-feeds~="{profile}"]) {{\n'
            "  --bar: var(--line);\n"
            "  --letter: var(--muted);\n"
            "  --name: var(--muted);\n"
            "}\n"
            f'{on} .family-stages .note[data-for="{profile}"] {{ display: block; }}'
        )
    return "\n".join(rules)


# One motion language for the whole site, kept in one place so every control moves the
# same way: short ease-out curves for things that appear, a slight overshoot only for a
# press or a tick, and nothing that loops. What a visitor needs to see (an underline on
# hover, the arrow on a row) is styled for everyone; only the movement between states
# sits behind prefers-reduced-motion, so a visitor who asked for less still gets every
# cue, just without the travel.
MOTION_CSS = """
:root {
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --ease-press: cubic-bezier(0.2, 0.9, 0.25, 1.35);
  --ease-theme: cubic-bezier(0.3, 0, 0.15, 1);
}
/* The radius of the theme reveal, registered so it can be animated: the soft edge of the
   new theme is a gradient mask that grows with it. */
@property --reveal-r {
  syntax: "<length>";
  inherits: false;
  initial-value: 0px;
}
/* Links in the header and the footer draw their underline from the left. */
.bar nav a, .foot nav a {
  background: linear-gradient(currentColor, currentColor) no-repeat 0 calc(50% + 0.8em) / 0 1px;
}
.bar nav a:hover, .foot nav a:hover, .bar nav a:focus-visible, .foot nav a:focus-visible {
  background-size: 100% 1px;
}
.bar nav a[aria-current="page"], .foot nav a[aria-current="page"] { background-size: 0 1px; }
/* A row in a skill list points where it goes. */
.skills a::after {
  content: "\\2192";
  margin-left: auto;
  padding-left: 1rem;
  color: var(--muted);
  opacity: 0;
}
.skills a:hover::after, .skills a:focus-visible::after { opacity: 1; }
@media (prefers-reduced-motion: no-preference) {
  /* Moving between pages: the header holds still while the page under it rises in. */
  @view-transition { navigation: auto; }
  .site-header { view-transition-name: banner; }
  ::view-transition-old(banner) { display: none; }
  ::view-transition-new(banner) { animation: none; }
  ::view-transition-old(root) { animation: page-out 160ms var(--ease) both; }
  ::view-transition-new(root) { animation: page-in 320ms var(--ease) both; }
  a, button {
    transition: color 160ms ease, background-color 160ms ease, opacity 160ms ease,
      background-size 280ms var(--ease), text-decoration-color 200ms ease,
      transform 200ms var(--ease), box-shadow 200ms var(--ease), outline-offset 160ms ease;
  }
  :focus-visible { outline-offset: 3px; }
  .skills a { transition: color 160ms ease, padding-left 240ms var(--ease); }
  .skills a::after {
    transform: translateX(-0.5rem);
    transition: opacity 200ms ease, transform 240ms var(--ease);
  }
  .skills a:hover::after, .skills a:focus-visible::after { transform: none; }
  #home { transition: letter-spacing 320ms var(--ease); }
  @media (hover: hover) {
    .skills a:hover { padding-left: 0.4rem; }
    #home:hover { letter-spacing: 0.3em; }
    .pill:hover, .family-reset:hover, .chip:hover, .tool:hover {
      transform: translateY(-1px);
      box-shadow: 0 0.5rem 1.25rem -0.75rem color-mix(in srgb, var(--ink) 55%, transparent);
    }
  }
  .pill:active, .family-reset:active, .chip:active, .tool:active {
    transform: scale(0.96);
    box-shadow: none;
    transition-duration: 80ms;
  }
  /* A choice the visitor has just made ticks in; one restored on load does not. */
  .chip input:checked:focus, .family-checks input:checked:focus {
    animation: tick 320ms var(--ease-press);
  }
  .family-checks .check { transition: color 200ms ease; }
  /* Rows the finder brings back fade in rather than appearing at once. */
  .filtered [data-name], .filtered [data-plugin], .filtered .hits {
    transition: opacity 240ms var(--ease), translate 240ms var(--ease);
  }
  @starting-style {
    .filtered [data-name], .filtered [data-plugin], .filtered .hits {
      opacity: 0;
      translate: 0 0.4rem;
    }
  }
  /* On the front page the card and each plugin rise in as they scroll into view. */
  @supports (animation-timeline: view()) {
    .listing .card, .listing .plugin {
      animation: rise-in linear both;
      animation-timeline: view();
      animation-range: entry 0% entry 60%;
    }
  }
  /* Switching theme spreads the new one out from the switch that was pressed. */
  html.theming .site-header { view-transition-name: none; }
  html.theming::view-transition-old(root) { animation: none; }
  html.theming::view-transition-new(root) {
    -webkit-mask-image: radial-gradient(
      circle at var(--reveal-x, 100%) var(--reveal-y, 0),
      #000 calc(var(--reveal-r) - 16vmax), transparent var(--reveal-r)
    );
    mask-image: radial-gradient(
      circle at var(--reveal-x, 100%) var(--reveal-y, 0),
      #000 calc(var(--reveal-r) - 16vmax), transparent var(--reveal-r)
    );
    animation: theme-in 900ms var(--ease-theme) both;
  }
  /* Where a browser has no view transitions, the colours cross-fade instead of jumping. */
  html.theme-fade, html.theme-fade * {
    transition: background-color 500ms ease, color 500ms ease, border-color 500ms ease,
      fill 500ms ease, stroke 500ms ease !important;
  }
  /* More specific, so the knob keeps its glide and the icons their turn during the fade. */
  html.theme-fade .knob {
    transition: transform 600ms var(--ease-theme), background-color 600ms ease,
      color 600ms ease !important;
  }
  html.theme-fade .knob svg {
    transition: opacity 400ms ease, transform 600ms var(--ease-theme) !important;
  }
}
@keyframes page-out { to { opacity: 0; } }
@keyframes page-in { from { opacity: 0; transform: translateY(0.75rem); } }
@keyframes rise-in { from { opacity: 0; transform: translateY(1.5rem); } }
@keyframes tick {
  0% { transform: scale(1); }
  45% { transform: scale(1.3); }
  100% { transform: scale(1); }
}
@keyframes theme-in {
  from { --reveal-r: 0px; }
  to { --reveal-r: 180vmax; }
}
"""

# ------------------------------------------------------------------ the plugin pages
#
# Every plugin page except /family/ (which is hand-drawn on its own) gets the same frame:
# the plugin's name in large capitals, one span per letter coloured from a palette that
# cycles, and a slim accent bar on each skill row in the same cycle. What differs is the
# palette and one entrance, chosen to fit what the plugin is for. All of it lives in this
# one table; the CSS is generated from it so ten plugins do not mean ten copies of the
# sizing, colour-cycling and accent-bar rules.
#
# Colours are held to 4.5:1 against the page: day values against --bg in day (#f4f1ea),
# night values against --bg in night (#000000). The console theme collapses every colour
# to --ink, as it does for the FAMILY stages. tests/test_catalogue_site.py recomputes the
# ratios from this table, so a colour edited by eye cannot slip under the floor.
#
# The finished heading is the element's own style: every entrance runs with a backwards
# fill inside the no-preference query, so a visitor who asked for less motion, a browser
# that does not run the animation, or a page with scripts off all see the whole word.
# `%P` stands for the plugin's page class, `--i` for a letter's position from 1, `--n` for
# the number of letters.


class PluginLook(NamedTuple):
    day: tuple[str, ...]
    night: tuple[str, ...]
    width: float  # em one capital takes in the heading's face, spacing included
    rules: str  # the entrance, written inside the no-preference query
    keyframes: str  # what the entrance animates, written outside it
    still: str = ""  # rules that hold whatever the motion setting
    caret: bool = False  # the entrance types, so the heading ends in a caret
    serif: bool = False  # the heading is set in the serif face


PLUGIN_LOOKS: dict[str, PluginLook] = {
    # Typed one key at a time, the caret trailing the last letter.
    "coding": PluginLook(
        day=("#1d4ed8", "#4338ca", "#0f766e"),
        night=("#8ab4ff", "#a5a0ff", "#4fd1c5"),
        width=0.66,
        caret=True,
        still="%P .plugin-word { font-family: var(--font-mono); font-weight: 700; }",
        rules="""\
%P .pl { animation: pw-coding-key 0.12s steps(1, start) calc(var(--i) * 0.16s) backwards; }
%P .caret {
  display: inline-block;
  width: 0.08em;
  height: 0.8em;
  margin-left: 0.06em;
  vertical-align: -0.02em;
  background: var(--ink);
  opacity: 0;
  animation: pw-coding-blink 0.8s steps(1) 0s 6;
}""",
        keyframes="""\
@keyframes pw-coding-key {
  from { max-width: 0; opacity: 0; }
  to { max-width: 1em; opacity: 1; }
}
@keyframes pw-coding-blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
}""",
    ),
    # A pulse that travels across the word, each letter lifting a beat after the last.
    "operations": PluginLook(
        day=("#14753a", "#0f766e", "#3f6212"),
        night=("#4ade80", "#2dd4bf", "#a3e635"),
        width=0.72,
        rules="%P .pl { animation: pw-operations-beat 0.9s ease-out calc(var(--i) * 0.09s) "
        "backwards; }",
        keyframes="""\
@keyframes pw-operations-beat {
  0% { opacity: 0; transform: translateY(0.5em); }
  28% { opacity: 1; transform: translateY(-0.22em); }
  42% { transform: translateY(0.06em); }
  58% { transform: translateY(-0.12em); }
  78% { transform: translateY(0.02em); }
  100% { opacity: 1; transform: none; }
}""",
    ),
    # Letters travel in along a line, then the line they ran on fills in underneath.
    "delivery": PluginLook(
        day=("#a05400", "#b4400c", "#8a5a00"),
        night=("#ffb347", "#ff8c4a", "#ffcc4d"),
        width=0.7,
        still="""\
%P .plugin-word { width: fit-content; max-width: 100%; }
%P .plugin-word::after {
  content: "";
  display: block;
  height: 0.07em;
  margin-top: 0.12em;
  border-radius: 0.04em;
  background: linear-gradient(90deg, var(--delivery-1), var(--delivery-2), var(--delivery-3));
  transform-origin: left center;
}""",
        rules="""\
%P .pl { animation: pw-delivery-slide 0.5s var(--ease) calc(var(--i) * 0.1s) backwards; }
%P .plugin-word::after {
  animation: pw-delivery-fill 0.7s ease-out calc(var(--n) * 0.1s + 0.35s) backwards;
}""",
        keyframes="""\
@keyframes pw-delivery-slide {
  from { opacity: 0; transform: translateX(-1.4em); }
  to { opacity: 1; transform: none; }
}
@keyframes pw-delivery-fill {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}""",
    ),
    # Letters fall in and bounce frame by frame, like a sprite. steps() applies to each
    # keyframe interval, not the whole animation, so the frames are written out and each
    # is held with steps(1): even 75ms frames and no half-transparent ghosts. The fall is
    # capped at 1.25rem because only 1.5rem separates the heading from the Back link.
    "gamedev": PluginLook(
        day=("#b0198f", "#6d28d9", "#0e7490"),
        night=("#ff7ae0", "#b69cff", "#22d3ee"),
        width=0.79,
        rules="%P .pl { --drop: min(0.6em, 1.25rem); animation: pw-gamedev-drop 0.6s "
        "steps(1, end) calc(var(--i) * 0.075s) backwards; }",
        keyframes="""\
@keyframes pw-gamedev-drop {
  0% { opacity: 0; transform: translateY(calc(var(--drop) * -1)); }
  12.5% { opacity: 1; transform: translateY(calc(var(--drop) * -1)); }
  25% { opacity: 1; transform: translateY(calc(var(--drop) * -0.5)); }
  37.5% { opacity: 1; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(calc(var(--drop) * -0.25)); }
  62.5% { opacity: 1; transform: translateY(0); }
  75% { opacity: 1; transform: translateY(calc(var(--drop) * -0.1)); }
  87.5% { opacity: 1; transform: translateY(0); }
  100% { opacity: 1; transform: none; }
}""",
    ),
    # A solid bar sits on each letter and shrinks away to show it, as a redaction lifts.
    "security": PluginLook(
        day=("#b91c1c", "#7f1d1d", "#be123c"),
        night=("#ff6b6b", "#ff8a80", "#ff5c8a"),
        width=0.7,
        rules="""\
%P .pl { position: relative; }
%P .pl::after {
  content: "";
  position: absolute;
  inset: 0.1em -0.02em 0.06em;
  background: var(--ink);
  transform: scaleX(0);
  transform-origin: right center;
  animation: pw-security-lift 0.45s cubic-bezier(0.7, 0, 0.3, 1)
    calc(var(--i) * 0.12s + 0.2s) backwards;
}""",
        keyframes="""\
@keyframes pw-security-lift {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}""",
    ),
    # Steady and level: the row settles into place one letter after another.
    "manager": PluginLook(
        day=("#1e3a8a", "#334e68", "#3b5b9a"),
        night=("#8fb0ff", "#9fb3c8", "#7aa2f7"),
        width=0.79,
        rules="%P .pl { animation: pw-manager-settle 0.6s ease-out calc(var(--i) * 0.12s) "
        "backwards; }",
        keyframes="""\
@keyframes pw-manager-settle {
  from { opacity: 0; transform: scale(0.85); }
  to { opacity: 1; transform: none; }
}""",
    ),
    # Set by hand: each letter lands a little crooked and straightens.
    "personal": PluginLook(
        day=("#be3a5a", "#a8472c", "#9f2f4a"),
        night=("#ff8fa8", "#ff9f7a", "#f2a0b5"),
        width=0.76,
        serif=True,
        still="""\
html:not([data-theme="reactor"]) %P .plugin-word {
  font-family: var(--font-serif);
  font-weight: 500;
  letter-spacing: 0.04em;
}""",
        rules="""\
%P .pl:nth-child(odd) { --tilt: -7deg; }
%P .pl:nth-child(even) { --tilt: 6deg; }
%P .pl {
  transform-origin: 50% 90%;
  animation: pw-personal-set 0.8s ease-out calc(var(--i) * 0.11s) backwards;
}""",
        keyframes="""\
@keyframes pw-personal-set {
  from { opacity: 0; transform: rotate(var(--tilt)) translateY(0.12em); }
  to { opacity: 1; transform: none; }
}""",
    ),
    # Each letter starts lower than the one before and climbs to the line.
    "career": PluginLook(
        day=("#856500", "#92561a", "#7a5200"),
        night=("#f2c14e", "#e0a066", "#d4a44a"),
        width=0.74,
        rules="%P .pl { animation: pw-career-climb 0.6s var(--ease) calc(var(--i) * 0.12s) "
        "backwards; }",
        keyframes="""\
@keyframes pw-career-climb {
  from { opacity: 0; transform: translateY(calc(var(--i) * 0.2em)); }
  to { opacity: 1; transform: none; }
}""",
    ),
    # A swatch card per letter, each in its own hue, popping to size.
    "design": PluginLook(
        day=("#c4281c", "#946400", "#137a38", "#0e7490", "#4338ca", "#a21caf"),
        night=("#ff7a7a", "#f5c542", "#6fdc8c", "#4fd1e6", "#9aa8ff", "#e08cff"),
        width=0.7,
        rules="%P .pl { animation: pw-design-swatch 0.5s cubic-bezier(0.3, 1.5, 0.5, 1) "
        "calc(var(--i) * 0.1s) backwards; }",
        keyframes="""\
@keyframes pw-design-swatch {
  from { opacity: 0; transform: scale(0); }
  to { opacity: 1; transform: none; }
}""",
    ),
    # A token being sampled: each letter flickers up out of a blur and settles sharp.
    "llm": PluginLook(
        day=("#0369a1", "#7e22ce", "#047857"),
        night=("#38bdf8", "#c084fc", "#34d399"),
        width=0.68,
        rules="%P .pl { animation: pw-llm-sample 0.7s ease-out calc(var(--i) * 0.2s) backwards; }",
        keyframes="""\
@keyframes pw-llm-sample {
  0% { opacity: 0; filter: blur(0.3em); }
  30% { opacity: 0.7; filter: blur(0.18em); }
  45% { opacity: 0.25; filter: blur(0.12em); }
  70% { opacity: 0.9; filter: blur(0.05em); }
  100% { opacity: 1; filter: none; }
}""",
    ),
    # Rows rise into place one after another, like a query result filling in.
    "data": PluginLook(
        day=("#1e40af", "#9a3412", "#065f46"),
        night=("#93c5fd", "#fdba74", "#6ee7b7"),
        width=0.7,
        rules="%P .pl { animation: pw-data-row 0.45s ease-out calc(var(--i) * 0.11s) backwards; }",
        keyframes="""\
@keyframes pw-data-row {
  from { opacity: 0; transform: translateY(0.35em); }
  to { opacity: 1; transform: none; }
}""",
    ),
}

# The shared frame. `--c` is the colour a letter or a row takes from the cycle.
# The heading is sized against the viewport less the page's 2.5rem of padding and 1rem
# more, since 100vw also counts a desktop scrollbar the page cannot draw into.
PLUGIN_BASE_CSS = """\
.plugin-word {
  font-size: clamp(2rem, calc((100vw - 3.5rem) / (var(--n) * var(--w))), 6rem);
  line-height: 1.05;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
.plugin-word .pl { display: inline-block; color: var(--c); }
.plugin-word .caret { display: none; }
.plugin-page .skills > li {
  --barw: 3px;
  position: relative;
  padding-left: 1rem;
}
.plugin-page .skills > li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.6rem;
  bottom: 0.6rem;
  width: var(--barw);
  border-radius: 3px;
  background: var(--c);
}
.plugin-page .skills > li:hover, .plugin-page .skills > li:focus-within { --barw: 8px; }
"""

PLUGIN_BASE_MOTION_CSS = """\
  .plugin-page .skills > li::before { transition: width 0.25s var(--ease); }
"""


def plugin_class(plugin: str) -> str:
    """The class a plugin's page carries, which every rule of its look is scoped to."""
    return f"plugin-{plugin}"


def _plugin_css() -> str:
    """The stylesheet for every plugin look, generated from ``PLUGIN_LOOKS``."""
    longest = max(len(name) for name in PLUGIN_LOOKS)
    day, night, console, scoped, rules, frames = [], [], [], [], [], []
    for name, look in PLUGIN_LOOKS.items():
        page = f".{plugin_class(name)}"
        size = len(look.day)
        for index, (by_day, by_night) in enumerate(zip(look.day, look.night, strict=True), 1):
            day.append(f"  --{name}-{index}: {by_day};")
            night.append(f"  --{name}-{index}: {by_night};")
            console.append(f"  --{name}-{index}: var(--ink);")
        scoped.append(f"{page} {{ --n: {len(name)}; --w: {look.width}; }}")
        for index in range(1, size + 1):
            scoped.append(
                f"{page} :is(.pl, .skills > li):nth-child({size}n + {index % size}) "
                f"{{ --c: var(--{name}-{index}); }}"
            )
        if look.still:
            scoped.append(look.still.replace("%P", page))
        rules.append(look.rules.replace("%P", page))
        frames.append(look.keyframes)
    letters = "\n".join(
        f".plugin-word .pl:nth-child({i}) {{ --i: {i}; }}" for i in range(1, longest + 1)
    )
    motion = "\n".join(
        "  " + line if line else line
        for line in (PLUGIN_BASE_MOTION_CSS.rstrip("\n") + "\n" + "\n".join(rules)).splitlines()
    )
    return (
        ":root {\n" + "\n".join(day) + "\n}\n"
        'html[data-theme="night"] {\n' + "\n".join(night) + "\n}\n"
        'html[data-theme="reactor"] {\n'
        + "\n".join(console)
        + "\n}\n"
        + PLUGIN_BASE_CSS
        + letters
        + "\n"
        + "\n".join(scoped)
        + "\n@media (prefers-reduced-motion: no-preference) {\n"
        + motion
        + "\n}\n"
        + "\n".join(frames)
        + "\n"
    )


# The routing graph on a plugin page (see site_graph). `--rg` is the colour of its lines
# and borders: the plugin's first look colour where it has one, so the drawing follows the
# day, night and console palettes without an inline style. The drawing is hidden below
# 40rem and the list beside it carries the page, because a scaled-down label is unreadable.
GRAPH_CSS = """\
.rg { --rg: var(--ink); margin-top: 3rem; }
.rg-title { font-size: 1.5rem; line-height: 1.2; font-weight: 500; letter-spacing: -0.02em; }
.rg-note { max-width: 42rem; margin-top: 0.5rem; color: var(--muted); }
.rg-map { display: none; margin-top: 1.5rem; }
.rg-svg { max-width: 100%; height: auto; }
.rg-edge { fill: none; stroke: var(--rg); stroke-width: 1.5; }
.rg-head { fill: var(--rg); }
.rg-node { fill: var(--card); stroke: var(--rg); stroke-width: 1.5; }
.rg-agent .rg-node { stroke-dasharray: 5 3; }
.rg-text { fill: var(--ink); font: 13px var(--font-mono); }
.rg-label { fill: var(--muted); font: 600 12px var(--font-sans); letter-spacing: 0.04em; }
.rg-list { display: grid; gap: 0.5rem; margin-top: 1.5rem; }
.rg-list a { text-decoration: underline; text-underline-offset: 4px; }
.rg-list code { font-size: 0.9375rem; }
@media (min-width: 40rem) {
  .rg-map { display: block; }
}
"""


def _graph_css() -> str:
    """The graph rules, then one line per look binding `--rg` to that plugin's colour."""
    colours = "\n".join(
        f".{plugin_class(name)} .rg {{ --rg: var(--{name}-1); }}" for name in PLUGIN_LOOKS
    )
    return GRAPH_CSS + colours + "\n"


CSS = (
    CSS.replace("@@PROFILE_RULES@@", _profile_rules()).replace("@@FONT_FACES@@", FONT_FACES.strip())
    + _plugin_css()
    + _graph_css()
    + MOTION_CSS
)

# The theme is set before the page paints, so a visitor at night never sees a flash of
# paper. This is the clock rule and the stored choice, nothing else.
HEAD_SCRIPT = (
    '(function(){var t=null;try{t=localStorage.getItem("theme")}catch(e){}'
    "var h=new Date().getHours();"
    'var theme=t==="reactor"?"reactor":t==="night"||(t!=="day"&&(h>=20||h<6))?"night":"day";'
    'document.documentElement.setAttribute("data-theme",theme);})();'
)

PAGE_SCRIPT = """
(function () {
  var KEY = "theme";
  var COLORS = { day: "#f4f1ea", night: "#000000", reactor: "#070807" };
  var root = document.documentElement;
  var meta = document.querySelector('meta[name="theme-color"]');
  var dark = document.getElementById("dark-switch");
  var consoleTheme = document.getElementById("console-theme");
  function isNight(hour) { return hour >= 20 || hour < 6; }
  function clock() { return isNight(new Date().getHours()) ? "night" : "day"; }
  function preferred() {
    var stored = null;
    try { stored = localStorage.getItem(KEY); } catch (e) {}
    return stored === "night" || stored === "day" || stored === "reactor" ? stored : clock();
  }
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    if (meta) meta.setAttribute("content", COLORS[theme]);
    dark.setAttribute("aria-checked", theme === "night" ? "true" : "false");
    consoleTheme.setAttribute("aria-pressed", theme === "reactor" ? "true" : "false");
  }
  function store(value) {
    try {
      if (value) localStorage.setItem(KEY, value);
      else localStorage.removeItem(KEY);
    } catch (e) {}
  }
  // A theme chosen by hand spreads out from the control that chose it. The clock's own
  // changes, and any visitor who asked for less motion, switch at once.
  var fadeTimer = 0;
  var spreading = null;
  function spreadTheme(from, change) {
    var still = !window.matchMedia ||
      !window.matchMedia("(prefers-reduced-motion: no-preference)").matches;
    if (still) { change(); return; }
    if (!document.startViewTransition) {
      // A second change while the first still fades restarts the clock, so the class is
      // never removed in the middle of the newer fade.
      root.classList.add("theme-fade");
      change();
      window.clearTimeout(fadeTimer);
      fadeTimer = window.setTimeout(function () { root.classList.remove("theme-fade"); }, 600);
      return;
    }
    var box = from.getBoundingClientRect();
    root.style.setProperty("--reveal-x", Math.round(box.left + box.width / 2) + "px");
    root.style.setProperty("--reveal-y", Math.round(box.top + box.height / 2) + "px");
    root.classList.add("theming");
    // A new transition skips the one still running, whose cleanup then fires early; only
    // the latest one may remove the class, or the newer reveal loses its mask mid-way.
    var transition = document.startViewTransition(change);
    spreading = transition;
    function done() {
      if (spreading !== transition) return;
      spreading = null;
      root.classList.remove("theming");
    }
    transition.finished.then(done, done);
  }
  dark.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "night" ? "day" : "night";
    store(next);
    spreadTheme(dark, function () { apply(next); });
  });
  consoleTheme.addEventListener("click", function () {
    if (root.getAttribute("data-theme") === "reactor") {
      store(null);
      spreadTheme(consoleTheme, function () { apply(clock()); });
      return;
    }
    store("reactor");
    spreadTheme(consoleTheme, function () { apply("reactor"); });
  });
  apply(preferred());
  window.setInterval(function () { apply(preferred()); }, 60000);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") apply(preferred());
  });

  var home = document.getElementById("home");
  home.addEventListener("click", function (event) {
    if (window.location.pathname === "/") {
      event.preventDefault();
      window.scrollTo(0, 0);
    }
  });
  var banner = document.getElementById("banner");
  var last = window.scrollY;
  function away(on) {
    banner.classList.toggle("away", on);
    banner.inert = on;
  }
  window.addEventListener("scroll", function () {
    var y = window.scrollY;
    var delta = y - last;
    if (y <= 64) away(false);
    else if (delta > 8) away(true);
    else if (delta < -8) away(false);
    last = y;
  }, { passive: true });

  var backs = document.querySelectorAll("[data-back]");
  function back(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var from = "";
    try { from = new URL(document.referrer).origin; } catch (e) {}
    if (from !== window.location.origin || window.history.length < 2) return;
    event.preventDefault();
    window.history.back();
  }
  for (var b = 0; b < backs.length; b++) backs[b].addEventListener("click", back);

  var dock = document.getElementById("dock");
  var upward = document.getElementById("to-top");
  var still = window.matchMedia("(prefers-reduced-motion: reduce)");
  function edge() {
    var inline = document.querySelector("main .back");
    if (!inline) return 320;
    return inline.getBoundingClientRect().bottom + window.scrollY;
  }
  var limit = edge();
  // To top follows the header's rule: away while reading down, back on the way up,
  // when a reader wants it, and at the end of the page. A focused button stays, so
  // keyboard focus never lands on something hidden.
  var mark = window.scrollY;
  var shown = false;
  function reveal() {
    var y = window.scrollY;
    var past = y > limit;
    if (dock) dock.classList.toggle("on", past);
    var end = y + window.innerHeight >= document.documentElement.scrollHeight - 2;
    if (!past) shown = false;
    else if (end || document.activeElement === upward) shown = true;
    else if (y < mark - 8) shown = true;
    else if (y > mark + 8) shown = false;
    if (Math.abs(y - mark) > 8) mark = y;
    upward.classList.toggle("on", shown);
  }
  window.addEventListener("scroll", reveal, { passive: true });
  window.addEventListener("resize", function () { limit = edge(); reveal(); });
  reveal();
  upward.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: still.matches ? "auto" : "smooth" });
    // The button hides once the page is at the top, so focus moves to the home link,
    // in the header, which is inert while it is hidden.
    away(false);
    home.focus({ preventScroll: true });
  });

  var input = document.getElementById("find");
  var tally = document.getElementById("count");
  var none = document.getElementById("none");
  var list = document.getElementById("list");
  if (!input || !tally || !list) return;
  var finder = document.getElementById("finder");
  var sections = list.querySelectorAll("[data-plugin]");
  var rows = list.querySelectorAll("[data-name]");
  var searching = false;
  function refine() {
    var needle = input.value.trim().toLowerCase();
    if (needle && !searching && finder) finder.scrollIntoView({ block: "start" });
    searching = needle.length > 0;
    var shown = 0;
    var total = sections.length || rows.length;
    var unit = sections.length ? "plugins" : "skills";
    sections.forEach(function (section) {
      var plugin = section.getAttribute("data-plugin") || "";
      var blurb = section.getAttribute("data-blurb") || "";
      var skills = (section.getAttribute("data-skills") || "").split(" ").filter(Boolean);
      var inPlugin = plugin.indexOf(needle) !== -1;
      var matches = needle ? skills.filter(function (skill) {
        return skill.indexOf(needle) !== -1 || inPlugin;
      }) : [];
      var show = !needle || inPlugin || blurb.indexOf(needle) !== -1 || matches.length > 0;
      section.hidden = !show;
      if (show) shown += 1;
      var hits = section.querySelector(".hits");
      if (hits) {
        var listed = needle && matches.length > 0 && !inPlugin;
        hits.textContent = listed ? matches.slice(0, 6).join(" \\u00b7 ") : "";
        hits.hidden = !listed;
      }
    });
    rows.forEach(function (row) {
      var show = !needle || (row.getAttribute("data-name") || "").indexOf(needle) !== -1;
      row.hidden = !show;
      if (show) shown += 1;
    });
    tally.textContent = needle ? shown + " of " + total : total + " " + unit;
    if (none) none.hidden = shown !== 0;
  }
  input.addEventListener("input", function () {
    // Only rows the finder brings back fade in, never the list as the page first draws it.
    list.classList.add("filtered");
    refine();
  });
})();
"""

# The Run a slice checklist on /family/. Ticks are kept in one localStorage entry, a JSON
# list of the stage letters ticked, so the page remembers them without an account. Every
# storage call sits in a try, because a private window or a blocked store throws; the
# boxes still work then, they are just not remembered. It also stops Enter in the picker
# from submitting the form the Clear button needs.
FAMILY_SCRIPT = """
(function () {
  var KEY = "family-slice";
  var boxes = document.querySelectorAll("[data-gate]");
  var reset = document.querySelector("[data-slice-reset]");
  var picker = document.querySelector(".picker");
  if (picker) picker.addEventListener("submit", function (event) { event.preventDefault(); });
  if (!boxes.length) return;
  function load() {
    var list = [];
    try {
      var parsed = JSON.parse(localStorage.getItem(KEY) || "[]");
      if (Array.isArray(parsed)) list = parsed;
    } catch (e) {}
    return list;
  }
  function save() {
    var ticked = [];
    boxes.forEach(function (box) {
      if (box.checked) ticked.push(box.getAttribute("data-gate"));
    });
    try {
      if (ticked.length) localStorage.setItem(KEY, JSON.stringify(ticked));
      else localStorage.removeItem(KEY);
    } catch (e) {}
  }
  var saved = load();
  boxes.forEach(function (box) {
    box.checked = saved.indexOf(box.getAttribute("data-gate")) !== -1;
    box.addEventListener("change", save);
  });
  if (reset) reset.addEventListener("click", function () {
    boxes.forEach(function (box) { box.checked = false; });
    save();
  });
})();
"""
