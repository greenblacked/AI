"""The routing graph on a plugin's page: which skills name which subagents.

Everything here runs at build time on the standard library alone, and the page it
produces needs no script. The graph is inline SVG drawn from a fixed layout, so the same
repository always yields byte-identical markup, and a plain list of the same edges sits
beside it for anyone the drawing does not serve.

An edge exists only where a source file states it. The rule, and nothing looser:

* the source is the page the site renders for a ``SKILL.md`` body (frontmatter
  excluded), read as HTML rather than as Markdown;
* the target is a subagent file under ``plugins/*/agents/``, matched by its file name;
* the page must show that name as inline code, `` `ci-log-reader` ``, with nothing else
  inside it, and not inside a code block.

Reading the rendered HTML is what makes the graph agree with the page by construction.
A hand-written Markdown scanner kept disagreeing with the renderer about what counts as
code, a comment or a list item's text, and each disagreement was an edge the page did not
show or a missing one it did. Here the renderer decides, and this module only looks at
what it emitted.

The code requirement is what keeps prose out. ``maker`` is a subagent and also an
English word that several unrelated skills use, so matching bare words would draw edges
nobody wrote. A subagent description that names a skill is not a source either: those
sentences say what the agent is *not* for ("Not for ... which is profiling"), which is a
boundary rather than a hand-off, so reading them as edges would draw the opposite of
what they say. The same holds inside a skill: a sentence opening "Do not use for" or
"Not for" names where the work should not go, so its code is skipped. A skill that names
an agent only in prose, or only in ``references/``, has no edge; the omission is visible
in the list and fixable in the skill.
"""

from __future__ import annotations

import html
import re
import sys
from collections.abc import Callable, Iterable
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple, Protocol

# Imported by name like the build's other modules, so a test that loads this file alone
# needs the directory on the path as much as the build does.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import site_markdown  # noqa: E402

# The labels are set in the monospace face, so a label's width follows from its length.
# The estimate runs a little wide on purpose: a label that overflows its box is a defect
# the eye sees at once, a box with spare room is not.
CHAR = 8
PAD = 12
NODE_H = 28
ROW = 40
GAP = 180
MARGIN = 2
TOP = 30


class Named(Protocol):
    plugin: str
    name: str


class Edge(NamedTuple):
    """One stated hand-off: a skill's body names a subagent."""

    skill_plugin: str
    skill: str
    agent_plugin: str
    agent: str


# A sentence that opens "Do not use for" or "Not for" says where the skill does not
# apply, so a name inside it is the thing to send the work away from, not a hand-off.
# A list marker never leads it: the renderer has already turned "1." and "1)" into markup.
_BOUNDARY = re.compile(r"[\W_]*(?:do not use for|not for)\b", re.IGNORECASE)


# These end in a full stop that does not end the sentence: "e.g. `maker`" inside a
# boundary sentence must not split it, or the names after the abbreviation would escape.
# A chain of initials ("U.S.") and short titles are covered as a shape, not a list,
# because a split that ends a boundary sentence early turns the names after it into
# hand-offs. A lone letter ("option A.") ends its sentence: it is more often a label.
_ABBREVIATION = re.compile(
    r"(?:^|[\s(])(?:e\.g|i\.e|etc|vs|cf|approx|incl|fig|no|mr|mrs|ms|dr|st|(?:[a-z]\.)+[a-z])\.$",
    re.IGNORECASE,
)

_CLOSERS = "\"')]\u2019\u201d\u00bb"


def _sentences(text: str) -> list[str]:
    """``text`` split after each sentence-ending mark that sits outside a code span."""
    sentences = []
    start = 0
    inside = False
    for index, char in enumerate(text):
        if char == "`":
            inside = not inside
            continue
        if char not in ".!?" or inside:
            continue
        # Closing quotes and brackets belong to the sentence they end: 'Not for "x."'
        end = index + 1
        while end < len(text) and text[end] in _CLOSERS:
            end += 1
        if (end == len(text) or text[end].isspace()) and not _ABBREVIATION.search(
            text[start : index + 1]
        ):
            sentences.append(text[start:end])
            start = end
    sentences.append(text[start:])
    return sentences


# Elements that start or end a block of text. Anything else the renderer emits (``a``,
# ``em``, ``strong``, ``br``) sits inside a block, so only these split one paragraph from
# the next; a nested list inside an item is its own block, which is what keeps one
# bullet's "Not for" from reaching the bullet after it.
_BLOCKS = frozenset(
    {
        "p", "li", "ul", "ol", "dl", "dt", "dd", "blockquote", "div", "hr", "pre",
        "table", "thead", "tbody", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6",
    }
)  # fmt: skip


