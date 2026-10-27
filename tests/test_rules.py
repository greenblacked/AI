"""Rule-level tests.

Each case builds a throwaway skill directory containing exactly one defect, so a
failure names the rule that broke rather than "something is wrong with validation".
"""

from __future__ import annotations

import json

import pytest

from skillcheck.rules import (
    ERROR,
    WARNING,
    _cede_targets,
    check_marketplace,
    check_skill,
    find_skills,
)

# Long enough to clear the description floor, because every "produces nothing" case
# below would otherwise be asserting against a short-description warning instead of the
# defect it is about.
GOOD_DESCRIPTION = (
    "Do a specific, useful thing end to end, from the first command through the check "
    "that says it worked. Use this skill whenever the user asks for that thing, "
    "including casual phrasings such as asking for it to be sorted out, looked at or "
    "finished off, and whenever they hand back the output of a run that stopped part "
    "way through. Covers the ordering the steps have to run in, the flag that matters "
    "on each command, and the state to leave behind when a run is abandoned half done "
    "so the next attempt starts from something known."
)

# The names a cede clause in these fixtures is allowed to reach. `neighbour` is in it
# because the fixture eval set routes a negative there, and passing `known` at all turns
# a name it does not hold into an `unknown-expected` error.
KNOWN = frozenset({"demo", "neighbour", "image-hardening"})


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
        # nothing" would trip over the missing-eval-set warning instead. One negative
        # names a winner for the same reason: a set where none does earns `no-routing`.
        (directory / "evals").mkdir(exist_ok=True)
        cases = [{"query": f"positive {i}", "should_trigger": True} for i in range(10)]
        cases += [{"query": "negative 0", "should_trigger": False, "expected": "neighbour"}]
        cases += [{"query": f"negative {i}", "should_trigger": False} for i in range(1, 10)]
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


def test_shouting_is_reported_for_every_occurrence_not_only_the_first(tmp_path):
    body = "You must ALWAYS check the exit code. NEVER ignore a nonzero one.\n"
    directory = write_skill(tmp_path, "demo", body=body)
    findings = [f for f in check_skill(directory, tmp_path) if f.code == "shouting"]
    assert len(findings) == 2


def test_shouting_inside_a_fenced_code_block_is_not_reported(tmp_path):
    # A shell comment or a quoted example is not the skill shouting at its reader — the
    # command and rule checks already masked fences for this reason; the skill body
    # check did not.
    body = "```bash\n# ALWAYS quote your variables\necho hi\n```\n"
    directory = write_skill(tmp_path, "demo", body=body)
    findings = [f for f in check_skill(directory, tmp_path) if f.code == "shouting"]
    assert findings == []


def test_shouting_in_the_description_is_reported(tmp_path):
    # The description loads every session regardless of whether the body is ever read,
    # so a shouted rule there was invisible to this check even though it is the one
    # place shouting reaches every time.
    description = GOOD_DESCRIPTION + " NEVER skip this step."
    directory = write_skill(tmp_path, "demo", description=description)
    findings = [f for f in check_skill(directory, tmp_path) if f.code == "shouting"]
    assert len(findings) == 1
    assert findings[0].line == 3


def test_an_over_long_skill_body_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", body="line\n" * 520)
    assert "long-skill" in codes(check_skill(directory, tmp_path), WARNING)


def test_find_skills_returns_every_skill_directory(tmp_path):
    write_skill(tmp_path, "one")
    write_skill(tmp_path, "two")
    assert [p.name for p in find_skills(tmp_path)] == ["one", "two"]


def test_find_skills_excludes_only_the_top_level_template_directory(tmp_path):
    (tmp_path / "template").mkdir()
    (tmp_path / "template" / "SKILL.md").write_text("---\nname: template\n---\n", encoding="utf-8")
    assert find_skills(tmp_path) == []


def test_find_skills_does_not_exclude_a_skill_named_template(tmp_path):
    """Matching the word anywhere in the path, rather than only at the root, used to
    exclude any skill named `template` at any depth — a plugin shipping
    `skills/template/` lost that skill from every check silently."""
    directory = write_skill(tmp_path, "template")
    assert find_skills(tmp_path) == [directory]


