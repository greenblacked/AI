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

FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500"
    "&family=Newsreader:wght@400;500&display=swap"
)

CSS = """
:root {
  --bg: #f4f1ea;
  --ink: #141413;
  --muted: #5e5a54;
  --line: #e3ddd3;
  --card: #ebe6dc;
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
  color-scheme: dark;
}
html[data-theme="reactor"] {
  --bg: #070807;
  --ink: #d2f07a;
  --muted: #8aa36a;
  --line: #24321c;
  --card: #10170e;
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
.knob svg { width: 0.875rem; height: 0.875rem; }
.moon { display: none; }
html[data-theme="night"] .moon { display: block; }
html[data-theme="night"] .sun { display: none; }
@media (prefers-reduced-motion: no-preference) {
  .track { transition: background-color 300ms cubic-bezier(0.2, 0, 0, 1); }
  .knob { transition: transform 300ms cubic-bezier(0.2, 0, 0, 1); }
}

/* Footer. */
.site-footer { border-top: 1px solid var(--line); }
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
  scroll-margin-top: 6rem;
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
.back, .crumbs a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  text-decoration: underline;
  text-underline-offset: 4px;
}
.back { gap: 0.375rem; font-size: 0.875rem; line-height: 1.4286; }
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
.back-link { margin-top: 2rem; }
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
}
.prose-lab code {
  font-family: var(--font-sans);
  font-size: 0.86em;
  background: var(--card);
  padding: 0.08em 0.35em;
  border-radius: 0.3rem;
}
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
"""

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
  dark.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "night" ? "day" : "night";
    store(next);
    apply(next);
  });
  consoleTheme.addEventListener("click", function () {
    if (root.getAttribute("data-theme") === "reactor") {
      store(null);
      apply(clock());
      return;
    }
    store("reactor");
    apply("reactor");
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
    var from = "";
    try { from = new URL(document.referrer).origin; } catch (e) {}
    if (from !== window.location.origin || window.history.length < 2) return;
    event.preventDefault();
    window.history.back();
  }
  for (var b = 0; b < backs.length; b++) backs[b].addEventListener("click", back);

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
  input.addEventListener("input", refine);
})();
"""
