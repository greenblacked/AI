"""The SkillSpector gate: what blocks, what is accepted, and what fails closed.

The job behind it scans one skill per process and writes a SARIF report and an exit code
for each. Every case here builds that layout in a temporary directory, the way the job
leaves it, and runs the gate over it — so a scan that did not happen is tested as such,
not only a finding that did.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.conftest import REPO, load_script

gate = load_script("skill_scan_gate.py")

SKILL = "plugins/demo/skills/sample"
OTHER = "plugins/demo/skills/other"


def result(rule="PE3", uri="SKILL.md", line=7, finding="~/.ssh/id_rsa", severity="HIGH"):
    props = {"severity": severity}
    if finding is not None:
        props["finding"] = finding
    return {
        "ruleId": rule,
        "message": {"text": "Credential Access"},
        "level": "error",
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": line},
                }
            }
        ],
        "properties": props,
    }


def sarif(*results, successful=True):
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "skillspector"}},
                "results": list(results),
                "invocations": [{"executionSuccessful": successful}],
            }
        ],
    }


def entry(
    rule="PE3",
    path=f"{SKILL}/SKILL.md",
    match="~/.ssh/id_rsa",
    cls="FP-defensive",
    reason="Named as a path never to read.",
):
    return {"rule_id": rule, "path": path, "match": match, "class": cls, "reason": reason}


def lay_out(tmp_path, reports, entries=(), rc=None):
    """Write a results directory, manifest and accepted list; return the gate's arguments."""
    results = tmp_path / "results"
    results.mkdir()
    manifest = tmp_path / "skills.txt"
    manifest.write_text("".join(f"{skill}\n" for skill in reports), encoding="utf-8")
    for skill, report in reports.items():
        name = skill.split("\t")[0] if "\t" in skill else gate.stem(skill)
        if report is not None:
            text = report if isinstance(report, str) else json.dumps(report)
            (results / f"{name}.sarif").write_text(text, encoding="utf-8")
        code = (rc or {}).get(skill, "0")
        if code is not None:
            (results / f"{name}.rc").write_text(f"{code}\n", encoding="utf-8")
    accepted = tmp_path / "accepted.json"
    accepted.write_text(json.dumps({"entries": list(entries)}), encoding="utf-8")
    return ["--manifest", str(manifest), "--results", str(results), "--accepted", str(accepted)]


def test_a_new_high_finding_fails_with_an_annotation_on_its_line(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result())})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert f"::error file={SKILL}/SKILL.md,line=7,title=SkillSpector PE3::HIGH PE3" in out
    assert "1 new" in out


def test_a_new_critical_finding_fails_too(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result(rule="P5", severity="CRITICAL"))})
    assert gate.main(args) == 1
    assert "CRITICAL P5 finding not in" in capsys.readouterr().out


def test_an_accepted_finding_passes(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result())}, [entry()])
    assert gate.main(args) == 0
    assert "0 new" in capsys.readouterr().out


def test_an_accepted_key_ignores_the_line_so_an_edit_above_it_stays_green(tmp_path):
    args = lay_out(tmp_path, {SKILL: sarif(result(line=90))}, [entry()])
    assert gate.main(args) == 0


def test_the_match_is_compared_with_its_whitespace_collapsed(tmp_path):
    reflowed = result(rule="TM1", finding="curl --resolve`\n  pins   a\thostname")
    accepted = entry(rule="TM1", match="curl --resolve` pins a hostname")
    args = lay_out(tmp_path, {SKILL: sarif(reflowed)}, [accepted])
    assert gate.main(args) == 0


def test_different_matched_text_under_the_same_rule_and_file_is_new(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result(finding="~/.aws/credentials"))}, [entry()])
    assert gate.main(args) == 1
    assert "~/.aws/credentials" in capsys.readouterr().out


def test_medium_and_low_findings_never_gate(tmp_path):
    args = lay_out(
        tmp_path,
        {SKILL: sarif(result(severity="MEDIUM"), result(rule="TM1", severity="LOW"))},
    )
    assert gate.main(args) == 0


def test_an_error_level_result_without_a_severity_is_treated_as_high(tmp_path):
    unlabelled = result()
    del unlabelled["properties"]["severity"]
    args = lay_out(tmp_path, {SKILL: sarif(unlabelled)})
    assert gate.main(args) == 1


