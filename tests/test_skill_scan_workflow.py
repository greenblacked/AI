"""Two shell steps in `security.yml`'s skill-scan jobs, run for real.

`Choose the skills to scan` decides what SkillSpector reads on a pull request, so a
selection bug is a skill that silently goes unscanned. `Scan every skill` prints a
summary of Cisco's findings into the job log, where a path or rule id the report carries
verbatim could otherwise open a workflow command. `Gate on new high and critical
findings` rescans a skill whose scan ran out of time, so a runner stall neither passes
nor fails a skill on what the scanner never read. All are bash embedded in the workflow,
so each is pulled out of the real file and executed, the way `test_evals_workflow.py`
does, rather than copied into a second version that would drift from the one CI runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO
from tests.test_evals_workflow import _extract_run_block

WORKFLOW = REPO / ".github" / "workflows" / "security.yml"
ALPHA = "plugins/demo/skills/alpha"
BETA = "plugins/demo/skills/beta"
SCAN_CONFIG = (
    ".github/workflows/security.yml",
    ".github/skill-scan/skillspector-accepted.json",
    ".github/requirements/skillspector.txt",
    "scripts/skill_scan_gate.py",
)
BASE_FILES = (
    f"{ALPHA}/SKILL.md",
    f"{ALPHA}/references/notes.md",
    f"{BETA}/SKILL.md",
    "plugins/demo/agents/helper.md",
    *SCAN_CONFIG,
)


def step(name: str) -> str:
    return _extract_run_block(WORKFLOW.read_text(encoding="utf-8"), name)


def git_env(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


def git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607 - relying on PATH, as the runner does
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()


@pytest.fixture
def scratch(tmp_path):
    """A repository with two skills, an agent and the scan configuration, committed once."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = git_env(tmp_path)
    git(repo, env, "init", "--quiet", "--initial-branch=main")
    for rel in BASE_FILES:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rel}\n", encoding="utf-8")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "--quiet", "-m", "base")
    return repo, env, git(repo, env, "rev-parse", "HEAD")


def choose(tmp_path, repo, env, *, event="pull_request", base_sha=""):
    """Commit whatever the test changed, run the step, and return it with its manifest."""
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "--quiet", "--allow-empty", "-m", "change")
    runner = tmp_path / "runner"
    runner.mkdir(exist_ok=True)
    result = subprocess.run(  # noqa: S603
        ["bash", "-c", step("Choose the skills to scan")],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=repo,
        env={**env, "RUNNER_TEMP": str(runner), "EVENT_NAME": event, "BASE_SHA": base_sha},
        check=False,
    )
    manifest = runner / "skillspector" / "skills.txt"
    lines = manifest.read_text(encoding="utf-8").splitlines() if manifest.exists() else None
    return result, lines


def test_a_reference_file_edit_selects_its_skill(tmp_path, scratch):
    repo, env, base = scratch
    (repo / ALPHA / "references" / "notes.md").write_text("changed\n", encoding="utf-8")
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == [ALPHA]


def test_a_renamed_skill_is_selected_at_its_new_path(tmp_path, scratch):
    repo, env, base = scratch
    git(repo, env, "mv", BETA, "plugins/demo/skills/gamma")
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == ["plugins/demo/skills/gamma"]


def test_a_deleted_skill_is_not_selected(tmp_path, scratch):
    repo, env, base = scratch
    git(repo, env, "rm", "-r", "--quiet", BETA)
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == []
    assert "changes no skill" in result.stdout


def test_an_agent_only_change_selects_nothing(tmp_path, scratch):
    repo, env, base = scratch
    (repo / "plugins/demo/agents/helper.md").write_text("changed\n", encoding="utf-8")
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == []


@pytest.mark.parametrize("config", SCAN_CONFIG)
def test_a_change_to_the_scan_configuration_scans_every_skill(tmp_path, scratch, config):
    repo, env, base = scratch
    (repo / config).write_text("changed\n", encoding="utf-8")
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == [ALPHA, BETA]
    assert "changes the skill scan configuration, so every skill is scanned" in result.stdout


def test_a_new_file_under_the_skill_scan_directory_scans_every_skill(tmp_path, scratch):
    repo, env, base = scratch
    (repo / ".github/skill-scan/README.md").write_text("new\n", encoding="utf-8")
    result, manifest = choose(tmp_path, repo, env, base_sha=base)
    assert result.returncode == 0, result.stderr
    assert manifest == [ALPHA, BETA]


def test_another_event_scans_every_skill(tmp_path, scratch):
    repo, env, _ = scratch
    result, manifest = choose(tmp_path, repo, env, event="push")
    assert result.returncode == 0, result.stderr
    assert manifest == [ALPHA, BETA]


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_a_symlink_under_plugins_fails_the_step(tmp_path, scratch, event):
    # A link inside a skill can point outside plugins/, so a later edit to its target
    # would change what is scanned without selecting the skill.
    repo, env, base = scratch
    (repo / ALPHA / "references" / "linked.md").symlink_to("../../../../../README.md")
    result, _ = choose(tmp_path, repo, env, event=event, base_sha=base)
    assert result.returncode == 1
    assert "::error title=skill scan::a symbolic link under plugins/" in result.stdout


