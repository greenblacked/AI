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
    # Clip chomping keeps exactly one trailing newline, as YAML does.
    assert front.values["description"] == "first line second line\n"


def test_reads_a_literal_block_scalar():
    front = parse("---\nname: demo\ndescription: |\n  first\n  second\n---\n")
    assert front.values["description"] == "first\nsecond\n"


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


# The expected strings below were checked against PyYAML's `safe_load` on the same
# input. PyYAML is not imported here: the validator has to run on a bare interpreter,
# and a test that needs a dependency the code does not would quietly undermine that.
@pytest.mark.parametrize(
    ("block", "expected"),
    [
        (">\n  one\n  two\n\n  three", "one two\nthree\n"),
        ("|\n  one\n  two\n\n  three", "one\ntwo\n\nthree\n"),
        (">-\n  one\n  two", "one two"),
        ("|-\n  one\n  two", "one\ntwo"),
        ("|\n  outer\n    indented\n  outer again", "outer\n  indented\nouter again\n"),
        (">\n  single line only", "single line only\n"),
    ],
)
def test_block_scalars_fold_the_way_yaml_folds(block, expected):
    # The 1024-character cap is enforced on this string, so if the folding rules differ
    # from the runtime's the validator polices something nobody ever loads.
    front = parse(f"---\nname: demo\ndescription: {block}\n---\n")
    assert front.values["description"] == expected


def test_a_literal_block_keeps_relative_indentation():
    front = parse("---\nname: demo\ndescription: |\n  a\n      deep\n  b\n---\n")
    assert front.values["description"] == "a\n    deep\nb\n"
