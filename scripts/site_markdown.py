"""A small, safe Markdown renderer for the catalogue site.

The site shows files from the repository (a skill's body, the usage guide, one README
section), and a page that renders text it did not write has to be safe whatever that text
holds. This module covers the subset those files use and refuses the rest as plain text:

* ATX headings with slug ids, a level offset and unique ids per page;
* paragraphs, fenced and indented code, block quotes, thematic breaks;
* nested unordered and ordered lists, tight or loose;
* GFM pipe tables;
* inline code, ``**bold**``, ``*em*`` / ``_em_``, links, autolinks, and images shown as
  a plain link so that no remote image ever loads from a page.

Safety rests on three rules. Every piece of source text is escaped where it is emitted, so
a ``<script>`` in the source reaches the page as ``&lt;script&gt;``; raw HTML is never
passed through. A link target is kept only when it is ``http``, ``https``, ``mailto`` or a
``#fragment``, or a relative path that stays inside the repository, which is rewritten to
the file on GitHub. Anything else, including ``javascript:`` in any case and with any
control characters hidden in it, renders as its label alone.

Standard library only: CI builds the site with no dependencies installed.
"""

from __future__ import annotations

import html
import posixpath
import re
import unicodedata
from urllib.parse import quote, unquote

BLOB_URL = "https://github.com/greenblacked/AI/blob/main"

# Ids the page chrome already owns. A heading called "Home" must not take `#home`, which
# is the header button, so these are treated as taken before the first heading is seen.
RESERVED_IDS = frozenset(
    {
        "content", "banner", "home", "theme", "console-theme", "dark-switch",
        "find", "finder", "list", "count", "none", "dock", "to-top",
    }
)  # fmt: skip

# Containers nest only this deep. Deeper input is shown as a paragraph, which stops a
# line of a few thousand ">" characters from exhausting the interpreter's stack.
MAX_DEPTH = 12

# A single block longer than this is shown as escaped text without formatting.
MAX_INLINE = 50_000

ALLOWED_SCHEMES = frozenset({"http", "https", "mailto"})
SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.-]*):")
ESCAPABLE = frozenset("\\`*_{}[]()#+-.!|<>~\"'&")

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[ \t]*(.*)$")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HR_RE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
QUOTE_RE = re.compile(r"^ {0,3}>[ ]?(.*)$")
ITEM_RE = re.compile(r"^( {0,3})([-*+]|\d{1,9}[.)])( +|$)(.*)$")
TABLE_DELIMITER_RE = re.compile(r"^ {0,3}\|?[ \t]*:?-+:?[ \t]*(\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
AUTOLINK_RE = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]*:[^\s<>]*)>")


class Slugs:
    """Heading ids for one page: lower-case, unique, never one the chrome uses."""

    def __init__(self, reserved: frozenset[str] = RESERVED_IDS) -> None:
        self.used: set[str] = set(reserved)

    def take(self, text: str) -> str:
        base = slugify(text) or "section"
        slug, count = base, 0
        while slug in self.used:
            count += 1
            slug = f"{base}-{count}"
        self.used.add(slug)
        return slug


def slugify(text: str) -> str:
    """The id GitHub would give a heading, so in-document links keep working."""
    kept = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s", "-", kept.strip())


def _strip_controls(url: str) -> str:
    """The URL without control characters, which no link target legitimately holds."""
    return "".join(ch for ch in url.strip() if unicodedata.category(ch)[0] != "C")


def _scheme_of(url: str) -> str | None:
    """The scheme as a browser would read it, or None when the target has none.

    Browsers drop tabs, newlines and spaces inside a scheme and ignore leading control
    characters, so ``java\tscript:`` is ``javascript:`` to them. The test therefore runs
    on a copy with every control and separator character removed, lower-cased.
    """
    squeezed = "".join(ch for ch in url if unicodedata.category(ch)[0] not in "CZ").lower()
    found = SCHEME_RE.match(squeezed)
    return found.group(1) if found else None


