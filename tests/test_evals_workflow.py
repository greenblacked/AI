"""The credential-check step in `evals.yml` decides whether trigger-eval scoring on a
pull request silently never runs — a same-repository pull request with no credential
configured used to print the fork's notice, which is false for it, and stand down with
no signal that the 0.7 floor was never enforced.

The step is bash embedded in a workflow, not Python, so it is exercised here by pulling
the step's own `run:` block out of the real file and executing it with `bash`, rather
than duplicating its logic in a second copy that would drift from the one CI runs.
PyYAML is not a dependency of this suite, so the block is found by indentation rather
than by parsing the file as YAML.
"""

from __future__ import annotations

import subprocess

from tests.conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "evals.yml"
STEP_NAME = "Check the backend has a credential"


def _extract_run_block(text: str, step_name: str) -> str:
    """The dedented body of one step's `run: |` block, found by indentation.

    Stops at the next `- name:` step or at the first sibling line no more indented than
    `run:` itself — `env:` in this case — so a step after the one asked for is never
    swept in.
    """
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}")
    run_index = next(
        i
        for i in range(start + 1, len(lines))
        if lines[i].strip() == "run: |" or (lines[i].strip().startswith("- name:") and i != start)
    )
    assert lines[run_index].strip() == "run: |", "step has no run: | block"
    run_indent = len(lines[run_index]) - len(lines[run_index].lstrip(" "))

    block: list[str] = []
    for line in lines[run_index + 1 :]:
        if not line.strip():
            block.append("")
            continue
        if len(line) - len(line.lstrip(" ")) <= run_indent:
            break
        block.append(line)

    base = min((len(line) - len(line.lstrip(" ")) for line in block if line.strip()), default=0)
    return "\n".join(line[base:] if line.strip() else "" for line in block)


def run_credential_check(tmp_path, *, same_repo: str, has_credential: bool):
    text = WORKFLOW.read_text(encoding="utf-8")
    script = _extract_run_block(text, STEP_NAME)

    output = tmp_path / "output"
    summary = tmp_path / "summary"
    output.write_text("", encoding="utf-8")
    summary.write_text("", encoding="utf-8")

    env = {
        "PATH": "/usr/bin:/bin",
        "SAME_REPO": same_repo,
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    if has_credential:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = "a-token"  # noqa: S105 - a fixture value, not a secret

    result = subprocess.run(  # noqa: S603
        ["bash", "-c", script],  # noqa: S607 - relying on PATH, as the workflow's own runner does
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result, output.read_text(encoding="utf-8"), summary.read_text(encoding="utf-8")


def test_a_same_repo_pull_request_with_no_credential_warns_rather_than_claims_a_fork(tmp_path):
    result, output, summary = run_credential_check(tmp_path, same_repo="true", has_credential=False)
    assert result.returncode == 0
    assert "skip=true" in output
    assert "::warning title=no credential configured::" in result.stdout
    assert "expected on a pull request from a fork" not in result.stdout
    assert "Scoring is inactive" in summary


def test_a_fork_pull_request_with_no_credential_still_gets_the_fork_notice(tmp_path):
    """The fork case is unaffected: this is the one where a contributor genuinely has no
    way to set the secret, so it must keep reading as expected rather than as a warning."""
    result, output, summary = run_credential_check(
        tmp_path, same_repo="false", has_credential=False
    )
    assert result.returncode == 0
    assert "skip=true" in output
    assert "::notice title=no credentials::" in result.stdout
    assert "expected on a pull request from a fork" in result.stdout
    assert "::warning" not in result.stdout


def test_a_credential_present_emits_neither_notice_nor_warning(tmp_path):
    result, output, _ = run_credential_check(tmp_path, same_repo="true", has_credential=True)
    assert result.returncode == 0
    assert "skip=false" in output
    assert "::warning" not in result.stdout
    assert "::notice" not in result.stdout