class _Blocks(HTMLParser):
    """The text of each block in rendered HTML, inline code written back as backticks.

    Code inside ``pre`` is a sample, not an instruction, and is dropped with the rest of
    the block's text. Every literal backtick is swapped for an apostrophe on the way in,
    so the only backticks in a block are the pairs written here and the sentence splitter
    and span reader below never see a stray one. A name never holds a backtick, so the
    swap cannot hide an edge.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)  # entities arrive decoded
        self.blocks: list[str] = []
        self._text: list[str] = []
        self._code: list[str] | None = None
        self._pre = 0

    def _flush(self) -> None:
        if self._text:
            self.blocks.append("".join(self._text))
            self._text = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCKS:
            self._flush()
        if tag == "pre":
            self._pre += 1
        elif tag == "code" and not self._pre:
            self._code = []
        elif tag == "br":
            self._text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self._code is not None:
            self._text.append("`" + "".join(self._code).replace("`", "'") + "`")
            self._code = None
        if tag == "pre":
            self._pre = max(self._pre - 1, 0)
        if tag in _BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._code is not None:
            self._code.append(data)
        elif not self._pre:
            self._text.append(data.replace("`", "'"))

    def close(self) -> None:
        super().close()
        self._flush()


def _code_spans(markup: str) -> set[str]:
    """The text of every inline code element in ``markup`` outside the boundary sentences.

    A sentence that opens "Do not use for" or "Not for" is left out, wherever in its
    block it sits and however many lines it wraps over: the names in it are what the
    skill sends work away from.
    """
    parser = _Blocks()
    parser.feed(markup)
    parser.close()
    spans: set[str] = set()
    for block in parser.blocks:
        kept = "".join(s for s in _sentences(block) if not _BOUNDARY.match(s))
        spans.update(re.findall(r"`([^`]*)`", kept))
    return spans


def derive_edges(skills: Iterable, agents: Iterable[Named]) -> list[Edge]:
    """Every skill-to-subagent edge the skills' own bodies state, sorted.

    ``skills`` carry ``plugin``, ``name`` and ``body``, and a ``directory`` if they have
    one. Each body is rendered exactly as the skill's page renders it. When subagents
    share a file name in different plugins, a skill's own plugin wins; otherwise the name
    is ambiguous and draws no edge, because picking one would claim a hand-off, and an
    install dependency, that the skill never stated.
    """
    by_name: dict[str, list[Named]] = {}
    for agent in agents:
        by_name.setdefault(agent.name, []).append(agent)
    for candidates in by_name.values():
        candidates.sort(key=lambda agent: agent.plugin)
    edges: set[Edge] = set()
    for skill in skills:
        # The directory only resolves relative links, which draw no edge, so a skill
        # without one is rendered with none.
        page = site_markdown.render(
            skill.body, source_dir=getattr(skill, "directory", ""), offset=1
        )
        for span in _code_spans(page):
            candidates = by_name.get(span)
            if not candidates:
                continue
            own = [agent for agent in candidates if agent.plugin == skill.plugin]
            if not own and len(candidates) > 1:
                continue
            target = (own or candidates)[0]
            edges.add(Edge(skill.plugin, skill.name, target.plugin, target.name))
    return sorted(edges)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _agent_label(edge: Edge, plugin: str) -> str:
    """A subagent's label: its name, with its plugin when it ships in another one."""
    if edge.agent_plugin == plugin:
        return edge.agent
    return f"{edge.agent} ({edge.agent_plugin})"


def _width(labels: list[str]) -> int:
    return max(len(label) for label in labels) * CHAR + 2 * PAD


def _grouped(edges: list[Edge], plugin: str) -> list[tuple[str, list[str]]]:
    """Skill name to the labels of the subagents it names, both sorted."""
    found: dict[str, set[str]] = {}
    for edge in edges:
        found.setdefault(edge.skill, set()).add(_agent_label(edge, plugin))
    return [(skill, sorted(found[skill])) for skill in sorted(found)]


def describe(plugin: str, edges: list[Edge]) -> str:
    """The sentence a screen reader gets for the drawing: every edge, grouped by skill."""
    groups = _grouped(edges, plugin)
    agents = {label for _, labels in groups for label in labels}
    lead = f"{_plural(len(groups), 'skill')} in {plugin} name {_plural(len(agents), 'subagent')}. "
    return lead + " ".join(f"{skill} names {', '.join(labels)}." for skill, labels in groups)


