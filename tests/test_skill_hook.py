"""The PostToolUse hook is the fastest feedback loop in the repository, and a hook that
is wrong is worse than none: it either nags on every edit or stays silent when it
should not. Each path it can take is pinned here.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from tests.conftest import load_script, write_skill

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


def test_edited_skill_walks_up_to_the_directory_holding_skill_md(mini_repo, monkeypatch):
    monkeypatch.setattr(hook, "ROOT", mini_repo)
    deep = mini_repo / "plugins" / "engineering" / "skills" / "alpha" / "scripts" / "x.sh"
    assert hook.edited_skill(payload(deep)) == Path("plugins/engineering/skills/alpha")
    assert hook.edited_skill(payload(mini_repo / "AGENTS.md")) is None
