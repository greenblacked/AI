#!/usr/bin/env python3
"""Report the figures and quotations in a generated artefact that no source contains.

This is a lexical check. It asks whether a number or a quoted span appears in the source
text after formatting differences are folded away; it does not ask whether the source
supports the claim the number is used in. A found number can still be attached to the
wrong thing, so the report narrows a human read of the artefact and does not replace it.

Reads one artefact and one or more sources (.md or .txt; a directory is walked for those
extensions). Never writes a file and never touches the network. Every input is checked
before any work starts.

Exit codes: 0 everything found, 1 at least one unsupported item, 2 usage or input error.
Standard library only.
"""

from __future__ import annotations

import argparse
import bisect
import json
import logging
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2
EXTENSIONS = {".md", ".txt"}
DEFAULT_MIN_QUOTE_WORDS = 4

logger = logging.getLogger("check_grounding")

QUOTE_MARKS = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"'})
APOSTROPHES = str.maketrans({"‘": "'", "’": "'", "‚": "'", "′": "'"})
DASHES = str.maketrans(dict.fromkeys("‐‑‒–—―−", "-"))

THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
PERCENT = re.compile(r"(?<=\d)\s*(?:%|percent\b|per cent\b|pct\b)")
# A scale word after a number joins the figure as the short form the sources tend to use,
# so "$4.2 billion" and "$4.2bn" are one figure and "$4.2 billion" is not "$4.2 million".
SCALES = {"thousand": "k", "million": "m", "billion": "bn", "trillion": "tn"}
SCALE_WORD = re.compile(rf"(?<=\d)\s*({'|'.join(SCALES)})\b")
TIMES_SIGN = re.compile(r"(?<=\d)\s*×\s*(?=\d)|(?<=\d)×")
# A spaced dash between two numbers is a range, unless a label word ("figure 3 - 40%")
# shows the first number is a reference rather than a bound.
RANGE_SPACES = re.compile(
    r"(?:(?P<label>\b(?:figure|fig|table|slide|step|section|page|chapter|part|item|chart)\s+))?"
    r"(?P<first>\d+(?:\.\d+)?)(?P<gap>\s*-\s*)(?=\d)"
)
CURRENCY = "$€£¥₹₩₽₺₪₫₱฿₦"
# One number: digits with optional decimals or further dotted parts (1.2.3), a leading
# dot (.5) and an exponent (1e6).
DIGITS = r"\d+(?:\.\d+)*(?:e[-+]?\d+)?"
FIRST = rf"\.?{DIGITS}"
# A unit written with no space: a percent sign, a degree mark, or a run of letters of any
# length (ms, mins, months, Mbps) that may carry digits after its first letter (m2, h30m,
# K60: NFKC turns m² into m2). An ordinal suffix (3rd) is not a unit.
UNIT = r"(?:%|°[^\W\d_]*|[^\W\d_]+(?:\d+[^\W\d_]*)*)"
ORDINAL = r"(?:st|[nr]d|th)(?!\w)"
# A figure: optional sign and currency symbol, a number, an optional unit, then any number
# of range, fraction, date or dimension parts (-, /, x) that each may carry a currency
# symbol and a unit of their own (5ms-10ms, 3/4, 2024-05-12, 1920x1080). A figure that
# ends in an ordinal or runs into more word characters is not one.
NUMBER = re.compile(
    rf"(?<![\w.+±-])[-+±]?[{CURRENCY}]?{FIRST}(?:(?!{ORDINAL}){UNIT})?"
    rf"(?:[-/x][{CURRENCY}]?{DIGITS}(?:(?!{ORDINAL}){UNIT})?)*(?!\w)"
)
# The shape of a figure that is a single range, whose two ends count as supplied. Chains
# of three or more parts (a date) and fractions are kept whole.
TOKEN = re.compile(
    rf"(?P<prefix>[-+±]?[{CURRENCY}]?)(?P<low>{FIRST})(?P<lunit>{UNIT})?"
    rf"(?:-(?P<hprefix>[{CURRENCY}]?)(?P<high>{DIGITS})(?P<hunit>{UNIT})?)?"
)
NEXT_WORD = re.compile(r"\s+([^\W\d_][\w'-]*)")
# A straight double quote directly after a digit is an inch or seconds mark when it would
# open a span, so it is not an opener; it can still close one ("... in 2024").
DOUBLE_QUOTE = re.compile(r'(?<!\d)"((?:[^"\n]|\n(?!\s*\n))+)"')
CURLY_QUOTE = re.compile(r"‘((?:[^‘’\n]|’(?=\w)|\n(?!\s*\n))+?)’(?!\w)")
# An apostrophe before a decade ('90s) is not an opener.
SINGLE_QUOTE = re.compile(r"(?<!\w)'(?!\d\ds\b)((?:[^'\n]|'(?=\w)|\n(?!\s*\n))+?)'(?!\w)")
# Structure that looks like a figure but is not a claim: a list marker (one or two digits at
# the start of a line, so a hard-wrapped "120. Revenue" is kept) or a slide label (not when
# a unit follows, so the verb in "slides 12%" is kept).
LABELS = re.compile(r"^\s*(?:[-*+]\s+)?\d{1,2}[.)]\s+|\bslides?\s+\d+(?:-\d+)?(?![\w%°/]|\.\d)")
# Only a bracket shaped like a citation is dropped from the artefact: one or more file
# names with an optional locator (a section, page, line or #anchor), a numbered reference,
# or a source, section, page, table or figure label with its number. A bracket that holds
# anything else beside a file name, such as [45% of users, survey.md], is a claim and
# stays, as do [n=999] and link text such as [77% of users](url). A bracket in a source
# is never dropped.
FILE_NAME = r"[\w./-]+\.(?:md|txt)\b"
LOCATOR_WORD = r"(?:sections?|sec|pp?|pages?|slides?|tables?|figures?|fig|lines?|chapters?|ch)"
CITATION = re.compile(
    rf"\[\s*{FILE_NAME}(?:\s*,\s*{FILE_NAME})*"
    rf"(?:(?:\s*[,;:]\s*|\s+)?(?:#[\w.-]+|(?:{LOCATOR_WORD}\b\.?\s*)?#?\d[\d\s.,;:-]*))?\s*\](?!\()"
    r"|\[(?:\s*\d+(?:\s*[,;-]\s*\d+)*\s*"
    rf"|\s*(?:sources?|{LOCATOR_WORD})\b\.?\s*#?\d[\d\s.,;-]*)\](?!\()"
)
LINK_TARGET = re.compile(r"(?<=\])\([^)\s]*\)")
EDGE_PUNCTUATION = ".,;:!? "


