#!/usr/bin/env python3
"""Lint a built page for the tells of a default, generated design.

Reads .html, .htm and .css files (and the <style> blocks inside HTML), applies the rule
table in assets/rules.json and prints one finding per line as
`file:line rule-id tier message`. It never writes and never fetches. Rules marked judged
are listed as a manual checklist, not tested.

Exit codes: 0 no unwaived finding, 1 a floor finding or an unwaived taste finding,
2 the input is unusable. Standard library only.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

TIERS = ("floor", "taste")
KINDS = ("css", "html", "copy", "judged")
SOURCE_SUFFIXES = (".html", ".htm", ".css")
DEFAULT_RULES = Path(__file__).resolve().parent.parent / "assets" / "rules.json"


class UnusableError(Exception):
    """An input cannot be read; nothing should be reported from it."""


# --- the model ----------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    id: str
    tier: str
    kind: str
    message: str
    check: str = ""
    params: dict = field(default_factory=dict)
    stricter: dict = field(default_factory=dict)  # parameter -> "higher" or "lower"


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    detail: str = ""


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    tier: str
    message: str
    detail: str = ""


@dataclass(frozen=True)
class Decl:
    file: str
    line: int
    selector: str
    prop: str
    value: str
    context: tuple[str, ...]


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict
    line: int
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)


@dataclass(eq=False)
class Text:
    text: str
    line: int
    parent: Node


@dataclass
class Doc:
    file: str
    root: Node
    nodes: list[Node]
    texts: list[Text]
    styles: list[tuple[str, int]]
    raw: str

    @property
    def is_document(self) -> bool:
        return any(n.tag in ("html", "head", "body") for n in self.nodes)


@dataclass
class Page:
    decls: list[Decl]
    css_text: str
    css_origin: tuple[str, int] | None
    docs: list[Doc]


# --- parsing: css -------------------------------------------------------------------

COMMENT = re.compile(r"/\*.*?\*/", re.S)
IMPORTANT = re.compile(r"\s*!\s*important\s*$", re.I)
DECLARATION_ONLY_AT_RULES = ("@font-face", "@property", "@page")


def strip_comments(css: str) -> str:
    """Blank comments out but keep their newlines, so line numbers stay true."""
    return COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), css)


def resolve_nesting(stack: list[str]) -> tuple[str, tuple[str, ...]]:
    """The selector a declaration applies to once nested rules are joined, and its at-rules.

    `.card { &:hover { ... } }` applies to `.card:hover`; a rule nested without `&` applies
    to a descendant. An at-rule such as @media is context, not part of the selector.
    """
    selector = ""
    context: list[str] = []
    for entry in stack:
        if entry.startswith("@"):
            context.append(entry)
        elif not selector:
            selector = entry
        else:
            parents = split_top_level(selector)
            children = split_top_level(entry)
            selector = ", ".join(
                child.replace("&", parent) if "&" in child else f"{parent} {child}"
                for parent in parents
                for child in children
            )
    if not selector:  # a declaration straight inside an at-rule, such as @font-face
        return stack[-1], tuple(context[:-1])
    return selector, tuple(context)


def clean_value(value: str) -> str:
    """The value on one line, without a trailing !important: priority does not change a value."""
    return IMPORTANT.sub("", " ".join(value.split()))


def parse_css(css: str, file: str, first_line: int = 1) -> list[Decl]:
    css = strip_comments(css)
    decls: list[Decl] = []
    stack: list[str] = []
    buf: list[str] = []
    buf_line = first_line
    line = first_line
    depth = 0
    quote = ""

    def flush() -> None:
        text = "".join(buf).strip()
        buf.clear()
        if ":" not in text or not stack:
            return
        prop, _, value = text.partition(":")
        selector, context = resolve_nesting(stack)
        decls.append(
            Decl(file, buf_line, selector, prop.strip().lower(), clean_value(value), context)
        )

    for ch in css:
        if ch == "\n":
            line += 1
        if quote:
            buf.append(ch)
            quote = "" if ch == quote else quote
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in ";{}":
            if ch == "{":
                stack.append(" ".join("".join(buf).split()))
                buf.clear()
            else:
                flush()
                if ch == "}" and stack:
                    stack.pop()
            continue
        if not buf and not ch.isspace():
            buf_line = line
        if buf or not ch.isspace():
            buf.append(ch)
    return decls


def usable(decls: list[Decl]) -> list[Decl]:
    """Declarations that style something; a font or property definition declares, not uses."""
    return [
        d
        for d in decls
        if not any(c.startswith(DECLARATION_ONLY_AT_RULES) for c in (*d.context, d.selector))
    ]


# --- parsing: html ------------------------------------------------------------------

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}  # fmt: skip
CLOSES_OPEN = {
    "li": {"li"},
    "p": {"p"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
    "tr": {"tr"},
    "td": {"td", "th"},
    "th": {"td", "th"},
    "option": {"option"},
}


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, 1)
        self.stack = [self.root]
        self.nodes: list[Node] = []
        self.texts: list[Text] = []
        self.styles: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        if self.stack[-1].tag in CLOSES_OPEN.get(tag, ()):
            self.stack.pop()
        node = Node(tag, {k: v or "" for k, v in attrs}, self.getpos()[0], self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        top = self.stack[-1]
        if top.tag == "style":
            self.styles.append((data, self.getpos()[0]))
        elif top.tag not in ("script", "noscript") and data.strip():
            self.texts.append(Text(data, self.getpos()[0], top))


def parse_html(text: str, file: str) -> Doc:
    builder = TreeBuilder()
    builder.feed(text)
    builder.close()
    return Doc(file, builder.root, builder.nodes, builder.texts, builder.styles, text)


# --- the page: every file linted together --------------------------------------------


def build_page(sources: list[tuple[str, str]]) -> Page:
    decls: list[Decl] = []
    css_parts: list[str] = []
    origin: tuple[str, int] | None = None
    docs: list[Doc] = []
    for file, text in sources:
        if file.lower().endswith(".css"):
            chunks = [(text, 1)]
        else:
            doc = parse_html(text, file)
            docs.append(doc)
            chunks = doc.styles
        for chunk, first_line in chunks:
            origin = origin or (file, first_line)
            decls.extend(parse_css(chunk, file, first_line))
            css_parts.append(strip_comments(chunk))
    return Page(usable(decls), "\n".join(css_parts), origin, docs)


# --- checks: one function per kind of test, parameters come from the rule table ------


NOT_PSEUDO = re.compile(r":not\(", re.I)


def strip_not(part: str) -> str:
    """The part without its :not( ... ) groups, so a marker inside one is not read as present."""
    out, index = [], 0
    while True:
        match = NOT_PSEUDO.search(part, index)
        if not match:
            out.append(part[index:])
            return "".join(out)
        out.append(part[index : match.start()])
        depth, cursor = 1, match.end()
        while cursor < len(part) and depth:
            depth += (part[cursor] == "(") - (part[cursor] == ")")
            cursor += 1
        index = cursor


NO_JS_NOT = re.compile(r"(?<![\w.#:-])(html|:root):not\(\s*\.no-js\s*\)", re.I)


def selector_matches(selector: str, include: str | None, exclude: str | None) -> bool:
    """True when some part of the selector list matches `include` and not `exclude`.

    Each part is judged alone: a list is not excused because another part carries the
    excusing marker, and a marker inside :not( ) excludes nothing.
    """
    for part in split_top_level(selector):
        # html:not(.no-js) is the scripts-on scope under another name; .no-js lives on
        # the root element, so on any other element it says nothing about scripts
        part = NO_JS_NOT.sub(r"\1.js", part)
        if include and not re.search(include, part, re.I):
            continue
        if exclude and re.search(exclude, strip_not(part), re.I):
            continue
        return True
    return False


URL = re.compile(r"url\(\s*(?:\"[^\"]*\"|'[^']*'|[^)]*)\)", re.I)


def check_declaration(page: Page, params: dict) -> list[Hit]:
    hits = []
    for d in page.decls:
        if not re.fullmatch(params["property"], d.prop, re.I):
            continue
        # a file name is not a colour or a size, so url( ) is blanked before the value is read
        if "value" in params and not re.search(params["value"], URL.sub("url()", d.value), re.I):
            continue
        if not selector_matches(d.selector, params.get("selector"), params.get("selector_not")):
            continue
        # each at-rule is tested whole: a search over the joined text would also excuse
        # `not (scripting: enabled)` and a comma list with another alternative
        if params.get("context_not") and any(
            re.fullmatch(params["context_not"], c.strip(), re.I) for c in d.context
        ):
            continue
        if params.get("unless_sibling_value") and any(
            other.file == d.file
            and other.selector == d.selector
            and other.prop == d.prop
            and re.search(params["unless_sibling_value"], other.value, re.I)
            for other in page.decls
        ):
            continue
        hits.append(Hit(d.file, d.line, f"{d.selector} {{ {d.prop}: {d.value} }}"))
    return hits


LENGTH = re.compile(r"(\d*\.?\d+)\s*(px|rem|em|pt)?", re.I)


def check_number_below(page: Page, params: dict) -> list[Hit]:
    """A length (unit px, rem and em read at 16px) or a unitless number under a minimum."""
    hits = []
    for d in page.decls:
        if not re.fullmatch(params["property"], d.prop, re.I):
            continue
        if not selector_matches(d.selector, params.get("selector"), params.get("selector_not")):
            continue
        match = LENGTH.fullmatch(d.value.strip())
        if not match:
            continue
        number, unit = float(match.group(1)), (match.group(2) or "").lower()
        if params["unit"] == "px" and unit:
            number *= {"px": 1, "pt": 4 / 3}.get(unit, 16)
        elif params["unit"] != unit:
            continue
        if number < params["minimum"]:
            hits.append(Hit(d.file, d.line, f"{d.selector} {{ {d.prop}: {d.value} }}"))
    return hits


def check_css_requires(page: Page, params: dict) -> list[Hit]:
    if page.css_origin is None or not re.search(params["when"], page.css_text, re.I | re.M):
        return []
    when_html = params.get("when_html")
    if when_html and page.docs and not any(re.search(when_html, d.raw, re.I) for d in page.docs):
        return []
    if re.search(params["require"], page.css_text, re.I):
        return []
    file, line = page.css_origin
    return [Hit(file, line, f"nothing in the styles matches {params['require']!r}")]


def has_ancestor(node: Node, ancestor: Node) -> bool:
    while node.parent is not None:
        node = node.parent
        if node is ancestor:
            return True
    return False


def text_within(doc: Doc, node: Node) -> str:
    return " ".join(
        t.text.strip() for t in doc.texts if t.parent is node or has_ancestor(t.parent, node)
    )


def check_required_element(page: Page, params: dict) -> list[Hit]:
    """Each full document must hold the element, with the attribute or text asked for."""
    hits = []
    for doc in (d for d in page.docs if d.is_document):
        wanted = {k: v.lower() for k, v in params.get("attrs", {}).items()}
        found = [
            n
            for n in doc.nodes
            if n.tag == params["tag"]
            and all(n.attrs.get(k, "").lower() == v for k, v in wanted.items())
        ]
        if not found:
            hits.append(Hit(doc.file, 1, f"no <{params['tag']}> element"))
            continue
        node = found[0]
        if "need_attr" in params and not node.attrs.get(params["need_attr"], "").strip():
            hits.append(Hit(doc.file, node.line, f"<{node.tag}> has no {params['need_attr']}"))
        if params.get("need_text") and not text_within(doc, node):
            hits.append(Hit(doc.file, node.line, f"<{node.tag}> is empty"))
    return hits


HEADING = re.compile(r"h([1-6])")


def check_heading_order(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        level = 0 if doc.is_document else None
        for node in doc.nodes:
            match = HEADING.fullmatch(node.tag)
            if not match:
                continue
            new = int(match.group(1))
            if level is not None and new > level + 1:
                where = f"h{level} is followed by" if level else "the document opens on"
                hits.append(Hit(doc.file, node.line, f"{where} h{new}"))
            level = new
    return hits


def check_phrase_list(page: Page, params: dict) -> list[Hit]:
    phrases = sorted(params["phrases"], key=len, reverse=True)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(p) for p in phrases) + r")(?!\w)", re.I)
    return text_matches(page, pattern)


def text_matches(page: Page, pattern: re.Pattern, tags=(), class_pattern: str = "") -> list[Hit]:
    hits = []
    for doc in page.docs:
        for text in doc.texts:
            if tags or class_pattern:
                classes = text.parent.attrs.get("class", "").split()
                inside = text.parent.tag in tags or any(
                    re.search(class_pattern, c, re.I) for c in classes if class_pattern
                )
                if not inside:
                    continue
            for match in pattern.finditer(text.text):
                line = text.line + text.text.count("\n", 0, match.start())
                hits.append(Hit(doc.file, line, match.group(0).strip()))
    return hits


# --- css checks that read values ----------------------------------------------------

GRADIENT = re.compile(r"(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)
DIRECTION = re.compile(
    r"\s*(?:to\s|[-\d.]+(?:deg|turn|rad|grad)|circle|ellipse|closest|farthest|at\s|from\s|in\s)",
    re.I,
)
HEX_COLOUR = re.compile(r"#([0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})\b", re.I)
FUNC_COLOUR = re.compile(r"\b(hsla?|oklch|rgba?)\(([^)]*)\)", re.I)
NUMBER = re.compile(r"-?\d*\.?\d+")
CHANNEL = re.compile(r"(-?\d*\.?\d+)(%?)")


def gradient_args(value: str) -> list[str]:
    """The text inside each gradient( ) in a value, parentheses balanced."""
    found = []
    for match in GRADIENT.finditer(value):
        depth, index = 1, match.end()
        while index < len(value) and depth:
            depth += (value[index] == "(") - (value[index] == ")")
            index += 1
        found.append(value[match.end() : index - 1])
    return found


def split_top_level(text: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def hex_hue(digits: str) -> tuple[float, float]:
    if len(digits) in (3, 4):
        digits = "".join(c * 2 for c in digits)
    return rgb_hue(*(int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)))


def rgb_hue(r: float, g: float, b: float) -> tuple[float, float]:
    r, g, b = (min(1.0, max(0.0, c)) for c in (r, g, b))
    hue, _, saturation = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, saturation


def functional_rgb(body: str) -> tuple[float, float] | None:
    """Hue and saturation of rgb(r, g, b) or rgb(r g b / a), in numbers or percentages."""
    channels = CHANNEL.findall(body.split("/")[0])[:3]
    if len(channels) < 3:
        return None
    r, g, b = (float(n) / (100 if pct else 255) for n, pct in channels)
    return rgb_hue(r, g, b)


def in_hue_band(args: str, p: dict) -> bool:
    """Whether a gradient uses a colour in the purple, blue or pink band."""
    lowered = args.lower()
    if any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in p["names"]):
        return True
    for match in HEX_COLOUR.finditer(args):
        hue, saturation = hex_hue(match.group(1))
        if p["hue_min"] <= hue <= p["hue_max"] and saturation >= p["min_saturation"]:
            return True
    for match in FUNC_COLOUR.finditer(args):
        numbers = [float(n) for n in NUMBER.findall(match.group(2))]
        if match.group(1).lower() == "oklch" and len(numbers) >= 3:
            _, chroma, hue = numbers[:3]
            if p["oklch_hue_min"] <= hue % 360 <= p["oklch_hue_max"] and chroma >= p["min_chroma"]:
                return True
        elif match.group(1).lower().startswith("rgb"):
            rgb = functional_rgb(match.group(2))
            if rgb and p["hue_min"] <= rgb[0] <= p["hue_max"] and rgb[1] >= p["min_saturation"]:
                return True
        elif match.group(1).lower().startswith("hsl") and len(numbers) >= 2:
            if (
                p["hue_min"] <= numbers[0] % 360 <= p["hue_max"]
                and numbers[1] / 100 >= p["min_saturation"]
            ):
                return True
    return False


def check_gradient_hue(page: Page, params: dict) -> list[Hit]:
    return [
        Hit(d.file, d.line, f"{d.selector} {{ {d.prop} }}")
        for d in page.decls
        if any(in_hue_band(args, params) for args in gradient_args(d.value))
    ]


def check_gradient_stops(page: Page, params: dict) -> list[Hit]:
    hits = []
    for d in page.decls:
        for args in gradient_args(d.value):
            parts = split_top_level(args)
            stops = len(parts) - (1 if parts and DIRECTION.match(parts[0]) else 0)
            if stops > params["max"]:
                hits.append(Hit(d.file, d.line, f"{stops} stops in {d.selector}"))
    return hits


GENERIC_VALUES = {"inherit", "initial", "unset", "revert", "normal", "bolder", "lighter"}


def normalise_family(value: str) -> str | None:
    first = value.split(",")[0].strip().strip("\"'").lower()
    return None if not first or "var(" in value or first in GENERIC_VALUES else first


def normalise_weight(value: str) -> str | None:
    value = {"normal": "400", "bold": "700"}.get(value.strip().lower(), value.strip())
    return value if value.isdigit() else None


NORMALISERS = {"family": normalise_family, "weight": normalise_weight}


def check_distinct_values(page: Page, params: dict) -> list[Hit]:
    seen: list[str] = []
    hits = []
    for d in page.decls:
        if not re.fullmatch(params["property"], d.prop, re.I):
            continue
        value = NORMALISERS[params["normalise"]](d.value)
        if value is None or value in seen:
            continue
        seen.append(value)
        if len(seen) == params["max"] + 1:
            hits.append(Hit(d.file, d.line, f"more than {params['max']} distinct values"))
    if hits:
        hits[0] = Hit(hits[0].file, hits[0].line, f"{len(seen)} distinct: {', '.join(seen)}")
    return hits


# --- html checks that read structure ------------------------------------------------


def descendants(node: Node):
    for child in node.children:
        yield child
        yield from descendants(child)


def class_tokens(node: Node) -> list[str]:
    return node.attrs.get("class", "").split()


def signature(node: Node) -> tuple[str, ...]:
    return (node.tag, *(d.tag for d in descendants(node)))


def check_attr_requires(page: Page, params: dict) -> list[Hit]:
    return [
        Hit(
            doc.file, n.line, f"<{n.tag}> has {params['when_attr']} but no {params['require_attr']}"
        )
        for doc in page.docs
        for n in doc.nodes
        if n.tag == params["tag"]
        and params["when_attr"] in n.attrs
        and params["require_attr"] not in n.attrs
    ]


def declared_area(node: Node) -> int:
    sizes = [re.match(r"\d+", node.attrs.get(a, "")) for a in ("width", "height")]
    return int(sizes[0].group()) * int(sizes[1].group()) if all(sizes) else 0


def check_lazy_largest(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        images = [n for n in doc.nodes if n.tag == "img"]
        if not images:
            continue
        largest = max(images, key=declared_area)  # the first one when no size is declared
        if largest.attrs.get("loading", "").lower() == "lazy":
            hits.append(Hit(doc.file, largest.line, "the largest image has loading=lazy"))
    return hits


MEDIA_TAGS = {"img", "svg", "video", "picture", "canvas", "iframe", "object"}


def check_placeholder(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        for n in doc.nodes:
            if n.tag == "img" and re.search(params["src_pattern"], n.attrs.get("src", ""), re.I):
                hits.append(Hit(doc.file, n.line, f"image source {n.attrs['src']!r}"))
            elif any(re.search(params["class_pattern"], c, re.I) for c in class_tokens(n)):
                shows = any(d.tag in MEDIA_TAGS for d in descendants(n)) or text_within(doc, n)
                if not shows:
                    hits.append(Hit(doc.file, n.line, "an empty placeholder block"))
    return hits


def check_nested_class(page: Page, params: dict) -> list[Hit]:
    def matches(node: Node) -> bool:
        return any(re.search(params["class_token"], c, re.I) for c in class_tokens(node))

    return [
        Hit(doc.file, inner.line, f"<{inner.tag}> inside <{outer.tag}>")
        for doc in page.docs
        for outer in doc.nodes
        if matches(outer)
        for inner in descendants(outer)
        if matches(inner)
    ]


def iconised(node: Node, params: dict) -> bool:
    return node.tag in params["icon_tags"] or any(
        params["icon_class"] in c.lower() for c in class_tokens(node)
    )


def icon_then_heading(card: Node, params: dict) -> bool:
    inner = list(descendants(card))
    icon = next((i for i, d in enumerate(inner) if iconised(d, params)), None)
    if icon is None or any(d.tag in params["heading_tags"] for d in inner[:icon]):
        return False
    return any(d.tag in params["heading_tags"] for d in inner[icon:])


def check_repeated_cards(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        for node in doc.nodes:
            kids = node.children
            if (
                len(kids) >= params["min_count"]
                and len({signature(k) for k in kids}) == 1
                and all(icon_then_heading(k, params) for k in kids)
            ):
                hits.append(Hit(doc.file, node.line, f"{len(kids)} equal icon-over-heading cards"))
    return hits


def check_eyebrow_headings(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        headings = [n for n in doc.nodes if n.tag in params["headings"]]
        marked = []
        for heading in headings:
            siblings = heading.parent.children if heading.parent else []
            index = next(i for i, s in enumerate(siblings) if s is heading)
            before = siblings[index - 1] if index else None
            if before and any(
                re.search(params["class_pattern"], c, re.I) for c in class_tokens(before)
            ):
                marked.append(heading)
        # `marked` empty also covers a page with no headings, so the division is safe
        enough = marked and len(marked) >= params["min_count"]
        if enough and len(marked) / len(headings) >= params["ratio"]:
            hits.append(Hit(doc.file, marked[0].line, f"{len(marked)} of {len(headings)} headings"))
    return hits


def check_adjacent_same_structure(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        for node in doc.nodes:
            for before, after in zip(node.children, node.children[1:], strict=False):
                if (
                    before.tag == after.tag == params["container_tag"]
                    and signature(before) == signature(after)
                    and len(signature(after)) >= params["min_nodes"]
                ):
                    hits.append(
                        Hit(doc.file, after.line, f"<{after.tag}> repeats the one before it")
                    )
    return hits


def check_closing_email(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        regions = []
        for tag in params["regions"]:
            tagged = [n for n in doc.nodes if n.tag == tag]
            regions += tagged[-1:] if tag == "section" else tagged
        for region in regions:
            for inner in descendants(region):
                if (
                    inner.tag == "input"
                    and inner.attrs.get("type", "").lower() == params["input_type"]
                ):
                    hits.append(
                        Hit(
                            doc.file,
                            inner.line,
                            f"an {params['input_type']} field in the closing <{region.tag}>",
                        )
                    )
    return hits


def counts_as_source(node: Node, source: dict) -> bool:
    """A source names a tag and the attribute that holds its address, and may require a rel."""
    if node.tag != source["tag"]:
        return False
    rel = source.get("rel")
    return not rel or rel in node.attrs.get("rel", "").lower().split()


def check_attr_values(page: Page, params: dict) -> list[Hit]:
    hits = []
    for doc in page.docs:
        seen: list[str] = []
        for node in doc.nodes:
            for source in params["sources"]:
                if not counts_as_source(node, source):
                    continue
                value = node.attrs.get(source["attr"], "")
                stem = value.split("?")[0].split("#")[0].lower()
                if stem and re.search(params["pattern"], stem, re.I) and stem not in seen:
                    seen.append(stem)
                    if len(seen) == params["min_distinct"]:
                        hits.append(Hit(doc.file, node.line, ", ".join(seen)))
    return hits


def check_text_regex(page: Page, params: dict) -> list[Hit]:
    pattern = re.compile(params["pattern"], re.I)
    return text_matches(
        page, pattern, tuple(params.get("tags", ())), params.get("class_pattern", "")
    )


# name -> (the kind of rule it serves, the function); a rule's kind must agree with it
CHECKS = {
    "declaration": ("css", check_declaration),
    "css-requires": ("css", check_css_requires),
    "number-below": ("css", check_number_below),
    "required-element": ("html", check_required_element),
    "heading-order": ("html", check_heading_order),
    "gradient-hue": ("css", check_gradient_hue),
    "gradient-stops": ("css", check_gradient_stops),
    "distinct-values": ("css", check_distinct_values),
    "attr-requires": ("html", check_attr_requires),
    "lazy-largest": ("html", check_lazy_largest),
    "placeholder": ("html", check_placeholder),
    "nested-class": ("html", check_nested_class),
    "repeated-cards": ("html", check_repeated_cards),
    "eyebrow-headings": ("html", check_eyebrow_headings),
    "adjacent-same-structure": ("html", check_adjacent_same_structure),
    "closing-email": ("html", check_closing_email),
    "attr-values": ("html", check_attr_values),
    "phrase-list": ("copy", check_phrase_list),
    "text-regex": ("copy", check_text_regex),
}


# --- the rule table -----------------------------------------------------------------


def resolve_shared(value, shared: dict):
    if isinstance(value, str) and value.startswith("$"):
        if value[1:] not in shared:
            raise UnusableError(f"rule table: unknown shared pattern {value!r}")
        return shared[value[1:]]
    if isinstance(value, dict):
        return {k: resolve_shared(v, shared) for k, v in value.items()}
    return value


# What each check reads with params[...] rather than params.get(...), so a hand-edited table
# that leaves one out is refused up front instead of raising KeyError mid-run.
REQUIRED_PARAMS = {
    "declaration": ("property",),
    "number-below": ("property", "unit", "minimum"),
    "css-requires": ("when", "require"),
    "required-element": ("tag",),
    "phrase-list": ("phrases",),
    "gradient-stops": ("max",),
    "distinct-values": ("property", "normalise", "max"),
    "attr-requires": ("tag", "when_attr", "require_attr"),
    "placeholder": ("src_pattern", "class_pattern"),
    "nested-class": ("class_token",),
    "repeated-cards": ("min_count", "icon_tags", "icon_class", "heading_tags"),
    "eyebrow-headings": ("headings", "class_pattern", "min_count", "ratio"),
    "adjacent-same-structure": ("container_tag", "min_nodes"),
    "closing-email": ("regions", "input_type"),
    "attr-values": ("sources", "pattern", "min_distinct"),
    "text-regex": ("pattern",),
}
NUMERIC_PARAMS = frozenset({"minimum", "max", "min_count", "ratio"})
REGEX_PARAMS = frozenset(
    {
        "property",
        "value",
        "selector",
        "selector_not",
        "context_not",
        "unless_sibling_value",
        "when",
        "when_html",
        "require",
        "src_pattern",
        "class_pattern",
        "class_token",
        "pattern",
    }
)


def parse_rule(raw, shared: dict) -> Rule:
    if not isinstance(raw, dict):
        raise UnusableError("rule table: a rule is not an object")
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not re.fullmatch(r"(floor|taste)-[a-z0-9-]+", rule_id):
        raise UnusableError(f"rule table: bad rule id {rule_id!r}")
    tier, kind = raw.get("tier"), raw.get("kind")
    if tier not in TIERS or not rule_id.startswith(f"{tier}-"):
        raise UnusableError(f"rule table: {rule_id} has tier {tier!r}, which its id does not match")
    if kind not in KINDS:
        raise UnusableError(f"rule table: {rule_id} has kind {kind!r}")
    message = raw.get("message")
    if not isinstance(message, str) or not message:
        raise UnusableError(f"rule table: {rule_id} has no message")
    if kind == "judged":
        return Rule(rule_id, tier, kind, message)
    check = raw.get("check")
    if check not in CHECKS or CHECKS[check][0] != kind:
        raise UnusableError(
            f"rule table: {rule_id} names check {check!r}, which is not a {kind} check"
        )
    params = resolve_shared(raw.get("params", {}), shared)
    if not isinstance(params, dict):
        raise UnusableError(f"rule table: {rule_id} has params that are not an object")
    missing = [key for key in REQUIRED_PARAMS.get(check, ()) if key not in params]
    if missing:
        raise UnusableError(f"rule table: {rule_id} lacks the {check} parameter {missing[0]!r}")
    for key in NUMERIC_PARAMS & params.keys():
        if isinstance(params[key], bool) or not isinstance(params[key], (int, float)):
            raise UnusableError(f"rule table: {rule_id} has a non-numeric {key!r}")
    for key in REGEX_PARAMS & params.keys():
        try:
            re.compile(params[key])
        except (re.error, TypeError):
            raise UnusableError(
                f"rule table: {rule_id} has an invalid pattern in {key!r}"
            ) from None
    stricter = raw.get("stricter", {})
    if not isinstance(stricter, dict) or any(
        direction not in ("higher", "lower") or name not in params
        for name, direction in stricter.items()
    ):
        raise UnusableError(f"rule table: {rule_id} has a bad stricter map")
    return Rule(rule_id, tier, kind, message, check, params, stricter)


def load_rules(path: Path) -> list[Rule]:
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UnusableError(
            f"rule table {str(path)!r}: cannot be read ({type(error).__name__})"
        ) from None
    if not isinstance(table, dict) or not isinstance(table.get("rules"), list):
        raise UnusableError(f"rule table {str(path)!r}: expected an object with a rules list")
    shared = table.get("shared", {})
    rules = [parse_rule(raw, shared) for raw in table["rules"]]
    ids = [r.id for r in rules]
    if len(set(ids)) != len(ids):
        raise UnusableError("rule table: a rule id is repeated")
    return rules


# --- running the rules --------------------------------------------------------------


def run_rules(page: Page, rules: list[Rule]) -> list[Finding]:
    found = []
    for rule in rules:
        if rule.kind == "judged":
            continue
        for hit in CHECKS[rule.check][1](page, rule.params):
            found.append(Finding(hit.file, hit.line, rule.id, rule.tier, rule.message, hit.detail))
    return sorted(found, key=lambda f: (f.file, f.line, f.rule))


# --- reading input ------------------------------------------------------------------


def expand_paths(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in SOURCE_SUFFIXES))
        elif path.suffix.lower() in SOURCE_SUFFIXES:
            files.append(path)
        else:
            raise UnusableError(f"{str(path)!r}: only .html, .htm and .css files are read")
    if not files:
        raise UnusableError("no .html, .htm or .css file to read")
    return files


def read_sources(paths: list[Path]) -> list[tuple[str, str]]:
    sources = []
    for path in expand_paths(paths):
        try:
            sources.append((str(path), path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError) as error:
            raise UnusableError(f"{str(path)!r}: cannot be read ({type(error).__name__})") from None
    return sources


# --- the decision record: waivers and overrides ------------------------------------

WAIVE = re.compile(r"^\s*(?:[-*]\s*)?waive:\s*(\S+)\s*(?:(?:—|–|--|-)\s*(.*?))?\s*$")
OVERRIDE = re.compile(r"^\s*(?:[-*]\s*)?override:\s*(\S+)\s+([\w-]+)=(\S+)\s*$")


@dataclass(frozen=True)
class Decisions:
    waivers: dict[str, str]  # rule id -> reason, which may be empty
    overrides: list[tuple[str, str, str]]  # rule id, parameter, value


@dataclass(frozen=True)
class Applied:
    rule: str
    parameter: str
    old: float
    new: float


def parse_decisions(text: str) -> Decisions:
    waivers: dict[str, str] = {}
    overrides: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if match := WAIVE.match(line):
            waivers[match.group(1)] = (match.group(2) or "").strip()
        elif match := OVERRIDE.match(line):
            overrides.append((match.group(1), match.group(2), match.group(3)))
    return Decisions(waivers, overrides)


def override_number(value: str, current: float) -> float | None:
    """The value as a number of the parameter's own type, or None when it is not usable."""
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    if isinstance(current, int):
        return int(number) if number == int(number) else None
    return number