@pytest.mark.parametrize("base_sha", ["", "HEAD", "main", "g" * 40, "A" * 40, "0" * 39])
def test_a_base_commit_that_is_not_forty_hex_digits_fails(tmp_path, scratch, base_sha):
    repo, env, _ = scratch
    result, _ = choose(tmp_path, repo, env, base_sha=base_sha)
    assert result.returncode == 1
    assert "::error title=skill scan::no usable base commit" in result.stdout


FAKE_SCANNER = """#!/bin/bash
set -Eeuo pipefail
while [ "$#" -gt 0 ]; do
  if [ "$1" = --output-json ]; then cp "$FAKE_REPORT" "$2"; fi
  shift
done
exit "$FAKE_RC"
"""


def run_cisco_scan(tmp_path, report: dict, rc: int = 0):
    runner = tmp_path / "runner"
    scanner = runner / "skill-scanner-venv" / "bin" / "skill-scanner"
    scanner.parent.mkdir(parents=True)
    scanner.write_text(FAKE_SCANNER, encoding="utf-8")
    scanner.chmod(0o755)
    crafted = tmp_path / "crafted.json"
    crafted.write_text(json.dumps(report), encoding="utf-8")
    return subprocess.run(  # noqa: S603
        ["bash", "-c", step("Scan every skill")],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "RUNNER_TEMP": str(runner),
            "FAKE_REPORT": str(crafted),
            "FAKE_RC": str(rc),
        },
        check=False,
    )


HOSTILE_REPORT = {
    "results": [
        {
            "skill_path": "plugins/x/skills/y\n::error title=forged::from a path",
            "findings": [
                {
                    "severity": "HIGH",
                    "rule_id": "R1\r\n##[error]forged from a rule id",
                    "file_path": "SKILL.md\n::add-mask::x",
                    "line_number": 3,
                },
                {
                    "severity": "CRITICAL",
                    "rule_id": "##[group]open",
                    "file_path": "a\r::stop-commands::token",
                    "line_number": 9,
                },
                {"severity": "MEDIUM", "rule_id": "M1", "file_path": "x", "line_number": 1},
            ],
        }
    ]
}


@pytest.mark.skipif(shutil.which("jq") is None, reason="the summary is a jq program")
def test_the_cisco_summary_cannot_open_a_workflow_command(tmp_path):
    result = run_cisco_scan(tmp_path, HOSTILE_REPORT)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    # One line per high or critical finding: a newline in a field cannot start another.
    assert len(lines) == 2, lines
    for line in lines:
        assert not line.lstrip().startswith("::"), line
        assert "##[" not in line, line
        assert "\r" not in line
    assert lines[0].startswith("  HIGH R1 ")
    assert lines[1].startswith("  CRITICAL ## [group]open ")


@pytest.mark.skipif(shutil.which("jq") is None, reason="the summary is a jq program")
def test_a_failing_cisco_scan_still_lists_its_findings_and_fails(tmp_path):
    report = {
        "results": [
            {
                "skill_path": "plugins/x/skills/y",
                "findings": [
                    {"severity": "HIGH", "rule_id": "R1", "file_path": "SKILL.md", "line_number": 4}
                ],
            }
        ]
    }
    result = run_cisco_scan(tmp_path, report, rc=1)
    assert result.returncode == 1
    assert "  HIGH R1 plugins/x/skills/y/SKILL.md:4" in result.stdout
    assert "::error title=cisco skill scan::skill-scanner exited 1" in result.stdout


# The rescan writes whichever report FAKE_REPORT names, and logs each call so a test can
# see which skills were rescanned and that the first pass's reports were not rescanned.
FAKE_SKILLSPECTOR = """#!/bin/bash
set -Eeuo pipefail
printf '%s\\n' "$*" >> "$FAKE_CALLS"
out=
while [ "$#" -gt 0 ]; do
  if [ "$1" = -o ]; then out="$2"; fi
  shift
done
cp "$FAKE_REPORT" "$out"
"""


def skillspector_report(*reason_codes: str) -> dict:
    """A SkillSpector SARIF with one AE1 per reason code, as 2.13.1 shapes it."""
    results = [
        {
            "ruleId": "AE1",
            "level": "error",
            "message": {"text": "Referenced artifact was not completely inspected"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "SKILL.md"},
                        "region": {"startLine": 21},
                    }
                }
            ],
            "properties": {
                "severity": "HIGH",
                "finding": "references/notes.md (partial)",
                "evidence": {"reasons": [{"reason_code": code, "phase": "artifact"}]},
            },
        }
        for code in reason_codes
    ]
    return {
        "version": "2.1.0",
        "runs": [{"results": results, "invocations": [{"executionSuccessful": True}]}],
    }


