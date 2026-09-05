"""Rule-level tests.

Each case builds a throwaway skill directory containing exactly one defect, so a
failure names the rule that broke rather than "something is wrong with validation".
"""

from __future__ import annotations

import json

import pytest

from skillcheck.rules import ERROR, WARNING, check_marketplace, check_skill, find_skills

GOOD_DESCRIPTION = (
    "Do a specific, useful thing end to end. Use this skill whenever the user asks "
    "for that thing, including casual phrasings."
)


def write_skill(
    root, name, *, description=GOOD_DESCRIPTION, front=None, body="# Demo\n", evals=True
):
    directory = root / "plugins" / "engineering" / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    if front is None:
        front = f"name: {name}\ndescription: {description}"
    (directory / "SKILL.md").write_text(f"---\n{front}\n---\n\n{body}", encoding="utf-8")
    if evals:
        # A fixture skill is otherwise incomplete, and every assertion of "produces
        # nothing" would trip over the missing-eval-set warning instead.
        (directory / "evals").mkdir(exist_ok=True)
        cases = [{"query": f"positive {i}", "should_trigger": True} for i in range(10)]
        cases += [{"query": f"negative {i}", "should_trigger": False} for i in range(10)]
        (directory / "evals" / "trigger-eval.json").write_text(json.dumps(cases), encoding="utf-8")
    return directory


def codes(findings, level=None):
    return {f.code for f in findings if level is None or f.level == level}


@pytest.mark.parametrize("name", ["claude-helper", "anthropic-tools", "my-claude-thing"])
def test_a_reserved_word_in_the_name_is_an_error(tmp_path, name):
    # The upload route rejects these, so without the check a skill named after the tool
    # it targets passes locally and fails at the boundary.
    directory = write_skill(tmp_path, name)
    assert "reserved-name" in codes(check_skill(directory, tmp_path))


def test_a_name_that_merely_resembles_a_reserved_word_is_fine(tmp_path):
    directory = write_skill(tmp_path, "clause-review")
    assert "reserved-name" not in codes(check_skill(directory, tmp_path))


def test_a_well_formed_skill_produces_nothing(tmp_path):
    directory = write_skill(tmp_path, "demo")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize(
    ("front", "expected"),
    [
        ("name: demo", "missing-description"),
        (f"description: {GOOD_DESCRIPTION}", "missing-name"),
        (f"name: \ndescription: {GOOD_DESCRIPTION}", "empty-name"),
        ("name: demo\ndescription: ''", "empty-description"),
        (f"name: Demo\ndescription: {GOOD_DESCRIPTION}", "bad-name"),
        (f"name: de--mo\ndescription: {GOOD_DESCRIPTION}", "bad-name"),
        (f"name: other\ndescription: {GOOD_DESCRIPTION}", "name-mismatch"),
        (f"name: demo\ndescription: {GOOD_DESCRIPTION} Use for <html>.", "angle-brackets"),
        (f"name: demo\ndescription: {GOOD_DESCRIPTION}\nallowed_tools: Read", "unknown-key"),
        (
            f"name: demo\ndescription: {GOOD_DESCRIPTION}\ncompatibility: {'x' * 501}",
            "long-compatibility",
        ),
    ],
)
def test_frontmatter_defects_are_errors(tmp_path, front, expected):
    directory = write_skill(tmp_path, "demo", front=front)
    assert expected in codes(check_skill(directory, tmp_path), ERROR)


def test_over_long_name_and_description_are_errors(tmp_path):
    long_name = "a" * 65
    directory = write_skill(
        tmp_path, long_name, front=f"name: {long_name}\ndescription: {'d' * 1025}"
    )
    found = codes(check_skill(directory, tmp_path), ERROR)
    assert {"long-name", "long-description"} <= found


def test_a_dangling_reference_is_an_error(tmp_path):
    directory = write_skill(
        tmp_path, "demo", body="Read `references/deep-dive.md` before starting.\n"
    )
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_reference_that_exists_is_fine(tmp_path):
    directory = write_skill(
        tmp_path, "demo", body="Read `references/deep-dive.md` before starting.\n"
    )
    (directory / "references").mkdir()
    (directory / "references" / "deep-dive.md").write_text("# Deep dive\n", encoding="utf-8")
    assert check_skill(directory, tmp_path) == []


def test_a_bare_directory_mention_is_not_a_reference(tmp_path):
    directory = write_skill(tmp_path, "demo", body="Put helper code in scripts/ if it repeats.\n")
    assert check_skill(directory, tmp_path) == []


def test_a_nested_skill_is_an_error(tmp_path):
    directory = write_skill(tmp_path, "demo")
    nested = directory / "references" / "inner"
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text("---\nname: inner\n---\n", encoding="utf-8")
    assert "nested-skill" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_shell_script_needs_a_shebang_and_the_executable_bit(tmp_path):
    directory = write_skill(tmp_path, "demo")
    scripts = directory / "scripts"
    scripts.mkdir()
    (scripts / "run.sh").write_text("echo hi\n", encoding="utf-8")
    found = codes(check_skill(directory, tmp_path), ERROR)
    assert {"no-shebang", "not-executable"} <= found