def rewrite_href(url: str, source_dir: str = "") -> str | None:
    """The href to emit for a link target, or ``None`` when only the label should show.

    ``source_dir`` is the repository-relative directory of the file being rendered. A
    relative path resolves against it and becomes the file's page on GitHub; a path that
    climbs out of the repository root is refused.
    """
    cleaned = _strip_controls(url)
    if not cleaned:
        return None
    if cleaned.startswith("#"):
        return cleaned
    scheme = _scheme_of(url)
    if scheme is not None:
        return cleaned.replace(" ", "%20") if scheme in ALLOWED_SCHEMES else None
    # "//host/path" is a network-path reference, not a repository path.
    if cleaned.startswith(("//", "\\\\")):
        return None
    path, hash_mark, fragment = cleaned.partition("#")
    path = path.partition("?")[0]
    path = unquote(path).replace("\\", "/")
    if not path:
        return None
    base = "" if path.startswith("/") else source_dir
    parts: list[str] = []
    for part in posixpath.join(base, path).split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    target = "/".join(parts)
    if path.endswith("/") and target:
        target += "/"
    href = f"{BLOB_URL}/{quote(target, safe='/-_.~')}"
    if hash_mark and fragment:
        href += "#" + quote(unquote(fragment), safe="-_.~")
    return href


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _anchor(href: str, label_html: str) -> str:
    external = href.startswith(("http://", "https://", "mailto:"))
    rel = ' rel="noopener noreferrer"' if external else ""
    return f'<a href="{_escape(href)}"{rel}>{label_html}</a>'


def _code_span_end(text: str, begin: int) -> tuple[int, int] | None:
    """For a backtick run at ``begin``, the (start, end) of its closing run, or None."""
    end = begin
    while end < len(text) and text[end] == "`":
        end += 1
    size = end - begin
    probe = end
    while probe < len(text):
        if text[probe] != "`":
            probe += 1
            continue
        stop = probe
        while stop < len(text) and text[stop] == "`":
            stop += 1
        if stop - probe == size:
            return probe, stop
        probe = stop
    return None


