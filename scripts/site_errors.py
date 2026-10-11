"""The pages a visitor lands on when something is missing or broken.

Two different things live here, because they fail differently.

The 404 is part of the site. Cloudflare serves the root ``404.html`` for every path that
has no asset, so it is built with the site's own header, footer and stylesheet through
``_page``; this module supplies what only it needs: a heading in the typed style of the
FAMILY page, the path the visitor asked for, and a "Did you mean" list worked out in the
browser from the real page paths embedded as JSON.

The pages under ``/errors/`` are not part of the site's chrome at all. A custom error
page is fetched once, by a service that is not a browser, and served in place of an
origin failure, so it cannot rely on anything else being reachable: every page here is
one file with its CSS and its few lines of script inline, no font, image, stylesheet or
script from anywhere, and each is far below the size those services allow. They use the
site's colours and the FAMILY stage colours, so they read as the same place.

Every animation sits inside ``prefers-reduced-motion: no-preference``, so a visitor who
asked for none gets the finished page and nothing that moves, and the page reads whole
without script.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass

# ---------------------------------------------------------------------- shared helpers


def json_for_script(value: object) -> str:
    """JSON that can sit inside a ``<script>`` element without ending it.

    ``json.dumps`` leaves ``<``, ``>`` and ``&`` alone, so a string holding ``</script>``
    would close the element and everything after it would be parsed as markup. Writing
    them as ``\\uXXXX`` escapes keeps the value identical to ``JSON.parse`` and takes
    the characters the HTML parser looks for out of the text. U+2028 and U+2029 are
    escaped as well so the block is valid in a script that evaluates it as a literal.
    """
    text = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
    for char, escape in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        text = text.replace(char, escape)
    return text


# ----------------------------------------------------------------------------- the 404

LOST_DIGITS = (("4", "f"), ("0", "i"), ("4", "y"))

LOST_CSS = """
/* The 404: the typed heading of the FAMILY page, in three of its stage colours. */
.lost-word {
  position: relative;
  font-size: clamp(5rem, 26vw, 9rem);
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.lost-word .typed { position: relative; display: inline-block; }
.lost-word .ld { display: inline-block; color: var(--stage); }
.lost-word .caret {
  display: inline-block;
  width: 0.07em;
  height: 0.78em;
  margin-left: 0.06em;
  vertical-align: -0.02em;
  background: var(--ink);
  opacity: 0;
}
.lost-word .typed::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, transparent 0 47%,
    color-mix(in srgb, var(--ink) 7%, transparent) 49.4%,
    color-mix(in srgb, var(--ink) 50%, transparent) 50%,
    color-mix(in srgb, var(--ink) 7%, transparent) 50.6%, transparent 53% 100%);
  background-size: 100% 300%;
  background-position: 0 100%;
  opacity: 0;
}
.lost-asked { margin-top: 1.5rem; max-width: 42rem; color: var(--muted); }
.lost-asked code {
  display: inline-block;
  max-width: 100%;
  padding: 0.125rem 0.5rem;
  border-radius: 0.5rem;
  background: var(--card);
  color: var(--ink);
  font-size: 0.9375rem;
  overflow-wrap: anywhere;
  vertical-align: baseline;
}
.lost-suggest { margin-top: 2.5rem; max-width: 42rem; }
.lost-suggest h2 {
  font-size: 0.875rem;
  line-height: 1.4286;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}
