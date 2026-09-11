"""The eval harness is what decides whether a description works, and it had no tests.

Nothing here reaches a model. A fake `claude` on PATH answers from a table, which is
enough to exercise every path the real one takes: the vote, the margin, routing,
the listing budget, the baseline diff, and the three ways the CLI can fail.
"""

from __future__ import annotations

import json
import sys

import pytest

from tests.conftest import load_script

harness = load_script("run_trigger_eval.py")


CLAUDE = ["claude", "-p", "{prompt}"]


class Args:
    def __init__(self, **overrides):
        self.runs = 3
        self.model = None
        self.command = list(CLAUDE)
        self.jobs = 1
        self.timeout = 30
        self.budget = None
        self.verbose = False
        self.__dict__.update(overrides)


# --- judge: the scoring rule in isolation ------------------------------------------


@pytest.mark.parametrize(
    ("case", "chosen", "passed", "reason"),
    [
        ({"should_trigger": True}, "alpha", True, ""),
        ({"should_trigger": True}, "NONE", False, "wanted alpha"),
        ({"should_trigger": True}, "beta", False, "wanted alpha"),
        ({"should_trigger": False}, "alpha", False, "wanted not alpha"),
        ({"should_trigger": False}, "NONE", True, ""),
        ({"should_trigger": False}, "gamma", True, ""),
        ({"should_trigger": False, "expected": "beta"}, "beta", True, ""),
        (
            {"should_trigger": False, "expected": "beta"},
            "gamma",
            False,
            "routed to gamma, expected beta",
        ),
        (
            {"should_trigger": False, "expected": "beta"},
            "NONE",
            False,
            "routed to NONE, expected beta",
        ),
        ({"should_trigger": False, "expected": "beta"}, "alpha", False, "wanted not alpha"),
    ],
)
def test_judge(case, chosen, passed, reason):
    assert harness.judge(case, chosen, "alpha") == (passed, reason)


# --- render: what the model is shown ------------------------------------------------


ENTRIES = {
    "alpha": ("skill", "A" * 100),
    "beta": ("skill", "B" * 100),
    "reader": ("subagent", "R" * 100),
}


def test_render_without_a_budget_shows_everything_and_labels_subagents():
    listing = harness.render(ENTRIES, None, "alpha")
    assert listing.splitlines() == [
        f"- alpha: {'A' * 100}",
        f"- beta: {'B' * 100}",
        f"- reader (subagent): {'R' * 100}",
    ]


def test_render_under_budget_drops_the_target_first_and_keeps_every_name():
    # 250 fits two of three descriptions. The target loses its own first, because the
    # runtime drops the least-used entries and a skill under test is the newest one.
    lines = harness.render(ENTRIES, 250, "beta").splitlines()
    assert lines[1] == "- beta"
    assert lines[0].startswith("- alpha: A") and lines[2].startswith("- reader (subagent): R")


def test_render_under_a_tiny_budget_leaves_only_names():
    assert harness.render(ENTRIES, 10, "alpha").splitlines() == [
        "- alpha",
        "- beta",
        "- reader (subagent)",
    ]


def test_render_caps_each_entry_at_the_runtime_limit():
    entries = {"long": ("skill", "x" * (harness.ENTRY_CAP + 500))}
    line = harness.render(entries, None, "other")
    assert line == f"- long: {'x' * harness.ENTRY_CAP}"


# --- catalogue and targets ----------------------------------------------------------


def test_catalogue_contains_skills_and_subagents_with_collapsed_whitespace(mini_repo):
    entries = harness.catalogue(mini_repo)
    assert set(entries) == {"alpha", "beta", "reader"}
    assert entries["alpha"][0] == "skill" and entries["reader"][0] == "subagent"
    assert "\n" not in entries["reader"][1]


def test_all_targets_finds_every_eval_set(mini_repo):
    targets = harness.all_targets(mini_repo)
    assert {(t.name, t.kind) for t in targets} == {
        ("alpha", "skill"),
        ("beta", "skill"),
        ("reader", "subagent"),
    }
    assert all(t.eval_set.is_file() for t in targets)


