#!/usr/bin/env python3
"""Export every skill as a self-contained Markdown file any assistant can read.

The skills in this repository are plain procedures. Nothing in them is specific to one
vendor — two files mention Claude at all, and both do it because the fact is about Claude
— but the *packaging* is: a `SKILL.md` with YAML frontmatter, sitting in a plugin with a
manifest, discovered by a marketplace. Chat assistants such as ChatGPT have no skill
loader and no marketplace to read, so the work does not travel there, and pasting a
`SKILL.md` into one of them hands the reader frontmatter it cannot use and `references/`
pointers it cannot open.

This flattens each skill into one file that stands alone:

- the frontmatter becomes a plain "Use this when" line, which is the only part of it a
  model without a skills runtime can act on
- every `references/*.md` is inlined as a section with its headings demoted to nest, and
  every pointer naming one is rewritten to name that section instead of a path — in the
  reference text as well as in the body, because a reference sending you to a sibling
  reference is as much a dangling pointer for a reader with no filesystem
- `assets/` and `scripts/` are inlined fenced, because a template or a script is a thing
  to copy rather than to read, and a script named in prose is a path a flattened copy
  cannot otherwise provide
- a path inside a fenced block is left exactly as written. It is part of a command, and
  the command needs it; the inlined section is what tells the reader which file to create

Output lands in `dist/portable/`: one file per skill, one per plugin, an index that lists
every description so a model can choose between them the way a skills runtime would, a
router — one line per skill, drawn from its own description, naming when it applies and
the path to open then, small enough to paste into a repository's own `AGENTS.md` rather
than pointing at a whole bundle — plus one narrower router per plugin, and a `LICENSE`
and `NOTICE` copied from the repository root so the release zip carries them too. CI
builds it on every run and uploads the result, so the files exist for someone with no
toolchain; `--check` verifies without writing, for when you only want the gate.

Standard library only, like the validator it imports.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import html
import posixpath
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402
from skillcheck.rules import BUNDLED_PATH_RE, find_plugins, find_skills  # noqa: E402

# Reusing the validator's own pointer regex, rather than a narrower local copy, is the
# point: the local copy only matched a flat `references/<x>.md`, `assets/<x>.md` or
# `scripts/<x>.<ext>`, so a nested `references/deep/topic.md` or a non-Markdown
# `assets/checklist.txt` was neither inlined nor reported — `--check` said clean while
# the export still pointed at a file the reader could not open. `BUNDLED_PATH_RE` has no
# capturing group, so callers below match on ``match.group(0)``.
BUNDLED_RE = BUNDLED_PATH_RE
# How to fence a shipped script, by extension. Anything unlisted is fenced without a
# language rather than guessed at.
SCRIPT_LANGUAGES = {".sh": "bash", ".bash": "bash", ".py": "python", ".js": "javascript"}
# How to fence a shipped asset, by extension. Unlike a script, an asset with no
# recognised extension still gets a language rather than none: `text` says the block
# was checked rather than guessed at, and every asset used to be fenced as `markdown`
# regardless of its actual extension — a checklist.txt or a config.yaml labelled that
# way reads as a claim about its syntax that is simply wrong.
ASSET_LANGUAGES = {
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".txt": "text",
}
# Any fence opener, with its full run of markers: the closing fence has to use the same
# character and be at least as long, or a four-backtick block quoting a three-backtick
# example closes early and everything after it is read as prose.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
ATX_RE = re.compile(r"^(#{1,6})(\s+)")
# The underline of a setext heading: a run of `=` or `-` and nothing else.
SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(?:=+|-+) *$")
# Blockquote markers alone, so the indentation left over is the line's own, and a list item
# marker with the width of its content: group 3 is the spaces after the marker.
QUOTE_PREFIX_RE = re.compile(r"^(?: {0,3}> ?)*")
ITEM_RE = re.compile(r"^( *)([-*+]|\d+[.)])(?:( +)(?=\S)|\s*$)")
# What may sit between the start of a line and a code fence: blockquote markers and list
# markers, however deeply nested and in either order. A fenced example quoted with `>` or
# nested under a bullet is still a fence. Group `item` is set when any list marker is there.
CONTAINER_PREFIX_RE = re.compile(r"^(?:\s{0,3}>|\s*(?P<item>(?:[-*+]|\d+[.)])\s+))*\s*")
# The start of an HTML block of types 1-6 (not a comment, which is handled on its own), tested
# on the text after any container prefix. Group 1 names a type-1 tag, group 2 is a type-6 tag.
HTML_BLOCK_START_RE = re.compile(
    r"^ {0,3}(?:<(script|pre|style|textarea)(?:\s|>|$)|<(\?|![A-Za-z]|!\[CDATA\[)"
    r"|</?(?:address|article|aside|blockquote|center|details|dialog|dir|div|dl|dt|dd|fieldset"
    r"|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend"
    r"|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|section|source"
    r"|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:\s|/?>|$))",
    re.I,
)
# A line that starts a block which can interrupt a paragraph, tested on the text after any
# container prefix: a thematic break or setext underline, or an HTML block of types 1-6
# (a comment, a processing instruction, a declaration, or a block-level tag).
BLOCK_START_RE = re.compile(
    r"^ {0,3}(?:(?:[-*_])(?: *[-*_]){2,} *$|=+ *$|-+ *$|<(?:!--|\?|![A-Za-z]|!\[CDATA\[)"
    r"|<(?:script|pre|style|textarea)(?:\s|>|$)"
    r"|</?(?:address|article|aside|blockquote|center|details|dialog|dir|div|dl|dt|dd|fieldset"
    r"|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend"
    r"|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|section|source"
    r"|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:\s|/?>|$))",
    re.I,
)
# A raw HTML element tag (open, close or self-closing, with attributes) or a comment, the
# only inline HTML that vanishes from a rendered heading. A tag name must start with a
# letter and be followed by whitespace, `/` or `>`, which keeps `<https://x>` and
# `<me@x.com>` (autolinks, whose text is shown) from reading as tags. Quoted values may hold
# angle brackets. An attribute may follow a closing quote with no space, which a renderer
# reads as text: refusing an `id` there errs toward failing the export.
_TAG_ATTRIBUTE = (
    r"""(?:\s+|(?<=["']))[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
)
HTML_TAG_RE = re.compile(
    rf"<[A-Za-z][A-Za-z0-9-]*(?:{_TAG_ATTRIBUTE})*\s*/?>|</[A-Za-z][A-Za-z0-9-]*\s*>|<!--.*?-->",
    re.S,
)
# A complete tag alone on its line: an HTML block of type 7, which cannot interrupt a paragraph.
HTML_BLOCK_GENERIC_RE = re.compile(
    rf"^ {{0,3}}(?:<[A-Za-z][A-Za-z0-9-]*(?:{_TAG_ATTRIBUTE})*\s*/?>"
    rf"|</[A-Za-z][A-Za-z0-9-]*\s*>)\s*$"
)
# A GitHub footnote definition: `[^label]:` with a label free of whitespace and brackets.
# Group 1 is the label.
FOOTNOTE_DEFINITION_RE = re.compile(r"^ {0,3}\[\^([^\s\[\]]+)\]:")
# A split point between two sentences, not a match on a sentence itself: matching the
# boundary and splitting on it is linear in the length of the description, where the old
# `.*?` lazy match tried every starting position in turn and rescanned to the end of the
# text each time it found no terminator to stop at — quadratic on a long description with
# none. The negative lookbehinds keep "e.g.", "i.e." and "etc." from reading as a
# sentence end — without them, "fix the workload, e.g. a slow query." split after
# "e.g." itself, which is not a sentence boundary a reader would recognise as one.
SENTENCE_RE = re.compile(r"(?<=[.!?])(?<!e\.g\.)(?<!i\.e\.)(?<!etc\.)\s+")
# Several descriptions in this repository state when a skill applies in a sentence that
# comes after a first sentence summarising the procedure instead — "Use when someone
# says...", further in, rather than at the start. Preferring the earliest such sentence,
# when one exists, over whichever happens to come first is what keeps the router line
# naming a situation rather than a summary. Descriptions here phrase that sentence
# several ways — "Use when", "Use this when", "Use whenever", "Use this skill whenever",
# "Use for", "Use this skill for", "Use it when" — so every "use ... when/whenever/for"
# shape is covered alongside the standalone "Trigger" some descriptions add later for a
# casual phrasing.
USE_WHEN_RE = re.compile(
    r"^(use (?:this skill |this |it )?(?:when|whenever|for)\b|trigger\b)", re.IGNORECASE
)

# A router line has room for one sentence, not the full description a plugin's own
# listing carries. This is a sane cap rather than a measured one: at 100 characters the
# combined router for this repository's own eight plugins already sits well into
# ROUTER_BUDGET_BYTES below, and the budget is meant to bite as the catalogue grows
# rather than to sit unused. If growth reaches the budget, first remove duplicated
# router markup or reconsider its structure while preserving descriptions and triggers.
ROUTER_USE_WHEN_CAP = 100

# Codex's default project-doc budget is 32 KiB (openai/codex, codex-rs/config/src/
# config_toml.rs: DEFAULT_PROJECT_DOC_MAX_BYTES = 32 * 1024), and codex-rs/core/src/
# agents_md.rs truncates AGENTS.md past that budget with only a tracing::warn! log line —
# nothing the session itself is ever told. Half of Codex's default is the ceiling here so
# a repository's own AGENTS.md content still has room to sit alongside the router rather
# than the router claiming the whole budget for itself.
ROUTER_BUDGET_BYTES = 16 * 1024

# Kept identical across router.md and every router-<plugin>.md: whichever one a reader
# pastes into AGENTS.md, the text still reads true on its own, without the rest of the
# export sitting alongside it to explain the other file.
ROUTER_PREAMBLE = (
    "Each line below names a skill and the situation it applies to. When a line matches "
    "the task at hand, open the `skills/<name>.md` file it names rather than loading "
    "every skill inline; otherwise skip it. In the portable export, router.md holds "
    "these lines for every plugin and router-<plugin>.md holds one plugin's."
)


def _pointer(match: re.Match[str]) -> str:
    """The path a `BUNDLED_RE` match names, normalised to how it appears on disk.

    Unlike the old local regex, `BUNDLED_PATH_RE` has no capturing group excluding a
    leading `./`, so a mention written `./references/x.md` and one written
    `references/x.md` would otherwise become two different dictionary keys for the same
    file — one resolved by the directory walk, the other never matching it, and the
    file inlined or left dangling depending on which form the prose happened to use.

    No trailing-punctuation stripping happens here: `BUNDLED_PATH_RE`'s character class
    cannot end a match on a `.`, `,`, `;` or `:`, so a match is never left holding one —
    `references/x.md.` and `references/x.md,` both already match as `references/x.md`.
    """
    return match.group(0).removeprefix("./")


def demote(text: str, levels: int) -> str:
    """Push every heading down ``levels``, leaving fenced code alone.

    A `#` at the start of a line inside a shell block is a comment, not a heading, and
    rewriting it would corrupt a command the reader is meant to run.
    """
    out: list[str] = []
    for line, fenced in zip(text.split("\n"), fence_spans(text), strict=True):
        match = None if fenced else ATX_RE.match(line)
        if match is None:
            out.append(line)
            continue
        hashes = "#" * min(6, len(match.group(1)) + levels)
        out.append(hashes + match.group(2) + line[match.end() :])
    return "\n".join(out)


def title_of(text: str, fallback: str) -> str:
    """A bundled file's own H1, or a title made from its filename."""
    for line, fenced in zip(text.split("\n"), fence_spans(text), strict=True):
        if not fenced and line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").capitalize()


def strip_frontmatter(text: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text.strip()
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def fence_spans(text: str) -> list[bool]:
    """One flag per line: True when the line is inside a fenced or indented code block.

    A path inside a fence is part of a command or a worked example. Rewriting it to
    "the … section below" turns a runnable line into prose — `git bisect run` needs a
    path, and the inlined section is what tells the reader which file to create. An
    indented code block is the same thing without the markers: four spaces past the
    enclosing list item's content, not continuing a paragraph. Wherever list nesting makes
    that unclear the line is taken as prose, which can only fail an export loudly.
    """
    flags: list[bool] = []
    opening: str | None = None
    depth = 0
    indent = 0
    in_paragraph = False
    list_indent = 0
    after_blank = True
    spaces = 0
    for line in text.split("\n"):
        prefix = CONTAINER_PREFIX_RE.match(line)
        content = line[prefix.end() :]
        quotes = prefix.group().count(">")
        if opening is not None and (
            # A fence inside a blockquote ends with the quote, and one inside a list item
            # with the item, closing marker or not.
            quotes < depth or (indent and line.strip() and len(line) - len(line.lstrip()) < indent)
        ):
            opening = None
        if opening is None:
            rest = line[QUOTE_PREFIX_RE.match(line).end() :]
            spaces = len(rest) - len(rest.lstrip(" "))
            if not rest.strip():
                in_paragraph = False
                after_blank = True
                flags.append(False)
                continue
            marker = ITEM_RE.match(rest) if spaces < list_indent + 4 else None
            if spaces >= list_indent + 4 and not in_paragraph and marker is None:
                flags.append(True)
                continue
            if marker is not None:
                gap = len(marker.group(3) or " ")
                list_indent = marker.end(2) + (gap if gap <= 4 else 1)
            elif after_blank and spaces == 0:
                list_indent = 0
            after_blank = False
        fence = FENCE_RE.match(content)
        # Four spaces past the container make text, not a fence; this is only reachable as
        # the continuation of a paragraph, since otherwise the line was code above.
        if fence is not None and opening is None and spaces >= list_indent + 4:
            fence = None
        # A backtick fence's info string may not contain a backtick: that line is code.
        if (
            fence is not None
            and opening is None
            and fence.group(1)[0] == "`"
            and "`" in content[fence.end() :]
        ):
            fence = None
        if fence is not None:
            marker_text = fence.group(1)
            if opening is None:
                opening = marker_text
                depth = quotes
                if prefix.group("item") and not quotes:
                    indent = len(prefix.group())
                elif list_indent and spaces >= list_indent and not quotes:
                    indent = list_indent  # a continuation line of the item above
                else:
                    indent = 0
                in_paragraph = False
                flags.append(True)
                continue
            # Inside a fence every line is content, so a quoted or bulleted fence marker
            # belongs to the example; only a line in the opener's own container closes it.
            if (
                marker_text[0] == opening[0]
                and len(marker_text) >= len(opening)
                and not content[fence.end() :].strip()
                and quotes == depth
                and prefix.group("item") is None
            ):
                opening = None
            flags.append(True)
            continue
        if opening is None:
            in_paragraph = ATX_RE.match(content) is None
        flags.append(opening is not None)
    return flags


def language_of(relative: str) -> str:
    """The fence language for a shipped script, or none when the extension is unknown."""
    return SCRIPT_LANGUAGES.get(Path(relative).suffix, "")


def asset_language_of(relative: str) -> str:
    """The fence language for a shipped asset, by extension, falling back to `text`.

    A script left unfenced when its extension is unknown is a judgement call an author
    can override by naming the extension in `SCRIPT_LANGUAGES`. An asset has no such
    author in the loop — it is whatever the reader's own project needs it to be — so it
    always gets a language, and `text` is the honest one when the extension names
    nothing more specific.
    """
    return ASSET_LANGUAGES.get(Path(relative).suffix, "text")


def drop_title(text: str) -> str:
    """A reference file's own H1, removed: the section heading already carries it, and
    keeping both renders as a title followed immediately by the same title again."""
    stripped = strip_frontmatter(text)
    if stripped.startswith("# "):
        return stripped.split("\n", 1)[1].lstrip("\n") if "\n" in stripped else ""
    return stripped


# The attribution MIT makes a condition of every copy. A flattened skill is the copy
# most likely to leave this repository — pasted into a project in another assistant, or
# a single file forwarded on — and until this line existed it left with no notice at
# all. It sits at the foot of every exported file, below the reference material, so a
# reader who scrolls to the end finds where the text came from and what they may do
# with it. MIT's actual condition is that the copyright notice and the licence text
# travel with the copy, not merely a line saying where it came from, so this names the
# copyright holder in full and points at the LICENSE this export ships alongside it
# rather than asking the reader to keep a sentence.
NOTICE = (
    "---\n"
    "Copyright (c) 2026 Serhii Zolotov (GitHub: greenblacked), "
    "https://github.com/greenblacked/AI. Licensed under the MIT License: the full text "
    "ships as LICENSE with this export and is at "
    "https://github.com/greenblacked/AI/blob/main/LICENSE. Keep the copyright notice "
    "and the licence with any copy."
)


def source_slug(heading: str) -> str:
    """GitHub source aliases: formatting/punctuation removed, spaces become hyphens.

    See GitHub basic-writing-and-formatting-syntax, section-links. Duplicate aliases
    are allocated across each source, including naturally suffixed headings.
    """

    # Only raw HTML tags vanish from a rendered heading. An autolink such as
    # `<https://example.com>` shows its address and a code span shows its angle brackets,
    # so a blanket `<...>` removal dropped text GitHub keeps and moved the alias. Entities
    # are decoded the same way: `&copy;` is a character in prose and literal text in code.
    def visible(text: str) -> str:
        return html.unescape(HTML_TAG_RE.sub("", text))

    pieces, last = [], 0
    for begin, end in closed_code_spans(heading):
        pieces.append(visible(heading[last:begin]) + heading[begin:end])
        last = end
    heading = ("".join(pieces) + visible(heading[last:])).lower().strip()
    return "".join(
        "-" if c.isspace() else c
        for c in heading
        if c.isspace() or c in "-_" or unicodedata.category(c)[0] in "LN"
    )


# The `unmatched-code-delimiter` reviewer benchmark patch carries three lines of context
# after this function, so nothing may be inserted directly below it.
def code_span_end(line: str, begin: int) -> int:
    """Skip closed code only; a closing delimiter must have the same run length."""
    run = len(line[begin:]) - len(line[begin:].lstrip("`"))
    for match in re.finditer(r"`+", line[begin + run :]):
        if len(match.group()) == run:
            return begin + run + match.end()
    return begin + run


def heading_display(heading: str, bindings: dict[str, str]) -> str:
    """Keep display labels from inline links and bound source references."""
    inline = {begin: finish for _, _, begin, finish in destination_spans(heading)}
    pieces, last, index = [], 0, 0
    while index < len(heading):
        if heading[index] == "\\":
            index += 2
            continue
        if heading[index] == "`":
            index = code_span_end(heading, index)
            continue
        if heading[index] != "[":
            index += 1
            continue
        end = bracket_end(heading, index)
        if end is None:
            break
        label = heading[index + 1 : end - 1]
        finish = end
        key = reference_key(label)
        if heading[end : end + 1] == "[":
            finish = bracket_end(heading, end)
            if finish is None:
                break
            key = reference_key(heading[end + 1 : finish - 1] or label)
        elif heading[end : end + 1] == "(":
            finish = inline.get(index)
            if finish is None:
                index = end
                continue
        if heading[end : end + 1] == "(" or key in bindings:
            start = index - 1 if image_marker(heading, index) else index
            pieces.append(heading[last:start] + heading_display(label, bindings))
            last = finish
        index = finish
    return "".join(pieces) + heading[last:]


def closed_code_spans(line: str) -> list[tuple[int, int]]:
    """Start and end of each closed inline code span, found the way the scanners above do.

    An escaped backtick opens nothing, and a span closes only on a run of its own length,
    so a shorter run inside it is content. An unclosed run is stepped over, not a span.
    """
    spans, index = [], 0
    while index < len(line):
        if line[index] == "\\":
            index += 2
        elif line[index] == "`":
            run = len(line[index:]) - len(line[index:].lstrip("`"))
            end = code_span_end(line, index)
            if end > index + run:
                spans.append((index, end))
            index = end
        else:
            index += 1
    return spans


def without_code_spans(line: str) -> str:
    """``line`` with each closed inline code span blanked; an unclosed backtick stays.

    A tag shown as an example inside code is inert text, so scanning raw HTML must not see
    it. Blanking to a space rather than deleting keeps text on either side from joining.
    """
    pieces, last, index = [], 0, 0
    while index < len(line):
        if line[index] == "\\":
            index += 2
        elif line[index] == "`":
            run = len(line[index:]) - len(line[index:].lstrip("`"))
            end = code_span_end(line, index)
            if end > index + run:  # closed; an unclosed run is stepped over, not consumed
                pieces.append(line[last:index] + " ")
                last = end
            index = end
        else:
            index += 1
    return "".join(pieces) + line[last:]


def has_custom_anchor(text: str) -> bool:
    """True when ``text`` carries a raw HTML tag with an `id` or `name` attribute.

    The text may span lines, since a tag can: scan it whole rather than line by line.
    Quoted values are blanked first so `title="name=x"` is not an attribute, and the
    attribute name has to follow whitespace, so `data-name` is not `name`. Closing tags
    and comments carry no attributes. The caller blanks code, which is inert.
    """
    for tag in HTML_TAG_RE.finditer(text):
        text = tag.group()
        if text.startswith(("</", "<!--")):
            continue
        if re.search(
            r"(?<![\w:.-])(?:id|name)\s*=", re.sub(r"\"[^\"]*\"|'[^']*'", '""', text), re.I
        ):
            return True
    return False


def block_layout(block: list[str], starts: list[int]) -> tuple[list[int], list[int], list[str]]:
    """Per line: where its paragraph ends, where its container ends, and its text.

    Both ends are offsets. A code span or an inline comment may not cross the paragraph's,
    and an HTML comment block runs no further than the container (blockquote or list
    item) it opened in. A paragraph ends at a blank line, a change of blockquote depth, a
    heading, a list item, a thematic break or setext underline, or the start of an HTML
    block of types 1-6, which is what CommonMark lets interrupt one. The text is the line
    without its container prefix.
    """
    prefixes = [CONTAINER_PREFIX_RE.match(line) for line in block]
    bodies = [line[prefix.end() :] for line, prefix in zip(block, prefixes, strict=True)]
    depths = [prefix.group().count(">") for prefix in prefixes]
    paragraph = [0] * len(block)
    for index in range(len(block) - 1, -1, -1):
        following = index + 1
        continues = (
            following < len(block)
            and bodies[index].strip()
            and ATX_RE.match(bodies[index]) is None
            and bodies[following].strip()
            and depths[following] == depths[index]
            and ATX_RE.match(bodies[following]) is None
            and prefixes[following].group("item") is None
            and BLOCK_START_RE.match(bodies[following]) is None
        )
        paragraph[index] = paragraph[following] if continues else starts[index] + len(block[index])
    container = []
    for index, prefix in enumerate(prefixes):
        rest = block[index][QUOTE_PREFIX_RE.match(block[index]).end() :]
        # An item line ends with its item; any other indented line is taken to sit in one.
        indent = (
            len(prefix.group())
            if prefix.group("item") and not depths[index]
            else len(rest) - len(rest.lstrip(" "))
        )
        last = index
        while (
            last + 1 < len(block)
            and depths[last + 1] >= depths[index]
            and (
                not indent
                or not block[last + 1].strip()
                or len(block[last + 1]) - len(block[last + 1].lstrip()) >= indent
            )
        ):
            last += 1
        container.append(starts[last] + len(block[last]))
    return paragraph, container, bodies


def html_block_end(
    block: list[str],
    bodies: list[str],
    starts: list[int],
    container: list[int],
    index: int,
    kind: str | None,
) -> int:
    """Offset where the HTML block of types 1-7 that begins on line ``index`` ends.

    ``kind`` names the tag or declaration of types 1-5, which run to the line holding their
    terminator. Types 6 and 7 (``None``) run to the next blank line. Any of them stops at
    the end of its container if that comes first.
    """
    last = index
    if kind is not None:
        kind = kind.lower()
        if kind in {"script", "pre", "style", "textarea"}:
            ends = re.compile(rf"</{kind}>", re.I)
        else:
            ends = re.compile(r"\?>" if kind == "?" else r"\]\]>" if kind.startswith("![") else ">")
        for following in range(index, len(block)):
            if starts[following] > container[index]:
                break
            last = following
            if ends.search(bodies[following]):
                break
    else:
        while (
            last + 1 < len(block)
            and bodies[last + 1].strip()
            and starts[last + 1] <= container[index]
        ):
            last += 1
    return starts[last] + len(block[last])


def inert_ranges(
    text: str, fenced: list[bool], *, markup: bool = True
) -> list[list[tuple[int, int]]]:
    """Per line, the character ranges that are raw text, not Markdown to rewrite.

    Two kinds sit outside a fence and inside a line scanner's blind spot: an HTML comment,
    whose contents render as nothing, and the part of a code span that continues past a
    line break. Neither is visible one line at a time, so each is found over a whole run
    of unfenced lines, in a single left-to-right scan. Whichever construct starts first
    wins, as in CommonMark: a backtick inside a comment is comment text, and `<!--` inside
    a code span is code. A code span or inline comment closes only within its paragraph; a
    comment that begins its line is an HTML block and runs to its `-->` or the end of its
    container. Not handled: a fence marker inside a comment or another HTML block, which
    `fence_spans` reads as a fence; an indented fence marker, likewise; a list item inside a
    blockquote, whose fence outlives the item; a comment opening inside an HTML block
    already open, or after a blank line at four spaces of indent, which is code; a link
    whose label contains a comment, which is rewritten in pieces; and a table row, whose
    cells GitHub parses one at a time.
    """
    lines = text.split("\n")
    ranges: list[list[tuple[int, int]]] = [[] for _ in lines]
    number = 0
    while number < len(lines):
        if fenced[number]:
            number += 1
            continue
        first = number
        while number < len(lines) and not fenced[number]:
            number += 1
        block = lines[first:number]
        starts, offset = [], 0
        for line in block:
            starts.append(offset)
            offset += len(line) + 1
        paragraph, container, bodies = block_layout(block, starts)
        joined = "\n".join(block)
        found: list[tuple[int, int]] = []
        position = raw_until = 0
        while position < len(joined):
            char = joined[position]
            line_index = bisect.bisect_right(starts, position) - 1

            if char == "\\":
                position += 2
            elif joined.startswith("<!--", position):
                column = position - starts[line_index] - len(block[line_index])
                column += len(bodies[line_index])
                block_start = column <= 3 and not bodies[line_index][:column].strip()
                if position < raw_until:
                    # Still inside the HTML block that the previous comment closed on this
                    # line: a comment here is raw HTML and cannot run onto later lines.
                    close = joined.find("-->", position + 4, raw_until)
                    if close < 0:
                        position += 4
                        continue
                    found.append((position, close + 3))
                    position = close + 3
                    continue
                limit = container[line_index] if block_start else paragraph[line_index]
                # Only a comment that begins its line is an HTML block, whose `-->` may
                # overlap its own `<!--` and which hides the rest of its container when
                # never closed; elsewhere it is inline and an unclosed one is literal.
                close = joined.find("-->", position + (2 if block_start else 4), limit)
                if close < 0 and not block_start:
                    position += 4
                    continue
                end = limit if close < 0 else close + 3
                found.append((position, end))
                if block_start and close >= 0:
                    # The rest of the line holding `-->` is part of the HTML block, so no
                    # code span starts there; it is not marked inert, since a tag in it is
                    # still real HTML.
                    closing = bisect.bisect_right(starts, close) - 1
                    raw_until = min(limit, starts[closing] + len(block[closing]))
                position = end
            elif char == "<" and markup:
                column = position - starts[line_index] - len(block[line_index])
                column += len(bodies[line_index])
                at_start = column <= 3 and not bodies[line_index][:column].strip()
                opener = (
                    HTML_BLOCK_START_RE.match(bodies[line_index][column:]) if at_start else None
                )
                kind = (opener.group(1) or opener.group(2)) if opener is not None else None
                # A complete tag alone on its line opens a block only where no paragraph
                # is running to be interrupted.
                fresh = line_index == 0 or paragraph[line_index - 1] == (
                    starts[line_index - 1] + len(block[line_index - 1])
                )
                generic = at_start and fresh and HTML_BLOCK_GENERIC_RE.match(bodies[line_index])
                if opener is not None or generic:
                    end = html_block_end(block, bodies, starts, container, line_index, kind)
                    found.append((position, end))
                    position = end
                    continue
                tag = HTML_TAG_RE.match(joined, position, paragraph[line_index])
                if tag is not None:
                    found.append((position, tag.end()))
                    position = tag.end()
                else:
                    position += 1
            elif char == "`" and position >= raw_until:
                run = len(joined[position:]) - len(joined[position:].lstrip("`"))
                end = position + run
                for match in re.finditer(r"`+", joined[position + run : paragraph[line_index]]):
                    if len(match.group()) == run:
                        end = position + run + match.end()
                        if "\n" in joined[position:end]:
                            found.append((position, end))
                        break
                position = end
            else:
                position += 1
        for begin, end in found:
            for index, line in enumerate(block):
                low, high = starts[index], starts[index] + len(line)
                if begin < high and end > low:
                    ranges[first + index].append((max(begin, low) - low, min(end, high) - low))
    return [sorted(set(found)) for found in ranges]


def blank_ranges(line: str, ranges: list[tuple[int, int]]) -> str:
    """``line`` with each range replaced by spaces, so offsets into it stay valid."""
    for begin, end in ranges:
        line = line[:begin] + " " * (end - begin) + line[end:]
    return line


def destination_spans(line: str) -> list[tuple[int, int, int, int]]:
    """Destination and protected syntax spans for inline links and definitions.

    Supports nested/escaped labels and parentheses, angle destinations, optional
    titles, and one-line reference definitions. Inline code is protected separately.
    This intentionally does not claim to be a complete CommonMark parser.
    """
    spans = []
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "`":
            i = code_span_end(line, i)
            continue
        if line[i] != "[":
            i += 1
            continue
        begin = i
        depth = 1
        i += 1
        while i < len(line) and depth:
            if line[i] == "\\":
                i += 2
                continue
            depth += (line[i] == "[") - (line[i] == "]")
            i += 1
        if depth or i >= len(line):
            continue
        definition = line[i] == ":" and not line[:begin].strip()
        if line[i] != "(" and not definition:
            if line[i] == "[":
                closing = line.find("]", i + 1)
                if closing >= 0:
                    spans.append((i, i, begin, closing + 1))
                    i = closing + 1
            continue
        i += 1
        while i < len(line) and line[i].isspace():
            i += 1
        angle = i < len(line) and line[i] == "<"
        i += angle
        dest_start = i
        depth = 0
        while i < len(line):
            c = line[i]
            if c == "\\":
                i += 2
                continue
            if angle:
                if c == ">":
                    break
            else:
                if c.isspace() or (c == ")" and depth == 0):
                    break
                depth += (c == "(") - (c == ")")
            i += 1
        dest_end = i
        if angle:
            i += 1
        if definition:
            spans.append((dest_start, dest_end, begin, len(line)))
            break
        # The optional title may itself contain a parenthesis.
        quote = None
        while i < len(line):
            c = line[i]
            if c == "\\":
                i += 2
                continue
            if quote:
                if c == quote:
                    quote = None
            elif c in "\"'":
                quote = c
            elif c == ")":
                spans.append((dest_start, dest_end, begin, i + 1))
                i += 1
                break
            i += 1
    return spans


def image_marker(line: str, begin: int) -> bool:
    """An image opener has an exclamation mark with an even escape prefix."""
    if line[begin - 1 : begin] != "!":
        return False
    prefix = line[: begin - 1]
    return (len(prefix) - len(prefix.rstrip("\\"))) % 2 == 0


def bracket_end(line: str, begin: int) -> int | None:
    """End of an escape-aware bracket label, including nested display brackets."""
    depth, index = 1, begin + 1
    while index < len(line):
        if line[index] == "\\":
            index += 2
            continue
        depth += (line[index] == "[") - (line[index] == "]")
        index += 1
        if depth == 0:
            return index
    return None


def reference_key(label: str) -> str:
    """CommonMark reference matching uses casefold and collapsed label whitespace.

    Backslash spelling is retained, independently of rendered display text. See
    spec.commonmark.org/0.31.2/#reference-links (including first-definition wins).
    """
    return " ".join(label.split()).casefold()


def definition_label(line: str) -> tuple[int, int] | None:
    # A footnote definition shares the `[label]:` shape but is not a link reference
    # definition: renaming it into one turns the footnote into a plain link.
    if FOOTNOTE_DEFINITION_RE.match(line):
        return None
    match = re.match(r"^ {0,3}\[", line)
    if not match:
        return None
    begin = match.end() - 1
    end = bracket_end(line, begin)
    if end is not None and line[end : end + 1] == ":":
        return begin, end
    return None


def render_skill(directory: Path) -> tuple[str, str, str, list[str]]:
    """Flatten a safe inventory, preserving original source-relative link identity.

    One-line inline links and reference definitions/uses are supported. Multiline
    reference bindings fail visibly instead of leaking source-local identifiers.
    ATX headings outside fences receive explicit anchors; custom HTML anchors are
    rejected visibly (rather than silently leaking duplicate IDs into a bundle).
    Bare root-prefixed prose pointers retain their historical section descriptions.
    """
    root = directory.resolve()
    if not (directory / "SKILL.md").resolve().is_relative_to(root):
        raise OSError("SKILL.md: symlink escapes skill root")
    source = (directory / "SKILL.md").read_text(encoding="utf-8")
    values = parse(source).values
    name = values.get("name", directory.name)
    description = " ".join((values.get("description") or "").split())
    sources = {"SKILL.md": strip_frontmatter(source)}
    unresolved: list[str] = []
    order = []
    for sub in ("references", "assets", "scripts"):
        for path in sorted((directory / sub).rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(directory).as_posix()
            if not path.resolve().is_relative_to(root):
                unresolved.append(f"{relative}: symlink escapes skill root")
                continue
            try:
                text = path.read_text(encoding="utf-8")
                # Reference metadata is not content: left in, it is emitted as YAML and the
                # H1 behind it is not seen as the first line, so the title is repeated.
                sources[relative] = (
                    strip_frontmatter(text) if relative.startswith("references/") else text
                )
                order.append(relative)
            except UnicodeDecodeError:
                continue
    # Preserve first-mention section ordering without reading destination-selected files.
    named = []
    for line, fenced in zip(
        sources["SKILL.md"].split("\n"), fence_spans(sources["SKILL.md"]), strict=True
    ):
        if not fenced:
            for match in BUNDLED_RE.finditer(line):
                candidate = _pointer(match)
                if "." in candidate.rsplit("/", 1)[-1] and candidate not in named:
                    named.append(candidate)
    order.sort(
        key=lambda relative: (named.index(relative) if relative in named else len(named), relative)
    )
    titles = {
        relative: title_of(text, Path(relative).stem)
        if relative.startswith("references/")
        else relative
        for relative, text in sources.items()
        if relative != "SKILL.md"
    }
    # Hex encodings and separators are injective, independent of output heading levels.
    prefix = "portable-" + directory.parent.parent.name.encode().hex() + "-" + name.encode().hex()
    roots = {relative: prefix + "-" + relative.encode().hex() + "-root" for relative in sources}
    # Definitions are source-local in Markdown. Flattening also changes this scope,
    # so destination anchors alone cannot preserve reference-style link binding.
    reference_ids: dict[str, dict[str, str]] = {}
    reference_destinations: dict[str, dict[str, str]] = {}
    identifier_owners: dict[str, tuple[str, str]] = {}
    # Footnote labels are document-global, so two inlined files that each define
    # `[^note]` would collide in the flattened document: GitHub keeps the first
    # definition and drops the second, changing what a reader sees. Namespacing them per
    # source file keeps both, and a use whose own file defines no such footnote is never
    # rewritten, so it cannot be captured by another file's definition.
    footnote_ids: dict[str, dict[str, str]] = {}
    for relative, text in sources.items():
        reference_ids[relative] = {}
        reference_destinations[relative] = {}
        footnote_ids[relative] = {}
        if relative != "SKILL.md" and not relative.startswith("references/"):
            continue
        fenced_lines = fence_spans(text)
        inert = inert_ranges(text, fenced_lines)
        for number, (line, fenced) in enumerate(zip(text.split("\n"), fenced_lines, strict=True)):
            # A definition inside a comment or a multiline code span defines nothing, so
            # collecting it would scope a use that the copied definition then fails to match.
            if fenced or inert[number] and not blank_ranges(line, inert[number]).strip():
                continue
            line = blank_ranges(line, inert[number])
            footnote = FOOTNOTE_DEFINITION_RE.match(line)
            if footnote is not None:
                key = reference_key(footnote.group(1))
                identity = roots[relative] + "-footnote-" + key.encode().hex()
                scoped = "portable-footnote-" + hashlib.sha256(identity.encode()).hexdigest()
                owner = identifier_owners.setdefault(scoped, (relative, "^" + key))
                if owner != (relative, "^" + key):
                    raise OSError("footnote identifier namespace collision")
                footnote_ids[relative].setdefault(key, scoped)
                continue
            definition = definition_label(line)
            if definition is None:
                continue
            begin, end = definition
            key = reference_key(line[begin + 1 : end - 1])
            if not key or not line[end + 1 :].strip():
                unresolved.append(f"{relative}: unsupported empty/multiline reference definition")
                continue
            # Keep emitted labels below CommonMark's 999-character limit even when
            # the original source path and label are long; assert digest ownership.
            identity = roots[relative] + "-" + key.encode().hex()
            scoped = "portable-reference-" + hashlib.sha256(identity.encode()).hexdigest()
            owner = identifier_owners.setdefault(scoped, (relative, key))
            if owner != (relative, key):
                raise OSError("reference identifier namespace collision")
            reference_ids[relative].setdefault(key, scoped)
            spans = destination_spans(line)
            if spans:
                start, finish, _, _ = spans[0]
                reference_destinations[relative].setdefault(key, line[start:finish])

    aliases: dict[str, dict[str, str]] = {}
    heading_ids: dict[str, dict[int, str]] = {}
    for relative, text in sources.items():
        aliases[relative] = {}
        heading_ids[relative] = {}
        if relative != "SKILL.md" and not relative.startswith("references/"):
            continue
        used: set[str] = set()
        fenced_lines = fence_spans(text)
        inert = inert_ranges(text, fenced_lines, markup=False)
        scrubbed = []
        source_lines = text.split("\n")
        paragraph_start: int | None = None
        for index, (line, fenced) in enumerate(zip(source_lines, fenced_lines, strict=True)):
            if fenced:
                scrubbed.append("")
                paragraph_start = None
                continue
            # A comment or the tail of a multiline code span is not a heading or an anchor.
            visible = blank_ranges(line, inert[index])
            scrubbed.append(without_code_spans(visible))
            # A heading may sit in a blockquote or a list item, or be indented up to three
            # spaces; four spaces make it text.
            lead = CONTAINER_PREFIX_RE.match(visible).end()
            match = ATX_RE.match(visible[lead:])
            quoted = ">" in visible[:lead]
            heading: str | None = None
            if match and (lead < 4 or quoted):
                heading = re.sub(r"\s+#+\s*$", "", line[lead + match.end() :])
                at = index
                paragraph_start = None
            elif not visible.strip():
                paragraph_start = None
                continue
            elif SETEXT_UNDERLINE_RE.match(visible) and paragraph_start is not None:
                # A setext heading is the paragraph above its underline. Only a plain
                # top-level paragraph counts: under a list item or quote the underline is a
                # thematic break or a continuation.
                heading = " ".join(part.strip() for part in source_lines[paragraph_start:index])
                at = paragraph_start
                paragraph_start = None
            elif (
                (container := CONTAINER_PREFIX_RE.match(visible)).group("item")
                or ">" in container.group()
                or visible.startswith("    ")
            ):
                paragraph_start = None
                continue
            else:
                if paragraph_start is None:
                    paragraph_start = index
                continue
            slug = source_slug(heading_display(heading, reference_destinations[relative]))
            alias, suffix = slug, 0
            while alias in used:
                suffix += 1
                alias = f"{slug}-{suffix}"
            used.add(alias)
            anchor = roots[relative].removesuffix("root") + f"heading-{at}"
            aliases[relative][alias] = anchor
            heading_ids[relative][at] = anchor
        if has_custom_anchor("\n".join(scrubbed)):
            unresolved.append(f"{relative}: unsupported custom HTML anchor")

    for relative, ids in reference_ids.items():
        if relative != "SKILL.md" and not relative.startswith("references/"):
            continue
        # Multi-line labels are legal Markdown, but are outside this line scanner's
        # supported syntax. Detect actual known bindings rather than arbitrary prose.
        visible = "\n".join(
            "" if fenced else re.sub(r"(`+)[^`]*?\1", "", line)
            for line, fenced in zip(
                sources[relative].split("\n"), fence_spans(sources[relative]), strict=True
            )
        )
        for match in re.finditer(r"\[([^\[\]]+)\](?:\[([^\[\]]*)\])?", visible):
            display, explicit = match.groups()
            key = reference_key(explicit or display)
            definition = visible[match.end() : match.end() + 1] == ":"
            if "\n" in match.group(0) and (definition or key in ids):
                unresolved.append(f"{relative}: unsupported multiline reference binding")

    def scope_references(line: str, current: str, *, images_only: bool = False) -> str:
        ids = reference_ids[current]
        definition = definition_label(line)
        if definition and not images_only:
            begin, end = definition
            key = reference_key(line[begin + 1 : end - 1])
            if key in ids:
                return line[: begin + 1] + ids[key] + line[end - 1 :]
            return line
        pieces, last, index = [], 0, 0
        while index < len(line):
            if line[index] == "\\":
                index += 2
                continue
            if line[index] == "`":
                index = code_span_end(line, index)
                continue
            if line[index : index + 2] == "[^":
                # Checked before the images-only filter: a footnote use can sit inside a
                # link label, which is scanned in that mode, and must be scoped there too.
                close = bracket_end(line, index)
                # A destination after the bracket makes this a link or image whose visible
                # text starts with `^`, so the link path below handles it instead.
                if close is not None and line[close : close + 1] != "(":
                    scoped = footnote_ids[current].get(reference_key(line[index + 2 : close - 1]))
                    if scoped is not None:
                        pieces.append(line[last:index] + "[^" + scoped + "]")
                        last = index = close
                        continue
            if line[index] != "[" or (images_only and not image_marker(line, index)):
                index += 1
                continue
            begin = index
            end = bracket_end(line, begin)
            if end is None:
                break
            label = line[begin + 1 : end - 1]
            scoped_label = scope_references(label, current, images_only=True)
            if line[end : end + 1] == "(":
                # Images can bind inside a link label; destinations and titles cannot.
                inline = destination_spans(line[begin:])
                index = begin + inline[0][3] if inline and inline[0][2] == 0 else end
                if image_marker(line, begin) and inline and inline[0][2] == 0:
                    start, finish, _, _ = inline[0]
                    resolve(line[begin + start : begin + finish], current, image=True)
                if scoped_label != label:
                    pieces.append(line[last:begin] + "[" + scoped_label + line[end - 1 : index])
                    last = index
                continue
            finish = end
            if line[end : end + 1] == "[":
                reference_end = bracket_end(line, end)
                if reference_end is None:
                    if reference_key(label) in ids:
                        unresolved.append(f"{current}: unsupported incomplete reference use")
                    break
                explicit = line[end + 1 : reference_end - 1]
                key = reference_key(explicit or label)
                # An explicit label that names no reference is not consumed: `[word][^x]`
                # is a bracket pair followed by a footnote use, which is scanned on its own.
                finish = reference_end if key in ids else end
            else:
                key = reference_key(label)
            if key in ids:
                if image_marker(line, begin):
                    destination = reference_destinations[current].get(key)
                    if destination is not None:
                        resolve(destination, current, image=True)
                pieces.append(line[last:begin])
                pieces.append("[" + scoped_label + "][" + ids[key] + "]")
                last = finish
            elif scoped_label != label:
                pieces.append(line[last:begin] + "[" + scoped_label + line[end - 1 : finish])
                last = finish
            index = finish
        pieces.append(line[last:])
        return "".join(pieces)

    def resolve(destination: str, current: str, *, image: bool = False) -> str | None:
        decoded = unquote(re.sub(r"\\([!\"#$%&'()*+,./:;<=>?@\[\]\^_`{|}~-])", r"\1", destination))
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", decoded) or decoded.startswith("//"):
            return None
        if image:
            # Flattened section anchors cannot render source-relative image assets.
            unresolved.append(f"{current}: unsupported local image source: {destination}")
            return None
        path, separator, fragment = decoded.partition("#")
        candidate = (
            posixpath.normpath(posixpath.join(posixpath.dirname(current), path))
            if path
            else current
        )
        # Historical root-prefixed references in reference prose are allowed only when
        # the actual relative target is absent and the exact inventory key exists.
        if (
            candidate not in sources
            and path.removeprefix("./") in sources
            and path.removeprefix("./").startswith(("references/", "assets/", "scripts/"))
        ):
            candidate = path.removeprefix("./")
        anchor = roots.get(candidate)
        if separator and fragment:
            anchor = aliases.get(candidate, {}).get(fragment)
        if candidate.startswith("../") or candidate.startswith("/") or anchor is None:
            unresolved.append(f"{current}: {destination}")
            return None
        return "#" + anchor

    def bare(text: str, current: str) -> str:
        def one(match: re.Match[str]) -> str:
            candidate = _pointer(match)
            title = prepared_titles.get(candidate)
            if (
                not title
                and current == "SKILL.md"
                and "." in candidate.rsplit("/", 1)[-1]
                and candidate not in unresolved
            ):
                unresolved.append(candidate)
            return f'the "{title}" section below' if title else match.group(0)

        # Consume fragments along with bare pointers, and verify their original alias.
        pattern = re.compile(BUNDLED_RE.pattern + r"(?:#[\w%.-]+)?")

        def with_fragment(match: re.Match[str]) -> str:
            path, separator, fragment = match.group(0).partition("#")
            if separator:
                target = resolve(path + "#" + fragment, current)
                title = prepared_titles.get(path.removeprefix("./"))
                return f'the "{title}" section below' if target and title else match.group(0)
            return one(match)

        text = pattern.sub(with_fragment, text)
        return re.sub(r'`the "([^"]+)" section below`', r'the "\1" section below', text)

    def prose_pointers(text: str, current: str) -> str:
        # Delimiter-aware, like every other scanner here: a regex pairing any two backtick
        # runs took the inner single run of a double-backtick span for a whole span and
        # rewrote the path inside the example it was meant to leave alone.
        pieces, last = [], 0
        for begin, end in closed_code_spans(text):
            pieces.append(bare(text[last:begin], current))
            span = text[begin:end]
            pieces.append(span if "[" in span else bare(span, current))
            last = end
        pieces.append(bare(text[last:], current))
        return "".join(pieces)

    def rewrite_prose(line: str, current: str, expand_bare: bool, *, at_start: bool = True) -> str:
        # A footnote definition's label is scoped and its text is prose like any other,
        # so links and pointers inside it still resolve; the label itself must not
        # reach `destination_spans`, which would read the text as a link destination.
        label = ""
        footnote = FOOTNOTE_DEFINITION_RE.match(line) if at_start else None
        # A title such as `[^t]: Title` looks like a definition but was never collected
        # as one, so it has no scoped label; it is then left as ordinary text.
        scoped = footnote_ids[current].get(reference_key(footnote.group(1))) if footnote else None
        if footnote is not None and scoped is not None:
            label = line[: footnote.start(1)] + scoped + "]:"
            line = line[footnote.end() :]
        line = scope_references(line, current)
        spans = destination_spans(line)
        pieces, last = [], 0
        for start, end, begin, finish in spans:
            pieces.append(
                prose_pointers(line[last:begin], current) if expand_bare else line[last:begin]
            )
            replacement = (
                resolve(line[start:end], current, image=image_marker(line, begin))
                if end > start
                else None
            )
            pieces.append(line[begin:start] + (replacement or line[start:end]) + line[end:finish])
            last = finish
        # Protect Markdown examples in inline code while retaining legacy bare paths.
        tail = line[last:]
        pieces.append(prose_pointers(tail, current) if expand_bare else tail)
        return label + "".join(pieces)

    def rewrite(text: str, current: str, *, expand_bare: bool = True) -> str:
        out = []
        fenced_lines = fence_spans(text)
        inert = inert_ranges(text, fenced_lines)
        for number, (line, fenced) in enumerate(zip(text.split("\n"), fenced_lines, strict=True)):
            if fenced:
                out.append(line)
                continue
            # Comments and the part of a code span past a line break are copied verbatim;
            # the prose between them is rewritten on its own.
            pieces, last = [], 0
            for begin, end in inert[number]:
                if begin > last:
                    pieces.append(
                        rewrite_prose(line[last:begin], current, expand_bare, at_start=last == 0)
                    )
                pieces.append(line[begin:end])
                last = end
            if last < len(line) or not pieces:
                pieces.append(rewrite_prose(line[last:], current, expand_bare, at_start=last == 0))
            out.append("".join(pieces))
        return "\n".join(out)

    def prose(relative: str, levels: int) -> tuple[str, str]:
        text = sources[relative]
        lines = text.split("\n")
        title_anchors = f'<a name="{roots[relative]}"></a>'
        if lines and lines[0].startswith("# "):
            if 0 in heading_ids[relative]:
                title_anchors += f'\n<a name="{heading_ids[relative][0]}"></a>'
            lines[0] = ""
        for index, anchor in heading_ids[relative].items():
            if index != 0 or not text.startswith("# "):
                quote = QUOTE_PREFIX_RE.match(lines[index]).group()
                lines[index] = f'{quote}<a name="{anchor}"></a>\n' + lines[index]
        return title_anchors, demote(rewrite("\n".join(lines), relative), levels).strip()

    # Prepare titles in their owning source without recursively expanding filenames.
    prepared_titles = {
        relative: rewrite(title, relative, expand_bare=False)
        if relative.startswith("references/")
        else title
        for relative, title in titles.items()
    }
    skill_title = rewrite(title_of(sources["SKILL.md"], name), "SKILL.md", expand_bare=False)
    root_anchors, body = prose("SKILL.md", 0)
    parts = [
        root_anchors,
        "# " + skill_title,
        "",
        f"**Skill:** `{name}`",
        "",
        f"**Use this when:** {description}",
        "",
        body,
    ]
    sections = []
    for relative in order:
        text = sources[relative]
        if relative.startswith("references/"):
            anchors, content = prose(relative, 3)
            sections.append(f"{anchors}\n### {prepared_titles[relative]}\n\n{content}")
        else:
            language = (
                asset_language_of(relative)
                if relative.startswith("assets/")
                else language_of(relative)
            )
            longest = max((len(m.group(0)) for m in re.finditer(r"`{3,}", text)), default=2)
            fence = "`" * (longest + 1)
            sections.append(
                f'<a name="{roots[relative]}"></a>\n### {titles[relative]}\n\n'
                f"{fence}{language}\n{text.rstrip()}\n{fence}"
            )
    if sections:
        parts += ["", "## Reference material", "", *(section + "\n" for section in sections)]
    parts += ["", NOTICE]
    return name, description, "\n".join(parts).rstrip() + "\n", unresolved


def _trim_to_word_boundary(sentence: str, cap: int) -> str:
    """``sentence``, cut at the last space at or before ``cap`` characters, not mid-word.

    A cut mid-word reads as a typo rather than a truncation — "netcod…" names nothing a
    reader could search for. Falling back to a hard cut only when the leading word is
    itself longer than the cap keeps a single very long token from producing an empty
    line instead of a short, honestly truncated one.
    """
    if len(sentence) <= cap:
        return sentence
    truncated = sentence[:cap]
    boundary = truncated.rfind(" ")
    if boundary <= 0:
        boundary = cap - 1
    return truncated[:boundary].rstrip() + "…"


def first_sentence(description: str, cap: int) -> str:
    """A short line drawn from ``description``, trimmed to ``cap`` characters.

    Prefers the earliest sentence stating when the skill applies — one starting "Use
    when", "Use whenever", "Use for", "Use this skill whenever" or "Trigger", among other
    shapes ``USE_WHEN_RE`` covers — over whichever sentence happens to come first: several
    descriptions in this repository put that sentence after a first one summarising the
    procedure instead, and a router line naming a situation is more useful than one
    naming a summary. Falls back to the first sentence when no such sentence exists.
    """
    text = " ".join(description.split())
    sentences = SENTENCE_RE.split(text) if text else [text]
    sentence = next(
        (candidate for candidate in sentences if USE_WHEN_RE.match(candidate)), sentences[0]
    )
    return _trim_to_word_boundary(sentence, cap)


def render_router(title: str, groups: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """One line per skill: when it applies, drawn from its own description, and the path
    to open when it does.

    This, not a bundle or ``index.md``, is what belongs in ``AGENTS.md``: a terminal
    agent that reads ``AGENTS.md`` in full pays for every byte of it on every turn, so
    the router carries only that line and a pointer, and ``skills/<name>.md`` stays
    something opened on demand rather than something paid for whether or not it fires.

    The title and preamble sit inside an HTML comment, not a heading and a paragraph:
    `cat`ting a router into a repository's own `AGENTS.md` would otherwise inject a
    stray "# Skill router" title and a paragraph that talks about "this file" in a
    document that is no longer this file, into prose that already has its own structure.
    A comment carries the same words for whoever opens the router directly without
    rendering as either.
    """
    lines = ["<!--", title, "", ROUTER_PREAMBLE, "-->", ""]
    for plugin, skills in groups:
        lines += [f"## {plugin}", ""]
        for name, use_when in skills:
            lines.append(f"- [{name}](skills/{name}.md): {use_when}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


HOW_TO_USE = """# Portable skills

Every skill in this library, flattened into files that stand alone. No frontmatter to
interpret, no plugin manifest, no `references/` path to follow — each file carries its
own reference material inline, so it works wherever you can paste or upload text.

`index.md` lists every skill with its full description, for a surface that retrieves from
uploaded files rather than reading one whole document per turn — a ChatGPT Project,
mainly. For a surface that reads one file in full and pays for every byte of it on every
turn, `router.md` is the router instead — one line per skill, drawn from its own
description, naming when it applies and the path to open then — and `router-<plugin>.md`
covers one plugin alone, for a narrower file. See "Codex, Gemini CLI and other terminal
agents" below for why the distinction matters there and not here.

## ChatGPT

**A Project** is the closest fit. Create one, upload the `plugins/*.md` bundles you want
as project files, and put this in the project instructions:

> You have a library of procedures in the project files. Before answering, check whether
> one applies — each begins with "Use this when". If one does, follow it rather than
> improvising, and say which you used. If none applies, answer normally.

**A Custom GPT** works the same way: the bundles go in Knowledge, and the text above goes
in Instructions.

For one skill only, paste `skills/<name>.md` into the conversation and say "follow this".

## Grok

Paste the skill you want into the conversation, or put the instructions text above into
custom instructions with the bundle attached. Grok has no persistent file store in every
surface, so the single-skill files are usually the better unit there. Grok Build itself
documents no size cap on a project instruction file, unlike Codex below.

## Codex, Gemini CLI and other terminal agents

Several of these now load skills natively and fire them on their own, which beats any
file here: the table in the repository README says which, and how to install for each —
<https://github.com/greenblacked/AI#chatgpt-grok-codex-and-everything-else>

For one that does not, most read `AGENTS.md` from the working directory, and what you put
there has to fit inside what that tool actually reads. Codex's default is
`project_doc_max_bytes`, 32 KiB, and past it Codex truncates `AGENTS.md` silently: the cut
is a log line the interactive session never sees, so a file that overflows the budget
reads as complete right up until the missing part turns out to be the part you needed.
Gemini CLI, GitHub Copilot and Mistral Vibe have no documented cap in the sources
checked — that is not the same claim as none existing.

That budget is why `router.md` or `router-<plugin>.md`, not a bundle or `index.md`, is
what belongs in `AGENTS.md`. Paste one in, and copy the `skills/` directory here to sit
next to that `AGENTS.md`: the router's own paths are `skills/<name>.md`, relative to
wherever `AGENTS.md` itself sits, not to here.

```bash
cat router-coding.md >> /path/to/your/repo/AGENTS.md
mkdir -p /path/to/your/repo/skills && cp -r skills/. /path/to/your/repo/skills/
```

A single large skill file is fine to open on demand once a router line matches —
`website-builder.md` alone is about 70 KB and already over Codex's default, which is
exactly why it is opened rather than pasted. Never append a whole bundle (well over a
hundred kilobytes each) or `index.md` (about 80 KB) to `AGENTS.md` directly: both are far
past 32 KiB on their own, and the router exists so you never have to carry either one
there.

## Claude Code

You do not need any of this — install the plugins instead, which gives you automatic
triggering rather than a file the model has to be told to read. See the repository
README.

## Regenerating

```bash
make portable
```

Everything under `dist/` is generated and git-ignored. Do not edit these files; edit the
skill and export again.

## Licence

MIT. Copyright (c) 2026 Serhii Zolotov (GitHub: greenblacked),
https://github.com/greenblacked/AI. The full text is in the `LICENSE` file in this
directory and at <https://github.com/greenblacked/AI/blob/main/LICENSE>; `NOTICE` here
adds statements of fact that do not change its terms. Every skill file ends with a short
copy of the same notice — keep the copyright line and the `LICENSE` file with any copy
you make.
"""


EXPORT_SENTINEL = ".portable-export"
SENTINEL_TEXT = (
    "This directory was produced by scripts/export_portable.py, which checks for this "
    "file before deleting a directory in its own way. Delete it yourself if you no "
    "longer want the directory recognised as a previous export.\n"
)


def _looks_like_a_previous_export(out: Path) -> bool:
    """Whether ``out`` was, as best this script can tell, produced by this script.

    The sentinel is the primary signal: a one-line file whose content never changes, so
    it survives edits to ``HOW_TO_USE`` that would otherwise make every future export
    refuse to overwrite the one before it purely because the prose in its README had
    since been reworded. The README check is kept alongside it for a directory from
    before the sentinel existed.
    """
    if (out / EXPORT_SENTINEL).is_file():
        return True
    marker = out / "README.md"
    return marker.is_file() and marker.read_text(encoding="utf-8") == HOW_TO_USE


def _unsafe_to_remove(root: Path, out: Path) -> str | None:
    """Why ``out`` must not be handed to ``shutil.rmtree``, or ``None`` if it may be.

    ``--out .`` would otherwise delete the working tree: this is called only when ``out``
    already exists, right before it would be replaced, and the caller was never asked to
    confirm anything more specific than a path. Three things make a directory too
    dangerous to remove outright — being the repository, containing it, or being the
    directory a stray argument most plausibly resolves to when nobody meant one at all —
    and a fourth catches everything else: this export writes a recognisable marker on
    every successful run, so a directory that formed some other way is left alone rather
    than guessed at.
    """
    resolved_root = root.resolve()
    resolved_out = out.resolve()
    if resolved_out == Path.home().resolve():
        return "it is the home directory"
    if resolved_out == resolved_root or resolved_out in resolved_root.parents:
        return "it is the repository root or a directory that contains it"
    if not _looks_like_a_previous_export(resolved_out):
        return (
            f"it does not look like a previous export (no {EXPORT_SENTINEL} and no "
            "README.md matching this script's own marker text) — delete the directory "
            "yourself if you are sure"
        )
    return None


def export(root: Path, out: Path, check: bool = False) -> int:
    plugins = find_plugins(root)
    if not plugins:
        print(f"no plugins under {root}", file=sys.stderr)
        return 2

    rendered: dict[str, list[tuple[str, str, str]]] = {}
    failures = 0
    for plugin in plugins:
        for directory in find_skills(plugin / "skills"):
            try:
                name, description, document, unresolved = render_skill(directory)
            except (FrontmatterError, OSError, UnicodeDecodeError) as error:
                print(f"::error::{directory.name}: {error}", file=sys.stderr)
                failures += 1
                continue
            # Nothing may leave here still pointing at a file the reader cannot open.
            # This is the whole reason the export is checked rather than trusted: the
            # validator catches a dangling pointer in the repository, and this catches
            # one reintroduced by flattening.
            for relative in unresolved:
                print(f"::error::{name} still points at {relative} after export")
                failures += 1
            rendered.setdefault(plugin.name, []).append((name, description, document))
    if failures:
        return 1

    total = sum(len(s) for s in rendered.values())

    # Built from the same rendered skills index.md is, just below — one line per skill
    # rather than the whole description — so the combined router and each per-plugin one
    # can be checked against ROUTER_BUDGET_BYTES before anything is written. Checked
    # ahead of the `check` branch, so `--check` catches an over-budget router the same
    # way it catches a dangling pointer, rather than only a real export finding out.
    router_groups: dict[str, list[tuple[str, str]]] = {
        plugin: [
            (name, first_sentence(description, ROUTER_USE_WHEN_CAP))
            for name, description, _ in sorted(rendered[plugin])
        ]
        for plugin in sorted(rendered)
    }
    routers: dict[str, str] = {
        "router.md": render_router("Skill router", list(router_groups.items()))
    }
    for plugin, skills in router_groups.items():
        routers[f"router-{plugin}.md"] = render_router(
            f"Skill router: {plugin}", [(plugin, skills)]
        )
    router_failed = False
    for filename, text in routers.items():
        size = len(text.encode("utf-8"))
        if size > ROUTER_BUDGET_BYTES:
            print(
                f"::error::{filename} is {size:,} bytes against a budget of "
                f"{ROUTER_BUDGET_BYTES:,}; reduce router markup or split the router "
                "without removing skill triggers or changing the budget by default",
                file=sys.stderr,
            )
            router_failed = True
    if router_failed:
        return 1

    if check:
        print(f"export is clean: {total} skill(s) across {len(rendered)} plugin(s)")
        return 0

    # The export is the copy most likely to leave the repository, so it has to carry the
    # same LICENSE and NOTICE the repository ships rather than only the per-file footer
    # — checked before anything is deleted, so a repository missing either fails without
    # first destroying whatever was at `out`.
    for name in ("LICENSE", "NOTICE"):
        if not (root / name).is_file():
            print(f"::error::no {name} at the repository root ({root})", file=sys.stderr)
            return 2

    if out.exists():
        unsafe = _unsafe_to_remove(root, out)
        if unsafe is not None:
            print(f"refusing to delete {out}: {unsafe}", file=sys.stderr)
            return 2
        shutil.rmtree(out)
    (out / "skills").mkdir(parents=True)
    (out / "plugins").mkdir(parents=True)
    (out / "README.md").write_text(HOW_TO_USE, encoding="utf-8")
    (out / EXPORT_SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    for name in ("LICENSE", "NOTICE"):
        shutil.copy(root / name, out / name)
    # Siblings of skills/, not nested under it, so a path inside any router — always
    # `skills/<name>.md` — resolves whether the reader pastes router.md or one
    # router-<plugin>.md into their own AGENTS.md and copies skills/ in beside it.
    for filename, text in routers.items():
        (out / filename).write_text(text, encoding="utf-8")

    index = ["# Skill index", "", f"{total} procedures across {len(rendered)} groups.", ""]
    for plugin in sorted(rendered):
        index += [f"## {plugin}", ""]
        bodies = []
        for name, description, document in sorted(rendered[plugin]):
            (out / "skills" / f"{name}.md").write_text(document, encoding="utf-8")
            index.append(f"- **{name}** — {description}")
            # Every document ends with the notice. The bundle is one file, so it carries
            # the notice once, at its foot, rather than once per skill it concatenates.
            body = document[: document.rindex(NOTICE)]
            # rstrip first: joining untrimmed documents leaves the blank-line runs
            # markdownlint reports on the bundle.
            bodies.append(demote(body, 1).rstrip())
        index.append("")
        bundle = [f"# {plugin}", "", "\n\n---\n\n".join(bodies), "", NOTICE]
        (out / "plugins" / f"{plugin}.md").write_text("\n".join(bundle).rstrip() + "\n", "utf-8")
    (out / "index.md").write_text("\n".join(index).rstrip() + "\n", encoding="utf-8")

    print(f"exported {total} skill(s) and {len(rendered)} bundle(s) into {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export_portable", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    parser.add_argument(
        "--check", action="store_true", help="verify the export without writing anything"
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    return export(root, args.out or root / "dist" / "portable", args.check)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