.lost-suggest ul { margin-top: 0.5rem; border-top: 1px solid var(--line); }
.lost-suggest li { border-bottom: 1px solid var(--line); }
.lost-suggest a {
  display: flex;
  min-height: 3.25rem;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0 1rem;
  padding: 0.75rem 0;
}
.lost-suggest a:hover .lost-name { text-decoration: underline; text-underline-offset: 4px; }
.lost-name { font-size: 1.125rem; font-weight: 500; overflow-wrap: anywhere; }
.lost-kind { font-size: 0.875rem; color: var(--muted); }
.lost-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 2.5rem;
}
.lost-links .pill { margin-top: 0; }
.lost-links .ghost {
  background: transparent;
  color: var(--ink);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 35%, transparent);
}
.lost-links .ghost:hover { background: color-mix(in srgb, var(--ink) 8%, transparent); opacity: 1; }
@media (prefers-reduced-motion: no-preference) {
  .lost-word .ld {
    max-width: 0;
    opacity: 0;
    overflow: hidden;
    vertical-align: bottom;
    animation: lost-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) forwards;
  }
  .lost-word .ld:nth-child(1) { animation-delay: 0.15s; }
  .lost-word .ld:nth-child(3) { animation-delay: 0.75s; }
  .lost-word .caret { animation: lost-caret 0.9s steps(1) 0s 4; }
  .lost-word .typed::after { animation: lost-scan 7s linear 1.4s infinite; }
  .lost-word .ld:nth-child(2) { animation: lost-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25)
    0.45s forwards, lost-glitch 7s steps(1) 4s infinite; }
  .lost-word ~ .lede, .lost-asked, .lost-links {
    opacity: 0;
    animation: lost-rise 0.6s ease-out 1.3s forwards;
  }
  .lost-asked { animation-delay: 1.45s; }
  .lost-links { animation-delay: 1.6s; }
  .lost-suggest:not([hidden]) { animation: lost-rise 0.6s ease-out 1.5s backwards; }
}
@keyframes lost-key {
  0% { max-width: 0; opacity: 0; transform: translateY(0.18em) scale(1.6); }
  1% { max-width: 1em; }
  100% { max-width: 1em; opacity: 1; transform: none; }
}
@keyframes lost-caret {
  0% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes lost-scan {
  0% { opacity: 1; background-position: 0 100%; }
  14% { opacity: 1; background-position: 0 0; }
  15%, 100% { opacity: 0; background-position: 0 0; }
}
@keyframes lost-glitch {
  0%, 94%, 100% { transform: none; text-shadow: none; }
  95% { transform: translate(0.025em, 0); text-shadow: -0.03em 0 var(--stage-f),
    0.03em 0 var(--stage-y); }
  97% { transform: translate(-0.02em, 0.01em); text-shadow: 0.03em 0 var(--stage-f),
    -0.03em 0 var(--stage-y); }
}
@keyframes lost-rise {
  from { opacity: 0; transform: translateY(0.5rem); }
  to { opacity: 1; transform: none; }
}
"""

# Edit distance with transpositions, so "statr" finds "start" at distance one. The
# requested path is the visitor's own and may be anything, so it is cut to 64 characters
# before it is compared, which bounds the work, and it only ever reaches the page
# through textContent.
LOST_SCRIPT = r"""
(function () {
  var shown = document.getElementById("lost-path");
  var asked = shown && shown.parentNode;
  var box = document.getElementById("lost-suggest");
  var list = document.getElementById("lost-list");
  var data = document.getElementById("lost-pages");
  var raw = window.location.pathname;
  var text = raw;
  try { text = decodeURIComponent(raw); } catch (e) {}
  if (shown && text !== "/") {
    shown.textContent = text.length > 120 ? text.slice(0, 117) + "…" : text;
    asked.hidden = false;
  }
  if (!box || !list || !data) return;
  var pages;
  try { pages = JSON.parse(data.textContent); } catch (e) { return; }
  var parts = text.split("/").filter(Boolean);
  var want = (parts.pop() || "").toLowerCase().replace(/\.(html?|php)$/, "")
    .replace(/[\s_]+/g, "-").slice(0, 64);
  if (want.length < 2) return;
  function distance(a, b) {
    var d = [], i, j;
    for (i = 0; i <= a.length; i++) d[i] = [i];
    for (j = 1; j <= b.length; j++) d[0][j] = j;
    for (i = 1; i <= a.length; i++) {
      for (j = 1; j <= b.length; j++) {
        var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
        if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) &&
            a.charAt(i - 2) === b.charAt(j - 1)) {
          d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
        }
      }
    }
    return d[a.length][b.length];
  }
  var scored = [];
  pages.forEach(function (page) {
    var href = page[0];
    if (typeof href !== "string" || href.charAt(0) !== "/" || href.charAt(1) === "/") return;
    var name = href.split("/").filter(Boolean).pop();
    if (!name) return;
    var allowed = Math.max(1, Math.floor(Math.max(name.length, want.length) / 3));
    var score = distance(want, name);
    // Someone who typed the start of a name meant that name, however long it is.
    if (want.length >= 3 && name.indexOf(want) === 0) {
      score = Math.min(score, 0.5 + (name.length - want.length) / 1000);
      allowed = Math.max(allowed, 1);
    }
    if (score <= allowed) scored.push({ page: page, score: score });
  });
  scored.sort(function (a, b) {
    return a.score - b.score || a.page[0].length - b.page[0].length;
  });
  scored.slice(0, 3).forEach(function (hit) {
    var item = document.createElement("li");
    var link = document.createElement("a");
    var name = document.createElement("span");
    var kind = document.createElement("span");
    link.setAttribute("href", hit.page[0]);
    name.className = "lost-name";
    name.textContent = String(hit.page[1]);
    kind.className = "lost-kind";
    kind.textContent = String(hit.page[2]);
    link.appendChild(name);
    link.appendChild(kind);
    item.appendChild(link);
    list.appendChild(item);
  });
  if (scored.length) box.hidden = false;
})();
"""


def missing_main(back: str, pages: list[list[str]]) -> str:
    """The body of the 404. ``back`` is the site's Back link, already built.

    The path and the suggestions start hidden and only the script reveals them, so
    without it the page is the heading, the sentence and the four links, all of which
    are plain anchors to root-relative addresses: this page is served from any depth.
    """
    digits = "".join(
        f'<span class="ld stage-{stage}">{digit}</span>' for digit, stage in LOST_DIGITS
    )
    links = (
        ("Home", "/", ""),
        ("Start", "/start/", " ghost"),
        ("Search the catalogue", "/#finder", " ghost"),
        ("FAMILY", "/family/", " ghost"),
    )
    nav = "".join(
        f'<a class="pill{extra}" href="{href}">{label}</a>' for label, href, extra in links
    )
    return (
        '<div class="page narrow lost">\n'
        f"{back}\n"
        '<h1 class="title lost-word"><span class="sr-only">Error 404: page not found</span>'
        f'<span class="typed" aria-hidden="true">{digits}<span class="caret"></span></span></h1>\n'
        '<p class="lede">There is nothing at this address.</p>\n'
        '<p class="lost-asked" hidden>You asked for <code id="lost-path"></code></p>\n'
        '<section class="lost-suggest" id="lost-suggest" aria-labelledby="lost-didyou" hidden>\n'
        '<h2 id="lost-didyou">Did you mean</h2>\n<ul id="lost-list"></ul>\n</section>\n'
        f'<nav class="lost-links" aria-label="Where to go">{nav}</nav>\n'
        f'<script type="application/json" id="lost-pages">{json_for_script(pages)}</script>\n'
        "</div>"
    )


# ------------------------------------------------------------------ the /errors/ pages

LIGHT = (
    "--bg: #f4f1ea; --ink: #141413; --muted: #5e5a54; --line: #e3ddd3; --card: #ebe6dc;"
    " --stage-f: #b42318; --stage-a: #a14a06; --stage-i: #0b6680; --stage-y: #7a35b5;"
)
NIGHT = (
    "--bg: #000000; --ink: #f3efe6; --muted: #a39e94; --line: #2a2724; --card: #141413;"
    " --stage-f: #ff8a7a; --stage-a: #ffae5c; --stage-i: #5ccbe6; --stage-y: #c79cff;"
)

# Chosen by the visitor on the site, and kept in this browser's own storage. Only the
# two plain themes are read: a page with no site around it has no console theme to show.
ERROR_HEAD_SCRIPT = (
    '(function(){try{var t=localStorage.getItem("theme");'
    'if(t==="day"||t==="night")document.documentElement.setAttribute("data-theme",t);'
    "}catch(e){}})();"
)

ERROR_SCRIPT = (
    '(function(){var b=document.getElementById("retry");if(!b)return;b.hidden=false;'
    'b.addEventListener("click",function(){window.location.reload();});})();'
)

# A dark tile with the site's mark, as a data URI so the tab has an icon without a
# request to anywhere.
FAVICON = (
    "data:image/svg+xml,%3Csvg viewBox='0 0 64 64' xmlns='http://www.w3.org/2000/svg'%3E"
    "%3Crect width='64' height='64' rx='14' fill='%23141413'/%3E%3Ctext x='32' y='41' "
    "font-family='sans-serif' font-size='26' font-weight='600' text-anchor='middle' "
    "fill='%23f3efe6'%3EAI%3C/text%3E%3C/svg%3E"
)

ERROR_CSS = (
    ":root {\n  "
    + LIGHT
    + """
  --font-sans: "Instrument Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="day"]) {
    """
    + NIGHT
    + """
    color-scheme: dark;
  }
}
:root[data-theme="night"] {
  """
    + NIGHT
    + """
  color-scheme: dark;
}
.stage-f { --stage: var(--stage-f); }
.stage-a { --stage: var(--stage-a); }
.stage-i { --stage: var(--stage-i); }
.stage-y { --stage: var(--stage-y); }
*, ::before, ::after { box-sizing: border-box; margin: 0; padding: 0; }
[hidden] { display: none !important; }
html {
  background: var(--bg);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
  -webkit-text-size-adjust: 100%;
}
body {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  font-family: var(--font-sans);
  font-size: 1.0625rem;
  line-height: 1.5;
}
h1, h2 { font-size: inherit; font-weight: inherit; }
a { color: inherit; text-decoration: none; }
svg { display: block; }
button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 3px; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.bar { width: 100%; max-width: 40rem; margin: 0 auto; padding: 1.25rem 1.25rem 0; }
.mark {
  display: inline-flex;
  min-width: 2.75rem;
  min-height: 2.75rem;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.1em;
}
.mark:hover { color: var(--muted); }
.err {
  display: flex;
  flex: 1;
  width: 100%;
  max-width: 40rem;
  margin: 0 auto;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 1.5rem 1.25rem 4rem;
}
.glyph { width: 4rem; height: 4rem; color: var(--stage); }
.glyph svg { width: 100%; height: 100%; overflow: visible; }
.digits {
  position: relative;
  margin-top: 1.25rem;
  font-size: clamp(5rem, 27vw, 9.5rem);
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--stage);
}
.digits .dg { display: inline-block; }
.digits .caret {
  display: inline-block;
  width: 0.07em;
  height: 0.78em;
  margin-left: 0.06em;
  vertical-align: -0.02em;
  background: var(--ink);
  opacity: 0;
}
.err-title {
  margin-top: 1rem;
  font-size: 1.875rem;
  line-height: 1.15;
  font-weight: 500;
  letter-spacing: -0.02em;
  text-wrap: balance;
}
.err-msg {
  max-width: 32rem;
  margin-top: 1rem;
  font-size: 1.125rem;
  line-height: 1.5556;
  text-wrap: pretty;
  color: var(--muted);
}
.progress {
  position: relative;
  width: 100%;
  max-width: 20rem;
  height: 0.5rem;
  margin-top: 1.75rem;
  border-radius: 999px;
  background: var(--card);
  box-shadow: inset 0 0 0 1px var(--line);
  overflow: hidden;
}
.progress i {
  display: block;
  width: 62%;
  height: 100%;
  border-radius: 999px;
  background: var(--stage);
}
.actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 2rem; }
.btn {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  padding: 0 1.25rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  font-size: 0.9375rem;
  font-weight: 500;
  line-height: 1.4286;
  white-space: nowrap;
}
.btn:hover { opacity: 0.82; }
.btn.ghost {
  background: transparent;
  color: var(--ink);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 35%, transparent);
}
.btn.ghost:hover { opacity: 1; background: color-mix(in srgb, var(--ink) 8%, transparent); }
.foot { padding: 1.25rem; font-size: 0.875rem; color: var(--muted); text-align: center; }
.foot { border-top: 1px solid var(--line); }
@media (prefers-reduced-motion: no-preference) {
  .btn { transition: opacity 160ms ease, background-color 160ms ease; }
  .digits .dg {
    max-width: 0;
    opacity: 0;
    overflow: hidden;
    vertical-align: bottom;
    animation: err-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) forwards;
  }
  .digits .dg:nth-child(1) { animation-delay: 0.1s; }
  .digits .dg:nth-child(2) { animation-delay: 0.4s; }
  .digits .dg:nth-child(3) { animation-delay: 0.7s; }
  .digits .caret { animation: err-caret 0.9s steps(1) 0s 4; }
  .err-title, .err-msg, .progress, .actions {
    opacity: 0;
    animation: err-rise 0.6s ease-out 1.1s forwards;
  }
  .err-msg { animation-delay: 1.2s; }
  .progress { animation-delay: 1.3s; }
  .actions { animation-delay: 1.4s; }
  .glyph { animation: err-rise 0.6s ease-out backwards; }
}
@keyframes err-key {
  0% { max-width: 0; opacity: 0; transform: translateY(0.18em) scale(1.6); }
  1% { max-width: 1em; }
  100% { max-width: 1em; opacity: 1; transform: none; }
}
@keyframes err-caret {
  0% { opacity: 1; }
  50% { opacity: 0; }
}
@keyframes err-rise {
  from { opacity: 0; transform: translateY(0.5rem); }
  to { opacity: 1; transform: none; }
}
"""
)

# What each page adds to the shared sheet: the effect that belongs to its code. Every
# one is inside the same no-preference query, so none of it exists when motion is off.
LOCK_CSS = """
@media (prefers-reduced-motion: no-preference) {
  .shackle { animation: err-lock 0.7s cubic-bezier(0.3, 1.5, 0.5, 1) 1s backwards; }
  .glyph svg { animation: err-rattle 6s ease-in-out 3s infinite; transform-origin: 50% 70%; }
}
@keyframes err-lock {
  from { transform: translateY(-8px); }
  to { transform: none; }
}
@keyframes err-rattle {
  0%, 90%, 100% { transform: none; }
  93% { transform: rotate(-4deg); }
  96% { transform: rotate(3deg); }
  98% { transform: rotate(-1.5deg); }
}
"""

SHAKE_CSS = """
@media (prefers-reduced-motion: no-preference) {
  .digits .dg:nth-child(1) { animation: err-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) 0.1s
    forwards, err-shake 5s ease-in-out 2.5s infinite; }
  .digits .dg:nth-child(2) { animation: err-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) 0.4s
    forwards, err-shake 5s ease-in-out 2.62s infinite; }
  .digits .dg:nth-child(3) { animation: err-key 0.34s cubic-bezier(0.2, 0.9, 0.25, 1.25) 0.7s
    forwards, err-shake 5s ease-in-out 2.74s infinite; }
  .led { animation: err-blink 2.4s steps(1) 1.5s infinite; }
}
@keyframes err-shake {
  0%, 12%, 100% { transform: none; }
  3% { transform: translateX(-0.025em) rotate(-0.8deg); }
  6% { transform: translateX(0.025em) rotate(0.8deg); }
  9% { transform: translateX(-0.015em); }
}
@keyframes err-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
"""

LINK_CSS = """
@media (prefers-reduced-motion: no-preference) {
  .wire { animation: err-dash 1s linear infinite; }
  .far { animation: err-blink 3.2s steps(1) 1.5s infinite; }
}
@keyframes err-dash {
  to { stroke-dashoffset: -7.1; }
}
@keyframes err-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}
"""

WAIT_CSS = """
@media (prefers-reduced-motion: no-preference) {
  .digits { animation: err-breathe 4.8s ease-in-out 2s infinite; }
  .progress i {
    background-image: linear-gradient(100deg, transparent 30%,
      color-mix(in srgb, var(--bg) 55%, transparent) 50%, transparent 70%);
    background-color: var(--stage);
    background-size: 220% 100%;
    animation: err-sweep 2.8s ease-in-out infinite;
  }
  .hand { animation: err-hand 24s linear infinite; transform-origin: 32px 32px; }
  .ring { animation: err-ring 4.8s ease-out 2s infinite; transform-origin: 32px 32px; }
}
@keyframes err-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.62; }
}
@keyframes err-sweep {
  from { background-position: 130% 0; }
  to { background-position: -130% 0; }
}
@keyframes err-hand {
  to { transform: rotate(360deg); }
}
@keyframes err-ring {
  0% { opacity: 0.5; transform: scale(1); }
  100% { opacity: 0; transform: scale(1.35); }
}
"""

_STROKE = 'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"'

LOCK_GLYPH = (
    f'<svg viewBox="0 0 64 64"><path class="shackle" d="M20 28v-8a12 12 0 0 1 24 0v8" {_STROKE}/>'
    '<rect x="14" y="28" width="36" height="26" rx="6" fill="currentColor"/>'
    '<circle cx="32" cy="39" r="3.5" fill="var(--bg)"/>'
    '<path d="M32 41v6" stroke="var(--bg)" stroke-width="3" stroke-linecap="round"/></svg>'
)
SERVER_GLYPH = (
    '<svg viewBox="0 0 64 64"><rect x="10" y="10" width="44" height="20" rx="6" fill="none" '
    'stroke="currentColor" stroke-width="4"/><rect x="10" y="34" width="44" height="20" rx="6" '
    'fill="none" stroke="currentColor" stroke-width="4"/>'
    '<circle cx="21" cy="20" r="2.6" fill="currentColor"/>'
    '<circle class="led" cx="21" cy="44" r="2.6" fill="currentColor"/>'
    '<path d="M32 20h14M32 44h14" stroke="currentColor" stroke-width="3" '
    'stroke-linecap="round"/></svg>'
)
LINK_GLYPH = (
    '<svg viewBox="0 0 64 64"><circle cx="9" cy="32" r="6" fill="currentColor"/>'
    '<path d="M17 32h10" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>'
    '<path d="M35 22l-6 20" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>'
    '<path class="wire" d="M38 32h8" fill="none" stroke="currentColor" stroke-width="3.5" '
    'stroke-linecap="round" stroke-dasharray="0.1 7"/>'
    '<circle class="far" cx="55" cy="32" r="6" fill="none" stroke="currentColor" '
    'stroke-width="4"/></svg>'
)
CLOCK_GLYPH = (
    '<svg viewBox="0 0 64 64"><circle class="ring" cx="32" cy="32" r="26" fill="none" '
    'stroke="currentColor" stroke-width="2"/>'
    '<circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" stroke-width="4"/>'
    '<path d="M32 32V18" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>'
    '<path class="hand" d="M32 32l10 6" stroke="currentColor" stroke-width="4" '
    'stroke-linecap="round"/></svg>'
)


@dataclass(frozen=True)
class ErrorPage:
    code: str
    title: str
    message: str
    stage: str
    glyph: str
    css: str
    retry: bool = False
    meter: bool = False


ERROR_PAGES = (
    ErrorPage(
        "403",
        "Access denied",
        "You do not have permission to open this page. If you expected to, check that you "
        "are signed in to the right account, or go back to the start.",
        "f",
        LOCK_GLYPH,
        LOCK_CSS,
    ),
    ErrorPage(
        "500",
        "Something went wrong",
        "The server hit a problem it could not recover from. It is not something you did. "
        "Try again in a moment.",
        "a",
        SERVER_GLYPH,
        SHAKE_CSS,
        retry=True,
    ),
    ErrorPage(
        "502",
        "Bad gateway",
        "The server could not get a valid answer from the service behind it. This usually "
        "clears up on its own, so try again shortly.",
        "y",
        LINK_GLYPH,
        LINK_CSS,
        retry=True,
    ),
    ErrorPage(
        "503",
        "Back shortly",
        "The site is down for maintenance or is too busy to answer right now. Nothing is "
        "lost. Try again in a few minutes.",
        "i",
        CLOCK_GLYPH,
        WAIT_CSS,
        retry=True,
        meter=True,
    ),
)


def render_error(page: ErrorPage) -> str:
    """One self-contained document: the whole page is this string and nothing it loads."""
    digits = "".join(f'<span class="dg">{digit}</span>' for digit in page.code)
    meter = (
        '<div class="progress" role="progressbar" aria-label="Maintenance in progress">'
        "<i></i></div>\n"
        if page.meter
        else ""
    )
    retry = (
        '<button type="button" class="btn" id="retry" hidden>Retry</button>'
        '<noscript><a class="btn" href="">Retry</a></noscript>'
        if page.retry
        else ""
    )
    home = " ghost" if page.retry else ""
    title = f"{page.code} {page.title} · AI"
    script = f"<script>\n{ERROR_SCRIPT}\n</script>\n" if page.retry else ""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        '<meta name="color-scheme" content="light dark">\n'
        f"<title>{html.escape(title)}</title>\n"
        f'<link rel="icon" href="{html.escape(FAVICON)}">\n'
        f"<style>\n{ERROR_CSS}{page.css}</style>\n"
        f"<script>\n{ERROR_HEAD_SCRIPT}\n</script>\n"
        "</head>\n"
        "<body>\n"
        '<header class="bar"><a class="mark" href="/" aria-label="Home">AI</a></header>\n'
        f'<main class="err stage-{page.stage}" id="content">\n'
        f'<div class="glyph" aria-hidden="true">{page.glyph}</div>\n'
        f'<p class="digits" aria-hidden="true">{digits}<span class="caret"></span></p>\n'
        f'<h1 class="err-title"><span class="sr-only">Error {page.code}: </span>'
        f"{html.escape(page.title)}</h1>\n"
        f'<p class="err-msg">{html.escape(page.message)}</p>\n'
        f"{meter}"
        f'<div class="actions">{retry}<a class="btn{home}" href="/">Home</a></div>\n'
        "</main>\n"
        f'<footer class="foot">Error {page.code}</footer>\n'
        f"{script}"
        "</body>\n"
        "</html>\n"
    )