def _svg(plugin: str, edges: list[Edge]) -> str:
    groups = _grouped(edges, plugin)
    left = [skill for skill, _ in groups]
    right = sorted({label for _, labels in groups for label in labels})
    left_w, right_w = _width(left), _width(right)
    width = MARGIN + left_w + GAP + right_w + MARGIN
    rows = max(len(left), len(right))
    height = TOP + rows * ROW + MARGIN

    def centres(count: int) -> list[int]:
        start = TOP + (rows - count) * ROW // 2
        return [start + index * ROW + ROW // 2 for index in range(count)]

    left_y = dict(zip(left, centres(len(left)), strict=True))
    right_y = dict(zip(right, centres(len(right)), strict=True))
    left_edge = MARGIN + left_w
    right_x = width - MARGIN - right_w
    mid = (left_edge + right_x) // 2
    prefix = f"rg-{plugin}"

    parts = [
        f'<svg class="rg-svg" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="{prefix}-title {prefix}-desc" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<title id="{prefix}-title">'
        f"{html.escape(plugin)}: which skills name which subagents</title>",
        f'<desc id="{prefix}-desc">{html.escape(describe(plugin, edges))}</desc>',
        f'<defs><marker id="{prefix}-head" markerWidth="8" markerHeight="8" refX="8" '
        'refY="4" orient="auto" markerUnits="userSpaceOnUse">'
        '<path class="rg-head" d="M0 0 L8 4 L0 8 z"/></marker></defs>',
        f'<text class="rg-label" x="{MARGIN}" y="16">Skills</text>',
        f'<text class="rg-label" x="{right_x}" y="16">Subagents</text>',
    ]
    for skill, labels in groups:
        for label in labels:
            y1, y2 = left_y[skill], right_y[label]
            parts.append(
                f'<path class="rg-edge" d="M{left_edge} {y1} C{mid} {y1} {mid} {y2} '
                f'{right_x} {y2}" marker-end="url(#{prefix}-head)"/>'
            )
    for text, y in left_y.items():
        parts.append(_node("rg-skill", MARGIN, left_w, y, text))
    for text, y in right_y.items():
        parts.append(_node("rg-agent", right_x, right_w, y, text))
    parts.append("</svg>")
    return "\n".join(parts)


def _node(kind: str, x: int, width: int, centre: int, text: str) -> str:
    return (
        f'<g class="{kind}"><rect class="rg-node" x="{x}" y="{centre - NODE_H // 2}" '
        f'width="{width}" height="{NODE_H}" rx="6"/>'
        f'<text class="rg-text" x="{x + PAD}" y="{centre}" dy="0.35em">'
        f"{html.escape(text)}</text></g>"
    )


def _list(plugin: str, edges: list[Edge], skill_href: Callable[[str, str], str]) -> str:
    items = []
    for skill, labels in _grouped(edges, plugin):
        agents = ", ".join(f"<code>{html.escape(label)}</code>" for label in labels)
        href = html.escape(skill_href(plugin, skill))
        items.append(f'<li><a href="{href}">{html.escape(skill)}</a> names {agents}</li>')
    return '<ul class="rg-list">\n' + "\n".join(items) + "\n</ul>"


def render(plugin: str, edges: Iterable[Edge], skill_href: Callable[[str, str], str]) -> str:
    """The graph section for ``plugin``, or an empty string when it has no edge.

    Only edges whose skill is in ``plugin`` are drawn. Below the page's 40rem breakpoint
    the drawing is hidden by CSS and the list carries the page alone: scaled to a phone
    the labels would be too small to read, which is worse than a list.
    """
    own = sorted(edge for edge in edges if edge.skill_plugin == plugin)
    if not own:
        return ""
    heading = f"rg-{plugin}-heading"
    return (
        f'<section class="rg" aria-labelledby="{heading}">\n'
        f'<h2 class="rg-title" id="{heading}">Subagent hand-offs</h2>\n'
        '<p class="rg-note">A line means the skill\'s own instructions name that subagent. '
        "Nothing is inferred beyond that. A subagent marked with a plugin ships in "
        "that plugin, which has to be installed too.</p>\n"
        f'<div class="rg-map">\n{_svg(plugin, own)}\n</div>\n'
        f"{_list(plugin, own, skill_href)}\n"
        "</section>\n"
    )
