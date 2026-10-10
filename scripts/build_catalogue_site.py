#!/usr/bin/env python3
"""Build the static catalogue a Cloudflare Worker serves for one release.

The GitHub Release already attaches one ``.skill`` archive per skill and the portable
bundle. This writes the same two things, plus the marketplace manifest and a page for the
catalogue, each plugin, each skill and a few guides, into a directory Wrangler can upload
as static assets. It is a download of that
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
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import export_portable  # noqa: E402
import package_skills  # noqa: E402
import site_markdown  # noqa: E402
import site_style  # noqa: E402

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402

SOURCE_URL = "https://github.com/greenblacked/AI"
SENTINEL = ".catalogue-site"
SENTINEL_TEXT = (
    "This directory was produced by scripts/build_catalogue_site.py. "
    "The deploy deletes a previous build only when this file is present.\n"
)
# The browser tab's icon: the header's "AI" mark drawn as strokes, because a font a
# favicon names is not loaded and the letters would fall back to whatever the browser
# has. Ink on the paper colour of the light theme, so it reads on light and dark tabs.
FAVICON = "favicon.svg"
FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="7" fill="#141413"/>'
    '<path d="M6.5 25 13 7l6.5 18M8.7 19h8.6M25.5 7v18" fill="none" stroke="#f4f1ea" '
    'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>\n"
)
# A skill name becomes a directory in the site, so it has to be one path component.
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
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
    "coding": (
        "Design, review, debug and ship software with an agent. APIs and schemas, tests, "
        "refactors, scaffolding, performance, and how the agent itself should be instructed, "
        "handed work, and told to stop."
    ),
    "gamedev": (
        "Take a game from a design doc to something you can ship and keep running. Levels, "
        "balance, assets, netcode, saves, performance, certification, greenlight and live ops."
    ),
    "operations": (
        "Run the system after it is built. Incidents, game days, SLOs, Kubernetes, backups, "
        "disaster recovery, cost, instrumentation and the runbooks that make a bad night shorter."
    ),
    "delivery": (
        "Get a change into production without inventing the path each time. Pipelines, GitOps, "
        "database migrations, cutovers, mobile releases, release notes and the strategy that "
        "decides when a change is ready."
    ),
    "security": (
        "Review the thing before it is the incident. Threat models, authentication and "
        "authorization, secrets, hosts, images, privacy, access reviews and a security test "
        "you can actually run."
    ),
    "manager": (
        "The work of leading engineers, written so an agent can draft it with you. Hiring, "
        "growth, compensation, hard conversations, OKRs, onboarding, retention and the cadence "
        "of a team."
    ),
    "personal": (
        "Life outside the repository. Health, money, habits, travel, a major purchase and the "
        "weekly review that keeps them from piling up. None of this is installed unless you "
        "ask for it."
    ),
    "career": (
        "The work around the job. Searching, negotiating an offer, writing a technical "
        "article, preparing a talk and keeping learning notes you can find again."
    ),
    "design": (
        "Look at an interface the way its users will. Review a screen against usability "
        "heuristics, audit a page against WCAG 2.2, set up tokens, themes and component states, "
        "and plan a small test with real people."
    ),
}

NUMBER_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
]


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _count_word(count: int) -> str:
    """A count as the heading spells it: a word up to twelve, digits above."""
    return NUMBER_WORDS[count].capitalize() if 1 <= count <= 12 else str(count)


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


# Root-relative, so a link works from a nested page as well as from the index.
PAGES = (
    ("FAMILY", "/family/"),
    ("Start", "/start/"),
    ("Workflows", "/workflows/"),
    ("Examples", "/examples/"),
    ("Quality", "/quality/"),
)
ELSEWHERE = (
    ("Repository", SOURCE_URL),
    ("Releases", f"{SOURCE_URL}/releases"),
    ("Portable", "/portable-skills.zip"),
    ("Manifest", "/marketplace.json"),
)


def _link(label: str, href: str, current: str = "") -> str:
    """A navigation link. A link off this site opens a new tab and drops the referrer."""
    if href.startswith(("https://", "http://")):
        extra = ' target="_blank" rel="noopener noreferrer"'
    else:
        extra = ' aria-current="page"' if href == current else ""
    return f'<a href="{_esc(href)}"{extra}>{_esc(label)}</a>'


def _nav(label: str, links: tuple[tuple[str, str], ...], current: str = "") -> str:
    inner = "".join(_link(text, href, current) for text, href in links)
    return f'<nav aria-label="{label}">{inner}</nav>'


CONSOLE_ICON = (
    '<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="none" stroke="currentColor" '
    'stroke-width="1.4" d="M2.5 2.5h4.2v4.2H2.5zM9.3 2.5h4.2v4.2H9.3zM2.5 9.3h4.2v4.2H2.5z'
    'M9.3 9.3h4.2v4.2H9.3z"/></svg>'
)
MOON_ICON = (
    '<svg viewBox="0 0 16 16" class="moon" aria-hidden="true"><path fill="currentColor" '
    'd="M9.6 2.2a5.8 5.8 0 1 0 4.2 9.6 5.2 5.2 0 0 1-4.2-9.6Z"/></svg>'
)
SUN_ICON = (
    '<svg viewBox="0 0 16 16" class="sun" aria-hidden="true"><circle cx="8" cy="8" r="2.4" '
    'fill="currentColor"/><g stroke="currentColor" stroke-width="1.4" stroke-linecap="round">'
    '<path d="M8 1.6v1.8M8 12.6v1.8M1.6 8h1.8M12.6 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3'
    'M12.6 3.4l-1.3 1.3M4.7 11.3l-1.3 1.3"/></g></svg>'
)


TOP_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" '
    'stroke-width="2" d="M12 20V5M5.5 11.5 12 5l6.5 6.5"/></svg>'
)


def _dock(parent: str | None) -> str:
    """The bar Back moves into once the page scrolls past its own Back.

    The same button as the one at the top of the page, on the left of a bar that spans
    the header's width, so on a wide screen it sits under the header's outer edge
    rather than crowding the text column. A navigation landmark straight after the
    header, so the keyboard reaches it before the page body. Hidden until the script
    finds the page scrolled past that Back; without the script it stays hidden, and the
    Back at the top still works. The front page has no Back, so it has no bar.
    """
    if parent is None:
        return ""
    return (
        '<nav class="dock" id="dock" aria-label="Page">\n'
        '<div class="dock-in">\n'
        f"{_back(parent)}\n"
        "</div>\n</nav>\n"
    )


def _to_top() -> str:
    """To top, floating at the bottom right once the page has scrolled.

    The same glass button as Back, round with only the arrow on a narrow screen and
    labelled where the margin beside the text column can hold it. Its accessible name
    is the label either way. Last in the document, after the footer, so the keyboard
    reaches it once the page has been read rather than before it.
    """
    return (
        '<button type="button" class="back fab" id="to-top" aria-label="To top">'
        f"{TOP_ICON}<span>To top</span></button>\n"
    )


def _page(
    title: str, main: str, version: str, *, current: str = "", parent: str | None = None
) -> str:
    """One document. ``main`` is already escaped HTML for the page body.

    ``current`` is the root-relative path of the page, which marks its footer link.
    ``parent`` is where Back goes without history, and None on the front page.
    """
    source = _esc(SOURCE_URL)
    dock = _dock(parent)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="catalogue-version" content="{_esc(version)}">\n'
        '<meta name="theme-color" content="#f4f1ea">\n'
        f"<title>{html.escape(title)}</title>\n"
        f'<link rel="icon" href="/{FAVICON}" type="image/svg+xml">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{_esc(site_style.FONTS_URL)}">\n'
        f"<style>\n{site_style.CSS}</style>\n"
        f"<script>\n{site_style.HEAD_SCRIPT}\n</script>\n"
        "</head>\n"
        "<body>\n"
        '<a class="sr-only skip" href="#content">Skip to content</a>\n'
        '<header class="site-header" id="banner">\n'
        '<div class="bar">\n'
        f"{_nav('Primary', ELSEWHERE)}\n"
        '<a id="home" href="/" aria-label="Home">AI</a>\n'
        '<div class="tools">\n'
        '<button type="button" id="console-theme" class="tool" aria-pressed="false" '
        f'aria-label="Console theme">{CONSOLE_ICON}</button>\n'
        '<button type="button" id="dark-switch" class="tool" role="switch" '
        'aria-checked="false" aria-label="Dark theme">'
        f'<span class="track"><span class="knob">{MOON_ICON}{SUN_ICON}</span></span>'
        "</button>\n"
        "</div>\n</div>\n</header>\n"
        f"{dock}"
        f'<main id="content">\n{main}\n</main>\n'
        '<footer class="site-footer">\n<div class="foot">\n'
        '<div>\n<p class="mark">AI</p>\n'
        '<p class="tag">Agent skills, subagents and slash commands. '
        "Install only the plugins you want.</p>\n"
        '<p class="credit">Made by Serhii Zolotov, '
        f'<a href="{source}" target="_blank" rel="noopener noreferrer">greenblacked</a></p>\n'
        "</div>\n"
        f"{_nav('Footer', PAGES + ELSEWHERE, current)}\n"
        "</div>\n</footer>\n"
        f"{_to_top()}"
        f"<script>\n{site_style.PAGE_SCRIPT}</script>\n"
        "</body>\n"
        "</html>\n"
    )


BACK_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" '
    'stroke-width="2" d="M20 12H5M11.5 5.5 5 12l6.5 6.5"/></svg>'
)


def _back(parent: str) -> str:
    """A Back link: the previous page on this site, else ``parent``.

    The script returns through the browser history only when the referrer is this
    origin, so a visitor who arrived from a search engine or a new tab goes to
    ``parent`` instead of leaving the site. Without the script it is a plain link.
    """
    return f'<a class="back" href="{_esc(parent)}" data-back>{BACK_ICON}<span>Back</span></a>'


def _narrow(inner: str) -> str:
    """The column every page but the index and the plugin page sits in."""
    return f'<div class="page narrow">\n{inner}\n</div>'


def _title(title: str, lede: str = "") -> str:
    intro = f'\n<p class="lede">{_esc(lede)}</p>' if lede else ""
    return f'<h1 class="title">{_esc(title)}</h1>{intro}'


def _prose(inner: str) -> str:
    return f'<div class="prose-lab page-body">\n{inner}\n</div>'


def _skill_href(plugin: str, name: str) -> str:
    return f"/plugins/{quote(plugin, safe='')}/{quote(name, safe='')}/"


def _plugin_href(plugin: str) -> str:
    return f"/plugins/{quote(plugin, safe='')}/"


def _blob(path: str) -> str:
    return f"{SOURCE_URL}/blob/main/{quote(path, safe='/-_.~')}"


def _tree(path: str) -> str:
    return f"{SOURCE_URL}/tree/main/{quote(path, safe='/-_.~')}"


# --------------------------------------------------------------------- the catalogue


@dataclass
class Skill:
    name: str
    plugin: str
    directory: str
    description: str = ""
    allowed_tools: str = ""
    body: str = ""
    references: list[str] = field(default_factory=list)
    evals: list[dict] = field(default_factory=list)


@dataclass
class Part:
    """A subagent or a slash command a plugin ships."""

    plugin: str
    name: str
    path: str
    description: str = ""
    hint: str = ""


@dataclass
class Catalogue:
    root: Path
    manifest: dict
    marketplace: str
    groups: list[tuple[str, list[str]]]
    skills: list[Skill]
    agents: list[Part]
    commands: list[Part]
    eval_sets: list[list[dict]]
    blurbs: dict[str, str]


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _front(path: Path) -> tuple[dict[str, str], str]:
    """A file's frontmatter values and its body; empty values when it has none."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ""
    try:
        values = dict(parse(text).values)
    except FrontmatterError:
        return {}, text.strip()
    return values, export_portable.strip_frontmatter(text)


