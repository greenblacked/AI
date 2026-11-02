"""Two shell steps in `security.yml`'s skill-scan jobs, run for real.

`Choose the skills to scan` decides what SkillSpector reads on a pull request, so a
selection bug is a skill that silently goes unscanned. `Scan every skill` prints a
summary of Cisco's findings into the job log, where a path or rule id the report carries
verbatim could otherwise open a workflow command. Both are bash embedded in the workflow,
so each is pulled out of the real file and executed, the way `test_evals_workflow.py`
does, rather than copied into a second version that would drift from the one CI runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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