def test_find_skills_does_not_exclude_a_skill_named_template_when_scoped_to_skills_dir(tmp_path):
    """Several callers pass a single plugin's `skills/` directory as `root` rather than
    the repository root — `check_marketplace`'s owned-skill set, `check_readme.py` and
    `export_portable.py` among them. Checking only the top-level directory name against
    that narrower `root` reintroduced the same bug one level down: `skills/template/`
    again looked like the repository's own template and was hidden from exactly the
    callers most likely to be scoped this way."""
    directory = write_skill(tmp_path, "template")
    skills_dir = tmp_path / "plugins" / "engineering" / "skills"
    assert find_skills(skills_dir) == [directory]


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


def test_a_bundled_script_that_is_not_utf8_reports_rather_than_crashing(tmp_path):
    """One mis-encoded script used to abort the whole run with a traceback and zero
    findings for every other skill, which in CI reads as "the validator is broken"."""
    directory = write_skill(tmp_path, "demo")
    scripts = directory / "scripts"
    scripts.mkdir()
    (scripts / "run.sh").write_bytes("#!/bin/sh\necho caf\xe9\n".encode("latin-1"))
    assert "not-utf8" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_reference_that_is_not_utf8_reports_rather_than_crashing(tmp_path):
    directory = write_skill(tmp_path, "demo")
    references = directory / "references"
    references.mkdir()
    (references / "depth.md").write_bytes("# caf\xe9\n".encode("latin-1"))
    assert "not-utf8" in codes(check_skill(directory, tmp_path), ERROR)


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


def test_unparseable_frontmatter_is_one_error_and_stops_there(tmp_path):
    # Every later rule reads the frontmatter, so a parse failure is reported once
    # rather than as a cascade of missing-name and missing-description.
    directory = write_skill(tmp_path, "demo", front="name: demo\ndescription")
    findings = check_skill(directory, tmp_path)
    assert [f.code for f in findings] == ["frontmatter"]


def test_a_directory_mentioned_generically_is_not_a_pointer(tmp_path):
    directory = write_skill(tmp_path, "demo", body="# Demo\n\nPut helpers in scripts/ later.\n")
    assert "dangling-reference" not in codes(check_skill(directory, tmp_path))


def test_a_long_reference_without_a_table_of_contents_warns(tmp_path):
    directory = write_skill(tmp_path, "demo", body="# Demo\n\nRead references/long.md first.\n")
    (directory / "references").mkdir()
    (directory / "references" / "long.md").write_text(
        "# Long\n\n" + "line\n" * 120, encoding="utf-8"
    )
    assert "no-toc" in codes(check_skill(directory, tmp_path), WARNING)
    (directory / "references" / "long.md").write_text(
        "# Long\n\n## Contents\n\n- [A](#a)\n\n" + "line\n" * 120, encoding="utf-8"
    )
    assert "no-toc" not in codes(check_skill(directory, tmp_path), WARNING)


def test_a_missing_marketplace_manifest_is_an_error(tmp_path):
    write_skill(tmp_path, "demo")
    assert codes(check_marketplace(tmp_path)) == {"no-marketplace"}


