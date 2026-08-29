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