def test_a_repo_local_subagent_is_a_target_and_is_in_the_listing(mini_repo):
    # The harness and the validator walk subagents through the same helper. They did
    # not always: the validator learned about `.claude/agents/` first, and for as long
    # as the harness had its own plugin-only walk a repo-local subagent validated clean
    # and could never be scored — worse, an explicit --agent run rendered a listing its
    # own name was missing from, so every positive scored as a miss.
    directory = mini_repo / ".claude" / "agents"
    directory.mkdir(parents=True)
    (directory / "local-helper.md").write_text(
        "---\nname: local-helper\ndescription: Do one narrow thing for work on this "
        "repository. Use when the caller is changing something here.\ntools: Read\n---\n\n"
        "Body.\n",
        encoding="utf-8",
    )
    (directory / "evals").mkdir()
    (directory / "evals" / "local-helper.json").write_text(
        json.dumps([{"query": "do the narrow thing", "should_trigger": True}]), encoding="utf-8"
    )
    entries = harness.catalogue(mini_repo)
    assert entries["local-helper"][0] == "subagent"
    assert "local-helper" in harness.render(entries, None, "alpha")
    assert ("local-helper", "subagent") in {
        (t.name, t.kind) for t in harness.all_targets(mini_repo)
    }


def test_a_target_without_an_eval_set_is_refused(mini_repo, fake_claude):
    bare = harness.Target.skill(mini_repo / "plugins" / "engineering" / "skills" / "nothing")
    with pytest.raises(SystemExit, match="no eval set"):
        harness.score(bare, {}, Args())


# --- score: the vote, the margin, routing -------------------------------------------


def _alpha(mini_repo):
    return harness.Target.skill(mini_repo / "plugins" / "engineering" / "skills" / "alpha")


def test_a_perfect_run_scores_everything(mini_repo, fake_claude):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers.update({f"alpha negative {i}": "beta" for i in range(8)})
    fake_claude(answers)
    report = harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args())
    assert (report["rate"], report["recall"], report["specificity"]) == (1.0, 1.0, 1.0)
    assert report["routing"] == 1.0  # every expected negative went to beta
    assert report["narrow"] == 0 and report["failures"] == []


def test_a_negative_that_lands_on_the_wrong_sibling_is_a_routing_miss(mini_repo, fake_claude):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers.update({f"alpha negative {i}": "reader" for i in range(8)})  # not beta
    fake_claude(answers)
    report = harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args())
    # Half the negatives carry expected=beta; those fail on routing, the rest pass.
    assert report["specificity"] == 0.5
    assert report["routing"] == 0.0
    assert all(f["reason"].startswith("routed to reader") for f in report["failures"])


def test_routing_is_absent_when_no_negative_names_a_winner(mini_repo, fake_claude):
    beta = harness.Target.skill(mini_repo / "plugins" / "engineering" / "skills" / "beta")
    fake_claude({f"beta positive {i}": "beta" for i in range(8)})
    report = harness.score(beta, harness.catalogue(mini_repo), Args())
    assert report["routing"] is None


def test_a_split_vote_is_counted_as_narrow_and_the_majority_wins(mini_repo, fake_claude):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers["alpha positive 0"] = ["alpha", "NONE", "alpha"]  # 2-1 for alpha
    answers["alpha positive 1"] = ["NONE", "alpha", "NONE"]  # 2-1 against
    fake_claude(answers)
    report = harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args())
    by_query = {r["query"]: r for r in [*report["failures"]]}
    assert report["narrow"] == 2
    assert "alpha positive 0" not in by_query  # majority alpha: passed
    assert (
        by_query["alpha positive 1"]["margin"] == 1
        and by_query["alpha positive 1"]["chose"] == "NONE"
    )


def test_verbose_prints_the_split(mini_repo, fake_claude, capsys):
    fake_claude({"alpha positive 0": ["alpha", "NONE", "alpha"]})
    harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args(verbose=True))
    err = capsys.readouterr().err
    assert "(2-1 split)" in err