def _queries(path: Path) -> list[dict]:
    """The usable entries of an eval file: a dict with a text ``query``."""
    data = _read_json(path)
    if not isinstance(data, list):
        return []
    found = []
    for entry in data:
        if isinstance(entry, dict) and isinstance(entry.get("query"), str) and entry["query"]:
            found.append(entry)
    return found


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _collect_skills(root: Path) -> list[Skill]:
    skills = []
    for directory in package_skills.find_skills(root):
        name = directory.name
        plugin = directory.parent.parent.name
        for part in (name, plugin):
            if SAFE_NAME_RE.fullmatch(part) is None:
                raise SystemExit(f"refusing skill directory {part!r}: not a single path component")
        values, body = _front(directory / "SKILL.md")
        references = sorted(
            path.name
            for path in (directory / "references").glob("*.md")
            if path.is_file() and not path.name.startswith(".")
        )
        skills.append(
            Skill(
                name=name,
                plugin=plugin,
                directory=directory.relative_to(root).as_posix(),
                description=_collapse(values.get("description", "")),
                allowed_tools=_collapse(values.get("allowed-tools", "")),
                body=body,
                references=references,
                evals=_queries(directory / "evals" / "trigger-eval.json"),
            )
        )
    return skills


def _collect_parts(root: Path, plugin: str, kind: str) -> list[Part]:
    parts = []
    for path in sorted((root / "plugins" / plugin / kind).glob("*.md")):
        if not path.is_file() or SAFE_NAME_RE.fullmatch(path.stem) is None:
            continue
        values, _ = _front(path)
        parts.append(
            Part(
                plugin=plugin,
                name=path.stem,
                path=path.relative_to(root).as_posix(),
                description=_collapse(values.get("description", "")),
                hint=_collapse(values.get("argument-hint", "")),
            )
        )
    return parts


