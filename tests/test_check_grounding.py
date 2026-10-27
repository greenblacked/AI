"""The grounding checker: what it finds, what formatting it forgives, and how it exits."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/llm/skills/source-grounded-prompts/scripts/check_grounding.py"

spec = importlib.util.spec_from_file_location("check_grounding", SCRIPT)
assert spec is not None
assert spec.loader is not None
grounding = importlib.util.module_from_spec(spec)
sys.modules["check_grounding"] = grounding
spec.loader.exec_module(grounding)


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = grounding.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def check(
    tmp_path: Path, artefact: str, source: str, capsys: pytest.CaptureFixture[str], *extra: str
) -> tuple[int, str, str]:
    art = write(tmp_path, "deck.md", artefact)
    src = write(tmp_path / "sources", "paper.md", source)
    return run([str(art), "--sources", str(src), *extra], capsys)


def report_of(
    tmp_path: Path, artefact: str, source: str, capsys: pytest.CaptureFixture[str], *extra: str
) -> dict:
    code, out, _ = check(tmp_path, artefact, source, capsys, "--json", *extra)
    assert code in {0, 1}
    return json.loads(out)


def values(report: dict) -> list[str]:
    return [item["value"] for item in report["unsupported_numbers"]]


# --- numbers -----------------------------------------------------------------------------


def test_a_number_present_in_a_source_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(tmp_path, "Revenue grew 12 percent.\n", "Revenue grew 12 percent.", capsys)
    assert code == 0
    assert "0 unsupported" in out


def test_a_number_missing_from_every_source_is_reported_with_its_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "Intro\n\nChurn fell to 7 students.\n", "Churn fell.", capsys)
    assert report["unsupported_numbers"] == [{"value": "7", "line": 3, "context": "7 students"}]


def test_exit_code_is_one_when_anything_is_unsupported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(tmp_path, "We sold 99 units.", "We sold some units.", capsys)
    assert code == 1
    assert "99" in out


@pytest.mark.parametrize(
    ("artefact", "source"),
    [
        ("1,200 users", "1200 users"),
        ("1200 users", "1,200 users"),
        ("45% of users", "45 percent of users"),
        ("45 percent of users", "45% of users"),
        ("45 % of users", "45 per cent of users"),
        ("3.5 hours", "3.5 hours"),
        ("in 2021", "In 2021 the team"),
        ("12–15 weeks", "12-15 weeks"),
        ("12-15 weeks", "12—15 weeks"),
        ("12 – 15 weeks", "12-15 weeks"),
    ],
)
def test_formatting_differences_do_not_cause_false_alarms(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], artefact: str, source: str
) -> None:
    code, out, _ = check(tmp_path, artefact, source, capsys)
    assert code == 0, out


def test_a_number_is_matched_as_a_token_not_as_a_substring(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, "Only 12 cases.", "There were 120 cases and 3.12 versions.", capsys
    )
    assert values(report) == ["12"]


def test_a_range_missing_from_the_sources_is_reported_as_one_item(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "Plan for 12–15 weeks.", "Plan for 12 weeks.", capsys)
    assert values(report) == ["12-15"]


def test_a_percentage_is_not_supported_by_the_bare_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "Up 45% overall.", "There were 45 cases.", capsys)
    assert values(report) == ["45%"]


def test_citation_brackets_and_slide_labels_are_not_treated_as_figures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = "## Slide 4\n1. Latency fell [paper.md, section 2.3]\n"
    code, out, _ = check(tmp_path, artefact, "Latency fell.", capsys)
    assert code == 0, out


def test_a_number_is_found_in_any_one_of_several_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.md", "Seen 31 times and 8 times.")
    one = write(tmp_path / "s", "one.md", "Seen 31 times.")
    two = write(tmp_path / "s", "two.txt", "Seen 8 times.")
    code, out, _ = run([str(art), "--sources", str(one), str(two)], capsys)
    assert code == 0, out


# --- quotes ------------------------------------------------------------------------------


def test_a_quote_found_in_a_source_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(
        tmp_path,
        'As the author put it, "the model forgets what it was never shown".',
        "Notes: the model forgets what it was never shown, and that is fine.",
        capsys,
    )
    assert code == 0, out


def test_an_invented_quote_is_reported_with_its_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, 'Title\n"we always ship on time" said the lead.\n', "Nothing here.", capsys
    )
    assert report["unsupported_quotes"] == [{"quote": "we always ship on time", "line": 2}]


def test_curly_and_straight_quotes_and_apostrophes_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(
        tmp_path,
        "“it’s the first time we’ve seen it”",
        "He said \"it's the first time we've seen it\" twice.",
        capsys,
    )
    assert code == 0, out


def test_a_quote_may_span_a_line_break_in_the_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(
        tmp_path,
        '"retrieval quality sets the ceiling for answers"',
        "Retrieval quality\nsets the   ceiling\nfor answers.\n",
        capsys,
    )
    assert code == 0, out


def test_quotes_shorter_than_the_minimum_are_ignored_and_the_minimum_is_adjustable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = 'The "so-called gap" remains.'
    assert check(tmp_path, artefact, "Nothing.", capsys)[0] == 0
    code, out, _ = check(tmp_path, artefact, "Nothing.", capsys, "--min-quote-words", "2")
    assert code == 1
    assert "so-called gap" in out


def test_trailing_punctuation_inside_a_quote_does_not_cause_a_miss(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(
        tmp_path,
        '"a clear finding about the data."',
        "A clear finding about the data, then more.",
        capsys,
    )
    assert code == 0, out


# --- sources and output ------------------------------------------------------------------


def test_a_directory_of_sources_is_walked_for_markdown_and_text_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.md", "Totals: 11 and 22 and 33.")
    sources = tmp_path / "sources"
    write(sources, "a.md", "eleven is 11")
    write(sources, "nested/b.txt", "twenty-two is 22")
    write(sources, "c.csv", "33")
    code, out, _ = run([str(art), "--sources", str(sources), "--json"], capsys)
    assert code == 1
    assert json.loads(out)["checked"]["sources"] == 2
    assert [item["value"] for item in json.loads(out)["unsupported_numbers"]] == ["33"]


def test_the_artefact_is_not_counted_as_its_own_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = tmp_path / "sources"
    art = write(sources, "deck.md", "We saw 77 cases.")
    write(sources, "paper.md", "We saw cases.")
    code, out, _ = run([str(art), "--sources", str(sources), "--json"], capsys)
    assert code == 1
    assert json.loads(out)["checked"]["sources"] == 1


def test_json_output_has_the_documented_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, 'Rose 5 points: "a quote nobody ever wrote down".', "Rose.", capsys
    )
    assert set(report) == {"unsupported_numbers", "unsupported_quotes", "checked"}
    assert report["checked"] == {"numbers": 1, "quotes": 1, "sources": 1}
    assert set(report["unsupported_numbers"][0]) == {"value", "line", "context"}
    assert set(report["unsupported_quotes"][0]) == {"quote", "line"}


def test_json_output_for_a_clean_artefact_is_empty_lists_and_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(tmp_path, "Rose 5 points.", "Rose 5 points.", capsys, "--json")
    assert code == 0
    assert json.loads(out)["unsupported_numbers"] == []


def test_logs_go_to_stderr_with_a_timestamp_and_level(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, err = check(tmp_path, "Rose 5.", "Rose 5.", capsys, "--log-level", "INFO")
    assert "INFO" in err
    assert err.split()[0][:2] == "20"
    assert "INFO" not in out


# --- exit code 2 -------------------------------------------------------------------------


def test_missing_artefact_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = write(tmp_path, "paper.md", "text")
    code, out, err = run([str(tmp_path / "nope.md"), "--sources", str(src)], capsys)
    assert code == 2
    assert out == ""
    assert "nope.md" in err


def test_missing_source_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.md", "text")
    code, _, err = run([str(art), "--sources", str(tmp_path / "gone.md")], capsys)
    assert code == 2
    assert "gone.md" in err


def test_no_sources_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    art = write(tmp_path, "deck.md", "text")
    with pytest.raises(SystemExit) as raised:
        grounding.main([str(art), "--sources"])
    assert raised.value.code == 2


def test_a_directory_with_no_readable_sources_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.md", "text")
    empty = tmp_path / "empty"
    write(empty, "notes.csv", "1,2,3")
    code, _, err = run([str(art), "--sources", str(empty)], capsys)
    assert code == 2
    assert "no .md or .txt" in err


def test_a_file_that_is_not_utf8_is_a_usage_error_and_nothing_is_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.md", "text 5")
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"caf\xe9 5")
    code, out, err = run([str(art), "--sources", str(bad)], capsys)
    assert code == 2
    assert out == ""
    assert "UTF-8" in err


def test_a_wrong_extension_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    art = write(tmp_path, "deck.pdf", "text")
    src = write(tmp_path, "paper.md", "text")
    code, _, err = run([str(art), "--sources", str(src)], capsys)
    assert code == 2
    assert ".md or .txt" in err


def test_an_empty_artefact_or_source_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = write(tmp_path, "paper.md", "text")
    art = write(tmp_path, "deck.md", "  \n")
    assert run([str(art), "--sources", str(src)], capsys)[0] == 2
    art = write(tmp_path, "deck.md", "text 4")
    blank = write(tmp_path, "blank.md", "\n")
    assert run([str(art), "--sources", str(blank)], capsys)[0] == 2


def test_a_zero_minimum_quote_length_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = check(tmp_path, "text", "text", capsys, "--min-quote-words", "0")
    assert code == 2
    assert "min-quote-words" in err


def test_nothing_is_written_anywhere(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    art = write(tmp_path, "deck.md", 'Up 9: "an invented sentence of words".')
    src = write(tmp_path / "sources", "paper.md", "Nothing.")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    run([str(art), "--sources", str(src)], capsys)
    run([str(art), "--sources", str(src), "--json"], capsys)
    run([str(art), "--sources", str(tmp_path / "gone")], capsys)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


# --- pure functions ----------------------------------------------------------------------


def test_normalise_folds_case_width_whitespace_quotes_dashes_and_separators() -> None:
    assert grounding.normalise("  \uff21\uff22  \u201cX\u201d\n\u2013 1,200  ") == 'ab "x" - 1200'


def test_the_ends_of_a_source_range_count_as_supplied(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(
        tmp_path, "At most 15 weeks, up to 20%.", "Plan 12-15 weeks, 10-20% slack.", capsys
    )
    assert code == 0, out


def test_extract_numbers_reports_context_and_line() -> None:
    found = grounding.extract_numbers("a\nGrew 45 percent in 2020\n")
    assert [(n.value, n.line, n.context) for n in found] == [
        ("45%", 2, "45% in"),
        ("2020", 2, "2020"),
    ]


# --- review fixes: units and signs, wrapped quotes, brackets, boundaries ---------------------


@pytest.mark.parametrize(
    ("figure", "token"),
    [
        ("3x faster", "3x"),
        ("raised $9.7M last year", "$9.7m"),
        ("a 40ms budget", "40ms"),
        ("about 250k users", "250k"),
        ("down -45% overall", "-45%"),
        ("up +12% overall", "+12%"),
        ("over 10K users", "10k"),
    ],
)
def test_a_figure_with_a_unit_or_sign_attached_is_extracted_and_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], figure: str, token: str
) -> None:
    report = report_of(tmp_path, f"We saw {figure}.", "Nothing numeric here.", capsys)
    assert values(report) == [token]
    code, out, _ = check(tmp_path, f"We saw {figure}.", f"Notes: {figure}.", capsys)
    assert code == 0, out


def test_a_unit_figure_is_not_supported_by_the_bare_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "A 3x gain.", "There were 3 cases.", capsys)
    assert values(report) == ["3x"]


def test_ordinals_are_not_figures(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = check(tmp_path, "The 3rd and 21st items.", "Nothing numeric.", capsys)
    assert code == 0, out


def test_a_quote_wrapped_across_lines_in_the_artefact_is_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = 'Intro\nHe said "this changes absolutely everything\nabout how we treat people".\n'
    report = report_of(tmp_path, artefact, "Nothing here.", capsys)
    assert report["unsupported_quotes"] == [
        {"quote": "this changes absolutely everything about how we treat people", "line": 2}
    ]


def test_an_unpaired_quote_does_not_shift_pairing_in_later_paragraphs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = 'A 5" pipe.\n\nLater: "an invented sentence of words" appears.\n'
    report = report_of(tmp_path, artefact, "Nothing here.", capsys)
    assert report["unsupported_quotes"] == [{"quote": "an invented sentence of words", "line": 3}]


def test_single_curly_quotation_marks_delimit_a_quote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, "She said ‘this changes absolutely everything about care’ today.", "None.", capsys
    )
    assert [q["quote"] for q in report["unsupported_quotes"]] == [
        "this changes absolutely everything about care"
    ]
    code, out, _ = check(
        tmp_path,
        "She said ‘it’s what the team’s data shows today’.",
        "It's what the team's data shows today, she said.",
        capsys,
    )
    assert code == 0, out


def test_straight_single_quotes_delimit_a_quote_only_outside_words(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, "She said 'this changes absolutely everything about care' today.", "None.", capsys
    )
    assert [q["quote"] for q in report["unsupported_quotes"]] == [
        "this changes absolutely everything about care"
    ]
    plain = report_of(
        tmp_path, "The team's plan isn't what the user's data shows at all.", "None.", capsys
    )
    assert plain["checked"]["quotes"] == 0


def test_bracketed_claims_and_link_text_in_the_artefact_are_still_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = "See [77% of users](https://example.org/a/2021) and Results [n=999].\n"
    report = report_of(tmp_path, artefact, "Nothing numeric.", capsys)
    assert values(report) == ["77%", "999"]


@pytest.mark.parametrize(
    "citation",
    ["[1]", "[1, 2]", "[source 2]", "[section 2.3]", "[paper.md, section 2.3]", "[p. 14]"],
)
def test_citation_shaped_brackets_are_not_figures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], citation: str
) -> None:
    code, out, _ = check(tmp_path, f"Latency fell {citation}.", "Latency fell.", capsys)
    assert code == 0, out


def test_brackets_in_a_source_are_never_stripped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = (
        "[Table 3: 312 controls, 18% dropout]\n\nThe interval [0, 1) holds.\n\n"
        "Then 62% and 840 appear [2] here."
    )
    code, out, _ = check(tmp_path, "312 controls, 18% dropout, 62% and 840.", source, capsys)
    assert code == 0, out


def test_a_quote_must_match_at_word_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(
        tmp_path, 'He wrote "he is not ready for this".', "She is not ready for this.", capsys
    )
    assert len(report["unsupported_quotes"]) == 1


def test_a_label_word_before_a_spaced_dash_is_not_a_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = check(tmp_path, "Figure 3 - 40% of users", "40% of users, Figure 3.", capsys)
    assert code == 0, out
    report = report_of(tmp_path, "Plan 12 - 15 weeks", "Plan 12 weeks.", capsys)
    assert values(report) == ["12-15"]


# --- second review: unit length, scale words, quote marks after digits, token shapes ------------

PHRASE = "we will double headcount next year"


def flagged(
    tmp_path: Path, artefact: str, source: str, capsys: pytest.CaptureFixture[str]
) -> tuple[list[str], list[str]]:
    report = report_of(tmp_path, artefact, source, capsys)
    return values(report), [item["quote"] for item in report["unsupported_quotes"]]


@pytest.mark.parametrize(
    ("artefact", "source", "numbers"),
    [
        # An attached unit of any length is part of the figure.
        (
            "100Mbps, 40mins, 18months, 5Gbps",
            "Nothing here.",
            ["100mbps", "40mins", "18months", "5gbps"],
        ),
        ("100Mbps", "a link of 100 Mbps", ["100mbps"]),
        ("1920x1080", "1920x1081", ["1920x1080"]),
        ("20°C", "25°C", ["20°c"]),
        # A scale word is folded into the figure, so magnitudes compare.
        ("$4.2 billion", "$4.2 million", ["$4.2bn"]),
        ("1.5 billion", "1,500,000,000", ["1.5bn"]),
        ("4-6 million", "4 million to 6 million", ["4-6m"]),
        # Currency symbols beyond the dollar, euro and pound.
        ("¥500", "500", ["¥500"]),
        ("₹40", "40", ["₹40"]),
        # Scientific notation, fractions, dates and dotted numbers stay whole.
        ("1e6", "1e7", ["1e6"]),
        ("3/4", "3/5", ["3/4"]),
        ("3/4", "3 and 4", ["3/4"]),
        ("2024-05-12", "2024-05-13", ["2024-05-12"]),
        ("12/05/2024", "12/05/2025", ["12/05/2024"]),
        ("1.2.3", "1.2.4", ["1.2.3"]),
        (".5 points", ".6 points", [".5"]),
        ("5ms-10ms", "5ms and 11ms", ["5ms-10ms"]),
    ],
)
def test_a_changed_figure_is_reported_in_its_whole_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    artefact: str,
    source: str,
    numbers: list[str],
) -> None:
    assert flagged(tmp_path, artefact, source, capsys) == (numbers, [])


@pytest.mark.parametrize(
    ("artefact", "source"),
    [
        ("$4.2 million", "$4.2M"),
        ("5 thousand users", "5k users"),
        ("2 trillion", "2tn"),
        ("3 thousandth", "3 thousandth"),
        ("The 3rd, 21st and 12th place", "none"),
        ("1920x1080 and 10×10", "1920x1080 and 10x10"),
        ("20°C", "20°C"),
        ("¥500 and ₹2,000", "¥500 and ₹2000"),
        ("1e6 rows and 1.5e3", "1e6 rows and 1.5e3"),
        ("3/4 of users", "3/4 of users"),
        ("5ms-10ms and 100k-200k", "5ms-10ms and 100k-200k"),
        ("10%", "10-20%"),
        ("4m", "4-6 million"),
    ],
)
def test_the_same_figure_in_another_format_is_not_a_false_alarm(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], artefact: str, source: str
) -> None:
    code, out, _ = check(tmp_path, artefact, source, capsys)
    assert code == 0, out


def test_a_range_end_with_a_shared_scale_word_counts_as_supplied(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert flagged(tmp_path, "$6m", "$4-6 million", capsys) == ([], [])
    assert flagged(tmp_path, "$5m", "$4-6 million", capsys) == (["$5m"], [])


def test_an_inch_mark_after_a_digit_is_not_a_quote_delimiter(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = f'Each desk gets 27" screens. "{PHRASE}," she said.'
    got = flagged(tmp_path, artefact, "Each desk gets 27 screens.", capsys)
    assert got == ([], [PHRASE])
    artefact = f'A 27" screen. Later "{PHRASE}" was said.'
    assert flagged(tmp_path, artefact, "A 27 screen.", capsys) == ([], [PHRASE])


def test_foot_and_inch_marks_do_not_hide_a_quote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = "The 6' pole and a 5'11\" tall man."
    artefact = f'{source} "{PHRASE}" he said.'
    assert flagged(tmp_path, artefact, source, capsys) == ([], [PHRASE])


def test_a_closing_quote_after_a_digit_still_closes_a_quote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = f'She said "the plan starts again in 2024" then left. Then "{PHRASE}" too.'
    assert flagged(tmp_path, artefact, "None.", capsys)[1] == [
        "the plan starts again in 2024",
        PHRASE,
    ]


def test_a_decade_apostrophe_does_not_open_a_quote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = f"The '90s were odd, and she said '{PHRASE}' to us."
    source = f"She said '{PHRASE}' to us. The 90s were odd."
    assert flagged(tmp_path, artefact, source, capsys)[1] == []


def test_a_bracket_with_a_file_name_and_a_claim_is_still_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert flagged(tmp_path, "[45% of users, survey.md]", "Nothing.", capsys) == (["45%"], [])
    assert flagged(tmp_path, "[survey.md, 45% of users]", "Nothing.", capsys) == (["45%"], [])


@pytest.mark.parametrize(
    "citation",
    ["[paper.md]", "[paper.md:12]", "[paper.md#sec-2]", "[a/b.txt, section 2.3]", "[a.md, b.md]"],
)
def test_a_file_name_with_only_a_locator_is_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], citation: str
) -> None:
    code, out, _ = check(tmp_path, f"Latency fell {citation}.", "Latency fell.", capsys)
    assert code == 0, out


@pytest.mark.parametrize(
    ("artefact", "source", "quotes"),
    [
        (f"“{PHRASE}”", "other", [PHRASE]),
        (f"‘{PHRASE}’", "other", [PHRASE]),
        (
            'He said "we will leave.\n\nThen "a plan that reduces cost today" for all.',
            "x",
            ["a plan that reduces cost today"],
        ),
        (
            "\"she said 'we will never agree to this' and left\"",
            "other",
            ["she said 'we will never agree to this' and left", "we will never agree to this"],
        ),
        ('"We will double\nheadcount next year"', "other", [PHRASE]),
    ],
)
def test_every_quote_style_is_checked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    artefact: str,
    source: str,
    quotes: list[str],
) -> None:
    assert flagged(tmp_path, artefact, source, capsys) == ([], quotes)


@pytest.mark.parametrize(
    "artefact",
    [
        "v1.2.3 and Q3 revenue",
        "US$5 and 5 USD",
        '"We will double\n\nheadcount next year"',
    ],
)
def test_documented_limits_stay_silent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], artefact: str
) -> None:
    # These are named under "Not reported" in references/diagnosis.md; if one starts being
    # reported, that page needs to change with it.
    assert flagged(tmp_path, artefact, "5 users, v1.2.4, Q4 revenue.", capsys) == ([], [])


# --- third review: units followed by digits, the label heuristic, plus-minus -------------------


@pytest.mark.parametrize(
    ("artefact", "source", "token"),
    [
        ("Floor area 1200m² here", "Floor area 900m² here", "1200m2"),
        ("Volume 30km³ total", "Volume 20km³ total", "30km3"),
        ("Floor area 1200m2 here", "Floor area 900m2 here", "1200m2"),
        ("Runs 1h30 long", "Runs 2h15 long", "1h30"),
        ("Runs 1h30m long", "Runs 2h15m long", "1h30m"),
        ("Mode 4K60 only", "Mode 4K30 only", "4k60"),
        ("About ±3% error", "About 3% error", "±3%"),
    ],
)
def test_a_unit_followed_by_a_digit_still_yields_the_figure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    artefact: str,
    source: str,
    token: str,
) -> None:
    assert values(report_of(tmp_path, artefact, source, capsys)) == [token]
    code, out, _ = check(tmp_path, artefact, artefact, capsys)
    assert code == 0, out


def test_a_slide_word_followed_by_a_unit_is_a_claim_not_a_label(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "Market share slides 12% year on year.", "Nothing.", capsys)
    assert values(report) == ["12%"]
    code, out, _ = check(tmp_path, "See slide 12.\n## Slide 4", "Nothing.", capsys)
    assert code == 0, out


def test_only_a_one_or_two_digit_number_is_a_list_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = report_of(tmp_path, "Sales reached\n120. Revenue grew.", "Nothing.", capsys)
    assert values(report) == ["120"]
    code, out, _ = check(tmp_path, "7. Revenue grew.\n12) Costs fell.", "Nothing.", capsys)
    assert code == 0, out
