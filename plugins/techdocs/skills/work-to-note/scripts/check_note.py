#!/usr/bin/env python3
"""Check a Markdown note against a notes vault's frontmatter, evidence and link rules.

Reads the notes named on the command line (and, with --vault, the vault's file names and
folder indexes) and never writes. Every input is validated before the first note is
reported, so a half-read set cannot produce a half-trusted report.

Exit codes: 0 clean (warnings allowed), 1 errors found, 2 an input is unusable.
Standard library only; no network.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger("check_note")

# One decision in one place: every rule's severity and its fixed summary live here. The
# checks below only name a rule and supply the detail that differs from case to case.
RULES: dict[str, tuple[str, str]] = {
    "frontmatter-syntax": ("error", "the frontmatter cannot be read"),
    "field-missing": ("error", "a required frontmatter field is absent"),
    "field-empty": ("error", "a required frontmatter field is empty"),
    "type-invalid": ("error", "type is not one the vault knows"),
    "date-invalid": ("error", "a date is not a calendar date written YYYY-MM-DD"),
    "draft-invalid": ("error", "draft is not true or false"),
    "description-length": ("warning", "the description is outside the usual length"),
    "adr-status": ("error", "an ADR needs a status from the lifecycle"),
    "adr-decided": ("error", "an ADR that is not proposed needs a decided date"),
    "evidence-level": ("error", "evidence is not one of the three levels"),
    "evidence-orphan": ("error", "a review field is set without evidence"),
    "reviewed-future": ("error", "reviewed is after today"),
    "reviewed-before-created": ("error", "reviewed is before created"),
    "review-due-order": ("error", "review-due is not after reviewed"),
    "review-due-span": ("error", "review-due is more than a year after reviewed"),
    "verified-missing": ("error", "operationally-verified needs a verified date"),
    "verified-future": ("error", "verified is after today"),
    "destructive-invalid": ("error", "destructive is not true or false"),
    "body-h1": ("error", "the body starts a top-level heading; the title is the page heading"),
    "evidence-section": ("error", "a note with evidence needs exactly one Evidence section"),
    "subsection-missing": ("error", "a required Evidence subsection is absent"),
    "subsection-empty": ("error", "a required Evidence subsection is empty"),
    "sources-link": ("error", "Sources checked holds no https link"),
    "reviewed-text": ("error", "the Evidence section never states the reviewed date"),
    "lab-run-fences": ("error", "Lab run needs a command block and an output block"),
    "danger-callout": ("error", "a destructive note needs a danger or warning callout"),
    "no-wikilink": ("error", "the note links to no other note"),
    "wikilink-unresolved": ("error", "a wikilink matches no file in the vault"),
    "index-missing": ("error", "the note's folder has no index page"),
    "not-in-index": ("error", "the folder index does not link the note"),
    "tag-unknown": ("error", "a tag is not in the taxonomy"),
}

BASE_FIELDS = ("title", "description", "type", "tags", "created", "modified", "draft")
TYPES = ("adr", "pattern", "tool", "standard", "runbook", "guide", "reference", "note")
ADR_STATUSES = ("proposed", "accepted", "rejected", "deprecated", "superseded")
LEVELS = ("source-reviewed", "lab-tested", "operationally-verified")
EXECUTABLE_SUBSECTIONS = (
    "environment",
    "prerequisites",
    "expected results",
    "failure conditions",
    "cleanup and rollback",
)
DESCRIPTION_RANGE = (50, 170)
MAX_REVIEW_DAYS = 366
MIN_LAB_FENCES = 2
# Pages that describe a folder or the site rather than belong to it. The vault's checker
# skips them entirely, so this one does too.
SKIPPED_STEMS = ("index", "tags", "template")

DATE_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}")
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
ITEM_LINE = re.compile(r"^\s*-(?:\s+(.*))?$")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CALLOUT = re.compile(r"^\s*>\s*\[!(?:danger|warning)\]", re.IGNORECASE)
WIKILINK = re.compile(r"\[\[([^\]\n]*)\]\]")
INLINE_CODE = re.compile(r"`[^`\n]*`")
HTTPS = re.compile(r"https://\S")
BACKTICKED_TAG = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
# YAML 1.2 core schema: only these spellings are booleans; the vault reads tRue as text.
BOOLEANS = {
    "true": True,
    "True": True,
    "TRUE": True,
    "false": False,
    "False": False,
    "FALSE": False,
}
UNSUPPORTED_START = "[{|>&*!%@`"


class InputError(Exception):
    """An input cannot be used; nothing should be reported from it."""


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    line: int
    message: str


def finding(rule: str, line: int, detail: str = "") -> Finding:
    severity, summary = RULES[rule]
    return Finding(rule, severity, line, f"{summary}: {detail}" if detail else summary)


@dataclass(frozen=True)
class Field:
    value: str | bool | list[str]
    line: int


@dataclass
class Frontmatter:
    fields: dict[str, Field] = field(default_factory=dict)
    problems: list[tuple[int, str]] = field(default_factory=list)
    body_start: int = 0  # index into the file's lines of the first body line


@dataclass(frozen=True)
class Line:
    number: int
    text: str
    ignored: bool  # inside a code fence
    opens_fence: bool = False


@dataclass(frozen=True)
class VaultView:
    """What the link checks need from the vault, read once by the caller."""

    known: frozenset[str]  # vault-relative POSIX paths of every file
    index_lines: list[str] | None  # the note's folder index, None when it has none


# ---------------------------------------------------------------------------
# Frontmatter


def parse_scalar(raw: str) -> tuple[str | bool | None, str]:
    """Return (value, problem). A problem means the text is not in the supported subset."""
    text = raw.strip()
    if not text:
        return "", ""
    first = text[0]
    if first in "\"'":
        return _parse_quoted(text)
    if first in UNSUPPORTED_START:
        return None, f"unsupported YAML starting with {first!r} (flow, block or anchor syntax)"
    plain = text.split(" #", 1)[0].rstrip()
    if ": " in plain or plain.endswith(":"):
        return None, "a plain value contains ': ' and must be quoted"
    if plain in BOOLEANS:
        return BOOLEANS[plain], ""
    return plain, ""


def _parse_quoted(text: str) -> tuple[str | None, str]:
    quote = text[0]
    out: list[str] = []
    i = 1
    while i < len(text):
        char = text[i]
        if quote == '"' and char == "\\" and i + 1 < len(text) and text[i + 1] in '"\\':
            out.append(text[i + 1])
            i += 2
            continue
        if quote == "'" and char == "'" and text[i + 1 : i + 2] == "'":
            out.append("'")
            i += 2
            continue
        if char == quote:
            rest = text[i + 1 :].strip()
            if rest and not rest.startswith("#"):
                return None, "text after the closing quote"
            return "".join(out), ""
        out.append(char)
        i += 1
    return None, "the quoted value is never closed"


def parse_frontmatter(lines: list[str]) -> Frontmatter:
    """Read the strict subset: key: value, quoted strings, `- item` lists, booleans, dates."""
    fm = Frontmatter()
    if not lines or lines[0].rstrip() != "---":
        fm.problems.append((1, "the file does not open with a --- frontmatter block"))
        return fm
    open_key: str | None = None  # the key whose value is still an empty, list-ready ""
    for index in range(1, len(lines)):
        number = index + 1
        text = lines[index].rstrip()
        if text == "---":
            fm.body_start = index + 1
            return fm
        stripped = text.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = ITEM_LINE.match(text)
        if item:
            _add_item(fm, open_key, item.group(1) or "", number)
            continue
        if text[0] in " \t":
            fm.problems.append((number, "unexpected indented line"))
            continue
        match = KEY_LINE.match(text)
        if not match:
            fm.problems.append((number, "cannot parse the line as `key: value`"))
            open_key = None
            continue
        key = match.group(1)
        value, problem = parse_scalar(match.group(2) or "")
        if problem or value is None:
            fm.problems.append((number, f"{key}: {problem or 'unreadable value'}"))
            open_key = None
        elif key in fm.fields:
            fm.problems.append((number, f"{key} repeats an earlier key"))
            open_key = None
        else:
            fm.fields[key] = Field(value, number)
            open_key = key if value == "" else None
    fm.problems.append((len(lines), "the frontmatter is never closed with ---"))
    fm.body_start = len(lines)
    return fm


def _add_item(fm: Frontmatter, key: str | None, raw: str, number: int) -> None:
    if key is None:
        fm.problems.append((number, "a list item that follows no empty key"))
        return
    value, problem = parse_scalar(raw)
    if problem or isinstance(value, bool) or value is None:
        fm.problems.append((number, f"{key}: list item: {problem or 'must be text'}"))
        return
    current = fm.fields[key]
    items = current.value if isinstance(current.value, list) else []
    fm.fields[key] = Field([*items, value], current.line)


def parse_date(value: object) -> dt.date | None:
    if not isinstance(value, str) or not DATE_SHAPE.fullmatch(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def parse_taxonomy(text: str) -> set[str]:
    """Tags are the backticked words under a heading naming the taxonomy, else anywhere."""
    section: list[str] = []
    inside = False
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            inside = "taxonomy" in heading.group(2).lower()
            continue
        if inside:
            section.append(line)
    source = "\n".join(section) if section else text
    return set(BACKTICKED_TAG.findall(source))


def check_frontmatter(
    fm: Frontmatter, today: dt.date, taxonomy: set[str] | None = None
) -> list[Finding]:
    out = [finding("frontmatter-syntax", line, detail) for line, detail in fm.problems]
    fields = fm.fields

    def value_of(key: str) -> object:
        return fields[key].value if key in fields else None

    def line_of(key: str) -> int:
        return fields[key].line if key in fields else 1

    for key in BASE_FIELDS:
        if key not in fields and not fm.problems:
            out.append(finding("field-missing", 1, key))
    out += _check_base(fields, line_of, value_of, taxonomy)
    out += _check_adr(fields, line_of, value_of)
    out += _check_evidence(fields, line_of, value_of, today)
    return out


def _check_base(fields, line_of, value_of, taxonomy) -> list[Finding]:
    out: list[Finding] = []
    for key in ("title", "description"):
        value = value_of(key)
        if key in fields and (not isinstance(value, str) or not value.strip()):
            out.append(finding("field-empty", line_of(key), key))
    description = value_of("description")
    if isinstance(description, str) and description.strip():
        low, high = DESCRIPTION_RANGE
        if not low <= len(description) <= high:
            out.append(
                finding(
                    "description-length",
                    line_of("description"),
                    f"{len(description)} characters, usually {low}-{high}",
                )
            )
    tags = value_of("tags")
    if "tags" in fields:
        if not isinstance(tags, list) or not tags or not all(t.strip() for t in tags):
            out.append(finding("field-empty", line_of("tags"), "tags needs at least one tag"))
        elif taxonomy is not None:
            out += [
                finding("tag-unknown", line_of("tags"), tag) for tag in tags if tag not in taxonomy
            ]
    if "type" in fields and value_of("type") not in TYPES:
        out.append(finding("type-invalid", line_of("type"), f"{value_of('type')!r}"))
    for key in ("created", "modified"):
        if key in fields and parse_date(value_of(key)) is None:
            out.append(finding("date-invalid", line_of(key), f"{key} is {value_of(key)!r}"))
    if "draft" in fields and not isinstance(value_of("draft"), bool):
        out.append(finding("draft-invalid", line_of("draft"), f"{value_of('draft')!r}"))
    return out


def _check_adr(fields, line_of, value_of) -> list[Finding]:
    if value_of("type") != "adr":
        return []
    out: list[Finding] = []
    status = value_of("status")
    if status not in ADR_STATUSES:
        out.append(finding("adr-status", line_of("status"), f"{status!r}"))
    if "decided" in fields:
        if parse_date(value_of("decided")) is None:
            out.append(
                finding("date-invalid", line_of("decided"), f"decided is {value_of('decided')!r}")
            )
    elif status != "proposed":
        out.append(finding("adr-decided", 1))
    return out


def _check_evidence(fields, line_of, value_of, today: dt.date) -> list[Finding]:
    out: list[Finding] = []
    level = value_of("evidence")
    if "verified" in fields:
        verified = parse_date(value_of("verified"))
        if verified is None:
            out.append(
                finding(
                    "date-invalid", line_of("verified"), f"verified is {value_of('verified')!r}"
                )
            )
        elif verified > today:
            out.append(finding("verified-future", line_of("verified"), f"{verified}"))
    if "evidence" not in fields:
        return out + [
            finding("evidence-orphan", line_of(key), key)
            for key in ("reviewed", "review-due", "destructive")
            if key in fields
        ]
    if level not in LEVELS:
        out.append(finding("evidence-level", line_of("evidence"), f"{level!r}"))
    if level == "operationally-verified" and "verified" not in fields:
        out.append(finding("verified-missing", line_of("evidence")))
    if "destructive" in fields and not isinstance(value_of("destructive"), bool):
        out.append(
            finding("destructive-invalid", line_of("destructive"), f"{value_of('destructive')!r}")
        )
    out += _check_review_dates(fields, line_of, value_of, today)
    return out


def _check_review_dates(fields, line_of, value_of, today: dt.date) -> list[Finding]:
    out: list[Finding] = []
    dates: dict[str, dt.date | None] = {}
    for key in ("reviewed", "review-due"):
        if key not in fields:
            out.append(finding("field-missing", line_of("evidence"), key))
            continue
        dates[key] = parse_date(value_of(key))
        if dates[key] is None:
            out.append(finding("date-invalid", line_of(key), f"{key} is {value_of(key)!r}"))
    reviewed, due = dates.get("reviewed"), dates.get("review-due")
    created = parse_date(value_of("created"))
    if reviewed and reviewed > today:
        out.append(finding("reviewed-future", line_of("reviewed"), f"{reviewed} is after {today}"))
    if reviewed and created and reviewed < created:
        out.append(
            finding("reviewed-before-created", line_of("reviewed"), f"{reviewed} < {created}")
        )
    if reviewed and due:
        if due <= reviewed:
            out.append(finding("review-due-order", line_of("review-due"), f"{due} <= {reviewed}"))
        elif (due - reviewed).days > MAX_REVIEW_DAYS:
            days = (due - reviewed).days
            out.append(
                finding(
                    "review-due-span",
                    line_of("review-due"),
                    f"{days} days, at most {MAX_REVIEW_DAYS}",
                )
            )
    return out


# ---------------------------------------------------------------------------
# Body


def scan(lines: list[str], start: int) -> list[Line]:
    """Number the body lines and mark those inside code fences.

    HTML comments are deliberately not special: the vault's own checker does not skip them,
    and guessing where one starts and ends is how a marker in a code span hid a whole note.
    """
    out: list[Line] = []
    fence: tuple[str, int] | None = None
    for index in range(start, len(lines)):
        text = lines[index]
        number = index + 1
        if fence is not None:
            closer = re.match(rf"^ {{0,3}}{re.escape(fence[0])}{{{fence[1]},}}\s*$", text)
            out.append(Line(number, text, True))
            if closer:
                fence = None
            continue
        opener = FENCE_OPEN.match(text)
        if opener:
            marker = opener.group(1)
            fence = (marker[0], len(marker))
            out.append(Line(number, text, True, opens_fence=True))
            continue
        out.append(Line(number, text, False))
    return out


@dataclass
class Section:
    heading: Line
    body: list[Line]


def split_sections(lines: list[Line], level: int) -> dict[str, list[Section]]:
    """Group lines under each heading of exactly `level`, ending at any heading up to it."""
    found: dict[str, list[Section]] = {}
    current: Section | None = None
    for line in lines:
        heading = None if line.ignored else HEADING.match(line.text)
        if heading and len(heading.group(1)) <= level:
            current = None
            if len(heading.group(1)) == level:
                current = Section(line, [])
                name = " ".join(heading.group(2).lower().split())
                found.setdefault(name, []).append(current)
            continue
        if current is not None:
            current.body.append(line)
    return found


def _has_text(section: Section) -> bool:
    return any(line.text.strip() for line in section.body)


def check_body(lines: list[str], fm: Frontmatter) -> list[Finding]:
    scanned = scan(lines, fm.body_start)
    out = [
        finding("body-h1", line.number, line.text.strip())
        for line in scanned
        if not line.ignored and re.match(r"^#\s", line.text)
    ]
    value = {key: f.value for key, f in fm.fields.items()}
    if value.get("destructive") is True and not any(
        not line.ignored and CALLOUT.match(line.text) for line in scanned
    ):
        out.append(finding("danger-callout", fm.fields["destructive"].line))
    if "evidence" in fm.fields:
        out += _check_evidence_section(scanned, value, fm.fields["evidence"].line)
    return out


def _check_evidence_section(scanned: list[Line], value: dict, evidence_line: int) -> list[Finding]:
    sections = split_sections(scanned, 2).get("evidence", [])
    if len(sections) != 1:
        where = sections[1].heading.number if sections else evidence_line
        return [finding("evidence-section", where, f"found {len(sections)}")]
    section = sections[0]
    subs = split_sections(section.body, 3)
    level = value.get("evidence")
    out: list[Finding] = []

    def need(name: str) -> Section | None:
        found = subs.get(name)
        if not found:
            out.append(finding("subsection-missing", section.heading.number, f"### {name}"))
            return None
        if not _has_text(found[0]):
            out.append(finding("subsection-empty", found[0].heading.number, f"### {name}"))
            return None
        return found[0]

    sources = need("sources checked")
    if sources and not any(HTTPS.search(line.text) for line in sources.body if not line.ignored):
        out.append(finding("sources-link", sources.heading.number))
    need("not verified")
    reviewed = value.get("reviewed")
    if isinstance(reviewed, str) and not any(reviewed in line.text for line in section.body):
        out.append(finding("reviewed-text", section.heading.number, reviewed))

    executable = (
        value.get("type") == "runbook"
        or value.get("destructive") is True
        or level in ("lab-tested", "operationally-verified")
    )
    if executable:
        for name in EXECUTABLE_SUBSECTIONS:
            need(name)
    if level in ("lab-tested", "operationally-verified") and "lab run" not in subs:
        need("lab run")
    lab = need("lab run") if "lab run" in subs else None
    if lab:
        opened = sum(line.opens_fence for line in lab.body)
        if opened < MIN_LAB_FENCES:
            out.append(finding("lab-run-fences", lab.heading.number, f"{opened} blocks"))
    if level == "operationally-verified":
        need("operational check")
    return out


# ---------------------------------------------------------------------------
# Links


def wikilink_targets(lines: list[Line]) -> list[tuple[int, str]]:
    """Each wikilink's target (alias, heading and table escape removed) with its line."""
    found = []
    for line in lines:
        if line.ignored:
            continue
        for match in WIKILINK.finditer(INLINE_CODE.sub("", line.text)):
            target = re.split(r"\\\||\||#", match.group(1), maxsplit=1)[0].strip()
            found.append((line.number, target))
    return found


