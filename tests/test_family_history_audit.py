"""The family-history register audit: each rule, with fictional registers."""

import copy
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/personal/skills/family-history-research/scripts/audit_registers.py"

spec = importlib.util.spec_from_file_location("audit_registers", SCRIPT)
assert spec is not None
assert spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules["audit_registers"] = audit
spec.loader.exec_module(audit)

CLEAN = {
    "sources.csv": [
        {
            "source_id": "S1",
            "citation": "Fictional parish register, baptisms 1851, entry 12",
            "kind": "original",
            "locator": "vol 3, folio 4",
            "how_obtained": "user visit",
            "local_copy_path": "copies/s1.jpg",
            "sha256": "a" * 64,
        },
        {
            "source_id": "S2",
            "citation": "Fictional parish register, marriages 1874, entry 3",
            "kind": "original",
            "locator": "vol 5, folio 9",
            "how_obtained": "user visit",
            "local_copy_path": "",
            "sha256": "",
        },
        {
            "source_id": "S3",
            "citation": "Fictional online tree, entry for Ana",
            "kind": "authored",
            "locator": "page 7",
            "how_obtained": "user search",
            "local_copy_path": "",
            "sha256": "",
        },
        {
            "source_id": "S4",
            "citation": "Fictional compiled family history, p. 40",
            "kind": "authored",
            "locator": "p. 40",
            "how_obtained": "library",
            "local_copy_path": "",
            "sha256": "",
        },
    ],
    "statements.csv": [
        {
            "statement_id": "T1",
            "source_id": "S1",
            "person_as_written": "Ana, daughter of Pieter and Johanna",
            "event": "baptism",
            "date_as_written": "3 March 1851",
            "place_as_written": "Alderbrook",
            "informant": "officiant",
            "informant_closeness": "present",
            "information": "first-hand",
        },
        {
            "statement_id": "T2",
            "source_id": "S2",
            "person_as_written": "Ana Verhoeven, parents Pieter and Johanna",
            "event": "marriage",
            "date_as_written": "9 May 1874",
            "place_as_written": "Alderbrook",
            "informant": "bride",
            "informant_closeness": "told",
            "information": "second-hand",
        },
        {
            "statement_id": "T3",
            "source_id": "S3",
            "person_as_written": "Ana Verhoeven",
            "event": "birth",
            "date_as_written": "1851",
            "place_as_written": "Alderbrook",
            "informant": "unknown",
            "informant_closeness": "unknown",
            "information": "undetermined",
        },
        {
            "statement_id": "T4",
            "source_id": "S4",
            "person_as_written": "Ana Verhoeven",
            "event": "birth",
            "date_as_written": "1851",
            "place_as_written": "Alderbrook",
            "informant": "unknown",
            "informant_closeness": "unknown",
            "information": "undetermined",
        },
    ],
    "people.csv": [
        {
            "person_id": "P1",
            "name": "Ana Verhoeven",
            "possibly_living": "no",
            "inclusion_basis": "",
        },
        {
            "person_id": "P2",
            "name": "Pieter Verhoeven",
            "possibly_living": "no",
            "inclusion_basis": "",
        },
    ],
    "conclusions.csv": [
        {
            "conclusion_id": "C1",
            "conclusion": "Pieter was the father of Ana",
            "kind": "relationship",
            "person_a": "P2",
            "person_b": "P1",
            "evidence": "direct",
            "statements_for": "T1;T2",
            "statements_against": "",
            "resolution": "",
            "proof_level": "proved",
        }
    ],
    "research-log.csv": [
        {
            "row_type": "search",
            "date": "2026-01-02",
            "repository_kind": "regional archive",
            "terms": "Verhoeven; Verhoven",
            "scope_covered": "baptisms 1850-1852, Alderbrook",
            "result": "one entry",
            "follow_up": "none",
            "coverage_item": "",
            "final_state": "",
            "reason": "",
        },
        {
            "row_type": "coverage",
            "date": "",
            "repository_kind": "",
            "terms": "",
            "scope_covered": "",
            "result": "",
            "follow_up": "",
            "coverage_item": "baptism register 1850-1852",
            "final_state": "searched-found",
            "reason": "",
        },
    ],
}


def write_registers(directory: Path, data: dict[str, list[dict[str, str]]] | None = None) -> Path:
    data = CLEAN if data is None else data
    for name, columns in audit.COLUMNS.items():
        with (directory / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data[name])
    return directory


def conclusion(**fields: str) -> list[dict[str, str]]:
    row = copy.deepcopy(CLEAN["conclusions.csv"][0])
    row.update(fields)
    return [row]


