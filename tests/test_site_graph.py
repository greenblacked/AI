"""The routing graph draws what the source files state and nothing else.

The edges are the part a reader cannot check by looking, so the first half pins the rule
that finds them against a fixture built to tempt it: a subagent name used as an English
word, one inside a code fence, one in another plugin. The second half pins the markup:
same bytes every build, the accessibility wiring, no inline style, and colours that clear
3:1 in every theme.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pytest

from tests.conftest import REPO, load_script

graph = load_script("site_graph.py")
site = load_script("build_catalogue_site.py")
style = site.site_style


@dataclass
class _Skill:
    plugin: str
    name: str
    body: str = ""


@dataclass
class _Agent:
    plugin: str
    name: str


AGENTS = [
    _Agent("ops", "log-reader"),
    _Agent("ops", "scribe"),
    _Agent("coding", "maker"),
    _Agent("coding", "diff-reader"),
]

SKILLS = [
    # Named in code spans: two edges, one of them to another plugin.
    _Skill("coding", "review", "Hand it to the `diff-reader` subagent. Then `scribe`."),
    # The English word, a fenced sample, and a span with extra text are not edges.
    _Skill(
        "coding",
        "cadence",
        "The decision maker signs off. Ask the maker.\n"
        "```\nuse `log-reader` here\n```\n"
        "Run `log-reader --help` or ``scribe`` or `Scribe`.\n",
    ),
    # Own plugin wins over an alphabetically earlier plugin with the same file name.
    _Skill("coding", "build", "Plan with `maker`.\n~~~\n`scribe`\n~~~\nAnd `diff-reader`."),
    _Skill("ops", "triage", "Send the run to `log-reader`; `log-reader` again."),
    _Skill("ops", "silent", "Nothing named here."),
]


def _edges():
    return graph.derive_edges(SKILLS, AGENTS)


def test_edges_come_only_from_code_spans_outside_fences():
    assert _edges() == [
        graph.Edge("coding", "build", "coding", "diff-reader"),
        graph.Edge("coding", "build", "coding", "maker"),
        graph.Edge("coding", "review", "coding", "diff-reader"),
        graph.Edge("coding", "review", "ops", "scribe"),
        graph.Edge("ops", "triage", "ops", "log-reader"),
    ]


def test_edge_derivation_ignores_input_order():
    assert graph.derive_edges(reversed(SKILLS), reversed(AGENTS)) == _edges()


def test_a_subagent_name_shared_across_plugins_resolves_to_the_skills_own_plugin():
    agents = [_Agent("zeta", "reader"), _Agent("alpha", "reader"), _Agent("mid", "reader")]
    skills = [
        _Skill("zeta", "a", "`reader`"),
        _Skill("mid", "b", "`reader`"),
        _Skill("x", "c", "`reader`"),
    ]
    got = {(e.skill, e.agent_plugin) for e in graph.derive_edges(skills, agents)}
    assert got == {("a", "zeta"), ("b", "mid"), ("c", "alpha")}


def test_unclosed_and_empty_spans_are_not_names():
    assert graph._code_spans("a `open and `b` c") == {"open and "}
    assert graph._code_spans("only `one") == set()
    assert graph._code_spans("``pair`` `x`") == {"x"}
    assert graph._code_spans("`a`\n`b`") == {"a", "b"}


def test_a_plugin_without_edges_renders_nothing():
    edges = _edges()
    assert graph.render("empty", edges, site._skill_href) == ""
    assert graph.render("ops", [], site._skill_href) == ""
    # Only the plugin's own skills are drawn, whatever else the edge list holds.
    section = graph.render("ops", edges, site._skill_href)
    assert "triage" in section and "review" not in section


def _render(plugin="coding", edges=None):
    return graph.render(plugin, _edges() if edges is None else edges, site._skill_href)


def test_output_is_byte_identical_and_independent_of_edge_order():
    first = _render()
    assert first == _render()
    assert first == _render(edges=list(reversed(_edges())))


def _svg(section):
    # The markup is this build's own output, never fetched, so the XML attacks do not apply.
    return ET.fromstring(re.search(r"<svg.*</svg>", section, re.S).group(0))  # noqa: S314


NS = "{http://www.w3.org/2000/svg}"


def test_the_drawing_is_labelled_for_assistive_technology():
    section = _render()
    svg = _svg(section)
    assert svg.get("role") == "img"
    ids = svg.get("aria-labelledby").split()
    assert ids == ["rg-coding-title", "rg-coding-desc"]
    by_id = {el.get("id"): el for el in svg.iter() if el.get("id")}
    assert by_id["rg-coding-title"].tag == NS + "title"
    desc = by_id["rg-coding-desc"]
    assert desc.tag == NS + "desc"
    assert desc.text == (
        "2 skills in coding name 3 subagents. "
        "build names diff-reader, maker. review names diff-reader, scribe (ops)."
    )
    # The title and desc come first, so assistive technology reaches them before the nodes.
    assert [child.tag for child in svg][:2] == [NS + "title", NS + "desc"]
    assert 'aria-labelledby="rg-coding-heading"' in section


def test_every_node_is_a_text_label_and_the_list_states_the_same_edges():
    section = _render()
    svg = _svg(section)
    labels = [el.text for el in svg.iter(NS + "text")]
    assert labels == [
        "Skills",
        "Subagents",
        "build",
        "review",
        "diff-reader",
        "maker",
        "scribe (ops)",
    ]
    items = re.findall(r"<li>(.*?)</li>", section)
    assert len(items) == 2
    assert items[0].startswith('<a href="/plugins/coding/build/">build</a> names ')
    assert "<code>diff-reader</code>, <code>maker</code>" in items[0]
    assert "<code>diff-reader</code>, <code>scribe (ops)</code>" in items[1]
    # Skills and subagents differ by outline pattern as well as by column, not by colour alone.
    assert 'class="rg-skill"' in section and 'class="rg-agent"' in section
    assert ".rg-agent .rg-node { stroke-dasharray" in style.CSS


def test_one_edge_is_drawn_per_pair_and_everything_sits_inside_the_viewbox():
    svg = _svg(_render())
    width, height = (int(n) for n in svg.get("viewBox").split()[2:])
    assert (int(svg.get("width")), int(svg.get("height"))) == (width, height)
    paths = list(svg.iter(NS + "path"))
    assert len([p for p in paths if p.get("class") == "rg-edge"]) == 4
    for rect in svg.iter(NS + "rect"):
        x, y = int(rect.get("x")), int(rect.get("y"))
        assert x >= 0 and x + int(rect.get("width")) <= width
        assert y >= 0 and y + int(rect.get("height")) <= height
    # A label's estimated width fits the box drawn for it.
    for group in svg.iter(NS + "g"):
        rect, text = list(group)
        assert len(text.text) * graph.CHAR + 2 * graph.PAD <= int(rect.get("width"))


def test_no_inline_style_script_or_handler_and_the_marker_is_referenced_by_id():
    section = _render()
    assert "style=" not in section and "<script" not in section.lower()
    assert not re.search(r"\son[a-z]+=", section)
    assert "javascript:" not in section.lower()
    assert re.findall(r'marker-end="url\(#([^)]+)\)"', section) == ["rg-coding-head"] * 4
    assert 'id="rg-coding-head"' in section
    ids = re.findall(r'\sid="([^"]+)"', section)
    assert len(ids) == len(set(ids))


def test_labels_are_escaped():
    edge = graph.Edge("p", "<s>", "p", 'a"b')
    section = graph.render("p", [edge], lambda plugin, name: f"/x/{name}/")
    assert "<s>" not in section
    assert "&lt;s&gt;" in section and "a&quot;b" in section
    _svg(section)  # still well-formed XML


def _luminance(colour):
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _ratio(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _variable(block_start, name):
    block = style.CSS.split(block_start, 1)[1].split("}", 1)[0]
    return re.search(rf"--{name}: (#[0-9a-f]{{6}});", block).group(1)


@pytest.mark.parametrize("plugin", sorted(style.PLUGIN_LOOKS))
def test_each_looks_line_colour_clears_3_to_1_on_both_grounds_in_both_themes(plugin):
    look = style.PLUGIN_LOOKS[plugin]
    # The page ground and the node fill, since the border sits against both.
    for theme, colour in (("day", look.day[0]), ("night", look.night[0])):
        start = ":root {" if theme == "day" else 'html[data-theme="night"] {'
        for ground in ("bg", "card"):
            assert _ratio(colour, _variable(start, ground)) >= 3, (plugin, theme, ground)
    # The label colour is checked too: it is text, so it needs 4.5:1.
    assert _ratio(_variable(":root {", "muted"), _variable(":root {", "bg")) >= 4.5
    assert (
        _ratio(
            _variable('html[data-theme="night"] {', "muted"),
            _variable('html[data-theme="night"] {', "bg"),
        )
        >= 4.5
    )
    assert f".{style.plugin_class(plugin)} .rg {{ --rg: var(--{plugin}-1); }}" in style.CSS


def test_the_drawing_is_hidden_on_a_phone_and_the_list_is_not():
    css = style.GRAPH_CSS
    assert ".rg-map { display: none;" in css
    assert re.search(r"@media \(min-width: 40rem\) \{\s*\.rg-map \{ display: block; \}", css)
    assert "display: none" not in css.split(".rg-list {")[1].split("}")[0]
    assert ".rg-svg { max-width: 100%; height: auto; }" in css
    assert "overflow" not in css


def test_the_real_repository_has_edges_and_only_its_stated_ones():
    catalogue_skills = site._collect_skills(REPO)
    agents = [
        part
        for plugin in sorted(p.name for p in (REPO / "plugins").iterdir())
        for part in site._collect_parts(REPO, plugin, "agents")
    ]
    edges = graph.derive_edges(catalogue_skills, agents)
    assert len(edges) > 10
    # A known pair, each end of which is written in the skill's own body.
    assert graph.Edge("operations", "ci-triage", "operations", "ci-log-reader") in edges
    # Cross-plugin: the postmortem skill is in manager and names the operations scribe.
    assert graph.Edge("manager", "postmortem", "operations", "incident-scribe") in edges
    # "maker" is an English word in several unrelated skills and must not become an edge.
    assert not [e for e in edges if e.agent == "maker" and e.skill_plugin != "family"]
    names = {skill.name: skill for skill in catalogue_skills}
    for edge in edges:
        assert f"`{edge.agent}`" in names[edge.skill].body


def test_building_the_real_repository_puts_a_graph_on_plugin_pages_with_edges(tmp_path):
    output = tmp_path / "real"
    site.build(REPO, output, "dev")
    skills = site._collect_skills(REPO)
    agents = [
        part
        for plugin in sorted(p.name for p in (REPO / "plugins").iterdir())
        for part in site._collect_parts(REPO, plugin, "agents")
    ]
    wanted = {e.skill_plugin for e in graph.derive_edges(skills, agents)} - {site.FAMILY_PLUGIN}
    assert wanted
    drawn = set()
    for page in sorted((output / "plugins").glob("*/index.html")):
        text = page.read_text(encoding="utf-8")
        plugin = page.parent.name
        has = '<section class="rg"' in text
        if has:
            drawn.add(plugin)
            assert text.count('<svg class="rg-svg"') == 1
            assert f'aria-labelledby="rg-{plugin}-title rg-{plugin}-desc"' in text
            # The graph markup carries no inline style, so a strict CSP is not needed for it.
            section = text[text.index('<section class="rg"') :].split("</section>", 1)[0]
            assert "style=" not in section
        elif plugin in wanted:
            pytest.fail(f"{plugin} has edges but no graph")
    assert drawn == wanted
    assert "coding" in drawn
    # Plugins with no stated edge get no empty heading.
    assert "career" not in drawn and 'class="rg"' not in (
        output / "plugins" / "career" / "index.html"
    ).read_text(encoding="utf-8")