class InputError(Exception):
    """An input cannot be used; nothing should be reported from it."""


@dataclass(frozen=True)
class NumberHit:
    value: str
    line: int
    context: str


@dataclass(frozen=True)
class QuoteHit:
    quote: str
    line: int


@dataclass(frozen=True)
class Report:
    unsupported_numbers: list[NumberHit]
    unsupported_quotes: list[QuoteHit]
    checked: dict[str, int]

    @property
    def unsupported(self) -> int:
        return len(self.unsupported_numbers) + len(self.unsupported_quotes)


def collapse_range(match: re.Match[str]) -> str:
    if match["label"] and match["gap"] != "-":
        return match.group()
    return f"{match['label'] or ''}{match['first']}-"


def normalise(text: str) -> str:
    """Fold case, width, quote and dash styles, separators and whitespace."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.translate(QUOTE_MARKS).translate(APOSTROPHES).translate(DASHES)
    text = " ".join(text.split())
    text = THOUSANDS.sub("", text)
    text = PERCENT.sub("%", text)
    text = SCALE_WORD.sub(lambda match: SCALES[match[1]], text)
    text = TIMES_SIGN.sub("x", text)
    return RANGE_SPACES.sub(collapse_range, text)


def strip_artefact_labels(line: str) -> str:
    """Drop citation-shaped brackets, link targets, list markers and slide labels."""
    line = CITATION.sub(" ", line)
    return LABELS.sub(" ", LINK_TARGET.sub("", line))


def extract_numbers(text: str, *, artefact: bool = True) -> list[NumberHit]:
    """Numbers with a context word, one hit per occurrence, with 1-based line numbers.

    Labels are stripped from an artefact only: stripping a source can only delete figures
    the artefact is entitled to use.
    """
    hits: list[NumberHit] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = normalise(raw)
        if artefact:
            line = strip_artefact_labels(line)
        for match in NUMBER.finditer(line):
            following = NEXT_WORD.match(line, match.end())
            context = match.group()
            if following:
                context = f"{context} {following.group(1)}"
            hits.append(NumberHit(match.group(), number, context))
    return hits


def extract_quotes(text: str, min_words: int) -> list[QuoteHit]:
    """Quoted spans across the whole artefact, reported at the line each one opens on.

    A span may wrap over single line breaks but not over a blank line, so one stray quote
    mark cannot pair with a mark several paragraphs later.
    """
    lines = [
        unicodedata.normalize("NFKC", raw).lower().translate(QUOTE_MARKS)
        for raw in text.splitlines()
    ]
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    joined = "\n".join(lines)
    found: dict[tuple[int, str], QuoteHit] = {}
    for pattern in (DOUBLE_QUOTE, CURLY_QUOTE, SINGLE_QUOTE):
        for match in pattern.finditer(joined):
            quote = normalise(match.group(1)).strip(EDGE_PUNCTUATION)
            if len(quote.split()) >= min_words:
                line = bisect.bisect_right(starts, match.start())
                found[(match.start(), quote)] = QuoteHit(quote, line)
    return [found[key] for key in sorted(found)]


def number_forms(value: str) -> set[str]:
    """A source number, plus the two ends of a source range, count as supplied.

    A unit written once at the end of a range ("5-10%", "$4-6m") belongs to both ends.
    """
    parts = TOKEN.fullmatch(value)
    if parts is None or parts["high"] is None:
        return {value}
    prefix, low_unit, high_unit = parts["prefix"], parts["lunit"] or "", parts["hunit"] or ""
    low = f"{prefix}{parts['low']}{low_unit or high_unit}"
    high = f"{parts['hprefix'] or prefix}{parts['high']}{high_unit}"
    return {value, low, high}


def source_numbers(sources: list[str]) -> set[str]:
    found: set[str] = set()
    for text in sources:
        for hit in extract_numbers(text, artefact=False):
            found |= number_forms(hit.value)
    return found


def contains_quote(haystack: str, quote: str) -> bool:
    """Whole-word containment, so "he is not ready" is not found in "she is not ready"."""
    return re.search(rf"(?<!\w){re.escape(quote)}(?!\w)", haystack) is not None


def find_unsupported(artefact: str, sources: list[str], min_quote_words: int) -> Report:
    known = source_numbers(sources)
    # Whitespace is collapsed, so a quote that wraps in a source still matches; the
    # newline between sources stops a quote from straddling two of them.
    haystack = "\n".join(normalise(source) for source in sources)
    numbers = extract_numbers(artefact)
    quotes = extract_quotes(artefact, min_quote_words)
    return Report(
        [hit for hit in numbers if hit.value not in known],
        [hit for hit in quotes if not contains_quote(haystack, hit.quote)],
        {"numbers": len(numbers), "quotes": len(quotes), "sources": len(sources)},
    )


def render(report: Report, as_json: bool) -> str:
    if as_json:
        return json.dumps(
            {
                "unsupported_numbers": [asdict(hit) for hit in report.unsupported_numbers],
                "unsupported_quotes": [asdict(hit) for hit in report.unsupported_quotes],
                "checked": report.checked,
            },
            indent=2,
            ensure_ascii=False,
        )
    checked = report.checked
    lines = [
        f"checked {checked['numbers']} numbers and {checked['quotes']} quotes "
        f"against {checked['sources']} sources"
    ]
    if report.unsupported:
        lines.append(f"{'KIND':<8}{'LINE':>5}  ITEM")
    lines += [
        f"{'number':<8}{hit.line:>5}  {hit.value}  ({hit.context})"
        for hit in report.unsupported_numbers
    ]
    lines += [f'{"quote":<8}{hit.line:>5}  "{hit.quote}"' for hit in report.unsupported_quotes]
    lines.append(f"{report.unsupported} unsupported")
    return "\n".join(lines)


def read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise InputError(f"{path} is not valid UTF-8") from None
    except OSError as error:
        raise InputError(f"{path} cannot be read ({type(error).__name__})") from None
    if not text.strip():
        raise InputError(f"{path} is empty")
    return text


def require_text_file(path: Path, role: str) -> None:
    if not path.exists():
        raise InputError(f"{role} {path} does not exist")
    if not path.is_file():
        raise InputError(f"{role} {path} is not a file")
    if path.suffix.lower() not in EXTENSIONS:
        raise InputError(f"{role} {path} must be a .md or .txt file")


def collect_sources(paths: list[Path], artefact: Path) -> list[Path]:
    """Expand directories, drop the artefact itself and repeats, and require at least one."""
    found: dict[Path, None] = {}
    for path in paths:
        if path.is_dir():
            walked = sorted(
                p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS
            )
            if not walked:
                raise InputError(f"no .md or .txt files under {path}")
            candidates = walked
        else:
            require_text_file(path, "source")
            candidates = [path]
        for candidate in candidates:
            found[candidate.resolve()] = None
    found.pop(artefact.resolve(), None)
    if not found:
        raise InputError("no sources left after excluding the artefact itself")
    return list(found)


def setup_logging(level: str) -> None:
    # A named logger, resolved at call time, so the stream is whatever stderr is now.
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List figures and quotations in an artefact that no source contains."
    )
    parser.add_argument("artefact", type=Path, help="the generated artefact's text (.md or .txt)")
    parser.add_argument(
        "--sources", nargs="+", required=True, type=Path, help="source files or directories"
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument(
        "--min-quote-words",
        type=int,
        default=DEFAULT_MIN_QUOTE_WORDS,
        help="shortest quoted span to check, in words (default %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="log threshold, written to stderr",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    try:
        if args.min_quote_words < 1:
            raise InputError("--min-quote-words must be at least 1")
        require_text_file(args.artefact, "artefact")
        source_paths = collect_sources(args.sources, args.artefact)
        artefact = read_text(args.artefact)
        sources = [read_text(path) for path in source_paths]
    except InputError as error:
        logger.error("%s", error)
        return EXIT_USAGE

    logger.info("checking %s against %d sources", args.artefact, len(sources))
    report = find_unsupported(artefact, sources, args.min_quote_words)
    print(render(report, args.json))
    logger.info("%d unsupported items", report.unsupported)
    return EXIT_FINDINGS if report.unsupported else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