def test_the_budget_changes_what_the_model_is_shown(mini_repo, fake_claude, monkeypatch):
    seen = []
    real_ask = harness.ask

    def spy(prompt, command, timeout, names=frozenset()):
        seen.append(prompt)
        return real_ask(prompt, command, timeout, names)

    monkeypatch.setattr(harness, "ask", spy)
    fake_claude({})
    harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args(budget=1))
    assert seen and "- alpha\n" in seen[0] and "- alpha:" not in seen[0]


# --- ask: the three ways the CLI fails, each of which must abort ---------------------


def test_ask_takes_the_last_non_empty_line(fake_claude):
    fake_claude({"hello": "alpha"})
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), CLAUDE, 30) == "alpha"


@pytest.mark.parametrize(
    ("raw", "name"),
    [
        ("ci-log-reader (subagent)", "ci-log-reader"),
        ("ci-triage (skill)", "ci-triage"),
        ("`ci-triage`", "ci-triage"),
        ("- ci-triage", "ci-triage"),
        ("ci-triage.", "ci-triage"),
        ("**ci-log-reader (subagent)**", "ci-log-reader"),
        ("NONE", "NONE"),
        ("ci-triage", "ci-triage"),
        ('"ci-triage"', "ci-triage"),
        ("'k8s-triage'", "k8s-triage"),
    ],
)
def test_an_echoed_label_is_reduced_to_the_bare_name(raw, name):
    # The catalogue shows `name (subagent)`, so a model that copies the label would
    # otherwise never match the judge and every positive would read as a miss.
    assert harness.normalise(raw) == name


def test_an_echoed_label_still_scores_as_fired(fake_claude):
    fake_claude({"hello": "reader (subagent)"})
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), CLAUDE, 30) == "reader"


def test_a_failing_cli_raises_rather_than_scoring(fake_claude):
    fake_claude(mode="fail")
    with pytest.raises(harness.ToolFailure, match="exited 1"):
        harness.ask("x", CLAUDE, 30)


def test_an_empty_answer_raises_rather_than_scoring(fake_claude):
    fake_claude(mode="empty")
    with pytest.raises(harness.ToolFailure, match="returned nothing"):
        harness.ask("x", CLAUDE, 30)


def test_a_missing_cli_raises_rather_than_scoring(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # nothing on it
    with pytest.raises(harness.ToolFailure, match="`claude` CLI is not on PATH"):
        harness.ask("x", CLAUDE, 30)


def test_a_model_flag_is_passed_through(fake_claude, tmp_path, monkeypatch):
    fake_claude({"q": "alpha"})
    seen = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_ARGV_FILE", str(seen))
    command = harness.build_command("claude", None, "haiku")
    assert harness.ask(harness.PROMPT.format(catalogue="", query="q"), command, 30) == "alpha"
    assert json.loads(seen.read_text())[-2:] == ["--model", "haiku"]


# --- backends: the harness holds no credential, the CLI does ---------------------------


@pytest.mark.parametrize(
    ("backend", "model", "argv"),
    [
        ("claude", None, ["claude", "-p", "{prompt}"]),
        ("claude", "opus", ["claude", "-p", "{prompt}", "--model", "opus"]),
        ("codex", None, ["codex", "exec", "--skip-git-repo-check", "{prompt}"]),
        (
            "codex",
            "o4-mini",
            ["codex", "exec", "--skip-git-repo-check", "{prompt}", "--model", "o4-mini"],
        ),
        ("gemini", "gemini-2.5-pro", ["gemini", "-p", "{prompt}", "--model", "gemini-2.5-pro"]),
        ("ollama", "llama3.1", ["ollama", "run", "llama3.1", "{prompt}"]),
    ],
)
def test_each_backend_builds_its_own_argv(backend, model, argv):
    assert harness.build_command(backend, None, model) == argv


def test_a_backend_with_a_positional_model_refuses_to_run_without_one():
    with pytest.raises(ValueError, match="ollama backend needs --model"):
        harness.build_command("ollama", None, None)


def test_a_custom_command_wins_over_the_backend_and_may_take_the_model():
    assert harness.build_command("claude", "mycli --quiet {prompt}", None) == [
        "mycli",
        "--quiet",
        "{prompt}",
    ]
    assert harness.build_command("claude", "mycli -m {model} {prompt}", "tiny") == [
        "mycli",
        "-m",
        "tiny",
        "{prompt}",
    ]
    # A model given to a template that has no slot for it is not silently dropped.
    assert harness.build_command("claude", "mycli {prompt}", "tiny") == ["mycli", "{prompt}"]


def test_a_custom_command_without_a_prompt_slot_is_refused():
    with pytest.raises(ValueError, match="must contain {prompt}"):
        harness.build_command("claude", "mycli --quiet", None)
    with pytest.raises(ValueError, match="command backend needs --model"):
        harness.build_command("claude", "mycli -m {model} {prompt}", None)


def test_another_cli_on_path_answers_the_same_way(fake_cli):
    configure = fake_cli("codex")
    configure({"hello": "alpha"})
    command = harness.build_command("codex", None, None)
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), command, 30) == "alpha"