def _blurb(root: Path, plugin: str) -> str:
    if plugin in ABOUT:
        return ABOUT[plugin]
    data = _read_json(root / "plugins" / plugin / ".claude-plugin" / "plugin.json")
    description = data.get("description") if isinstance(data, dict) else None
    return _collapse(description) if isinstance(description, str) else ""


def collect(
    root: Path, manifest: dict, groups: list[tuple[str, list[str]]], skills: list[Skill]
) -> Catalogue:
    """Everything the pages below say, read once from the repository."""
    plugins = [plugin for plugin, _ in groups]
    plugins += sorted(
        path.name
        for path in (root / "plugins").glob("*")
        if path.is_dir() and path.name not in plugins
    )
    agents: list[Part] = []
    commands: list[Part] = []
    eval_sets = [skill.evals for skill in skills if skill.evals]
    for plugin in plugins:
        if SAFE_NAME_RE.fullmatch(plugin) is None:
            continue
        agents += _collect_parts(root, plugin, "agents")
        commands += _collect_parts(root, plugin, "commands")
        for path in sorted((root / "plugins" / plugin / "agents" / "evals").glob("*.json")):
            queries = _queries(path)
            if queries:
                eval_sets.append(queries)
    return Catalogue(
        root=root,
        manifest=manifest,
        marketplace=manifest["name"],
        groups=groups,
        skills=skills,
        agents=agents,
        commands=commands,
        eval_sets=eval_sets,
        blurbs={plugin: _blurb(root, plugin) for plugin in plugins},
    )


# ------------------------------------------------------------------------ the index


def _finder(label: str, count: str) -> str:
    return (
        '<div class="finder" id="finder">\n'
        f'<label><span class="sr-only">{_esc(label)}</span>\n'
        f'<input id="find" type="search" autocomplete="off" placeholder="{_esc(label)}"></label>\n'
        f'<p class="small" id="count" aria-live="polite">{_esc(count)}</p>\n'
        "</div>\n"
    )


