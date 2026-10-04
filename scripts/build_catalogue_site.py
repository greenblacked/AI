#!/usr/bin/env python3
"""Build the static catalogue a Cloudflare Worker serves for one release.

The GitHub Release already attaches one ``.skill`` archive per skill and the portable
bundle. This writes the same two things, plus the marketplace manifest and a single
index, into a directory Wrangler can upload as static assets. It is a download of that
release, not a marketplace Claude Code can install from: the manifest's plugin sources
are paths inside the git repository, and they only resolve there.

The output directory is replaced only when it is already one of these builds. A path
that is the repository, contains it, or is the home directory is refused before
anything is deleted.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import export_portable  # noqa: E402
import package_skills  # noqa: E402

SOURCE_URL = "https://github.com/greenblacked/AI"
SENTINEL = ".catalogue-site"
SENTINEL_TEXT = (
    "This directory was produced by scripts/build_catalogue_site.py. "
    "The deploy deletes a previous build only when this file is present.\n"
)
# A version is a label written into the page and into version.txt. It is never a path.
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")


def normalise_version(raw: str) -> str:
    """The version label, or exit. Rejects anything that is not a single token."""
    version = raw.strip()
    if VERSION_RE.fullmatch(version) is None:
        raise SystemExit(
            f"refusing version {raw!r}: use a token such as v1.2.3, pr-abcdef0 or main-abcdef0"
        )
    return version


def unsafe_output(root: Path, output: Path) -> str | None:
    """Why ``output`` must not be replaced, or ``None`` when it may be."""
    resolved_root = root.resolve()
    resolved_out = output.resolve()
    if resolved_out == Path.home().resolve():
        return "it is the home directory"
    if resolved_out == resolved_root or resolved_out in resolved_root.parents:
        return "it is the repository root or a directory that contains it"
    if resolved_out.exists() and not (resolved_out / SENTINEL).is_file():
        return "it is not a previous catalogue site (no .catalogue-site)"
    return None


def _manifest(root: Path) -> dict:
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        raise SystemExit(f"no marketplace manifest at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not data["name"]:
        raise SystemExit(f"{path} has no string name")
    return data


def _ordered_groups(manifest: dict, grouped: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    """Marketplace order first, then any plugin the manifest does not name."""
    named: list[str] = []
    plugins = manifest.get("plugins")
    if isinstance(plugins, list):
        for plugin in plugins:
            if isinstance(plugin, dict) and isinstance(plugin.get("name"), str):
                named.append(plugin["name"])
    order = [name for name in named if name in grouped]
    order += sorted(set(grouped) - set(order))
    return [(name, sorted(grouped[name])) for name in order]


ABOUT = {
    "coding": "Software engineering",
    "gamedev": "Making games",
    "operations": "Running systems",
    "delivery": "Shipping the change",
    "security": "Review and hardening",
    "manager": "Engineering leadership",
    "personal": "Life outside work",
    "career": "The work around the job",
}

# The page is one file. Colours match the preview: paper by day, black from 20:00
# to 06:00 in the browser, or whenever the visitor presses Black.
CSS = """
:root {
  --bg: #f4f1ea;
  --ink: #141413;
  --muted: #5e5a54;
  --line: #e3ddd3;
  --card: #ebe6dc;
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
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
  font-family: "Iowan Old Style", Palatino, Georgia, serif;
  font-size: 1.0625rem;
  line-height: 1.5;
}
button, input { font: inherit; color: inherit; }
button {
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
a { color: inherit; }
.skip {
  position: absolute;
  left: -999px;
}
.skip:focus {
  left: 1rem;
  top: 1rem;
  z-index: 20;
  background: var(--ink);
  color: var(--bg);
  padding: 0.5rem 1rem;
  border-radius: 999px;
}
.banner {
  position: sticky;
  top: 0;
  z-index: 10;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1.25rem;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  backdrop-filter: blur(12px);
}
.banner.away { transform: translateY(-100%); }
@media (prefers-reduced-motion: no-preference) {
  .banner { transition: transform 200ms ease; }
}
.banner nav { display: none; gap: 1.5rem; }
.banner a, .foot a, #home, #theme {
  min-height: 2.75rem;
  display: inline-flex;
  align-items: center;
}
#home {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  min-width: 2.75rem;
  justify-content: center;
  letter-spacing: 0.14em;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
}
#theme {
  margin-left: auto;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 1rem;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.875rem;
}
#theme[aria-pressed="true"] {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
}
@media (min-width: 64rem) {
  .banner nav { display: flex; }
}
.wrap { width: min(72rem, calc(100% - 2.5rem)); margin: 0 auto; }
main { flex: 1; }
.hero {
  display: grid;
  gap: 2.5rem;
  padding: 4rem 0 2rem;
}
.hero h1 {
  margin: 0;
  max-width: 16ch;
  font-size: clamp(2.6rem, 6vw, 3.75rem);
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.hero h1 span {
  text-decoration: underline;
  text-underline-offset: 0.18em;
}
.lede { margin: 0; color: var(--muted); font-size: 1.125rem; }
.counts { margin: 1.5rem 0 0; color: var(--muted); font-size: 0.875rem; }
.source {
  margin-top: 2rem;
  min-height: 2.75rem;
  display: inline-flex;
  align-items: center;
  padding: 0 1rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.875rem;
  text-decoration: none;
}
.card {
  margin: 0 0 3.5rem;
  padding: 2.5rem 1.5rem;
  border-radius: 1.5rem;
  background: var(--card);
  font-size: clamp(1.6rem, 3vw, 2.25rem);
  line-height: 1.35;
}
.find {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
  justify-content: space-between;
}
.find input {
  width: min(28rem, 100%);
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  padding: 0.75rem 0;
  outline: none;
}
.find p { margin: 0; color: var(--muted); font-size: 0.875rem; }
.group { border-top: 1px solid var(--line); padding: 2rem 0; }
.group h2 {
  margin: 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.about { margin: 0.25rem 0 0; color: var(--muted); font-size: 0.875rem; }
.head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 1rem;
}
ul { list-style: none; margin: 0; padding: 0; }
li { border-bottom: 1px solid var(--line); }
li a {
  min-height: 2.75rem;
  display: flex;
  align-items: center;
  text-decoration: none;
  font-family: ui-sans-serif, system-ui, sans-serif;
}
li a:hover { color: var(--muted); }
@media (min-width: 40rem) {
  .hero { grid-template-columns: 7fr 5fr; align-items: end; }
  ul { columns: 2; column-gap: 3rem; }
  .card { padding: 3.5rem 2.5rem; }
}
.miss { margin: 4rem 0; color: var(--muted); }
.foot {
  border-top: 1px solid var(--line);
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  justify-content: space-between;
  align-items: flex-end;
  padding: 2.5rem 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.875rem;
}
.mark { margin: 0; letter-spacing: 0.14em; font-weight: 500; }
.foot p { margin: 0.5rem 0 0; max-width: 24rem; color: var(--muted); }
.foot a { text-decoration: none; }
.foot nav { display: flex; flex-wrap: wrap; gap: 0.25rem 1.25rem; }
:focus-visible { outline: 2px solid var(--ink); outline-offset: 3px; }
"""

HEAD_SCRIPT = """
(function () {
  var stored = null;
  try { stored = localStorage.getItem("theme"); } catch (e) {}
  var hour = new Date().getHours();
  var night = stored === "night" || (stored !== "day" && (hour >= 20 || hour < 6));
  document.documentElement.setAttribute("data-theme", night ? "night" : "day");
})();
"""

PAGE_SCRIPT = """
(function () {
  var night = document.documentElement.getAttribute("data-theme") === "night";
  var theme = document.getElementById("theme");
  var color = document.querySelector('meta[name="theme-color"]');
  function paint(on) {
    document.documentElement.setAttribute("data-theme", on ? "night" : "day");
    theme.setAttribute("aria-pressed", on ? "true" : "false");
    if (color) color.setAttribute("content", on ? "#000000" : "#f4f1ea");
  }
  paint(night);
  theme.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") !== "night";
    try { localStorage.setItem("theme", next ? "night" : "day"); } catch (e) {}
    paint(next);
  });
  document.getElementById("home").addEventListener("click", function () {
    window.scrollTo(0, 0);
  });
  var banner = document.getElementById("banner");
  var last = window.scrollY;
  window.addEventListener("scroll", function () {
    var y = window.scrollY;
    var delta = y - last;
    if (y <= 64) banner.classList.remove("away");
    else if (delta > 8) banner.classList.add("away");
    else if (delta < -8) banner.classList.remove("away");
    last = y;
  }, { passive: true });
  var input = document.getElementById("find");
  var list = document.getElementById("list");
  var tally = document.getElementById("count");
  if (!input || !list || !tally) return;
  var total = list.querySelectorAll("li").length;
  function apply() {
    var needle = input.value.trim().toLowerCase();
    var shown = 0;
    list.querySelectorAll("section").forEach(function (section) {
      var plugin = section.getAttribute("data-plugin") || "";
      var visible = 0;
      section.querySelectorAll("li").forEach(function (item) {
        var name = item.getAttribute("data-name") || "";
        var hit = !needle || name.indexOf(needle) !== -1 || plugin.indexOf(needle) !== -1;
        item.hidden = !hit;
        if (hit) visible += 1;
      });
      section.hidden = visible === 0;
      shown += visible;
    });
    tally.textContent = needle ? (shown + " of " + total) : (total + " skills");
  }
  input.addEventListener("input", apply);
})();
"""


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _links() -> str:
    source = html.escape(SOURCE_URL, quote=True)
    return (
        f'<a href="{source}">Repository</a>'
        f'<a href="{source}/releases">Releases</a>'
        '<a href="portable-skills.zip">Portable</a>'
        '<a href="marketplace.json">Manifest</a>'
    )


def _page(title: str, main: str, version: str) -> str:
    """One document. ``main`` is already escaped HTML for the page body."""
    source = html.escape(SOURCE_URL, quote=True)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="catalogue-version" content="{html.escape(version, quote=True)}">\n'
        '<meta name="theme-color" content="#f4f1ea">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>\n{CSS}</style>\n"
        f"<script>\n{HEAD_SCRIPT}</script>\n"
        "</head>\n"
        "<body>\n"
        '<a class="skip" href="#content">Skip to content</a>\n'
        '<header class="banner" id="banner">\n'
        f"<nav>{_links()}</nav>\n"
        '<button type="button" id="home">AI</button>\n'
        '<button type="button" id="theme" aria-pressed="false">Black</button>\n'
        "</header>\n"
        f'<main id="content">\n{main}\n</main>\n'
        '<footer class="wrap foot">\n'
        "<div>\n"
        '<p class="mark">AI</p>\n'
        "<p>Agent skills, subagents and slash commands. "
        "Install only the plugins you want.</p>\n"
        "<p>Made by Serhii Zolotov, "
        f'<a href="{source}">greenblacked</a></p>\n'
        "</div>\n"
        f"<nav>{_links()}</nav>\n"
        "</footer>\n"
        f"<script>\n{PAGE_SCRIPT}</script>\n"
        "</body>\n"
        "</html>\n"
    )


def render_index(manifest: dict, groups: list[tuple[str, list[str]]], version: str) -> str:
    """The one page. Every value taken from the repository is escaped."""
    description = manifest.get("description")
    intro = ""
    if isinstance(description, str) and description.strip():
        intro = f'<p class="lede">{html.escape(description.strip())}</p>\n'
    sections = []
    skill_count = 0
    for plugin, skills in groups:
        skill_count += len(skills)
        items = "\n".join(
            f'<li data-name="{html.escape(skill.removesuffix(".skill").lower(), quote=True)}">'
            f'<a href="skills/{html.escape(skill, quote=True)}">'
            f"{html.escape(skill.removesuffix('.skill'))}</a></li>"
            for skill in skills
        )
        blurb = ABOUT.get(plugin, "")
        about = f'<p class="about">{html.escape(blurb)}</p>' if blurb else ""
        sections.append(
            f'<section class="group" data-plugin="{html.escape(plugin.lower(), quote=True)}">\n'
            f'<div class="head"><h2>{html.escape(plugin)}</h2>{about}</div>\n'
            f"<ul>\n{items}\n</ul>\n</section>"
        )
    plugin_count = len(groups)
    main = (
        '<section class="wrap hero">\n'
        f"<h1>{html.escape(_plural(plugin_count, 'plugin'))}. "
        "Install <span>only the ones</span> you want.</h1>\n"
        "<div>\n"
        f"{intro}"
        f'<p class="counts">{html.escape(_plural(plugin_count, "plugin"))}'
        f" · {html.escape(_plural(skill_count, 'skill'))}</p>\n"
        f'<a class="source" href="{html.escape(SOURCE_URL, quote=True)}">View source</a>\n'
        "</div>\n"
        "</section>\n"
        '<section class="wrap">\n'
        '<p class="card">One skill each, plus the portable bundle. '
        "The manifest points at the repository, so this copy is not "
        "a marketplace you add.</p>\n"
        '<div class="find">\n'
        "<label>Find a skill\n"
        '<input id="find" type="search" autocomplete="off" '
        'placeholder="Find a skill"></label>\n'
        f'<p id="count">{skill_count} skills</p>\n'
        "</div>\n"
        f'<div id="list">\n{"".join(sections)}\n</div>\n'
        "</section>\n"
    )
    return _page("AI", main, version)


def _robots(noindex: bool) -> str:
    if noindex:
        return "User-agent: *\nDisallow: /\n"
    return "User-agent: *\nAllow: /\n"


def _write_archives(root: Path, skills_dir: Path) -> dict[str, list[str]]:
    skills = package_skills.find_skills(root)
    if not skills:
        raise SystemExit(f"no skills under {root}")
    grouped: dict[str, list[str]] = {}
    for skill in skills:
        archive = package_skills.package(skill, skills_dir, root)
        grouped.setdefault(skill.parent.parent.name, []).append(archive.name)
    return grouped


def _write_portable(root: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="catalogue-portable-") as tmp:
        exported = Path(tmp) / "portable"
        code = export_portable.export(root, exported)
        if code != 0:
            raise SystemExit(f"portable export failed ({code})")
        with zipfile.ZipFile(output / "portable-skills.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(exported.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(exported).as_posix())


def build(root: Path, output: Path, version: str, *, noindex: bool = False) -> None:
    """Replace ``output`` with the site for ``version``."""
    version = normalise_version(version)
    manifest = _manifest(root)
    reason = unsafe_output(root, output)
    if reason is not None:
        raise SystemExit(f"refusing to write {output}: {reason}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    # Wrangler reads this and does not upload the sentinel. A dotfile with no other
    # purpose should not be part of the site a visitor can fetch.
    (output / ".assetsignore").write_text(f"{SENTINEL}\n", encoding="utf-8")
    skills_dir = output / "skills"
    skills_dir.mkdir()
    grouped = _write_archives(root, skills_dir)
    _write_portable(root, output)
    (output / "marketplace.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "version.txt").write_text(version + "\n", encoding="utf-8")
    (output / "robots.txt").write_text(_robots(noindex), encoding="utf-8")
    groups = _ordered_groups(manifest, grouped)
    (output / "index.html").write_text(render_index(manifest, groups, version), encoding="utf-8")
    (output / "404.html").write_text(
        _page(
            "Not found",
            '<section class="wrap hero"><h1>Not found</h1>'
            '<p><a class="source" href="/">Back to the catalogue</a></p></section>',
            version,
        ),
        encoding="utf-8",
    )
    print(f"built {output} for {version}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_catalogue_site", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument(
        "--version", required=True, help="label written into the page and version.txt"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="output directory (default: dist/site)"
    )
    parser.add_argument(
        "--noindex", action="store_true", help="tell crawlers not to index this build"
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = args.out if args.out is not None else root / "dist" / "site"
    build(root, output, args.version, noindex=args.noindex)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
