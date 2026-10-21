"""The ci-triage bisect probe: its exit code is the whole contract with git bisect."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "plugins/operations/skills/ci-triage/scripts/bisect-probe.sh"
BASH = shutil.which("bash") or "/bin/bash"


def run(cwd: Path, **env: str) -> int:
    full = {**os.environ, "BISECT_BUILD_CMD": "true", **env}
    # A fixed argv: the shipped probe and an absolute bash, nothing taken from input.
    result = subprocess.run([BASH, str(PROBE)], cwd=cwd, env=full, capture_output=True)  # noqa: S603
    return result.returncode


def install_runner(cwd: Path, exit_code: int) -> None:
    runner = cwd / "node_modules" / ".bin" / "jest"
    runner.parent.mkdir(parents=True)
    runner.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    runner.chmod(runner.stat().st_mode | stat.S_IXUSR)


def test_a_commit_without_the_runner_is_skipped_not_fetched(tmp_path: Path) -> None:
    # The default runner is the commit's own binary; with none installed the commit is
    # untestable (125), never handed to a runner fetched from the registry.
    assert run(tmp_path) == 125


# 126 and 127 from a runner that did launch are failures like any other, not a skip.
@pytest.mark.parametrize(("runner_exit", "verdict"), [(0, 0), (1, 1), (126, 1), (127, 1)])
def test_the_installed_runner_decides(tmp_path: Path, runner_exit: int, verdict: int) -> None:
    install_runner(tmp_path, runner_exit)
    assert run(tmp_path) == verdict


def test_a_build_failure_is_skipped(tmp_path: Path) -> None:
    install_runner(tmp_path, 0)
    assert run(tmp_path, BISECT_BUILD_CMD="false") == 125


@pytest.mark.parametrize(
    "command",
    [
        "env FOO=bar node_modules/.bin/jest path/to/suspect.test.ts",
        "NODE_OPTIONS=--max-old-space-size=4096 node_modules/.bin/jest path/to/suspect.test.ts",
    ],
)
def test_a_wrapped_runner_that_is_missing_is_skipped(tmp_path: Path, command: str) -> None:
    # Whatever wraps the runner, the named binary is checked before the command runs.
    runner = "node_modules/.bin/jest"
    assert run(tmp_path, BISECT_TEST_CMD=command, BISECT_RUNNER=runner) == 125


def test_a_custom_command_that_exits_127_is_bad(tmp_path: Path) -> None:
    # With no runner to check, a returned 127 is the test's verdict, not a launch error.
    assert run(tmp_path, BISECT_TEST_CMD="sh -c 'exit 127'") == 1


def test_a_custom_command_decides(tmp_path: Path) -> None:
    assert run(tmp_path, BISECT_TEST_CMD="true") == 0
    assert run(tmp_path, BISECT_TEST_CMD="false") == 1
