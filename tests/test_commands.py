"""Slash commands get the same treatment as skills and subagents.

Upstream accepts a command file with a misspelled frontmatter key: it installs, and
simply loses whatever the key was for. That is the same silent class of defect as a
dangling reference, so it is checked here rather than discovered by someone wondering
why their argument hint never appears.
"""

from __future__ import annotations

import pytest

from skillcheck.rules import ERROR, WARNING, check_command, find_commands

GOOD = """---
description: Do one narrow thing with the argument it is given.
argument-hint: [path]
allowed-tools: Read, Grep
---

Read $1 and report what it contains.
"""


def write_command(root, name, text=GOOD):
    directory = root / "commands"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


def codes(findings, level=ERROR):
    return {f.code for f in findings if f.level == level}


def test_a_well_formed_command_produces_nothing(tmp_path):
    assert check_command(write_command(tmp_path, "demo"), tmp_path) == []


@pytest.mark.parametrize("key", ["model", "disable-model-invocation", "allowed-tools"])
def test_the_documented_keys_are_allowed(tmp_path, key):
    text = f"---\ndescription: A thing.\n{key}: value\n---\n\nBody.\n"
    assert check_command(write_command(tmp_path, "demo", text), tmp_path) == []


def test_an_unknown_key_is_an_error(tmp_path):
    text = "---\ndescription: A thing.\nname: demo\n---\n\nBody.\n"
    assert "unknown-key" in codes(check_command(write_command(tmp_path, "demo", text), tmp_path))


def test_a_missing_description_is_an_error(tmp_path):
    text = "---\nallowed-tools: Read\n---\n\nBody.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "missing-description" in codes(findings)


def test_angle_brackets_in_the_description_are_an_error(tmp_path):
    text = "---\ndescription: Do a thing to <target>.\n---\n\nBody.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "angle-brackets" in codes(findings)


def test_a_long_description_is_an_error(tmp_path):
    text = f"---\ndescription: {'x' * 1100}\n---\n\nBody.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "long-description" in codes(findings)


@pytest.mark.parametrize("name", ["Demo", "demo_command", "demo--command", "demo.command"])
def test_a_filename_that_is_not_a_slug_is_an_error(tmp_path, name):
    findings = check_command(write_command(tmp_path, name), tmp_path)
    assert "bad-command-name" in codes(findings)


def test_a_command_with_no_body_is_an_error(tmp_path):
    text = "---\ndescription: A thing.\n---\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "empty-command" in codes(findings)


def test_broken_frontmatter_is_reported_once(tmp_path):
    findings = check_command(write_command(tmp_path, "demo", "no frontmatter here\n"), tmp_path)
    assert codes(findings) == {"frontmatter"}


@pytest.mark.parametrize("token", ["$ARGUMENTS", "$1", "$9"])
def test_reading_an_argument_without_a_hint_warns(tmp_path, token):
    text = f"---\ndescription: A thing.\n---\n\nRun against {token}.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "no-argument-hint" in codes(findings, WARNING)


def test_a_declared_hint_clears_the_warning(tmp_path):
    text = "---\ndescription: A thing.\nargument-hint: [path]\n---\n\nRun against $1.\n"
    assert check_command(write_command(tmp_path, "demo", text), tmp_path) == []


def test_a_dollar_inside_a_fence_does_not_demand_a_hint(tmp_path):
    # A shell example is documentation, not an argument the command actually reads.
    text = "---\ndescription: A thing.\n---\n\n```bash\necho $1\n```\n"
    assert check_command(write_command(tmp_path, "demo", text), tmp_path) == []


def test_a_dangling_reference_is_an_error_and_names_the_command(tmp_path):
    text = "---\ndescription: A thing.\n---\n\nSee references/missing.md for detail.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "dangling-reference" in codes(findings)
    assert "demo.md points at" in findings[0].message


def test_a_reference_that_exists_is_accepted(tmp_path):
    path = write_command(
        tmp_path, "demo", "---\ndescription: A thing.\n---\n\nSee references/here.md.\n"
    )
    (path.parent / "references").mkdir()
    (path.parent / "references" / "here.md").write_text("depth\n", encoding="utf-8")
    assert check_command(path, tmp_path) == []


def test_shouting_in_the_body_warns(tmp_path):
    text = "---\ndescription: A thing.\n---\n\nYou must ALWAYS do the thing.\n"
    findings = check_command(write_command(tmp_path, "demo", text), tmp_path)
    assert "shouting" in codes(findings, WARNING)


def test_find_commands_skips_a_readme_and_recurses(tmp_path):
    write_command(tmp_path, "demo")
    (tmp_path / "commands" / "README.md").write_text("docs\n", encoding="utf-8")
    nested = tmp_path / "commands" / "group"
    nested.mkdir()
    (nested / "other.md").write_text(GOOD, encoding="utf-8")
    assert [p.name for p in find_commands(tmp_path / "commands")] == ["demo.md", "other.md"]


def test_find_commands_on_a_missing_directory_is_empty(tmp_path):
    assert find_commands(tmp_path / "nothing") == []