def test_the_message_is_the_key_only_when_no_matched_text_exists(tmp_path):
    args = lay_out(
        tmp_path,
        {SKILL: sarif(result(finding=None))},
        [entry(match="Credential Access")],
    )
    assert gate.main(args) == 0


def test_a_reference_file_is_keyed_by_its_repository_path(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result(uri="references/red-flags.md", line=85))})
    assert gate.main(args) == 1
    assert f"file={SKILL}/references/red-flags.md,line=85" in capsys.readouterr().out


def test_a_missing_sarif_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(), OTHER: None})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "found 1 SARIF report(s) for 2 skill(s) scanned" in out
    assert f"no readable SARIF for {OTHER}" in out


def test_an_unparseable_sarif_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: "{not json"})
    assert gate.main(args) == 1
    assert "SkillSpector scan failed" in capsys.readouterr().out


def test_a_sarif_with_no_runs_fails(tmp_path):
    assert gate.main(lay_out(tmp_path, {SKILL: {"version": "2.1.0", "runs": []}})) == 1


def test_an_unsuccessful_execution_fails(tmp_path):
    assert gate.main(lay_out(tmp_path, {SKILL: sarif(successful=False)})) == 1


def test_a_location_outside_the_skill_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result(uri="../other/SKILL.md"))})
    assert gate.main(args) == 1
    assert "outside the skill" in capsys.readouterr().out


def test_a_result_with_no_location_is_keyed_on_the_skill(tmp_path):
    bare = result()
    del bare["locations"]
    args = lay_out(tmp_path, {SKILL: sarif(bare)}, [entry(path=SKILL)])
    assert gate.main(args) == 0


def test_a_gating_result_with_no_rule_fails(tmp_path):
    nameless = result()
    del nameless["ruleId"]
    assert gate.main(lay_out(tmp_path, {SKILL: sarif(nameless)})) == 1


def test_a_scan_that_exited_2_fails_even_with_a_clean_report(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()}, rc={SKILL: "2"})
    assert gate.main(args) == 1
    assert "SkillSpector exited 2 scanning" in capsys.readouterr().out


def test_a_scan_that_left_no_exit_code_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()}, rc={SKILL: None})
    assert gate.main(args) == 1
    assert "left no exit code" in capsys.readouterr().out


def test_exit_1_is_a_risk_score_not_an_error(tmp_path):
    args = lay_out(tmp_path, {SKILL: sarif(result())}, [entry()], rc={SKILL: "1"})
    assert gate.main(args) == 0


def test_a_stray_report_the_manifest_does_not_name_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "results" / "demo__stray.sarif").write_text(json.dumps(sarif()))
    assert gate.main(args) == 1
    assert "found 2 SARIF report(s) for 1 skill(s)" in capsys.readouterr().out


def test_an_accepted_entry_without_a_reason_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result())}, [entry(reason="  ")])
    assert gate.main(args) == 1
    assert "accepted entry 1 has no reason" in capsys.readouterr().out


def test_an_accepted_entry_marked_real_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(result())}, [entry(cls="REAL")])
    assert gate.main(args) == 1
    assert "never a real one" in capsys.readouterr().out


def test_a_repeated_or_malformed_accepted_entry_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()}, [entry(), entry(), "not an object"])
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "accepted entry 2 repeats an earlier entry" in out
    assert "accepted entry 3 is not an object" in out


def test_an_accepted_list_that_is_not_a_list_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "accepted.json").write_text("[]", encoding="utf-8")
    assert gate.main(args) == 1
    assert "has no `entries` list" in capsys.readouterr().out


def test_an_unreadable_accepted_list_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "accepted.json").write_text("{", encoding="utf-8")
    assert gate.main(args) == 1
    assert "cannot read the accepted list" in capsys.readouterr().out


def test_a_stale_accepted_entry_is_reported_not_failed(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()}, [entry()])
    assert gate.main(args) == 0
    out = capsys.readouterr().out
    assert f"::notice file={SKILL}/SKILL.md,title=Stale SkillSpector entry::" in out
    assert "1 stale accepted entry," in out


def test_an_entry_for_a_skill_this_run_did_not_scan_is_not_stale(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()}, [entry(path=f"{OTHER}/SKILL.md")])
    assert gate.main(args) == 0
    assert "Stale" not in capsys.readouterr().out


