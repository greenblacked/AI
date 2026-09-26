"""The reviewer benchmark measures output quality, not routing, and had no tests.

Two things are checked here. First, a drift guard that needs no model at all: every
committed case's `case.json` matches its schema, every patch still applies to the
current tree, and every defect's `lesson` names a real heading in
`docs/review-lessons.md` — a case that rots fails `make test` rather than failing
silently the day someone runs the benchmark for real. Second, the runner end to end
against a fake `claude` on PATH, the same way `tests/test_harness.py` exercises
`run_trigger_eval.py` without reaching a model.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.conftest import load_script

benchmark = load_script("run_review_benchmark.py")
GIT = benchmark._git()

REPO = Path(__file__).resolve().parent.parent
CASES_DIR = REPO / ".claude" / "agents" / "benchmarks" / "reviewer"
LESSON_HEADING_RE = re.compile(r"^### (.+)$", re.M)


def real_cases() -> list[Path]:
    return sorted(p.parent for p in CASES_DIR.glob("*/case.json"))


def real_lessons() -> set[str]:
    text = (REPO / "docs" / "review-lessons.md").read_text(encoding="utf-8")
    return set(LESSON_HEADING_RE.findall(text))


# --- drift guard: the committed cases against the repository they are drawn from ----


def test_at_least_one_case_of_each_kind_exists():
    cases = [json.loads((c / "case.json").read_text(encoding="utf-8")) for c in real_cases()]
    kinds = [c["kind"] for c in cases]
    assert kinds.count("defect") >= 1
    assert kinds.count("clean") >= 1


@pytest.mark.parametrize("case_dir", real_cases(), ids=lambda p: p.name)
def test_case_json_matches_the_schema(case_dir):
    data = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert data["kind"] in ("defect", "clean")
    assert isinstance(data.get("intent"), str) and data["intent"].strip()
    if data["kind"] == "defect":
        assert isinstance(data.get("lesson"), str) and data["lesson"].strip()
        must_mention = data.get("must_mention")
        assert isinstance(must_mention, list) and must_mention
        for pattern in must_mention:
            re.compile(pattern)  # raises re.error on anything unusable as a regex
    else:
        assert "must_mention" not in data


@pytest.mark.parametrize("case_dir", real_cases(), ids=lambda p: p.name)
def test_case_patch_applies_to_the_current_tree(case_dir):
    result = subprocess.run(  # noqa: S603
        [GIT, "apply", "--check", str(case_dir / "change.patch")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "case_dir",
    [c for c in real_cases() if json.loads((c / "case.json").read_text())["kind"] == "defect"],
    ids=lambda p: p.name,
)
def test_defect_lesson_names_a_real_heading(case_dir):
    data = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert data["lesson"] in real_lessons()


@pytest.mark.parametrize("case_dir", real_cases(), ids=lambda p: p.name)
def test_case_directory_holds_exactly_the_patch_and_the_case_file(case_dir):
    # A stray third file in a case directory is either dead weight or something the
    # runner silently ignores; either way it is not part of the committed contract.
    names = sorted(p.name for p in case_dir.iterdir())
    assert names == ["case.json", "change.patch"]


# Every defect here is a deliberately weakened copy of something real. None of that is
# allowed to touch the machinery that would actually validate a change, or the reviewer
# and hook that judge one - a patch that did would stop being a fixture and start being
# a genuine attempt to weaken this repository's own gates.
PROTECTED_PATCH_PREFIXES = (
    ".claude/settings.json",
    ".claude/agents/reviewer.md",
    "scripts/hooks/",
)


@pytest.mark.parametrize("case_dir", real_cases(), ids=lambda p: p.name)
def test_case_patch_never_touches_the_reviewer_or_its_hook(case_dir):
    text = (case_dir / "change.patch").read_text(encoding="utf-8")
    touched = set(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.M))
    for path in touched:
        for forbidden in PROTECTED_PATCH_PREFIXES:
            assert not path.startswith(forbidden), (case_dir.name, path)


# --- the runner against a fake CLI ---------------------------------------------------


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run = lambda *args: subprocess.run(  # noqa: S603, E731
        [GIT, *args], cwd=root, check=True, capture_output=True, text=True
    )
    run("init", "-q")
    run("config", "user.email", "bench@example.com")
    run("config", "user.name", "Bench")
    (root / "file.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    run("add", ".")
    run("commit", "-q", "-m", "init")
    return root


def make_patch(root: Path, new_text: str) -> str:
    """Edit file.txt, capture the diff, then put the tree back."""
    (root / "file.txt").write_text(new_text, encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [GIT, "diff"], cwd=root, check=True, capture_output=True, text=True
    )
    subprocess.run([GIT, "checkout", "--", "."], cwd=root, check=True, capture_output=True)  # noqa: S603
    return result.stdout


def write_case(
    root: Path,
    name: str,
    *,
    kind: str,
    intent: str,
    patch_text: str,
    must_mention: list[str] | None = None,
    lesson: str = "A count in prose goes stale",
) -> Path:
    case_dir = root / ".claude" / "agents" / "benchmarks" / "reviewer" / name
    case_dir.mkdir(parents=True)
    (case_dir / "change.patch").write_text(patch_text, encoding="utf-8")
    payload = {"kind": kind, "intent": intent}
    if kind == "defect":
        payload["lesson"] = lesson
        payload["must_mention"] = must_mention or []
    (case_dir / "case.json").write_text(json.dumps(payload), encoding="utf-8")
    return case_dir


def fake_query(intent: str) -> str:
    """The text the fake CLI extracts as its lookup key, from the runner's own prompt.

    The commit named earlier in the prompt does not affect this: the extraction is
    everything between "User message:\\n" and "\\n\\nReply", which is the intent alone.
    """
    prompt = benchmark.build_prompt(intent, "0" * 40)
    return prompt.split("User message:\n", 1)[1].split("\n\nReply", 1)[0].strip()


def cli_answer(result_text: str, cost: float = 0.01, model: str = "fable", **extra) -> str:
    """A JSON `--output-format json` payload, as the fake CLI would print it verbatim.

    `**extra` merges in anything a specific test needs beyond the three defaults every
    other test relies on — `modelUsage`, `num_turns`, `subtype`, `stop_reason`.
    """
    payload = {"result": result_text, "total_cost_usd": cost, "model": model}
    payload.update(extra)
    return json.dumps(payload)


class Args:
    def __init__(self, **overrides):
        self.root = None
        self.case = None
        self.runs = 1
        self.jobs = 1
        self.max_turns = 40
        self.max_budget_usd = 2.00
        self.model = None
        self.command = None
        self.threshold_catch = 0.85
        self.threshold_false_alarm = 0.34
        self.timeout = 30
        self.json = None
        self.__dict__.update(overrides)


def run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["run_review_benchmark.py", *argv])
    return benchmark.main()


def test_a_ship_verdict_passes_a_clean_case(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "clean-one", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude(
        {
            fake_query("Add a trailing line."): cli_answer(
                "Verdict: SHIP\n\nNothing further is owed."
            )
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "clean-one",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is True
    assert result["verdict"] == "SHIP"
    assert result["cost_usd"] == pytest.approx(0.01)


def test_a_ship_verdict_on_a_defect_case_is_a_miss(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "defect-missed",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt"],
    )
    fake_claude({fake_query("Drop a redundant flag."): cli_answer("Verdict: SHIP\n\nLooks fine.")})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "defect-missed",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert "wanted FIX or STOP" in result["reason"]


def test_a_fix_verdict_with_every_must_mention_present_passes(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "defect-caught",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt", "redundant"],
    )
    report = "Verdict: FIX\n\n### Findings\nfile.txt lost a redundant safeguard."
    fake_claude({fake_query("Drop a redundant flag."): cli_answer(report)})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "defect-caught",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is True
    assert result["verdict"] == "FIX"


def test_a_fix_verdict_missing_a_must_mention_fails(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "defect-partial",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt", "nonexistent-term"],
    )
    report = "Verdict: FIX\n\n### Findings\nfile.txt lost a safeguard."
    fake_claude({fake_query("Drop a redundant flag."): cli_answer(report)})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "defect-partial",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert "nonexistent-term" in result["reason"]


def test_a_report_with_no_verdict_line_fails_the_case(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "no-verdict", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude({fake_query("Add a trailing line."): cli_answer("I looked at it and it seems ok.")})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "no-verdict",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert result["reason"] == "no verdict"


def test_a_tool_failure_is_raised_rather_than_scored(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "cli-down", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude({}, mode="fail")
    with pytest.raises(benchmark.ToolFailureError):
        benchmark.run_case(
            root / ".claude" / "agents" / "benchmarks" / "reviewer" / "cli-down",
            root,
            benchmark.build_command(None, None, 40, 2.00),
            Args(),
        )


def test_a_patch_that_does_not_apply_is_a_hard_error_naming_the_case(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    write_case(
        root,
        "bad-patch",
        kind="clean",
        intent="whatever",
        patch_text=(
            "diff --git a/nope.txt b/nope.txt\n"
            "--- a/nope.txt\n+++ b/nope.txt\n@@ -1 +1 @@\n-old\n+new\n"
        ),
    )
    with pytest.raises(benchmark.PatchFailureError) as caught:
        benchmark.run_case(
            root / ".claude" / "agents" / "benchmarks" / "reviewer" / "bad-patch",
            root,
            benchmark.build_command(None, None, 40, 2.00),
            Args(),
        )
    assert "bad-patch" in str(caught.value)


def test_main_runs_a_single_case_and_exits_zero_on_ship(tmp_path, fake_claude, monkeypatch, capsys):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "only-one", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude({fake_query("Add a trailing line."): cli_answer("Verdict: SHIP\n\nOK.")})
    code = run_main(monkeypatch, "--root", str(root), "--case", "only-one")
    out = capsys.readouterr().out
    assert code == 0
    assert "false-alarm rate: 0%" in out


def test_main_writes_json_and_reports_a_hard_error_for_a_bad_patch(
    tmp_path, fake_claude, monkeypatch, capsys
):
    root = make_repo(tmp_path)
    write_case(
        root,
        "bad-patch",
        kind="clean",
        intent="whatever",
        patch_text=(
            "diff --git a/nope.txt b/nope.txt\n"
            "--- a/nope.txt\n+++ b/nope.txt\n@@ -1 +1 @@\n-old\n+new\n"
        ),
    )
    out = tmp_path / "results.json"
    code = run_main(monkeypatch, "--root", str(root), "--case", "bad-patch", "--json", str(out))
    assert code == 2
    written = json.loads(out.read_text())
    assert written[0]["error"] is True
    assert "bad-patch" in written[0]["reason"]


def test_main_returns_two_when_no_cases_exist(tmp_path, monkeypatch, capsys):
    root = tmp_path / "empty"
    root.mkdir()
    code = run_main(monkeypatch, "--root", str(root))
    assert code == 2
    assert "no benchmark cases found" in capsys.readouterr().err


def test_main_returns_one_when_below_the_catch_threshold(
    tmp_path, fake_claude, monkeypatch, capsys
):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "missed-defect",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt"],
    )
    fake_claude({fake_query("Drop a redundant flag."): cli_answer("Verdict: SHIP\n\nLooks fine.")})
    code = run_main(monkeypatch, "--root", str(root), "--case", "missed-defect")
    assert code == 1
    assert "catch rate: 0%" in capsys.readouterr().out


def test_a_custom_command_must_contain_a_prompt_placeholder():
    with pytest.raises(ValueError):
        benchmark.build_command("mycli --quiet", None, 40, 2.00)


def test_build_command_passes_model_and_budget_through():
    argv = benchmark.build_command(None, "haiku", 12, 1.5)
    assert "--model" in argv and "haiku" in argv
    assert "12" in argv and "1.5" in argv
    assert "{prompt}" in argv
    assert argv.index("{prompt}") < argv.index("--allowedTools")


def test_build_prompt_states_the_commit_and_asks_for_separate_commands():
    prompt = benchmark.build_prompt("Do the thing.", "abc1234")
    assert "commit abc1234" in prompt
    assert "git diff HEAD" in prompt
    assert "without shell variables or command substitution" in prompt


def test_head_sha_reads_the_worktrees_own_commit(tmp_path):
    root = make_repo(tmp_path)
    worktree = benchmark.make_worktree(root)
    try:
        expected = subprocess.run(  # noqa: S603
            [GIT, "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        assert benchmark.head_sha(worktree) == expected
    finally:
        benchmark.remove_worktree(root, worktree)


def test_parse_json_result_tolerates_a_preamble_line():
    data = benchmark.parse_json_result('thinking...\n{"result": "Verdict: SHIP"}')
    assert data["result"] == "Verdict: SHIP"


def test_parse_json_result_raises_when_nothing_parses():
    with pytest.raises(benchmark.ToolFailureError):
        benchmark.parse_json_result("not json at all")


def test_command_line_elides_the_prompt_but_shows_everything_else():
    argv = benchmark.build_command(None, None, 40, 2.00)
    line = benchmark.command_line(argv)
    assert "<prompt elided>" in line
    assert "--allowedTools" in line
    assert "--disallowedTools" in line


def test_ask_prints_the_command_line_before_running(fake_claude, tmp_path, capsys):
    prompt = "preamble\n\nUser message:\nhello\n\nReply now"
    fake_claude({"hello": '{"result": "Verdict: SHIP"}'})
    benchmark.ask(["claude", "-p", "{prompt}"], prompt, tmp_path, 5)
    err = capsys.readouterr().err
    assert "<prompt elided>" in err
    assert "hello" not in err


def test_parse_json_result_reads_a_whole_pretty_printed_object():
    data = benchmark.parse_json_result('{\n  "result": "Verdict: SHIP"\n}\n')
    assert data["result"] == "Verdict: SHIP"


def test_git_raises_when_git_is_not_on_path(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SystemExit):
        benchmark._git()


def test_ask_reports_a_missing_cli(tmp_path):
    with pytest.raises(benchmark.ToolFailureError, match="not on PATH"):
        benchmark.ask(["no-such-cli-anywhere", "{prompt}"], "hello", tmp_path, 5)


def test_load_cases_with_no_name_lists_every_case(tmp_path):
    root = make_repo(tmp_path)
    write_case(root, "a", kind="clean", intent="x", patch_text="")
    write_case(root, "b", kind="clean", intent="y", patch_text="")
    cases = benchmark.load_cases(root, None)
    assert [c.name for c in cases] == ["a", "b"]


def test_load_cases_rejects_an_unknown_name(tmp_path):
    root = make_repo(tmp_path)
    with pytest.raises(SystemExit, match="no case named"):
        benchmark.load_cases(root, "missing")


def test_main_rejects_zero_runs_and_zero_jobs(tmp_path, monkeypatch, capsys):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(SystemExit):
        run_main(monkeypatch, "--root", str(root), "--runs", "0")
    assert "at least 1" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        run_main(monkeypatch, "--root", str(root), "--jobs", "0")
    assert "at least 1" in capsys.readouterr().err


def test_main_runs_every_case_in_parallel_with_jobs(tmp_path, fake_claude, monkeypatch, capsys):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "clean-a", kind="clean", intent="Add a line, take one.", patch_text=patch)
    write_case(root, "clean-b", kind="clean", intent="Add a line, take two.", patch_text=patch)
    fake_claude(
        {
            fake_query("Add a line, take one."): cli_answer("Verdict: SHIP"),
            fake_query("Add a line, take two."): cli_answer("Verdict: SHIP"),
        }
    )
    code = run_main(monkeypatch, "--root", str(root), "--jobs", "2")
    assert code == 0
    assert "false-alarm rate: 0%" in capsys.readouterr().out


def test_main_honours_a_model_and_a_custom_command(tmp_path, fake_cli, monkeypatch):
    configure = fake_cli("mycli")
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "only-one", kind="clean", intent="Add a trailing line.", patch_text=patch)
    configure({fake_query("Add a trailing line."): cli_answer("Verdict: SHIP")})
    code = run_main(
        monkeypatch,
        "--root",
        str(root),
        "--case",
        "only-one",
        "--command",
        "mycli --quiet {prompt}",
    )
    assert code == 0


def test_majority_vote_across_runs_uses_the_winning_report(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "voted", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude(
        {
            fake_query("Add a trailing line."): [
                cli_answer("Verdict: SHIP"),
                cli_answer("Verdict: SHIP"),
                cli_answer("Verdict: STOP"),
            ]
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "voted",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(runs=3),
    )
    assert result["verdict"] == "SHIP"
    assert result["passed"] is True
    assert result["runs"] == 3


def test_a_defect_split_fix_stop_ship_passes_on_two_judged_hits(tmp_path, fake_claude):
    # FIX, STOP and SHIP are three different verdict words, so a vote over the words
    # alone is a three-way tie broken by whichever ran first (SHIP, a miss). Voting on
    # the judged outcome instead sees two hits (FIX, STOP) and one miss (SHIP).
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "defect-three-way",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt"],
    )
    fake_claude(
        {
            fake_query("Drop a redundant flag."): [
                cli_answer("Verdict: FIX\n\nfile.txt lost a safeguard."),
                cli_answer("Verdict: STOP\n\nfile.txt lost a safeguard."),
                cli_answer("Verdict: SHIP\n\nLooks fine."),
            ]
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "defect-three-way",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(runs=3),
    )
    assert result["passed"] is True
    assert result["passes"] == 2
    assert result["verdict"] in ("FIX", "STOP")


def test_a_first_fix_run_missing_must_mention_still_passes_on_later_hits(tmp_path, fake_claude):
    # The first run's report is the one an earlier version checked `must_mention`
    # against, regardless of which verdict word actually won. Here the first FIX run
    # misses the mention and the STOP and FIX runs that follow both carry it: two of
    # three runs are judged hits, and the case should pass on them.
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(
        root,
        "defect-later-hit",
        kind="defect",
        intent="Drop a redundant flag.",
        patch_text=patch,
        must_mention=["file\\.txt"],
    )
    fake_claude(
        {
            fake_query("Drop a redundant flag."): [
                cli_answer("Verdict: FIX\n\nSomething is missing here."),
                cli_answer("Verdict: STOP\n\nfile.txt lost a safeguard."),
                cli_answer("Verdict: FIX\n\nfile.txt lost a safeguard."),
            ]
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "defect-later-hit",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(runs=3),
    )
    assert result["passed"] is True
    assert result["passes"] == 2


def test_a_clean_case_split_ship_fix_fix_fails(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "clean-split", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude(
        {
            fake_query("Add a trailing line."): [
                cli_answer("Verdict: SHIP\n\nNothing further is owed."),
                cli_answer("Verdict: FIX\n\nfalse alarm one."),
                cli_answer("Verdict: FIX\n\nfalse alarm two."),
            ]
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "clean-split",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(runs=3),
    )
    assert result["passed"] is False
    assert result["passes"] == 1


def test_a_tied_vote_with_two_runs_fails(tmp_path, fake_claude):
    # A tie is a coin flip, not a decision. Rewarding whichever run happened to come
    # first would let an unstable reviewer pass by luck of ordering.
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "clean-tie", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude(
        {
            fake_query("Add a trailing line."): [
                cli_answer("Verdict: SHIP\n\nNothing further is owed."),
                cli_answer("Verdict: FIX\n\nfalse alarm."),
            ]
        }
    )
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "clean-tie",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(runs=2),
    )
    assert result["passed"] is False
    assert result["passes"] == 1


# --- the least-privilege allowlist and harness-level failure diagnostics ------------

FORBIDDEN_SUBSTRINGS = ("push", "fetch", "curl", "write", "edit", "notebookedit")


def test_allowed_tools_contains_no_obvious_write_or_network_command_name():
    # A prefix match, not a read-only guarantee: `git diff --output=<path>` still
    # writes, and `make test` executes the worktree's own code. This only holds that
    # no entry's own command *name* is an obvious write or network tool.
    for entry in benchmark.ALLOWED_TOOLS:
        lowered = entry.lower()
        for bad in FORBIDDEN_SUBSTRINGS:
            assert bad not in lowered, entry
        assert not re.search(r"\brm\b", lowered), entry


def test_default_command_passes_the_allowlist_and_the_denylist():
    argv = benchmark.build_command(None, None, 40, 2.00)
    assert "--allowedTools" in argv
    assert "--disallowedTools" in argv
    # still under dontAsk, not bypassPermissions or auto: an unlisted tool must be
    # denied rather than silently approved.
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"


def test_every_allow_and_deny_rule_is_its_own_argv_element():
    # `--allowedTools <tools...>` is variadic and a rule may contain spaces
    # (`Bash(git diff *)`), so a joined string would misparse if the CLI ever stopped
    # accepting a single comma-joined value; each rule must survive as one element.
    argv = benchmark.build_command(None, None, 40, 2.00)
    allow_start = argv.index("--allowedTools") + 1
    allow_end = argv.index("--disallowedTools")
    assert argv[allow_start:allow_end] == list(benchmark.ALLOWED_TOOLS)
    deny_start = allow_end + 1
    deny_end = argv.index("--max-turns")
    assert argv[deny_start:deny_end] == list(benchmark.DISALLOWED_TOOLS)


def test_the_prompt_precedes_the_variadic_allow_and_deny_flags():
    # A variadic option consumes every following element until the next flag-looking
    # token, so the prompt has to sit before --allowedTools/--disallowedTools starts,
    # or it would be read as one more tool name rather than as the prompt.
    argv = benchmark.build_command(None, None, 40, 2.00)
    assert argv.index("{prompt}") < argv.index("--allowedTools")


def test_a_custom_command_does_not_carry_the_allowlist_or_the_denylist():
    argv = benchmark.build_command("mycli {prompt}", None, 40, 2.00)
    assert "--allowedTools" not in argv
    assert "--disallowedTools" not in argv


def test_allowed_tools_use_the_space_form_not_the_colon_form():
    for entry in benchmark.ALLOWED_TOOLS:
        assert ":*" not in entry, entry


def test_disallowed_tools_covers_every_named_write_or_network_command():
    joined = " ".join(benchmark.DISALLOWED_TOOLS)
    for must_have in (
        "git push",
        "git fetch",
        "git pull",
        "git clone",
        "git remote",
        "git reset",
        "git checkout",
        "git worktree",
        "curl",
        "wget",
        "rm ",
        "ssh",
        "scp",
        "nc ",
        "pip",
        "npm",
        "Write",
        "Edit",
        "NotebookEdit",
    ):
        assert must_have in joined, must_have


def test_nothing_is_both_allowed_and_denied():
    assert set(benchmark.ALLOWED_TOOLS).isdisjoint(benchmark.DISALLOWED_TOOLS)


def test_diagnose_failure_reports_the_denied_command():
    data = {
        "permission_denials": [
            {"tool_name": "Bash", "tool_input": {"command": "git status --short"}}
        ]
    }
    assert benchmark.diagnose_failure(data) == "permission denied: Bash: git status --short"


def test_diagnose_failure_reports_several_denials_in_order():
    data = {
        "permission_denials": [
            {"tool_name": "Bash", "tool_input": {"command": "git diff HEAD"}},
            {"tool_name": "Write", "tool_input": {"file_path": "docs/ci.md"}},
        ]
    }
    assert benchmark.diagnose_failure(data) == (
        'permission denied: Bash: git diff HEAD; Write: {"file_path": "docs/ci.md"}'
    )


def test_denial_texts_falls_back_to_the_bare_tool_name_with_no_input():
    assert benchmark.denial_texts({"permission_denials": [{"tool_name": "Bash"}]}) == ["Bash"]


def test_denial_texts_truncates_a_long_command_at_200_characters():
    command = "git diff " + "x" * 250
    texts = benchmark.denial_texts(
        {"permission_denials": [{"tool_name": "Bash", "tool_input": {"command": command}}]}
    )
    assert texts[0].startswith("Bash: git diff xxx")
    assert len(texts[0]) < len(command)
    assert texts[0].endswith("…")


def test_diagnose_failure_reports_budget_exhausted():
    assert benchmark.diagnose_failure({"subtype": "error_max_budget_usd"}) == "budget exhausted"


def test_diagnose_failure_reports_turn_limit():
    assert benchmark.diagnose_failure({"subtype": "error_max_turns"}) == "turn limit"


def test_diagnose_failure_is_none_when_nothing_is_wrong():
    assert benchmark.diagnose_failure({"result": "Verdict: SHIP"}) is None
    assert benchmark.diagnose_failure({}) is None


def test_a_denied_tool_call_is_reported_instead_of_no_verdict(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "denied", kind="clean", intent="Add a trailing line.", patch_text=patch)
    payload = json.dumps({"permission_denials": [{"tool_name": "Bash"}], "total_cost_usd": 0.02})
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "denied",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert result["reason"] == "permission denied: Bash"
    assert result["denials"] == ["Bash"]
    assert result["verdict"] is None


def test_a_budget_exhausted_run_is_reported_instead_of_no_verdict(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "budget", kind="clean", intent="Add a trailing line.", patch_text=patch)
    payload = json.dumps({"subtype": "error_max_budget_usd", "total_cost_usd": 1.0})
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "budget",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert result["reason"] == "budget exhausted"


def test_a_turn_limit_run_is_reported_instead_of_no_verdict(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "turns", kind="clean", intent="Add a trailing line.", patch_text=patch)
    payload = json.dumps({"subtype": "error_max_turns", "total_cost_usd": 0.5})
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "turns",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert result["reason"] == "turn limit"


def test_a_real_verdict_with_stray_denials_still_reports_the_verdict(tmp_path, fake_claude):
    # A denial earlier in a run that still reached a verdict should not be treated as
    # the reason the case failed - the verdict is what judge() reads.
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "recovered", kind="clean", intent="Add a trailing line.", patch_text=patch)
    payload = json.dumps(
        {
            "result": "Verdict: SHIP\n\nNothing further is owed.",
            "permission_denials": [{"tool_name": "Bash"}],
            "total_cost_usd": 0.03,
        }
    )
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "recovered",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["verdict"] == "SHIP"
    assert result["passed"] is True
    assert result["denials"] == ["Bash"]


# --- tolerant verdict parsing --------------------------------------------------------


@pytest.mark.parametrize(
    ("report", "verdict"),
    [
        ("Verdict: SHIP\n\nNothing further is owed.", "SHIP"),
        ("**Verdict: SHIP**\n\nFindings.", "SHIP"),
        ("Verdict: **FIX**\n\nFindings.", "FIX"),
        ("## Verdict: STOP\n\nFindings.", "STOP"),
        ("> Verdict: FIX\n\nFindings.", "FIX"),
        ("- Verdict: SHIP\n\nFindings.", "SHIP"),
        ("* Verdict: STOP\n\nFindings.", "STOP"),
        ("_Verdict: FIX_\n\nFindings.", "FIX"),
        ("`Verdict: SHIP`\n\nFindings.", "SHIP"),
        ("Some findings first.\n\nVerdict: STOP\n\nMore text after.", "STOP"),
    ],
)
def test_verdict_re_matches_every_decorated_form(report, verdict):
    match = benchmark.VERDICT_RE.search(report)
    assert match is not None, report
    assert match.group(1) == verdict


@pytest.mark.parametrize(
    "report",
    [
        "no verdict: FIX yet, still reviewing.",
        "There is no verdict: FIX has not been decided.",
        "The reviewer said Verdict: FIX inline, not at the start of a line.",
        "Verdict: MAYBE\n\nnot one of the three words.",
        "Verdicts: FIX\n\nplural, not the word.",
    ],
)
def test_verdict_re_does_not_match_prose_mentioning_the_word(report):
    assert benchmark.VERDICT_RE.search(report) is None


@pytest.mark.parametrize(
    "report",
    [
        "#" * 50000 + "x",
        "> " * 20000 + "Verdict",
    ],
)
def test_verdict_re_stays_linear_on_a_long_run_of_decoration(report):
    # CodeQL's py/redos flagged an earlier version of VERDICT_RE: a repeated group
    # each carrying its own unbounded quantifier (`(?:[...]+\s*)*`) has exponentially
    # many ways to split a long run of decoration characters across the two
    # quantifiers. Neither input here reaches "Verdict:" cleanly (the first has no
    # colon at all; the second never gets to the literal word inside the class), so
    # both are expected to return None — the regression is a hang, not a false match.
    start = time.monotonic()
    match = benchmark.VERDICT_RE.search(report)
    elapsed = time.monotonic() - start
    assert match is None
    assert elapsed < 1.0, f"took {elapsed:.3f}s, should be linear in the input length"


# --- capturing what the model said on a "no verdict" outcome -------------------------


def test_no_verdict_detail_captures_head_tail_turns_and_stop_reason():
    report = "x" * 500
    data = {"num_turns": 9, "stop_reason": "tool_use", "subtype": "success"}
    reason, detail = benchmark.no_verdict_detail(data, report)
    assert detail["result_head"] == report[:300]
    assert detail["result_tail"] == report[-300:]
    assert detail["num_turns"] == 9
    assert detail["stop_reason"] == "tool_use"
    assert detail["subtype"] == "success"
    assert "9 turns" in reason
    assert "stop_reason=tool_use" in reason
    assert "subtype=success" in reason


def test_no_verdict_detail_falls_back_to_terminal_reason():
    reason, detail = benchmark.no_verdict_detail({"terminal_reason": "budget_exhausted"}, "short")
    assert detail["stop_reason"] == "budget_exhausted"
    assert "stop_reason=budget_exhausted" in reason


def test_no_verdict_detail_has_no_tail_when_the_report_is_short():
    reason, detail = benchmark.no_verdict_detail({}, "short report")
    assert detail["result_tail"] == ""
    assert detail["result_head"] == "short report"
    assert reason == "no verdict"


def test_a_no_verdict_run_records_head_tail_turns_and_stop_reason(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "rambling", kind="clean", intent="Add a trailing line.", patch_text=patch)
    long_report = "I looked at it. " * 40
    payload = cli_answer(long_report, num_turns=11, stop_reason="end_turn")
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "rambling",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["passed"] is False
    assert result["verdict"] is None
    assert "11 turns" in result["reason"]
    assert "stop_reason=end_turn" in result["reason"]
    assert result["result_head"] == long_report[:300]
    assert result["result_tail"] == long_report[-300:]
    assert result["num_turns"] == 11
    assert result["stop_reason"] == "end_turn"


def test_a_ship_verdict_carries_no_no_verdict_detail(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "clean-ship", kind="clean", intent="Add a trailing line.", patch_text=patch)
    fake_claude({fake_query("Add a trailing line."): cli_answer("Verdict: SHIP")})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "clean-ship",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert result["result_head"] == ""
    assert result["result_tail"] == ""
    assert result["num_turns"] is None


# --- reporting every model in modelUsage, not just the first ------------------------


def test_model_costs_returns_every_model_with_its_own_cost():
    data = {
        "modelUsage": {
            "claude-haiku-4-5": {"costUSD": 0.001},
            "claude-fable-5-1": {"costUSD": 1.01},
        }
    }
    assert set(benchmark.model_costs(data)) == {
        ("claude-haiku-4-5", 0.001),
        ("claude-fable-5-1", 1.01),
    }


def test_model_costs_is_empty_with_no_model_usage():
    assert benchmark.model_costs({}) == []


def test_model_costs_handles_a_missing_cost_key():
    data = {"modelUsage": {"claude-fable-5-1": {}}}
    assert benchmark.model_costs(data) == [("claude-fable-5-1", None)]


def test_run_case_reports_every_model_with_its_cost(tmp_path, fake_claude):
    root = make_repo(tmp_path)
    patch = make_patch(root, "one\ntwo\nthree\nfour\n")
    write_case(root, "two-models", kind="clean", intent="Add a trailing line.", patch_text=patch)
    payload = cli_answer(
        "Verdict: SHIP",
        modelUsage={
            "claude-haiku-4-5": {"costUSD": 0.0011},
            "claude-fable-5-1": {"costUSD": 1.0103},
        },
    )
    fake_claude({fake_query("Add a trailing line."): payload})
    result = benchmark.run_case(
        root / ".claude" / "agents" / "benchmarks" / "reviewer" / "two-models",
        root,
        benchmark.build_command(None, None, 40, 2.00),
        Args(),
    )
    assert any("claude-fable-5-1" in m and "1.0103" in m for m in result["models"])
    assert any("claude-haiku-4-5" in m and "0.0011" in m for m in result["models"])