def loosens(rule: Rule, name: str, default: float, new: float) -> bool | None:
    """Whether a floor override is looser than the table's value; None when the way is unknown."""
    direction = rule.stricter.get(name)
    if direction is None:
        return None
    return new < default if direction == "higher" else new > default


def apply_overrides(rules: list[Rule], overrides: list[tuple[str, str, str]]):
    """Return the rules with the record's parameter values, those applied, and each refusal.

    A floor rule may only be made stricter than the table's value, because an override that
    loosens one does the work of a waiver without a reason. A taste rule may go either way.
    """
    defaults = {r.id: r for r in rules}
    by_id = dict(defaults)
    applied: list[Applied] = []
    notes: list[str] = []
    for rule_id, name, value in overrides:
        rule = by_id.get(rule_id)
        if rule is None:
            notes.append(f"override of {rule_id} ignored: {rule_id} is not a rule in the table")
            continue
        current = rule.params.get(name)
        if not isinstance(current, (int, float)) or isinstance(current, bool):
            notes.append(f"override ignored: {rule_id} has no parameter {name} that is a number")
            continue
        number = override_number(value, current)
        if number is None:
            notes.append(
                f"override refused: {value!r} is not a finite, non-negative number of the "
                f"right kind for {rule_id} {name}"
            )
            continue
        if rule.tier == "floor":
            looser = loosens(rule, name, defaults[rule_id].params[name], number)
            if looser is None:
                notes.append(
                    f"override refused: {rule_id} {name}={value} has no declared stricter "
                    "direction, so a floor rule cannot be changed through it"
                )
                continue
            if looser:
                notes.append(
                    f"override refused: {rule_id} {name}={value} would loosen a floor rule, "
                    "which cannot be waived or relaxed"
                )
                continue
        by_id[rule_id] = Rule(
            rule.id, rule.tier, rule.kind, rule.message, rule.check,
            {**rule.params, name: number}, rule.stricter,
        )  # fmt: skip
        applied.append(Applied(rule_id, name, current, number))
    return [by_id[r.id] for r in rules], applied, notes