def render_index(catalogue: Catalogue, version: str) -> str:
    """The front page: one section per plugin. Every value from the repository is escaped."""
    description = catalogue.manifest.get("description")
    intro = ""
    if isinstance(description, str) and description.strip():
        intro = f'<p class="lede">{_esc(description.strip())}</p>\n'
    sections = []
    for plugin, archives in catalogue.groups:
        names = [skill.name for skill in catalogue.skills if skill.plugin == plugin]
        blurb = catalogue.blurbs.get(plugin, "")
        about = f'<p class="blurb">{_esc(blurb)}</p>\n' if blurb else ""
        sections.append(
            f'<section class="plugin" data-plugin="{_esc(plugin.lower())}" '
            f'data-blurb="{_esc(blurb.lower())}" '
            f'data-skills="{_esc(" ".join(name.lower() for name in names))}">\n'
            '<div class="row">\n'
            f'<h2><a href="{_esc(_plugin_href(plugin))}">{_esc(plugin)}</a></h2>\n'
            f'<p class="small">{_esc(_plural(len(archives), "skill"))}</p>\n'
            "</div>\n"
            f'{about}<p class="small hits" hidden></p>\n'
            "</section>"
        )
    plugin_count = len(catalogue.groups)
    skill_count = len(catalogue.skills)
    main = (
        '<section class="wrap hero">\n'
        f"<h1>{_esc(_count_word(plugin_count))} {'plugin' if plugin_count == 1 else 'plugins'}. "
        "Install <span>only the ones</span> you want.</h1>\n"
        '<div class="side">\n'
        f"{intro}"
        f'<p class="small counts">{_esc(_plural(plugin_count, "plugin"))}'
        f" · {_esc(_plural(skill_count, 'skill'))}</p>\n"
        f'<a class="pill" href="{_esc(SOURCE_URL)}" target="_blank" '
        'rel="noopener noreferrer">View source</a>\n'
        "</div>\n"
        "</section>\n"
        '<section class="wrap listing">\n'
        '<div class="card"><p>One skill each, plus the portable bundle. '
        "The manifest points at the repository, so this copy is not "
        "a marketplace you add.</p></div>\n"
        f"{_finder('Find a plugin', _plural(plugin_count, 'plugin'))}"
        '<p class="none" id="none" hidden>Nothing matches that name.</p>\n'
        f'<div id="list">\n{"".join(sections)}\n</div>\n'
        "</section>\n"
    )
    return _page("AI", main, version)


# ------------------------------------------------------------------ a plugin's page


def _install_line(plugin: str, marketplace: str) -> str:
    return f"/plugin install {plugin}@{marketplace}"


def _code_block(text: str) -> str:
    return f'<pre tabindex="0"><code>{_esc(text)}\n</code></pre>'


def render_plugin(plugin: str, catalogue: Catalogue, version: str) -> str:
    skills = [skill for skill in catalogue.skills if skill.plugin == plugin]
    blurb = catalogue.blurbs.get(plugin, "")
    about = f'<p class="lede">{_esc(blurb)}</p>\n' if blurb else ""
    items = "\n".join(
        f'<li data-name="{_esc(skill.name.lower())}">'
        f'<a href="{_esc(_skill_href(plugin, skill.name))}">{_esc(skill.name)}</a></li>'
        for skill in skills
    )
    install = _code_block(_install_line(plugin, catalogue.marketplace))
    main = (
        '<div class="page">\n'
        f"{_back('/')}\n"
        f'<h1 class="title-xl">{_esc(plugin)}</h1>\n'
        f"{about}"
        f'<p class="small count">{_esc(_plural(len(skills), "skill"))}</p>\n'
        f'<div class="install">{install}</div>\n'
        f"{_finder('Find a skill', _plural(len(skills), 'skill'))}"
        '<p class="none" id="none" hidden>Nothing matches that name.</p>\n'
        f'<ul class="skills" id="list">\n{items}\n</ul>\n'
        "</div>"
    )
    return _page(f"{plugin} · AI", main, version, parent="/")


# -------------------------------------------------------------------- a skill's page


def _owner(expected: object, catalogue: Catalogue) -> str:
    """The winner a near-miss names: a link when it is a skill, text otherwise."""
    if not isinstance(expected, str) or not expected.strip():
        return ""
    name = expected.strip()
    owner = next((skill for skill in catalogue.skills if skill.name == name), None)
    if owner is not None:
        href = _esc(_skill_href(owner.plugin, owner.name))
        return f' <span class="say">→</span> <a href="{href}">{_esc(name)}</a>'
    kind = " (subagent)" if any(agent.name == name for agent in catalogue.agents) else ""
    return f' <span class="say">→</span> <code>{_esc(name)}</code>{_esc(kind)}'