def run(
    tmp_path: Path,
    data: dict[str, list[dict[str, str]]],
    capsys: pytest.CaptureFixture[str],
    *flags: str,
) -> tuple[int, str]:
    write_registers(tmp_path, data)
    code = audit.main([str(tmp_path), *flags])
    return code, capsys.readouterr().out


def test_a_clean_case_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(tmp_path, CLEAN, capsys)
    assert code == 0
    assert out.strip() == "0 errors, 0 warnings"


def test_the_shipped_registers_are_header_only_and_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assets = SCRIPT.parent.parent / "assets"
    assert audit.main([str(assets)]) == 0
    assert capsys.readouterr().out.strip() == "0 errors, 0 warnings"


def test_a_statement_citing_a_missing_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["statements.csv"][0]["source_id"] = "S99"
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[missing-source]" in out
    assert "'S99'" in out


def test_a_conclusion_citing_a_missing_statement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_for="T1;T99")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[missing-statement]" in out
    assert "'T99'" in out


def test_a_conclusion_citing_a_missing_person(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(person_a="P99")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[missing-person]" in out


@pytest.mark.parametrize("missing", ["person_a", "person_b"])
def test_a_relationship_needs_both_people(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(**{missing: ""})
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[relationship-people]" in out


def test_an_identity_conclusion_may_name_one_person(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(kind="identity", person_b="")
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_two_trees_do_not_make_a_proved_or_probable_conclusion(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Both supporting statements come from authored works: agreement between them is not
    # independent confirmation, whatever level the researcher wanted to write.
    for level in ("proved", "probable"):
        data = copy.deepcopy(CLEAN)
        data["conclusions.csv"] = conclusion(statements_for="T3;T4", proof_level=level)
        code, out = run(tmp_path, data, capsys)
        assert code == 1
        assert "[no-original-support]" in out


def test_derivative_support_alone_is_not_original(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["sources.csv"][0]["kind"] = "derivative"
    data["conclusions.csv"] = conclusion(statements_for="T1", proof_level="probable")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[no-original-support]" in out


def test_authored_support_at_possible_is_allowed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_for="T3;T4", proof_level="possible")
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_proved_on_one_original_source_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_for="T1;T3")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[one-original]" in out


def test_proved_resting_only_on_negative_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(evidence="negative")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[negative-only]" in out


def test_negative_evidence_beside_direct_evidence_is_not_negative_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(evidence="direct;negative")
    code, out = run(tmp_path, data, capsys)
    assert code == 0, out


@pytest.mark.parametrize("level", ["proved", "probable"])
def test_statements_against_need_a_resolution(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], level: str
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_against="T3", proof_level=level)
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[unresolved-conflict]" in out


def test_a_resolution_clears_the_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(
        statements_against="T3", resolution="T3 is an authored tree with no source"
    )
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_an_open_conflict_is_fine_at_possible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_against="T3", proof_level="possible")
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_a_coverage_row_with_no_final_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["research-log.csv"][1]["final_state"] = ""
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[coverage-state]" in out


@pytest.mark.parametrize("state", ["inaccessible", "out-of-scope"])
def test_inaccessible_and_out_of_scope_need_a_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], state: str
) -> None:
    data = copy.deepcopy(CLEAN)
    data["research-log.csv"][1]["final_state"] = state
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[coverage-reason]" in out
    data["research-log.csv"][1]["reason"] = "not digitised"
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_a_possibly_living_person_needs_an_inclusion_basis(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["people.csv"][0]["possibly_living"] = "yes"
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[living-no-basis]" in out
    data["people.csv"][0]["inclusion_basis"] = "the user, agreed in writing"
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_probable_on_a_single_source_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(statements_for="T1", proof_level="probable")
    code, out = run(tmp_path, data, capsys)
    assert code == 0
    assert "WARNING" in out
    assert "[single-source]" in out
    assert "0 errors, 1 warnings" in out


def test_a_local_copy_without_a_hash_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["sources.csv"][0]["sha256"] = ""
    code, out = run(tmp_path, data, capsys)
    assert code == 0
    assert "[no-sha256]" in out


def test_strict_turns_warnings_into_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["sources.csv"][0]["sha256"] = ""
    code, _ = run(tmp_path, data, capsys, "--strict")
    assert code == 1


def test_register_text_is_printed_with_repr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A newline in third-party text must not start a line that looks like our output.
    forged = "S99\nERROR conclusions.csv row 1 [none] 0 errors"
    data = copy.deepcopy(CLEAN)
    data["statements.csv"][0]["source_id"] = forged
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "\\n" in out
    lines = out.splitlines()
    assert all(line.startswith(("ERROR", "WARNING")) or line.endswith("warnings") for line in lines)
    # two findings (the bad source breaks T1 and leaves C1 on one original) and the summary
    assert len(lines) == 3


def test_nothing_is_printed_when_a_later_file_is_unusable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["statements.csv"][0]["source_id"] = "S99"  # would be an error if reached
    write_registers(tmp_path, data)
    (tmp_path / "research-log.csv").write_text("row_type,date\nsearch,2026-01-01\n")
    code = audit.main([str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "research-log.csv" in captured.err


def test_a_malformed_csv_is_unusable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    header = ",".join(audit.COLUMNS["people.csv"])
    (tmp_path / "people.csv").write_text(f'{header}\nP1,"unclosed name,no,\n')
    assert audit.main([str(tmp_path)]) == 2
    assert capsys.readouterr().out == ""


def test_a_short_row_is_unusable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    header = ",".join(audit.COLUMNS["people.csv"])
    (tmp_path / "people.csv").write_text(f"{header}\nP1,Ana\n")
    assert audit.main([str(tmp_path)]) == 2
    assert "people.csv" in capsys.readouterr().err


def test_a_missing_file_is_unusable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    (tmp_path / "sources.csv").unlink()
    assert audit.main([str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "sources.csv" in captured.err


def test_a_missing_column_is_unusable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    (tmp_path / "sources.csv").write_text("source_id,citation,kind,locator\n")
    assert audit.main([str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "sha256" in captured.err


def test_an_empty_file_is_unusable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    (tmp_path / "people.csv").write_text("")
    assert audit.main([str(tmp_path)]) == 2


def test_a_file_that_is_not_utf8_is_unusable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_registers(tmp_path)
    (tmp_path / "people.csv").write_bytes(b"person_id,name\n\xff\xfe\n")
    assert audit.main([str(tmp_path)]) == 2


def test_the_audit_never_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    audit.main([str(tmp_path)])
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_a_relationship_between_a_person_and_themselves_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(person_a="P1", person_b="P1")
    code, out = run(tmp_path, data, capsys)
    assert code == 1
    assert "[relationship-same-person]" in out


def test_an_identity_conclusion_may_repeat_a_person(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = copy.deepcopy(CLEAN)
    data["conclusions.csv"] = conclusion(kind="identity", person_a="P1", person_b="P1")
    code, _ = run(tmp_path, data, capsys)
    assert code == 0


def test_a_derivative_of_the_one_original_does_not_silence_single_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # S5 is a derivative copy of S1; T5 and T3 add sources but no second original.
    data = copy.deepcopy(CLEAN)
    data["sources.csv"].append(
        {
            "source_id": "S5",
            "citation": "Fictional certificate copied from the S1 entry",
            "kind": "derivative",
            "locator": "no. 8",
            "how_obtained": "archive",
            "local_copy_path": "",
            "sha256": "",
        }
    )
    data["statements.csv"].append(
        {
            "statement_id": "T5",
            "source_id": "S5",
            "person_as_written": "Ana, daughter of Pieter",
            "event": "baptism",
            "date_as_written": "3 March 1851",
            "place_as_written": "Alderbrook",
            "informant": "clerk",
            "informant_closeness": "copied",
            "information": "second-hand",
        }
    )
    data["conclusions.csv"] = conclusion(statements_for="T1;T5;T3", proof_level="probable")
    code, out = run(tmp_path, data, capsys)
    assert code == 0
    assert "[single-source]" in out
    assert "0 errors, 1 warnings" in out


def test_the_documented_out_of_scope_value_is_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Feed the value the documentation tells the user to type, read from the docs
    # themselves, so the prose and the script cannot drift apart again.
    skill_dir = SCRIPT.parent.parent
    logging_doc = (skill_dir / "references/searching-and-logging.md").read_text()
    report = (skill_dir / "assets/researcher-report.md").read_text()
    skill = (skill_dir / "SKILL.md").read_text()
    assert "- **out-of-scope:**" in logging_doc
    assert "out-of-scope]" in report
    assert "`out-of-scope`" in skill
    value = "out-of-scope"
    data = copy.deepcopy(CLEAN)
    data["research-log.csv"][1]["final_state"] = value
    data["research-log.csv"][1]["reason"] = "a minor, not searched online"
    code, out = run(tmp_path, data, capsys)
    assert code == 0, out