def test_an_empty_manifest_passes_with_a_notice(tmp_path, capsys):
    assert gate.main(lay_out(tmp_path, {})) == 0
    assert "::notice title=SkillSpector gate::no skill to scan" in capsys.readouterr().out


def test_a_manifest_line_that_is_not_a_skill_directory_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "skills.txt").write_text(f"{SKILL}\n{SKILL}\n../etc\n", encoding="utf-8")
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "'../etc', which is not a skill directory" in out
    assert "more than once" in out


def test_a_missing_manifest_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "skills.txt").unlink()
    assert gate.main(args) == 1
    assert "cannot read the manifest" in capsys.readouterr().out


def test_matched_text_cannot_open_a_workflow_command(tmp_path, capsys):
    # The matched text is whatever a pull request wrote into a skill. Collapsing its
    # whitespace already keeps it on one line; the legacy marker is broken as well.
    hostile = "x\n::warning::forged ##[group]y, 100%"
    args = lay_out(tmp_path, {SKILL: sarif(result(finding=hostile))})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "::warning" not in out.replace("x ::warning::forged", "")
    assert "x ::warning::forged ## [group]y, 100%25" in out
    assert not any(row.startswith("::warning") for row in out.splitlines())


def test_annotation_text_is_escaped(capsys):
    gate.annotate("error", "a\nb ##[x] 5%", file="p,q:r", line=3, title="t")
    out = capsys.readouterr().out
    assert out == "::error file=p%2Cq%3Ar,line=3,title=t::a%0Ab ## [x] 5%25\n"


def test_a_long_match_is_shortened_in_the_annotation():
    assert len(gate.shorten("x" * 500)) == gate.MATCH_LIMIT


def test_the_committed_accepted_list_is_well_formed():
    # The gate reads this file on every run; a malformed entry there fails every pull
    # request, so it is checked here, before it can merge.
    path = REPO / ".github" / "skill-scan" / "skillspector-accepted.json"
    accepted, problems = gate.read_accepted(path)
    assert problems == []
    assert accepted
    for _, entry_path, match in accepted:
        # A skill file, or the source of a subagent or command read through its shim.
        assert entry_path.startswith("plugins/") or re.fullmatch(
            r"\.claude/(agents|commands)/[a-z0-9-]+\.md", entry_path
        ), entry_path
        assert match == gate.normalise(match)


def test_a_run_or_result_of_the_wrong_shape_fails(tmp_path):
    bad_run = {"version": "2.1.0", "runs": ["not a run"]}
    bad_result = sarif()
    bad_result["runs"][0]["results"] = ["not a result"]
    args = lay_out(tmp_path, {SKILL: bad_run, OTHER: bad_result})
    assert gate.main(args) == 1


def test_a_location_with_no_uri_is_keyed_on_the_skill_at_its_line(tmp_path):
    nameless = result()
    nameless["locations"][0]["physicalLocation"]["artifactLocation"] = {}
    args = lay_out(tmp_path, {SKILL: sarif(nameless)}, [entry(path=SKILL)])
    assert gate.main(args) == 0


def test_an_annotation_needs_no_properties(capsys):
    gate.annotate("notice", "plain")
    assert capsys.readouterr().out == "::notice::plain\n"


def with_completeness(report, value):
    """Set `analysisCompleteness` where SkillSpector 2.13.1 writes it: on the invocation."""
    invocation = report["runs"][0]["invocations"][0]
    invocation["properties"] = {"analysisCompleteness": value}
    return report


def test_a_scan_that_left_a_file_entirely_uninspected_fails(tmp_path, capsys):
    report = with_completeness(sarif(), {"entirelyUninspectedFiles": 2})
    assert gate.main(lay_out(tmp_path, {SKILL: report})) == 1
    out = capsys.readouterr().out
    assert f"::error file={SKILL}/SKILL.md,title=SkillSpector scan incomplete::" in out
    assert "left 2 file(s) entirely uninspected" in out


def test_a_scan_with_every_file_inspected_passes(tmp_path):
    complete = {"entirelyUninspectedFiles": 0, "partiallyInspectedFiles": 1}
    report = with_completeness(sarif(), complete)
    assert gate.main(lay_out(tmp_path, {SKILL: report})) == 0


