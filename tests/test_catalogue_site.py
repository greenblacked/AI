"""The catalogue site is what a release uploads, so a bad build has to fail here.

The deploy workflow trusts this script to refuse a version that is not a token and to
refuse to delete a directory it did not itself create. Both are silent if they only
hold in the happy path.
"""

from __future__ import annotations

import hashlib
import html
import http.server
import json
import os
import re
import struct
import subprocess
import sys
import threading
import time
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.conftest import REPO, eval_set, load_script, write_skill
from tests.test_evals_workflow import _extract_run_block

site = load_script("build_catalogue_site.py")


def test_a_mini_repository_builds_a_site(mini_repo, tmp_path):
    manifest_path = mini_repo / ".claude-plugin" / "marketplace.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "A <b>catalogue</b>"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "site"
    site.build(mini_repo, output, "  v1.2.3  ")
    assert (output / "version.txt").read_text(encoding="utf-8") == "v1.2.3\n"
    names = sorted(path.name for path in (output / "skills").iterdir())
    assert names == ["alpha.skill", "beta.skill"]
    page = (output / "index.html").read_text(encoding="utf-8")
    assert "engineering" in page
    assert "v1.2.3" in page
    assert "https://github.com/greenblacked/AI" in page
    assert "Made by Serhii Zolotov" in page
    assert ">Black<" not in page and 'id="theme"' not in page
    assert 'role="switch"' in page and 'aria-label="Dark theme"' in page
    assert 'aria-label="Console theme"' in page
    assert "Release <code>" not in page
    assert html.escape("A <b>catalogue</b>") in page
    assert "<b>" not in page
    manifest = json.loads((output / "marketplace.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "mini"
    assert (output / "robots.txt").read_text(encoding="utf-8").startswith("User-agent: *\nAllow:")
    assert (output / ".catalogue-site").is_file()
    assert ".catalogue-site" in (output / ".assetsignore").read_text(encoding="utf-8")
    with zipfile.ZipFile(output / "portable-skills.zip") as bundle:
        assert any(name.endswith("alpha.md") for name in bundle.namelist())
    # A second build replaces the first rather than refusing its own sentinel.
    site.build(mini_repo, output, "v1.2.4", noindex=True)
    assert (output / "version.txt").read_text(encoding="utf-8") == "v1.2.4\n"
    assert "Disallow:" in (output / "robots.txt").read_text(encoding="utf-8")


HOSTILE_BODY = """# Alpha

Body with <script>alert(1)</script> and [x](javascript:alert(1)) and
[y](JaVaScRiPt:alert(1)) and [r](references/deep.md).

## Home

```bash
echo "<b>not bold</b>"
```
"""


def _hostile_skill(root, *, hostile_owner=False):
    """Replace alpha with a skill whose body, references and evals are all hostile.

    The validator refuses an ``expected`` that names nothing, and the portable export
    refuses a link out of the skill's directory, so those two can only be shown to the
    page renderer directly (``hostile_owner``), never through a full build.
    """
    queries = [{"query": "alpha says <script>alert(1)</script>", "should_trigger": True}]
    queries += [{"query": f"alpha extra {n}", "should_trigger": True} for n in range(7)]
    queries += [
        {"query": "go to beta", "should_trigger": False, "expected": "beta"},
        {"query": "go to the reader", "should_trigger": False, "expected": "reader"},
        {"query": "no owner", "should_trigger": False},
    ]
    queries += [{"query": f"alpha other {n}", "should_trigger": False} for n in range(5)]
    if hostile_owner:
        queries.append(
            {"query": "bad owner", "should_trigger": False, "expected": '"><script>x</script>'}
        )
    directory = write_skill(root, "engineering", "alpha", evals=queries)
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---\n", 2)[1]
    body = HOSTILE_BODY
    if hostile_owner:
        body += "\nA [z](../../../../etc/passwd) link and a [w](../../../../../etc/passwd) one.\n"
    (directory / "SKILL.md").write_text(
        f"---\n{front}allowed-tools: Read, Bash(git:*)\n---\n\n{body}", encoding="utf-8"
    )
    (directory / "references").mkdir(exist_ok=True)
    (directory / "references" / "deep.md").write_text("# Deep\n", encoding="utf-8")
    return directory


def _catalogue(root):
    manifest = site._manifest(root)
    groups = [("engineering", ["alpha.skill", "beta.skill"])]
    return site.collect(root, manifest, groups, site._collect_skills(root))


def _build(root, tmp_path):
    output = tmp_path / "site"
    site.build(root, output, "v9")
    return output


class _TagParser(HTMLParser):
    """Collects start tags the way a browser tokenises them, case and all."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tags = set()
        self.blocks = []
        self._open = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._open = (tag, attrs, [])
        else:
            self.tags.add(tag)

    def handle_data(self, data):
        if self._open:
            self._open[2].append(data)

    def handle_endtag(self, tag):
        if self._open and tag == self._open[0]:
            self.blocks.append((tag, self._open[1], "".join(self._open[2]).strip()))
            self._open = None


def _live_tags(page):
    """Opening tags in a page that are not part of the template the build writes.

    A script or style block passes only when it is one of the template's own,
    attribute-free and byte-for-byte; any other one is reported as a live tag.
    """
    template = {
        ("style", site.site_style.CSS.strip()),
        ("script", site.site_style.HEAD_SCRIPT.strip()),
        ("script", site.site_style.PAGE_SCRIPT.strip()),
        ("script", site.site_style.FAMILY_SCRIPT.strip()),
        ("script", site.site_offline.REGISTER_SCRIPT.strip()),
        # The offline page's own style and script, which no other page carries.
        ("style", site.site_offline.OFFLINE_CSS.strip()),
        ("script", site.site_offline.render_offline_script().strip()),
    }
    parser = _TagParser()
    parser.feed(page)
    parser.close()
    tags = set(parser.tags)
    for tag, attrs, body in parser.blocks:
        if attrs or (tag, body) not in template:
            tags.add(tag)
    if parser._open:
        tags.add(parser._open[0])
    return tags


SAFE_TAGS = {
    "html", "head", "meta", "title", "body", "a", "header", "nav", "button", "main",
    "footer", "div", "p", "section", "h1", "h2", "h3", "h4", "h5", "h6", "span", "ul",
    "ol", "li", "pre", "code", "strong", "em", "br", "hr", "table", "thead", "tbody",
    "tr", "th", "td", "blockquote", "label", "input", "link", "svg", "path", "circle", "g",
    "article", "details", "summary", "dl", "dt", "dd", "fieldset", "legend", "form", "noscript",
}  # fmt: skip


BACK = '<a class="back" href="{}" data-back>' + site.BACK_ICON + "<span>Back</span></a>"


@pytest.mark.parametrize(
    ("path", "parent"),
    [
        ("plugins/engineering/index.html", "/"),
        ("plugins/engineering/alpha/index.html", "/plugins/engineering/"),
        ("family/index.html", "/"),
        ("family/example/index.html", "/family/"),
        ("start/index.html", "/"),
        ("workflows/index.html", "/"),
        ("examples/index.html", "/"),
        ("quality/index.html", "/"),
        ("404.html", "/"),
    ],
)
def test_every_page_below_the_index_has_one_back_link_to_its_parent(
    mini_repo, tmp_path, path, parent
):
    page = (_build(mini_repo, tmp_path) / path).read_text(encoding="utf-8")
    main = page.split('<main id="content">', 1)[1].split("</main>", 1)[0]
    # Without the script the link is a plain one to the page above, so it still works.
    assert main.count(BACK.format(parent)) == 1
    assert main.count("data-back>") == 1


def test_the_back_link_sits_above_the_crumbs_and_every_theme_has_its_glass(mini_repo, tmp_path):
    # How Back looks and behaves is tested in a browser (tests/test_site_browser.py);
    # this is the markup order and the tokens each theme has to define for it.
    page = (_build(mini_repo, tmp_path) / "plugins/engineering/alpha/index.html").read_text(
        encoding="utf-8"
    )
    # Its own row above the crumbs, not one of the underlined crumb links.
    assert BACK.format("/plugins/engineering/") + '\n<nav class="crumbs"' in page
    css = site.site_style.CSS
    for theme in (":root {", 'html[data-theme="night"] {', 'html[data-theme="reactor"] {'):
        tokens = css.split(theme, 1)[1].split("}", 1)[0]
        for token in ("--glass-tint", "--glass-edge", "--glass-sheen", "--glass-shadow"):
            assert f"{token}:" in tokens, (theme, token)


TO_TOP = (
    '<button type="button" class="back fab" id="to-top" aria-label="To top">'
    + site.TOP_ICON
    + "<span>To top</span></button>"
)


@pytest.mark.parametrize(
    ("path", "parent"),
    [
        ("index.html", None),
        ("plugins/engineering/index.html", "/"),
        ("plugins/engineering/alpha/index.html", "/plugins/engineering/"),
        ("family/index.html", "/"),
        ("family/example/index.html", "/family/"),
        ("start/index.html", "/"),
        ("quality/index.html", "/"),
        ("404.html", "/"),
    ],
)
def test_every_page_has_the_bar_with_back_only_below_the_index(mini_repo, tmp_path, path, parent):
    page = (_build(mini_repo, tmp_path) / path).read_text(encoding="utf-8")
    if parent is None:
        # The front page has no Back, so it has no bar either.
        assert 'id="dock"' not in page
    else:
        assert page.count('id="dock"') == 1
        # A labelled landmark straight after the header, so the keyboard reaches it
        # before the page body, holding the same Back as the top of the page.
        opening = '</header>\n<nav class="dock" id="dock" aria-label="Page">\n'
        assert opening in page
        dock = page.split(opening, 1)[1].split("\n</div>\n</nav>", 1)[0]
        assert dock == '<div class="dock-in">\n' + BACK.format(parent)
    # To top is on every page, outside the bar, last after the footer.
    assert page.count('id="to-top"') == 1
    assert "</footer>\n" + TO_TOP + "\n<script>" in page


def test_the_index_has_no_back_link(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "index.html").read_text(encoding="utf-8")
    assert "data-back>" not in page


def test_every_page_names_the_tab_and_home_screen_icons_and_both_ship(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    # Each icon is a real PNG of the size its link declares; IHDR holds width and height.
    for name, size in (("favicon.png", 64), ("apple-touch-icon.png", 180)):
        data = (output / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", name
        assert struct.unpack(">II", data[16:24]) == (size, size), name
    # The pages under errors/ are shown on their own, in place of a failing page, so they
    # carry no link to a file on the site: their icon is a data URI, checked below.
    pages = sorted(p for p in output.rglob("*.html") if p.parent.name != "errors")
    assert len(pages) > 5
    for page in (output / "errors").glob("*.html"):
        head = page.read_text(encoding="utf-8").split("</head>", 1)[0]
        assert head.count('<link rel="icon" href="data:image/svg+xml,') == 1, page
        assert "/favicon.png" not in head and "apple-touch-icon" not in head, page
    links = (
        '<link rel="icon" href="/favicon.png" type="image/png" sizes="64x64">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
    )
    for page in pages:
        head = page.read_text(encoding="utf-8").split("</head>", 1)[0]
        for link in links:
            assert head.count(link) == 1, (page, link)


def _font_urls(page: str) -> set[str]:
    """Every font address a page names: its preloads and the url() of each @font-face."""
    urls = set(re.findall(r'<link rel="preload" href="([^"]+)" as="font"', page))
    for face in re.findall(r"@font-face\s*\{[^}]*\}", page):
        urls.update(re.findall(r"url\(([^)]+)\)", face))
    return urls


def test_no_built_page_asks_a_font_host_for_anything(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    texts = [p for p in output.rglob("*") if p.suffix in (".html", ".txt", ".json", ".css")]
    assert len(texts) > 5
    for path in texts:
        text = path.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in text, path
        assert "fonts.gstatic.com" not in text, path
    # The pages the visitor reads each name the sans and open no connection ahead of time.
    pages = [p for p in output.rglob("*.html") if p.parent.name != "errors"]
    assert len(pages) > 5
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "preconnect" not in text and '<link rel="stylesheet"' not in text, path
        assert f'href="{site.site_style.SANS_URL}"' in text, path


def test_every_font_a_page_names_exists_in_the_build_and_is_a_real_woff2(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    pages = [p for p in output.rglob("*.html") if p.parent.name != "errors"]
    seen = set()
    for path in pages:
        urls = _font_urls(path.read_text(encoding="utf-8"))
        # The stylesheet declares both faces, so every page names at least the pair.
        assert {site.site_style.SANS_URL, site.site_style.SERIF_URL} <= urls, path
        for url in urls:
            # Absolute, because the 404 page is served from whatever depth was asked for.
            assert url.startswith("/fonts/"), (path, url)
            assert (output / url.lstrip("/")).is_file(), (path, url)
            seen.add(url)
    for url in seen:
        assert (output / url.lstrip("/")).read_bytes()[:4] == b"wOF2", url


def test_the_card_and_prose_pages_preload_the_serif_and_others_do_not(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    sans, serif = site.site_style.SANS_URL, site.site_style.SERIF_URL
    for path in (output / "index.html", output / "plugins" / "engineering" / "index.html"):
        preloaded = re.findall(r'<link rel="preload" href="([^"]+)"', path.read_text("utf-8"))
        assert preloaded[0] == sans
    index = re.findall(
        r'<link rel="preload" href="([^"]+)"', (output / "index.html").read_text("utf-8")
    )
    assert index == [sans, serif]
    skill = (output / "plugins" / "engineering" / "alpha" / "index.html").read_text("utf-8")
    assert re.findall(r'<link rel="preload" href="([^"]+)"', skill) == [sans, serif]
    assert site._font_preloads("<p>plain</p>").count("<link") == 1
    for tag in re.findall(r"<link rel=\"preload\"[^>]*>", site._font_preloads('class="card"')):
        # crossorigin is not optional: a font preload without it is fetched a second time.
        assert 'as="font"' in tag and 'type="font/woff2"' in tag and tag.endswith("crossorigin>")


def test_font_file_names_carry_a_hash_of_their_bytes(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    fonts = output / "fonts"
    names = sorted(p.name for p in fonts.iterdir())
    assert len(names) == 4
    for built in fonts.iterdir():
        stem, digest, suffix = built.name.rsplit(".", 2)
        assert re.fullmatch(r"[0-9a-f]{10}", digest), built.name
        assert hashlib.sha256(built.read_bytes()).hexdigest().startswith(digest), built.name
    # The names in the stylesheet are those hashed names, not the source ones.
    assert site.site_style.SANS_FILE in names and site.site_style.SERIF_FILE in names
    assert "instrument-sans-latin.woff2" not in names


def test_the_headers_file_caches_the_fonts_for_a_year_and_never_the_worker(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    assert (output / "_headers").read_text(encoding="utf-8") == (
        "/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/sw.js\n  Cache-Control: no-cache\n"
    )
    # Cloudflare reads _headers and _redirects at upload and does not serve them.
    assert (output / "_redirects").is_file()


def test_each_font_ships_with_its_licence_and_the_upstream_copyright_line(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    licences = {
        site.site_style.SANS_LICENCE: (
            "Copyright 2022 The Instrument Sans Project Authors "
            "(https://github.com/Instrument/instrument-sans)"
        ),
        site.site_style.SERIF_LICENCE: (
            "Copyright 2020 The Newsreader Project Authors "
            "(http://github.com/productiontype/Newsreader)"
        ),
    }
    for name, copyright_line in licences.items():
        text = (output / "fonts" / name).read_text(encoding="utf-8")
        assert text.startswith(copyright_line + "\n"), name
        assert "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007" in text, name
        assert "PERMISSION & CONDITIONS" in text, name
    # The stylesheet points at them, so the licence is findable from the page that uses it.
    page = (output / "index.html").read_text(encoding="utf-8")
    for name in licences:
        assert f"/fonts/{name}" in page
    notice = (REPO / "NOTICE").read_text(encoding="utf-8")
    for copyright_line in licences.values():
        assert copyright_line in notice


def test_the_committed_font_files_are_the_ones_the_licences_describe():
    # Each woff2 is Google's latin subset of a variable font, so its name table holds the
    # same copyright line as the licence beside it.
    for font, licence in (
        ("instrument-sans-latin.woff2", "OFL-instrument-sans.txt"),
        ("newsreader-latin.woff2", "OFL-newsreader.txt"),
    ):
        assert (site.site_style.FONT_DIR / font).read_bytes()[:4] == b"wOF2"
        first = (site.site_style.FONT_DIR / licence).read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("Copyright ") and "Project Authors" in first


def test_a_missing_font_is_refused_before_the_previous_build_is_touched(
    mini_repo, tmp_path, monkeypatch
):
    output = _build(mini_repo, tmp_path)
    before = sorted(p.relative_to(output) for p in output.rglob("*"))
    monkeypatch.setattr(site.site_style, "FONT_DIR", tmp_path / "no-fonts")
    with pytest.raises(SystemExit, match="cannot read the site font file"):
        site.build(mini_repo, output, "v2")
    assert sorted(p.relative_to(output) for p in output.rglob("*")) == before
    assert (output / "version.txt").read_text(encoding="utf-8") != "v2\n"


def _with_family(mini_repo):
    """The mini repository plus a family plugin: two skills and two stage agents."""
    family = mini_repo / "plugins" / "family"
    (family / ".claude-plugin").mkdir(parents=True)
    (family / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    write_skill(mini_repo, "family", "family-workflow", evals=eval_set("family-workflow"))
    write_skill(mini_repo, "family", "qa-workflow", evals=eval_set("qa-workflow"))
    (family / "agents").mkdir()
    for name, text in (
        ("inspector", "Inspect a change against its frame — run the checks. Use when ready."),
        ("framer", "Turn a vague request into a frame. Use when a request arrives."),
    ):
        (family / "agents" / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: {text}\n---\n\nBody.\n", encoding="utf-8"
        )
    manifest = mini_repo / ".claude-plugin" / "marketplace.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["plugins"].append({"name": "family", "source": "./plugins/family"})
    manifest.write_text(json.dumps(data), encoding="utf-8")


def test_the_family_plugin_has_no_page_of_its_own_and_its_address_redirects(mini_repo, tmp_path):
    _with_family(mini_repo)
    output = _build(mini_repo, tmp_path)
    assert not (output / "plugins" / "family" / "index.html").exists()
    assert (output / "plugins" / "family" / "qa-workflow" / "index.html").is_file()
    # Both spellings, because a rule matches the path as written; permanent.
    assert (output / "_redirects").read_text(encoding="utf-8") == (
        "/plugins/family/ /family/ 301\n/plugins/family /family/ 301\n"
    )
    # One rule sends every link there: the card, the plugin list, a skill's Back and crumbs.
    assert site._plugin_href("family") == "/family/"
    assert site._plugin_href("engineering") == "/plugins/engineering/"
    for page in (output / "index.html", output / "start" / "index.html"):
        text = page.read_text(encoding="utf-8")
        assert 'href="/family/"' in text and 'href="/plugins/family/"' not in text
    skill = (output / "plugins" / "family" / "qa-workflow" / "index.html").read_text(
        encoding="utf-8"
    )
    assert BACK.format("/family/") in skill
    assert '<a href="/family/">family</a>' in skill and '/plugins/family/"' not in skill
    for path in output.rglob("index.html"):
        assert 'href="/plugins/family/"' not in path.read_text(encoding="utf-8"), path
    # Every other plugin keeps its own page and its plain heading.
    text = (output / "plugins" / "engineering" / "index.html").read_text(encoding="utf-8")
    assert '<h1 class="title-xl">engineering</h1>' in text
    assert '<h1 class="title family-word">' not in text


def test_the_family_page_is_the_plugin_page_too(mini_repo, tmp_path):
    _with_family(mini_repo)
    page = (_build(mini_repo, tmp_path) / "family" / "index.html").read_text(encoding="utf-8")
    assert "/plugin install family@mini" in page
    # The same finder the plugin page uses, over the family skills.
    assert 'id="finder"' in page and 'id="find"' in page and 'id="list"' in page
    assert '<li data-name="qa-workflow"><a href="/plugins/family/qa-workflow/">' in page
    assert "2 skills" in page
    # The subagents, in stage order, each with the first clause of its description.
    agents = page.split('<ul class="family-agents">', 1)[1].split("</ul>", 1)[0]
    assert agents.index("framer") < agents.index("inspector")
    assert "— Turn a vague request into a frame</li>" in agents
    assert "— Inspect a change against its frame</li>" in agents
    assert 'href="/family/example/">See one slice end to end</a>' in page


def test_the_family_stages_open_to_the_agent_and_where_each_verdict_goes(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "family" / "index.html").read_text(encoding="utf-8")
    stages = page.split('<ol class="family-stages">', 1)[1].split("</ol>", 1)[0]
    assert stages.count("<details>") == 6 and stages.count("<summary>") == 6
    for letter, name, _ in site.FAMILY_STAGES:
        detail = site.FAMILY_DETAILS[letter]
        item = stages.split(f'<li class="stage-{letter.lower()}"', 1)[1].split("</li>", 1)[0]
        assert f"<h3>{name}</h3>" in item
        assert f"<dd><code>{detail['agent']}</code></dd>" in item
        assert detail["question"] in item and "Waivable" in item
        for word, target in detail["verdicts"]:
            assert f"<dt><code>{word}</code></dt><dd>→ {target}</dd>" in item
    # The routing table is the source: a diverged build goes back to architect.
    assert "<dt><code>DIVERGED</code></dt><dd>→ architect, never maker again</dd>" in stages
    assert "Yes, when the slice carries no hard-to-reverse decision" in stages


def test_the_profile_picker_is_four_radios_in_a_labelled_group_with_no_default(mini_repo, tmp_path):
    _with_family(mini_repo)
    page = (_build(mini_repo, tmp_path) / "family" / "index.html").read_text(encoding="utf-8")
    group = page.split("<fieldset>", 1)[1].split("</fieldset>", 1)[0]
    assert "<legend>Who is running it?</legend>" in group
    radios = re.findall(r'<label class="chip"><input type="radio" name="profile" value="(\w+)">'
                        r" <span>(\w+)</span></label>", group)  # fmt: skip
    assert radios == [("solo", "Solo"), ("developer", "Developer"), ("qa", "QA"), ("team", "Team")]
    assert "checked" not in group
    # Each profile names the skill it starts from, linked when the plugin ships it.
    assert 'starts from <a href="/plugins/family/qa-workflow/">qa-workflow</a>' in page
    assert "starts from <code>solo-development</code>" in page
    # What each profile owns, per the profile skills.
    owns = {
        letter: re.search(rf'<li class="stage-{letter.lower()}" data-own="([^"]*)"', page).group(1)
        for letter, _, _ in site.FAMILY_STAGES
    }
    assert owns["F"] == "solo developer team" and owns["I"] == "solo qa team"
    assert owns["L"] == "solo team" and owns["Y"] == "solo developer team"
    assert 'data-feeds="qa"' in page
    css = site.site_style.CSS
    assert '.family-flow:has(input[value="developer"]:checked)' in css and "@@" not in css


def test_the_slice_checklist_has_one_box_per_gate_and_a_script_that_survives_no_storage(
    mini_repo, tmp_path
):
    page = (_build(mini_repo, tmp_path) / "family" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<input type="checkbox" data-gate="(\w)"', page) == list("family")
    for _, detail in site.FAMILY_DETAILS.items():
        assert detail["question"] in page.split("Run a slice", 1)[1]
    assert "data-slice-reset" in page
    script = site.site_style.FAMILY_SCRIPT
    assert script.strip() in page and script.count('"family-slice"') == 1
    # Every storage call is guarded, so a blocked store leaves working boxes.
    for call in re.findall(r"localStorage\.\w+", script):
        before = script.split(call, 1)[0]
        assert before.rfind("try {") > before.rfind("} catch"), call


def test_the_family_example_walks_one_slice_through_all_six_stages(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    page = (output / "family" / "example" / "index.html").read_text(encoding="utf-8")
    assert BACK.format("/family/") in page
    assert '<h1 class="title">One slice, end to end</h1>' in page
    sections = re.findall(r'<section class="example-stage stage-(\w)">', page)
    assert sections == list("family")
    assert page.count("Verdict:") == 6
    assert "FIX, then PASS" in page and "placeholder text" in page
    assert 'href="/family/">FAMILY page</a>' in page
    # No vendor or AI product is named.
    for word in ("Claude", "Anthropic", "OpenAI", "Cloudflare", "GitHub", "Playwright"):
        main = page.split('<main id="content">', 1)[1].split("</main>", 1)[0]
        assert word.lower() not in main.lower(), word


def test_every_page_is_written_beside_the_archives(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    for path in (
        "index.html",
        "404.html",
        "errors/403.html",
        "errors/500.html",
        "errors/502.html",
        "errors/503.html",
        "family/index.html",
        "family/example/index.html",
        "start/index.html",
        "workflows/index.html",
        "examples/index.html",
        "quality/index.html",
        "plugins/engineering/index.html",
        "plugins/engineering/alpha/index.html",
        "plugins/engineering/beta/index.html",
    ):
        assert (output / path).is_file(), path
    # Nothing but the archives lives under skills/.
    assert sorted(p.name for p in (output / "skills").iterdir()) == ["alpha.skill", "beta.skill"]
    index = (output / "index.html").read_text(encoding="utf-8")
    # The index lists plugins, spelled out, and each one leads to its own page; the
    # skills are one level further down.
    assert "<h1>One plugin. Install <span>only the ones</span> you want.</h1>" in index
    assert 'href="/plugins/engineering/"' in index and 'href="skills/' not in index
    assert 'href="/plugins/engineering/alpha/"' not in index
    assert 'data-skills="alpha beta"' in index and "2 skills" in index
    assert "Find a plugin" in index and "Nothing matches that name." in index
    plugin = (output / "plugins" / "engineering" / "index.html").read_text(encoding="utf-8")
    assert (
        'href="/plugins/engineering/alpha/"' in plugin
        and 'href="/plugins/engineering/beta/"' in plugin
    )
    assert "/plugin install engineering@mini" in plugin and "<h1" in plugin
    assert 'href="/"' in plugin and "Find a skill" in plugin


def test_navigation_is_root_relative_and_marks_the_current_page(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    start = (output / "start" / "index.html").read_text(encoding="utf-8")
    footer = start.split('<footer class="site-footer">', 1)[1]
    for href in (
        "/family/",
        "/start/",
        "/workflows/",
        "/examples/",
        "/quality/",
        "/portable-skills.zip",
    ):
        assert f'href="{href}"' in footer
    assert 'href="/marketplace.json"' in footer
    assert 'href="portable-skills.zip"' not in start and 'href="marketplace.json"' not in start
    # The header carries the four outside links and nothing else; the pages are in the footer.
    header = start.split("</header>", 1)[0]
    assert "Repository" in header and "Manifest" in header
    assert "/start/" not in header and "Workflows" not in header
    assert start.count('aria-current="page">') == 1
    assert 'href="/start/" aria-current="page"' in start
    assert 'href="/quality/" aria-current="page"' not in start
    index = (output / "index.html").read_text(encoding="utf-8")
    assert 'aria-current="page">' not in index
    assert "Made by Serhii Zolotov" in start
    # The theme controls are the design's two buttons; there is no text button.
    assert ">Black<" not in start and 'id="theme"' not in start
    assert 'role="switch"' in start and 'aria-label="Dark theme"' in start
    assert 'aria-label="Console theme"' in start
    assert "localStorage.getItem" in start
    # The typefaces come from the site itself: a preload for the body sans, no request to a
    # font host and no stylesheet link at all.
    assert (
        f'<link rel="preload" href="{site.site_style.SANS_URL}" as="font" type="font/woff2" '
        "crossorigin>"
    ) in start
    assert "fonts.googleapis.com" not in start and "preconnect" not in start
    assert '<link rel="stylesheet"' not in start
    # Links off the site say so; links on it do not open a new tab.
    assert 'href="https://github.com/greenblacked/AI/releases" target="_blank"' in start
    assert 'rel="noopener noreferrer"' in start
    assert (
        'href="/start/" target' not in start and 'href="/portable-skills.zip" target' not in start
    )
    # The 404 is served from any path, so its links cannot be relative either.
    missing = (output / "404.html").read_text(encoding="utf-8")
    assert 'href="/start/"' in missing and 'href="portable-skills.zip"' not in missing


def test_the_family_page_is_hand_drawn_with_the_stages_and_profiles(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    page = (output / "family" / "index.html").read_text(encoding="utf-8")
    # The one page not generated from a plugin's own files: a stage timeline and cards.
    assert 'class="family-stages"' in page and 'class="family-profiles"' in page
    for letter, name, _ in site.FAMILY_STAGES:
        assert f">{letter}</span>" in page and f"<h3>{name}</h3>" in page
    for name, _ in site.FAMILY_PROFILES:
        assert f"<h3>{name}</h3>" in page
    assert "/plugin install family@mini" in page
    # The typed heading: one accessible name, the visible letters hidden from it, and a
    # stage class on each letter so the colour follows the stage rather than the order.
    heading = re.search(r'<h1 class="title family-word">(.*?)</h1>', page).group(1)
    assert heading.startswith('<span class="sr-only">The FAMILY workflow</span>')
    assert '<span class="typed" aria-hidden="true">' in heading
    typed = re.findall(
        r'<span class="fl stage-(\w)"><span class="fk">(\w)</span>'
        r'<span class="fd">\.</span></span>',
        heading,
    )
    assert typed == [(letter.lower(), letter) for letter, _, _ in site.FAMILY_STAGES]
    for letter, _, _ in site.FAMILY_STAGES:
        assert f'<li class="stage-{letter.lower()}">' in page
    assert 'href="/family/" aria-current="page"' in page
    assert BACK.format("/") in page


def test_a_skill_page_shows_the_skill_and_neutralises_hostile_content(mini_repo, tmp_path):
    _hostile_skill(mini_repo)
    built = (
        _build(mini_repo, tmp_path) / "plugins" / "engineering" / "alpha" / "index.html"
    ).read_text(encoding="utf-8")
    assert _live_tags(built) <= SAFE_TAGS and "javascript:" not in built.lower()
    _hostile_skill(mini_repo, hostile_owner=True)
    catalogue = _catalogue(mini_repo)
    skill = next(item for item in catalogue.skills if item.name == "alpha")
    page = site.render_skill(skill, catalogue, "v9")
    assert "<h1>alpha</h1>" in page
    assert 'href="/skills/alpha.skill"' in page
    assert (
        'href="https://github.com/greenblacked/AI/tree/main/plugins/engineering/skills/alpha"'
        in page
    )
    assert "/plugin install engineering@mini" in page
    assert "Read, Bash(git:*)" in page
    assert "Do the alpha thing end to end" in page
    # Headings drop below the page h1, and "Home" does not take the header button's id.
    assert '<h2 id="alpha">Alpha</h2>' in page and 'id="home-1"' in page
    assert page.count('id="home"') == 1
    # The body's own markup arrives escaped, never live.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "&lt;b&gt;not bold&lt;/b&gt;" in page
    assert _live_tags(page) <= SAFE_TAGS
    assert "<script>alert" not in page
    for target in re.findall(r'href="([^"]*)"', page):
        assert not target.lower().startswith(("javascript:", "data:", "vbscript:")), target
        assert ".." not in target, target
    assert "javascript:" not in page.lower()
    # The relative link and the one that stays inside the repository both become GitHub links.
    assert (
        "https://github.com/greenblacked/AI/blob/main/plugins/engineering/skills/alpha/"
        "references/deep.md" in page
    )
    assert "https://github.com/greenblacked/AI/blob/main/etc/passwd" in page
    # The reference list, and both halves of the eval set.
    assert "<code>references/deep.md</code>" in page
    assert "Fires on" in page and "Goes elsewhere" in page
    assert "alpha says &lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert 'href="/plugins/engineering/beta/"' in page
    assert "<code>reader</code> (subagent)" in page
    assert "&quot;&gt;&lt;script&gt;x&lt;/script&gt;" in page
    assert "bad owner" in page and "no owner" in page


def test_a_skill_with_no_body_references_or_evals_still_has_a_page(mini_repo):
    directory = mini_repo / "plugins" / "engineering" / "skills" / "beta"
    (directory / "evals" / "trigger-eval.json").write_text("not json", encoding="utf-8")
    (directory / "SKILL.md").write_text("---\nname: beta\n---\n", encoding="utf-8")
    catalogue = _catalogue(mini_repo)
    skill = next(item for item in catalogue.skills if item.name == "beta")
    page = site.render_skill(skill, catalogue, "v9")
    assert "<h1>beta</h1>" in page and "References" not in page and "Fires on" not in page
    assert "Allowed tools" not in page


def test_a_skill_whose_frontmatter_cannot_be_read_is_still_listed(mini_repo):
    path = mini_repo / "plugins" / "engineering" / "skills" / "beta" / "SKILL.md"
    path.write_text("no frontmatter here\n\n# Heading\n", encoding="utf-8")
    catalogue = _catalogue(mini_repo)
    skill = next(item for item in catalogue.skills if item.name == "beta")
    assert skill.description == "" and "no frontmatter here" in skill.body
    assert site._front(mini_repo / "missing.md") == ({}, "")
    path.write_bytes(b"\xff\xfe")
    assert site._front(path) == ({}, "")
    assert site._queries(mini_repo / "missing.json") == []


def test_start_builds_without_the_usage_guide_and_renders_it_when_present(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "start" / "index.html").read_text(encoding="utf-8")
    assert "/plugin marketplace add greenblacked/AI" in page
    assert "/plugin install engineering@mini" in page
    assert "/reload-plugins" in page
    assert 'href="/portable-skills.zip"' in page
    assert "Using the skills" not in page
    (mini_repo / "docs").mkdir()
    (mini_repo / "docs" / "using.md").write_text(
        "# Using the skills\n\nSee [the README](../README.md#top) and [x](javascript:alert(1)).\n"
        "\n## Install\n\n<script>alert(1)</script>\n"
        "\nJump to [the Claude Code part](#claude-code).\n\n## Claude Code\n\nThe guide's own.\n",
        encoding="utf-8",
    )
    page = (_build(mini_repo, tmp_path) / "start" / "index.html").read_text(encoding="utf-8")
    assert "<h2" in page and "Using the skills" in page
    assert "https://github.com/greenblacked/AI/blob/main/README.md#top" in page
    assert "javascript:" not in page and "<script>alert" not in page
    # The generated install section must not take the guide's own anchors.
    assert page.count('id="claude-code"') == 1
    assert re.search(r'id="claude-code">Claude Code</h\d>', page)
    assert page.index('id="claude-code"') > page.index("Using the skills")
    assert 'href="#claude-code"' in page
    # An empty or unreadable guide is left out rather than failing the build.
    (mini_repo / "docs" / "using.md").write_text("  \n", encoding="utf-8")
    page = (_build(mini_repo, tmp_path) / "start" / "index.html").read_text(encoding="utf-8")
    assert "Using the skills" not in page


def test_workflows_lists_commands_and_subagents_by_plugin(mini_repo, tmp_path):
    commands = mini_repo / "plugins" / "engineering" / "commands"
    commands.mkdir()
    (commands / "ship-it.md").write_text(
        "---\ndescription: Ship <b>it</b>\nargument-hint: '[branch]'\n"
        "disable-model-invocation: true\n---\n\nDo it.\n",
        encoding="utf-8",
    )
    (commands / "bad name.md").write_text("---\ndescription: x\n---\n", encoding="utf-8")
    extra = mini_repo / "plugins" / "orphan" / "agents"
    extra.mkdir(parents=True)
    (extra / "lone.md").write_text("---\nname: lone\ndescription: Alone.\n---\n", encoding="utf-8")
    page = (_build(mini_repo, tmp_path) / "workflows" / "index.html").read_text(encoding="utf-8")
    assert "<code>/engineering:ship-it</code>" in page and "<code>[branch]</code>" in page
    assert "<code>/ship-it</code>" not in page
    assert "Ship &lt;b&gt;it&lt;/b&gt;" in page and "<b>it</b>" not in page
    assert (
        "https://github.com/greenblacked/AI/blob/main/plugins/engineering/commands/ship-it.md"
        in page
    )
    assert "bad name" not in page
    assert "<code>reader</code>" in page and "<code>lone</code>" in page
    assert "<h2 " in page and "How they fit together" in page
    assert "2 skills here" in page and "1 command here" in page


def test_workflows_says_so_when_nothing_ships_but_skills(mini_repo, tmp_path):
    for path in (mini_repo / "plugins" / "engineering" / "agents").rglob("*"):
        if path.is_file():
            path.unlink()
    page = (_build(mini_repo, tmp_path) / "workflows" / "index.html").read_text(encoding="utf-8")
    assert "No subagents or slash commands ship in this build." in page


def test_examples_renders_the_readme_week_and_up_to_three_queries_per_skill(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "examples" / "index.html").read_text(encoding="utf-8")
    assert "What a real week looks like" not in page
    assert page.count("You say:") == 6  # three each for alpha and beta
    assert "alpha positive 0" in page and "alpha positive 3" not in page
    assert 'href="/plugins/engineering/alpha/"' in page
    (mini_repo / "README.md").write_text(
        "# Title\n\n## Before\n\nno\n\n## What a real week looks like\n\nMonday <i>x</i>.\n\n"
        "```\n## not a heading\n```\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\n## After\n\nno\n",
        encoding="utf-8",
    )
    page = (_build(mini_repo, tmp_path) / "examples" / "index.html").read_text(encoding="utf-8")
    assert "What a real week looks like" in page and "Monday &lt;i&gt;x&lt;/i&gt;." in page
    assert "## not a heading" in page and "<table>" in page
    assert "Before" not in page and "After" not in page


def test_examples_degrades_to_a_notice_when_there_is_nothing_to_show(mini_repo, tmp_path):
    for skill in ("alpha", "beta"):
        (
            mini_repo / "plugins" / "engineering" / "skills" / skill / "evals" / "trigger-eval.json"
        ).unlink()
    page = (_build(mini_repo, tmp_path) / "examples" / "index.html").read_text(encoding="utf-8")
    assert "No examples are available in this build." in page


def test_readme_section_stops_at_the_next_heading_and_handles_absence():
    text = "## A\n\none\n\n~~~\n## inside\n~~~\n\n## B\n\ntwo\n"
    assert site.readme_section(text, "A") == "## A\n\none\n\n~~~\n## inside\n~~~"
    assert site.readme_section(text, "B") == "## B\n\ntwo"
    assert site.readme_section(text, "C") is None
    assert site.readme_section("", "A") is None


def test_quality_counts_come_from_the_repository(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "quality" / "index.html").read_text(encoding="utf-8")
    assert "Quality evidence" in page
    assert re.search(r"Skills</th><td class=\"num\">2<", page)
    assert re.search(r"Subagents</th><td class=\"num\">1<", page)
    assert re.search(r"Slash commands</th><td class=\"num\">0<", page)
    assert re.search(r"Eval sets</th><td class=\"num\">3<", page)  # two skills and one subagent
    assert re.search(r"Queries</th><td class=\"num\">48<", page)
    assert re.search(r"Should fire</th><td class=\"num\">24<", page)
    assert re.search(r"Should not fire</th><td class=\"num\">24<", page)
    assert re.search(r"named owner</th><td class=\"num\">12<", page)
    assert "actions" in page and "docs/ci.md" not in page
    # Every optional source is absent here, and none of its sections appears.
    for absent in ("Description listing", "Gates", "What review has caught"):
        assert absent not in page


def test_quality_reports_each_source_that_exists(mini_repo, tmp_path):
    (mini_repo / "listing-budget.json").write_text(
        json.dumps({"plugins": {"engineering": 5000}}), encoding="utf-8"
    )
    (mini_repo / "pyproject.toml").write_text(
        "[tool.coverage.report]\nfail_under = 95  # floor\n", encoding="utf-8"
    )
    cases = mini_repo / ".claude" / "agents" / "benchmarks" / "reviewer"
    for name in ("one", "two"):
        (cases / name).mkdir(parents=True)
        (cases / name / "case.json").write_text("{}", encoding="utf-8")
    (cases / "three").mkdir()
    (mini_repo / "docs").mkdir()
    (mini_repo / "docs" / "ci.md").write_text("# CI\n", encoding="utf-8")
    (mini_repo / "docs" / "review-lessons.md").write_text(
        "# Lessons\n\n### First <b>class</b>\n\n```\n### not a title\n```\n\n### Second\n\n###\n",
        encoding="utf-8",
    )
    page = (_build(mini_repo, tmp_path) / "quality" / "index.html").read_text(encoding="utf-8")
    assert "Description listing" in page and "5,000" in page
    assert re.search(r"Test coverage floor</th><td class=\"num\">95%<", page)
    assert re.search(r"Reviewer benchmark cases</th><td class=\"num\">2<", page)
    assert "<li>First &lt;b&gt;class&lt;/b&gt;</li>" in page and "<li>Second</li>" in page
    assert "not a title" not in page
    assert "blob/main/docs/ci.md" in page and "greenblacked/AI/actions" in page


def test_quality_tolerates_malformed_sources(mini_repo, tmp_path):
    (mini_repo / "listing-budget.json").write_text("{", encoding="utf-8")
    (mini_repo / "pyproject.toml").write_text(
        "[tool.coverage.report]\nfloor = x\n", encoding="utf-8"
    )
    page = (_build(mini_repo, tmp_path) / "quality" / "index.html").read_text(encoding="utf-8")
    assert "Description listing" not in page and "Test coverage floor" not in page
    (mini_repo / "listing-budget.json").write_text(
        json.dumps({"plugins": {"engineering": True}}), encoding="utf-8"
    )
    page = (_build(mini_repo, tmp_path) / "quality" / "index.html").read_text(encoding="utf-8")
    assert "Description listing" in page and "—" in page


def test_eval_totals_ignore_entries_that_are_not_queries():
    sets = [
        [
            {"query": "a", "should_trigger": True},
            {"query": "b", "should_trigger": False, "expected": "x"},
            {"query": "c", "should_trigger": False, "expected": "  "},
            {"query": "d"},
        ]
    ]
    assert site.eval_totals(sets) == {
        "sets": 1,
        "queries": 3,
        "positives": 1,
        "negatives": 2,
        "routed": 1,
    }
    assert site.eval_totals([])["queries"] == 0


def test_a_skill_directory_that_is_not_one_path_component_is_refused(mini_repo, tmp_path):
    odd = mini_repo / "plugins" / "engineering" / "skills" / "-odd"
    odd.mkdir()
    (odd / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="path component"):
        site.build(mini_repo, tmp_path / "site", "v1")
    assert not (tmp_path / "site").exists()


def test_two_skills_with_one_name_are_refused_before_anything_is_written(mini_repo, tmp_path):
    other = mini_repo / "plugins" / "second"
    (other / ".claude-plugin").mkdir(parents=True)
    (other / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    write_skill(mini_repo, "second", "alpha", evals=eval_set("alpha"))
    with pytest.raises(SystemExit, match="share a name"):
        site.build(mini_repo, tmp_path / "site", "v1")
    assert not (tmp_path / "site").exists()


def test_a_missing_icon_is_refused_before_the_previous_build_is_touched(
    mini_repo, tmp_path, monkeypatch
):
    output = _build(mini_repo, tmp_path)
    before = sorted(p.relative_to(output) for p in output.rglob("*"))
    monkeypatch.setattr(site, "SITE_ASSETS", tmp_path / "no-assets")
    with pytest.raises(SystemExit, match="cannot read the site icon favicon.png"):
        site.build(mini_repo, output, "v2")
    assert sorted(p.relative_to(output) for p in output.rglob("*")) == before
    assert (output / "version.txt").read_text(encoding="utf-8") != "v2\n"


def test_plugin_blurbs_fall_back_to_the_plugin_manifest(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "start" / "index.html").read_text(encoding="utf-8")
    assert "<code>engineering</code></a> — 2 skills. test" in page
    assert site._blurb(mini_repo, "nowhere") == ""


def test_the_real_repository_builds_every_page_and_renders_every_markdown_source(tmp_path):
    output = tmp_path / "real"
    site.build(REPO, output, "dev")
    pages = sorted(output.rglob("index.html"))
    skills = list((REPO / "plugins").glob("*/skills/*/SKILL.md"))
    plugins = list((REPO / "plugins").glob("*/skills"))
    # The index, family, its example, start, workflows, examples, quality and offline; then
    # a page per skill and per plugin, except family, whose page is /family/ and not its own.
    assert len(pages) == len(skills) + len(plugins) - 1 + 8
    assert not (output / "plugins" / "family" / "index.html").exists()
    assert (output / "plugins" / "family" / "family-workflow" / "index.html").is_file()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert _live_tags(text) <= SAFE_TAGS, page
        assert "javascript:" not in text.lower(), page
        assert text.count(' id="home"') == 1, page
        ids = re.findall(r' id="([^"]+)"', text)
        assert len(ids) == len(set(ids)), (page, sorted({i for i in ids if ids.count(i) > 1}))
    assert (output / "plugins" / "coding" / "code-review" / "index.html").is_file()
    # Every link within a page lands on a heading that page has.
    for page in pages:
        text = page.read_text(encoding="utf-8")
        ids = set(re.findall(r' id="([^"]+)"', text))
        for fragment in re.findall(r'href="#([^"]+)"', text):
            assert fragment in ids, (page, fragment)
    start = (output / "start" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'id="claude-code">Claude Code</h\d>', start)
    guide_title = (REPO / "docs" / "using.md").read_text(encoding="utf-8").split("\n", 1)[0]
    assert start.index('id="claude-code"') > start.index(html.escape(guide_title.lstrip("# ")))
    # Every link to somewhere on the site leads to a page or file that was built.
    for page in pages:
        for target in re.findall(r'href="(/[^"#?]*)', page.read_text(encoding="utf-8")):
            local = output / target.lstrip("/")
            assert local.is_file() or (local / "index.html").is_file(), (page, target)


def test_versions_that_are_not_a_single_token_are_refused(mini_repo, tmp_path):
    for raw in ("", "../etc", "has space", "a" * 81, ".hidden"):
        with pytest.raises(SystemExit):
            site.build(mini_repo, tmp_path / "site", raw)


def test_a_missing_or_nameless_manifest_is_refused(mini_repo, tmp_path):
    manifest = mini_repo / ".claude-plugin" / "marketplace.json"
    manifest.unlink()
    with pytest.raises(SystemExit, match="no marketplace"):
        site.build(mini_repo, tmp_path / "site", "v1")
    manifest.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit, match="not JSON"):
        site.build(mini_repo, tmp_path / "site", "v1")
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="no string name"):
        site.build(mini_repo, tmp_path / "site", "v1")


def test_the_repository_itself_and_a_foreign_directory_are_not_deleted(mini_repo, tmp_path):
    with pytest.raises(SystemExit, match="repository root"):
        site.build(mini_repo, mini_repo, "v1")
    assert (mini_repo / "LICENSE").is_file()
    foreign = tmp_path / "notes"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit, match="not a previous"):
        site.build(mini_repo, foreign, "v1")
    assert (foreign / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_home_and_a_parent_of_the_repository_are_unsafe(mini_repo):
    assert site.unsafe_output(mini_repo, Path.home()) == "it is the home directory"
    assert "contains it" in site.unsafe_output(mini_repo, mini_repo.parent)


def test_plugins_the_manifest_does_not_name_are_still_listed():
    groups = site._ordered_groups(
        {"plugins": [{"name": "beta"}, "nope", {"name": 1}, {"name": "missing"}]},
        {"alpha": ["a.skill"], "beta": ["b.skill", "a.skill"]},
    )
    assert groups == [("beta", ["a.skill", "b.skill"]), ("alpha", ["a.skill"])]


def test_plugins_that_are_not_a_list_are_still_listed():
    groups = site._ordered_groups({"plugins": "nope"}, {"alpha": ["a.skill"]})
    assert groups == [("alpha", ["a.skill"])]


def test_a_failed_portable_export_is_refused(mini_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(site.export_portable, "export", lambda _root, _exported: 2)
    with pytest.raises(SystemExit, match="portable export failed"):
        site.build(mini_repo, tmp_path / "site", "v1")


def test_the_real_pin_matches_the_lockfile():
    pin = load_script("check_wrangler_pin.py")
    assert pin.problems(REPO, "4.149.0") == []
    assert any("not" in item for item in pin.problems(REPO, "0.0.1"))


def test_a_lockfile_without_an_integrity_is_refused(tmp_path):
    pin = load_script("check_wrangler_pin.py")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "package.json").write_text(
        json.dumps({"dependencies": {"wrangler": "1.2.3"}}), encoding="utf-8"
    )
    (deploy / "package-lock.json").write_text(
        json.dumps({"packages": {"node_modules/wrangler": {"version": "1.2.3"}}}),
        encoding="utf-8",
    )
    found = pin.problems(tmp_path, "1.2.3")
    assert any("integrity" in item for item in found)
    assert pin.problems(tmp_path / "missing", "1.2.3")


def test_a_pin_that_is_not_json_is_refused(tmp_path, capsys):
    pin = load_script("check_wrangler_pin.py")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "package.json").write_text("{", encoding="utf-8")
    (deploy / "package-lock.json").write_text("{}", encoding="utf-8")
    assert any("not JSON" in item for item in pin.problems(tmp_path, "1"))
    (deploy / "package.json").write_text("[]", encoding="utf-8")
    (deploy / "package-lock.json").write_text("[]", encoding="utf-8")
    assert pin.problems(tmp_path, "1")
    assert pin.main(["--version", "0.0.1", str(REPO)]) == 1
    assert "::error::" in capsys.readouterr().err


def test_a_repository_with_no_skills_is_refused(tmp_path):
    root = tmp_path / "empty"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text('{"name": "x"}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="no skills"):
        site.build(root, tmp_path / "site", "v1")


def test_mains_report_the_pin_and_the_deploy_url(mini_repo, tmp_path, capsys):
    output = tmp_path / "out"
    assert site.main(["--version", "dev", "--out", str(output), str(mini_repo)]) == 0
    assert "dev" in capsys.readouterr().out
    pin = load_script("check_wrangler_pin.py")
    assert pin.main(["--version", "", str(REPO)]) == 1
    assert pin.main(["--version", "4.149.0", str(REPO)]) == 0
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(
        json.dumps({"type": "deploy", "targets": ["https://greenblacked-ai.account.workers.dev"]})
        + "\n",
        encoding="utf-8",
    )
    assert reader.main([str(log)]) == 0
    assert "url=https://greenblacked-ai.account.workers.dev" in capsys.readouterr().out
    assert reader.main([str(tmp_path / "missing")]) == 1
    version = "12345678-1234-1234-1234-123456789abc"
    text = "\n".join(
        [
            "not json",
            json.dumps({"type": "wrangler-session", "version": 1}),
            json.dumps(
                {
                    "type": "deploy",
                    "targets": [
                        "https://abc.greenblacked-ai.account.workers.dev",
                        "http://greenblacked-ai.account.workers.dev",
                        "https://greenblacked-ai.account.workers.dev/extra",
                        "https://greenblacked-ai.account.workers.dev",
                        "https://example.com",
                    ],
                    "version_id": version,
                }
            ),
        ]
    )
    url, found = reader.parse(text)
    assert url == "https://greenblacked-ai.account.workers.dev"
    assert found == version
    with pytest.raises(SystemExit):
        reader.parse("{}\n")
    # A version id that is not a UUID is dropped rather than written into an output file.
    loose = json.dumps(
        {
            "type": "deploy",
            "targets": ["https://greenblacked-ai.account.workers.dev"],
            "version_id": "not a uuid\nurl=https://evil.example",
        }
    )
    assert reader.parse(loose)[1] == ""


def _preview_line(urls):
    return json.dumps({"type": "preview", "version": 1, "preview_urls": urls}) + "\n"


def test_a_preview_log_reports_the_workers_dev_and_stage_hosts(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(
        "not json\n"
        + _preview_line(["https://old.account.workers.dev"])
        + _preview_line(
            [
                "https://stage-ai.account.workers.dev",
                "https://stage.ai.szolotov.com",
                "https://other.ai.szolotov.com",
            ]
        ),
        encoding="utf-8",
    )
    assert reader.main(["--preview", str(log)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "url=https://stage-ai.account.workers.dev",
        "custom_url=https://stage.ai.szolotov.com",
    ]
    assert reader.parse_preview(log.read_text(encoding="utf-8")) == (
        "https://stage-ai.account.workers.dev",
        "https://stage.ai.szolotov.com",
    )


def test_a_preview_log_without_the_custom_host_leaves_it_empty(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(_preview_line(["https://stage-ai.account.workers.dev"]), encoding="utf-8")
    assert reader.main(["--preview", str(log)]) == 0
    assert capsys.readouterr().out == "url=https://stage-ai.account.workers.dev\n"
    # A different host under the custom domain is reported as such, not as the stage host.
    assert reader.parse_preview(_preview_line(["https://x.ai.szolotov.com"])) == (
        "",
        "https://x.ai.szolotov.com",
    )


def test_a_preview_log_with_no_line_or_no_acceptable_url_is_an_error(tmp_path):
    reader = load_script("read_wrangler_deploy.py")
    deploy_only = json.dumps({"type": "deploy", "targets": ["https://a.b.workers.dev"]})
    with pytest.raises(SystemExit):
        reader.parse_preview(deploy_only + "\n")
    with pytest.raises(SystemExit):
        reader.parse_preview("")
    with pytest.raises(SystemExit):
        reader.parse_preview(json.dumps({"type": "preview", "preview_urls": "x"}))
    # Only the last preview line counts: an earlier good one does not cover a later empty one.
    with pytest.raises(SystemExit):
        reader.parse_preview(_preview_line(["https://a.b.workers.dev"]) + _preview_line([]))
    assert reader.main(["--preview", str(tmp_path / "missing")]) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://stage.ai.szolotov.com",
        "https://user@stage.ai.szolotov.com",
        "https://user:pw@stage.ai.szolotov.com",
        "https://stage.ai.szolotov.com:8443",
        "https://stage.ai.szolotov.com/path",
        "https://stage.ai.szolotov.com/?q=1",
        "https://stage.ai.szolotov.com#frag",
        "https://stage.ai.szolotov.com.evil.com",
        "https://evil.com/stage.ai.szolotov.com",
        "https://notai.szolotov.com",
        "https://stage.szolotov.com",
        "https://szolotov.com",
        "https://workers.dev",
        "https://a.workers.dev.evil.com",
        "https://a.b.workers.dev:443",
        "https://example.com",
        "https://STAGE.ai.szolotov.com",
        "https://a.b.workers.dev\nurl=https://evil.example",
    ],
)
def test_hostile_preview_urls_are_dropped(url):
    reader = load_script("read_wrangler_deploy.py")
    with pytest.raises(SystemExit):
        reader.parse_preview(_preview_line([url]))
    # One hostile entry does not hide a good one next to it.
    good = "https://stage.ai.szolotov.com"
    assert reader.parse_preview(_preview_line([url, good])) == ("", good)


def test_the_deploy_log_keeps_only_a_workers_dev_url(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    version = "12345678-1234-1234-1234-123456789abc"
    text = "\n".join(
        [
            "",
            json.dumps({"type": "deploy", "targets": "https://a.b.workers.dev"}),
            json.dumps(
                {
                    "type": "deploy",
                    "targets": ["https://not.a.worker.example", "https://name.account.workers.dev"],
                    "version_id": version,
                }
            ),
        ]
    )
    url, found = reader.parse(text)
    assert url == "https://name.account.workers.dev"
    assert found == version
    log = tmp_path / "wrangler.jsonl"
    log.write_text(text, encoding="utf-8")
    assert reader.main([str(log)]) == 0
    assert f"version_id={version}" in capsys.readouterr().out


ACTIVE_VERSION = "0f1e2d3c-4b5a-6978-8a9b-acbdcedf0011"


def _deployment(*versions):
    return json.dumps(
        {
            "id": "deployment",
            "source": "wrangler",
            "strategy": "percentage",
            "versions": [{"version_id": vid, "percentage": pct} for vid, pct in versions],
        }
    )


WORKERS_DEV = "https://greenblacked-ai.account.workers.dev"
PRODUCTION = "https://ai.szolotov.com"
# Wrangler's `renderRoute` writes a custom domain as the bare pattern, never with a scheme;
# only workers.dev targets get `https://`. The first string is what the live v0.1.0 deploy
# logged for deploy/wrangler.json's route.
CUSTOM_TARGET = "ai.szolotov.com (custom domain) [previews: enabled]"
DEPLOYED = "12345678-1234-1234-1234-123456789abc"


def _deploy_line(targets, **extra):
    return json.dumps({"type": "deploy", "targets": targets, **extra}) + "\n"


def test_the_custom_target_is_what_wrangler_renders_for_the_configured_route():
    config = json.loads((REPO / "deploy" / "wrangler.json").read_text(encoding="utf-8"))
    (route,) = config["routes"]
    assert route["custom_domain"] is True and route["previews_enabled"] is True
    assert f"{route['pattern']} (custom domain) [previews: enabled]" == CUSTOM_TARGET


def test_the_deploy_log_reports_the_production_custom_domain(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(
        _deploy_line([WORKERS_DEV, CUSTOM_TARGET], version_id=DEPLOYED), encoding="utf-8"
    )
    assert reader.main([str(log)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"url={WORKERS_DEV}",
        f"custom_url={PRODUCTION}",
        f"version_id={DEPLOYED}",
    ]
    assert reader.parse_deploy(log.read_text(encoding="utf-8")) == (
        WORKERS_DEV,
        DEPLOYED,
        PRODUCTION,
    )


@pytest.mark.parametrize(
    "target",
    [
        "ai.szolotov.com (custom domain)",
        "ai.szolotov.com (custom domain) [previews: enabled]",
        "ai.szolotov.com (custom domain) [production: enabled, previews: disabled]",
        "ai.szolotov.com (custom domain - zone name: szolotov.com)",
        "ai.szolotov.com (custom domain - zone name: szolotov.com) [previews: enabled]",
        "ai.szolotov.com (custom domain - zone id: 0123456789abcdef0123456789abcdef)",
    ],
)
def test_every_rendering_of_the_production_custom_domain_is_accepted(target):
    reader = load_script("read_wrangler_deploy.py")
    assert reader.parse_deploy(_deploy_line([target, WORKERS_DEV]))[2] == PRODUCTION


def test_a_deploy_without_the_custom_domain_prints_no_custom_url(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(_deploy_line([WORKERS_DEV]), encoding="utf-8")
    assert reader.main([str(log)]) == 0
    assert capsys.readouterr().out == f"url={WORKERS_DEV}\n"
    # Only the last deploy line counts: an earlier custom domain does not cover a later
    # deploy that dropped it.
    text = _deploy_line([WORKERS_DEV, CUSTOM_TARGET]) + _deploy_line([WORKERS_DEV])
    assert reader.parse_deploy(text)[2] == ""


@pytest.mark.parametrize(
    "target",
    [
        "ai.szolotov.com.evil.com (custom domain)",
        "evil.ai.szolotov.com (custom domain)",
        # Attached but serving no production traffic.
        "ai.szolotov.com (custom domain) [production: disabled, previews: enabled]",
        "ai.szolotov.com (custom domain - zone name: szolotov.com) [production: disabled]",
        "stage.ai.szolotov.com (custom domain)",
        "AI.szolotov.com (custom domain)",
        "szolotov.com (custom domain)",
        # A route, not a custom domain: it does not attach the domain.
        "ai.szolotov.com",
        "ai.szolotov.com (zone name: szolotov.com)",
        "ai.szolotov.com/* (zone name: szolotov.com)",
        "ai.szolotov.com [previews: enabled]",
        # Wrangler never writes a custom domain with a scheme, a port or a path.
        "https://ai.szolotov.com",
        "https://ai.szolotov.com (custom domain)",
        "ai.szolotov.com:8443 (custom domain)",
        "ai.szolotov.com/path (custom domain)",
        "ai.szolotov.com  (custom domain)",
        "ai.szolotov.com (custom domains)",
        "ai.szolotov.com (custom domainX)",
        "ai.szolotov.com (CUSTOM DOMAIN)",
        "x ai.szolotov.com (custom domain)",
        "ai.szolotov.com\n(custom domain)",
        "",
        7,
        None,
    ],
)
def test_only_the_exact_production_host_with_the_marker_counts_as_the_custom_domain(target):
    reader = load_script("read_wrangler_deploy.py")
    assert reader.parse_deploy(_deploy_line([WORKERS_DEV, target]))[2] == ""


def test_one_worker_serves_production_and_previews_on_the_custom_domain():
    config = json.loads((REPO / "deploy" / "wrangler.json").read_text(encoding="utf-8"))
    assert config["name"] == "ai"
    assert config["workers_dev"] is True
    assert config["preview_urls"] is True
    assert config["previews"] == {}
    assert config["routes"] == [
        {"pattern": "ai.szolotov.com", "custom_domain": True, "previews_enabled": True}
    ]
    # No environments remain: a second name would be a second Worker.
    assert "env" not in config


def test_the_stage_branch_uploads_a_preview_and_fetches_nothing_behind_access():
    workflow = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "--env" not in workflow
    assert "wrangler rollback" not in workflow
    assert "wrangler deploy --config" not in workflow
    deploy = workflow.split("      - name: Upload the stage Preview\n", 1)[1].split(
        "      - name: Check the stage Preview's address\n", 1
    )[0]
    assert "wrangler preview --config wrangler.json --name stage" in deploy
    assert "WRANGLER_OUTPUT_FILE_PATH" in deploy
    assert 'read_wrangler_deploy.py" --preview' in deploy
    check = workflow.split("      - name: Check the stage Preview's address\n", 1)[1]
    assert "stage_url=https://stage.ai.szolotov.com" in check
    assert "::error::Wrangler did not report ${stage_url} for this Preview" in check
    assert "enable ai.szolotov.com for Preview traffic (docs/ci.md)" in check
    # Stage is behind Cloudflare Access, so the job fetches nothing from it.
    assert "smoke_site.sh" not in workflow
    assert "curl" not in check


def _production_steps():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    cloudflare = workflow.split("  cloudflare:\n", 1)[1]
    names = [
        "Smoke-test the production Worker",
        "Confirm production serves the deployed version",
        "Probe the custom domain (information only)",
        "Roll back the production Worker",
    ]
    marks = [f"      - name: {name}\n" for name in names]
    for earlier, later in zip(marks, marks[1:], strict=False):
        assert cloudflare.index(earlier) < cloudflare.index(later)
    steps = {}
    for mark, following in zip(marks, [*marks[1:], None], strict=True):
        body = cloudflare.split(mark, 1)[1]
        steps[mark.split("name: ", 1)[1].strip()] = (
            body if following is None else body.split(following, 1)[0]
        )
    return cloudflare, steps


def test_production_is_smoked_through_workers_dev_not_the_custom_domain():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "--env" not in workflow
    _cloudflare, steps = _production_steps()
    smoke = steps["Smoke-test the production Worker"]
    assert "WORKERS_DEV_URL: ${{ steps.deploy.outputs.url }}" in smoke
    assert "CUSTOM_URL: ${{ steps.deploy.outputs.custom_url }}" in smoke
    assert 'if [ -z "$WORKERS_DEV_URL" ]' in smoke
    assert "::error::Wrangler reported no workers.dev address for this deploy" in smoke
    assert 'if [ "$CUSTOM_URL" != "$production_url" ]' in smoke
    assert "production_url=https://ai.szolotov.com" in smoke
    assert smoke.count("scripts/smoke_site.sh") == 1
    assert 'scripts/smoke_site.sh "$WORKERS_DEV_URL" "$TAG" greenblacked-ai' in smoke
    # No fetch of the custom domain, and none of the configured URL, in a blocking step.
    assert "curl" not in smoke and "urls=(" not in smoke
    assert "CONFIGURED_URL" not in smoke


def test_production_confirms_the_active_version_before_it_can_roll_back():
    cloudflare, steps = _production_steps()
    confirm = steps["Confirm production serves the deployed version"]
    assert "DEPLOYED_VERSION_ID: ${{ steps.deploy.outputs.version_id }}" in confirm
    assert 'if [ -z "$DEPLOYED_VERSION_ID" ]' in confirm
    assert "wrangler deployments status --config wrangler.json --json" in confirm
    assert '--active-is "$DEPLOYED_VERSION_ID" "$status"' in confirm
    assert "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}" in confirm
    # It runs after the deploy and before the rollback, whose condition still covers it.
    assert cloudflare.index("Deploy the production Worker") < cloudflare.index(
        "Confirm production serves the deployed version"
    )
    rollback = steps["Roll back the production Worker"]
    assert "if: failure() && steps.deploy.outputs.deployed == 'true'" in cloudflare
    assert "wrangler rollback" in rollback


def test_the_custom_domain_probe_is_information_only_and_holds_no_token():
    _cloudflare, steps = _production_steps()
    probe = steps["Probe the custom domain (information only)"]
    assert '"${production_url}/version.txt" || true)' in probe
    assert "--max-time" in probe
    assert "::notice::Bot Fight Mode blocks GitHub runners on ai.szolotov.com" in probe
    assert "exit" not in probe
    # The token reaches only the steps that run wrangler.
    for name in ("Smoke-test the production Worker", "Probe the custom domain (information only)"):
        assert "CLOUDFLARE" not in steps[name]
        assert "secrets." not in steps[name]


def _write_stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -Eeuo pipefail\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _run_step(tmp_path, workflow, step, env, *, subdir=""):
    """Run one workflow step's `run:` block against stub curl, smoke_site.sh and wrangler.

    The stubs record their arguments in ``calls.log`` and answer from ``STUB_*`` variables,
    so a case chooses what the custom domain, workers.dev and the API say.
    """
    work = tmp_path / "work"
    log = tmp_path / "calls.log"
    log.touch()
    _write_stub(
        work / "scripts" / "smoke_site.sh",
        'echo "smoke $*" >> "$STUB_LOG"\nexit "${STUB_SMOKE_RC:-0}"\n',
    )
    _write_stub(
        tmp_path / "bin" / "curl",
        'echo "curl $*" >> "$STUB_LOG"\n'
        'printf "%s" "${STUB_CURL_CODE:-000}"\nexit "${STUB_CURL_RC:-0}"\n',
    )
    _write_stub(
        work / "deploy" / "node_modules" / ".bin" / "wrangler",
        'echo "wrangler $*" >> "$STUB_LOG"\n'
        '[ "${STUB_WRANGLER_RC:-0}" -eq 0 ] || { echo "wrangler failed" >&2; exit 1; }\n'
        'printf "%s" "$STUB_STATUS_JSON"\n',
    )
    script = _extract_run_block(
        (REPO / ".github" / "workflows" / workflow).read_text(encoding="utf-8"), step
    )
    path = os.pathsep.join(
        [str(tmp_path / "bin"), str(Path(sys.executable).parent), "/usr/bin:/bin"]
    )
    result = subprocess.run(  # noqa: S603
        ["bash", "-c", script],  # noqa: S607 - execute the workflow's own shell block
        cwd=work / subdir,
        capture_output=True,
        text=True,
        env={
            "PATH": path,
            "STUB_LOG": str(log),
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_WORKSPACE": str(REPO),
            **env,
        },
        check=False,
    )
    return result, log.read_text(encoding="utf-8").splitlines()


SMOKE = "Smoke-test the production Worker"
CONFIRM = "Confirm production serves the deployed version"
PROBE = "Probe the custom domain (information only)"
PRODUCTION_ENV = {"WORKERS_DEV_URL": WORKERS_DEV, "CUSTOM_URL": PRODUCTION, "TAG": "v0.1.1"}
CONFIRM_ENV = {
    "CLOUDFLARE_API_TOKEN": "token",
    "CLOUDFLARE_ACCOUNT_ID": "account",
    "DEPLOYED_VERSION_ID": DEPLOYED,
    "STUB_STATUS_JSON": _deployment((DEPLOYED, 100)),
}


def test_production_smoke_passes_on_workers_dev_without_fetching_the_custom_domain(tmp_path):
    result, calls = _run_step(tmp_path, "release.yml", SMOKE, PRODUCTION_ENV)
    assert result.returncode == 0, result.stderr
    assert calls == [f"smoke {WORKERS_DEV} v0.1.1 greenblacked-ai"]


def _deploy_outputs(tmp_path, targets):
    """What the deploy step writes to GITHUB_OUTPUT for a wrangler log with these targets."""
    log = tmp_path / "wrangler-output.jsonl"
    log.write_text(_deploy_line(targets, version_id=DEPLOYED), encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(REPO / "scripts" / "read_wrangler_deploy.py"), str(log)],
        capture_output=True,
        text=True,
        check=True,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines())


def test_production_smoke_accepts_the_targets_wrangler_really_logs(tmp_path):
    outputs = _deploy_outputs(tmp_path, [WORKERS_DEV, CUSTOM_TARGET])
    env = {"WORKERS_DEV_URL": outputs["url"], "CUSTOM_URL": outputs["custom_url"], "TAG": "v0.1.1"}
    result, calls = _run_step(tmp_path, "release.yml", SMOKE, env)
    assert result.returncode == 0, result.stdout
    assert calls == [f"smoke {WORKERS_DEV} v0.1.1 greenblacked-ai"]


@pytest.mark.parametrize("target", ["ai.szolotov.com", "https://ai.szolotov.com"])
def test_production_smoke_rejects_a_deploy_that_logged_no_custom_domain(tmp_path, target):
    outputs = _deploy_outputs(tmp_path, [WORKERS_DEV, target])
    assert "custom_url" not in outputs
    env = {"WORKERS_DEV_URL": outputs["url"], "CUSTOM_URL": "", "TAG": "v0.1.1"}
    result, calls = _run_step(tmp_path, "release.yml", SMOKE, env)
    assert result.returncode != 0
    assert calls == []


def test_production_smoke_fails_when_workers_dev_fails(tmp_path):
    result, calls = _run_step(
        tmp_path, "release.yml", SMOKE, {**PRODUCTION_ENV, "STUB_SMOKE_RC": "1"}
    )
    assert result.returncode != 0
    assert calls == [f"smoke {WORKERS_DEV} v0.1.1 greenblacked-ai"]


def test_production_smoke_fails_on_an_empty_workers_dev_url(tmp_path):
    result, calls = _run_step(
        tmp_path, "release.yml", SMOKE, {**PRODUCTION_ENV, "WORKERS_DEV_URL": ""}
    )
    assert result.returncode != 0
    assert "::error::Wrangler reported no workers.dev address" in result.stdout
    assert calls == []


@pytest.mark.parametrize("custom", ["", "https://stage.ai.szolotov.com", "https://other.example"])
def test_production_smoke_fails_when_the_custom_domain_was_not_attached(tmp_path, custom):
    result, calls = _run_step(
        tmp_path, "release.yml", SMOKE, {**PRODUCTION_ENV, "CUSTOM_URL": custom}
    )
    assert result.returncode != 0
    assert "::error::Wrangler did not report https://ai.szolotov.com" in result.stdout
    assert calls == []


def test_the_active_version_check_passes_for_the_deployed_version(tmp_path):
    result, calls = _run_step(tmp_path, "release.yml", CONFIRM, CONFIRM_ENV, subdir="deploy")
    assert result.returncode == 0, result.stderr
    assert calls == ["wrangler deployments status --config wrangler.json --json"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"STUB_STATUS_JSON": _deployment((ACTIVE_VERSION, 100))},
        {"STUB_STATUS_JSON": _deployment((DEPLOYED, 50), (ACTIVE_VERSION, 50))},
        {"STUB_STATUS_JSON": "not json"},
        {"STUB_WRANGLER_RC": "1"},
        {"DEPLOYED_VERSION_ID": ""},
        {"CLOUDFLARE_API_TOKEN": ""},
    ],
    ids=["mismatch", "split", "unreadable", "wrangler-fails", "no-version", "no-token"],
)
def test_the_active_version_check_fails_unless_the_deployed_version_serves_everything(
    tmp_path, overrides
):
    result, _calls = _run_step(
        tmp_path, "release.yml", CONFIRM, {**CONFIRM_ENV, **overrides}, subdir="deploy"
    )
    assert result.returncode != 0


def test_the_custom_domain_probe_never_fails_on_a_403(tmp_path):
    result, calls = _run_step(tmp_path, "release.yml", PROBE, {"STUB_CURL_CODE": "403"})
    assert result.returncode == 0, result.stderr
    assert "answered HTTP 403" in result.stdout
    assert "::notice::Bot Fight Mode blocks GitHub runners on ai.szolotov.com" in result.stdout
    assert len(calls) == 1 and calls[0].endswith("https://ai.szolotov.com/version.txt")
    assert "--max-time" in calls[0]


@pytest.mark.parametrize(
    "env",
    [
        {"STUB_CURL_CODE": "200"},
        {"STUB_CURL_CODE": "502"},
        {"STUB_CURL_CODE": "000", "STUB_CURL_RC": "28"},
    ],
    ids=["200", "502", "timeout"],
)
def test_the_custom_domain_probe_never_fails_on_any_answer(tmp_path, env):
    result, _calls = _run_step(tmp_path, "release.yml", PROBE, env)
    assert result.returncode == 0, result.stderr
    assert "::notice::" not in result.stdout


STAGE = "Check the stage Preview's address"
STAGE_URL = "https://stage.ai.szolotov.com"
STAGE_ENV = {
    "WORKERS_DEV_URL": "https://stage-ai.account.workers.dev",
    "CUSTOM_URL": STAGE_URL,
}


def test_the_preview_check_passes_on_the_stage_host_without_fetching_anything(tmp_path):
    result, calls = _run_step(tmp_path, "deploy.yml", STAGE, STAGE_ENV)
    assert result.returncode == 0, result.stderr
    assert f"Wrangler reported {STAGE_URL} for this Preview" in result.stdout
    assert calls == []


@pytest.mark.parametrize(
    "custom_url",
    ["", "https://ai.szolotov.com", "https://other.ai.szolotov.com", f"{STAGE_URL}/"],
    ids=["missing", "production", "other-preview", "trailing-slash"],
)
def test_the_preview_check_fails_without_the_stage_host(tmp_path, custom_url):
    env = {**STAGE_ENV, "CUSTOM_URL": custom_url}
    result, calls = _run_step(tmp_path, "deploy.yml", STAGE, env)
    assert result.returncode != 0
    assert "::error::Wrangler did not report https://stage.ai.szolotov.com" in result.stdout
    assert calls == []


def test_production_deploys_are_serialized_across_release_tags():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "  group: release-${{ github.ref }}" in workflow
    cloudflare = workflow.split("  cloudflare:\n", 1)[1]
    job_header = cloudflare.split("    steps:\n", 1)[0]
    assert "    needs: release\n" in job_header
    assert (
        "    concurrency:\n      group: production-cloudflare\n      cancel-in-progress: false\n"
    ) in job_header
    assert job_header.count("      group:") == 1


def _run_blocks(workflow: str) -> list[str]:
    """The text of every `run:` step, found by indentation rather than a YAML parser."""
    blocks = []
    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("run:"):
            continue
        indent = len(line) - len(stripped)
        body = [stripped[len("run:") :]]
        for follow in lines[index + 1 :]:
            if follow.strip() and len(follow) - len(follow.lstrip()) <= indent:
                break
            body.append(follow)
        blocks.append("\n".join(body))
    return blocks


def test_release_accepts_a_dispatch_only_on_a_version_tag_ref():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    triggers = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "  push:\n    tags: ['v[0-9]+.[0-9]+.[0-9]+']\n" in triggers
    assert "  workflow_dispatch:\n" in triggers
    assert "inputs:" not in triggers
    release_job = workflow.split("  release:\n", 1)[1].split("  cloudflare:\n", 1)[0]
    cloudflare = workflow.split("  cloudflare:\n", 1)[1]
    for job in (release_job, cloudflare):
        steps = job.split("    steps:\n", 1)[1]
        first = steps.split("\n      - ", 2)[0] if steps.startswith("      - name:") else ""
        assert first.startswith("      - name: Refuse anything but a vX.Y.Z tag"), (
            "the ref guard must be the first step, ahead of checkout"
        )
        assert '[ "$GITHUB_REF_TYPE" != "tag" ]' in first
        assert '[[ "$GITHUB_REF_NAME" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+$ ]]' in first
        assert "set -Eeuo pipefail" in first
        assert "${{" not in first
        assert "persist-credentials: false" in job


def test_cut_release_is_a_main_only_dispatch_with_two_narrow_grants():
    workflow = (REPO / ".github" / "workflows" / "cut-release.yml").read_text(encoding="utf-8")
    assert "\npermissions: {}\n" in workflow
    triggers = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert triggers.startswith("  workflow_dispatch:\n    inputs:\n      version:\n")
    assert "        required: true\n        type: string\n" in triggers
    assert triggers.count("  push:") == 0 and "pull_request" not in triggers
    assert "  group: cut-release\n  cancel-in-progress: false\n" in workflow
    job = workflow.split("jobs:\n", 1)[1]
    header = job.split("    steps:\n", 1)[0]
    # No job-level `if`: a skipped job reports success, so the refusal must be a step.
    assert "    if:" not in header
    assert "    timeout-minutes: 10\n" in header
    permissions = header.split("    permissions:\n", 1)[1].split("    env:\n", 1)[0]
    grants = [line.split("#")[0].strip() for line in permissions.splitlines()]
    grants = [grant for grant in grants if grant]
    assert sorted(grants) == ["actions: write", "contents: write"]
    assert "      VERSION: ${{ inputs.version }}\n" in header
    # A dispatch elsewhere is refused by a visible failing step, the first one.
    guard = job.split("    steps:\n", 1)[1].split("      - uses:", 1)[0]
    assert '[ "$GITHUB_REF" != "refs/heads/main" ]' in guard
    assert "exit 1" in guard
    assert "persist-credentials: false" in workflow
    assert "fetch-depth: 0" in workflow
    assert "cache:" not in workflow.replace("No `cache:`", "")
    assert 'python scripts/release.py check "$VERSION"' in workflow
    assert 'gh workflow run release.yml --ref "v$VERSION"' in workflow
    assert "git push" not in workflow


def test_cut_release_never_interpolates_an_input_into_a_shell_block():
    for name in ("cut-release.yml", "release.yml"):
        workflow = (REPO / ".github" / "workflows" / name).read_text(encoding="utf-8")
        blocks = _run_blocks(workflow)
        assert blocks, name
        for block in blocks:
            assert "${{" not in block, f"{name}: an expression inside run: {block!r}"
            assert "set -Eeuo pipefail" in block, f"{name}: a run: block without strict mode"
        assert "github.event.inputs" not in workflow
        assert workflow.count("${{ inputs.") == (1 if name == "cut-release.yml" else 0)


def test_cut_release_token_is_scoped_to_the_steps_that_call_the_api():
    workflow = (REPO / ".github" / "workflows" / "cut-release.yml").read_text(encoding="utf-8")
    steps = workflow.split("    steps:\n", 1)[1].split("\n      - ")
    with_token = [step for step in steps if "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in step]
    without = [step for step in steps if "GH_TOKEN" not in step]
    assert len(with_token) == 3
    for step in with_token:
        assert "gh " in step
    for step in without:
        assert "gh api" not in step and "gh workflow" not in step


def test_the_smoke_script_rejects_a_url_that_is_not_https():
    script = REPO / "scripts" / "smoke_site.sh"
    refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://example.com", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1
    usage = subprocess.run(  # noqa: S603 - the script under test, no arguments
        [str(script)], capture_output=True, text=True, check=False
    )
    assert usage.returncode == 2


class _Versions(http.server.BaseHTTPRequestHandler):
    """Serves version.txt from a script of answers, then the rest of a good catalogue."""

    def do_GET(self):  # noqa: N802 - the http.server hook name
        server = self.server
        if self.path == "/version.txt":
            server.hits += 1
            index = min(server.hits - 1, len(server.answers) - 1)
            body = (server.answers[index] + "\n").encode()
        elif self.path == "/marketplace.json":
            body = b'{"name": "greenblacked-ai"}'
        elif self.path == "/portable-skills.zip":
            body = b"PK\x03\x04"
        else:
            body = b"<html></html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _smoke_against(answers, version):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Versions)
    server.answers = answers
    server.hits = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = {**os.environ, "SMOKE_SITE_TEST_MODE": "1"}
        result = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [
                str(REPO / "scripts" / "smoke_site.sh"),
                f"http://127.0.0.1:{server.server_address[1]}",
                version,
                "greenblacked-ai",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=120,
        )
    finally:
        server.shutdown()
        server.server_close()
    return result, server.hits


def test_the_smoke_script_waits_out_a_host_serving_the_previous_version():
    result, hits = _smoke_against(["v1", "v1", "v1", "v2"], "v2")
    assert result.returncode == 0, result.stderr
    assert hits == 4


def test_the_smoke_script_fails_when_the_version_never_arrives():
    result, hits = _smoke_against(["v1"], "v2")
    assert result.returncode == 1
    assert "version.txt is 'v1' after 3s (" in result.stderr
    assert "expected 'v2'" in result.stderr
    assert hits >= 2


class _Stalls(http.server.BaseHTTPRequestHandler):
    """Accepts every request and answers nothing until long after the wait is over."""

    def do_GET(self):  # noqa: N802 - the http.server hook name
        time.sleep(30)

    def log_message(self, *args):
        pass


def test_the_smoke_wait_is_bounded_by_time_when_a_host_stalls():
    # A stalled host used to cost every attempt its full request timeout; the wait
    # now ends at its time budget, whatever the host does.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stalls)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [
                str(REPO / "scripts" / "smoke_site.sh"),
                f"http://127.0.0.1:{server.server_address[1]}",
                "v2",
                "greenblacked-ai",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "SMOKE_SITE_TEST_MODE": "1"},
            timeout=60,
        )
    finally:
        server.shutdown()
        server.server_close()
    assert result.returncode == 1
    assert "did not answer" in result.stderr
    assert time.monotonic() - started < 15


def test_the_loopback_hook_accepts_only_a_bare_port():
    script = REPO / "scripts" / "smoke_site.sh"
    for url in ("http://127.0.0.1:1@example.invalid", "http://127.0.0.1:80/x", "http://127.0.0.1:"):
        refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [str(script), url, "v1", "greenblacked-ai"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "SMOKE_SITE_TEST_MODE": "1"},
            timeout=30,
        )
        assert refused.returncode == 1, url
        assert "must be https" in refused.stderr, url


def test_the_loopback_hook_is_off_by_default():
    script = REPO / "scripts" / "smoke_site.sh"
    env = {k: v for k, v in os.environ.items() if k != "SMOKE_SITE_TEST_MODE"}
    refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://127.0.0.1:9", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert refused.returncode == 1
    assert "must be https" in refused.stderr
    # Even in test mode only the loopback address is accepted over http.
    elsewhere = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://example.com", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
        env={**env, "SMOKE_SITE_TEST_MODE": "1"},
    )
    assert elsewhere.returncode == 1
    assert "must be https" in elsewhere.stderr


def test_the_active_reader_prints_the_version_serving_all_traffic(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    status = tmp_path / "status.json"
    status.write_text(_deployment((ACTIVE_VERSION, 100)), encoding="utf-8")
    assert reader.main(["--active", str(status)]) == 0
    assert capsys.readouterr().out == f"version_id={ACTIVE_VERSION}\n"
    status.write_text(_deployment((ACTIVE_VERSION, 100.0)), encoding="utf-8")
    assert reader.main(["--active", str(status)]) == 0


@pytest.mark.parametrize(
    "text",
    [
        _deployment((ACTIVE_VERSION, 60), ("11111111-2222-3333-4444-555555555555", 40)),
        _deployment((ACTIVE_VERSION, 100), ("11111111-2222-3333-4444-555555555555", 0)),
        _deployment((ACTIVE_VERSION, True)),
        _deployment((ACTIVE_VERSION, "100")),
        _deployment(("not-a-version\nurl=https://evil.example", 100)),
        _deployment(),
        json.dumps({"versions": "all"}),
        json.dumps([]),
        "The Worker ai has no deployments.",
    ],
)
def test_the_active_reader_refuses_anything_but_one_full_version(tmp_path, text):
    reader = load_script("read_wrangler_deploy.py")
    status = tmp_path / "status.json"
    status.write_text(text, encoding="utf-8")
    with pytest.raises(SystemExit) as refused:
        reader.main(["--active", str(status)])
    # The reader's own refusal carries a message; argparse rejecting the flag exits 2.
    assert isinstance(refused.value.code, str)


def test_the_active_is_mode_succeeds_only_for_the_version_serving_everything(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    status = tmp_path / "status.json"
    status.write_text(_deployment((ACTIVE_VERSION, 100)), encoding="utf-8")
    assert reader.main(["--active-is", ACTIVE_VERSION, str(status)]) == 0
    assert capsys.readouterr().out == f"version_id={ACTIVE_VERSION}\n"
    with pytest.raises(SystemExit) as other:
        reader.main(["--active-is", DEPLOYED, str(status)])
    assert isinstance(other.value.code, str)
    assert ACTIVE_VERSION in other.value.code and DEPLOYED in other.value.code
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "text",
    [
        _deployment((ACTIVE_VERSION, 60), (DEPLOYED, 40)),
        _deployment((DEPLOYED, 100), (ACTIVE_VERSION, 0)),
        _deployment(),
        "The Worker ai has no deployments.",
    ],
)
def test_the_active_is_mode_refuses_a_split_or_unreadable_status(tmp_path, text):
    reader = load_script("read_wrangler_deploy.py")
    status = tmp_path / "status.json"
    status.write_text(text, encoding="utf-8")
    # Even the version holding 60% or 40% is not "serving", so the release rolls back.
    for wanted in (ACTIVE_VERSION, DEPLOYED):
        with pytest.raises(SystemExit) as refused:
            reader.main(["--active-is", wanted, str(status)])
        assert isinstance(refused.value.code, str)


@pytest.mark.parametrize("wanted", ["", "not-a-version", f"{ACTIVE_VERSION}\nx=y"])
def test_the_active_is_mode_refuses_a_version_that_is_not_a_version_id(tmp_path, wanted):
    reader = load_script("read_wrangler_deploy.py")
    status = tmp_path / "status.json"
    status.write_text(_deployment((ACTIVE_VERSION, 100)), encoding="utf-8")
    with pytest.raises(SystemExit) as refused:
        reader.main(["--active-is", wanted, str(status)])
    assert isinstance(refused.value.code, str)
    assert reader.main(["--active-is", ACTIVE_VERSION, str(tmp_path / "missing")]) == 1


def test_production_rolls_back_to_the_version_it_replaced():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    cloudflare = workflow.split("  cloudflare:\n", 1)[1]
    record = cloudflare.split("      - name: Record the version production is serving\n", 1)[1]
    record = record.split("      - name: Deploy the production Worker\n", 1)[0]
    assert "wrangler deployments status --config wrangler.json --json" in record
    assert 'read_wrangler_deploy.py" --active "$status"' in record
    # A failure to read the serving version stops the job before it deploys.
    assert "not deploying without a version to roll back to" in record
    # Recording happens before the deploy, not after it.
    assert cloudflare.index("Record the version production is serving") < cloudflare.index(
        "Deploy the production Worker"
    )
    rollback = cloudflare.split("      - name: Roll back the production Worker\n", 1)[1]
    assert "PREVIOUS_VERSION_ID: ${{ steps.active.outputs.version_id }}" in rollback
    assert 'wrangler rollback "$PREVIOUS_VERSION_ID"' in rollback
    assert 'if [ -z "$PREVIOUS_VERSION_ID" ]' in rollback


def test_the_plugin_count_is_spelled_as_a_word_up_to_twelve():
    assert site._count_word(1) == "One" and site._count_word(8) == "Eight"
    assert site._count_word(12) == "Twelve" and site._count_word(13) == "13"
    assert site._count_word(0) == "0"


def test_an_unsafe_plugin_directory_is_refused(mini_repo, tmp_path):
    odd = mini_repo / "plugins" / ".hidden" / "skills" / "gamma"
    odd.mkdir(parents=True)
    (odd / "SKILL.md").write_text("---\nname: gamma\n---\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="path component"):
        site.build(mini_repo, tmp_path / "site", "v1")


def test_links_in_rendered_prose_are_underlined():
    """Prose links share the text colour, so the underline is what marks them."""
    rule = re.search(r"\.prose-lab a \{([^}]*)\}", site.site_style.CSS)
    assert rule and "text-decoration: underline" in rule.group(1)


def test_every_id_the_page_chrome_writes_is_reserved_from_headings():
    sources = [
        Path(site.__file__),
        Path(site.site_style.__file__),
    ]
    written = set()
    for source in sources:
        written |= set(re.findall(r'id="([a-z][a-z-]*)"', source.read_text(encoding="utf-8")))
    assert written <= site.site_markdown.RESERVED_IDS, written - site.site_markdown.RESERVED_IDS


def test_a_failed_dispatch_prints_a_command_that_dispatches_on_the_tag():
    workflow = (REPO / ".github" / "workflows" / "cut-release.yml").read_text(encoding="utf-8")
    dispatch = workflow.split("- name: Dispatch the release workflow on the tag", 1)[1]
    assert "gh workflow run release.yml --repo $GH_REPO --ref v$VERSION" in dispatch
    assert "Actions tab" not in dispatch


# --- the 404 and the /errors/ pages -----------------------------------------------------

ERROR_CODES = ("403", "500", "502", "503")


def _suggestion_data(page):
    block = re.search(r'<script type="application/json" id="lost-pages">(.*?)</script>', page, re.S)
    assert block, "the 404 embeds no page list"
    return block.group(1), json.loads(block.group(1))


def test_the_404_embeds_every_real_page_for_its_suggestions(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "404.html").read_text(encoding="utf-8")
    _, pages = _suggestion_data(page)
    built = {entry[0] for entry in pages}
    assert len(built) == len(pages), "a page is offered twice"
    assert {
        "/family/",
        "/family/example/",
        "/start/",
        "/workflows/",
        "/examples/",
        "/quality/",
        "/plugins/engineering/",
        "/plugins/engineering/alpha/",
        "/plugins/engineering/beta/",
    } == built
    assert ["/plugins/engineering/alpha/", "alpha", "Skill in engineering"] in pages
    # The 404 is served from any depth, so nothing on it may be relative.
    for href in re.findall(r'href="([^"]*)"', page):
        assert href.startswith(("/", "#", "https://")), href
    for label, href in (("Home", "/"), ("Start", "/start/"), ("FAMILY", "/family/")):
        assert f'href="{href}">{label}</a>' in page
    assert 'href="/#finder">Search the catalogue</a>' in page
    # What the visitor asked for and what is suggested start hidden, and only script shows
    # them, so without script the page is the heading, the sentence and the links.
    assert '<p class="lost-asked" hidden>' in page and 'id="lost-suggest"' in page
    assert "hidden>\n<h2" in page


def test_the_embedded_page_list_cannot_close_its_script_element():
    hostile = [["/x/", "</script><script>alert(1)</script>", "<!-- & \u2028 \u2029 -->"]]
    escaped = site.site_errors.json_for_script(hostile)
    assert not set("<>&") & set(escaped) and "\u2028" not in escaped and "\u2029" not in escaped
    assert json.loads(escaped) == hostile
    page = site.render_missing(hostile, "v9")
    assert page.count("<script") == page.count("</script>")
    block, pages = _suggestion_data(page)
    assert pages == hostile and "<" not in block
    # The path the visitor asked for is shown through textContent and nothing else.
    script = site.site_errors.LOST_SCRIPT
    assert "textContent" in script
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", script)


def test_the_404_keeps_the_site_header_and_footer_and_its_own_motion_rules(mini_repo, tmp_path):
    page = (_build(mini_repo, tmp_path) / "404.html").read_text(encoding="utf-8")
    assert '<header class="site-header" id="banner">' in page
    assert '<footer class="site-footer">' in page and "Made by Serhii Zolotov" in page
    assert '<span class="sr-only">Error 404: page not found</span>' in page
    assert "Did you mean" in page
    css = site.site_errors.LOST_CSS
    assert _outside_motion_query(css).count("animation") == 0
    assert "prefers-reduced-motion: no-preference" in css


def _outside_motion_query(css):
    """The stylesheet with every ``prefers-reduced-motion: no-preference`` block removed."""
    kept, rest = [], css
    marker = "@media (prefers-reduced-motion: no-preference) {"
    while marker in rest:
        before, _, after = rest.partition(marker)
        kept.append(before)
        depth = 1
        for index, char in enumerate(after):
            depth += (char == "{") - (char == "}")
            if depth == 0:
                rest = after[index + 1 :]
                break
        else:  # pragma: no cover - an unbalanced stylesheet fails the assertions anyway
            rest = ""
    return "".join(kept) + rest


@pytest.mark.parametrize("code", ERROR_CODES)
def test_each_error_page_is_one_self_contained_noindex_file(mini_repo, tmp_path, code):
    path = _build(mini_repo, tmp_path) / "errors" / f"{code}.html"
    raw = path.read_bytes()
    page = raw.decode("utf-8")
    # A custom error page is fetched once and shown on its own, so size is a contract.
    assert len(raw) < 100_000
    assert '<meta name="robots" content="noindex">' in page
    # Nothing is loaded: no script, stylesheet, image, font or frame, and every link a
    # visitor can follow stays on the host serving the page.
    assert not re.search(r"<(?:img|iframe|object|embed|audio|video|source)\b", page)
    assert not re.search(r"<script[^>]*\bsrc=", page)
    assert not re.search(r'<link[^>]*rel="(?:stylesheet|preload|preconnect|prefetch)', page)
    assert "@import" not in page and "@font-face" not in page
    assert not re.search(r"url\(\s*[\"']?(?!data:|#)", page)
    for value in re.findall(r'(?:href|src|action)="([^"]*)"', page):
        assert value in ("/", "") or value.startswith("data:image/"), value
    # The one address in the file is the SVG namespace inside the tab icon's data URI.
    assert "https://" not in page
    assert page.replace("http://www.w3.org/2000/svg", "").count("http://") == 0
    # Motion exists only where the visitor has not asked for less; the page is whole
    # without it, and without script.
    assert "prefers-reduced-motion: no-preference" in page
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert "animation" in css and "animation" not in _outside_motion_query(css)
    assert "prefers-color-scheme: dark" in css and 'data-theme="night"' in css
    assert ":focus-visible" in css and "<h1" in page and "Error " + code in page
    assert page.count('href="/"') == 2  # the mark and the Home button
    # No vendor, model or host is named.
    assert not re.search(r"claude|anthropic|openai|gpt|gemini|codex|cloudflare|copilot", page, re.I)
    retry = 'id="retry"' in page
    assert retry == (code != "403")
    if retry:
        assert "location.reload()" in page or "window.location.reload()" in page
        assert "<noscript>" in page


def test_error_pages_have_distinct_headings_and_stay_small(mini_repo, tmp_path):
    errors = _build(mini_repo, tmp_path) / "errors"
    assert sorted(p.name for p in errors.iterdir()) == [f"{code}.html" for code in ERROR_CODES]
    titles = [
        re.search(r"<title>(.*?)</title>", (errors / f"{code}.html").read_text("utf-8")).group(1)
        for code in ERROR_CODES
    ]
    assert len(set(titles)) == 4 and all(title.endswith(" · AI") for title in titles)
    assert max(p.stat().st_size for p in errors.iterdir()) < 20_000


def test_a_missing_font_is_refused_by_name_rather_than_with_a_traceback():
    # The hashed names are computed when site_style is imported, before build() runs its
    # own check, so this path has to refuse cleanly on its own.
    import site_style

    with pytest.raises(SystemExit, match="cannot read the site font file no-such-font.woff2"):
        site_style._hashed("no-such-font.woff2")


# --- the offline page and the service worker -------------------------------------------


def _worker(output):
    return (output / "sw.js").read_text(encoding="utf-8")


def _worker_list(text, name):
    """The JSON array a ``var NAME = [...];`` line of the worker holds."""
    return json.loads(re.search(rf"^var {name} = (\[.*\]);$", text, re.M).group(1))


def test_the_worker_is_written_at_the_root_and_names_the_version_in_both_caches(
    mini_repo, tmp_path
):
    output = _build(mini_repo, tmp_path)
    text = _worker(output)
    # Each deploy gets a fresh pair of caches, and the old pairs are found by their prefix.
    assert 'var PREFIX = "ai-site-";' in text
    assert 'var STATIC = PREFIX + "v9" + "-static";' in text
    assert 'var PAGES = PREFIX + "v9" + "-pages";' in text
    other = tmp_path / "other"
    site.build(mini_repo, other, "v10")
    assert 'PREFIX + "v10" + "-static"' in _worker(other)
    assert _worker(other) != text
    # Not a page, not under a directory: the scope of a worker is the folder it is served from.
    assert not (output / "sw.js" / "index.html").exists()


def test_the_worker_precaches_the_offline_page_the_icon_and_the_two_fonts_and_nothing_else(
    mini_repo, tmp_path
):
    output = _build(mini_repo, tmp_path)
    precache = _worker_list(_worker(output), "PRECACHE")
    assert precache == [
        "/offline/",
        "/favicon.png",
        site.site_style.SANS_URL,
        site.site_style.SERIF_URL,
    ]
    # Each is a file the build wrote, at the address the worker will fetch. The offline page
    # is the directory index: the Worker answers /offline.html with a redirect, and a
    # redirected response cannot be served for a navigation.
    assert (output / "offline" / "index.html").is_file()
    assert not (output / "offline.html").exists()
    for url in precache:
        path = output / url.lstrip("/")
        assert (path / "index.html" if url.endswith("/") else path).is_file(), url
    assert site.site_offline.precache_urls() == precache


def test_the_worker_names_no_other_origin(mini_repo, tmp_path):
    text = _worker(_build(mini_repo, tmp_path))
    assert not re.search(r"https?:|(^|[^:*/])//[A-Za-z0-9.-]+\.[a-z]{2,}", text)
    # Every address it holds is rooted at this origin.
    for name in ("PRECACHE", "IMMUTABLE_ICONS"):
        for url in _worker_list(text, name):
            assert url.startswith("/") and not url.startswith("//"), url
    assert "importScripts" not in text and "XMLHttpRequest" not in text


def test_the_worker_stores_only_a_plain_200_and_never_a_redirect_or_opaque_response(
    mini_repo, tmp_path
):
    text = _worker(_build(mini_repo, tmp_path))
    # The one gate everything stored passes through: Cloudflare Access's sign-in is a
    # redirect, and a copy of it served later as a page would lock a visitor out.
    assert (
        'return response.status === 200 && response.type === "basic" && !response.redirected;'
        in text
    )
    assert "plain(response) && isHtml(response)" in text
    assert text.count("cache.put(") == 3  # precache, a page, an immutable file
    puts = re.findall(r"^.*cache\.put\(.*$", text, re.M)
    assert all("response" in line or "copy" in line for line in puts), puts


def test_the_worker_leaves_everything_but_pages_fonts_and_icons_to_the_browser(mini_repo, tmp_path):
    text = _worker(_build(mini_repo, tmp_path))
    handler = text.split('self.addEventListener("fetch"', 1)[1]
    assert text.count("event.respondWith(") == 2
    assert 'if (request.method !== "GET") return;' in handler
    assert "if (url.origin !== self.location.origin) return;" in handler
    assert handler.index('request.method !== "GET"') < handler.index("event.respondWith(")
    assert handler.index("url.origin !==") < handler.index("event.respondWith(")
    assert 'request.mode === "navigate"' in handler
    assert _worker_list(text, "IMMUTABLE_ICONS") == ["/favicon.png", "/apple-touch-icon.png"]
    assert 'var FONTS = "/fonts/";' in text


def test_the_worker_caps_the_page_cache_and_cleans_up_only_its_own_caches(mini_repo, tmp_path):
    text = _worker(_build(mini_repo, tmp_path))
    assert "var MAX_PAGES = 60;" in text
    assert "keys.slice(0, Math.max(0, keys.length - MAX_PAGES))" in text
    activate = text.split('self.addEventListener("activate"', 1)[1].split("\n});", 1)[0]
    assert "name.indexOf(PREFIX) === 0 && name !== STATIC && name !== PAGES" in activate
    assert activate.index("caches.delete(") < activate.index("self.clients.claim()")


def test_the_worker_is_plain_es2017(mini_repo, tmp_path):
    text = _worker(_build(mini_repo, tmp_path))
    # Syntax newer than ES2017 would stop the worker parsing on an older browser, and a
    # worker that does not parse is a silent absence of offline support.
    for newer in ("?.", "??", "catch {", "...", "import ", "#"):
        assert newer not in re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S), newer


def test_the_version_reaches_the_worker_only_as_a_json_string():
    text = site.site_offline.render_worker('v"; evil(); "')
    assert 'PREFIX + "v\\"; evil(); \\"" + "-static"' in text
    assert "@@" not in text


def test_the_offline_page_is_the_sites_own_and_is_not_indexed(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    page = (output / "offline" / "index.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="noindex">' in page
    assert "<title>Offline · AI</title>" in page
    # The site's header, footer and Back, and the 404's heading and list.
    assert '<header class="site-header"' in page and '<footer class="site-footer"' in page
    assert BACK.format("/") in page
    assert 'class="title lost-word"' in page and 'class="lost-suggest"' in page
    assert "You're offline" in page and "You are offline" in page
    # The script fills the list from the Cache API; without it the page is whole.
    assert 'id="offline-retry" hidden>Try again</button>' in page
    assert '<noscript><a class="pill" href="">Try again</a></noscript>' in page
    assert "window.location.reload()" in page and "caches.keys()" in page
    # Nothing is loaded from anywhere but the site's own precached files.
    assert not re.search(r'(src|href)="https?://(?!github\.com/greenblacked)', page)
    assert "preconnect" not in page and '<link rel="stylesheet"' not in page
    # Other pages are indexable: only this one carries the tag.
    assert "noindex" not in (output / "index.html").read_text(encoding="utf-8")


def test_the_offline_page_links_only_to_a_rooted_path_of_the_same_origin(mini_repo, tmp_path):
    script = site.site_offline.render_offline_script()
    assert "url.origin !== window.location.origin" in script
    assert 'path.charAt(1) === "/"' in script
    assert "textContent" in script and "innerHTML" not in script
    assert "path === OFFLINE" in script


def test_every_page_registers_the_worker_after_load_and_the_error_pages_do_not(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    registration = (
        '<script>(function(){if(!("serviceWorker" in navigator)||!window.isSecureContext)return;'
        'window.addEventListener("load",function(){'
        'navigator.serviceWorker.register("/sw.js").catch(function(){});});})();</script>'
    )
    pages = [p for p in output.rglob("*.html") if p.parent.name != "errors"]
    assert len(pages) > 5
    for path in pages:
        assert path.read_text(encoding="utf-8").count(registration) == 1, path
    errors = sorted((output / "errors").glob("*.html"))
    assert errors
    for path in errors:
        text = path.read_text(encoding="utf-8")
        assert "serviceWorker" not in text and "sw.js" not in text, path
