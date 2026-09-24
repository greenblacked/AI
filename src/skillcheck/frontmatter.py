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
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?:[ \t]+(.*))?$")
BLOCK_INDICATORS = {">", "|", ">-", "|-", ">+", "|+"}
# A block-scalar header carrying an explicit indentation indicator (`|2`, `>-1`, `|1+`):
# valid YAML, and a real parser resolves it, but not one of the six headers this reader
# implements folding and chomping for. Matched only to word the error accurately - it is
# vanishingly rare in frontmatter, and a caller who needs one is better served by a
# quoted scalar - not to support it.
EXPLICIT_INDENTATION_RE = re.compile(r"^[|>](?:[1-9][-+]?|[-+][1-9])$")


class FrontmatterError(Exception):
    """A frontmatter block that cannot be read at all.

    ``code`` defaults to ``"frontmatter"``, the code every caller has reported for
    every variety of unparseable block since before this attribute existed. A check
    that reports a specific, actionable divergence from what a real YAML parser would
    do — rather than "the block does not parse" — passes a more specific one instead,
    so CI output and the code tables in docs/ can tell the two apart.
    """

    def __init__(self, message: str, line: int = 1, code: str = "frontmatter") -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.code = code


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


def _strip_comment(value: str) -> str:
    """Drop a trailing ``# comment`` from an unquoted scalar, as YAML does.

    Keeping it meant the length and angle-bracket checks measured a string the runtime
    never sees, and a comment after ``name:`` produced a bogus name-mismatch.
    """
    if value[:1] in "\"'":
        return value
    cut = value.find(" #")
    return value[:cut].rstrip() if cut >= 0 else value


# The plain-scalar indicator characters a real YAML parser treats specially at the
# start of a value: flow collections, anchors, aliases, tags, a comment, and the
# reserved directive/future-use indicators. ``-`` and ``|``/``>`` are handled separately
# below, because each is only a problem in some of its forms.
AMBIGUOUS_LEADING_CHARS = "[{&*!%@`#"


def _reject_leading_indicator(value: str, line: int) -> None:
    """Refuse a value beginning with a character YAML would not read as plain text.

    Split out of ``_reject_unquotable`` so the same checks can run against the first
    content line of a wrapped, indicator-less value: YAML does not care which physical
    line a node starts on, so ``description:\\n  - foo`` is a one-item list to a real
    parser for exactly the reason ``description: - foo`` is, and deserves the same
    error. The trailing ``': '`` check stays behind in ``_reject_unquotable``, because
    a colon partway through a wrapped body is ``_reject_mapping_like_body``'s check, not
    this one, and running both here would report it under two different codes depending
    on which line it fell on.
    """
    if value[:1] in AMBIGUOUS_LEADING_CHARS:
        raise FrontmatterError(
            f"value starts with {value[0]!r}; YAML reads that as a flow collection, "
            "anchor, alias, tag, comment or directive rather than as a plain string, "
            "so this parses differently here than it does on upload. Quote the value.",
            line,
            code="ambiguous-yaml",
        )
    if value == "-" or value.startswith("- "):
        raise FrontmatterError(
            "value starts with '- ', which YAML reads as a sequence entry rather than "
            "a plain string — a real parser rejects this outright. Quote the value.",
            line,
            code="ambiguous-yaml",
        )
    if value[:1] in "|>":
        if EXPLICIT_INDENTATION_RE.match(value):
            raise FrontmatterError(
                f"{value!r} is a block scalar header with an explicit indentation "
                "indicator; a real YAML parser accepts it, but explicit indentation "
                "indicators are not supported by this reader. Rewrite it without one, "
                "or quote the value.",
                line,
                code="ambiguous-yaml",
            )
        raise FrontmatterError(
            f"value starts with {value[0]!r} but is not one of the block-scalar headers "
            f"({', '.join(sorted(BLOCK_INDICATORS))}); YAML reads a bare "
            f"{value[0]!r} as a block scalar indicator and fails to parse the rest of "
            "the line. Quote the value.",
            line,
            code="ambiguous-yaml",
        )