def waiver_problems(waivers: dict[str, str], rules: list[Rule]) -> list[str]:
    by_id = {r.id: r for r in rules}
    notes = []
    for rule_id, reason in waivers.items():
        if rule_id not in by_id:
            notes.append(f"waiver ignored: {rule_id} is not a rule in the table")
        elif by_id[rule_id].tier == "floor":
            notes.append(f"waiver refused: {rule_id} is a floor rule and cannot be waived")
        elif not reason:
            notes.append(f"waiver ignored: {rule_id} gives no reason")
    return notes


def waiver_reason(finding: Finding, waivers: dict[str, str]) -> str:
    """The reason a finding is waived, or an empty string when it is not."""
    return waivers.get(finding.rule, "") if finding.tier == "taste" else ""


# --- report -------------------------------------------------------------------------


def summarise(findings: list[Finding], waivers: dict[str, str]) -> dict[str, int]:
    waived = [f for f in findings if waiver_reason(f, waivers)]
    open_ = [f for f in findings if f not in waived]
    return {
        "floor": sum(f.tier == "floor" for f in open_),
        "taste": sum(f.tier == "taste" for f in open_),
        "waived": len(waived),
    }


def exit_code(summary: dict[str, int]) -> int:
    return 1 if summary["floor"] or summary["taste"] else 0


