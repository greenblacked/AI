"""The routing graph on a plugin's page: which skills name which subagents.

Everything here runs at build time on the standard library alone, and the page it
produces needs no script. The graph is inline SVG drawn from a fixed layout, so the same
repository always yields byte-identical markup, and a plain list of the same edges sits
beside it for anyone the drawing does not serve.

An edge exists only where a source file states it. The rule, and nothing looser:

* the source is the body of a ``SKILL.md`` (frontmatter excluded), outside fenced code;
* the target is a subagent file under ``plugins/*/agents/``, matched by its file name;
* the body must write that name as an inline code span, `` `ci-log-reader` ``, with
  nothing else inside the backticks.

The code-span requirement is what keeps prose out. ``maker`` is a subagent and also an
English word that three unrelated skills use, so matching bare words would draw edges
nobody wrote. A subagent description that names a skill is not a source either: those
sentences say what the agent is *not* for ("Not for ... which is profiling"), which is a
boundary rather than a hand-off, so reading them as edges would draw the opposite of
what they say. A skill that names an agent only in prose, or only in ``references/``, has
no edge; the omission is visible in the list and fixable in the skill.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Iterable
from typing import NamedTuple, Protocol

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


def _prose(body: str) -> str:
    """The body with fenced code removed: a sample in a fence is not an instruction."""
    kept = []
    fence = ""
    for line in body.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence:
            if stripped.startswith(fence):
                fence = ""
            continue
        if marker in ("```", "~~~"):
            fence = marker
            continue
        kept.append(line)
    return "\n".join(kept)


def _code_spans(text: str) -> set[str]:
    """The contents of every single-backtick span on one line of ``text``."""
    spans: set[str] = set()
    for line in text.splitlines():
        parts = line.split("`")
        # An odd count of backticks leaves the last piece unclosed, so it is not a span.
        # Even indexes are outside a span, odd ones inside; a double backtick yields an
        # empty piece, which is never a name.
        for index in range(1, len(parts) - 1, 2):
            if parts[index]:
                spans.add(parts[index])
    return spans


def derive_edges(skills: Iterable, agents: Iterable[Named]) -> list[Edge]:
    """Every skill-to-subagent edge the skills' own bodies state, sorted.

    ``skills`` carry ``plugin``, ``name`` and ``body``. When two subagents share a file
    name in different plugins, a skill's own plugin wins, and otherwise the first plugin
    alphabetically does, so the choice is the same on every build.
    """
    by_name: dict[str, list[Named]] = {}
    for agent in agents:
        by_name.setdefault(agent.name, []).append(agent)
    for candidates in by_name.values():
        candidates.sort(key=lambda agent: agent.plugin)
    edges: set[Edge] = set()
    for skill in skills:
        for span in _code_spans(_prose(skill.body)):
            candidates = by_name.get(span)
            if not candidates:
                continue
            own = [agent for agent in candidates if agent.plugin == skill.plugin]
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