def test_an_agent_outside_every_plugin_is_unowned(tmp_path):
    write_skill(tmp_path, "demo")
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "m",
                "owner": {"name": "t"},
                "plugins": [{"name": "engineering", "source": "./plugins/engineering"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "plugins" / "engineering" / ".claude-plugin").mkdir()
    (tmp_path / "plugins" / "engineering" / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "engineering", "description": "t"}), encoding="utf-8"
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "stray.md").write_text(
        "---\nname: stray\ndescription: Do a thing. Use when asked.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert "unowned-agent" in codes(check_marketplace(tmp_path))


def test_a_cede_clause_naming_a_skill_that_does_not_exist_is_an_error(tmp_path):
    # Deleting a subagent left a description ceding to it and nothing noticed. The
    # description is what the runtime loads, so the turned-away query lands nowhere.
    description = GOOD_DESCRIPTION + " Not for rebuilding the base image (image-builder)."
    directory = write_skill(tmp_path, "demo", description=description)
    findings = [f for f in check_skill(directory, tmp_path, KNOWN) if f.code == "dangling-cede"]
    assert [f.level for f in findings] == [ERROR]
    assert "image-builder" in findings[0].message


def test_the_which_is_form_of_a_cede_clause_is_read_too(tmp_path):
    description = GOOD_DESCRIPTION + " Not for auditing the modules, which is iac-review."
    directory = write_skill(tmp_path, "demo", description=description)
    assert "dangling-cede" in codes(check_skill(directory, tmp_path, KNOWN), ERROR)


def test_a_cede_clause_naming_something_that_exists_is_clean(tmp_path):
    description = GOOD_DESCRIPTION + " Not for locking down a base image (image-hardening)."
    directory = write_skill(tmp_path, "demo", description=description)
    assert check_skill(directory, tmp_path, KNOWN) == []


def test_a_cede_clause_naming_a_command_is_still_an_error(tmp_path):
    # Commands are deliberately absent from `known`. A cede clause tells the router
    # where the query should go instead, and a command never receives a routed query —
    # it only fires when typed — so ceding to one sends the query nowhere.
    description = GOOD_DESCRIPTION + " Not for cutting the release, which is ship-release."
    directory = write_skill(tmp_path, "demo", description=description)
    commands = tmp_path / "plugins" / "engineering" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    (commands / "ship-release.md").write_text("# Ship\n", encoding="utf-8")
    assert "dangling-cede" in codes(check_skill(directory, tmp_path, KNOWN), ERROR)


@pytest.mark.parametrize(
    "description",
    [
        "Run the smoke suite rather than the full one, which is long-running.",
        "Ownership belongs to the on-call engineer (read-only).",
        "The team cannot form a plan without the numbers (dry-run).",
        "Unlike the full pipeline, which is multi-stage.",
        "Do not use it for (a) reviewing a plan or (b) writing a module.",
        "Not for step (1) or step (2) of the rollout.",
    ],
)
def test_ordinary_prose_is_never_read_as_a_cede_clause(tmp_path, description):
    # Every one of these was a false positive while the marker list included "rather
    # than", "belongs to" and "Unlike ". The scan runs from the first marker to the end
    # of the description, so a loose marker drags an ordinary parenthesised aside into
    # the span. Only explicit negatives open a cede clause.
    assert _cede_targets(description) == []


def test_a_description_with_no_cede_clause_is_not_scanned(tmp_path):
    description = GOOD_DESCRIPTION + " The default run is safe (read-only) until confirmed."
    directory = write_skill(tmp_path, "demo", description=description)
    assert check_skill(directory, tmp_path, KNOWN) == []


def test_a_hyphenated_aside_before_the_cede_clause_is_not_a_target(tmp_path):
    # The false-positive guard the whole rule rests on: over a full description the same
    # two shapes match asides such as "(read-only)" and report them as missing skills,
    # which is why the scan starts at the cede marker and not at the first character.
    description = (
        GOOD_DESCRIPTION + " The first pass is safe (read-only) and the rollback is "
        "single-step, which is deliberate. Not for locking down a base image "
        "(image-hardening)."
    )
    directory = write_skill(tmp_path, "demo", description=description)
    assert check_skill(directory, tmp_path, KNOWN) == []


def test_without_a_known_set_the_cede_clause_is_not_checked(tmp_path):
    # The precedent `unknown-expected` set: a caller that cannot say what exists gets
    # silence rather than a guess at it.
    description = GOOD_DESCRIPTION + " Not for rebuilding the base image (image-builder)."
    directory = write_skill(tmp_path, "demo", description=description)
    assert check_skill(directory, tmp_path) == []


def _description_of_length(length: int) -> str:
    """A description that triggers nothing but the length rules, padded to `length`."""
    base = "Do the thing. Use this skill when asked for it. "
    return base + "x" * (length - len(base))


def test_a_description_under_the_floor_warns(tmp_path):
    # 500 is the floor of the guidance in AGENTS.md, and nothing enforced it: a
    # description this short names the topic without the trigger phrasings or the
    # boundary, so it fires on everything adjacent or on nothing.
    directory = write_skill(tmp_path, "demo", description=_description_of_length(499))
    assert "short-description" in codes(check_skill(directory, tmp_path, KNOWN), WARNING)


def test_a_description_on_the_floor_does_not_warn(tmp_path):
    directory = write_skill(tmp_path, "demo", description=_description_of_length(500))
    assert check_skill(directory, tmp_path, KNOWN) == []


def _with_scripts(tmp_path, body, *, reference=None):
    """A skill shipping scripts/run.py and scripts/run.sh, with the given body."""
    directory = write_skill(tmp_path, "demo", body=body)
    scripts = directory / "scripts"
    scripts.mkdir()
    (scripts / "run.py").write_text("print('x')\n", encoding="utf-8")
    shell = scripts / "run.sh"
    shell.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    shell.chmod(0o755)
    if reference is not None:
        (directory / "references").mkdir()
        (directory / "references" / "deep.md").write_text(reference, encoding="utf-8")
    return directory


# A relative path resolves against the user's project, so a file there at the same path
# runs in place of the bundled one. Every form below was in a skill before #328-#330.
@pytest.mark.parametrize(
    "line",
    [
        "Run `python3 scripts/run.py` first.",
        "Run `python scripts/run.py --flag`.",
        "Run `python3 -I scripts/run.py`.",
        "Run `python3 -I -X utf8 ./scripts/run.py`.",
        "Run `bash scripts/run.sh`.",
        "Run `./scripts/run.sh`.",
        "Run `git bisect run ./scripts/run.sh`.",
        'Run `python "scripts/run.py"`.',
        "Run `bash 'scripts/run.sh'`.",
        "Run `python3.11 scripts/run.py`.",
        "Run `python -W ignore scripts/run.py`.",
        "Run `python3 -X dev scripts/run.py`.",
        "Run `uv run scripts/run.py`.",
        "Run `source scripts/run.sh`.",
        'Run `bash -c "scripts/run.sh"`.',
    ],
)
def test_a_bundled_script_run_by_a_relative_path_is_an_error(tmp_path, line):
    directory = _with_scripts(tmp_path, f"# Demo\n\n{line}\n")
    found = [f for f in check_skill(directory, tmp_path) if f.code == "relative-bundled-script"]
    assert [f.level for f in found] == [ERROR]
    assert "${CLAUDE_SKILL_DIR}/scripts/run." in found[0].message
    lines = (directory / "SKILL.md").read_text().split("\n")
    assert "scripts/run." in lines[found[0].line - 1]


@pytest.mark.parametrize("prefix", ["", "$ "])
def test_a_command_at_the_start_of_a_fenced_line_is_an_error(tmp_path, prefix):
    directory = _with_scripts(tmp_path, f"```bash\n{prefix}scripts/run.sh --all\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    ("info", "fires"),
    [
        ("text", False),
        ("tree", False),
        ("plaintext", False),
        ("markdown", False),
        ("bash", True),
        ("sh", True),
        ("", False),
    ],
)
def test_a_line_start_script_is_only_an_invocation_in_a_shell_fence(tmp_path, info, fires):
    # A layout tree in a text fence lists scripts/run.py with a trailing comment; that is
    # an illustration, and telling its author to add ${CLAUDE_SKILL_DIR} would be wrong.
    body = f"```{info}\nscripts/run.py   # the checker\n```\n"
    directory = _with_scripts(tmp_path, body)
    found = "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)
    assert found is fires


def test_a_directory_named_like_a_reference_does_not_crash(tmp_path):
    directory = _with_scripts(tmp_path, "# Demo\n", reference="# Deep\n")
    (directory / "references" / "odd.md").mkdir()
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize("name", ["dang.md", "loop.md"])
def test_a_broken_symlink_reference_is_reported_once_not_a_crash(tmp_path, name):
    directory = _with_scripts(tmp_path, "# Demo\n", reference="# Deep\n")
    link = directory / "references" / name
    link.symlink_to("gone.md" if name == "dang.md" else name)
    found = [f for f in check_skill(directory, tmp_path) if f.code == "dangling-reference"]
    assert [f.level for f in found] == [ERROR]
    assert name in found[0].message


def test_a_relative_script_in_a_reference_file_is_an_error(tmp_path):
    directory = _with_scripts(
        tmp_path,
        "Read `references/deep.md`.\n",
        reference="# Deep\n\nRun `python3 scripts/run.py`.\n",
    )
    found = [f for f in check_skill(directory, tmp_path) if f.code == "relative-bundled-script"]
    assert len(found) == 1
    assert str(found[0].path).endswith("references/deep.md")
    assert found[0].line == 3
    assert "references/deep.md" in found[0].message


@pytest.mark.parametrize(
    "body",
    [
        "`scripts/run.py` reads only the config.\n",
        "The helper lives in scripts/run.py and is small.\n",
        "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/run.py`.\n",
        "Run `bash $CLAUDE_SKILL_DIR/scripts/run.sh`.\n",
        "Run `${CLAUDE_SKILL_DIR}/scripts/run.sh`.\n",
        # Outside a fence, a line that merely begins with the path is prose.
        "scripts/run.py is the helper.\n",
        "```bash\npython3 ${CLAUDE_SKILL_DIR}/scripts/run.py\n```\n",
    ],
)
def test_other_mentions_of_a_script_are_not_relative_invocations(tmp_path, body):
    directory = _with_scripts(tmp_path, f"# Demo\n\n{body}")
    assert "relative-bundled-script" not in codes(check_skill(directory, tmp_path))
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize("line", ["Run `python3 scripts/other.py`.", "Run `./scripts/other.sh`."])
def test_a_script_the_skill_does_not_ship_is_not_a_relative_invocation(tmp_path, line):
    # A runbook may name its own project's script; only a file the skill bundles is the
    # one a same-named project file would shadow.
    directory = write_skill(tmp_path, "demo", body=f"# Demo\n\n```bash\n{line}\n```\n")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize(
    "body",
    [
        "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/missing.py`.\n",
        "```bash\npython3 ${CLAUDE_SKILL_DIR}/scripts/missing.py\n```\n",
        "Read `$CLAUDE_SKILL_DIR/references/missing.md`.\n",
    ],
)
def test_a_dangling_skill_dir_pointer_is_an_error_fenced_or_not(tmp_path, body):
    directory = _with_scripts(tmp_path, f"# Demo\n\n{body}")
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "body",
    [
        "Run `${CLAUDE_SKILL_DIR}/scripts/x.{py,sh}`.\n",
        "Run `${CLAUDE_SKILL_DIR}/scripts/x-$V.sh`.\n",
        "Run `${CLAUDE_SKILL_DIR}/scripts/*.sh`.\n",
        "Run `${CLAUDE_SKILL_DIR}/scripts/<name>.sh`.\n",
        "Run `${CLAUDE_SKILL_DIR}/scripts/x.py*`.\n",
        "Read `${CLAUDE_SKILL_DIR}/references/api.v2-<topic>.md`.\n",
        "Read `${CLAUDE_SKILL_DIR}/references/v1.2-*.md`.\n",
        "Helpers live under `${CLAUDE_SKILL_DIR}/scripts`.\n",
    ],
)
def test_a_skill_dir_pattern_or_directory_is_not_a_dangling_pointer(tmp_path, body):
    # The relative form of each of these is already skipped by the prose check.
    directory = _with_scripts(tmp_path, f"# Demo\n\n{body}")
    assert "dangling-reference" not in codes(check_skill(directory, tmp_path))