def test_a_description_with_no_trigger_clause_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", description="Does a thing competently.")
    assert "no-trigger" in codes(check_skill(directory, tmp_path), WARNING)


def test_a_description_near_the_cap_warns(tmp_path):
    description = "Use this skill when asked. " + "x" * 990
    directory = write_skill(tmp_path, "demo", description=description)
    assert "description-headroom" in codes(check_skill(directory, tmp_path), WARNING)


def test_shouting_warns_but_does_not_fail(tmp_path):
    directory = write_skill(tmp_path, "demo", body="You must ALWAYS check the exit code.\n")
    findings = check_skill(directory, tmp_path)
    assert "shouting" in codes(findings, WARNING)
    assert not any(f.failed for f in findings)


def test_an_over_long_skill_body_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", body="line\n" * 520)
    assert "long-skill" in codes(check_skill(directory, tmp_path), WARNING)


def test_find_skills_returns_every_skill_directory(tmp_path):
    write_skill(tmp_path, "one")
    write_skill(tmp_path, "two")
    assert [p.name for p in find_skills(tmp_path)] == ["one", "two"]


def write_plugin(root, name="engineering"):
    """Make a fixture directory into a real plugin."""
    manifest = root / "plugins" / name / ".claude-plugin"
    manifest.mkdir(parents=True, exist_ok=True)
    (manifest / "plugin.json").write_text(f'{{"name": "{name}"}}', encoding="utf-8")


def write_marketplace(root, plugins):
    directory = root / ".claude-plugin"
    directory.mkdir(exist_ok=True)
    (directory / "marketplace.json").write_text(
        json.dumps({"name": "x", "owner": {"name": "y"}, "plugins": plugins}), encoding="utf-8"
    )


def test_a_plugin_on_disk_must_be_listed(tmp_path):
    write_skill(tmp_path, "demo")
    write_plugin(tmp_path)
    write_marketplace(tmp_path, [])
    assert "unlisted-plugin" in codes(check_marketplace(tmp_path), ERROR)


def test_a_listed_plugin_must_exist(tmp_path):
    write_skill(tmp_path, "demo")
    write_plugin(tmp_path)
    write_marketplace(
        tmp_path,
        [
            {"name": "engineering", "source": "./plugins/engineering"},
            {"name": "ghost", "source": "./plugins/ghost"},
        ],
    )
    found = codes(check_marketplace(tmp_path), ERROR)
    assert "missing-listed-plugin" in found
    assert "unlisted-plugin" not in found


def test_a_skill_outside_every_plugin_is_reported(tmp_path):
    # A skill that no plugin ships installs for nobody, which is the same silent
    # failure as a skill missing from the old explicit list.
    write_plugin(tmp_path)
    write_marketplace(tmp_path, [{"name": "engineering", "source": "./plugins/engineering"}])
    stray = tmp_path / "loose" / "demo"
    stray.mkdir(parents=True)
    (stray / "SKILL.md").write_text(
        f"---\nname: demo\ndescription: {GOOD_DESCRIPTION}\n---\n", encoding="utf-8"
    )
    assert "unowned-skill" in codes(check_marketplace(tmp_path), ERROR)


def test_invalid_marketplace_json_is_an_error(tmp_path):
    write_skill(tmp_path, "demo")
    manifest = tmp_path / ".claude-plugin"
    manifest.mkdir()
    (manifest / "marketplace.json").write_text("{ not json", encoding="utf-8")
    assert "bad-json" in codes(check_marketplace(tmp_path), ERROR)


def test_a_path_inside_a_fenced_block_is_not_a_pointer(tmp_path):
    # Skills document layouts. Treating an illustrative path as a dangling pointer made
    # it impossible to show one without failing the build.
    body = (
        "Another project lays itself out like this:\n\n"
        "```text\ntheirs/\n  references/other.md\n```\n"
    )
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_tilde_fence_is_masked_too(tmp_path):
    body = "Example:\n\n~~~text\nreferences/other.md\n~~~\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_pointer_after_a_fence_is_still_checked(tmp_path):
    body = "```text\nsome/example\n```\n\nNow read `references/deep.md`.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_the_reported_line_points_at_the_pointer(tmp_path):
    body = "one\ntwo\n\nRead `references/deep.md` now.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    finding = next(f for f in check_skill(directory, tmp_path) if f.code == "dangling-reference")
    lines = (directory / "SKILL.md").read_text().split("\n")
    assert "references/deep.md" in lines[finding.line - 1]


def test_an_unterminated_fence_does_not_switch_the_check_off(tmp_path):
    # Masking to end-of-file would silently stop checking every pointer after it, which
    # is the failure this validator exists to prevent rather than to have.
    body = "```text\nnever closed\n\nRead `references/deep.md`.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_longer_fence_survives_a_nested_shorter_one(tmp_path):
    body = "````text\nouter\n```\ninner\n```\nreferences/inside.md\n````\n"
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