def _skip_label(text: str, begin: int) -> int | None:
    """Index of the ``]`` that closes the ``[`` at ``begin``, or None."""
    depth = 0
    i = begin
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            span = _code_span_end(text, i)
            if span is not None:
                i = span[1]
                continue
            while i < len(text) and text[i] == "`":
                i += 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _label_ends(text: str) -> tuple[set[int], dict[int, int]]:
    """Every ``[`` in one forward pass, and the ``]`` that closes each one that closes.

    It tokenises exactly as ``_skip_label`` does, so for any ``[`` this pass sees it gives
    the same answer, but once per block rather than once per bracket: a paragraph of
    unmatched brackets would otherwise rescan its whole suffix for every one of them.
    """
    opens: set[int] = set()
    ends: dict[int, int] = {}
    stack: list[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            span = _code_span_end(text, i)
            if span is not None:
                i = span[1]
                continue
            while i < len(text) and text[i] == "`":
                i += 1
            continue
        if ch == "[":
            opens.add(i)
            stack.append(i)
        elif ch == "]" and stack:
            ends[stack.pop()] = i
        i += 1
    return opens, ends


def _parse_destination(text: str, begin: int) -> tuple[str, int] | None:
    """Parse ``(dest "title")`` starting at the ``(`` at ``begin``; the end index follows."""
    i = begin + 1
    while i < len(text) and text[i] in " \t\n":
        i += 1
    if i >= len(text):
        return None
    if text[i] == "<":
        stop = text.find(">", i + 1)
        if stop == -1 or "\n" in text[i:stop]:
            return None
        destination = text[i + 1 : stop]
        i = stop + 1
    else:
        depth = 0
        start = i
        while i < len(text):
            ch = text[i]
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch in " \t\n":
                break
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        destination = text[start:i]
    while i < len(text) and text[i] in " \t\n":
        i += 1
    if i < len(text) and text[i] in "\"'(":
        closer = ")" if text[i] == "(" else text[i]
        stop = text.find(closer, i + 1)
        if stop == -1:
            return None
        i = stop + 1
        while i < len(text) and text[i] in " \t\n":
            i += 1
    if i >= len(text) or text[i] != ")":
        return None
    return re.sub(r"\\([^\w\s])", r"\1", destination), i + 1


def _find_closer(text: str, begin: int, delimiter: str) -> int | None:
    """Index where the emphasis delimiter closing one opened before ``begin`` starts.

    A run of the delimiter character that follows a non-space is a closer; one that
    follows a space opens something else and is skipped whole. In a run longer than the
    delimiter the closer is its last characters, which leaves the rest to an inner pass,
    so ``**a *b***`` closes both.
    """
    mark = delimiter[0]
    size = len(delimiter)
    i = begin
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            span = _code_span_end(text, i)
            if span is not None:
                i = span[1]
                continue
            while i < len(text) and text[i] == "`":
                i += 1
            continue
        if ch != mark:
            i += 1
            continue
        run = 0
        while i + run < len(text) and text[i + run] == mark:
            run += 1
        after = text[i + run : i + run + 1]
        intraword = mark == "_" and (after.isalnum() or after == "_")
        if i > begin and not text[i - 1].isspace() and run >= size and not intraword:
            return i + run - size
        i += run
    return None


def render_inline(text: str, source_dir: str = "", *, links: bool = True) -> str:
    """Inline HTML for one block of source text. Every character is escaped on the way."""
    if len(text) > MAX_INLINE:
        return _escape(text)
    out: list[str] = []
    dead: dict[str, int] = {}
    labels = _label_ends(text) if "[" in text else None
    i = 0
    size = len(text)
    plain_start = 0

    def flush(upto: int) -> None:
        if upto > plain_start:
            out.append(_text(text[plain_start:upto]))

    while i < size:
        ch = text[i]
        if ch == "\\" and i + 1 < size and text[i + 1] in ESCAPABLE:
            flush(i)
            out.append(_escape(text[i + 1]))
            i += 2
            plain_start = i
        elif ch == "`":
            flush(i)
            span = _code_span_end(text, i)
            run = 0
            while i + run < size and text[i + run] == "`":
                run += 1
            if span is None:
                out.append("`" * run)
                i += run
            else:
                inner = text[i + run : span[0]].replace("\n", " ")
                if len(inner) > 2 and inner[0] == " " and inner[-1] == " " and inner.strip():
                    inner = inner[1:-1]
                out.append(f"<code>{_escape(inner)}</code>")
                i = span[1]
            plain_start = i
        elif ch == "!" and text.startswith("![", i):
            flush(i)
            consumed = _inline_link(text, i + 1, source_dir, links, image=True, labels=labels)
            if consumed is None:
                out.append("!")
                i += 1
            else:
                out.append(consumed[0])
                i = consumed[1]
            plain_start = i
        elif ch == "[":
            flush(i)
            consumed = _inline_link(text, i, source_dir, links, image=False, labels=labels)
            if consumed is None:
                out.append("[")
                i += 1
            else:
                out.append(consumed[0])
                i = consumed[1]
            plain_start = i
        elif ch == "<":
            flush(i)
            auto = AUTOLINK_RE.match(text, i)
            if auto is None:
                out.append("&lt;")
                i += 1
            else:
                href = rewrite_href(auto.group(1)) if links else None
                label = _escape(auto.group(1))
                out.append(_anchor(href, label) if href is not None else label)
                i = auto.end()
            plain_start = i
        elif ch in "*_":
            run = 1
            while i + run < size and text[i + run] == ch:
                run += 1
            emphasised = _emphasis(text, i, run, source_dir, links, dead)
            if emphasised is None:
                i += run
            else:
                flush(i)
                out.append(emphasised[0])
                i = emphasised[1]
                plain_start = i
        else:
            i += 1
    flush(size)
    return "".join(out)


def _text(raw: str) -> str:
    """Escaped plain text, with a two-space line ending kept as a line break."""
    escaped = _escape(raw)
    return re.sub(r" {2,}\n", "<br>\n", escaped)


def _emphasis(
    text: str, begin: int, run: int, source_dir: str, links: bool, dead: dict[str, int]
) -> tuple[str, int] | None:
    """Emphasis opened by the ``run`` delimiter characters at ``begin``, or None."""
    mark = text[begin]
    # A bare underscore inside a word (snake_case) is not emphasis.
    if mark == "_" and begin > 0 and (text[begin - 1].isalnum() or text[begin - 1] == "_"):
        return None
    if run > 3:
        return None
    delimiter = mark * run
    inner_start = begin + run
    if inner_start >= len(text) or text[inner_start].isspace():
        return None
    # A search that failed from an earlier start fails from a later one, which keeps a
    # line of unmatched asterisks from costing a scan each.
    if inner_start >= dead.get(delimiter, len(text) + 1):
        return None
    closer = _find_closer(text, inner_start, delimiter)
    if closer is None:
        dead[delimiter] = min(dead.get(delimiter, inner_start), inner_start)
        return None
    inner = render_inline(text[inner_start:closer], source_dir, links=links)
    tag = {1: "em", 2: "strong", 3: "strong><em"}[run]
    closing = {1: "em", 2: "strong", 3: "em></strong"}[run]
    return f"<{tag}>{inner}</{closing}>", closer + run


def _inline_link(
    text: str,
    begin: int,
    source_dir: str,
    links: bool,
    *,
    image: bool,
    labels: tuple[set[int], dict[int, int]] | None = None,
) -> tuple[str, int] | None:
    """A ``[label](target)`` at ``begin``; returns the HTML and where it ended."""
    if labels is not None and begin in labels[0]:
        close = labels[1].get(begin)
    else:
        close = _skip_label(text, begin)
    if close is None or close + 1 >= len(text) or text[close + 1] != "(":
        return None
    parsed = _parse_destination(text, close + 1)
    if parsed is None:
        return None
    destination, end = parsed
    label = text[begin + 1 : close]
    href = rewrite_href(destination, source_dir) if links else None
    if image:
        # No remote image is ever loaded: the picture becomes a link to its address.
        shown = render_inline(label, source_dir, links=False) if label.strip() else ""
        if not shown:
            shown = _escape(destination.strip())
        return (_anchor(href, shown) if href is not None else shown), end
    inner = render_inline(label, source_dir, links=False)
    return (_anchor(href, inner) if href is not None else inner), end


def plain_text(markup: str) -> str:
    """The visible text of rendered inline HTML, for slugs."""
    return html.unescape(re.sub(r"<[^>]*>", "", markup))


# ---------------------------------------------------------------------------- blocks


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank(line: str) -> bool:
    return not line.strip()


def _split_cells(row: str) -> list[str]:
    """The cells of a pipe-table row, honouring ``\\|`` and code spans."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    cells: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            current.append("|")
            i += 2
        elif ch == "`":
            span = _code_span_end(row, i)
            if span is None:
                current.append(ch)
                i += 1
            else:
                current.append(row[i : span[1]].replace("\\|", "|"))
                i = span[1]
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
            i += 1
        else:
            current.append(ch)
            i += 1
    tail = "".join(current).strip()
    if tail or not row.endswith("|"):
        cells.append(tail)
    return cells


def _alignment(cell: str) -> str:
    cell = cell.strip()
    left, right = cell.startswith(":"), cell.endswith(":")
    if left and right:
        return "c"
    return "r" if right else ""


class _Renderer:
    def __init__(self, source_dir: str, offset: int, slugs: Slugs) -> None:
        self.source_dir = source_dir
        self.offset = offset
        self.slugs = slugs

    def inline(self, text: str) -> str:
        return render_inline(text, self.source_dir)

    # A block is (kind, html, inner); inner is a paragraph's content, used for tight lists.
    def blocks(self, lines: list[str], depth: int = 0) -> tuple[list[tuple[str, str, str]], bool]:
        """Render ``lines``; also say whether blank lines separated any two blocks."""
        out: list[tuple[str, str, str]] = []
        spaced = False
        blank_seen = False
        i = 0

        def emit(kind: str, markup: str, inner: str = "") -> None:
            nonlocal spaced, blank_seen
            if out and blank_seen:
                spaced = True
            blank_seen = False
            out.append((kind, markup, inner))

        while i < len(lines):
            line = lines[i]
            if _is_blank(line):
                blank_seen = True
                i += 1
                continue
            if depth >= MAX_DEPTH:
                inner = self.inline(line.strip())
                emit("p", f"<p>{inner}</p>", inner)
                i += 1
                continue
            fence = FENCE_RE.match(line)
            if fence is not None and not (fence.group(2)[0] == "`" and "`" in fence.group(3)):
                i = self._fenced(lines, i, fence, emit)
                continue
            heading = ATX_RE.match(line)
            if heading is not None:
                level = min(6, len(heading.group(1)) + self.offset)
                content = self.inline((heading.group(2) or "").strip())
                slug = self.slugs.take(plain_text(content))
                emit("h", f'<h{level} id="{_escape(slug)}">{content}</h{level}>')
                i += 1
                continue
            if HR_RE.match(line):
                emit("hr", "<hr>")
                i += 1
                continue
            if QUOTE_RE.match(line):
                i = self._quote(lines, i, depth, emit)
                continue
            item = ITEM_RE.match(line)
            if item is not None:
                i = self._list(lines, i, depth, emit)
                continue
            if self._table_at(lines, i):
                i = self._table(lines, i, emit)
                continue
            if _indent(line) >= 4:
                i = self._indented(lines, i, emit)
                continue
            i = self._paragraph(lines, i, emit)
        return out, spaced

    def _paragraph(self, lines: list[str], i: int, emit) -> int:
        collected = [lines[i].lstrip()]
        i += 1
        while i < len(lines):
            line = lines[i]
            if _is_blank(line) or self._interrupts(lines, i):
                break
            collected.append(line.lstrip())
            i += 1
        collected[-1] = collected[-1].rstrip()
        inner = self.inline("\n".join(collected))
        emit("p", f"<p>{inner}</p>", inner)
        return i

    def _interrupts(self, lines: list[str], i: int) -> bool:
        line = lines[i]
        fence = FENCE_RE.match(line)
        if fence is not None and not (fence.group(2)[0] == "`" and "`" in fence.group(3)):
            return True
        if ATX_RE.match(line) or HR_RE.match(line) or QUOTE_RE.match(line):
            return True
        item = ITEM_RE.match(line)
        if item is not None and item.group(4).strip():
            marker = item.group(2)
            if marker in "-*+" or marker.rstrip(".)") == "1":
                return True
        return self._table_at(lines, i)

    def _fenced(self, lines: list[str], i: int, fence: re.Match[str], emit) -> int:
        lead = len(fence.group(1))
        marker = fence.group(2)
        info = fence.group(3).strip().split(None, 1)
        language = re.sub(r"[^a-z0-9-]", "", info[0].lower()) if info else ""
        close = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$")
        body: list[str] = []
        i += 1
        while i < len(lines) and not close.match(lines[i]):
            line = lines[i]
            strip = min(lead, _indent(line))
            body.append(line[strip:])
            i += 1
        cls = f' class="language-{language}"' if language else ""
        code = _escape("\n".join(body))
        emit("pre", f'<pre tabindex="0"><code{cls}>{code}\n</code></pre>')
        return i + 1 if i < len(lines) else i

    def _indented(self, lines: list[str], i: int, emit) -> int:
        body: list[str] = []
        while i < len(lines) and (_is_blank(lines[i]) or _indent(lines[i]) >= 4):
            body.append(lines[i][4:] if not _is_blank(lines[i]) else "")
            i += 1
        while body and not body[-1]:
            body.pop()
        emit("pre", f'<pre tabindex="0"><code>{_escape(chr(10).join(body))}\n</code></pre>')
        return i

    def _quote(self, lines: list[str], i: int, depth: int, emit) -> int:
        inner: list[str] = []
        while i < len(lines):
            match = QUOTE_RE.match(lines[i])
            if match is not None:
                inner.append(match.group(1))
                i += 1
            elif (
                inner
                and not _is_blank(lines[i])
                and not _is_blank(inner[-1])
                and not self._interrupts(lines, i)
            ):
                inner.append(lines[i])  # lazy continuation of a paragraph
                i += 1
            else:
                break
        blocks, _ = self.blocks(inner, depth + 1)
        body = "\n".join(markup for _, markup, _ in blocks)
        emit("quote", f"<blockquote>\n{body}\n</blockquote>")
        return i

    def _table_at(self, lines: list[str], i: int) -> bool:
        if i + 1 >= len(lines) or "|" not in lines[i]:
            return False
        delimiter = lines[i + 1]
        if not TABLE_DELIMITER_RE.match(delimiter) or "-" not in delimiter:
            return False
        return len(_split_cells(lines[i])) == len(_split_cells(delimiter)) >= 1

    def _table(self, lines: list[str], i: int, emit) -> int:
        header = _split_cells(lines[i])
        aligns = [_alignment(cell) for cell in _split_cells(lines[i + 1])]
        i += 2
        rows: list[list[str]] = []
        while i < len(lines) and not _is_blank(lines[i]) and not self._starts_block(lines[i]):
            rows.append(_split_cells(lines[i]))
            i += 1
        width = len(header)

        def cell(tag: str, text: str, column: int) -> str:
            cls = f' class="al-{aligns[column]}"' if aligns[column] else ""
            return f"<{tag}{cls}>{self.inline(text)}</{tag}>"

        head = "".join(cell("th", text, n) for n, text in enumerate(header))
        body = []
        for row in rows:
            row = (row + [""] * width)[:width]
            body.append(
                "<tr>" + "".join(cell("td", text, n) for n, text in enumerate(row)) + "</tr>"
            )
        markup = (
            '<div class="table-wrap"><table>\n'
            f"<thead><tr>{head}</tr></thead>\n"
            f"<tbody>\n{chr(10).join(body)}\n</tbody>\n</table></div>"
        )
        emit("table", markup)
        return i

    def _starts_block(self, line: str) -> bool:
        return bool(
            FENCE_RE.match(line) or ATX_RE.match(line) or HR_RE.match(line) or QUOTE_RE.match(line)
        )

    def _list(self, lines: list[str], i: int, depth: int, emit) -> int:
        first = ITEM_RE.match(lines[i])
        if first is None:  # the caller matched this line already
            return i
        ordered = first.group(2)[0].isdigit()
        kind = first.group(2)[-1] if ordered else first.group(2)
        start = int(first.group(2)[:-1]) if ordered else 1
        items: list[tuple[list[tuple[str, str, str]], bool]] = []
        loose = False
        while i < len(lines):
            match = ITEM_RE.match(lines[i])
            if match is None:
                break
            marker = match.group(2)
            if marker[0].isdigit() != ordered or (marker[-1] if ordered else marker) != kind:
                break
            padding = len(match.group(3))
            content_offset = len(match.group(1)) + len(marker) + (padding if 0 < padding < 5 else 1)
            if not match.group(4).strip():
                content_offset = len(match.group(1)) + len(marker) + 1
            item_lines = [match.group(4) if padding < 5 else " " * (padding - 1) + match.group(4)]
            i += 1
            while i < len(lines):
                line = lines[i]
                if _is_blank(line):
                    ahead = i
                    while ahead < len(lines) and _is_blank(lines[ahead]):
                        ahead += 1
                    if ahead < len(lines) and _indent(lines[ahead]) >= content_offset:
                        item_lines.extend("" for _ in range(ahead - i))
                        i = ahead
                        continue
                    break
                if _indent(line) >= content_offset:
                    item_lines.append(line[content_offset:])
                    i += 1
                elif (
                    not _is_blank(item_lines[-1])
                    and not self._interrupts(lines, i)
                    and not ITEM_RE.match(line)
                    and not _open_fence(item_lines)
                ):
                    item_lines.append(line.lstrip())
                    i += 1
                else:
                    break
            blocks, spaced = self.blocks(item_lines, depth + 1)
            items.append((blocks, spaced))
            # A blank line then a sibling marker keeps the list going, but loosely.
            ahead = i
            while ahead < len(lines) and _is_blank(lines[ahead]):
                ahead += 1
            sibling = ITEM_RE.match(lines[ahead]) if ahead < len(lines) else None
            if (
                sibling is not None
                and ahead > i
                and sibling.group(2)[0].isdigit() == ordered
                and (sibling.group(2)[-1] if ordered else sibling.group(2)) == kind
            ):
                loose = True
                i = ahead
        loose = loose or any(spaced for _, spaced in items)
        rendered = []
        for blocks, _ in items:
            parts = []
            for block_kind, markup, inner in blocks:
                parts.append(markup if loose or block_kind != "p" else inner)
            rendered.append("<li>" + "\n".join(parts) + "</li>")
        tag = "ol" if ordered else "ul"
        attr = f' start="{start}"' if ordered and start != 1 else ""
        emit("list", f"<{tag}{attr}>\n" + "\n".join(rendered) + f"\n</{tag}>")
        return i


def _open_fence(lines: list[str]) -> bool:
    """True when the lines end inside a fenced block that was never closed."""
    marker = ""
    for line in lines:
        match = FENCE_RE.match(line)
        if not marker and match is not None:
            marker = match.group(2)
        elif (
            marker
            and match is not None
            and match.group(2)[0] == marker[0]
            and len(match.group(2)) >= len(marker)
            and not match.group(3).strip()
        ):
            marker = ""
    return bool(marker)


def render(
    text: str,
    *,
    source_dir: str = "",
    offset: int = 0,
    slugs: Slugs | None = None,
) -> str:
    """HTML for ``text``.

    ``source_dir`` is the repository directory the file sits in, so a relative link
    resolves to the right file on GitHub. ``offset`` pushes every heading down that many
    levels (capped at ``h6``). Pass one :class:`Slugs` for every call on a page so that
    ids stay unique across them.
    """
    renderer = _Renderer(source_dir.strip("/"), offset, slugs or Slugs())
    lines = [
        line.expandtabs(4) for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    blocks, _ = renderer.blocks(lines)
    return "\n".join(markup for _, markup, _ in blocks)
