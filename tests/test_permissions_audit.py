"""The top-level permissions audit in `security.yml` is bash embedded in a workflow, not
Python, so it is exercised here by pulling the step's own `run:` block out of the real
file and executing it against a scratch tree, rather than duplicating its logic in a
second copy that would drift from the one CI runs. This mirrors
`tests/test_evals_workflow.py`'s approach to the same problem.

The step used to accept `permissions: write-all` and `permissions: read-all` — and a
block form granting `write` on any scope — because it only checked that a
`^permissions:` line existed, never what it said.

A second pass over the same script found four more shapes it let through: a trailing
comment on the `permissions:` line captured as if it were the value, an unquoted-only
`write` pattern that missed `"write"` and `'write'`, a single-line flow map
(`{contents: write}`) treated the same as an inert `{}`, and a column-zero comment
between `permissions:` and its block ending the scan before the grant was ever read.
"""

from __future__ import annotations

import subprocess

from tests.conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "security.yml"
STEP_NAME = "Every workflow must set a top-level permissions block that grants nothing"


def _extract_run_block(text: str, step_name: str) -> str:
    """The dedented body of one step's `run: |` block, found by indentation.

    Stops at the next `- name:` step or at the first sibling line no more indented than
    `run:` itself, so a step after the one asked for is never swept in.
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


def run_audit(tmp_path, workflow_text: str):
    script = _extract_run_block(WORKFLOW.read_text(encoding="utf-8"), STEP_NAME)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "demo.yml").write_text(workflow_text, encoding="utf-8")
    return subprocess.run(  # noqa: S603
        ["bash", "-c", script],  # noqa: S607 - relying on PATH, as the workflow's own runner does
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )


def test_an_empty_permissions_map_passes(tmp_path):
    result = run_audit(tmp_path, "name: Demo\npermissions: {}\njobs: {}\n")
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_missing_permissions_block_fails(tmp_path):
    result = run_audit(tmp_path, "name: Demo\njobs: {}\n")
    assert result.returncode != 0
    assert "no permissions block" in result.stdout


def test_write_all_fails(tmp_path):
    result = run_audit(tmp_path, "name: Demo\npermissions: write-all\njobs: {}\n")
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_read_all_fails(tmp_path):
    result = run_audit(tmp_path, "name: Demo\npermissions: read-all\njobs: {}\n")
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_block_form_granting_write_fails(tmp_path):
    text = "name: Demo\npermissions:\n  contents: write\n  actions: read\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_block_form_with_only_reads_passes(tmp_path):
    text = "name: Demo\npermissions:\n  contents: read\n  actions: read\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_trailing_comment_on_the_permissions_line_does_not_hide_a_block_grant(tmp_path):
    # "permissions:  # least privilege" used to be read as a non-empty, single-line
    # value and skipped outright, so the `contents: write` on the next line was never
    # reached.
    text = "name: Demo\npermissions:  # least privilege\n  contents: write\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_double_quoted_write_in_a_block_fails(tmp_path):
    text = 'name: Demo\npermissions:\n  contents: "write"\njobs: {}\n'
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_single_quoted_write_in_a_block_fails(tmp_path):
    text = "name: Demo\npermissions:\n  contents: 'write'\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_single_line_flow_map_granting_write_fails(tmp_path):
    # Any non-empty single-line value used to be waved through as if it were "{}".
    text = "name: Demo\npermissions: {contents: write}\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout


def test_a_single_line_flow_map_with_only_reads_passes(tmp_path):
    text = "name: Demo\npermissions: {contents: read, actions: read}\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_column_zero_comment_before_the_block_does_not_end_the_scan(tmp_path):
    # `/^[^[:space:]]/ { exit }` used to treat a comment starting in column zero as the
    # sibling key that ends the permissions block, so nothing after it was ever read.
    text = "name: Demo\npermissions:\n# note\n  contents: write\njobs: {}\n"
    result = run_audit(tmp_path, text)
    assert result.returncode != 0
    assert "over-broad permissions" in result.stdout