def format_finding(f: Finding) -> str:
    return f"{f.file}:{f.line} {f.rule} {f.tier} {f.message}" + (
        f" [{f.detail}]" if f.detail else ""
    )


def format_number(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def report_text(findings, rules, waivers, applied, summary) -> str:
    lines = [format_finding(f) for f in findings if not waiver_reason(f, waivers)]
    lines += [
        f"override {a.rule} {a.parameter}: {format_number(a.old)} -> {format_number(a.new)}"
        for a in applied
    ]
    lines += [
        f"waived {f.rule}: {waiver_reason(f, waivers)} ({f.file}:{f.line})"
        for f in findings
        if waiver_reason(f, waivers)
    ]
    manual = [r for r in rules if r.kind == "judged"]
    if manual:
        lines.append("Manual checks (judged, not tested):")
        lines += [f"  {r.id} {r.tier} {r.message}" for r in manual]
    total = summary["floor"] + summary["taste"]
    lines.append(
        f"{total} findings ({summary['floor']} floor, {summary['taste']} taste), "
        f"{summary['waived']} waived"
    )
    return "\n".join(lines)


def report_json(findings, rules, waivers, applied, notes, summary) -> str:
    return json.dumps(
        {
            "findings": [
                {
                    "file": f.file,
                    "line": f.line,
                    "rule": f.rule,
                    "tier": f.tier,
                    "message": f.message,
                    "detail": f.detail,
                    "waived": bool(waiver_reason(f, waivers)),
                    "reason": waiver_reason(f, waivers),
                }
                for f in findings
            ],
            "manual": [
                {"rule": r.id, "tier": r.tier, "message": r.message}
                for r in rules
                if r.kind == "judged"
            ],
            "overrides": [
                {"rule": a.rule, "parameter": a.parameter, "old": a.old, "new": a.new}
                for a in applied
            ],
            "refused": notes,
            "summary": summary,
        },
        indent=2,
    )


def read_decisions(path: Path | None) -> Decisions:
    if path is None:
        return Decisions({}, [])
    try:
        return parse_decisions(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise UnusableError(f"{str(path)!r}: cannot be read ({type(error).__name__})") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a built page for generic design tells.")
    parser.add_argument("paths", nargs="+", type=Path, help=".html, .htm or .css files")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="the rule table")
    parser.add_argument("--waivers", type=Path, help="the decision record to read waivers from")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    try:
        decisions = read_decisions(args.waivers)
        rules, applied, notes = apply_overrides(load_rules(args.rules), decisions.overrides)
        page = build_page(read_sources(args.paths))
    except UnusableError as error:
        print(f"unusable input: {error}", file=sys.stderr)
        return 2
    notes += waiver_problems(decisions.waivers, rules)
    findings = run_rules(page, rules)
    summary = summarise(findings, decisions.waivers)
    if args.json:
        print(report_json(findings, rules, decisions.waivers, applied, notes, summary))
    else:
        print(report_text(findings, rules, decisions.waivers, applied, summary))
    for note in notes:
        print(note, file=sys.stderr)
    return exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