def test_a_readme_in_the_agents_directory_is_not_a_subagent(tmp_path):
    from skillcheck.rules import find_agents

    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "README.md").write_text("# Subagents\n", encoding="utf-8")
    (agents / "real-agent.md").write_text("---\nname: real-agent\n---\n", encoding="utf-8")
    assert [p.name for p in find_agents(agents)] == ["real-agent.md"]


@pytest.mark.parametrize(
    "body",
    [
        "See https://example.com/assets/logo.png for the badge.\n",
        "See [the spec](https://cdn.example.com/references/spec.md).\n",
        "Their layout is `their-repo/references/x.md` upstream.\n",
        "Compare with ../other-skill/references/deep.md if curious.\n",
    ],
)
def test_a_path_inside_a_longer_path_is_not_a_pointer(tmp_path, body):
    # Matching a bare substring reported a URL, and another project's path, as a
    # dangling pointer into this skill's own bundle.
    directory = write_skill(tmp_path, "demo", body=body)
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize(
    "body",
    [
        "Read `references/deep.md` before starting.\n",
        "Read references/deep.md before starting.\n",
        "- references/deep.md explains it\n",
        "(see references/deep.md)\n",
    ],
)
def test_a_real_pointer_is_still_caught_however_it_is_written(tmp_path, body):
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        ("[]", "manifest is a list"),
        ('{"plugins": "x"}', "plugins is a string"),
        ('{"plugins": ["x"]}', "a plugin entry is a string"),
        (
            '{"plugins": [{"name": "p", "source": 1}]}',
            "skills is a string",
        ),
        ('{"plugins": [{"name": "p", "agents": "x"}]}', "agents is a string"),
        ('{"plugins": [{"name": "p", "skills": [1]}]}', "skills holds a non-string"),
    ],
)
def test_a_malformed_manifest_reports_rather_than_crashes(tmp_path, manifest, reason):
    # Reaching `.get` on a string aborted the whole run with a traceback, and iterating
    # a string `skills` value reported one dangling entry per character. Neither said
    # anything about the actual problem.
    write_skill(tmp_path, "demo")
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(manifest, encoding="utf-8")
    assert "bad-marketplace-shape" in codes(check_marketplace(tmp_path), ERROR), reason


@pytest.mark.parametrize(
    "body",
    [
        "Read ./references/deep.md first.\n",
        "Read `./references/deep.md` first.\n",
        "Read [deep](./references/deep.md) first.\n",
        "Run ./scripts/run.sh afterwards.\n",
    ],
)
def test_a_relative_pointer_written_with_a_dot_slash_is_caught(tmp_path, body):
    # The lookbehind that stopped URLs matching also excluded '.' and '/', which killed
    # the ordinary ./references/x.md form - the commonest way to link a bundled file.
    directory = write_skill(tmp_path, "demo", body=body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_file_that_is_not_utf8_reports_rather_than_crashing(tmp_path):
    directory = write_skill(tmp_path, "demo")
    (directory / "SKILL.md").write_bytes(
        "---\nname: demo\ndescription: caf\xe9.\n---\n".encode("latin-1")
    )
    assert codes(check_skill(directory, tmp_path), ERROR) == {"not-utf8"}


def test_two_skills_may_not_share_a_name(tmp_path):
    from skillcheck.rules import check_duplicate_names, find_skills

    write_skill(tmp_path, "demo")
    other = tmp_path / "plugins" / "personal" / "skills" / "demo"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text(
        f"---\nname: demo\ndescription: {GOOD_DESCRIPTION}\n---\n", encoding="utf-8"
    )
    skills = find_skills(tmp_path)
    assert "duplicate-skill-name" in codes(check_duplicate_names(skills, tmp_path), ERROR)


def test_a_nested_script_is_checked_too(tmp_path):
    directory = write_skill(tmp_path, "demo")
    nested = directory / "scripts" / "helpers"
    nested.mkdir(parents=True)
    (nested / "inner.sh").write_text("echo hi\n", encoding="utf-8")
    assert {"no-shebang", "not-executable"} <= codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize("key", ["when_to_use", "argument-hint", "disable-model-invocation"])
def test_a_claude_code_only_key_is_refused_with_the_portability_reason(tmp_path, key):
    # Claude Code accepts these; the Skills API upload route rejects them with a hard
    # error. The message has to say that, because "unexpected key" invites the author
    # to argue with the validator rather than learn the constraint.
    directory = write_skill(tmp_path, "demo", front=f"name: demo\ndescription: x\n{key}: y")
    findings = [f for f in check_skill(directory, tmp_path) if f.code == "unknown-key"]
    assert len(findings) == 1
    assert "upload route rejects" in findings[0].message
    if key == "when_to_use":
        assert "'description'" in findings[0].message
