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

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "evals.yml"
STEP_NAME = "Check the backend has a credential"


def _extract_run_block(text: str, step_name: str, occurrence: int = 0) -> str:
    """The dedented body of one step's `run: |` block, found by indentation.

    Stops at the next `- name:` step or at the first sibling line no more indented than
    `run:` itself — `env:` in this case — so a step after the one asked for is never
    swept in.
    """
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}"]
    start = starts[occurrence]
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


@pytest.mark.parametrize("publisher", [0, 1], ids=["catalogue", "changed"])
@pytest.mark.parametrize("inconclusive", [1, 0, None], ids=["tie", "zero", "legacy"])
def test_both_publishers_show_inconclusive_without_losing_zero(tmp_path, publisher, inconclusive):
    result, summary = run_score_publisher(tmp_path, publisher, inconclusive=inconclusive)
    assert result.returncode == 0, result.stderr
    expected = "-" if inconclusive is None else str(inconclusive)
    assert "| Routing | Narrow | Inconclusive |" in summary
    assert "| --- | --- | --- | --- | --- | --- | --- |" in summary
    assert f"| `alpha` | 80% | 80% | 80% | 80% | 2 | {expected} |" in summary


def run_score_publisher(tmp_path, publisher, *, inconclusive=1, rate=0.8):
    row = {
        "target": "alpha",
        "rate": rate,
        "recall": 0.8,
        "specificity": 0.8,
        "routing": 0.8,
        "narrow": 2,
    }
    if inconclusive is not None:
        row["inconclusive"] = inconclusive
    (tmp_path / "evals.json").write_text(json.dumps([row]), encoding="utf-8")
    results = tmp_path / "eval-results"
    results.mkdir()
    (results / "alpha.json").write_text(json.dumps([row]), encoding="utf-8")
    summary = tmp_path / "summary"
    script = _extract_run_block(
        WORKFLOW.read_text(encoding="utf-8"), "Publish the scores", publisher
    )
    env = dict(os.environ, GITHUB_STEP_SUMMARY=str(summary))
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(  # noqa: S603
        ["bash", "-c", script],  # noqa: S607 - execute the workflow's own shell block
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result, summary.read_text(encoding="utf-8")


def test_changed_publisher_keeps_under_floor_error_and_exit_code(tmp_path):
    result, summary = run_score_publisher(tmp_path, 1, rate=0.6)
    assert result.returncode == 1
    assert "::error title=below the eval floor::alpha scored 60%" in result.stdout
    assert "Below the 70% floor: `alpha`. This fails the job." in summary
    assert "| `alpha` | 60% | 80% | 80% | 80% | 2 | 1 |" in summary


def test_reviewer_dependencies_match_ci_and_follow_scoring_gates():
    import re

    text = WORKFLOW.read_text(encoding="utf-8")
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for name in ("PYTEST_VERSION", "COVERAGE_VERSION"):
        pattern = rf"^  {name}: '([^']+)'$"
        assert re.search(pattern, text, re.MULTILINE).group(1) == re.search(
            pattern, ci, re.MULTILINE
        ).group(1)
    job = text.split("  reviewer-benchmark:", 1)[1]
    install = job.index("- name: Install the reviewer repository test dependencies")
    assert job.index("id: credentials") < install < job.index("- name: Benchmark the reviewer")
    step = job[install : job.index("- name: Benchmark the reviewer")]
    assert (
        "if: steps.gate.outputs.run == 'true' && steps.credentials.outputs.skip != 'true'" in step
    )
    script = _extract_run_block(text, "Install the reviewer repository test dependencies")
    assert (
        'python -m pip install "pytest==${PYTEST_VERSION}" "coverage==${COVERAGE_VERSION}"'
        in script
    )


@pytest.mark.parametrize("event", ["pull_request", "schedule", "workflow_dispatch"])
@pytest.mark.parametrize("credential", [False, True])
def test_reviewer_credential_gate_preserves_stand_down(tmp_path, event, credential):
    script = _extract_run_block(
        WORKFLOW.read_text(encoding="utf-8"), "Check the benchmark has a credential"
    )
    output = tmp_path / "output"
    env = {"PATH": "/usr/bin:/bin", "GITHUB_EVENT_NAME": event, "GITHUB_OUTPUT": str(output)}
    if credential:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = "fixture"  # noqa: S105 - fixture only
    result = subprocess.run(  # noqa: S603 - execute actual workflow gate offline
        ["bash", "-c", script],  # noqa: S607 - same PATH as workflow
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert output.read_text(encoding="utf-8") == f"skip={str(not credential).lower()}\n"
    assert result.returncode == (1 if event == "workflow_dispatch" and not credential else 0)


@pytest.mark.parametrize(
    ("event", "reviewer", "expected"),
    [
        ("schedule", "", "true"),
        ("workflow_dispatch", "true", "true"),
        ("workflow_dispatch", "false", "false"),
    ],
)
def test_reviewer_selection_gate_preserves_dispatch_opt_in(tmp_path, event, reviewer, expected):
    script = _extract_run_block(
        WORKFLOW.read_text(encoding="utf-8"), "Decide whether the benchmark measures this change"
    )
    output = tmp_path / "output"
    result = subprocess.run(  # noqa: S603 - execute workflow gate without scoring
        ["bash", "-c", script],  # noqa: S607 - same PATH as workflow
        env={
            "PATH": "/usr/bin:/bin",
            "GITHUB_EVENT_NAME": event,
            "REVIEWER_INPUT": reviewer,
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == f"run={expected}\n"


def run_target_selector(tmp_path, changed, targets):
    """Execute the actual embedded selector against a small catalogue, offline."""
    for path, queries in targets.items():
        definition = tmp_path / path
        definition.parent.mkdir(parents=True, exist_ok=True)
        definition.write_text("fixture", encoding="utf-8")
        if queries is not None:
            eval_path = (
                definition.parent / "evals" / "trigger-eval.json"
                if definition.name == "SKILL.md"
                else definition.parent / "evals" / f"{definition.stem}.json"
            )
            eval_path.parent.mkdir(parents=True, exist_ok=True)
            eval_path.write_text(json.dumps(queries), encoding="utf-8")
    (tmp_path / "changed-paths.txt").write_text("\n".join(changed), encoding="utf-8")
    script = (
        _extract_run_block(
            WORKFLOW.read_text(encoding="utf-8"), "Work out which targets the pull request touches"
        )
        .split("python - <<'EOF'\n", 1)[1]
        .rsplit("\nEOF", 1)[0]
    )
    summary, output = tmp_path / "summary", tmp_path / "output"
    result = subprocess.run(  # noqa: S603 - execute the workflow's real selector offline
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary), GITHUB_OUTPUT=str(output)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return (
        (tmp_path / "targets.txt").read_text(encoding="utf-8").splitlines(),
        output.read_text(encoding="utf-8"),
        summary.read_text(encoding="utf-8"),
    )


@pytest.mark.parametrize("parent", ["plugins/coding/agents", ".claude/agents"])
@pytest.mark.parametrize("source", ["definition", "eval", "both"])
def test_agent_only_changes_select_the_paired_target_once(tmp_path, parent, source):
    definition = f"{parent}/alpha.md"
    paired = f"{parent}/evals/alpha.json"
    changed = {"definition": [definition], "eval": [paired], "both": [definition, paired]}[source]
    selected, output, summary = run_target_selector(tmp_path, changed, {definition: []})
    assert selected == [f"agent {definition}"]
    assert output == "count=1\n"
    assert "Scoring 1 changed target(s) and 0 declared neighbour(s)." in summary


def test_mixed_changes_deduplicate_neighbours_and_expand_agent_evals(tmp_path):
    skill = "plugins/coding/skills/alpha/SKILL.md"
    agent = "plugins/coding/agents/beta.md"
    repo_agent = ".claude/agents/gamma.md"
    selected, output, summary = run_target_selector(
        tmp_path,
        [skill, "plugins/coding/skills/alpha/references/detail.md", agent],
        {
            skill: [{"expected": "beta"}, {"expected": "gamma"}],
            agent: [{"expected": "alpha"}, {"expected": "gamma"}, {"expected": "missing"}],
            repo_agent: [],
        },
    )
    assert selected == [
        "skill plugins/coding/skills/alpha",
        f"agent {agent}",
        f"agent {repo_agent}",
    ]
    assert output == "count=3\n"
    assert "Scoring 2 changed target(s) and 1 declared neighbour(s)." in summary


def test_deleted_and_unscorable_targets_do_not_reach_the_harness(tmp_path):
    orphan = tmp_path / ".claude/agents/evals/deleted.json"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("[]", encoding="utf-8")
    selected, output, summary = run_target_selector(
        tmp_path,
        [
            ".claude/agents/deleted.md",
            ".claude/agents/evals/deleted.json",
            ".claude/agents/unscorable.md",
            "plugins/coding/skills/gone/SKILL.md",
            ".claude/agents/benchmarks/reviewer/case/case.json",
            "README.md",
        ],
        {".claude/agents/unscorable.md": None},
    )
    assert selected == []
    assert output == "count=0\n"
    assert "Not scored, no eval set: `.claude/agents/unscorable.md`." in summary
    assert "deleted" not in summary


@pytest.mark.parametrize("changed_count", [11, 14])
def test_cap_counts_only_selected_changed_targets_and_neighbours(tmp_path, changed_count):
    definitions = [f".claude/agents/agent-{index:02}.md" for index in range(changed_count)]
    targets = dict.fromkeys(definitions, [{"expected": "neighbour-a"}, {"expected": "neighbour-b"}])
    targets.update({".claude/agents/neighbour-a.md": [], ".claude/agents/neighbour-b.md": []})
    selected, output, summary = run_target_selector(tmp_path, definitions, targets)
    assert len(selected) == 12
    assert output == "count=12\n"
    scored_changed = min(changed_count, 12)
    assert (
        f"Scoring {scored_changed} changed target(s) and "
        f"{12 - scored_changed} declared neighbour(s)." in summary
    )
    assert f"Truncated at 12 targets; {changed_count + 2 - 12} more were dropped." in summary
    assert selected[:scored_changed] == [f"agent {path}" for path in definitions[:12]]
