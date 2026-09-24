"""The parser is stricter than YAML on purpose; these tests pin down where."""

from __future__ import annotations

import json
from pathlib import Path

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
        # The old message said "must be a flat key/value block", which misdescribed
        # a block that is flat. The real rule is that a value stays on one line.
        ("---\n  name: demo\n---\n", "one line"),
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


# These were verified against PyYAML across ~11,500 generated shapes; the folded cases
# below are the ones the first implementation got wrong.
@pytest.mark.parametrize(
    ("block", "expected"),
    [
        (">\n  one\n    two\n  three", "one\n  two\nthree\n"),
        (">\n  one\n\n    deep\n\n  two", "one\n\n  deep\n\ntwo\n"),
        (">\n  a\n  b\n\n    c", "a b\n\n  c\n"),
        # Uniform indentation is the block's own indent, so neither line is
        # more-indented and the blank folds to a single newline.
        (">\n    deep\n\n    also", "deep\nalso\n"),
        (">+\n  yy\n    ind\n", "yy\n  ind\n\n"),
        ("|+\n  ", "\n"),
    ],
)
def test_more_indented_lines_are_not_folded(block, expected):
    # YAML keeps a more-indented line literal and does not fold the breaks around it.
    # Folding them produced a shorter string than the runtime loads, which meant the
    # 1024-character cap was measured against the wrong thing.
    front = parse(f"---\nname: demo\ndescription: {block}\n---\n")
    assert front.values["description"] == expected


@pytest.mark.parametrize(
    "text",
    [
        "---\nname: demo\ndescription: the answer is: red\n---\n",
        "---\nname: demo\ndescription: trailing colon:\n---\n",
        "---\nname:demo\n---\n",
    ],
)
def test_input_a_real_yaml_parser_rejects_is_rejected_here(text):
    # Accepting these meant `--strict` was green on a file the runtime and the upload
    # API cannot parse, which is the opposite of what a stricter-than-YAML reader is for.
    with pytest.raises(FrontmatterError):
        parse(text)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("see https://example.com/x", "see https://example.com/x"),
        ("at 10:30 sharp", "at 10:30 sharp"),
        ('"quoted: fine"', "quoted: fine"),
    ],
)
def test_a_colon_that_yaml_accepts_is_still_accepted(value, expected):
    front = parse(f"---\nname: demo\ndescription: {value}\n---\n")
    assert front.values["description"] == expected


# Each of these validated clean before the parser learned to reject them, and each was
# confirmed against PyYAML's `safe_load` to either raise or read as something other than
# the plain string this reader used to hand back — a mapping, a list, or a scanner error.
@pytest.mark.parametrize(
    "text",
    [
        # PyYAML reads this as {"description": {"Use when": "xxx"}}, not a two-line
        # string — the divergence this validator exists to catch.
        "---\nname: demo\ndescription:\n  Use when: xxx\n---\n",
        # PyYAML raises ScannerError: sequence entries are not allowed here.
        "---\nname: demo\ndescription: - Use when foo\n---\n",
        # PyYAML reads this as {"description": ["x"]}, a list rather than a string.
        "---\nname: demo\ndescription: [x]\n---\n",
        "---\nname: demo\ndescription: {a: b}\n---\n",
        # An anchor: PyYAML reads "bar" for this, discarding "&foo" as a node label.
        "---\nname: demo\ndescription: &foo bar\n---\n",
        # Not a block-scalar header; PyYAML raises ScannerError scanning a block scalar.
        "---\nname: demo\ndescription: >=1.0\n---\n",
        "---\nname: demo\ndescription: |not-a-header\n---\n",
        # A later block-content line reading as a mapping key is a scanner error too,
        # not merely the first line.
        "---\nname: demo\ndescription:\n  first line\n  second: line\n---\n",
        # YAML does not care which physical line a node starts on: each of these three
        # is exactly as ambiguous on the first line of a wrapped, indicator-less value
        # as it is written on the key's own line.
        # PyYAML reads this as {"description": ["foo"]}, a one-item list.
        "---\nname: demo\ndescription:\n  - foo\n---\n",
        # PyYAML reads this as {"description": ["x"]}, a one-item list.
        "---\nname: demo\ndescription:\n  [x]\n---\n",
        # PyYAML reads this as {"description": None}: the whole value is a comment.
        "---\nname: demo\ndescription:\n  # foo\n---\n",
    ],
)
def test_a_value_a_real_yaml_parser_reads_differently_is_rejected_here(text):
    with pytest.raises(FrontmatterError) as caught:
        parse(text)
    assert caught.value.code == "ambiguous-yaml"


@pytest.mark.parametrize("header", ["|2", ">2", "|1-", "|-1", "|+1", "|1+"])
def test_an_explicit_indentation_indicator_names_itself_rather_than_calling_it_invalid(
    header,
):
    # PyYAML accepts every one of these; this reader still rejects them; the message
    # said "fails to parse the rest of the line" either way, which is wrong for a header
    # that a real parser resolves just fine — this reader simply does not implement it.
    with pytest.raises(FrontmatterError) as caught:
        parse(f"---\nname: demo\ndescription: {header}\n---\n")
    assert caught.value.code == "ambiguous-yaml"
    assert "not supported" in caught.value.message
    assert "fails to parse" not in caught.value.message


def test_a_paths_block_sequence_is_not_flagged_as_a_first_line_sequence_entry():
    # `paths:` is the one key whose block form legitimately starts every line with
    # `- `; the first-line check that catches `description:\n  - foo` must not also
    # catch this.
    front = parse('---\npaths:\n  - "a/**"\n  - "b/**"\n---\n')
    assert "paths" in front.values