def _reject_unquotable(key: str, value: str, line: int) -> None:
    """Refuse a plain scalar a real YAML parser would not read the same way.

    ``description: the answer is: red`` parses here as a plain string and is rejected by
    every real YAML parser, so the file validates clean and then fails on upload — the
    opposite of what a stricter-than-YAML scanner is for. A colon is only a problem when
    followed by a space or ending the value, which is why ``https://x`` and ``10:30``
    are fine.

    The same failure mode has a second shape: a value that YAML reads as something other
    than a plain string at all. ``description: [x]`` validates here as the four
    characters ``[x]`` and loads on the Skills API as a one-element list, and
    ``argument-hint: [skill-name]`` — the form eleven command files in this repository
    used to carry — is the same bug with a friendlier-looking value. ``description: -
    Use when foo`` is worse: a real parser rejects it outright as a sequence entry with
    no key, so it fails on upload with no local warning at all. Quoting the value is
    the fix in every case, which is why the message says so rather than describing the
    YAML grammar.

    ``paths:`` is the one key this reader deliberately treats as more than a scalar —
    ``_rule_globs`` documents both YAML sequence forms it accepts: the flow form,
    ``paths: ["a/**", "b/**"]``, on the key's own line, and the block form, one glob per
    line starting with ``- ``, on the lines that follow it. Only the flow form is
    exempted here: rejecting it would make a documented, working rule fail for looking
    like the bug this check exists to catch. The block form's ``- `` never appears on
    the key's own line — ``paths: - "a/**"`` is not shorthand for it, it is a real YAML
    ``ScannerError`` — so it is exempted only in ``_reject_mapping_like_body``, which
    checks the lines the block form actually occupies.
    """
    if value[:1] in "\"'":
        return
    if value in BLOCK_INDICATORS or value == "":
        return
    if key == "paths" and value.startswith("["):
        return
    # The leading-character cases are checked first because they are the more specific
    # diagnosis: ``{a: b}`` also contains ": ", but it is a flow mapping, not a plain
    # scalar with a stray colon in it, and the message should say which.
    _reject_leading_indicator(value, line)
    if ": " in value or value.endswith(":"):
        raise FrontmatterError(
            "unquoted ':' followed by a space in a value; YAML reads that as a nested "
            "key. Quote the value, or use a '>' block.",
            line,
        )


# The double-quoted escapes this reader decodes. YAML defines many more (\0, \a, \e,
# \xXX, \UXXXXXXXX and several named Unicode spaces among them), but these five are the
# ones a skill description plausibly contains; an escape outside this set is left in the
# string verbatim rather than guessed at.
_SIMPLE_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t"}


def _decode_double_quoted(inner: str) -> str:
    """Decode the escapes inside a double-quoted scalar's body.

    The 1024-character cap and every other length or content check run on this decoded
    string, because that is what the runtime loads. The two-pass ``.replace()`` this
    replaced decoded ``\\"`` before ``\\\\``, so ``\\\\"`` — an escaped backslash
    followed by a literal quote — round-tripped through the first replacement before the
    second ever saw it and came out wrong; scanning left to right and consuming each
    escape once avoids that.
    """
    result: list[str] = []
    index = 0
    while index < len(inner):
        char = inner[index]
        if char == "\\" and index + 1 < len(inner):
            following = inner[index + 1]
            if following in _SIMPLE_ESCAPES:
                result.append(_SIMPLE_ESCAPES[following])
                index += 2
                continue
            if following == "u" and index + 6 <= len(inner):
                digits = inner[index + 2 : index + 6]
                try:
                    result.append(chr(int(digits, 16)))
                    index += 6
                    continue
                except ValueError:
                    pass
        result.append(char)
        index += 1
    return "".join(result)