def test_a_report_without_the_completeness_field_passes(tmp_path):
    report = with_completeness(sarif(), {"isComplete": True})
    other = sarif()
    other["runs"][0]["invocations"][0]["properties"] = {}
    assert gate.main(lay_out(tmp_path, {SKILL: report, OTHER: other})) == 0


def test_an_uninspected_count_that_is_not_a_count_fails(tmp_path, capsys):
    reports = {
        SKILL: with_completeness(sarif(), {"entirelyUninspectedFiles": "2"}),
        OTHER: with_completeness(sarif(), "complete"),
    }
    assert gate.main(lay_out(tmp_path, reports)) == 1
    assert "2 other failure(s)" in capsys.readouterr().out


# SkillSpector's AE1 is a coverage finding: a referenced file whose inspection ended
# `partial`. The reason sits in `properties.evidence.reasons[].reason_code`, and the same
# ledger outcome is echoed in the invocation's `toolExecutionNotifications`. These shapes
# are trimmed from real 2.13.1 reports: `runtime_limit` is a wall-clock budget running
# out, which depends on the runner rather than the skill; `static_parse_limit` and
# `obfuscated_instruction_text` are the content itself, the kind the accepted list holds.
def coverage(target="references/guide.md", reasons=("runtime_limit",)):
    finding = result(rule="AE1", line=21, finding=f"{target} (partial)")
    finding["message"] = {"text": "Referenced artifact was not completely inspected"}
    finding["properties"]["evidence"] = {
        "target_path": target,
        "target_disposition": "partial",
        "reasons": [{"reason_code": code, "phase": "artifact"} for code in reasons],
    }
    return finding


def coverage_entry(target="references/guide.md"):
    return entry(
        rule="AE1",
        match=f"{target} (partial)",
        cls="FP-scanner-limitation",
        reason="The file is long; the parser stops before its end.",
    )


def with_notification(report, reason_code, phase="artifact"):
    invocation = report["runs"][0]["invocations"][0]
    invocation.setdefault("toolExecutionNotifications", []).append(
        {
            "message": {"text": "Inspection reached its configured runtime limit."},
            "level": "warning",
            "properties": {"outcome": "partial", "phase": phase, "reasonCode": reason_code},
        }
    )
    return report


def first_pass(tmp_path, reports, entries=()):
    """The job's first gate run: incomplete skills go to a file instead of failing."""
    out = tmp_path / "rescan.txt"
    return [*lay_out(tmp_path, reports, entries), "--incomplete-out", str(out)], out


def test_a_runtime_limited_finding_is_set_aside_for_a_rescan(tmp_path, capsys):
    # Even an accepted entry with the very same key must not let a scan that ran out of
    # time count as reviewed: what it missed was never looked at.
    args, out = first_pass(tmp_path, {SKILL: sarif(coverage())}, [coverage_entry()])
    assert gate.main(args) == gate.RESCAN
    assert out.read_text(encoding="utf-8") == f"{SKILL}\n"
    printed = capsys.readouterr().out
    assert f"::notice file={SKILL}/SKILL.md,title=SkillSpector scan incomplete::" in printed
    assert "rescan" in printed
    # The accepted entry was not consumed, and is not stale either: the skill was not judged.
    assert "Stale" not in printed


def test_a_runtime_limited_finding_on_the_final_pass_fails_as_incomplete(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(coverage())}, [coverage_entry()])
    assert gate.main(args) == 1
    printed = capsys.readouterr().out
    assert f"::error file={SKILL}/SKILL.md,title=SkillSpector scan incomplete::" in printed
    assert "ran out of time" in printed
    assert "re-run the job" in printed


def test_a_content_coverage_finding_still_uses_the_accepted_list(tmp_path, capsys):
    report = with_notification(
        sarif(coverage(reasons=("static_parse_limit",))), "static_parse_limit", "static"
    )
    args, out = first_pass(tmp_path, {SKILL: report}, [coverage_entry()])
    assert gate.main(args) == 0
    assert out.read_text(encoding="utf-8") == ""


def test_an_unaccepted_content_coverage_finding_is_new(tmp_path, capsys):
    report = sarif(coverage(reasons=("obfuscated_instruction_text",)))
    args, out = first_pass(tmp_path, {SKILL: report})
    assert gate.main(args) == 1
    assert "HIGH AE1 finding not in" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8") == ""