def test_a_custom_command_runs_whatever_was_named(fake_cli, tmp_path, monkeypatch):
    configure = fake_cli("mycli")
    configure({"hello": "beta"})
    seen = tmp_path / "argv.json"
    monkeypatch.setenv("FAKE_ARGV_FILE", str(seen))
    command = harness.build_command("claude", "mycli --quiet {prompt}", None)
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), command, 30) == "beta"
    assert json.loads(seen.read_text())[0] == "--quiet"


def test_a_failure_names_the_cli_that_failed(fake_cli):
    configure = fake_cli("codex")
    configure(mode="fail")
    with pytest.raises(harness.ToolFailure, match="the `codex` CLI exited 1"):
        harness.ask("x", harness.build_command("codex", None, None), 30)


def test_a_fenced_answer_is_read_through_the_fence(fake_claude):
    fake_claude({"hello": "alpha"}, mode="fenced")
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), CLAUDE, 30) == "alpha"


def test_a_footer_after_the_answer_is_skipped_when_the_catalogue_is_known(fake_claude):
    # codex prints token counts after its reply. Read as the last line, every answer
    # would be the footer and every skill would score zero for a reason nobody looks for.
    fake_claude({"hello": "alpha"}, mode="footer")
    prompt = harness.PROMPT.format(catalogue="", query="hello")
    assert harness.ask(prompt, CLAUDE, 30, frozenset({"alpha"})) == "alpha"
    assert harness.ask(prompt, CLAUDE, 30) == "tokens used: 1234"


def test_a_name_in_the_wrong_case_is_matched_to_the_catalogue(fake_claude):
    fake_claude({"hello": "Alpha", "bye": "None"})
    prompt = harness.PROMPT.format(catalogue="", query="hello")
    assert harness.ask(prompt, CLAUDE, 30, frozenset({"alpha"})) == "alpha"
    prompt = harness.PROMPT.format(catalogue="", query="bye")
    assert harness.ask(prompt, CLAUDE, 30, frozenset({"alpha"})) == "NONE"


def test_stdin_is_closed_so_a_client_that_reads_it_does_not_wait(fake_claude):
    fake_claude({"hello": "alpha"}, mode="stdin")
    assert harness.ask(harness.PROMPT.format(catalogue="", query="hello"), CLAUDE, 5) == "alpha"


# --- main: the command line end to end ----------------------------------------------


def run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["run_trigger_eval.py", *argv])
    return harness.main()


def test_even_runs_are_rejected(mini_repo, monkeypatch, capsys):
    with pytest.raises(SystemExit) as caught:
        run_main(monkeypatch, "--all", "--root", str(mini_repo), "--runs", "2")
    assert caught.value.code == 2
    assert "must be a positive odd number" in capsys.readouterr().err