def resolve(target: str, known: frozenset[str]) -> list[str]:
    """Vault paths a wikilink target names: by file name or by folder-qualified path."""
    wanted = target.strip("/")
    if wanted.endswith(".md"):
        wanted = wanted[:-3]
    hits = []
    for path in sorted(known):
        bare = path[:-3] if path.endswith(".md") else path
        if wanted in (bare, path) or bare.endswith("/" + wanted) or path.endswith("/" + wanted):
            hits.append(path)
    return hits


def index_required(note_rel: str) -> bool:
    return Path(note_rel).parent != Path(".")


def check_links(
    lines: list[str], start: int, note_rel: str, vault: VaultView | None
) -> list[Finding]:
    scanned = scan(lines, start)
    # Tag pages are generated at build time, so they are neither a file to resolve nor a
    # related note to link to.
    links = [(n, t) for n, t in wikilink_targets(scanned) if t and not t.startswith("tags/")]
    stem = Path(note_rel).stem
    out: list[Finding] = []
    if not any(Path(t).stem != stem for _, t in links):
        out.append(finding("no-wikilink", 1))
    if vault is None:
        return out
    out += [
        finding("wikilink-unresolved", number, f"[[{target}]]")
        for number, target in links
        if not resolve(target, vault.known)
    ]
    if index_required(note_rel):
        out += _check_index(note_rel, vault)
    return out