def test_a_new_finding_elsewhere_fails_the_first_pass_despite_a_rescan(tmp_path, capsys):
    args, out = first_pass(tmp_path, {SKILL: sarif(coverage()), OTHER: sarif(result())})
    assert gate.main(args) == 1
    assert out.read_text(encoding="utf-8") == f"{SKILL}\n"
    printed = capsys.readouterr().out
    assert f"::error file={OTHER}/SKILL.md,line=7,title=SkillSpector PE3::HIGH PE3" in printed
    assert "1 new" in printed


def test_a_finding_with_a_runtime_and_a_content_reason_is_incomplete(tmp_path):
    mixed = coverage(reasons=("static_parse_limit", "runtime_limit"))
    args, out = first_pass(tmp_path, {SKILL: sarif(mixed)}, [coverage_entry()])
    assert gate.main(args) == gate.RESCAN
    assert out.read_text(encoding="utf-8") == f"{SKILL}\n"


def test_a_runtime_limit_with_no_finding_is_incomplete_too(tmp_path):
    # A budget can run out where no AE1 follows, as SkillSpector's structured-skill pass
    # does: the report is clean only because it stopped looking.
    report = with_notification(sarif(), "runtime_limit", "structured_skill")
    args, out = first_pass(tmp_path, {SKILL: report, OTHER: sarif()})
    assert gate.main(args) == gate.RESCAN
    assert out.read_text(encoding="utf-8") == f"{SKILL}\n"
    final = tmp_path / "final"
    final.mkdir()
    assert gate.main(lay_out(final, {SKILL: report})) == 1


def test_a_runtime_limit_takes_precedence_over_an_uninspected_count(tmp_path):
    report = with_completeness(
        with_notification(sarif(), "runtime_limit", "cache"), {"entirelyUninspectedFiles": 7}
    )
    args, _ = first_pass(tmp_path, {SKILL: report})
    assert gate.main(args) == gate.RESCAN


def test_a_clean_first_pass_writes_an_empty_rescan_list(tmp_path):
    args, out = first_pass(tmp_path, {SKILL: sarif(result())}, [entry()])
    out.write_text("stale\n", encoding="utf-8")
    assert gate.main(args) == 0
    assert out.read_text(encoding="utf-8") == ""


def test_an_unwritable_rescan_list_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(coverage())})
    missing = tmp_path / "no-such-directory" / "rescan.txt"
    assert gate.main([*args, "--incomplete-out", str(missing)]) == 1
    assert "cannot write the rescan list" in capsys.readouterr().out


def test_runtime_limit_evidence_of_the_wrong_shape_fails_closed(tmp_path, capsys):
    # A reasons field that is not a list, or an entry that is not an object, cannot be
    # read for a runtime limit. Skipping it would let a time-limited AE1 reach the
    # accepted list, so the report is refused as unreadable instead.
    not_a_list = sarif(coverage())
    not_a_list["runs"][0]["results"][0]["properties"]["evidence"]["reasons"] = "runtime_limit"
    not_an_object = sarif(coverage())
    not_an_object["runs"][0]["results"][0]["properties"]["evidence"]["reasons"] = ["runtime_limit"]
    for number, report in enumerate((not_a_list, not_an_object)):
        (tmp_path / str(number)).mkdir()
        args = lay_out(tmp_path / str(number), {SKILL: report}, [coverage_entry()])
        assert gate.main(args) == 1
        printed = capsys.readouterr().out
        assert "title=SkillSpector scan failed" in printed
        assert "reasons" in printed


# A subagent or command is scanned as a one-file skill, a "shim", and its manifest line
# is `<id>\t<source path>`. The gate reports and accepts against the source path, so an
# accepted entry names the file a reviewer opens, not a directory that exists only on the
# runner.
AGENT_SRC = "plugins/demo/agents/helper.md"
AGENT_LINE = f"agent--demo--helper\t{AGENT_SRC}"
COMMAND_SRC = "plugins/demo/commands/run-it.md"
COMMAND_LINE = f"command--demo--run-it\t{COMMAND_SRC}"
REPO_AGENT_SRC = ".claude/agents/builder.md"
REPO_AGENT_LINE = f"agent--claude--builder\t{REPO_AGENT_SRC}"


