"""The aggregate gate accepts only the exact set of successful prerequisite jobs."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, load_script

job_results = load_script("check_job_results.py")
SCRIPT = REPO / "scripts" / "check_job_results.py"


def run_gate(expected, needs, *, summary=None, skippable=None):
    env = os.environ.copy()
    env.pop("SKIPPABLE", None)
    if skippable is not None:
        env["SKIPPABLE"] = skippable
    if needs is None:
        env.pop("NEEDS_JSON", None)
    else:
        env["NEEDS_JSON"] = needs if isinstance(needs, str) else json.dumps(needs)
    if summary is not None:
        env["GITHUB_STEP_SUMMARY"] = str(summary)
    else:
        env.pop("GITHUB_STEP_SUMMARY", None)
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *expected],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )


def test_exact_success_set_passes_and_writes_summary(tmp_path):
    summary = tmp_path / "summary.md"
    result = run_gate(
        ["build", "lint"],
        {"build": {"result": "success"}, "lint": {"result": "success"}},
        summary=summary,
    )
    assert result.returncode == 0
    assert result.stdout == "all 2 required job(s) succeeded\n"
    assert summary.read_text(encoding="utf-8") == (
        "| Job | Result |\n| --- | --- |\n| `build` | success |\n| `lint` | success |\n"
    )


@pytest.mark.parametrize(
    ("expected", "needs"),
    [
        ([], {}),
        (["build", "build"], {"build": {"result": "success"}}),
        (["build"], None),
        (["build"], "not json"),
        (["build"], '{"build":{"result":"success"},"build":{"result":"success"}}'),
        (["build"], []),
        (["build", "lint"], {"build": {"result": "success"}}),
        (["build"], {"build": {"result": "success"}, "extra": {"result": "success"}}),
        (["build"], {"build": "success"}),
        (["build"], {"build": {}}),
        (["build"], {"build": {"result": "unknown"}}),
        (["build"], {"build": {"result": "skipped"}}),
        (["build"], {"build": {"result": "cancelled"}}),
        (["build"], {"build": {"result": "failure"}}),
    ],
)
def test_invalid_or_unsuccessful_inputs_fail(expected, needs):
    result = run_gate(expected, needs)
    assert result.returncode == 1
    assert "did not satisfy" in result.stderr


def test_untrusted_json_values_are_not_echoed_or_written(tmp_path):
    attack = "secret|value\n::error::injected"
    summary = tmp_path / "summary.md"
    result = run_gate(["build"], {"build": {"result": attack}}, summary=summary)
    assert result.returncode == 1
    assert attack not in result.stdout + result.stderr
    assert attack not in summary.read_text(encoding="utf-8")
    assert "| `build` | invalid |" in summary.read_text(encoding="utf-8")


def test_malformed_json_marks_each_expected_job_invalid_in_the_summary(tmp_path):
    summary = tmp_path / "summary.md"
    result = run_gate(["build", "lint"], "not json", summary=summary)
    assert result.returncode == 1
    written = summary.read_text(encoding="utf-8")
    assert "| `build` | invalid |" in written
    assert "| `lint` | invalid |" in written


def test_an_unwritable_summary_fails_the_gate(tmp_path):
    result = run_gate(
        ["build"],
        {"build": {"result": "success"}},
        summary=tmp_path / "missing" / "summary.md",
    )
    assert result.returncode == 1


def test_main_uses_the_supplied_arguments(monkeypatch, capsys):
    monkeypatch.setenv("NEEDS_JSON", '{"build":{"result":"success"}}')
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert job_results.main(["build"]) == 0
    assert "all 1 required job(s) succeeded" in capsys.readouterr().out


def test_a_skipped_job_passes_only_when_the_scope_listed_it():
    needs = {
        "scope": {"result": "success"},
        "test": {"result": "skipped"},
        "lint": {"result": "success"},
    }
    assert run_gate(["scope", "test", "lint"], needs, skippable="test").returncode == 0
    # Not listed: a skipped job is still a failure, the way it was before scopes existed.
    assert run_gate(["scope", "test", "lint"], needs, skippable="lint").returncode == 1
    assert run_gate(["scope", "test", "lint"], needs).returncode == 1


@pytest.mark.parametrize("result", ["failure", "cancelled"])
def test_a_listed_job_that_failed_or_was_cancelled_still_fails(result):
    needs = {"test": {"result": result}}
    assert run_gate(["test"], needs, skippable="test").returncode == 1


@pytest.mark.parametrize("skippable", ["unknown-job", "test ../x", "test;rm"])
def test_a_skip_list_naming_anything_the_aggregate_does_not_expect_fails(skippable):
    needs = {"test": {"result": "skipped"}}
    result = run_gate(["test"], needs, skippable=skippable)
    assert result.returncode == 1 and "did not satisfy" in result.stderr