def _check_index(note_rel: str, vault: VaultView) -> list[Finding]:
    folder = Path(note_rel).parent.as_posix()
    if vault.index_lines is None:
        return [finding("index-missing", 1, f"{folder}/index.md")]
    index_links = wikilink_targets(scan(vault.index_lines, 0))
    if any(note_rel in resolve(target, vault.known) for _, target in index_links if target):
        return []
    return [finding("not-in-index", 1, f"{folder}/index.md has no link to {Path(note_rel).stem}")]


# ---------------------------------------------------------------------------
# Whole-note check, output and the command line


def check_text(
    text: str,
    note_rel: str,
    today: dt.date,
    taxonomy: set[str] | None = None,
    vault: VaultView | None = None,
) -> list[Finding]:
    if Path(note_rel).stem in SKIPPED_STEMS:
        return []
    lines = text.splitlines()
    fm = parse_frontmatter(lines)
    found = check_frontmatter(fm, today, taxonomy)
    found += check_body(lines, fm)
    found += check_links(lines, fm.body_start, note_rel, vault)
    return sorted(found, key=lambda f: (f.line, f.rule))


def render(results: dict[str, list[Finding]], as_json: bool) -> str:
    errors = sum(f.severity == "error" for found in results.values() for f in found)
    warnings = sum(f.severity == "warning" for found in results.values() for f in found)
    if as_json:
        files = [
            {
                "file": name,
                "findings": [
                    {"line": f.line, "rule": f.rule, "severity": f.severity, "message": f.message}
                    for f in found
                ],
            }
            for name, found in results.items()
        ]
        return json.dumps({"files": files, "errors": errors, "warnings": warnings}, indent=2)
    rows = [
        f"{name}:{f.line} {f.rule} {f.severity} {f.message}"
        for name, found in results.items()
        for f in found
    ]
    return "\n".join([*rows, f"{errors} errors, {warnings} warnings"])