def test_a_shim_finding_is_reported_on_its_source_path_and_line(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif(result(line=7))})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert f"::error file={AGENT_SRC},line=7,title=SkillSpector PE3::HIGH PE3" in out
    assert "agent--demo--helper" not in out.replace(AGENT_LINE, "")


def test_an_accepted_entry_on_the_source_path_matches_a_shim_finding(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif(result())}, [entry(path=AGENT_SRC)])
    assert gate.main(args) == 0
    assert "0 new" in capsys.readouterr().out


def test_an_entry_on_the_shim_directory_does_not_match(tmp_path):
    args = lay_out(
        tmp_path,
        {AGENT_LINE: sarif(result())},
        [entry(path="agent--demo--helper/SKILL.md")],
    )
    assert gate.main(args) == 1


def test_a_repository_level_definition_is_keyed_on_its_claude_path(tmp_path):
    args = lay_out(tmp_path, {REPO_AGENT_LINE: sarif(result())}, [entry(path=REPO_AGENT_SRC)])
    assert gate.main(args) == 0


def test_a_command_shim_line_is_mapped_back_past_the_inserted_name(tmp_path, capsys):
    # The shim has `name: <id>` as its second line, so shim line N is source line N - 1.
    report = sarif(result(line=9), result(rule="TM1", line=2), result(rule="E2", line=1))
    assert gate.main(lay_out(tmp_path, {COMMAND_LINE: report})) == 1
    out = capsys.readouterr().out
    assert f"file={COMMAND_SRC},line=8,title=SkillSpector PE3" in out
    assert f"file={COMMAND_SRC},line=1,title=SkillSpector TM1" in out
    assert f"file={COMMAND_SRC},line=1,title=SkillSpector E2" in out


def test_an_agent_shim_line_is_not_shifted(tmp_path, capsys):
    assert gate.main(lay_out(tmp_path, {AGENT_LINE: sarif(result(line=9))})) == 1
    assert f"file={AGENT_SRC},line=9," in capsys.readouterr().out


@pytest.mark.parametrize("uri", ["references/notes.md", "../other/SKILL.md", "/etc/passwd", "a:b"])
def test_a_foreign_uri_in_a_shim_fails_closed(tmp_path, capsys, uri):
    args = lay_out(tmp_path, {AGENT_LINE: sarif(result(uri=uri))}, [entry(path=AGENT_SRC)])
    assert gate.main(args) == 1
    assert "outside the skill" in capsys.readouterr().out


def test_a_shim_result_with_no_location_is_keyed_on_its_source(tmp_path):
    bare = result()
    del bare["locations"]
    args = lay_out(tmp_path, {AGENT_LINE: sarif(bare)}, [entry(path=AGENT_SRC)])
    assert gate.main(args) == 0


def test_skills_and_shims_are_judged_together(tmp_path, capsys):
    args = lay_out(
        tmp_path,
        {SKILL: sarif(), AGENT_LINE: sarif(), COMMAND_LINE: sarif(result(rule="P5"))},
    )
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "1 new" in out


def test_the_count_check_includes_shims(tmp_path, capsys):
    args = lay_out(tmp_path, {SKILL: sarif(), AGENT_LINE: None, COMMAND_LINE: sarif()})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert "found 2 SARIF report(s) for 1 skill(s) and 2 definition(s) scanned" in out
    assert "no readable SARIF for plugins/demo/agents/helper.md" in out


def test_a_shim_scan_that_exited_2_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif()}, rc={AGENT_LINE: "2"})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert f"SkillSpector exited 2 scanning {AGENT_SRC}" in out


def test_a_stale_entry_on_a_scanned_shim_source_is_reported(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif()}, [entry(path=AGENT_SRC)])
    assert gate.main(args) == 0
    assert "::notice file=plugins/demo/agents/helper.md,title=Stale SkillSpector entry" in (
        capsys.readouterr().out
    )


def test_an_entry_for_a_definition_this_run_did_not_scan_is_not_stale(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif()}, [entry(path=COMMAND_SRC)])
    assert gate.main(args) == 0
    assert "Stale" not in capsys.readouterr().out


