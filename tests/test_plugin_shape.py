"""The plugin shape: no auto-run components, a validated project kit, a completeness notice.

Hooks reach an installer only as opt-in templates under a skill's `assets/hooks/`, so the
validator refuses the plugin-root places Claude Code would load them from, validates the
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


# plugin-auto-component


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
    ],
)
def test_a_plugin_root_auto_component_is_an_error(tmp_path, rel):
    plugin = make_plugin(tmp_path)
    target = plugin / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "plugin-auto-component"]
    assert len(found) == 1 and found[0].level == ERROR
    assert rel.split("/")[0] in str(found[0].path)
    assert "assets/hooks" in found[0].message


@pytest.mark.parametrize("rel", ["Hooks/hooks.json", ".MCP.json", "Settings.json", "BIN/tool"])
def test_an_auto_component_is_refused_whatever_its_case(tmp_path, rel):
    plugin = make_plugin(tmp_path)
    target = plugin / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")
    found = [f for f in check_plugin_shape(plugin, tmp_path) if f.code == "plugin-auto-component"]
    assert len(found) == 1 and found[0].level == ERROR


def test_a_plugin_without_auto_components_has_no_such_finding(tmp_path):
    plugin = make_plugin(tmp_path)
    assert "plugin-auto-component" not in codes(check_plugin_shape(plugin, tmp_path))


def test_the_cli_fails_on_a_plugin_root_hooks_folder(tmp_path, capsys):
    write_skill(tmp_path, "demo")
    plugin = make_plugin(tmp_path)
    (plugin / "hooks").mkdir()
    (plugin / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
    assert main([str(tmp_path), "--skip-marketplace"]) == 1
    assert "plugin-auto-component" in capsys.readouterr().out


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


# kit-hook


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
