"""The catalogue site is what a release uploads, so a bad build has to fail here.

The deploy workflow trusts this script to refuse a version that is not a token and to
refuse to delete a directory it did not itself create. Both are silent if they only
hold in the happy path.
"""

from __future__ import annotations

import html
import http.server
import json
import os
import re
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
    "article",
}  # fmt: skip


def test_every_page_is_written_beside_the_archives(mini_repo, tmp_path):
    output = _build(mini_repo, tmp_path)
    for path in (
        "index.html",
        "404.html",
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
    for href in ("/start/", "/workflows/", "/examples/", "/quality/", "/portable-skills.zip"):
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
    assert site.site_style.FONTS_URL.startswith("https://fonts.googleapis.com/css2?")
    assert f'<link rel="stylesheet" href="{html.escape(site.site_style.FONTS_URL)}">' in start
    # Links off the site say so; links on it do not open a new tab.
    assert 'href="https://github.com/greenblacked/AI/releases" target="_blank"' in start
    assert 'rel="noopener noreferrer"' in start
    assert (
        'href="/start/" target' not in start and 'href="/portable-skills.zip" target' not in start
    )
    # The 404 is served from any path, so its links cannot be relative either.
    missing = (output / "404.html").read_text(encoding="utf-8")
    assert 'href="/start/"' in missing and 'href="portable-skills.zip"' not in missing


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
    assert "<code>/ship-it</code>" in page and "<code>[branch]</code>" in page
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
    # The index, start, workflows, examples and quality; then a page per plugin and skill.
    assert len(pages) == len(skills) + len(plugins) + 5
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
    assert pin.problems(REPO, "4.147.0") == []
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
    assert pin.main(["--version", "4.147.0", str(REPO)]) == 0
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
DEPLOYED = "12345678-1234-1234-1234-123456789abc"


def _deploy_line(targets, **extra):
    return json.dumps({"type": "deploy", "targets": targets, **extra}) + "\n"


def test_the_deploy_log_reports_the_production_custom_domain(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(_deploy_line([WORKERS_DEV, PRODUCTION], version_id=DEPLOYED), encoding="utf-8")
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


def test_a_deploy_without_the_custom_domain_prints_no_custom_url(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(_deploy_line([WORKERS_DEV]), encoding="utf-8")
    assert reader.main([str(log)]) == 0
    assert capsys.readouterr().out == f"url={WORKERS_DEV}\n"
    # Only the last deploy line counts: an earlier custom domain does not cover a later
    # deploy that dropped it.
    text = _deploy_line([WORKERS_DEV, PRODUCTION]) + _deploy_line([WORKERS_DEV])
    assert reader.parse_deploy(text)[2] == ""


@pytest.mark.parametrize(
    "url",
    [
        "http://ai.szolotov.com",
        "https://user@ai.szolotov.com",
        "https://ai.szolotov.com:8443",
        "https://ai.szolotov.com/path",
        "https://ai.szolotov.com/?q=1",
        "https://ai.szolotov.com#frag",
        "https://ai.szolotov.com.evil.com",
        "https://stage.ai.szolotov.com",
        "https://AI.szolotov.com",
        "https://szolotov.com",
        "https://ai.szolotov.com\ncustom_url=https://evil.example",
    ],
)
def test_only_the_exact_production_host_counts_as_the_custom_domain(url):
    reader = load_script("read_wrangler_deploy.py")
    assert reader.parse_deploy(_deploy_line([WORKERS_DEV, url]))[2] == ""


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


def test_the_stage_branch_uploads_a_preview_and_smokes_it_through_workers_dev():
    workflow = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "--env" not in workflow
    assert "wrangler rollback" not in workflow
    assert "wrangler deploy --config" not in workflow
    deploy = workflow.split("      - name: Upload the stage Preview\n", 1)[1].split(
        "      - name: Smoke-test the stage Preview\n", 1
    )[0]
    assert "wrangler preview --config wrangler.json --name stage" in deploy
    assert "WRANGLER_OUTPUT_FILE_PATH" in deploy
    assert 'read_wrangler_deploy.py" --preview' in deploy
    smoke = workflow.split("      - name: Smoke-test the stage Preview\n", 1)[1]
    assert "stage_url=https://stage.ai.szolotov.com" in smoke
    assert "::error::Wrangler did not report ${stage_url} for this Preview" in smoke
    assert "enable ai.szolotov.com for Preview traffic (docs/ci.md)" in smoke
    # The blocking target is the workers.dev Preview URL, and nothing else is smoked.
    assert 'if [ -z "$WORKERS_DEV_URL" ]' in smoke
    assert "::error::Wrangler reported no workers.dev Preview URL" in smoke
    assert smoke.count("scripts/smoke_site.sh") == 1
    assert 'scripts/smoke_site.sh "$WORKERS_DEV_URL" "$VERSION" greenblacked-ai' in smoke
    # The configured URL names the custom domain, so fetching it would bring the 403 back.
    assert "CONFIGURED_URL" not in smoke
    assert "urls=(" not in smoke
    # The stage custom-domain fetch is information only.
    assert '"${stage_url}/version.txt" || true)' in smoke
    assert "::notice::Bot Fight Mode blocks GitHub runners on stage.ai.szolotov.com" in smoke


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


STAGE = "Smoke-test the stage Preview"
STAGE_URL = "https://stage.ai.szolotov.com"
STAGE_ENV = {
    "WORKERS_DEV_URL": "https://stage-ai.account.workers.dev",
    "CUSTOM_URL": STAGE_URL,
    "VERSION": "stage-abc1234",
}


def test_the_preview_smoke_passes_when_only_the_custom_domain_answers_403(tmp_path):
    result, calls = _run_step(tmp_path, "deploy.yml", STAGE, {**STAGE_ENV, "STUB_CURL_CODE": "403"})
    assert result.returncode == 0, result.stderr
    assert calls[0] == "smoke https://stage-ai.account.workers.dev stage-abc1234 greenblacked-ai"
    assert len(calls) == 2 and calls[1].endswith(f"{STAGE_URL}/version.txt")
    assert (
        "::notice::Bot Fight Mode blocks GitHub runners on stage.ai.szolotov.com" in result.stdout
    )


def test_the_preview_smoke_fails_when_workers_dev_fails_whatever_the_domain_says(tmp_path):
    env = {**STAGE_ENV, "STUB_SMOKE_RC": "1", "STUB_CURL_CODE": "200"}
    result, _calls = _run_step(tmp_path, "deploy.yml", STAGE, env)
    assert result.returncode != 0


def test_the_preview_smoke_fails_on_an_empty_workers_dev_url(tmp_path):
    result, calls = _run_step(tmp_path, "deploy.yml", STAGE, {**STAGE_ENV, "WORKERS_DEV_URL": ""})
    assert result.returncode != 0
    assert "::error::Wrangler reported no workers.dev Preview URL" in result.stdout
    assert calls == []


def test_the_preview_smoke_fails_without_the_stage_host_even_when_workers_dev_passes(tmp_path):
    result, calls = _run_step(tmp_path, "deploy.yml", STAGE, {**STAGE_ENV, "CUSTOM_URL": ""})
    assert result.returncode != 0
    assert "::error::Wrangler did not report https://stage.ai.szolotov.com" in result.stdout
    assert calls[0].startswith("smoke https://stage-ai.account.workers.dev")


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


def test_the_index_filter_and_theme_script_cover_what_the_design_does(mini_repo, tmp_path):
    index = (_build(mini_repo, tmp_path) / "index.html").read_text(encoding="utf-8")
    # Night by the clock from 20:00 to 06:00, a stored choice wins, and a console theme exists.
    assert "h>=20||h<6" in index and 'localStorage.getItem("theme")' in index
    assert '"reactor"' in index and "#070807" in index
    # The filter matches a plugin's name, its blurb or any of its skill names.
    assert 'getAttribute("data-blurb")' in index and 'getAttribute("data-skills")' in index


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