def test_all_scores_skills_and_subagents_and_writes_json_incrementally(
    mini_repo, fake_claude, monkeypatch, capsys, tmp_path
):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    fake_claude(answers)
    out = tmp_path / "out.json"
    code = run_main(monkeypatch, "--all", "--root", str(mini_repo), "--json", str(out))
    text = capsys.readouterr().out
    assert code == 1  # beta and reader never fire, so they are below threshold
    reports = json.loads(out.read_text())
    assert [r["target"] for r in reports] == ["alpha", "beta", "reader"]
    assert reports[2]["kind"] == "subagent"
    assert "routing" in text and "narrow" in text


def test_a_tool_failure_aborts_with_scores_so_far_written(
    mini_repo, fake_claude, monkeypatch, capsys, tmp_path
):
    # alpha scores fine; then the CLI dies before beta. The file must hold alpha only.
    out = tmp_path / "out.json"
    original = harness.score
    calls = []

    def flaky(target, entries, args):
        calls.append(target.name)
        if target.name == "beta":
            raise harness.ToolFailure("simulated")
        return original(target, entries, args)

    monkeypatch.setattr(harness, "score", flaky)
    fake_claude({f"alpha positive {i}": "alpha" for i in range(8)})
    code = run_main(monkeypatch, "--all", "--root", str(mini_repo), "--json", str(out))
    assert code == 2
    assert [r["target"] for r in json.loads(out.read_text())] == ["alpha"]
    assert "aborting: simulated" in capsys.readouterr().err
    assert calls == ["alpha", "beta"]


def test_single_skill_and_single_agent_targets(mini_repo, fake_claude, monkeypatch, capsys):
    fake_claude({f"reader positive {i}": "reader" for i in range(8)})
    agent = mini_repo / "plugins" / "engineering" / "agents" / "reader.md"
    assert run_main(monkeypatch, "--agent", str(agent), "--root", str(mini_repo)) == 1
    assert "reader" in capsys.readouterr().out
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    fake_claude({f"alpha positive {i}": "alpha" for i in range(8)})
    assert (
        run_main(monkeypatch, "--skill", str(skill), "--root", str(mini_repo), "--threshold", "0.4")
        == 0
    )


def test_baseline_prints_a_delta_and_new_for_unknown_targets(
    mini_repo, fake_claude, monkeypatch, capsys, tmp_path
):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps([{"target": "alpha", "rate": 0.5}, {"skill": "beta", "rate": 1.0}])
    )
    # alpha scores a perfect run; beta never fires, so it keeps only its negatives;
    # reader has no baseline row at all.
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers.update({f"alpha negative {i}": "beta" for i in range(0, 8, 2)})
    fake_claude(answers)
    run_main(
        monkeypatch,
        "--all",
        "--root",
        str(mini_repo),
        "--baseline",
        str(baseline),
        "--threshold",
        "0",
    )
    out = capsys.readouterr().out
    lines = {line.split()[0]: line for line in out.splitlines() if line and line[0].isalpha()}
    assert "delta" in lines["target"]
    assert lines["alpha"].rstrip().endswith("+50%")  # 0.5 -> 1.0
    assert lines["beta"].rstrip().endswith("-50%")  # 1.0 -> 0.5; legacy `skill` key still read
    assert lines["reader"].rstrip().endswith("new")


def test_a_missing_baseline_is_an_error(mini_repo, fake_claude, monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="no baseline"):
        run_main(monkeypatch, "--all", "--root", str(mini_repo), "--baseline", str(tmp_path / "x"))


def test_below_threshold_lists_every_miss_with_its_reason(
    mini_repo, fake_claude, monkeypatch, capsys
):
    fake_claude({})  # everything NONE
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    assert run_main(monkeypatch, "--skill", str(skill), "--root", str(mini_repo)) == 1
    err = capsys.readouterr().err
    assert "alpha below threshold" in err
    assert "wanted alpha, chose NONE: alpha positive 0" in err
    assert "routed to NONE, expected beta, chose NONE: alpha negative 0" in err


def test_an_empty_repository_has_nothing_to_score(tmp_path, monkeypatch, capsys):
    root = tmp_path / "empty"
    (root / "plugins").mkdir(parents=True)
    assert run_main(monkeypatch, "--all", "--root", str(root)) == 2
    assert "nothing has an eval set" in capsys.readouterr().err


