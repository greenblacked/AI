"""A strict, dependency-free reader for SKILL.md YAML frontmatter.

This deliberately does not use PyYAML. CI runs on an interpreter provided by
``actions/setup-python``, where PyYAML is absent, and skill frontmatter is a flat
mapping of scalars — so a hand-written scanner costs nothing and is *stricter*
than a real YAML parser. It can reject tabs, byte-order marks and duplicate keys,
all of which YAML would either accept silently or resolve in a surprising way.

The parser tracks the line number of every key so callers can emit GitHub
annotations that land on the right line of the diff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DELIMITER = "---"
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):[ \t]*(.*)$")
BLOCK_INDICATORS = {">", "|", ">-", "|-", ">+", "|+"}


class FrontmatterError(Exception):
    """A frontmatter block that cannot be read at all."""

    def __init__(self, message: str, line: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.line = line


@dataclass
class Frontmatter:
    """A parsed frontmatter block.

    ``values`` maps key to string value; ``lines`` maps key to its 1-based line
    number in the file; ``end_line`` is the line holding the closing delimiter.
    """

    values: dict[str, str]
    lines: dict[str, int]
    end_line: int

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.values.get(key, default)

    def line_of(self, key: str) -> int:
        return self.lines.get(key, 1)


def _unquote(raw: str) -> str:
    """Strip one layer of quoting, mirroring YAML's scalar rules closely enough."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        inner = raw[1:-1]
        if raw[0] == '"':
            return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    return raw


def _fold(lines: list[str]) -> str:
    """Fold a folded block the way YAML folds one.

    Two rules do the work. Consecutive line breaks collapse to one fewer newline, so a
    single break between ordinary lines becomes a space and a blank line becomes a
    newline. A line indented further than the block is *more-indented*: it is kept
    verbatim, and the breaks on either side of it stay newlines rather than folding.

    Missing that second rule is how the earlier version diverged: it folded a
    more-indented line into the surrounding text and produced a string shorter than the
    one the runtime loads, which meant the 1024-character cap was measured against the
    wrong thing.
    """
    result: list[str] = []
    previous: str | None = None
    previous_indented = False

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            run = 0
            while index < len(lines) and not lines[index].strip():
                run += 1
                index += 1
            # A break next to a more-indented line is never folded, so one survives
            # on top of the newlines the blank lines themselves contribute. One,
            # not one per side: a run between two more-indented lines still only
            # has the single unfolded break.
            following_indented = index < len(lines) and lines[index][:1].isspace()
            trailing = index >= len(lines)
            extra = int((previous_indented and not trailing) or following_indented)
            result.append("\n" * (run + extra))
            previous, previous_indented = "blank", False
            continue

        indented = line[:1].isspace()
        if previous is None or previous == "blank":
            separator = ""
        elif indented or previous_indented:
            separator = "\n"
        else:
            separator = " "
        result.append(separator + (line if indented else line.strip()))
        previous, previous_indented = "line", indented
        index += 1

    return "".join(result)


def _block_scalar(indicator: str, raw: list[str]) -> str:
    """Resolve a YAML block scalar the way a real YAML parser would.

    This matters more than it looks. The 1024-character cap on ``description`` is
    enforced on whatever string this returns, so if the folding rules differ from the
    runtime's, the validator polices a string nobody ever loads. The earlier
    implementation joined every line with a single space or newline and dropped blank
    lines entirely, which disagreed with YAML on any block containing a paragraph
    break.

    Handles the two indicators and the three chomping modes. Explicit indentation
    indicators (``|2``) are not supported; they are vanishingly rare in frontmatter and
    a caller who needs one is better served by a quoted scalar.
    """
    literal = indicator.startswith("|")
    chomp = "clip"
    if indicator.endswith("-"):
        chomp = "strip"
    elif indicator.endswith("+"):
        chomp = "keep"

    content = [line for line in raw]
    while content and not content[-1].strip():
        if chomp == "keep":
            break
        content.pop()
    if not content:
        return ""

    # Strip the block's own indentation, set by its first non-empty line, rather than
    # each line's leading whitespace: relative indentation inside a literal block is
    # content.
    indents = [len(line) - len(line.lstrip()) for line in content if line.strip()]
    base = min(indents) if indents else 0
    stripped = [line[base:] if len(line) > base else line.strip() for line in content]

    if not any(line.strip() for line in stripped):
        # A block of nothing but blank lines has no final line break to clip or keep,
        # so chomping does not apply to it.
        return "\n" * len(stripped) if chomp == "keep" else ""

    body = "\n".join(stripped) if literal else _fold(stripped)

    if chomp == "strip":
        return body
    return body + "\n"


def parse(text: str) -> Frontmatter:
    """Parse the frontmatter block at the top of ``text``.

    Raises :class:`FrontmatterError` when the block is missing or malformed.
    """
    if text.startswith("﻿"):
        raise FrontmatterError(
            "file begins with a UTF-8 byte-order mark; the frontmatter delimiter "
            "must be the very first byte"
        )

    lines = text.split("\n")
    if not lines or lines[0].rstrip() != DELIMITER:
        raise FrontmatterError("no YAML frontmatter: the file must start with '---'")

    closing = None
    for index in range(1, len(lines)):
        if lines[index].rstrip() == DELIMITER:
            closing = index
            break
    if closing is None:
        raise FrontmatterError("frontmatter is never closed: no second '---' line")

    values: dict[str, str] = {}
    key_lines: dict[str, int] = {}

    index = 1
    while index < closing:
        raw = lines[index]
        number = index + 1

        if "\t" in raw:
            raise FrontmatterError("frontmatter contains a tab character", number)
        if not raw.strip() or raw.lstrip().startswith("#"):
            index += 1
            continue
        if raw[0].isspace():
            raise FrontmatterError(
                "unexpected indentation: frontmatter must be a flat key/value block",
                number,
            )

        match = KEY_RE.match(raw)
        if not match:
            raise FrontmatterError(f"cannot read frontmatter line: {raw!r}", number)

        key, rest = match.group(1), match.group(2).strip()
        if key in values:
            raise FrontmatterError(f"duplicate frontmatter key {key!r}", number)

        if rest in BLOCK_INDICATORS or rest == "":
            collected = []
            index += 1
            while index < closing:
                following = lines[index]
                if following.strip() and not following[0].isspace():
                    break
                collected.append(following)
                index += 1
            values[key] = _block_scalar(rest, collected)
            key_lines[key] = number
            continue

        values[key] = _unquote(rest)
        key_lines[key] = number
        index += 1

    return Frontmatter(values=values, lines=key_lines, end_line=closing + 1)