def run_gate_step(tmp_path, first: dict[str, dict], rescan: dict, **fake_python: str):
    """Lay out the scan step's results, then run the real gate step over them."""
    work = tmp_path / "work"
    (work / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "skill_scan_gate.py", work / "scripts")
    accepted = work / ".github" / "skill-scan" / "skillspector-accepted.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text(json.dumps({"entries": []}), encoding="utf-8")
    runner = tmp_path / "runner"
    results = runner / "skillspector"
    results.mkdir(parents=True)
    (results / "skills.txt").write_text("".join(f"{s}\n" for s in first), encoding="utf-8")
    for skill, report in first.items():
        name = f"{skill.split('/')[1]}__{skill.split('/')[3]}"
        (results / f"{name}.sarif").write_text(json.dumps(report), encoding="utf-8")
        (results / f"{name}.rc").write_text("1\n", encoding="utf-8")
    scanner = runner / "skillspector-venv" / "bin" / "skillspector"
    scanner.parent.mkdir(parents=True)
    scanner.write_text(FAKE_SKILLSPECTOR, encoding="utf-8")
    scanner.chmod(0o755)
    fresh = tmp_path / "rescan.sarif"
    fresh.write_text(json.dumps(rescan), encoding="utf-8")
    calls = tmp_path / "calls.txt"
    calls.touch()
    result = subprocess.run(  # noqa: S603
        ["bash", "-c", step("Gate on new high and critical findings")],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=work,
        env={
            "PATH": f"{fake_python.get('bindir', Path(sys.executable).parent)}:/usr/bin:/bin",
            "FAKE_RESCAN": fake_python.get("listed", ""),
            "RUNNER_TEMP": str(runner),
            "FAKE_REPORT": str(fresh),
            "FAKE_CALLS": str(calls),
        },
        check=False,
    )
    return result, calls.read_text(encoding="utf-8").splitlines(), results


def test_a_scan_that_ran_out_of_time_is_rescanned_and_then_judged(tmp_path):
    first = {ALPHA: skillspector_report("runtime_limit"), BETA: skillspector_report()}
    result, calls, results = run_gate_step(tmp_path, first, skillspector_report())
    assert result.returncode == 0, result.stdout + result.stderr
    # Only the skill that ran out of time is scanned again, once, into its own files.
    assert calls == [f"scan {ALPHA} --no-llm --format sarif -o {results}/demo__alpha.sarif"]
    assert (results / "demo__alpha.rc").read_text(encoding="utf-8") == "0\n"
    assert json.loads((results / "demo__alpha.sarif").read_text())["runs"][0]["results"] == []
    assert f"::notice file={ALPHA}/SKILL.md,title=SkillSpector scan incomplete::" in result.stdout


def test_a_scan_that_runs_out_of_time_twice_fails(tmp_path):
    first = {ALPHA: skillspector_report("runtime_limit"), BETA: skillspector_report()}
    result, calls, _ = run_gate_step(tmp_path, first, skillspector_report("runtime_limit"))
    assert result.returncode == 1
    assert len(calls) == 1
    assert f"::error file={ALPHA}/SKILL.md,title=SkillSpector scan incomplete::" in result.stdout
    assert "ran out of time" in result.stdout


def test_a_new_finding_fails_the_gate_step_without_a_rescan(tmp_path):
    first = {ALPHA: skillspector_report("runtime_limit"), BETA: skillspector_report("x")}
    result, calls, _ = run_gate_step(tmp_path, first, skillspector_report())
    assert result.returncode == 1
    assert calls == []
    assert "HIGH AE1 finding not in" in result.stdout


# Stands in for the gate's first pass, listing a skill the selection step would never have
# chosen, to show the step checks each name itself rather than trusting the file.
FAKE_FIRST_GATE_RUN = """#!/bin/bash
set -Eeuo pipefail
while [ "$#" -gt 0 ]; do
  if [ "$1" = --incomplete-out ]; then printf '%s\\n' "$FAKE_RESCAN" > "$2"; exit 3; fi
  shift
done
exit 0
"""


@pytest.mark.parametrize(
    "listed", ["plugins/demo/skills/../../../etc", "-o", "plugins/demo/skills/gamma"]
)
def test_a_rescan_name_the_selection_step_would_refuse_fails(tmp_path, listed):
    fake = tmp_path / "fakebin"
    fake.mkdir()
    (fake / "python3").write_text(FAKE_FIRST_GATE_RUN, encoding="utf-8")
    (fake / "python3").chmod(0o755)
    first = {ALPHA: skillspector_report("runtime_limit")}
    result, calls, _ = run_gate_step(
        tmp_path, first, skillspector_report(), bindir=str(fake), listed=listed
    )
    assert result.returncode == 1
    assert calls == []
    assert "refusing to rescan a directory with an unexpected name" in result.stdout