def _reject_mapping_like_body(key: str, lines: list[str], first_line: int) -> None:
    """Refuse a wrapped plain scalar whose body a real YAML parser reads as a mapping,
    or whose first content line opens something other than a plain string.

    ``description:`` with nothing after it, followed by indented lines, is read here as
    a folded plain scalar — the same rule ``_fold`` implements for an explicit ``>``
    block, and correct for ordinary wrapped prose. It is only correct when none of those
    lines themselves look like a mapping entry: ``description:\\n  Use when: xxx`` is not
    a two-line string to a real parser, it is a mapping with one key, and every line
    after the one that first looks like a key is a scanner error rather than folded text.
    Unlike an explicit block scalar, where the content is literal and a colon is never
    ambiguous, there is no indicator here distinguishing "wrapped string" from "nested
    mapping" except this shape — so this check does not apply inside ``>`` or ``|``.

    YAML does not care which physical line a node starts on, so the first non-blank
    line gets the same leading-character scrutiny a single-line value does first:
    ``description:\\n  - foo`` is a one-item list and ``description:\\n  [x]`` is a
    one-item list of a different shape, neither of which is the wrapped string it looks
    like here. A comment line gets its own message rather than the leading-character
    one: it is not read as a flow collection or any other node, it is simply dropped,
    which is a plainer defect than the others and deserves saying so rather than being
    filed under the same wording as ``[x]``.

    ``paths:`` is exempted from the ``- `` case the same way it is in
    ``_reject_unquotable``, for the same reason: its block-sequence form starts every
    entry with exactly this ``- ``. It is exempted from the comment case too, but
    differently — a comment line is skipped rather than accepted, because
    ``_rule_globs`` skips one the same way when it scans this same block for globs, so
    ``paths:`` followed by an explanatory comment and then its list is not ambiguous at
    all, merely delayed by one line.
    """
    for offset, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if key == "paths" and stripped.startswith("#"):
            continue
        if key == "paths" and (stripped == "-" or stripped.startswith("- ")):
            break
        if stripped.startswith("#"):
            raise FrontmatterError(
                "a comment line inside a wrapped value is dropped by YAML and kept by this reader",
                first_line + offset,
                code="ambiguous-yaml",
            )
        _reject_leading_indicator(stripped, first_line + offset)
        break
    for offset, line in enumerate(lines):
        if ": " in line or line.rstrip().endswith(":"):
            raise FrontmatterError(
                "this line reads as 'key: value' inside a value with no block-scalar "
                "header; YAML parses the whole thing as a nested mapping instead of the "
                "wrapped string it looks like here. Quote the value, or start the block "
                "with a '>' or '|'.",
                first_line + offset,
                code="ambiguous-yaml",
            )


def _unquote(raw: str) -> str:
    """Strip one layer of quoting, mirroring YAML's scalar rules closely enough."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        inner = raw[1:-1]
        if raw[0] == '"':
            return _decode_double_quoted(inner)
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
        # The caller has already reduced a blank line to the empty string. A line
        # that still holds white space is more-indented than the block, and YAML
        # treats that as content, not as a paragraph break.
        if line == "":
            run = 0
            while index < len(lines) and lines[index] == "":
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
        # Trailing white space on a content line is content in YAML, so the fold
        # space is added to it rather than replacing it.
        result.append(separator + line)
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

    # Strip the block's own indentation - the smallest indent of any non-empty line -
    # rather than each line's own leading whitespace. Relative indentation inside the
    # block is content: literal blocks keep it, and folded blocks treat a
    # more-indented line as unfoldable.
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
                "a value has to fit on one line; YAML allows a wrapped plain scalar but "
                "this reader does not. Use a '>' block to wrap.",
                number,
            )

        match = KEY_RE.match(raw)
        if not match:
            raise FrontmatterError(f"cannot read frontmatter line: {raw!r}", number)

        key, rest = match.group(1), (match.group(2) or "").strip()
        rest = _strip_comment(rest)
        _reject_unquotable(key, rest, number)
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
            if rest == "":
                _reject_mapping_like_body(key, collected, number + 1)
            values[key] = _block_scalar(rest, collected)
            key_lines[key] = number
            continue

        values[key] = _unquote(rest)
        key_lines[key] = number
        index += 1

    return Frontmatter(values=values, lines=key_lines, end_line=closing + 1)
