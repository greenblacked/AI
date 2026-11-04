"""The plugin shape: an allowlisted root, a validated project kit, a completeness notice.

A plugin root holds `.claude-plugin`, `skills`, `agents` and `commands` and nothing else,
because Claude Code keeps adding component types it loads on enabling a plugin. Hooks reach
an installer only as opt-in templates under a skill's `assets/hooks/`, so the validator
refuses every other plugin-root entry, validates the
kit files themselves, and reports a plugin that lacks the shape as a notice that strict
mode does not fail until `PLUGIN_SHAPE_ENFORCED` is flipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillcheck import rules
from skillcheck.cli import main
from skillcheck.rules import ERROR, NOTICE, WARNING, check_kit, check_plugin_shape
from tests.test_rules import GOOD_DESCRIPTION, write_skill

ROOT = Path(__file__).resolve().parent.parent

HOOK_CMD = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard.sh'
GOOD_HOOK = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 10}]}
        ]
    }
}
GOOD_SCRIPT = "#!/usr/bin/env bash\nset -Eeuo pipefail\nexit 0\n"
GOOD_RULE = '---\npaths:\n  - "**/*.tf"\n---\n\n# Terraform\n\nKeep plans saved.\n'


def codes(findings, level=None):
    return [f.code for f in findings if level is None or f.level == level]


def make_plugin(tmp_path, name="engineering"):
    plugin = tmp_path / "plugins" / name
    (plugin / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    return plugin


def write_kit(assets: Path, *, rule=GOOD_RULE, hook=GOOD_HOOK, script=GOOD_SCRIPT, template=True):
    (assets / "rules").mkdir(parents=True, exist_ok=True)
    (assets / "hooks").mkdir(parents=True, exist_ok=True)
    (assets / "templates").mkdir(parents=True, exist_ok=True)
    if rule is not None:
        (assets / "rules" / "r.md").write_text(rule, encoding="utf-8")
    if hook is not None:
        text = hook if isinstance(hook, str) else json.dumps(hook)
        (assets / "hooks" / "guard.json").write_text(text, encoding="utf-8")
    if script is not None:
        (assets / "hooks" / "guard.sh").write_text(script, encoding="utf-8")
    if template:
        (assets / "templates" / "t.md").write_text("# Template\n", encoding="utf-8")


def write_clean_skills(root):
    """Two skills that route to each other and validate clean, so only the shape is tested."""
    other = GOOD_DESCRIPTION.replace(
        "Use this skill whenever the user asks for that thing",
        "Use this skill whenever the user wants the other, unrelated job done and",
    )
    for name, owner, description in (
        ("demo", "demo-two", GOOD_DESCRIPTION),
        ("demo-two", "demo", other),
    ):
        directory = write_skill(root, name, description=description, evals=False)
        (directory / "evals").mkdir()
        cases = [{"query": f"{name} positive {i}", "should_trigger": True} for i in range(10)]
        cases += [{"query": "negative 0", "should_trigger": False, "expected": owner}]
        cases += [{"query": f"negative {i}", "should_trigger": False} for i in range(1, 10)]
        (directory / "evals" / "trigger-eval.json").write_text(json.dumps(cases), encoding="utf-8")


def write_agent(plugin: Path):
    (plugin / "agents").mkdir(exist_ok=True)
    (plugin / "agents" / "reader.md").write_text(
        "---\nname: reader\ndescription: Reads.\ntools: Read\n---\n\nBody.\n", encoding="utf-8"
    )


# plugin-root-entry


@pytest.mark.parametrize(
    "rel",
    [
        "hooks/hooks.json",
        "hooks.json",
        ".mcp.json",
        ".lsp.json",
        "monitors/m.json",
        "bin/tool",
        "settings.json",
        "output-styles/s.md",
        # Component types Claude Code gained after the denylist was written, and files
        # that are merely not part of the shape.
        "workflows/w.yml",
        "themes/t.json",
        "README.md",
        "LICENSE",
        "scripts/run.sh",
    ],
)
def test_a_plugin_root_entry_outside_the_allowlist_is_an_error(tmp_path, rel):
    plugin = make_plugin(tmp_path)
    target = plugin / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "plugin-root-entry"]
    assert len(found) == 1 and found[0].level == ERROR
    assert rel.split("/")[0] in str(found[0].path)
    assert "assets/hooks" in found[0].message


@pytest.mark.parametrize(
    "rel",
    [
        "Hooks/hooks.json",
        ".MCP.json",
        "Settings.json",
        "BIN/tool",
        "Agents/reader.md",
        "Commands/run.md",
        "Skills/x/SKILL.md",
        ".Claude-Plugin/plugin.json",
        "Workflows/w.yml",
        "Themes/t.json",
    ],
)
def test_a_plugin_root_entry_is_compared_case_sensitively(tmp_path, rel):
    plugin = make_plugin(tmp_path)
    target = plugin / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "plugin-root-entry"]
    assert len(found) == 1 and found[0].level == ERROR
    assert rel.split("/")[0] in str(found[0].path)


def test_every_allowed_plugin_root_entry_is_accepted(tmp_path):
    plugin = make_plugin(tmp_path)
    for name in ("skills", "agents", "commands"):
        (plugin / name).mkdir()
    assert "plugin-root-entry" not in codes(check_plugin_shape(plugin, tmp_path))
    assert rules.PLUGIN_ROOT_ENTRIES == (".claude-plugin", "skills", "agents", "commands")


def test_the_cli_fails_on_a_plugin_root_hooks_folder(tmp_path, capsys):
    write_skill(tmp_path, "demo")
    plugin = make_plugin(tmp_path)
    (plugin / "hooks").mkdir()
    (plugin / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
    assert main([str(tmp_path), "--skip-marketplace"]) == 1
    assert "plugin-root-entry" in capsys.readouterr().out


# kit-rule


def test_a_good_kit_has_no_findings(tmp_path):
    write_kit(tmp_path / "assets")
    assert check_kit(tmp_path / "assets", tmp_path) == []


def test_a_kit_rule_glob_need_not_match_this_repository(tmp_path):
    # The glob scopes the installer's project, not this one, so dangling-glob is wrong here.
    write_kit(tmp_path / "assets")
    assert check_kit(tmp_path / "assets", tmp_path) == []


@pytest.mark.parametrize(
    "rule",
    [
        "# No frontmatter\n\nBody.\n",
        "---\npaths:\n---\n\nBody.\n",
        "---\nname: x\n---\n\nBody.\n",
        '---\npaths:\n  - "**/*.tf"\n',
        '---\npaths:\n  - "**/*.tf"\n---\n',
    ],
)
def test_a_kit_rule_without_usable_paths_is_an_error(tmp_path, rule):
    write_kit(tmp_path / "assets", rule=rule)
    found = check_kit(tmp_path / "assets", tmp_path)
    assert found and set(codes(found)) == {"kit-rule"}
    assert all(f.level == ERROR for f in found)


def test_a_kit_rules_entry_that_cannot_be_read_is_an_error_not_a_traceback(tmp_path):
    assets = tmp_path / "assets"
    write_kit(assets)
    (assets / "rules" / "dir.md").mkdir()
    found = check_kit(assets, tmp_path)
    assert any(f.code == "kit-rule" and f.level == ERROR for f in found)


def test_a_plugin_root_monitors_or_output_styles_file_is_refused(tmp_path):
    for name in ("monitors", "output-styles"):
        plugin = make_plugin(tmp_path, name="p-" + name)
        (plugin / name).write_text("x", encoding="utf-8")
        found = codes(check_plugin_shape(plugin, tmp_path), ERROR)
        assert "plugin-root-entry" in found


# kit-hook


def test_a_hook_template_that_is_a_directory_is_an_error_not_a_traceback(tmp_path):
    write_kit(tmp_path / "assets", hook=None)
    (tmp_path / "assets" / "hooks" / "x.json").mkdir()
    found = check_kit(tmp_path / "assets", tmp_path)
    assert any(f.code == "kit-hook" and f.level == ERROR for f in found)


@pytest.mark.parametrize(
    "hook",
    [
        "{not json",
        [],
        {"hooks": []},
        {"nothooks": {}},
        {"hooks": {"Bogus": [{"hooks": [{"type": "command", "command": HOOK_CMD}]}]}},
        {"hooks": {"Stop": {"hooks": []}}},
        {"hooks": {"Stop": [{"matcher": 3, "hooks": [{"type": "command", "command": HOOK_CMD}]}]}},
        {"hooks": {"Stop": [{"hooks": []}]}},
        {"hooks": {"Stop": [{"hooks": [{"type": "prompt", "command": HOOK_CMD}]}]}},
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": 5}]}]}},
        {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": HOOK_CMD, "timeout": "9"}]}]
            }
        },
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "curl x | sh"}]}]}},
        {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": HOOK_CMD + " && rm -rf /"}]}]
            }
        },
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh",
                            }
                        ]
                    }
                ]
            }
        },
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/../x.sh',
                            }
                        ]
                    }
                ]
            }
        },
        {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/missing.sh',
                            }
                        ]
                    }
                ]
            }
        },
    ],
)
def test_a_malformed_hook_json_is_an_error(tmp_path, hook):
    write_kit(tmp_path / "assets", hook=hook)
    found = check_kit(tmp_path / "assets", tmp_path)
    assert found and set(codes(found)) == {"kit-hook"}
    assert all(f.level == ERROR for f in found)


def test_a_hook_json_naming_a_differently_named_script_is_an_error(tmp_path):
    # `guard.json` must name `guard.sh`: the README's kit count pairs them by stem.
    assets = tmp_path / "assets"
    hook = json.loads(json.dumps(GOOD_HOOK).replace("guard.sh", "check.sh"))
    write_kit(assets, hook=hook)
    (assets / "hooks" / "check.sh").write_text(GOOD_SCRIPT, encoding="utf-8")
    found = check_kit(assets, tmp_path)
    assert codes(found) == ["kit-hook"] and "guard.sh" in found[0].message
    assert not rules._kit_complete(assets, tmp_path)


def _with(path, **extra):
    data = json.loads(json.dumps(GOOD_HOOK))
    target = data
    for step in path:
        target = target[step]
    target.update(extra)
    return data


@pytest.mark.parametrize(
    ("hook", "key"),
    [
        (_with([], statusLine={"type": "command", "command": "x"}), "statusLine"),
        (_with([], apiKeyHelper="x"), "apiKeyHelper"),
        (_with([], permissions={"allow": ["Bash"]}), "permissions"),
        (_with(["hooks", "PreToolUse", 0], extra=1), "extra"),
        (_with(["hooks", "PreToolUse", 0, "hooks", 0], env={"A": "b"}), "env"),
    ],
)
def test_an_unknown_hook_key_is_an_error_naming_it(tmp_path, hook, key):
    write_kit(tmp_path / "assets", hook=hook)
    found = check_kit(tmp_path / "assets", tmp_path)
    assert found and set(codes(found)) == {"kit-hook"}
    assert any(key in f.message for f in found)


@pytest.mark.parametrize("timeout", [0, -5, True])
def test_a_non_positive_timeout_is_an_error(tmp_path, timeout):
    hook = _with(["hooks", "PreToolUse", 0, "hooks", 0], timeout=timeout)
    write_kit(tmp_path / "assets", hook=hook)
    assert set(codes(check_kit(tmp_path / "assets", tmp_path))) == {"kit-hook"}


@pytest.mark.parametrize(
    "event",
    [
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "Stop",
        "SubagentStop",
        "SessionStart",
        "SessionEnd",
        "Notification",
        "PreCompact",
    ],
)
def test_every_documented_event_is_accepted(tmp_path, event):
    hook = {"hooks": {event: [{"hooks": [{"type": "command", "command": HOOK_CMD}]}]}}
    write_kit(tmp_path / "assets", hook=hook)
    assert check_kit(tmp_path / "assets", tmp_path) == []


@pytest.mark.parametrize(
    "script",
    [
        "set -Eeuo pipefail\nexit 0\n",
        "#!/bin/bash\nset -Eeuo pipefail\n",
        "#!/usr/bin/env bash\nset -e\n",
    ],
)
def test_a_hook_script_needs_the_shebang_and_strict_mode(tmp_path, script):
    write_kit(tmp_path / "assets", script=script)
    found = check_kit(tmp_path / "assets", tmp_path)
    assert codes(found) == ["kit-hook"] and found[0].level == ERROR


def test_a_hook_json_whose_script_is_missing_is_an_error(tmp_path):
    write_kit(tmp_path / "assets", script=None)
    found = check_kit(tmp_path / "assets", tmp_path)
    assert codes(found) == ["kit-hook"] and "guard.sh" in found[0].message


# plugin-incomplete


def complete_plugin(tmp_path):
    plugin = make_plugin(tmp_path)
    write_agent(plugin)
    write_skill(tmp_path, "demo")
    write_kit(tmp_path / "plugins" / "engineering" / "skills" / "demo" / "assets")
    return plugin


def test_a_complete_plugin_has_no_shape_finding(tmp_path):
    plugin = complete_plugin(tmp_path)
    assert check_plugin_shape(plugin, tmp_path) == []


def test_a_plugin_without_a_subagent_or_kit_gets_a_notice_by_default(tmp_path):
    write_skill(tmp_path, "demo")
    plugin = make_plugin(tmp_path)
    found = check_plugin_shape(plugin, tmp_path)
    assert codes(found) == ["plugin-incomplete"]
    assert found[0].level == NOTICE and not found[0].failed
    assert "subagent" in found[0].message and "kit" in found[0].message


@pytest.mark.parametrize("missing", ["rule", "hook", "script", "template"])
def test_a_kit_missing_any_part_is_incomplete(tmp_path, missing):
    plugin = make_plugin(tmp_path)
    write_agent(plugin)
    write_skill(tmp_path, "demo")
    assets = plugin / "skills" / "demo" / "assets"
    write_kit(
        assets,
        rule=None if missing == "rule" else GOOD_RULE,
        hook=None if missing == "hook" else GOOD_HOOK,
        script=None if missing == "script" else GOOD_SCRIPT,
        template=missing != "template",
    )
    # A hook json with no script is also a kit-hook error; the notice is the point here.
    assert "plugin-incomplete" in codes(check_plugin_shape(plugin, tmp_path))


def test_a_subagent_alone_does_not_complete_the_shape(tmp_path):
    plugin = make_plugin(tmp_path)
    write_agent(plugin)
    write_skill(tmp_path, "demo")
    found = check_plugin_shape(plugin, tmp_path)
    assert "plugin-incomplete" in codes(found)
    assert "subagent" not in found[0].message


def test_enforcing_the_shape_makes_the_finding_a_warning(tmp_path, monkeypatch):
    write_skill(tmp_path, "demo")
    plugin = make_plugin(tmp_path)
    monkeypatch.setattr(rules, "PLUGIN_SHAPE_ENFORCED", True)
    found = check_plugin_shape(plugin, tmp_path)
    assert codes(found) == ["plugin-incomplete"] and found[0].level == WARNING


def test_the_shape_is_not_enforced_yet():
    assert rules.PLUGIN_SHAPE_ENFORCED is False


def test_strict_mode_passes_on_a_notice_and_fails_once_enforced(tmp_path, monkeypatch, capsys):
    write_clean_skills(tmp_path)
    make_plugin(tmp_path)
    assert main([str(tmp_path), "--skip-marketplace", "--strict"]) == 0
    assert "notice" in capsys.readouterr().out
    monkeypatch.setattr(rules, "PLUGIN_SHAPE_ENFORCED", True)
    assert main([str(tmp_path), "--skip-marketplace", "--strict"]) == 1


def test_a_notice_is_annotated_not_counted_as_a_warning(tmp_path, capsys):
    write_clean_skills(tmp_path)
    make_plugin(tmp_path)
    main([str(tmp_path), "--skip-marketplace", "--github"])
    out = capsys.readouterr().out
    assert "::notice " in out and "0 warning(s)" in out and "1 notice(s)" in out


# template/


def test_the_template_kit_passes_every_kit_check():
    assert check_kit(ROOT / "template" / "kit", ROOT) == []


def test_the_template_is_not_discovered_as_a_skill():
    assert not any("template" in p.parts for p in rules.find_skills(ROOT))


def test_the_template_agent_validates_apart_from_its_placeholder_name():
    # The file is called agent.md so it can sit in template/; the copy is renamed.
    found = rules.check_agent(ROOT / "template" / "agent.md", ROOT)
    assert codes(found) == ["name-mismatch"]


EXAMPLE_HOOK = ROOT / "template" / "kit" / "hooks" / "example.sh"
NOT_AN_OBJECT = [
    "[]",
    "3",
    '"text"',
    "null",
    "{not json",
    "",
    '{"tool_input": null}',
    '{"tool_input": 3}',
    '{"tool_input": []}',
    '{"tool_input": {"command": null}}',
    '{"tool_input": {"command": 3}}',
    '{"tool_input": {}}',
]
BLOCKED = '{"tool_input": {"command": "run example-forbidden-command now"}}'


def run_example_hook(tmp_path, stdin, tools):
    """Run the template hook with only `tools` on PATH, so which parser it picks is known."""
    import os
    import shutil
    import subprocess

    directory = tmp_path / "bin"
    directory.mkdir()
    for tool in tools:
        (directory / tool).symlink_to(shutil.which(tool))
    return subprocess.run(  # noqa: S603
        [shutil.which("bash"), str(EXAMPLE_HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env={"PATH": str(directory), "HOME": os.environ.get("HOME", "/")},
        check=False,
    )


def _has(tool):
    import shutil

    return shutil.which(tool) is not None


# The two branches: jq on PATH (python3 is also there, but jq is tried first), and jq stripped.
BRANCHES = [
    pytest.param(
        ("bash", "cat", "jq"),
        marks=pytest.mark.skipif(not _has("jq"), reason="the jq branch needs jq"),
        id="jq",
    ),
    pytest.param(("bash", "cat", "python3"), id="python"),
]


@pytest.mark.parametrize("tools", BRANCHES)
@pytest.mark.parametrize("stdin", NOT_AN_OBJECT)
def test_the_example_hook_allows_input_it_cannot_read_a_command_from(tmp_path, stdin, tools):
    result = run_example_hook(tmp_path, stdin, tools)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("tools", BRANCHES)
def test_the_example_hook_still_blocks_its_one_command_on_both_branches(tmp_path, tools):
    result = run_example_hook(tmp_path, BLOCKED, tools)
    assert result.returncode == 2
    assert "blocked" in result.stderr


# SKILL.md case, and entries git ignores


@pytest.mark.parametrize("name", ["skill.md", "Skill.md", "SKILL.MD", "skill.MD"])
def test_a_differently_cased_skill_file_is_an_error(tmp_path, name):
    plugin = make_plugin(tmp_path)
    skill = plugin / "skills" / "alpha"
    skill.mkdir(parents=True)
    (skill / name).write_text("---\nname: alpha\n---\n", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "skill-file-case"]
    assert len(found) == 1 and found[0].level == ERROR
    assert name in str(found[0].path)


def test_an_exact_skill_file_is_not_a_case_error(tmp_path):
    plugin = make_plugin(tmp_path)
    skill = plugin / "skills" / "alpha"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
    assert "skill-file-case" not in codes(check_plugin_shape(plugin, tmp_path))


def _init_git(tmp_path, ignore):
    import subprocess

    (tmp_path / ".gitignore").write_text(ignore, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607


@pytest.mark.parametrize("git_checkout", [True, False], ids=["git", "no-git"])
def test_an_ignored_plugin_root_file_is_accepted_and_an_unignored_one_refused(
    tmp_path, git_checkout
):
    if git_checkout:
        _init_git(tmp_path, ".DS_Store\n")
    else:
        (tmp_path / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
    plugin = make_plugin(tmp_path)
    (plugin / ".DS_Store").write_text("x", encoding="utf-8")
    (plugin / "notes.txt").write_text("x", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "plugin-root-entry"]
    assert [f.path.name for f in found] == ["notes.txt"]


@pytest.mark.parametrize(
    "command",
    [
        '["example-forbidden-command"]',
        '{"a": "example-forbidden-command"}',
        "3",
        "true",
    ],
)
def test_the_two_example_hook_branches_agree_on_a_non_string_command(tmp_path, command):
    # jq -r prints a non-string value as JSON, so a list holding the forbidden word is blocked;
    # the python branch has to print it too or the two branches give different verdicts.
    if not _has("jq"):
        pytest.skip("the comparison needs jq")
    stdin = f'{{"tool_input": {{"command": {command}}}}}'
    results = []
    for index, tools in enumerate((("bash", "cat", "jq"), ("bash", "cat", "python3"))):
        directory = tmp_path / str(index)
        directory.mkdir()
        results.append(run_example_hook(directory, stdin, tools))
    assert results[0].returncode == results[1].returncode
    assert results[0].stderr == results[1].stderr
    assert results[0].returncode == (2 if "forbidden" in command else 0)