def test_a_shim_whose_scan_ran_out_of_time_is_listed_by_its_manifest_line(tmp_path, capsys):
    reports = {AGENT_LINE: with_notification(sarif(), "runtime_limit"), SKILL: sarif()}
    args, out = first_pass(tmp_path, reports)
    assert gate.main(args) == 3
    assert out.read_text(encoding="utf-8") == f"{AGENT_LINE}\n"
    assert f"::notice file={AGENT_SRC},title=SkillSpector scan incomplete::" in (
        capsys.readouterr().out
    )


NESTED_SRC = "plugins/demo/commands/release/notes.md"
NESTED_LINE = f"command--demo--release--notes\t{NESTED_SRC}"
DEEP_SRC = ".claude/commands/team/review/pr.md"
DEEP_LINE = f"command--claude--team--review--pr\t{DEEP_SRC}"


def test_a_nested_command_shim_maps_back_to_its_source_and_line(tmp_path, capsys):
    args = lay_out(tmp_path, {NESTED_LINE: sarif(result(line=9)), DEEP_LINE: sarif(result(line=3))})
    assert gate.main(args) == 1
    out = capsys.readouterr().out
    assert f"file={NESTED_SRC},line=8," in out
    assert f"file={DEEP_SRC},line=2," in out


def test_an_accepted_entry_on_a_nested_commands_source_matches(tmp_path):
    args = lay_out(tmp_path, {NESTED_LINE: sarif(result())}, [entry(path=NESTED_SRC)])
    assert gate.main(args) == 0


@pytest.mark.parametrize(
    "line",
    [
        f"command--demo--notes\t{NESTED_SRC}",  # the folder is missing from the id
        "command--demo--release--notes\tplugins/demo/commands/notes.md",
        "agent--demo--nested--deep\tplugins/demo/agents/nested/deep.md",  # agents stay flat
        "command--demo--Release--notes\tplugins/demo/commands/Release/notes.md",
        "command--demo--release--notes\tplugins/demo/commands/release//notes.md",
    ],
)
def test_a_nested_manifest_line_that_does_not_fit_its_source_fails(tmp_path, capsys, line):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "skills.txt").write_text(f"{line}\n", encoding="utf-8")
    assert gate.main(args) == 1
    assert "manifest names" in capsys.readouterr().out


@pytest.mark.parametrize(
    "line",
    [
        "agent--demo--helper",  # an id with no source
        f"agent--demo--helper\t{AGENT_SRC}\textra",
        f"agent--demo--other\t{AGENT_SRC}",  # id does not belong to the source
        f"command--demo--helper\t{AGENT_SRC}",  # kind does not match the directory
        f"agent--claude--helper\t{AGENT_SRC}",
        f"agent--demo--helper\t../{AGENT_SRC}",
        "agent--demo--helper\tplugins/demo/agents/evals/helper.md",
        "agent--demo--helper\tplugins/demo/skills/x/SKILL.md",
        "agent--Demo--Helper\tplugins/Demo/agents/Helper.md",
        # `--` is the separator, so a part may not contain one.
        "agent--demo--two--hyphens\tplugins/demo/agents/two--hyphens.md",
        "agent--two--hy--x\tplugins/two--hy/agents/x.md",
        f" agent--demo--helper\t{AGENT_SRC}",
        f"agent--demo--helper\t{AGENT_SRC} ",
    ],
)
def test_a_malformed_shim_manifest_line_fails(tmp_path, capsys, line):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "skills.txt").write_text(f"{line}\n", encoding="utf-8")
    assert gate.main(args) == 1
    assert "manifest names" in capsys.readouterr().out


def test_a_shim_listed_twice_or_by_a_clashing_id_fails(tmp_path, capsys):
    args = lay_out(tmp_path, {AGENT_LINE: sarif()})
    (tmp_path / "skills.txt").write_text(f"{AGENT_LINE}\n{AGENT_LINE}\n", encoding="utf-8")
    assert gate.main(args) == 1
    assert "more than once" in capsys.readouterr().out


def test_the_shim_id_scheme_matches_the_script_that_writes_it():
    # Two implementations of one scheme, in a script and in the gate that cross-checks the
    # manifest: they must agree on every definition the repository has today.
    shims = load_script("definition_shims.py")
    found = shims.list_definitions(REPO)
    plugins = shims.plugin_names(REPO)
    assert found
    for path in found:
        line = f"{shims.definition_id(path, plugins)}\t{path}"
        assert gate.SHIM_LINE_RE.fullmatch(line), line
        assert gate.expected_id(path) == line.split("\t")[0]


