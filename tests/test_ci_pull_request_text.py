"""How `ci.yml` reads a pull request's title and body, and when an edit cancels a run.

Two failures with no symptom of their own. An `edited` event that cancels the run in
flight turns `ci` red on the head commit, because the aggregate counts a cancelled
dependency as a failure. And a job that reads the title or body from the event payload
checks text frozen when the run was triggered, so a description fixed seconds after
opening still fails the run for `opened`. The jobs now read the live values through the
API; the text is pull-request-controlled, so it must reach the check without passing
through a `${{ }}` expression or through anything that evaluates it.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys

import pytest

from tests.conftest import REPO
from tests.test_evals_workflow import _extract_run_block

CI = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

ATTRIBUTION_STEP = "Check commits, branch name and pull request text for tool attribution"
NAMING_STEP = "Check tracked file names, and on a pull request the branch, commits and title"

# job id, the step that reads the pull request, and the script that step hands the text to
JOBS = [
    ("attribution", ATTRIBUTION_STEP, "check_attribution.py"),
    ("naming", NAMING_STEP, "check_naming.py"),
]


def job_text(job: str) -> str:
    """One job's lines, from its key to the next sibling job key."""
    match = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", CI, re.M | re.S)
    assert match, f"no job {job!r} in ci.yml"
    return match.group(0)


def permissions_of(job: str) -> dict[str, str]:
    block = re.search(r"^    permissions:\n((?:      .*\n|\n)+)", job_text(job), re.M)
    assert block, f"job {job!r} has no permissions block"
    grants = {}
    for line in block.group(1).splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            key, _, value = line.partition(":")
            grants[key.strip()] = value.strip()
    return grants


def test_an_edit_does_not_cancel_the_run_in_flight():
    match = re.search(r"^  cancel-in-progress: >-\n\s+(\$\{\{.*?\}\})\n", CI, re.M | re.S)
    assert match, "cancel-in-progress is not a folded expression"
    expression = match.group(1)
    assert "github.event_name == 'pull_request'" in expression
    assert "github.event.action != 'edited'" in expression


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_the_job_grants_contents_and_pull_request_read_only(job, step, script):
    assert permissions_of(job) == {"contents": "read", "pull-requests": "read"}


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_the_job_does_not_read_the_text_from_the_event_payload(job, step, script):
    text = job_text(job)
    env_block = text.split("        env:\n", 1)[1].split("        run:", 1)[0]
    assert "github.event.pull_request.body" not in env_block
    assert "github.event.pull_request.title" not in env_block
    assert not re.search(r"^\s+PR_(TITLE|BODY):", env_block, re.M)
    assert "PR_NUMBER: ${{ github.event.pull_request.number }}" in env_block
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in env_block
    assert "GH_REPO: ${{ github.repository }}" in env_block


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_the_job_reads_this_pull_request_through_the_api(job, step, script):
    run = _extract_run_block(job_text(job), step)
    assert 'gh api "repos/$GH_REPO/pulls/$PR_NUMBER"' in run
    assert "eval" not in re.findall(r"\w+", run)


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_no_expression_reaches_a_run_block(job, step, script):
    assert "${{" not in _extract_run_block(job_text(job), step)


# --- running the step ----------------------------------------------------------------

BODY = 'first line\nsays "hi" and `date` and $(touch pwned)\n$HOME \\n ${PATH} end'
STUB_GH = """#!/bin/sh
if [ "$1" != api ] || [ "$2" != "repos/octo/demo/pulls/7" ]; then
  echo "unexpected gh arguments: $*" >&2
  exit 64
fi
if [ -n "${STUB_GH_FAIL:-}" ]; then
  echo "HTTP 502" >&2
  exit 1
fi
cat "$STUB_GH_JSON"
"""
STUB_CHECK = """import os
from pathlib import Path

Path("seen-title").write_bytes(os.environ["PR_TITLE"].encode())
if "PR_BODY" in os.environ:
    Path("seen-body").write_bytes(os.environ["PR_BODY"].encode())
"""


def run_step(tmp_path, job, step, script, payload, *, gh_fails=False, event="pull_request"):
    bin_dir = tmp_path / "bin"
    work = tmp_path / "work"
    runner_temp = tmp_path / "runner-temp"
    for directory in (bin_dir, work / "scripts", runner_temp):
        directory.mkdir(parents=True, exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(STUB_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    for name in ("python", "python3"):
        (bin_dir / name).symlink_to(sys.executable)
    (work / "scripts" / script).write_text(STUB_CHECK, encoding="utf-8")
    json_file = tmp_path / "pull.json"
    json_file.write_text(payload, encoding="utf-8")

    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "EVENT_NAME": event,
        "PR_NUMBER": "7",
        "GH_REPO": "octo/demo",
        "GH_TOKEN": "a-token",  # a fixture value, not a secret
        "GITHUB_BASE_REF": "main",
        "RUNNER_TEMP": str(runner_temp),
        "STUB_GH_JSON": str(json_file),
    }
    if gh_fails:
        env["STUB_GH_FAIL"] = "1"
    return subprocess.run(  # noqa: S603
        ["bash", "-c", _extract_run_block(job_text(job), step)],  # noqa: S607
        capture_output=True,
        text=True,
        env=env,
        cwd=work,
        check=False,
    )


def json_payload(title, body):
    import json

    return json.dumps({"title": title, "body": body})


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_hostile_text_arrives_verbatim_and_executes_nothing(tmp_path, job, step, script):
    title = 'Add "x" `id` $(touch pwned)'
    result = run_step(tmp_path, job, step, script, json_payload(title, BODY))
    assert result.returncode == 0, result.stderr
    work = tmp_path / "work"
    assert not (work / "pwned").exists()
    assert not list(tmp_path.rglob("pwned"))
    assert (work / "seen-title").read_text(encoding="utf-8") == title
    if job == "attribution":
        assert (work / "seen-body").read_text(encoding="utf-8") == BODY


def test_a_null_body_is_an_empty_string(tmp_path):
    result = run_step(
        tmp_path, "attribution", ATTRIBUTION_STEP, "check_attribution.py", json_payload("T", None)
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "work" / "seen-body").read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(("job", "step", "script"), JOBS)
def test_a_failed_read_fails_the_job_and_never_runs_the_check(tmp_path, job, step, script):
    result = run_step(tmp_path, job, step, script, json_payload("T", "B"), gh_fails=True)
    assert result.returncode != 0
    assert not (tmp_path / "work" / "seen-title").exists()


def test_a_non_pull_request_event_never_calls_the_api(tmp_path):
    result = run_step(
        tmp_path,
        "attribution",
        ATTRIBUTION_STEP,
        "check_attribution.py",
        json_payload("T", "B"),
        gh_fails=True,
        event="push",
    )
    assert result.returncode == 0
    assert not (tmp_path / "work" / "seen-title").exists()
    assert os.path.exists(tmp_path / "bin" / "gh")
