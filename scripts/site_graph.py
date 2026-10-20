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
English word that several unrelated skills use, so matching bare words would draw edges
nobody wrote. A subagent description that names a skill is not a source either: those
sentences say what the agent is *not* for ("Not for ... which is profiling"), which is a
boundary rather than a hand-off, so reading them as edges would draw the opposite of
what they say. The same holds inside a skill: a sentence opening "Do not use for" or
"Not for" names where the work should not go, so its code spans are skipped. A skill
that names an agent only in prose, or only in ``references/``, has no edge; the
omission is visible in the list and fixable in the skill.
"""

from __future__ import annotations

import html
import re
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


class _Line(NamedTuple):
    """One source line, split into the container it sits in and what follows it."""

    depth: int  # how many ``>`` quote markers lead the line
    indent: int  # spaces before the first list marker or content, after the quotes
    col: int  # the column the content starts at once list markers are skipped
    listed: bool  # whether a list marker precedes the content
    blank: bool
    run: str  # a leading run of three or more backticks or tildes, else empty
    rest: str  # what follows that run, stripped


_QUOTE = re.compile(r" {0,3}> ?")
_MARKER = re.compile(r"(?:[-*+]|\d{1,9}[.)])(?: +|$)")


def _scan(line: str) -> _Line:
    """Split ``line`` into quote depth, list indentation and a fence run, if it opens one."""
    line = line.expandtabs(4)
    depth = pos = 0
    while match := _QUOTE.match(line, pos):
        depth += 1
        pos = match.end()
    text = line[pos:]
    body = text.lstrip(" ")
    indent = col = len(text) - len(body)
    listed = False
    while match := _MARKER.match(body):
        token = match.group()
        spaces = len(token) - len(token.rstrip(" "))
        # Five or more spaces after a marker make the content an indented code block,
        # so the content column is one past the marker, not past the padding.
        col += len(token) - spaces + (spaces if 0 < spaces < 5 else 1)
        body = body[match.end() :]
        listed = True
    run = ""
    if body[:1] in ("`", "~"):
        found = body[: len(body) - len(body.lstrip(body[0]))]
        run = found if len(found) >= 3 else ""
    return _Line(depth, indent, col, listed, not text.strip(), run, body[len(run) :].strip())


class _Fence(NamedTuple):
    """The opener of the fence being skipped, and the container it sits in."""

    run: str
    depth: int
    col: int
    listed: bool


def _opens(scan: _Line) -> _Fence | None:
    # A backtick fence's info string cannot hold a backtick; ``a`` alone on a line is a
    # code span, and skipping it as a fence would swallow the prose after it.
    if not scan.run or (scan.run[0] == "`" and "`" in scan.rest):
        return None
    return _Fence(scan.run, scan.depth, scan.col if scan.listed else scan.indent, scan.listed)


def _ends_container(fence: _Fence, scan: _Line) -> bool:
    """Whether ``scan`` leaves the quote or list item the fence opened in."""
    if scan.depth < fence.depth:
        return True
    return fence.listed and scan.depth == fence.depth and not scan.blank and scan.indent < fence.col


def _closes(fence: _Fence, scan: _Line) -> bool:
    """Whether ``scan`` closes the fence.

    Only a run of the same character, at least as long as the opener's and with nothing
    after it, closes a fence, and only from the opener's own container: the same quote
    depth, no list marker, and at most three spaces in from the container's content. A
    quoted or bulleted marker, or one indented four or more, inside an unquoted fence is
    fenced content. Closing early on one would read the rest of the sample as prose and
    draw an edge from it, the direction this rule must not err in.
    """
    if not (
        scan.run
        and scan.run[0] == fence.run[0]
        and len(scan.run) >= len(fence.run)
        and not scan.rest
        and scan.depth == fence.depth
        and not scan.listed
    ):
        return False
    # A closer sits at most three spaces past its container's content, whatever the
    # opener's own indent: outside a list that is the margin, so "   ```" opening a fence
    # is not closed by "      ```", which is fenced content.
    floor = fence.col if fence.listed else 0
    return floor <= scan.indent <= floor + 3


def _prose(body: str) -> str:
    """The body with fenced and indented code removed: a sample is not an instruction.

    An indented code block is four or more columns past the content of the list item it
    sits in (or past the margin outside a list), and it cannot interrupt a paragraph, so
    it starts only after a blank line, a heading or a change of quote depth.
    """
    kept = []
    fence: _Fence | None = None
    item_col = 0  # the content column of the list item the text sits in, else 0
    depth = 0
    boundary = True  # whether the previous line ended a paragraph
    indented = False
    for line in body.splitlines():
        scan = _scan(line)
        if fence:
            if not _ends_container(fence, scan):
                if _closes(fence, scan):
                    fence = None
                    boundary = True
                continue
            fence = None
        if scan.depth != depth:
            depth, item_col, boundary, indented = scan.depth, 0, True, False
        if scan.blank:
            kept.append(line)
            boundary = True
            continue
        if (boundary or indented) and scan.indent >= item_col + 4:
            indented = True
            continue
        indented = False
        if scan.listed:
            item_col = scan.col
        elif boundary and scan.indent < item_col:
            item_col = 0  # a paragraph back at the margin has left the list
        fence = _opens(scan)
        if fence:
            continue
        kept.append(line)
        boundary = not scan.listed and not scan.run and bool(_HEADING.match(scan.rest))
    return "\n".join(kept)


# A sentence that opens "Do not use for" or "Not for" says where the skill does not
# apply, so a name inside it is the thing to send the work away from, not a hand-off.
# An ordered-list marker may lead it: "1)" stays attached, where "1." is split off as
# a sentence of its own, so the digits are skipped here for both forms to behave alike.
_BOUNDARY = re.compile(r"[\W_]*(?:\d{1,9}[.)])?[\W_]*(?:do not use for|not for)\b", re.IGNORECASE)


# These end in a full stop that does not end the sentence: "e.g. `maker`" inside a
# boundary sentence must not split it, or the names after the abbreviation would escape.
_ABBREVIATION = re.compile(r"(?:^|[\s(])(?:e\.g|i\.e|etc|vs|cf)\.$", re.IGNORECASE)
_HEADING = re.compile(r" {0,3}#{1,6}(?:\s|$)")


def _sentences(text: str) -> list[str]:
    """``text`` split after each sentence-ending mark that sits outside a code span."""
    sentences = []
    start = 0
    inside = False
    for index, char in enumerate(text):
        if char == "`":
            inside = not inside
        elif (
            char in ".!?"
            and not inside
            and (index + 1 == len(text) or text[index + 1].isspace())
            and not _ABBREVIATION.search(text[start : index + 1])
        ):
            sentences.append(text[start : index + 1])
            start = index + 1
    sentences.append(text[start:])
    return sentences


def _paragraphs(text: str) -> list[str]:
    """``text`` as paragraphs, each one's physical lines joined by a space.

    SKILL.md prose wraps at about ninety columns, so a sentence routinely runs onto the
    next line and the boundary rule has to see all of it. A blank line, a list item, a
    heading or a change of quote depth starts a new paragraph, so one bullet's "Not for"
    cannot swallow the bullet after it.
    """
    paragraphs: list[list[str]] = []
    previous: _Line | None = None
    after_heading = False
    for line in text.splitlines():
        scan = _scan(line)
        if scan.blank:
            previous = None
            continue
        expanded = line.expandtabs(4)
        pos = 0
        while match := _QUOTE.match(expanded, pos):
            pos = match.end()
        content = expanded[pos:].strip()
        heading = bool(_HEADING.match(content))
        if (
            previous is None
            or scan.listed
            or heading
            or after_heading
            or previous.depth != scan.depth
        ):
            paragraphs.append([])
        paragraphs[-1].append(content)
        previous, after_heading = scan, heading
    return [" ".join(lines) for lines in paragraphs]


# A comment renders as nothing, so a name inside one is not an instruction anyone reads.
# One left unclosed runs to the end, as an HTML block of that kind does.
_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)


def _uncommented(text: str) -> str:
    """``text`` with every HTML comment removed, keeping its line breaks."""
    return _COMMENT.sub(lambda match: "\n" * match.group().count("\n"), text)


def _code_spans(text: str) -> set[str]:
    """The contents of every single-backtick span in the paragraphs of ``text``.

    A sentence that opens "Do not use for" or "Not for" is left out, wherever in its
    paragraph it sits and however many lines it wraps over: the names in it are what the
    skill sends work away from.
    """
    spans: set[str] = set()
    for paragraph in _paragraphs(text):
        kept = "".join(s for s in _sentences(paragraph) if not _BOUNDARY.match(s))
        parts = kept.split("`")
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
        for span in _code_spans(_uncommented(_prose(skill.body))):
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
