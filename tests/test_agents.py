"""Subagent definitions get the same treatment as skills.

Nothing else in the pipeline reads `agents/*.md`, so a misspelled key or a name that
disagrees with the filename fails the same silent way a dangling skill reference does:
delegation never happens and no error is raised anywhere.
"""

from __future__ import annotations

import pytest

from skillcheck.rules import ERROR, check_agent, find_agents

GOOD = """---
name: demo-agent
description: Do one narrow thing and return a conclusion. Use when the caller wants that.
tools: Read, Grep
---

Body.
"""


def write_agent(root, name, text=GOOD):
    directory = root / "agents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


def codes(findings):
    return {f.code for f in findings if f.level == ERROR}


def test_a_well_formed_agent_produces_nothing(tmp_path):
    assert check_agent(write_agent(tmp_path, "demo-agent"), tmp_path) == []


def test_model_is_an_allowed_key(tmp_path):
    text = GOOD.replace("tools: Read, Grep", "tools: Read\nmodel: sonnet")
    assert check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (GOOD.replace("name: demo-agent", "name: other"), "name-mismatch"),
        (GOOD.replace("name: demo-agent", "name: Demo_Agent"), "bad-name"),
        (GOOD.replace("tools: Read, Grep", "allowed-tools: Read"), "unknown-key"),
        (GOOD.replace("tools: Read, Grep", "tools: Read,,Grep"), "bad-tools"),
        (GOOD.replace("tools: Read, Grep", "tools:  "), "bad-tools"),
        (GOOD.replace("description: ", "summary: "), "missing-description"),
        (GOOD.replace("Use when the caller wants that.", "Use for a and b."), None),
    ],
)
def test_agent_defects(tmp_path, text, expected):
    found = codes(check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path))
    if expected is None:
        assert found == set()
    else:
        assert expected in found


def test_angle_brackets_in_a_description_are_rejected(tmp_path):
    text = GOOD.replace("that.", "that, e.g. <html>.")
    assert "angle-brackets" in codes(
        check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path)
    )


def test_a_missing_frontmatter_block_is_reported_once(tmp_path):
    path = write_agent(tmp_path, "demo-agent", "# No frontmatter here\n")
    assert codes(check_agent(path, tmp_path)) == {"frontmatter"}


def test_find_agents_is_sorted_and_ignores_other_files(tmp_path):
    write_agent(tmp_path, "b-agent")
    write_agent(tmp_path, "a-agent")
    (tmp_path / "agents" / "notes.txt").write_text("ignored", encoding="utf-8")
    assert [p.stem for p in find_agents(tmp_path / "agents")] == ["a-agent", "b-agent"]


@pytest.mark.parametrize(
    "key",
    [
        "disallowedTools",
        "effort",
        "maxTurns",
        "skills",
        "memory",
        "background",
        "isolation",
        "omitClaudeMd",
    ],
)
def test_the_documented_plugin_agent_keys_are_allowed(tmp_path, key):
    text = GOOD.replace("tools: Read, Grep\n", f"tools: Read, Grep\n{key}: value\n")
    assert check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path) == []


@pytest.mark.parametrize("key", ["color", "initialPrompt"])
def test_keys_the_plugins_reference_does_not_list_are_refused(tmp_path, key):
    # Both were accepted here once, on the assumption that a subagent file's key set and
    # a plugin-shipped subagent's are the same. They are not: the plugins reference lists
    # twelve keys a plugin agent supports and neither of these is among them, so an author
    # following the validator could ship one and never learn that nothing read it.
    #
    # That absence is the whole reason, and it is worth being exact about what it is not.
    # A plugin agent *can* run as the main session agent — `claude --agent my-plugin:name`
    # is documented — so "it is never the main agent" would be a false argument for
    # refusing `initialPrompt`, and the next reader who discovers that would restore both
    # keys. The second assertion pins the other half: these are ordinary unknown keys, not
    # the security-reasoned refusal that `hooks`, `mcpServers` and `permissionMode` get,
    # because that message states a reason untrue of a display colour.
    text = GOOD.replace("tools: Read, Grep\n", f"tools: Read, Grep\n{key}: value\n")
    findings = check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path)
    assert codes(findings) == {"unknown-key"}
    assert "plugin-shipped" not in findings[0].message


@pytest.mark.parametrize("key", ["hooks", "mcpServers", "permissionMode"])
def test_keys_a_plugin_may_not_ship_are_refused_with_the_reason(tmp_path, key):
    # These work in a project-level agent and are refused in a plugin-shipped one, so
    # the message has to say why rather than "unexpected key".
    text = GOOD.replace("tools: Read, Grep\n", f"tools: Read, Grep\n{key}: value\n")
    findings = check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path)
    assert codes(findings) == {"unknown-key"}
    assert "plugin-shipped" in findings[0].message


def test_a_missing_name_is_an_error(tmp_path):
    text = GOOD.replace("name: demo-agent\n", "")
    assert "missing-name" in codes(check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path))


def test_a_description_over_the_cap_is_an_error(tmp_path):
    text = GOOD.replace("Do one narrow thing", "Do one narrow thing " + "x" * 1024)
    assert "long-description" in codes(
        check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path)
    )


def test_a_cede_clause_naming_a_subagent_that_does_not_exist_is_an_error(tmp_path):
    # A subagent's description routes exactly as a skill's does, and this is the case
    # that motivated the rule: deleting an agent left another one ceding to it.
    text = GOOD.replace(
        "wants that.", "wants that. Not for finding the sources, which is source-finder."
    )
    path = write_agent(tmp_path, "demo-agent", text)
    findings = check_agent(path, tmp_path, frozenset({"demo-agent"}))
    assert [f.code for f in findings] == ["dangling-cede"]
    assert "source-finder" in findings[0].message


def test_a_cede_clause_naming_a_subagent_that_exists_is_clean(tmp_path):
    text = GOOD.replace("wants that.", "wants that. Not for the wider sweep (deep-audit).")
    path = write_agent(tmp_path, "demo-agent", text)
    assert check_agent(path, tmp_path, frozenset({"demo-agent", "deep-audit"})) == []


def test_without_a_known_set_an_agent_cede_clause_is_not_checked(tmp_path):
    # The two-argument call is what every other caller here uses, and it stays silent
    # for the same reason `unknown-expected` does: nothing has told it what exists.
    text = GOOD.replace(
        "wants that.", "wants that. Not for finding the sources, which is source-finder."
    )
    assert check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path) == []


def test_a_hyphenated_aside_outside_an_agent_cede_clause_is_not_a_target(tmp_path):
    text = GOOD.replace(
        "wants that.", "wants that. It reports only (read-only) and changes nothing."
    )
    assert check_agent(write_agent(tmp_path, "demo-agent", text), tmp_path, frozenset()) == []