def render_skill(skill: Skill, catalogue: Catalogue, version: str) -> str:
    slugs = site_markdown.Slugs()
    archive = f"/skills/{quote(skill.name, safe='')}.skill"
    crumbs = (
        f"{_back(_plugin_href(skill.plugin))}\n"
        '<nav class="crumbs" aria-label="Skill">'
        '<a href="/">Catalogue</a>'
        f'<a href="{_esc(_plugin_href(skill.plugin))}">{_esc(skill.plugin)}</a>'
        f'<a class="quiet" href="{_esc(_blob(skill.directory + "/SKILL.md"))}" target="_blank" '
        'rel="noopener noreferrer">On GitHub</a>'
        "</nav>"
    )
    parts = [
        f"<h1>{_esc(skill.name)}</h1>",
        f'<p class="lead">{_esc(skill.description)}</p>' if skill.description else "",
        '<div class="actions">'
        f'<a class="pill" href="{_esc(archive)}">Download</a>'
        f'<a class="pill" href="{_esc(_tree(skill.directory))}" target="_blank" '
        'rel="noopener noreferrer">View source</a>'
        "</div>",
        f'<h2 id="{slugs.take("Install")}">Install</h2>',
        _code_block(_install_line(skill.plugin, catalogue.marketplace)),
    ]
    if skill.allowed_tools:
        parts.append(f"<p>Allowed tools: <code>{_esc(skill.allowed_tools)}</code></p>")
    if skill.body:
        parts.append(
            site_markdown.render(skill.body, source_dir=skill.directory, offset=1, slugs=slugs)
        )
    if skill.references:
        items = "\n".join(
            f'<li><a href="{_esc(_blob(f"{skill.directory}/references/{name}"))}" '
            'target="_blank" rel="noopener noreferrer">'
            f"<code>references/{_esc(name)}</code></a></li>"
            for name in skill.references
        )
        parts.append(f'<h2 id="{slugs.take("References")}">References</h2>\n<ul>\n{items}\n</ul>')
    fires = [e["query"] for e in skill.evals if e.get("should_trigger") is True]
    elsewhere = [e for e in skill.evals if e.get("should_trigger") is False]
    if fires:
        items = "\n".join(f"<li>“{_esc(query)}”</li>" for query in fires)
        heading = f'<h2 id="{slugs.take("Fires on")}">Fires on</h2>'
        parts.append(f"{heading}\n<ul>\n{items}\n</ul>")
    if elsewhere:
        items = "\n".join(
            f"<li>“{_esc(entry['query'])}”{_owner(entry.get('expected'), catalogue)}</li>"
            for entry in elsewhere
        )
        heading = f'<h2 id="{slugs.take("Goes elsewhere")}">Goes elsewhere</h2>'
        parts.append(f"{heading}\n<ul>\n{items}\n</ul>")
    inner = (
        crumbs
        + '\n<article class="prose-lab">\n'
        + "\n".join(p for p in parts if p)
        + "\n</article>"
    )
    main = _narrow(inner)
    return _page(f"{skill.name} · AI", main, version, parent=_plugin_href(skill.plugin))


# ------------------------------------------------------------------------ /start/


def render_start(catalogue: Catalogue, version: str) -> str:
    slugs = site_markdown.Slugs()
    repo = SOURCE_URL.removeprefix("https://github.com/")
    lines = [f"/plugin marketplace add {repo}"]
    lines += [_install_line(plugin, catalogue.marketplace) for plugin, _ in catalogue.groups]
    lines.append("/reload-plugins")
    items = []
    for plugin, archives in catalogue.groups:
        blurb = catalogue.blurbs.get(plugin, "")
        said = f" {_esc(blurb)}" if blurb else ""
        items.append(
            f'<li><a href="{_esc(_plugin_href(plugin))}"><code>{_esc(plugin)}</code></a> — '
            f"{_esc(_plural(len(archives), 'skill'))}.{said}</li>"
        )
    parts = [
        f'<h2 id="{slugs.take("Install in Claude Code")}">Install in Claude Code</h2>',
        "<p>Register the marketplace once, install the plugins you will use, and reload. "
        "Every plugin installs on its own; each description a plugin ships sits in context "
        "for the whole session, so install only what you need.</p>",
        _code_block("\n".join(lines)),
        f"<ul>\n{chr(10).join(items)}\n</ul>",
        f'<h2 id="{slugs.take("Install in other tools")}">Install in other tools</h2>',
        '<p>Download <a href="/portable-skills.zip"><code>portable-skills.zip</code></a>: '
        "the same skills as plain Markdown files, with a router that says when to open "
        "each one. It works wherever you can attach files or put text in an instructions "
        "file.</p>",
    ]
    guide = catalogue.root / "docs" / "using.md"
    if guide.is_file():
        try:
            text = guide.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        if text.strip():
            parts.append(site_markdown.render(text, source_dir="docs", offset=1, slugs=slugs))
    main = _narrow(
        _back("/")
        + "\n"
        + _title(
            "Getting started",
            "Install one plugin, or the lot. The skills load themselves when a request matches.",
        )
        + "\n"
        + _prose("\n".join(parts))
    )
    return _page("Getting started · AI", main, version, current="/start/", parent="/")


# --------------------------------------------------------------------- /workflows/


def _part_item(part: Part, *, command: bool) -> str:
    label = ("/" if command else "") + part.name
    href = _esc(_blob(part.path))
    link = f'<a href="{href}" rel="noopener noreferrer"><code>{_esc(label)}</code></a>'
    hint = f" <code>{_esc(part.hint)}</code>" if part.hint else ""
    text = f" — {_esc(part.description)}" if part.description else ""
    return f"<li>{link}{hint}{text}</li>"


