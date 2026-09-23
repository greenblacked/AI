"""The PostToolUse hook is the fastest feedback loop in the repository, and a hook that
is wrong is worse than none: it either nags on every edit or stays silent when it
should not. Each path it can take is pinned here.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import eval_set, load_script, write_agent, write_skill

hook = load_script("hooks/skill_hook.py")


def run_hook(monkeypatch, root: Path, payload) -> tuple[int, str]:
    monkeypatch.setattr(hook, "ROOT", root)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    return hook.main(), err.getvalue()


def payload(path: Path) -> dict:
    return {"tool_input": {"file_path": str(path)}}


def test_a_clean_skill_is_silent(mini_repo, monkeypatch):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha" / "SKILL.md"
    assert run_hook(monkeypatch, mini_repo, payload(skill)) == (0, "")


def test_a_broken_skill_exits_two_with_only_its_own_errors(mini_repo, monkeypatch):
    alpha = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (alpha / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Use this skill when x.\n---\n\nSee references/gone.md.\n",
        encoding="utf-8",
    )
    # Break beta too, to prove the hook reports the edited skill and not the tree.
    beta = mini_repo / "plugins" / "engineering" / "skills" / "beta"
    (beta / "SKILL.md").write_text("---\nname: other\n---\n\nBody.\n", encoding="utf-8")

    code, err = run_hook(monkeypatch, mini_repo, payload(alpha / "SKILL.md"))
    assert code == 2
    assert "found 1 error(s) in plugins/engineering/skills/alpha" in err
    assert "dangling-reference" in err
    assert "beta" not in err


def test_other_files_broken_stays_silent_for_a_clean_edit(mini_repo, monkeypatch):
    """The validator exits 1 whenever anything in the repository has findings, not only
    when the edited file does. A hook that read "nonzero exit" as "crashed" would nag on
    every edit as soon as anything else in the tree was already broken."""
    alpha = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    beta = mini_repo / "plugins" / "engineering" / "skills" / "beta"
    (beta / "SKILL.md").write_text("---\nname: other\n---\n\nBody.\n", encoding="utf-8")

    assert run_hook(monkeypatch, mini_repo, payload(alpha / "SKILL.md")) == (0, "")


def test_a_validator_crash_is_reported_rather_than_silent(mini_repo, monkeypatch):
    """A nonzero exit with no ERROR line anywhere — a SyntaxError in rules.py, an
    uncaught exception — used to be read the same as "some other file has findings" and
    the hook returned 0, turning itself off with no signal."""
    alpha = mini_repo / "plugins" / "engineering" / "skills" / "alpha"

    def crashed(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Traceback (most recent call last):\n  ...\nSyntaxError: invalid syntax\n",
        )

    monkeypatch.setattr(hook.subprocess, "run", crashed)
    code, err = run_hook(monkeypatch, mini_repo, payload(alpha / "SKILL.md"))
    assert code == 2
    assert "did not run to completion" in err
    assert "SyntaxError" in err


def test_an_edit_to_a_reference_file_is_attributed_to_its_skill(mini_repo, monkeypatch):
    alpha = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (alpha / "references").mkdir()
    (alpha / "references" / "depth.md").write_text("depth\n", encoding="utf-8")
    (alpha / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: x\n---\n\nSee references/missing.md\n", encoding="utf-8"
    )
    code, err = run_hook(monkeypatch, mini_repo, payload(alpha / "references" / "depth.md"))
    assert code == 2 and "references/missing.md" in err


def test_warnings_are_deliberately_not_reported(mini_repo, monkeypatch):
    # A skill with no eval set earns a warning from the validator, never from the hook.
    lonely = write_skill(mini_repo, "engineering", "lonely", evals=None)
    assert run_hook(monkeypatch, mini_repo, payload(lonely / "SKILL.md")) == (0, "")


def test_a_file_outside_the_repository_is_ignored(mini_repo, monkeypatch, tmp_path):
    outside = tmp_path / "elsewhere" / "SKILL.md"
    outside.parent.mkdir()
    outside.write_text("---\nname: nope\n---\n", encoding="utf-8")
    assert run_hook(monkeypatch, mini_repo, payload(outside)) == (0, "")


def test_a_file_not_inside_any_skill_is_ignored(mini_repo, monkeypatch):
    readme = mini_repo / "README.md"
    readme.write_text("# hi\n", encoding="utf-8")
    assert run_hook(monkeypatch, mini_repo, payload(readme)) == (0, "")


@pytest.mark.parametrize("stdin", ["", "not json", "[]", "{}", '{"tool_input": {}}'])
def test_malformed_or_empty_input_is_ignored(mini_repo, monkeypatch, stdin):
    assert run_hook(monkeypatch, mini_repo, stdin) == (0, "")


def test_edited_target_walks_up_to_the_directory_holding_skill_md(mini_repo, monkeypatch):
    monkeypatch.setattr(hook, "ROOT", mini_repo)
    deep = mini_repo / "plugins" / "engineering" / "skills" / "alpha" / "scripts" / "x.sh"
    assert hook.edited_target(payload(deep)) == (
        "plugins/engineering/skills/alpha",
        "plugins/engineering/skills/alpha/",
    )
    assert hook.edited_target(payload(mini_repo / "AGENTS.md")) is None


# The validator covers subagents, commands and rules too, and the hook said nothing
# about any of them: `edited_skill` walked up looking for a `SKILL.md` and gave up.
# Editing a subagent meant finding out in CI instead, which is the delay the hook
# exists to remove.


@pytest.mark.parametrize(
    "relative",
    [
        "plugins/engineering/agents/reader.md",
        ".claude/agents/reviewer.md",
        "plugins/engineering/commands/ship.md",
        ".claude/commands/ship.md",
        ".claude/commands/nested/deeper.md",
        ".claude/rules/skills.md",
    ],
)
def test_a_subagent_command_or_rule_owns_only_its_own_findings(mini_repo, monkeypatch, relative):
    monkeypatch.setattr(hook, "ROOT", mini_repo)
    target = hook.edited_target(payload(mini_repo / relative))
    assert target == (relative, f"{relative}:"), relative


@pytest.mark.parametrize(
    "relative",
    [
        "plugins/engineering/skills/alpha/references/depth.md",  # a skill, matched by directory
        "agents/stray.md",  # a top-level agents/ the validator reports as unowned
        "docs/writing-skills.md",
        ".claude/settings.json",
        ".claude/rules/notes.txt",  # not Markdown, so not a rule
    ],
)
def test_paths_that_are_not_a_single_file_target(mini_repo, monkeypatch, relative):
    monkeypatch.setattr(hook, "ROOT", mini_repo)
    assert not hook._is_file_target(Path(relative)), relative


def test_a_broken_subagent_is_reported_against_its_own_file(mini_repo, monkeypatch):
    agents = mini_repo / "plugins" / "engineering" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    broken = agents / "reader.md"
    # `name` disagreeing with the filename is the silent failure check_agent exists for:
    # delegation simply never happens and nothing anywhere says so.
    broken.write_text(
        "---\nname: not-reader\ndescription: Read a thing and report what it says.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    # Break a sibling too. The `:` terminator is the whole point of the change, and a
    # prefix match on the directory would pass an assertion that only looks for the
    # edited file's own path.
    (agents / "writer.md").write_text(
        "---\nname: wrong-again\ndescription: Write a thing and say what it did.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    code, err = run_hook(monkeypatch, mini_repo, payload(broken))
    assert code == 2
    assert "plugins/engineering/agents/reader.md" in err
    assert "writer" not in err


# `_check_eval_file` reports content errors — a thin set, an unbalanced one, a malformed
# entry — against the eval JSON's own path, `agents/evals/<name>.json`, not against the
# agent's `.md`. Discovered by breaking one in a scratch copy of this repository and
# running `python -m skillcheck . --skip-marketplace`: the finding read
# `plugins/gamedev/agents/evals/frame-capture-reader.json:1 [thin-eval-set] ...`, never
# the agent file. The hook has to key on that path directly.


def test_a_broken_agent_eval_set_is_reported_against_its_own_file(mini_repo, monkeypatch):
    reader_evals = mini_repo / "plugins" / "engineering" / "agents" / "evals" / "reader.json"
    reader_evals.write_text(json.dumps([{"query": "q", "should_trigger": True}]), encoding="utf-8")

    # Break a sibling's eval set too, the same shape as the reader.md/writer.md test
    # above: the `:` terminator is the whole point, and a prefix match on the shared
    # `agents/evals/` directory would pass an assertion that only looks for the edited
    # file's own path.
    write_agent(mini_repo, "engineering", "writer", evals=eval_set("writer", expected="reader"))
    writer_evals = mini_repo / "plugins" / "engineering" / "agents" / "evals" / "writer.json"
    writer_evals.write_text(json.dumps([{"query": "q", "should_trigger": True}]), encoding="utf-8")

    code, err = run_hook(monkeypatch, mini_repo, payload(reader_evals))
    assert code == 2
    assert "plugins/engineering/agents/evals/reader.json" in err
    assert "thin-eval-set" in err
    assert "writer" not in err


@pytest.mark.parametrize(
    "relative",
    [
        "plugins/engineering/agents/evals/reader.json",
        ".claude/agents/evals/reviewer.json",
    ],
)
def test_an_agent_eval_set_owns_only_its_own_findings(mini_repo, monkeypatch, relative):
    monkeypatch.setattr(hook, "ROOT", mini_repo)
    target = hook.edited_target(payload(mini_repo / relative))
    assert target == (relative, f"{relative}:"), relative


@pytest.mark.parametrize(
    "relative",
    [
        "plugins/engineering/skills/alpha/evals/trigger-eval.json",  # a skill's own set
        "plugins/engineering/agents/reader.md",  # the agent itself, not its eval set
        "plugins/engineering/agents/evals/reader.md",  # right directory, wrong suffix
        "plugins/engineering/agents/reader.json",  # right suffix, not inside evals/
        "agents/evals/stray.json",  # no plugins/ or .claude/ prefix
    ],
)
def test_paths_that_are_not_an_agent_eval_set(relative):
    assert not hook._is_agent_eval(Path(relative)), relative