def test_a_dangling_skill_dir_pointer_in_a_reference_file_is_an_error(tmp_path):
    directory = _with_scripts(
        tmp_path,
        "Read `references/deep.md`.\n",
        reference="Run `python3 ${CLAUDE_SKILL_DIR}/scripts/missing.py`.\n",
    )
    found = [f for f in check_skill(directory, tmp_path) if f.code == "dangling-reference"]
    assert len(found) == 1
    assert str(found[0].path).endswith("references/deep.md")


@pytest.mark.parametrize(
    "line",
    [
        "cd /tmp && scripts/run.sh",
        "FOO=1 scripts/run.sh",
        "true || scripts/run.sh",
        "true; scripts/run.sh",
        "echo x | scripts/run.sh",
        ". scripts/run.sh",
    ],
)
def test_a_script_after_a_shell_operator_in_a_shell_fence_is_an_error(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "line",
    [
        'cd "${CLAUDE_SKILL_DIR}" && ./scripts/run.sh',
        "cd ${CLAUDE_SKILL_DIR} && python3 scripts/run.py",
        "cd $CLAUDE_SKILL_DIR && bash scripts/run.sh",
    ],
)
def test_a_command_after_cd_into_the_skill_dir_on_the_same_line_is_not_relative(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize("info", ["console", "shell-session"])
def test_a_console_fence_line_is_a_command_only_after_a_prompt(tmp_path, info):
    # These fences hold command output too; a listing of the skill's own script is output.
    output = _with_scripts(tmp_path, f"```{info}\n$ git diff --name-only\nscripts/run.sh\n```\n")
    assert "relative-bundled-script" not in codes(check_skill(output, tmp_path))


@pytest.mark.parametrize("info", ["console", "shell-session"])
def test_a_prompted_script_in_a_console_fence_is_an_error(tmp_path, info):
    directory = _with_scripts(tmp_path, f"```{info}\n$ scripts/run.sh --all\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize("line", ["python3 scripts/run.py", "./scripts/run.sh", "scripts/run.sh"])
def test_a_command_after_a_cd_on_an_earlier_line_of_the_fence_is_not_relative(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\ncd ${{CLAUDE_SKILL_DIR}}\n{line}\n```\n")
    assert check_skill(directory, tmp_path) == []


def test_a_cd_into_the_skill_dir_does_not_carry_into_the_next_fence(tmp_path):
    body = "```bash\ncd ${CLAUDE_SKILL_DIR}\n```\n\n```bash\npython3 scripts/run.py\n```\n"
    directory = _with_scripts(tmp_path, body)
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "line",
    [
        "# Runs the bundled checker (scripts/check.py) against the project",
        "cmd  # see also; scripts/check.py docs",
        "grep x | sort  # the pipe | scripts/check.py is not used",
    ],
)
def test_a_shell_comment_that_mentions_a_script_is_not_an_invocation(tmp_path, line):
    body = f"```bash\n{line}\n```\n"
    directory = _with_scripts(tmp_path, body)
    (directory / "scripts" / "check.py").write_text("print('x')\n", encoding="utf-8")
    assert "relative-bundled-script" not in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize("info", ["", "bash"])
def test_a_cd_into_the_skill_directory_holds_in_any_fence(tmp_path, info):
    body = f'```{info}\ncd "${{CLAUDE_SKILL_DIR}}"\npython3 scripts/run.py\n```\n'
    directory = _with_scripts(tmp_path, body)
    assert "relative-bundled-script" not in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "line",
    [
        'cd "${CLAUDE_SKILL_DIR}/.." && python3 scripts/run.py',
        "cd ${CLAUDE_SKILL_DIR}/scripts && python3 scripts/run.py",
        "cd $CLAUDE_SKILL_DIR_OTHER && python3 scripts/run.py",
    ],
)
def test_a_cd_that_does_not_land_in_the_skill_dir_is_no_exemption(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "line",
    ['cd "${CLAUDE_SKILL_DIR}/" && ./scripts/run.sh', "cd ${CLAUDE_SKILL_DIR}; ./scripts/run.sh"],
)
def test_a_cd_to_exactly_the_skill_dir_is_still_an_exemption(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize(
    "line",
    ["git diff -- ./scripts/run.py", "cat ./scripts/run.sh", "chmod +x ./scripts/run.sh"],
)
def test_a_dot_slash_path_that_is_only_an_argument_is_not_a_run(tmp_path, line):
    # Reading or diffing a project file does not execute the bundled script, and the
    # suggested fix would change which file the command inspects.
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert "relative-bundled-script" not in codes(check_skill(directory, tmp_path))


@pytest.mark.parametrize(
    "line", ["sudo ./scripts/run.sh", "exec scripts/run.sh", "time ./scripts/run.sh --all"]
)
def test_a_script_after_an_execution_wrapper_is_an_error(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "line",
    [
        'printf "%s" " # " && python3 scripts/run.py',
        "echo 'a # b'; ./scripts/run.sh",
        "echo \\# && python3 scripts/run.py",
    ],
)
def test_a_quoted_or_escaped_hash_is_not_a_shell_comment(tmp_path, line):
    directory = _with_scripts(tmp_path, f"```bash\n{line}\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "body",
    [
        '(cd "${CLAUDE_SKILL_DIR}" && python3 scripts/run.py)\npython3 scripts/run.py',
        '(cd "${CLAUDE_SKILL_DIR}" && true); python3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}"\ncd -\npython3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}" && cd /tmp && python3 scripts/run.py',
        '(cd "${CLAUDE_SKILL_DIR}"\ntrue\n)\npython3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}"; cd; python3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}" || { cd /tmp && python3 scripts/run.py; }',
    ],
)
def test_a_cd_holds_only_in_its_own_shell_scope(tmp_path, body):
    directory = _with_scripts(tmp_path, f"```bash\n{body}\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


@pytest.mark.parametrize(
    "body",
    [
        '(cd "${CLAUDE_SKILL_DIR}" && python3 scripts/run.py)',
        'cd "${CLAUDE_SKILL_DIR}" && (python3 scripts/run.py)',
        'echo "(" && cd "${CLAUDE_SKILL_DIR}"\npython3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}" && echo "cd /tmp" && python3 scripts/run.py',
        '(cd "${CLAUDE_SKILL_DIR}"\npython3 scripts/run.py\n)',
        '(\ncd "${CLAUDE_SKILL_DIR}"\n./scripts/run.sh\n)',
        'cd "${CLAUDE_SKILL_DIR}" && printf "%s" cd && python3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}" && cat docs/cd.md && python3 scripts/run.py',
        'cd "${CLAUDE_SKILL_DIR}"\nls cd\npython3 scripts/run.py',
    ],
)
def test_a_cd_still_covers_commands_inside_its_scope(tmp_path, body):
    directory = _with_scripts(tmp_path, f"```bash\n{body}\n```\n")
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize("info", ["console", "shell-session"])
@pytest.mark.parametrize(
    "output", ["python3 scripts/run.py", "./scripts/run.sh --all", "bash scripts/run.sh"]
)
def test_unprompted_output_in_a_transcript_is_not_a_command(tmp_path, info, output):
    body = f"```{info}\n$ cat history.txt\n{output}\n```\n"
    directory = _with_scripts(tmp_path, body)
    assert "relative-bundled-script" not in codes(check_skill(directory, tmp_path))


@pytest.mark.parametrize("info", ["console", "shell-session"])
def test_a_prompted_cd_into_the_skill_covers_the_next_prompted_command(tmp_path, info):
    body = f'```{info}\n$ cd "${{CLAUDE_SKILL_DIR}}"\n$ python3 scripts/run.py\n```\n'
    directory = _with_scripts(tmp_path, body)
    assert check_skill(directory, tmp_path) == []


@pytest.mark.parametrize("info", ["console", "shell-session"])
def test_a_prompted_relative_run_in_a_transcript_is_still_an_error(tmp_path, info):
    directory = _with_scripts(tmp_path, f"```{info}\n$ python3 scripts/run.py\n```\n")
    assert "relative-bundled-script" in codes(check_skill(directory, tmp_path), ERROR)


def test_a_dangling_skill_dir_pointer_in_transcript_output_is_still_reported(tmp_path):
    body = "```console\n$ ls\n${CLAUDE_SKILL_DIR}/scripts/missing.py\n```\n"
    directory = _with_scripts(tmp_path, body)
    assert "dangling-reference" in codes(check_skill(directory, tmp_path), ERROR)