def test_the_prompt_names_the_query_and_the_catalogue():
    prompt = harness.PROMPT.format(catalogue="- a: x", query="do the thing")
    assert "- a: x" in prompt and "do the thing" in prompt and "NONE" in prompt


def test_a_hanging_cli_raises_rather_than_scoring(fake_claude):
    fake_claude(mode="hang")
    with pytest.raises(harness.ToolFailure, match="timed out after 1s"):
        harness.ask("x", CLAUDE, 1)


def test_the_report_records_which_client_and_model_scored_it(mini_repo, fake_claude):
    fake_claude({})
    report = harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args(model="opus"))
    assert (report["backend"], report["model"]) == ("claude", "opus")


def test_main_resolves_the_backend_flags(mini_repo, fake_cli, monkeypatch, capsys, tmp_path):
    configure = fake_cli("codex")
    configure({f"alpha positive {i}": "alpha" for i in range(8)})
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    out = tmp_path / "out.json"
    argv = (
        "--skill",
        str(skill),
        "--root",
        str(mini_repo),
        "--backend",
        "codex",
        "--model",
        "o4-mini",
        "--threshold",
        "0",
        "--json",
        str(out),
    )
    assert run_main(monkeypatch, *argv) == 0
    report = json.loads(out.read_text())[0]
    assert (report["backend"], report["model"]) == ("codex", "o4-mini")


def test_main_rejects_a_command_without_a_prompt_slot(mini_repo, monkeypatch, capsys):
    with pytest.raises(SystemExit) as caught:
        run_main(monkeypatch, "--all", "--root", str(mini_repo), "--command", "mycli --quiet")
    assert caught.value.code == 2
    assert "must contain {prompt}" in capsys.readouterr().err


def test_parallel_jobs_score_the_same_as_one(mini_repo, fake_claude):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers.update({f"alpha negative {i}": "beta" for i in range(8)})
    fake_claude(answers)
    entries = harness.catalogue(mini_repo)
    serial = harness.score(_alpha(mini_repo), entries, Args(jobs=1))
    parallel = harness.score(_alpha(mini_repo), entries, Args(jobs=4))
    keys = ("rate", "recall", "specificity", "routing", "narrow", "unrecognised")
    assert [parallel[k] for k in keys] == [serial[k] for k in keys] == [1.0, 1.0, 1.0, 1.0, 0, 0]


def test_a_client_that_never_names_an_entry_aborts_rather_than_scoring_zero(mini_repo, fake_claude):
    queries = [f"alpha positive {i}" for i in range(8)] + [f"alpha negative {i}" for i in range(8)]
    fake_claude({q: "Sure, here is my analysis of the request" for q in queries})
    with pytest.raises(harness.ToolFailure, match="named a catalogue entry"):
        harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args())


def test_a_partly_unrecognised_run_is_counted_not_aborted(mini_repo, fake_claude):
    answers = {f"alpha positive {i}": "alpha" for i in range(8)}
    answers["alpha positive 0"] = "let me think about that"
    fake_claude(answers)
    report = harness.score(_alpha(mini_repo), harness.catalogue(mini_repo), Args())
    assert report["unrecognised"] == 1
    assert report["recall"] == 7 / 8


def test_show_listing_prints_what_the_model_would_see_and_asks_nothing(
    mini_repo, monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("PATH", str(tmp_path))  # no CLI at all, and none is needed
    argv = ("--all", "--root", str(mini_repo), "--show-listing", "--budget", "1")
    assert run_main(monkeypatch, *argv) == 0
    out = capsys.readouterr().out
    assert "# alpha (skill)" in out and "# reader (subagent)" in out
    assert "- alpha\n" in out  # its own description dropped first under the budget


def test_zero_jobs_is_rejected(mini_repo, monkeypatch, capsys):
    with pytest.raises(SystemExit) as caught:
        run_main(monkeypatch, "--all", "--root", str(mini_repo), "--jobs", "0")
    assert caught.value.code == 2
    assert "--jobs must be at least 1" in capsys.readouterr().err
