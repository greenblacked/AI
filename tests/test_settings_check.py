"""The hook registration, which nothing else in the repository reads.

Every case here is a way of disabling the `PostToolUse` hook without producing an error.
The runtime does not complain about a `command` that names nothing; it runs the hook
never and says so nowhere. That is the same shape as a README that has stopped matching
the tree — a claim the repository makes about itself that only a person reading would
catch — which is why this check sits in `scripts/` beside that one rather than in the
validator.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from tests.conftest import load_script

settings = load_script("check_settings.py")


def write_settings(root: Path, data) -> Path:
    path = root / "scripts" / "hooks" / "skill_hook.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    target = root / ".claude" / "settings.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return target


def registration(command: str = "$CLAUDE_PROJECT_DIR/scripts/hooks/skill_hook.py", **overrides):
    group = {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": command}]}
    group.update(overrides)
    return {"hooks": {"PostToolUse": [group]}}


def test_a_registration_pointing_at_a_real_script_passes(mini_repo, capsys):
    write_settings(mini_repo, registration())
    assert settings.check(mini_repo) == 0
    assert "1 hook command(s) across 1 event(s)" in capsys.readouterr().out


def test_no_settings_file_is_a_repository_with_no_hooks(mini_repo, capsys):
    # `mini_repo` ships none, which is the case a tree without hooks has to survive:
    # failing here would make the check impossible to adopt anywhere else.
    assert not (mini_repo / ".claude" / "settings.json").exists()
    assert settings.check(mini_repo) == 0
    assert "no hooks to check" in capsys.readouterr().out


def test_a_file_that_does_not_parse_fails(mini_repo, capsys):
    write_settings(mini_repo, "{not json")
    assert settings.check(mini_repo) == 1
    assert "does not parse as JSON" in capsys.readouterr().out


def test_a_stale_path_fails(mini_repo, capsys):
    # The failure this exists for: the script moved and the registration did not. The
    # session still starts, the hook simply never runs.
    write_settings(mini_repo, registration("$CLAUDE_PROJECT_DIR/.claude/hooks/skill_hook.py"))
    assert settings.check(mini_repo) == 1
    assert "which does not exist" in capsys.readouterr().out


def test_a_script_without_the_executable_bit_fails(mini_repo, capsys):
    write_settings(mini_repo, registration())
    hook = mini_repo / "scripts" / "hooks" / "skill_hook.py"
    hook.chmod(hook.stat().st_mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    assert settings.check(mini_repo) == 1
    assert "which is not executable" in capsys.readouterr().out


def test_a_missing_matcher_fails(mini_repo, capsys):
    data = registration()
    del data["hooks"]["PostToolUse"][0]["matcher"]
    write_settings(mini_repo, data)
    assert settings.check(mini_repo) == 1
    assert "has no matcher" in capsys.readouterr().out


def test_an_empty_matcher_fails(mini_repo, capsys):
    write_settings(mini_repo, registration(matcher="   "))
    assert settings.check(mini_repo) == 1
    assert "has an empty matcher" in capsys.readouterr().out


def test_what_the_matcher_means_is_not_judged(mini_repo):
    # How the runtime anchors the pattern is not confirmed, so the check reads it as
    # text. A gate that guessed would fail a correct registration.
    write_settings(mini_repo, registration(matcher="Write|Edit|MultiEdit|NotebookEdit"))
    assert settings.check(mini_repo) == 0
    write_settings(mini_repo, registration(matcher="*"))
    assert settings.check(mini_repo) == 0


def test_a_command_with_arguments_resolves_to_its_first_word(mini_repo, capsys):
    write_settings(
        mini_repo, registration("$CLAUDE_PROJECT_DIR/scripts/hooks/skill_hook.py --strict")
    )
    assert settings.check(mini_repo) == 0
    assert "1 hook command(s)" in capsys.readouterr().out


def test_a_relative_path_resolves_against_the_repository(mini_repo):
    write_settings(mini_repo, registration("./scripts/hooks/skill_hook.py"))
    assert settings.check(mini_repo) == 0


def test_a_path_outside_the_repository_fails(mini_repo, capsys):
    # It may well exist on the machine that wrote it. It will not exist in the clone
    # of anyone who checks the file out, which is the only tree that matters.
    write_settings(mini_repo, registration("$CLAUDE_PROJECT_DIR/../elsewhere/hook.py"))
    assert settings.check(mini_repo) == 1
    assert "outside the repository" in capsys.readouterr().out


def test_a_command_naming_no_file_fails(mini_repo, capsys):
    # Skipping a bare name would leave the hole exactly where a typo lands: a mistyped
    # path with no separator left in it would read as a system binary and pass.
    write_settings(mini_repo, registration("jq -r .tool_input"))
    assert settings.check(mini_repo) == 1
    assert "names no file" in capsys.readouterr().out


def test_a_command_that_is_not_a_string_fails(mini_repo, capsys):
    write_settings(mini_repo, {"hooks": {"PostToolUse": [{"matcher": "Write", "hooks": [{}]}]}})
    assert settings.check(mini_repo) == 1
    assert "has no command" in capsys.readouterr().out


def test_an_unparseable_command_line_fails(mini_repo, capsys):
    write_settings(mini_repo, registration('"unterminated quote'))
    assert settings.check(mini_repo) == 1
    assert "names no file" in capsys.readouterr().out


def test_a_matcher_group_registering_no_hooks_fails(mini_repo, capsys):
    write_settings(mini_repo, registration(hooks=[]))
    assert settings.check(mini_repo) == 1
    assert "registers no hooks" in capsys.readouterr().out


def test_a_settings_file_with_no_hooks_key_passes(mini_repo, capsys):
    write_settings(mini_repo, {"permissions": {"allow": ["Read"]}})
    assert settings.check(mini_repo) == 0
    assert "0 hook command(s)" in capsys.readouterr().out


def test_malformed_shapes_fail_rather_than_crash(mini_repo, capsys):
    # Each of these is JSON the runtime would reject or ignore. A traceback here would
    # read as a broken gate rather than a broken file, and gates that crash get removed.
    for data, expected in (
        ([], "and the runtime expects an object"),
        ({"hooks": []}, "`hooks` is not an object"),
        ({"hooks": {"PostToolUse": {}}}, "is not a list of matcher groups"),
        ({"hooks": {"PostToolUse": ["Write"]}}, "is not an object"),
        ({"hooks": {"PostToolUse": [{"matcher": "W", "hooks": ["x"]}]}}, "is not an object"),
    ):
        write_settings(mini_repo, data)
        assert settings.check(mini_repo) == 1, data
        assert expected in capsys.readouterr().out, data


def test_an_empty_command_line_names_nothing(mini_repo):
    # The guard behind `check`'s own emptiness test, kept so a command that splits to
    # nothing raises no IndexError from inside the gate.
    assert settings.executable_path("", mini_repo) is None
    assert settings.executable_path('""', mini_repo) is None


def test_main_accepts_a_root(mini_repo):
    write_settings(mini_repo, registration())
    assert settings.main([str(mini_repo)]) == 0


def test_this_repository_is_wired_correctly():
    # The repository's own registration, checked the way CI checks it. Without this the
    # suite would only prove the checker works on fixtures.
    root = Path(__file__).resolve().parent.parent
    assert settings.check(root) == 0
    hook = root / "scripts" / "hooks" / "skill_hook.py"
    assert os.access(hook, os.X_OK)
