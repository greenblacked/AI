"""The note checker: each rule family, the vault checks and the command line."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/techdocs/skills/work-to-note/scripts/check_note.py"

spec = importlib.util.spec_from_file_location("check_note", SCRIPT)
assert spec is not None
assert spec.loader is not None
check_note = importlib.util.module_from_spec(spec)
sys.modules["check_note"] = check_note
spec.loader.exec_module(check_note)

TODAY = "2026-10-27"
DESCRIPTION = (
    "Rotate a shared credential in two overlapping steps so that no client ever "
    "presents a key the server has already forgotten."
)

EVIDENCE_TAIL = """
## Evidence

### Sources checked

- [Vendor guide](https://example.com/guide): the rotation flags, checked 2026-10-20.

### Not verified

- The behaviour on older releases.
"""

EXECUTABLE = """
### Environment

Linux host, tool version 1.2.

### Prerequisites

A backup taken first.

### Expected results

The command exits 0.

### Failure conditions

A non-zero exit.

### Cleanup and rollback

Restore from the backup.
"""

LAB_RUN = """
### Lab run

Host: Linux. Date: 2026-10-20.

```bash
tool --version
```

```text
tool 1.2
```
"""

OPERATIONAL = """
### Operational check

Checked on a staging cluster by the owner on 2026-10-20.
"""


def frontmatter(**fields: object) -> str:
    """Build a frontmatter block; a value of None drops the key, `_` in a name becomes `-`."""
    values: dict[str, object] = {
        "title": "Secret rotation without downtime",
        "description": DESCRIPTION,
        "type": "pattern",
        "tags": ["security"],
        "created": "2026-01-10",
        "modified": "2026-01-10",
        "draft": False,
    }
    values.update({key.replace("_", "-"): value for key, value in fields.items()})
    lines = ["---"]
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def evidence_fields(**fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "evidence": "source-reviewed",
        "reviewed": "2026-10-20",
        "review_due": "2027-04-20",
    }
    base.update(fields)
    return base


BODY = "\nRotate in two steps, as in [[other-note]].\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def check(
    tmp_path: Path,
    text: str,
    capsys: pytest.CaptureFixture[str],
    *flags: str,
    name: str = "note.md",
) -> tuple[int, list[str]]:
    note = write(tmp_path / name, text)
    code = check_note.main([str(note), "--today", TODAY, *flags])
    out = capsys.readouterr().out
    return code, out.splitlines()


def rules_of(lines: list[str]) -> list[str]:
    """The rule ids on the finding lines (`file:line rule severity message`)."""
    found = []
    for line in lines:
        parts = line.split(" ")
        if len(parts) > 2 and parts[2] in {"error", "warning"}:
            found.append(parts[1])
    return found


def assert_fails_with(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    text: str,
    rule: str,
    *flags: str,
) -> None:
    code, lines = check(tmp_path, text, capsys, *flags)
    assert rule in rules_of(lines), lines
    assert code == 1


def source_reviewed(extra_fields: dict[str, object] | None = None, tail: str = "") -> str:
    fields = evidence_fields(**(extra_fields or {}))
    return frontmatter(**fields) + BODY + EVIDENCE_TAIL + tail


# ---------------------------------------------------------------------------
# Valid notes of each kind


def test_a_plain_pattern_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, lines = check(tmp_path, frontmatter() + BODY, capsys)
    assert code == 0
    assert lines[-1] == "0 errors, 0 warnings"


def test_an_accepted_adr_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = frontmatter(type="adr", status="accepted", decided="2026-02-01") + BODY
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


def test_a_proposed_adr_needs_no_decided_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, lines = check(tmp_path, frontmatter(type="adr", status="proposed") + BODY, capsys)
    assert code == 0, lines


def test_a_source_reviewed_note_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, lines = check(tmp_path, source_reviewed(), capsys)
    assert code == 0, lines


def test_a_destructive_runbook_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = (
        frontmatter(**evidence_fields(type="runbook", destructive=True))
        + "\n> [!danger] Revokes the old key\n> Clients on it stop working.\n"
        + BODY
        + EVIDENCE_TAIL
        + EXECUTABLE
    )
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


def test_a_lab_tested_note_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = source_reviewed({"evidence": "lab-tested"}, EXECUTABLE + LAB_RUN)
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


def test_an_operationally_verified_note_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(
        {"evidence": "operationally-verified", "verified": "2026-10-20"},
        EXECUTABLE + LAB_RUN + OPERATIONAL,
    )
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


# ---------------------------------------------------------------------------
# The frontmatter parser


def parse(*lines: str) -> object:
    return check_note.parse_frontmatter(list(lines))


def test_the_parser_reads_scalars_booleans_and_lists() -> None:
    fm = parse(
        "---",
        'title: "Quoted: with colon"',
        "description: 'it''s single'",
        "tags:",
        "  - one",
        "  - two # trailing comment",
        "draft: true",
        "created: 2026-10-11",
        "---",
        "body",
    )
    assert fm.problems == []
    values = {key: field.value for key, field in fm.fields.items()}
    assert values == {
        "title": "Quoted: with colon",
        "description": "it's single",
        "tags": ["one", "two"],
        "draft": True,
        "created": "2026-10-11",
    }
    assert fm.fields["draft"].line == 7
    assert fm.body_start == 9


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
    ],
)
def test_the_parser_accepts_the_three_spellings_of_each_boolean(raw: str, expected: bool) -> None:
    fm = parse("---", f"draft: {raw}", "---")
    assert fm.fields["draft"].value is expected


@pytest.mark.parametrize("raw", ["tRue", "fALSE", "tRUE"])
def test_the_parser_keeps_other_casings_as_text(raw: str) -> None:
    # The vault's parser reads only true/True/TRUE as a boolean, so neither may this one.
    fm = parse("---", f"draft: {raw}", "---")
    assert fm.fields["draft"].value == raw


def test_the_parser_reports_lines_it_cannot_read() -> None:
    fm = parse(
        "---",
        "title: ok",
        "no colon here",
        "description: has: colon",
        "title: again",
        "tags: scalar",
        "  - orphan",
        "key: [a, b]",
        "---",
    )
    messages = {line: detail for line, detail in fm.problems}
    assert set(messages) == {3, 4, 5, 7, 8}
    assert "flow" in messages[8]
    assert "repeats" in messages[5]


def test_the_parser_reports_an_unclosed_block_and_a_missing_one() -> None:
    assert parse("---", "title: x").problems[-1][1].startswith("the frontmatter is never closed")
    assert parse("no frontmatter").problems[0][0] == 1


def test_an_unterminated_quote_is_reported() -> None:
    fm = parse("---", 'title: "never closed', "---")
    assert fm.problems and fm.problems[0][0] == 2


def test_a_syntax_problem_is_a_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = frontmatter().replace("draft: false", "draft: [false]")
    assert_fails_with(tmp_path, capsys, text + BODY, "frontmatter-syntax")


def test_a_note_with_no_frontmatter_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(tmp_path, capsys, "Just text with [[a-link]].\n", "frontmatter-syntax")


# ---------------------------------------------------------------------------
# Base fields


@pytest.mark.parametrize(
    "field", ["title", "description", "type", "tags", "created", "modified", "draft"]
)
def test_each_base_field_is_required(
    field: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter(**{field: None}) + BODY, "field-missing")


def test_an_empty_title_and_empty_tags_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter(title='""', tags="") + BODY
    code, lines = check(tmp_path, text, capsys)
    assert code == 1
    assert rules_of(lines).count("field-empty") == 2


def test_an_unknown_type_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter(type="essay") + BODY, "type-invalid")


@pytest.mark.parametrize("value", ["2026-10-11T08:00:00", "10/11/2026", "2026-02-30", "yesterday"])
def test_dates_must_be_calendar_dates(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter(created=value) + BODY, "date-invalid")


def test_draft_must_be_a_boolean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter(draft="maybe") + BODY, "draft-invalid")


@pytest.mark.parametrize("length", [49, 171])
def test_a_description_outside_the_range_warns_without_failing(
    length: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, lines = check(tmp_path, frontmatter(description="d" * length) + BODY, capsys)
    assert code == 0
    assert rules_of(lines) == ["description-length"]


@pytest.mark.parametrize("length", [50, 170])
def test_a_description_at_the_range_edges_is_fine(
    length: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, lines = check(tmp_path, frontmatter(description="d" * length) + BODY, capsys)
    assert code == 0
    assert rules_of(lines) == []


# ---------------------------------------------------------------------------
# ADR fields


def test_an_adr_needs_a_known_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = frontmatter(type="adr", status="Accepted", decided="2026-02-01") + BODY
    assert_fails_with(tmp_path, capsys, text, "adr-status")
    text = frontmatter(type="adr", decided="2026-02-01") + BODY
    assert_fails_with(tmp_path, capsys, text, "adr-status")


def test_an_accepted_adr_needs_a_decided_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(
        tmp_path, capsys, frontmatter(type="adr", status="accepted") + BODY, "adr-decided"
    )


def test_a_decided_date_must_be_valid_even_when_proposed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter(type="adr", status="proposed", decided="soon") + BODY
    assert_fails_with(tmp_path, capsys, text, "date-invalid")


# ---------------------------------------------------------------------------
# Evidence fields


def test_an_unknown_evidence_level_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(
        tmp_path, capsys, source_reviewed({"evidence": "tested-ish"}), "evidence-level"
    )


@pytest.mark.parametrize("missing", ["reviewed", "review_due"])
def test_evidence_needs_both_review_dates(
    missing: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(tmp_path, capsys, source_reviewed({missing: None}), "field-missing")


def test_a_review_in_the_future_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = source_reviewed({"reviewed": "2026-10-28", "review_due": "2027-01-01"})
    assert_fails_with(tmp_path, capsys, text, "reviewed-future")


def test_a_review_before_the_note_was_created_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter(**evidence_fields(created="2026-10-21")) + BODY + EVIDENCE_TAIL
    assert_fails_with(tmp_path, capsys, text, "reviewed-before-created")


def test_review_due_must_follow_the_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for due in ("2026-10-20", "2026-10-01"):
        assert_fails_with(
            tmp_path, capsys, source_reviewed({"review_due": due}), "review-due-order"
        )


def test_review_due_at_366_days_passes_and_367_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # 2026-10-20 plus 366 days is 2027-10-21; the extra day lands on 2027-10-22.
    code, lines = check(tmp_path, source_reviewed({"review_due": "2027-10-21"}), capsys)
    assert code == 0, lines
    assert_fails_with(
        tmp_path, capsys, source_reviewed({"review_due": "2027-10-22"}), "review-due-span"
    )


def test_operationally_verified_needs_a_verified_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(
        {"evidence": "operationally-verified"}, EXECUTABLE + LAB_RUN + OPERATIONAL
    )
    assert_fails_with(tmp_path, capsys, text, "verified-missing")


def test_a_verified_date_in_the_future_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter(verified="2026-10-28") + BODY
    assert_fails_with(tmp_path, capsys, text, "verified-future")


def test_a_verified_date_must_be_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter(verified="today") + BODY, "date-invalid")


@pytest.mark.parametrize(
    "field", [("reviewed", "2026-10-20"), ("review_due", "2027-01-01"), ("destructive", True)]
)
def test_review_fields_without_evidence_are_an_error(
    field: tuple[str, object], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter(**dict([field])) + BODY
    assert_fails_with(tmp_path, capsys, text, "evidence-orphan")


def test_destructive_must_be_a_boolean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert_fails_with(
        tmp_path, capsys, source_reviewed({"destructive": "sure"}), "destructive-invalid"
    )


# ---------------------------------------------------------------------------
# Body


def test_an_h1_fails_and_names_its_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = frontmatter() + "\n# Repeats the title\n" + BODY
    code, lines = check(tmp_path, text, capsys)
    assert code == 1
    assert any(":12 body-h1 error" in line for line in lines), lines


def test_headings_and_callouts_inside_fences_are_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fenced = "\n```markdown\n# Example H1\n## Evidence\n> [!danger] example\n```\n"
    code, lines = check(tmp_path, frontmatter() + BODY + fenced, capsys)
    assert code == 0, lines


def test_a_tilde_fence_hides_headings_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fenced = "\n~~~text\n# Not a heading\n~~~\n"
    code, lines = check(tmp_path, frontmatter() + BODY + fenced, capsys)
    assert code == 0, lines


def test_evidence_needs_exactly_one_evidence_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = frontmatter(**evidence_fields()) + BODY
    assert_fails_with(tmp_path, capsys, missing, "evidence-section")
    twice = source_reviewed() + EVIDENCE_TAIL
    assert_fails_with(tmp_path, capsys, twice, "evidence-section")


def test_the_evidence_heading_matches_without_regard_to_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = (
        source_reviewed()
        .replace("## Evidence", "## EVIDENCE ")
        .replace("### Sources checked", "### sources CHECKED")
    )
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


def test_sources_checked_must_exist_hold_text_and_an_https_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gone = source_reviewed().replace("### Sources checked", "### Sources")
    assert_fails_with(tmp_path, capsys, gone, "subsection-missing")
    empty = source_reviewed().replace(
        "- [Vendor guide](https://example.com/guide): the rotation flags, checked 2026-10-20.", ""
    )
    assert_fails_with(tmp_path, capsys, empty, "subsection-empty")
    http = source_reviewed().replace("https://example.com", "http://example.com")
    assert_fails_with(tmp_path, capsys, http, "sources-link")


def test_not_verified_must_hold_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = source_reviewed().replace("- The behaviour on older releases.", "")
    assert_fails_with(tmp_path, capsys, text, "subsection-empty")


def test_the_reviewed_date_must_appear_in_the_evidence_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed().replace("checked 2026-10-20", "checked last week")
    assert_fails_with(tmp_path, capsys, text, "reviewed-text")


def test_a_runbook_with_evidence_needs_the_executable_subsections(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed({"type": "runbook"})
    code, lines = check(tmp_path, text, capsys)
    assert code == 1
    assert rules_of(lines).count("subsection-missing") == 5


def test_an_executable_subsection_must_say_something(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed({"type": "runbook"}, EXECUTABLE.replace("Restore from the backup.", ""))
    assert_fails_with(tmp_path, capsys, text, "subsection-empty")


def test_a_lab_tested_note_needs_a_lab_run_with_two_fences(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed({"evidence": "lab-tested"}, EXECUTABLE)
    assert_fails_with(tmp_path, capsys, text, "subsection-missing")
    one_fence = source_reviewed(
        {"evidence": "lab-tested"}, EXECUTABLE + LAB_RUN.replace("```text\ntool 1.2\n```\n", "")
    )
    assert_fails_with(tmp_path, capsys, one_fence, "lab-run-fences")


def test_an_optional_lab_run_still_needs_two_fences(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(tail="\n### Lab run\n\nOne block only.\n\n```bash\nls\n```\n")
    assert_fails_with(tmp_path, capsys, text, "lab-run-fences")


def test_operationally_verified_needs_an_operational_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(
        {"evidence": "operationally-verified", "verified": "2026-10-20"}, EXECUTABLE + LAB_RUN
    )
    assert_fails_with(tmp_path, capsys, text, "subsection-missing")


def test_a_destructive_note_needs_the_executable_subsections_and_a_callout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed({"destructive": True})
    code, lines = check(tmp_path, text, capsys)
    assert code == 1
    assert rules_of(lines).count("subsection-missing") == 5
    assert "danger-callout" in rules_of(lines)


def test_a_callout_inside_a_fence_does_not_satisfy_a_destructive_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fenced = "\n```markdown\n> [!danger] only an example\n```\n"
    text = (
        frontmatter(**evidence_fields(destructive=True))
        + BODY
        + fenced
        + EVIDENCE_TAIL
        + EXECUTABLE
    )
    assert_fails_with(tmp_path, capsys, text, "danger-callout")


def test_a_warning_callout_also_satisfies_a_destructive_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = (
        frontmatter(**evidence_fields(destructive=True))
        + "\n> [!warning] Deletes data\n"
        + BODY
        + EVIDENCE_TAIL
        + EXECUTABLE
    )
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


# ---------------------------------------------------------------------------
# Links, vault and taxonomy


def test_a_note_without_a_wikilink_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert_fails_with(tmp_path, capsys, frontmatter() + "\nNo links here.\n", "no-wikilink")


def test_wikilinks_in_code_or_to_itself_do_not_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter() + "\nUse `[[inline]]` or [[note]] itself.\n\n```text\n[[fenced]]\n```\n"
    assert_fails_with(tmp_path, capsys, text, "no-wikilink")


def test_link_forms_with_aliases_headings_and_table_escapes_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter() + "\n| a |\n| - |\n| [[other-note\\|Other]] |\n"
    code, lines = check(tmp_path, text, capsys)
    assert code == 0, lines


def make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    write(vault / "patterns" / "other-note.md", frontmatter() + BODY)
    write(vault / "patterns" / "index.md", "- [[other-note]]\n- [[note|The note]]\n")
    write(vault / "adr" / "index.md", "| [[0001-first\\|0001]] | First |\n")
    write(vault / "adr" / "0001-first.md", frontmatter(type="adr", status="proposed") + BODY)
    return vault


def test_a_resolving_and_indexed_note_passes_with_a_vault(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(vault / "patterns" / "note.md", frontmatter() + BODY)
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 0, capsys.readouterr().out


def test_an_unresolved_wikilink_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    note = write(
        vault / "patterns" / "note.md", frontmatter() + "\n[[other-note]] and [[ghost]].\n"
    )
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    out = capsys.readouterr().out
    assert code == 1
    assert "wikilink-unresolved" in out
    assert "ghost" in out
    assert "other-note" not in out.split("wikilink-unresolved")[1].splitlines()[0]


def test_a_folder_qualified_link_resolves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(
        vault / "patterns" / "note.md",
        frontmatter() + "\n[[patterns/other-note#Heading|text]] and [[adr/index]].\n",
    )
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 0, capsys.readouterr().out


def test_a_note_missing_from_its_folder_index_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(vault / "patterns" / "fresh.md", frontmatter() + BODY)
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 1
    assert "not-in-index" in capsys.readouterr().out


def test_an_adr_needs_its_row_in_the_adr_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(
        vault / "adr" / "0002-second.md",
        frontmatter(type="adr", status="proposed") + "\n[[0001-first]]\n",
    )
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 1
    assert "not-in-index" in capsys.readouterr().out
    index = vault / "adr" / "index.md"
    index.write_text(index.read_text(encoding="utf-8") + "| [[0002-second\\|0002]] | Second |\n")
    assert check_note.main([str(note), "--vault", str(vault), "--today", TODAY]) == 0


def test_a_folder_without_an_index_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(vault / "tools" / "fresh.md", frontmatter(type="tool") + "\n[[other-note]]\n")
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 1
    assert "index-missing" in capsys.readouterr().out


def test_an_index_page_is_not_asked_to_list_itself(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    index = vault / "patterns" / "index.md"
    index.write_text(frontmatter(type="standard") + "\n- [[other-note]]\n", encoding="utf-8")
    assert check_note.main([str(index), "--vault", str(vault), "--today", TODAY]) == 0


def test_a_link_to_a_namesake_in_another_folder_is_not_a_self_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    write(vault / "runbooks" / "rotation.md", frontmatter(type="runbook") + BODY)
    index = vault / "patterns" / "index.md"
    index.write_text(index.read_text(encoding="utf-8") + "- [[patterns/rotation]]\n")
    note = write(vault / "patterns" / "rotation.md", frontmatter() + "\n[[runbooks/rotation]]\n")
    code = check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert code == 0, capsys.readouterr().out


def test_a_folder_qualified_link_to_the_note_itself_is_still_a_self_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    note = write(
        vault / "patterns" / "note.md", frontmatter() + "\n[[patterns/note]] and [[note]].\n"
    )
    check_note.main([str(note), "--vault", str(vault), "--today", TODAY])
    assert "no-wikilink" in capsys.readouterr().out


def test_without_a_vault_a_folder_qualified_namesake_counts_as_another_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter() + "\n[[runbooks/note]]\n"
    code, lines = check(tmp_path, text, capsys)
    assert "no-wikilink" not in rules_of(lines), lines


def test_without_a_vault_a_folder_qualified_link_to_itself_is_still_a_self_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter() + "\n[[patterns/note]]\n"
    code, lines = check(tmp_path, text, capsys, name="patterns/note.md")
    assert "no-wikilink" in rules_of(lines), lines


def test_taxonomy_tags_must_be_listed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    taxonomy = write(
        tmp_path / "taxonomy.md",
        "Field table: `title` `tags`\n\n## Tagging taxonomy\n\n"
        "| Kind | Tags |\n| - | - |\n| Concern | `security`, `reliability` |\n\n"
        "## Next\n\n`other`\n",
    )
    ok, lines = check(tmp_path, frontmatter() + BODY, capsys, "--taxonomy", str(taxonomy))
    assert ok == 0, lines
    text = frontmatter(tags=["security", "invented", "title", "other"]) + BODY
    code, lines = check(tmp_path, text, capsys, "--taxonomy", str(taxonomy))
    assert code == 1
    assert rules_of(lines).count("tag-unknown") == 3


def test_a_taxonomy_without_a_taxonomy_heading_uses_every_backticked_tag() -> None:
    assert check_note.parse_taxonomy("Tags: `alpha`, `beta-2`.\n`Not A Tag`") == {"alpha", "beta-2"}


# ---------------------------------------------------------------------------
# Output and exit codes


def test_findings_print_as_file_line_rule_severity_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, lines = check(tmp_path, frontmatter(type="essay") + BODY, capsys)
    assert code == 1
    assert lines[0].startswith(f"{tmp_path / 'note.md'}:4 type-invalid error ")
    assert lines[-1] == "1 errors, 0 warnings"


def test_json_output_has_a_stable_shape(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = frontmatter(type="essay", description="short") + BODY
    code, lines = check(tmp_path, text, capsys, "--json")
    assert code == 1
    data = json.loads("\n".join(lines))
    assert set(data) == {"files", "errors", "warnings"}
    assert data["errors"] == 1
    assert data["warnings"] == 1
    [entry] = data["files"]
    assert entry["file"] == str(tmp_path / "note.md")
    assert {finding["rule"] for finding in entry["findings"]} == {
        "type-invalid",
        "description-length",
    }
    assert set(entry["findings"][0]) == {"line", "rule", "severity", "message"}


def test_several_notes_are_checked_and_the_worst_decides_the_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = write(tmp_path / "good.md", frontmatter() + BODY)
    bad = write(tmp_path / "bad.md", frontmatter(type="essay") + BODY)
    code = check_note.main([str(good), str(bad), "--today", TODAY])
    assert code == 1
    assert capsys.readouterr().out.splitlines()[-1] == "1 errors, 0 warnings"


def test_exit_two_for_a_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_note.main([str(tmp_path / "absent.md")]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR" in captured.err


def test_exit_two_for_a_non_utf8_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "latin.md"
    bad.write_bytes(b"---\ntitle: caf\xe9\n---\n")
    assert check_note.main([str(bad)]) == 2
    assert "UTF-8" in capsys.readouterr().err


def test_exit_two_for_a_bad_today(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    note = write(tmp_path / "note.md", frontmatter() + BODY)
    assert check_note.main([str(note), "--today", "2026-13-40"]) == 2
    assert "--today" in capsys.readouterr().err


def test_exit_two_for_a_directory_given_as_a_note(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_note.main([str(tmp_path)]) == 2


def test_exit_two_for_a_missing_vault_or_taxonomy_or_a_note_outside_the_vault(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    note = write(tmp_path / "note.md", frontmatter() + BODY)
    assert check_note.main([str(note), "--vault", str(tmp_path / "nope")]) == 2
    assert check_note.main([str(note), "--taxonomy", str(tmp_path / "nope.md")]) == 2
    vault = tmp_path / "vault"
    vault.mkdir()
    assert check_note.main([str(note), "--vault", str(vault)]) == 2
    assert "outside" in capsys.readouterr().err


def test_a_usage_error_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        check_note.main([])
    assert raised.value.code == 2


def test_inputs_are_validated_before_any_note_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = write(tmp_path / "bad.md", frontmatter(type="essay") + BODY)
    assert check_note.main([str(bad), str(tmp_path / "absent.md")]) == 2
    assert capsys.readouterr().out == ""


def test_logs_go_to_stderr_with_a_timestamp_and_level(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    note = write(tmp_path / "note.md", frontmatter() + BODY)
    check_note.main([str(note), "--today", TODAY, "--log-level", "INFO"])
    captured = capsys.readouterr()
    assert "INFO" in captured.err
    assert captured.err.split()[0].count("-") == 2
    assert "INFO" not in captured.out


def test_nothing_is_written(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vault = make_vault(tmp_path)
    note = write(vault / "patterns" / "note.md", frontmatter() + "\n[[ghost]]\n")
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file()}
    check_note.main([str(note), "--vault", str(vault), "--today", TODAY, "--json"])
    after = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_every_rule_in_the_table_has_a_severity_and_summary() -> None:
    for rule, (severity, summary) in check_note.RULES.items():
        assert severity in {"error", "warning"}, rule
        assert summary, rule


def test_the_shipped_template_passes(capsys: pytest.CaptureFixture[str]) -> None:
    template = SCRIPT.parent.parent / "assets" / "note-template.md"
    assert check_note.main([str(template), "--today", TODAY]) == 0


def test_html_comments_are_not_special(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # The vault's own checker does not skip comments, so a commented heading counts.
    hidden = "\n<!--\n# A heading\n-->\n"
    code, lines = check(tmp_path, frontmatter() + BODY + hidden, capsys)
    assert "body-h1" in rules_of(lines), lines
    code, lines = check(tmp_path, frontmatter() + "\n<!-- [[other-note]] -->\n", capsys)
    assert "no-wikilink" not in rules_of(lines), lines


def test_a_comment_marker_in_a_code_span_hides_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = frontmatter() + "\nUse `<!--` to start a comment.\n\n# Real H1\n\n[[other-note]]\n"
    code, lines = check(tmp_path, text, capsys)
    assert rules_of(lines) == ["body-h1"], lines
    runbook = source_reviewed({"type": "runbook"}, EXECUTABLE).replace(
        "\n### Not verified", "\n### Not verified\n\nThe `<!--` marker.\n", 1
    )
    code, lines = check(tmp_path, runbook, capsys)
    assert "subsection-missing" not in rules_of(lines), lines


def test_a_commented_skeleton_beside_a_real_evidence_section_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(tail="\n<!--\n## Evidence\n-->\n")
    assert_fails_with(tmp_path, capsys, text, "evidence-section")


def test_the_parser_accepts_zero_indent_items_and_capitalised_booleans() -> None:
    fm = parse("---", "tags:", "- a", "- b", "draft: True", "destructive: FALSE", "---")
    assert fm.problems == []
    assert fm.fields["tags"].value == ["a", "b"]
    assert fm.fields["draft"].value is True
    assert fm.fields["destructive"].value is False


def test_an_empty_optional_lab_run_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = source_reviewed(tail="\n### Lab run\n")
    assert_fails_with(tmp_path, capsys, text, "subsection-empty")


def test_index_tags_and_template_pages_are_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    for name in ("index", "tags", "template"):
        page = write(vault / "patterns" / f"{name}.md", "# Page\n\nNo frontmatter.\n")
        assert check_note.main([str(page), "--vault", str(vault), "--today", TODAY]) == 0


def test_generated_tag_page_links_resolve_but_do_not_count_as_a_note_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    ok = write(
        vault / "patterns" / "note.md", frontmatter() + "\n[[other-note]] and [[tags/security]].\n"
    )
    assert check_note.main([str(ok), "--vault", str(vault), "--today", TODAY]) == 0
    only = write(vault / "patterns" / "note.md", frontmatter() + "\n[[tags/security]]\n")
    assert check_note.main([str(only), "--vault", str(vault), "--today", TODAY]) == 1
    assert "no-wikilink" in capsys.readouterr().out


def test_a_non_utf8_index_page_exits_two_before_any_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    vault = make_vault(tmp_path)
    (vault / "patterns" / "index.md").write_bytes(b"- [[note]] caf\xe9\n")
    note = write(vault / "patterns" / "note.md", frontmatter() + BODY)
    assert check_note.main([str(note), "--vault", str(vault), "--today", TODAY]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "UTF-8" in captured.err