def read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise InputError(f"{label} {str(path)!r} does not exist") from None
    except UnicodeDecodeError:
        raise InputError(f"{label} {str(path)!r} is not valid UTF-8") from None
    except OSError as error:
        raise InputError(f"{label} {str(path)!r} cannot be read ({type(error).__name__})") from None


def vault_files(vault: Path) -> frozenset[str]:
    return frozenset(
        p.relative_to(vault).as_posix()
        for p in vault.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(vault).parts)
    )


def vault_view(vault: Path, known: frozenset[str], note_rel: str) -> VaultView:
    index = vault / Path(note_rel).parent / "index.md"
    lines = read_text(index, "index page").splitlines() if index.is_file() else None
    return VaultView(known, lines)


def parse_today(raw: str | None) -> dt.date:
    if raw is None:
        return dt.date.today()
    parsed = parse_date(raw)
    if parsed is None:
        raise InputError(f"--today {raw!r} is not a YYYY-MM-DD date")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check notes against a vault's rules (read-only).")
    parser.add_argument("notes", nargs="+", type=Path, help="Markdown notes to check")
    parser.add_argument("--vault", type=Path, help="vault root: resolve wikilinks, check indexes")
    parser.add_argument("--taxonomy", type=Path, help="file listing the allowed tags")
    parser.add_argument("--today", help="YYYY-MM-DD to judge dates against (default: today)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument(
        "--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    return parser


def load_inputs(args: argparse.Namespace):
    """Validate everything before any note is checked; raise InputError on the first fault."""
    today = parse_today(args.today)
    taxonomy = None
    if args.taxonomy:
        taxonomy = parse_taxonomy(read_text(args.taxonomy, "taxonomy"))
    vault = None
    known: frozenset[str] = frozenset()
    if args.vault:
        vault = args.vault.resolve()
        if not vault.is_dir():
            raise InputError(f"--vault {str(args.vault)!r} is not a directory")
        known = vault_files(vault)
    notes = []  # (path, text, vault-relative name, view)
    for path in args.notes:
        if path.is_dir():
            raise InputError(f"{str(path)!r} is a directory, not a note")
        text = read_text(path, "note")
        rel = ""
        if vault:
            try:
                rel = path.resolve().relative_to(vault).as_posix()
            except ValueError:
                raise InputError(f"{str(path)!r} is outside the vault {str(vault)!r}") from None
        # Read the folder index here, with every other input, so an unreadable one exits 2.
        view = vault_view(vault, known, rel) if vault else None
        notes.append((path, text, rel or path.name, view))
    return today, taxonomy, notes


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
        force=True,
    )
    try:
        today, taxonomy, notes = load_inputs(args)
    except InputError as error:
        LOG.error("unusable input: %s", error)
        return 2
    results: dict[str, list[Finding]] = {}
    for path, text, rel, view in notes:
        LOG.info("checking %s", path)
        results[str(path)] = check_text(text, rel, today, taxonomy, view)
    print(render(results, args.json))
    failed = any(f.severity == "error" for found in results.values() for f in found)
    LOG.info("%d note(s) checked, %s", len(results), "errors found" if failed else "no errors")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