def test_a_paths_block_sequence_may_open_with_an_explanatory_comment():
    # `_rule_globs` skips a `#` line the same way when it scans this block for globs, so
    # a comment ahead of the list is not ambiguous - merely delayed by one line.
    front = parse('---\npaths:\n  # only the validator reads this key\n  - "src/**"\n---\n')
    assert "paths" in front.values


def test_a_paths_dash_on_the_keys_own_line_is_still_a_scanner_error():
    # `paths: - "a/**"` is not shorthand for the block form: a real parser raises
    # ScannerError on it. Only `_reject_mapping_like_body`'s exemption, which applies to
    # the lines the block form actually occupies, may accept a leading `- `.
    with pytest.raises(FrontmatterError) as caught:
        parse('---\npaths: - "a/**"\n---\n')
    assert caught.value.code == "ambiguous-yaml"


def test_a_comment_line_in_a_wrapped_value_gets_its_own_message():
    # Dropped by YAML rather than read as any kind of node, so it is not filed under the
    # same "flow collection, anchor, alias..." wording the other leading characters share.
    with pytest.raises(FrontmatterError) as caught:
        parse("---\nname: demo\ndescription:\n  # foo\n---\n")
    assert caught.value.code == "ambiguous-yaml"
    assert "dropped by YAML" in caught.value.message
    assert "flow collection" not in caught.value.message


def test_a_wrapped_value_starting_with_ordinary_prose_is_still_accepted():
    front = parse("---\nname: demo\ndescription:\n  first line\n  second line\n---\n")
    assert front.values["description"] == "first line second line\n"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # A dash not followed by a space is an ordinary plain scalar in YAML, not a
        # sequence entry.
        ("-1", "-1"),
        ("-a", "-a"),
        # Quoting sidesteps every one of the ambiguous-leading-character cases.
        ('"[x]"', "[x]"),
        ("'[x]'", "[x]"),
    ],
)
def test_a_leading_character_yaml_accepts_as_plain_is_still_accepted(value, expected):
    front = parse(f"---\nname: demo\ndescription: {value}\n---\n")
    assert front.values["description"] == expected


def test_a_colon_inside_an_explicit_block_scalar_is_not_ambiguous():
    # Unlike the implicit, indicator-less form, an explicit `>` or `|` block's content is
    # never read as a nested mapping — YAML treats every line as literal or foldable text.
    front = parse("---\nname: demo\ndescription: |\n  a: b\n---\n")
    assert front.values["description"] == "a: b\n"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (r'"tab\there"', "tab\there"),
        (r'"line\nbreak"', "line\nbreak"),
        (r'"back\\slash"', "back\\slash"),
    ],
)
def test_double_quoted_escapes_are_decoded(raw, expected):
    # The 1024-character cap is measured on this decoded string; before this, \t and \n
    # were left as the two literal source characters, so the cap policed the wrong string.
    front = parse(f"---\nname: demo\ndescription: {raw}\n---\n")
    assert front.values["description"] == expected


def test_a_unicode_escape_is_decoded():
    # Built from chr() rather than typed as a literal \u escape in this file, so nothing
    # between here and the interpreter can pre-decode it and make the test pass without
    # exercising the parser's own \u handling at all.
    backslash = chr(92)
    raw = '"smile ' + backslash + 'u263a"'
    front = parse("---\nname: demo\ndescription: " + raw + "\n---\n")
    assert front.values["description"] == "smile " + chr(0x263A)


def test_an_unrecognised_or_truncated_escape_is_left_verbatim():
    # A backslash followed by something that is not one of the escapes this reader
    # decodes is passed through rather than guessed at: better an unchanged `\z` or a
    # truncated `\u12` than a wrong character silently substituted for it.
    backslash = chr(92)
    not_hex = '"' + backslash + "u12zz" + '"'
    front = parse("---\nname: demo\ndescription: " + not_hex + "\n---\n")
    assert front.values["description"] == backslash + "u12zz"

    truncated = '"' + backslash + "u12" + '"'
    front = parse("---\nname: demo\ndescription: " + truncated + "\n---\n")
    assert front.values["description"] == backslash + "u12"

    unknown = '"' + backslash + "z" + '"'
    front = parse("---\nname: demo\ndescription: " + unknown + "\n---\n")
    assert front.values["description"] == backslash + "z"


def test_an_inline_comment_is_dropped_as_yaml_drops_it():
    # Keeping it made the length and angle-bracket checks measure a string the runtime
    # never sees, and produced a bogus name-mismatch.
    front = parse("---\nname: demo  # the skill name\ndescription: A thing.  # TODO\n---\n")
    assert front.values == {"name": "demo", "description": "A thing."}


def _block_scalar_cases():
    path = Path(__file__).parent / "fixtures" / "block_scalars.json"
    for case in json.loads(path.read_text(encoding="utf-8")):
        label = case["indicator"] + " " + json.dumps(case["lines"])
        yield pytest.param(case["indicator"], case["lines"], case["expected"], id=label)


@pytest.mark.parametrize(("indicator", "lines", "expected"), list(_block_scalar_cases()))
def test_every_recorded_block_scalar_resolves_as_pyyaml_resolves_it(indicator, lines, expected):
    # The fixture was produced by tests/fixtures/generate_block_scalars.py, which asks
    # PyYAML for the answer to every combination of indicator and body it knows about
    # and refuses to write the file while this parser disagrees with any of them. The
    # cases replay here so the guarantee holds without PyYAML installed.
    text = "---\nname: demo\ndescription: " + indicator + "\n" + "\n".join(lines) + "\n---\n"
    assert parse(text).values["description"] == expected
