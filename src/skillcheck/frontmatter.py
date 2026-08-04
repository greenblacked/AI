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
            folded = rest.startswith(">")
            collected: list[str] = []
            index += 1
            while index < closing:
                following = lines[index]
                if following.strip() and not following[0].isspace():
                    break
                collected.append(following.strip())
                index += 1
            joined = (" " if folded else "\n").join(part for part in collected if part)
            values[key] = joined
            key_lines[key] = number
            continue

        values[key] = _unquote(rest)
        key_lines[key] = number
        index += 1

    return Frontmatter(values=values, lines=key_lines, end_line=closing + 1)