def render_workflows(catalogue: Catalogue, version: str) -> str:
    slugs = site_markdown.Slugs()
    skills, agents, commands = len(catalogue.skills), len(catalogue.agents), len(catalogue.commands)
    parts = [
        f'<h2 id="{slugs.take("How they fit together")}">How they fit together</h2>',
        f"<p>A <strong>skill</strong> is a Markdown procedure that loads on its own when a "
        f"request matches its description ({_esc(_plural(skills, 'skill'))} here). "
        f"A <strong>subagent</strong> works in a context of its own: the main agent delegates "
        "to one when the work would otherwise fill the session with material you do not need "
        f"afterwards, and gets the conclusion back ({_esc(_plural(agents, 'subagent'))} here). "
        f"A <strong>slash command</strong> runs only when you type it, so it suits work that "
        f"takes an argument ({_esc(_plural(commands, 'command'))} here).</p>",
        "<p>A plugin ships whichever of the three it has, and installing the plugin installs "
        "them together.</p>",
    ]
    order = [plugin for plugin, _ in catalogue.groups]
    order += sorted({part.plugin for part in catalogue.agents + catalogue.commands} - set(order))
    for plugin in order:
        mine_commands = [part for part in catalogue.commands if part.plugin == plugin]
        mine_agents = [part for part in catalogue.agents if part.plugin == plugin]
        if not mine_commands and not mine_agents:
            continue
        parts.append(f'<h2 id="{slugs.take(plugin)}">{_esc(plugin)}</h2>')
        if mine_commands:
            items = "\n".join(_part_item(part, command=True) for part in mine_commands)
            parts.append(f'<h3 id="{slugs.take(plugin + " commands")}">Commands</h3>')
            parts.append(f"<ul>\n{items}\n</ul>")
        if mine_agents:
            items = "\n".join(_part_item(part, command=False) for part in mine_agents)
            parts.append(f'<h3 id="{slugs.take(plugin + " subagents")}">Subagents</h3>')
            parts.append(f"<ul>\n{items}\n</ul>")
    if not catalogue.agents and not catalogue.commands:
        parts.append("<p>No subagents or slash commands ship in this build.</p>")
    main = _narrow(
        _back("/")
        + "\n"
        + _title(
            "Workflows", "The subagents and slash commands that ship beside the skills, by plugin."
        )
        + "\n"
        + _prose("\n".join(parts))
    )
    return _page("Workflows · AI", main, version, current="/workflows/", parent="/")


# ---------------------------------------------------------------------- /examples/


def readme_section(text: str, title: str) -> str | None:
    """A README's ``## title`` section: its heading up to the next ``##`` heading."""
    collected: list[str] = []
    inside = False
    fence = ""
    for line in text.split("\n"):
        stripped = line.strip()
        marker = stripped[:3] if stripped[:3] in ("```", "~~~") else ""
        if marker and not fence:
            fence = marker
        elif marker and marker == fence:
            fence = ""
        if not fence and not marker and re.match(r"^## +", line):
            if inside:
                break
            inside = line[3:].strip() == title
        if inside:
            collected.append(line)
    return "\n".join(collected).strip() or None


def render_examples(catalogue: Catalogue, version: str) -> str:
    slugs = site_markdown.Slugs()
    parts = []
    readme = catalogue.root / "README.md"
    if readme.is_file():
        try:
            section = readme_section(
                readme.read_text(encoding="utf-8"), "What a real week looks like"
            )
        except (OSError, UnicodeDecodeError):
            section = None
        if section:
            parts.append(site_markdown.render(section, offset=0, slugs=slugs))
    order = [plugin for plugin, _ in catalogue.groups]
    for plugin in order:
        rows = []
        for skill in catalogue.skills:
            if skill.plugin != plugin:
                continue
            said = [e["query"] for e in skill.evals if e.get("should_trigger") is True][:3]
            link = f'<a href="{_esc(_skill_href(plugin, skill.name))}">{_esc(skill.name)}</a>'
            rows += [
                f'<li><span class="say">You say:</span> “{_esc(query)}” '
                f'<span class="say">→</span> {link}</li>'
                for query in said
            ]
        if rows:
            parts.append(f'<h2 id="{slugs.take(plugin)}">{_esc(plugin)}</h2>')
            parts.append("<ul>\n" + "\n".join(rows) + "\n</ul>")
    if not parts:
        parts.append("<p>No examples are available in this build.</p>")
    main = _narrow(
        _back("/")
        + "\n"
        + _title("Examples", "What you type, and the skill it reaches. Nobody types a skill name.")
        + "\n"
        + _prose("\n".join(parts))
    )
    return _page("Examples · AI", main, version, current="/examples/", parent="/")


# ----------------------------------------------------------------------- /quality/


def _count_row(label: str, value: object) -> str:
    return f'<tr><th scope="row">{_esc(label)}</th><td class="num">{_esc(str(value))}</td></tr>'


def _table(
    head: list[str], rows: list[str], *, numeric: frozenset[int] | set[int] = frozenset()
) -> str:
    cells = "".join(
        f'<th class="num">{_esc(label)}</th>' if n in numeric else f"<th>{_esc(label)}</th>"
        for n, label in enumerate(head)
    )
    return (
        '<div class="table-wrap"><table>\n'
        f"<thead><tr>{cells}</tr></thead>\n<tbody>\n{chr(10).join(rows)}\n</tbody>\n"
        "</table></div>"
    )


