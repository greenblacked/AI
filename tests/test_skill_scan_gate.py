"""The SkillSpector gate: what blocks, what is accepted, and what fails closed.

The job behind it scans one skill per process and writes a SARIF report and an exit code
for each. Every case here builds that layout in a temporary directory, the way the job
leaves it, and runs the gate over it — so a scan that did not happen is tested as such,
not only a finding that did.
"""

from __future__ import annotations

import json

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
        name = gate.stem(skill)
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
        assert entry_path.startswith("plugins/")
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
