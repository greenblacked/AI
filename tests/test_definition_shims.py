"""`scripts/definition_shims.py`: wrapping a subagent or command as a one-file skill.

Neither skill scanner has an agent or command type, so the `security.yml` scan jobs read
each definition through a shim. These cases build a small git repository, because the
script enumerates with `git ls-files`, and pin the three things a mistake would make
silent: which files are scanned, what the shim's id is (Cisco suppressions key on it),
and that a refused file fails the run rather than going unscanned.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from tests.conftest import REPO, load_script

shims = load_script("definition_shims.py")

AGENT = "---\nname: helper\ndescription: Reads logs.\ntools: Read\n---\n\nBody.\n"
COMMAND = "---\ndescription: Do a thing.\nallowed-tools: Bash(git status:*)\n---\n\nRun it.\n"

# Every location the script covers, and a file in each.
LOCATIONS = {
    "plugins/demo/agents/helper.md": AGENT,
    "plugins/demo/commands/run-it.md": COMMAND,
    ".claude/agents/builder.md": AGENT,
    ".claude/commands/ship-it.md": COMMAND,
}
# Close to a location but not in it, so none is a definition.
EXCLUDED = {
    "plugins/demo/agents/evals/helper.json": "{}\n",
    ".claude/agents/benchmarks/reviewer/case/change.patch": "+x\n",
    ".claude/agents/evals/builder.json": "{}\n",
    "plugins/demo/agents/notes.txt": "text\n",
    "plugins/demo/skills/alpha/SKILL.md": "---\nname: alpha\n---\n",
    "plugins/demo/skills/alpha/agents/inner.md": "# nested\n",
    "docs/agents/guide.md": "# docs\n",
    # No .md of any case or depth below an agents/ folder is excluded: Claude Code's loader
    # reads them all (see test_a_markdown_file_anywhere_under_agents_is_refused).
}


def git_env(home):
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


def git(repo, env, *args):
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()


class Repo:
    def __init__(self, path, env):
        self.path, self.env = path, env

    def write(self, rel, text):
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message="change"):
        git(self.path, self.env, "add", "-A")
        git(self.path, self.env, "commit", "--quiet", "--allow-empty", "-m", message)
        return git(self.path, self.env, "rev-parse", "HEAD")

    def git(self, *args):
        return git(self.path, self.env, *args)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    env = git_env(tmp_path)
    git(root, env, "init", "--quiet", "--initial-branch=main")
    built = Repo(root, env)
    for rel, text in {**LOCATIONS, **EXCLUDED}.items():
        built.write(rel, text)
    built.commit("base")
    return built


def run(repo, out, *args):
    return shims.main(["--repo", str(repo.path), "--out", str(out), *args])


def test_all_four_locations_are_enumerated_and_nothing_near_them(repo):
    assert shims.list_definitions(repo.path) == sorted(LOCATIONS)


def test_the_real_repository_enumerates_what_an_independent_glob_finds():
    # Path.glob's `*` never crosses a slash and `**` does, so this is a second opinion on
    # the depth rule (both kinds at any depth), not a copy of the regex.
    expected = set()
    for pattern in (
        "plugins/*/agents/**/*.md",
        "plugins/*/commands/**/*.md",
        ".claude/agents/**/*.md",
        ".claude/commands/**/*.md",
    ):
        expected |= {p.relative_to(REPO).as_posix() for p in REPO.glob(pattern)}
    found = shims.list_definitions(REPO)
    assert set(found) == expected
    assert expected
    assert not [p for p in found if "/evals/" in p or "/benchmarks/" in p]


@pytest.mark.parametrize(
    ("path", "ident"),
    [
        ("plugins/operations/agents/ci-log-reader.md", "agent--operations--ci-log-reader"),
        ("plugins/delivery/commands/changelog.md", "command--delivery--changelog"),
        (".claude/agents/reviewer.md", "agent--claude--reviewer"),
        (".claude/commands/ship.md", "command--claude--ship"),
        ("plugins/delivery/commands/release/notes.md", "command--delivery--release--notes"),
        (".claude/commands/team/review/pr.md", "command--claude--team--review--pr"),
    ],
)
def test_the_id_scheme_is_pinned(path, ident):
    # Cisco suppressions in cisco-policy.yaml name a shim by this id, so changing the
    # scheme silently detaches every one of them.
    assert shims.definition_id(path, {"operations", "delivery"}) == ident


@pytest.mark.parametrize(
    "path",
    [
        "docs/agents/guide.md",
        "plugins/demo/agents/evals/notes.md",
        "plugins/demo/skills/alpha/SKILL.md",
        ".claude/agents/benchmarks/reviewer/case/README.md",
        "plugins/demo/agents/nested/deep.md",
        ".claude/agents/nested/deep.md",
        "plugins/demo/agents/helper.json",
        "agents/helper.md",
    ],
)
def test_definition_id_refuses_a_path_that_is_not_a_definition(path):
    with pytest.raises(shims.DefinitionError):
        shims.definition_id(path, {"demo"})


@pytest.mark.parametrize(
    "path",
    [
        "plugins/demo/commands/Group/run.md",
        "plugins/demo/commands/two--hyphens/run.md",
        "plugins/demo/commands/group/under_score.md",
        "plugins/demo/commands/-lead/run.md",
        "plugins/demo/commands/group//run.md",
    ],
)
def test_a_nested_command_name_that_fails_the_strict_pattern_is_refused(path):
    with pytest.raises(shims.DefinitionError):
        shims.definition_id(path, {"demo"})


@pytest.mark.parametrize(
    "name",
    ["Upper.md", "under_score.md", "has space.md", "-lead.md", "trail-.md", "two--hyphens.md"]
    + ["dot.in.md", ".hidden.md", "README.md", "semi;colon.md", "newline\nx.md", "tab\tx.md"],
)
def test_a_file_name_that_fails_the_strict_pattern_is_refused(name):
    with pytest.raises(shims.DefinitionError):
        shims.definition_id(f"plugins/demo/agents/{name}", {"demo"})


@pytest.mark.parametrize("plugin", ["Demo", "de_mo", "two--hyphens", "-demo", "de.mo"])
def test_a_plugin_name_that_fails_the_strict_pattern_is_refused(plugin):
    with pytest.raises(shims.DefinitionError):
        shims.definition_id(f"plugins/{plugin}/agents/helper.md", {plugin})


def test_a_plugin_called_claude_is_refused_because_its_id_would_collide(repo, tmp_path):
    repo.write("plugins/claude/skills/x/SKILL.md", "---\nname: x\n---\n")
    repo.commit()
    with pytest.raises(shims.DefinitionError, match="claude"):
        shims.list_definitions(repo.path)
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_duplicate_id_fails_hard():
    with pytest.raises(shims.DefinitionError, match="more than one"):
        shims.assign_ids(["plugins/demo/agents/a.md", "plugins/demo/agents/a.md"], {"demo"})


@pytest.mark.parametrize(
    "path",
    [
        "plugins/demo/agents/sub/x.md",
        ".claude/agents/sub/x.md",
        "plugins/demo/agents/evals/notes.md",
        ".claude/agents/benchmarks/reviewer/case/README.md",
        "plugins/demo/agents/X.MD",
        "plugins/demo/agents/x.Md",
        ".claude/agents/UP.MD",
        "plugins/demo/agents/README.md",
        "plugins/demo/agents/readme.md",
        ".claude/agents/README.md",
        ".claude/agents/readme.md",
        "plugins/demo/commands/Run.MD",
        "plugins/demo/commands/sub/Run.Md",
    ],
)
@pytest.mark.parametrize("text", [AGENT, "# plain\n", "\ufeff---\nname: sneaky\n---\nBody.\n"])
def test_a_markdown_file_anywhere_under_agents_is_refused(repo, path, text):
    # Claude Code's plugin loader walks agents/ recursively and accepts any name ending in
    # .md in any case, with or without frontmatter, so each of these loads as a subagent
    # that the scan would never wrap if it were skipped.
    repo.write(path, text)
    repo.commit()
    with pytest.raises(shims.DefinitionError, match="not a subagent or command file|readme"):
        shims.list_definitions(repo.path)


def test_an_agents_readme_that_is_a_symlink_is_refused(repo):
    os.symlink("helper.md", repo.path / "plugins/demo/agents/readme.md")
    repo.commit()
    with pytest.raises(shims.DefinitionError, match="symbolic link"):
        shims.list_definitions(repo.path)


def test_a_tracked_symlink_is_refused(repo, tmp_path):
    os.symlink("helper.md", repo.path / "plugins/demo/agents/alias.md")
    repo.commit()
    with pytest.raises(shims.DefinitionError, match="symbolic link"):
        shims.list_definitions(repo.path)
    assert run(repo, tmp_path / "out", "--all") == 1
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir())


def test_a_definition_that_is_not_a_regular_file_on_disk_is_refused(repo, tmp_path, capsys):
    # Tracked as a regular file, replaced by a link in the working tree after checkout.
    # The link points at a file with valid frontmatter, so only the regular-file check
    # stands between it and being wrapped as though it were the definition.
    target = repo.path / "plugins/demo/agents/helper.md"
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text(AGENT + "PLANTED\n", encoding="utf-8")
    target.unlink()
    os.symlink(elsewhere, target)
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert "is not a regular file" in capsys.readouterr().err
    assert not out.exists()


def test_a_tracked_definition_missing_from_the_tree_is_refused(repo, tmp_path):
    (repo.path / "plugins/demo/agents/helper.md").unlink()
    assert run(repo, tmp_path / "out", "--all") == 1


def test_an_agent_shim_is_its_source_with_the_name_line_replaced_in_place(repo, tmp_path):
    # Cisco matches a suppression against the frontmatter name, so the shim carries its
    # globally unique id there. Same line count, so agent line numbers map 1:1.
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    shim = (out / "agent--demo--helper" / "SKILL.md").read_text(encoding="utf-8")
    assert shim == AGENT.replace("name: helper", "name: agent--demo--helper")
    assert shim.count("\n") == AGENT.count("\n")
    claude = (out / "agent--claude--builder" / "SKILL.md").read_text(encoding="utf-8")
    assert claude == AGENT.replace("name: helper", "name: agent--claude--builder")


def test_an_agent_name_with_odd_spacing_is_still_replaced_and_the_rest_is_untouched(repo, tmp_path):
    text = "---\nname :   helper  \ndescription: x\n---\nname: not frontmatter\n"
    repo.write("plugins/demo/agents/helper.md", text)
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    shim = (out / "agent--demo--helper" / "SKILL.md").read_text(encoding="utf-8")
    assert shim == text.replace("name :   helper  ", "name: agent--demo--helper", 1)


@pytest.mark.parametrize(
    "text",
    [
        "---\ndescription: no name\n---\n",
        "---\nname: a\nname: b\ndescription: two\n---\n",
        "---\ndescription: x\n---\nname: only in the body\n",
        "no frontmatter\nname: x\n",
        "---\nname: unterminated\n",
        "\n---\nname: leading blank line\n---\n",
    ],
)
def test_an_agent_without_exactly_one_frontmatter_name_is_refused(repo, tmp_path, text):
    repo.write("plugins/demo/agents/helper.md", text)
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert not out.exists()


def test_a_command_shim_gets_only_a_name_line_inserted_first_in_the_frontmatter(repo, tmp_path):
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    shim = (out / "command--demo--run-it" / "SKILL.md").read_text(encoding="utf-8")
    original = COMMAND.splitlines(keepends=True)
    assert shim.splitlines(keepends=True) == [
        original[0],
        "name: command--demo--run-it\n",
        *original[1:],
    ]
    # Removing the one inserted line gives the source back, byte for byte.
    assert shim.replace("name: command--demo--run-it\n", "", 1) == COMMAND


def test_a_shim_directory_holds_only_its_skill_file(repo, tmp_path):
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["map.tsv", *(shims.definition_id(p, {"demo"}) for p in LOCATIONS)]
    )
    for directory in out.iterdir():
        if directory.is_dir():
            assert [p.name for p in directory.iterdir()] == ["SKILL.md"]


def test_the_map_pairs_each_id_with_its_source_path(repo, tmp_path):
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == sorted(lines)
    assert lines == [
        "agent--claude--builder\t.claude/agents/builder.md\t0",
        "agent--demo--helper\tplugins/demo/agents/helper.md\t0",
        "command--claude--ship-it\t.claude/commands/ship-it.md\t1",
        "command--demo--run-it\tplugins/demo/commands/run-it.md\t1",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "no frontmatter at all\n",
        "---\r\ndescription: crlf\r\n---\r\n",
        "---\nname: already\ndescription: has a name\n---\n",
        "\n---\ndescription: leading blank line\n---\n",
    ],
)
def test_a_command_the_name_cannot_be_inserted_into_is_refused(repo, tmp_path, text):
    repo.write("plugins/demo/commands/run-it.md", text)
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_refused_command_does_not_leave_a_half_built_output(repo, tmp_path):
    repo.write("plugins/demo/commands/run-it.md", "no frontmatter\n")
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert not out.exists()


def test_an_output_directory_with_something_in_it_is_refused(repo, tmp_path):
    out = tmp_path / "out"
    (out / "stale").mkdir(parents=True)
    assert run(repo, out, "--all") == 1
    assert (out / "stale").is_dir()


def test_an_error_names_its_path_without_letting_it_open_a_workflow_command(repo, tmp_path, capsys):
    repo.write("plugins/demo/agents/Bad\n::error::forged.md", AGENT)
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1
    err = capsys.readouterr().err
    assert "forged" in err
    assert not any(line.lstrip().startswith("::") for line in err.splitlines())


def test_changed_selects_what_the_pull_request_touched(repo, tmp_path):
    base = repo.commit("base again")
    repo.write("plugins/demo/agents/helper.md", AGENT + "more\n")
    repo.write("plugins/demo/commands/new-one.md", COMMAND)
    repo.write("docs/agents/guide.md", "# edited\n")
    repo.write("plugins/demo/agents/evals/helper.json", '{"a": 1}\n')
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--changed", base) == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == [
        "agent--demo--helper\tplugins/demo/agents/helper.md\t0",
        "command--demo--new-one\tplugins/demo/commands/new-one.md\t1",
    ]
    assert sorted(p.name for p in out.iterdir() if p.is_dir()) == [
        "agent--demo--helper",
        "command--demo--new-one",
    ]


def test_changed_uses_the_merge_base_not_the_tip_of_the_base_branch(repo, tmp_path):
    fork = repo.commit("fork point")
    repo.git("switch", "--quiet", "-c", "topic")
    repo.write("plugins/demo/agents/helper.md", AGENT + "topic\n")
    repo.commit("topic")
    repo.git("switch", "--quiet", "main")
    repo.write(".claude/agents/builder.md", AGENT + "main moved on\n")
    tip = repo.commit("main moves")
    repo.git("switch", "--quiet", "topic")
    out = tmp_path / "out"
    assert run(repo, out, "--changed", tip) == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == ["agent--demo--helper\tplugins/demo/agents/helper.md\t0"]
    assert fork != tip


def test_changed_lists_a_renamed_definition_at_its_new_path(repo, tmp_path):
    base = repo.commit("base again")
    repo.git("mv", "plugins/demo/agents/helper.md", "plugins/demo/agents/renamed.md")
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--changed", base) == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == ["agent--demo--renamed\tplugins/demo/agents/renamed.md\t0"]


def test_changed_does_not_select_a_deleted_definition(repo, tmp_path):
    base = repo.commit("base again")
    repo.git("rm", "--quiet", "plugins/demo/agents/helper.md")
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--changed", base) == 0
    assert (out / "map.tsv").read_text(encoding="utf-8") == ""
    assert [p for p in out.iterdir()] == [out / "map.tsv"]


def test_changed_still_refuses_a_changed_file_with_a_bad_name(repo, tmp_path):
    base = repo.commit("base again")
    repo.write("plugins/demo/agents/Bad_Name.md", AGENT)
    repo.commit()
    assert run(repo, tmp_path / "out", "--changed", base) == 1


@pytest.mark.parametrize("base", ["", "HEAD", "main", "g" * 40, "A" * 40, "0" * 39, "-x"])
def test_changed_needs_a_full_lowercase_commit_id(repo, tmp_path, base):
    # The `=` form, so that a value starting with a hyphen reaches the script as a value.
    assert run(repo, tmp_path / "out", f"--changed={base}") == 1


def test_changed_refuses_a_real_commit_not_spelled_in_full_lowercase(repo, tmp_path):
    # Git resolves both of these to the commit, so only the script's own pattern refuses them.
    sha = repo.git("rev-parse", "HEAD")
    assert repo.git("rev-parse", "--verify", sha[:12]) == sha
    assert repo.git("rev-parse", "--verify", sha.upper()) == sha
    assert run(repo, tmp_path / "short", f"--changed={sha[:12]}") == 1
    assert run(repo, tmp_path / "upper", f"--changed={sha.upper()}") == 1
    assert run(repo, tmp_path / "full", f"--changed={sha}") == 0


def test_changed_with_an_unknown_commit_fails(repo, tmp_path):
    assert run(repo, tmp_path / "out", "--changed", "0" * 40) == 1


def test_a_mode_is_required():
    with pytest.raises(SystemExit):
        shims.main(["--out", "x"])


def test_the_summary_line_counts_what_was_written(repo, tmp_path, capsys):
    assert run(repo, tmp_path / "out", "--all") == 0
    assert capsys.readouterr().out.strip() == "4 definition(s) wrapped as shims"


NESTED = "plugins/demo/commands/release/notes.md"
NESTED_ID = "command--demo--release--notes"
DEEP = ".claude/commands/team/review/pr.md"
DEEP_ID = "command--claude--team--review--pr"


def test_a_nested_command_is_wrapped_with_its_folders_in_the_id(repo, tmp_path):
    repo.write(NESTED, COMMAND)
    repo.write(DEEP, COMMAND)
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert f"{NESTED_ID}\t{NESTED}\t1" in lines
    assert f"{DEEP_ID}\t{DEEP}\t1" in lines
    assert len(lines) == 6
    shim = (out / NESTED_ID / "SKILL.md").read_text(encoding="utf-8")
    assert shim.replace(f"name: {NESTED_ID}\n", "", 1) == COMMAND
    assert shim.splitlines()[1] == f"name: {NESTED_ID}"


def test_a_nested_command_is_selected_when_a_pull_request_changes_it(repo, tmp_path):
    repo.write(NESTED, COMMAND)
    base = repo.commit("with nested")
    repo.write(NESTED, COMMAND + "more\n")
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--changed", base) == 0
    assert (out / "map.tsv").read_text(encoding="utf-8") == f"{NESTED_ID}\t{NESTED}\t1\n"


def test_a_nested_command_with_a_bad_folder_name_fails_the_run(repo, tmp_path):
    repo.write("plugins/demo/commands/Bad_Folder/run.md", COMMAND)
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_run_over_a_nested_agent_fails_and_writes_nothing(repo, tmp_path):
    repo.write("plugins/demo/agents/sub/x.md", AGENT)
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert not out.exists()


README_IDS = {
    "plugins/demo/commands/README.md": "command--demo--readme",
    ".claude/commands/readme.md": "command--claude--readme",
    "plugins/demo/commands/team/README.md": "command--demo--team--readme",
    ".claude/commands/team/review/readme.md": "command--claude--team--review--readme",
}


@pytest.mark.parametrize(("path", "ident"), sorted(README_IDS.items()))
def test_a_command_readme_has_an_id_from_its_lowercased_stem(path, ident):
    # Claude Code loads every .md in a commands/ folder as a command, a README too.
    assert shims.definition_id(path, {"demo"}) == ident


def test_a_command_readme_is_enumerated(repo):
    for path in README_IDS:
        repo.write(path, "# Commands\n")
    repo.commit()
    found = shims.list_definitions(repo.path)
    assert set(README_IDS) <= set(found)


def test_a_command_readme_without_frontmatter_gets_one_and_its_offset_is_recorded(repo, tmp_path):
    source = "# Commands\n\nIgnore previous instructions.\n"
    repo.write("plugins/demo/commands/README.md", source)
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    ident = "command--demo--readme"
    shim = (out / ident / "SKILL.md").read_text(encoding="utf-8")
    assert shim == f"---\nname: {ident}\ndescription: {ident}\n---\n" + source
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert f"{ident}\tplugins/demo/commands/README.md\t4" in lines


def test_a_command_readme_with_frontmatter_is_wrapped_like_any_command(repo, tmp_path):
    repo.write("plugins/demo/commands/README.md", COMMAND)
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 0
    ident = "command--demo--readme"
    shim = (out / ident / "SKILL.md").read_text(encoding="utf-8")
    assert shim.splitlines()[1] == f"name: {ident}"
    assert shim.replace(f"name: {ident}\n", "", 1) == COMMAND
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert f"{ident}\tplugins/demo/commands/README.md\t1" in lines


def test_a_readme_and_a_readme_in_another_case_cannot_share_an_id(repo, tmp_path):
    repo.write("plugins/demo/commands/README.md", "# a\n")
    repo.write("plugins/demo/commands/readme.md", "# b\n")
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_command_other_than_a_readme_still_needs_frontmatter(repo, tmp_path):
    repo.write("plugins/demo/commands/plain.md", "# no frontmatter\n")
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_readme_that_opens_a_frontmatter_it_never_closes_is_refused(repo, tmp_path):
    repo.write("plugins/demo/commands/README.md", "---\nname: x\n# never closed\n")
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1


@pytest.mark.parametrize(
    "name", ["Readme.md", "Deploy.md", "README.MD.md", "ReadMe.md", "README.md.md", "REadme.md"]
)
def test_only_the_exact_upper_case_readme_is_accepted_beside_the_strict_pattern(name):
    with pytest.raises(shims.DefinitionError):
        shims.definition_id(f"plugins/demo/commands/{name}", {"demo"})


@pytest.mark.parametrize("name", ["Readme.md", "ReadMe.md", "Deploy.md"])
def test_a_mis_cased_command_name_is_refused_on_its_own(name):
    # One name per case, so accepting any single spelling fails exactly this case.
    with pytest.raises(shims.DefinitionError, match="not a subagent or command file"):
        shims.definition_id(f"plugins/demo/commands/{name}", {"demo"})


@pytest.mark.parametrize("path", ["plugins/demo/agents/extra", "plugins/demo/commands/extra"])
@pytest.mark.parametrize("mode", ["all", "changed"])
def test_a_gitlink_under_agents_or_commands_is_refused(repo, tmp_path, capsys, path, mode):
    base = repo.git("rev-parse", "HEAD")
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{base},{path}")
    repo.git("commit", "--quiet", "-m", "submodule")
    args = ["--all"] if mode == "all" else ["--changed", base]
    out = tmp_path / "out"
    assert run(repo, out, *args) == 1
    assert "submodule" in capsys.readouterr().err
    assert not out.exists()


def test_a_gitlink_elsewhere_under_claude_is_refused(repo, tmp_path):
    base = repo.git("rev-parse", "HEAD")
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{base},.claude/rules/extra")
    repo.git("commit", "--quiet", "-m", "submodule")
    assert run(repo, tmp_path / "out", "--all") == 1


def test_a_path_cannot_open_the_legacy_workflow_command_marker(repo, tmp_path, capsys):
    repo.write("plugins/demo/agents/Bad##[warning]x.md", AGENT)
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1
    err = capsys.readouterr().err
    assert "##[" not in err
    assert "## [warning]" in err


def test_two_commands_cannot_share_an_id(tmp_path):
    # `a/b-c.md` and `a-b/c.md` give different ids; the same path twice is what repeats one.
    ids = shims.assign_ids(
        ["plugins/demo/commands/a/b-c.md", "plugins/demo/commands/a-b/c.md"], {"demo"}
    )
    assert sorted(ids) == ["command--demo--a--b-c", "command--demo--a-b--c"]
    with pytest.raises(shims.DefinitionError, match="more than one"):
        shims.assign_ids(["plugins/demo/commands/a/b.md"] * 2, {"demo"})


@pytest.mark.parametrize(
    "extra",
    ["? name\n: spoofed\n", "'name': spoofed\n", '"name": spoofed\n', "? name\n"],
)
@pytest.mark.parametrize(
    "path,base",
    [
        ("plugins/demo/agents/helper.md", "---\nname: helper\n{extra}description: x\n---\n"),
        ("plugins/demo/commands/run-it.md", "---\n{extra}description: x\n---\n"),
    ],
)
def test_a_name_spelled_as_a_complex_or_quoted_key_is_refused(
    repo, tmp_path, extra, path, base, capsys
):
    # A loader lets the later spelling win, which would borrow another shim's suppression.
    # The repository parser refuses these lines too, so the message is what shows that the
    # indicator check itself fired and would still hold the day the parser models the keys.
    repo.write(path, base.replace("{extra}", extra))
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert "complex, quoted or indicator-led key" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(
    "char",
    ["\r", "\x85", " ", " ", "\x00", "\x0b", "\x0c", "\x1b", "\x1f"],
)
@pytest.mark.parametrize(
    "path,base",
    [
        ("plugins/demo/agents/helper.md", "---\nname: helper\ndescription: a{c}b\n---\n"),
        ("plugins/demo/commands/run-it.md", "---\ndescription: a{c}b\n---\n"),
    ],
)
def test_a_line_break_or_control_character_in_frontmatter_is_refused(
    repo, tmp_path, char, path, base
):
    # YAML breaks lines on these where the repository's own parser does not, so a second
    # `name` could be read by Cisco but not here and borrow another shim's suppression.
    repo.write(path, base.replace("{c}", char))
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert not out.exists()


def test_a_carriage_return_in_the_body_is_still_allowed(repo, tmp_path):
    repo.write("plugins/demo/agents/helper.md", "---\nname: helper\ndescription: x\n---\nBody\r\n")
    assert run(repo, tmp_path / "out", "--all") == 0


@pytest.mark.parametrize("prefix", ["!", "&", "*", "{", "["])
@pytest.mark.parametrize(
    "path,base",
    [
        ("plugins/demo/agents/helper.md", "---\nname: helper\n{extra}description: x\n---\n"),
        ("plugins/demo/commands/run-it.md", "---\n{extra}description: x\n---\n"),
    ],
)
def test_a_frontmatter_line_opening_with_a_yaml_indicator_is_refused(
    repo, tmp_path, prefix, path, base, capsys
):
    repo.write(path, base.replace("{extra}", f"{prefix}name: spoofed\n"))
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert "complex, quoted or indicator-led key" in capsys.readouterr().err
    assert not out.exists()


def test_a_shim_whose_name_is_not_its_id_is_refused():
    # Nothing the repository parser accepts can reach this today, so the check is called
    # directly: it is the last guarantee that a shim loads under its own id.
    text = b"---\nname: agent--demo--other\ndescription: x\n---\n"
    with pytest.raises(shims.DefinitionError, match="other than its shim id"):
        shims.confirm_name("agent--demo--helper", "p", text)
    shims.confirm_name("agent--demo--other", "p", text)


# Claude Code loads a definition from wherever a manifest points, not only from the four
# default places, so the run fails closed on every manifest shape that could do that.
GOOD_MARKETPLACE = {"plugins": [{"name": "demo", "source": "./plugins/demo"}]}
GOOD_PLUGIN = {"name": "demo", "description": "x"}


def write_manifests(repo, marketplace=GOOD_MARKETPLACE, plugin=GOOD_PLUGIN):
    repo.write(".claude-plugin/marketplace.json", json.dumps(marketplace))
    repo.write("plugins/demo/.claude-plugin/plugin.json", json.dumps(plugin))
    repo.commit("manifests")


def test_ordinary_manifests_are_accepted(repo):
    write_manifests(repo)
    assert shims.list_definitions(repo.path) == sorted(LOCATIONS)


@pytest.mark.parametrize("key", ["agents", "commands", "skills", "hooks"])
def test_a_plugin_manifest_that_adds_components_is_refused(repo, key):
    # `"agents": ["./extra/evil.md"]` loads a file the scan never enumerates.
    write_manifests(repo, plugin={**GOOD_PLUGIN, key: ["./extra/evil.md"]})
    with pytest.raises(shims.DefinitionError, match=rf"plugin\.json.*`{key}`"):
        shims.list_definitions(repo.path)


@pytest.mark.parametrize("key", ["agents", "commands", "skills", "hooks"])
def test_a_marketplace_entry_that_adds_components_is_refused(repo, key):
    entry = {"name": "demo", "source": "./plugins/demo", key: {"inline": "content"}}
    write_manifests(repo, marketplace={"plugins": [entry]})
    with pytest.raises(shims.DefinitionError, match=rf"marketplace\.json.*`{key}`"):
        shims.list_definitions(repo.path)


@pytest.mark.parametrize(
    "source",
    [
        "./tools/zz",
        "plugins/demo",
        "./plugins/demo/sub",
        "./plugins/Demo",
        "../plugins/demo",
        7,
        None,
    ],
)
def test_a_marketplace_source_outside_plugins_is_refused(repo, source):
    write_manifests(repo, marketplace={"plugins": [{"name": "zz", "source": source}]})
    with pytest.raises(shims.DefinitionError, match=r"marketplace\.json.*source"):
        shims.list_definitions(repo.path)


@pytest.mark.parametrize(
    "path",
    [
        "tools/zz/.claude-plugin/plugin.json",
        "plugins/demo/nested/.claude-plugin/plugin.json",
        "plugins/demo/.claude-plugin/extra.json",
        "plugins/Bad_Name/.claude-plugin/plugin.json",
    ],
)
def test_a_manifest_in_an_unexpected_place_is_refused(repo, path):
    write_manifests(repo)
    repo.write(path, json.dumps(GOOD_PLUGIN))
    repo.commit("stray manifest")
    with pytest.raises(shims.DefinitionError, match="manifest"):
        shims.list_definitions(repo.path)


@pytest.mark.parametrize("text", ["{", "[]", '{"plugins": 3}', '{"plugins": [3]}'])
def test_a_marketplace_that_cannot_be_read_is_refused(repo, text):
    repo.write(".claude-plugin/marketplace.json", text)
    repo.commit("bad marketplace")
    with pytest.raises(shims.DefinitionError, match="marketplace"):
        shims.list_definitions(repo.path)


@pytest.mark.parametrize("text", ["{", "[]"])
def test_a_plugin_manifest_that_cannot_be_read_is_refused(repo, text):
    repo.write("plugins/demo/.claude-plugin/plugin.json", text)
    repo.commit("bad plugin manifest")
    with pytest.raises(shims.DefinitionError, match="plugin.json"):
        shims.list_definitions(repo.path)


def test_a_refused_manifest_fails_the_run_and_writes_nothing(repo, tmp_path):
    write_manifests(repo, plugin={**GOOD_PLUGIN, "agents": ["./extra/evil.md"]})
    out = tmp_path / "out"
    assert run(repo, out, "--all") == 1
    assert not out.exists()


@pytest.mark.parametrize("mode", ["all", "changed"])
@pytest.mark.parametrize(
    "link",
    ["plugins/demo/agents/sub", "plugins/demo/skills/notes.txt", "docs/pointer"],
)
def test_any_symlink_is_refused_wherever_it_sits(repo, tmp_path, capsys, link, mode):
    # A directory link below agents/, a non-.md link under skills/ and one outside plugins/
    # and .claude/ all fail: LOCATION_RE would let the first two through.
    base = repo.git("rev-parse", "HEAD")
    (repo.path / link).parent.mkdir(parents=True, exist_ok=True)
    os.symlink("helper.md", repo.path / link)
    repo.commit("link")
    args = ["--all"] if mode == "all" else ["--changed", base]
    out = tmp_path / "out"
    assert run(repo, out, *args) == 1
    assert "symbolic link" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("mode", ["all", "changed"])
def test_a_gitlink_standing_in_for_the_manifest_directory_is_refused(repo, tmp_path, capsys, mode):
    base = repo.git("rev-parse", "HEAD")
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{base},.claude-plugin")
    repo.git("commit", "--quiet", "-m", "submodule")
    args = ["--all"] if mode == "all" else ["--changed", base]
    out = tmp_path / "out"
    assert run(repo, out, *args) == 1
    assert "submodule" in capsys.readouterr().err
    assert not out.exists()


def test_a_frontmatter_error_cannot_open_the_legacy_workflow_command_marker(repo, tmp_path, capsys):
    repo.write("plugins/demo/agents/odd.md", "---\nname: odd\nbad ##[warning] line\n---\nBody.\n")
    repo.commit()
    assert run(repo, tmp_path / "out", "--all") == 1
    err = capsys.readouterr().err
    assert "frontmatter does not parse" in err
    assert "##[" not in err
    assert "## [warning]" in err
