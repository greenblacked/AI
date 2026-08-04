"""The parser is stricter than YAML on purpose; these tests pin down where."""

from __future__ import annotations

import pytest

from skillcheck.frontmatter import FrontmatterError, parse


def test_reads_a_plain_block():
    front = parse("---\nname: demo\ndescription: Does a thing.\n---\n\n# Demo\n")
    assert front.values == {"name": "demo", "description": "Does a thing."}
    assert front.line_of("description") == 3
    assert front.end_line == 4


def test_strips_one_layer_of_quoting():
    front = parse('---\nname: demo\ndescription: "Use when \\"x\\" happens."\n---\n')
    assert front.values["description"] == 'Use when "x" happens.'


def test_reads_a_folded_block_scalar():
    front = parse("---\nname: demo\ndescription: >\n  first line\n  second line\n---\n")
    assert front.values["description"] == "first line second line"


def test_reads_a_literal_block_scalar():
    front = parse("---\nname: demo\ndescription: |\n  first\n  second\n---\n")
    assert front.values["description"] == "first\nsecond"


def test_ignores_comments_and_blank_lines():
    front = parse("---\n# a note\n\nname: demo\n---\n")
    assert front.values == {"name": "demo"}


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("name: demo\n", "must start with '---'"),
        ("﻿---\nname: demo\n---\n", "byte-order mark"),
        ("---\nname: demo\n", "never closed"),
        ("---\nname: demo\nname: other\n---\n", "duplicate"),
        ("---\nname:\tdemo\n---\n", "tab"),
        ("---\n  name: demo\n---\n", "indentation"),
        ("---\nnot a mapping line\n---\n", "cannot read"),
    ],
)
def test_rejects_malformed_blocks(text, fragment):
    with pytest.raises(FrontmatterError) as caught:
        parse(text)
    assert fragment in caught.value.message