# Claude Code loads a commands/ README.md as a command, so it is scanned like one. One
# with no frontmatter is given four lines by its shim, and map.tsv records that as a
# third column the manifest carries through.
README_SRC = "plugins/demo/commands/README.md"
README_ID = "command--demo--readme"
README_BARE = f"{README_ID}\t{README_SRC}\t4"
README_FM = f"{README_ID}\t{README_SRC}\t1"


def test_a_frontmatterless_readme_is_mapped_back_past_the_four_synthesised_lines(tmp_path, capsys):
    report = sarif(result(line=9), result(rule="TM1", line=3), result(rule="E2", line=5))
    assert gate.main(lay_out(tmp_path, {README_BARE: report})) == 1
    out = capsys.readouterr().out
    assert f"file={README_SRC},line=5,title=SkillSpector PE3" in out
    assert f"file={README_SRC},line=1,title=SkillSpector TM1" in out
    assert f"file={README_SRC},line=1,title=SkillSpector E2" in out


def test_a_readme_with_frontmatter_is_shifted_by_one_like_any_command(tmp_path, capsys):
    assert gate.main(lay_out(tmp_path, {README_FM: sarif(result(line=9))})) == 1
    assert f"file={README_SRC},line=8," in capsys.readouterr().out


def test_an_accepted_entry_on_a_command_readme_matches(tmp_path):
    args = lay_out(tmp_path, {README_BARE: sarif(result())}, [entry(path=README_SRC)])
    assert gate.main(args) == 0


def test_an_unaccepted_finding_in_a_command_readme_fails_the_gate(tmp_path, capsys):
    assert gate.main(lay_out(tmp_path, {README_BARE: sarif(result())})) == 1
    assert f"file={README_SRC}," in capsys.readouterr().out


def test_a_manifest_line_without_the_offset_column_gets_the_commands_default(tmp_path, capsys):
    bare = f"{README_ID}\t{README_SRC}"
    assert gate.main(lay_out(tmp_path, {bare: sarif(result(line=9))})) == 1
    assert f"file={README_SRC},line=8," in capsys.readouterr().out


@pytest.mark.parametrize(
    "line",
    [
        f"{README_ID}\t{README_SRC}\t2",  # only 1 or 4 is something the script writes
        f"{README_ID}\t{README_SRC}\t-1",
        f"{README_ID}\t{README_SRC}\t04",
        f"{README_ID}\t{README_SRC}\t",
        f"{README_ID}\t{README_SRC}\t1\t1",
        f"command--demo--run-it\t{COMMAND_SRC}\t4",  # only a readme is given frontmatter
        f"{AGENT_LINE}\t1",  # an agent's shim adds nothing
        "command--demo--readme\tplugins/demo/commands/Readme.md\t1",
        f"command--demo--README\t{README_SRC}\t1",  # the id is lowercase
    ],
)
def test_a_manifest_offset_the_script_would_not_write_fails(tmp_path, capsys, line):
    args = lay_out(tmp_path, {SKILL: sarif()})
    (tmp_path / "skills.txt").write_text(f"{line}\n", encoding="utf-8")
    assert gate.main(args) == 1
    assert "manifest names" in capsys.readouterr().out


def test_a_lowercase_command_readme_with_the_four_line_offset_is_accepted(tmp_path, capsys):
    src = ".claude/commands/team/readme.md"
    line = f"command--claude--team--readme\t{src}\t4"
    assert gate.main(lay_out(tmp_path, {line: sarif(result(line=9))})) == 1
    assert f"file={src},line=5,title=SkillSpector PE3" in capsys.readouterr().out


def test_an_agents_readme_is_not_a_definition_to_the_gate():
    assert gate.expected_id("plugins/demo/agents/README.md") is None
    assert gate.expected_id(README_SRC) == README_ID


def test_the_gate_and_the_script_agree_on_what_a_readme_is(tmp_path):
    shims = load_script("definition_shims.py")
    for source in (README_SRC, ".claude/commands/team/readme.md", ".claude/commands/README.md"):
        assert gate.expected_id(source) == shims.definition_id(source, {"demo"})