def eval_totals(eval_sets: list[list[dict]]) -> dict[str, int]:
    """Query counts across every eval set: positives, negatives and routed negatives."""
    positives = negatives = routed = 0
    for entries in eval_sets:
        for entry in entries:
            if entry.get("should_trigger") is True:
                positives += 1
            elif entry.get("should_trigger") is False:
                negatives += 1
                if isinstance(entry.get("expected"), str) and entry["expected"].strip():
                    routed += 1
    return {
        "sets": len(eval_sets),
        "queries": positives + negatives,
        "positives": positives,
        "negatives": negatives,
        "routed": routed,
    }


def _coverage_floor(root: Path) -> str | None:
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = re.search(r"^fail_under\s*=\s*(\d+(?:\.\d+)?)\s*(?:#.*)?$", text, re.M)
    return match.group(1) if match else None


def _benchmark_cases(root: Path) -> int | None:
    base = root / ".claude" / "agents" / "benchmarks"
    if not base.is_dir():
        return None
    return sum(1 for _ in base.glob("*/*/case.json"))


def _lesson_titles(root: Path) -> list[str]:
    try:
        text = (root / "docs" / "review-lessons.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    titles = []
    fence = ""
    for line in text.split("\n"):
        marker = line.strip()[:3]
        if marker in ("```", "~~~"):
            fence = "" if fence == marker else (fence or marker)
        elif not fence and line.startswith("### ") and line[4:].strip():
            titles.append(line[4:].strip())
    return titles


def render_quality(catalogue: Catalogue, version: str) -> str:
    slugs = site_markdown.Slugs()
    root = catalogue.root

    def heading(text: str) -> str:
        return f'<h2 id="{slugs.take(text)}">{_esc(text)}</h2>'

    counts = _table(
        ["What", "How many"],
        [
            _count_row("Plugins", len(catalogue.groups)),
            _count_row("Skills", len(catalogue.skills)),
            _count_row("Subagents", len(catalogue.agents)),
            _count_row("Slash commands", len(catalogue.commands)),
        ],
        numeric={1},
    )
    totals = eval_totals(catalogue.eval_sets)
    evals = _table(
        ["Trigger evals", "How many"],
        [
            _count_row("Eval sets", totals["sets"]),
            _count_row("Queries", totals["queries"]),
            _count_row("Should fire", totals["positives"]),
            _count_row("Should not fire", totals["negatives"]),
            _count_row("Not firing, with a named owner", totals["routed"]),
        ],
        numeric={1},
    )
    parts = [
        heading("What is in the catalogue"),
        counts,
        heading("Trigger evals"),
        "<p>Each skill and subagent has a set of queries it should fire on and near-misses "
        "it should not. A near-miss that names the skill that should win it is what shows "
        "one description taking another's queries.</p>",
        evals,
    ]
    sizes: dict[str, int] = {}
    for skill in catalogue.skills:
        sizes[skill.plugin] = sizes.get(skill.plugin, 0) + len(skill.description)
    budget = _read_json(root / "listing-budget.json")
    ceilings = budget.get("plugins") if isinstance(budget, dict) else None
    if isinstance(ceilings, dict) and sizes:
        rows = []
        for plugin, _ in catalogue.groups:
            ceiling = ceilings.get(plugin)
            shown = (
                f"{ceiling:,}"
                if isinstance(ceiling, int) and not isinstance(ceiling, bool)
                else "—"
            )
            rows.append(
                f'<tr><th scope="row">{_esc(plugin)}</th>'
                f'<td class="num">{sizes.get(plugin, 0):,}</td>'
                f'<td class="num">{_esc(shown)}</td></tr>'
            )
        parts += [
            heading("Description listing"),
            "<p>Every description a plugin ships sits in context for the whole session, so each "
            "plugin has a ceiling, in characters, that a new skill has to be a decision to "
            "raise.</p>",
            _table(["Plugin", "Characters", "Ceiling"], rows, numeric={1, 2}),
        ]
    checks = []
    floor = _coverage_floor(root)
    if floor is not None:
        checks.append(_count_row("Test coverage floor", f"{floor}%"))
    cases = _benchmark_cases(root)
    if cases is not None:
        checks.append(_count_row("Reviewer benchmark cases", cases))
    if checks:
        parts += [heading("Gates"), _table(["Gate", "Value"], checks, numeric={1})]
    titles = _lesson_titles(root)
    if titles:
        items = "\n".join(f"<li>{_esc(title)}</li>" for title in titles)
        parts += [
            heading("What review has caught"),
            "<p>Each entry is a defect class a review found once, with the check that now "
            f'catches it, recorded in <a href="{_esc(_blob("docs/review-lessons.md"))}" '
            'rel="noopener noreferrer"><code>docs/review-lessons.md</code></a>.</p>',
            f"<ul>\n{items}\n</ul>",
        ]
    links = []
    if (root / "docs" / "ci.md").is_file():
        links.append(
            f'<li><a href="{_esc(_blob("docs/ci.md"))}" rel="noopener noreferrer">'
            "What CI checks</a></li>"
        )
    links.append(
        f'<li><a href="{_esc(SOURCE_URL)}/actions" rel="noopener noreferrer">'
        "Recent runs on GitHub Actions</a></li>"
    )
    parts += [heading("Read more"), "<ul>\n" + "\n".join(links) + "\n</ul>"]
    main = _narrow(
        _back("/")
        + "\n"
        + _title(
            "Quality evidence", "Figures worked out from the repository when this site was built."
        )
        + "\n"
        + _prose("\n".join(parts))
    )
    return _page("Quality evidence · AI", main, version, current="/quality/", parent="/")


# ------------------------------------------------------------------------ /family/

# The one page this file draws by hand rather than from a plugin's own files. The
# workflow is the product here, so it gets a stage timeline and profile cards rather
# than the generated prose and tables every other page falls back to.
FAMILY_STAGES = (
    ("F", "Frame", "What problem, for whom, what done means, and the smallest valuable slice."),
    (
        "A",
        "Architect",
        "The approach, the boundaries, the interfaces, and the hardest decision to reverse.",
    ),
    ("M", "Make", "The order the slice is built in, and the proof each step carries."),
    ("I", "Inspect", "Whether the change is correct, safe and accessible, with evidence."),
    ("L", "Launch", "Whether it is ready to reach users, and how it comes back."),
    ("Y", "Yield", "What the outcome teaches the next slice, fed back into Frame."),
)

FAMILY_PROFILES = (
    ("Solo", "One person runs all six stages, lightly, with the agents as independent checkers."),
    ("Developer", "Frame, Architect, Make and Yield in depth; Inspect and Launch handed off."),
    ("QA", "Inspect in depth, with acceptance criteria pushed back into Frame and Architect."),
    ("Team", "All six with a named owner and a handoff contract between each stage."),
)


def render_family(catalogue: Catalogue, version: str) -> str:
    plugin = "family"
    stages = "\n".join(
        f'<li><span class="letter" aria-hidden="true">{letter}</span>'
        f"<div><h3>{_esc(name)}</h3><p>{_esc(text)}</p></div></li>"
        for letter, name, text in FAMILY_STAGES
    )
    profiles = "\n".join(
        f"<li><h3>{_esc(name)}</h3><p>{_esc(text)}</p></li>" for name, text in FAMILY_PROFILES
    )
    main = (
        '<div class="page narrow">\n'
        f"{_back('/')}\n"
        '<h1 class="title">The FAMILY workflow</h1>\n'
        '<p class="lede">Frame · Architect · Make · Inspect · Launch · Yield — one '
        "workflow from a vague request to a measured outcome.</p>\n"
        '<div class="prose-lab page-body">\n'
        "<p>FAMILY keeps its shape whether one person or a whole team is running it. It "
        "takes one slice of work from a vague request to a measured outcome, and each "
        "stage has one gate, one artifact and one handoff to the next.</p>\n"
        f'<ol class="family-stages">\n{stages}\n</ol>\n'
        "<h2>The four profiles</h2>\n"
        "<p>The stages never change; their depth does. Name the profile you are running, "
        "so a shortcut is a decision rather than an accident.</p>\n"
        f'<ul class="family-profiles">\n{profiles}\n</ul>\n'
        "<h2>Run it</h2>\n"
        f'<p>The <a href="{_esc(_plugin_href(plugin))}">family</a> plugin ships the '
        f'<a href="{_esc(_skill_href(plugin, "family-workflow"))}">family-workflow</a> '
        "skill and a read-only subagent per stage, so the main conversation keeps the "
        "conclusion of each stage and not the material it read.</p>\n"
        f"{_code_block(_install_line(plugin, catalogue.marketplace))}\n"
        "</div>\n"
        "</div>"
    )
    return _page("FAMILY · AI", main, version, current="/family/", parent="/")


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
    # Read and check what the pages need before anything is deleted or written, so a
    # refusal leaves the previous build alone rather than a half-made one.
    skills = _collect_skills(root)
    if not skills:
        raise SystemExit(f"no skills under {root}")
    names = [skill.name for skill in skills]
    if len(names) != len(set(names)):
        raise SystemExit("two skills share a name; their pages and archives would collide")
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
    (output / FAVICON).write_text(FAVICON_SVG, encoding="utf-8")
    groups = _ordered_groups(manifest, grouped)
    catalogue = collect(root, manifest, groups, skills)
    pages = {
        "": render_index(catalogue, version),
        "family": render_family(catalogue, version),
        "start": render_start(catalogue, version),
        "workflows": render_workflows(catalogue, version),
        "examples": render_examples(catalogue, version),
        "quality": render_quality(catalogue, version),
    }
    for plugin, _ in groups:
        pages[f"plugins/{plugin}"] = render_plugin(plugin, catalogue, version)
    for skill in catalogue.skills:
        pages[f"plugins/{skill.plugin}/{skill.name}"] = render_skill(skill, catalogue, version)
    for directory, content in pages.items():
        target = output / directory
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(content, encoding="utf-8")
    missing = _page(
        "Not found · AI",
        _narrow(_back("/") + "\n" + _title("Not found", "There is nothing at this address.")),
        version,
        parent="/",
    )
    (output / "404.html").write_text(missing, encoding="utf-8")
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
