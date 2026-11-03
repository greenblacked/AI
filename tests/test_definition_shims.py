"""`scripts/definition_shims.py`: wrapping a subagent or command as a one-file skill.

Neither skill scanner has an agent or command type, so the `security.yml` scan jobs read
each definition through a shim. These cases build a small git repository, because the
script enumerates with `git ls-files`, and pin the three things a mistake would make
silent: which files are scanned, what the shim's id is (Cisco suppressions key on it),
and that a refused file fails the run rather than going unscanned.
"""

from __future__ import annotations

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
    "plugins/demo/agents/evals/notes.md": "# not a definition\n",
    ".claude/agents/benchmarks/reviewer/case/change.patch": "+x\n",
    ".claude/agents/benchmarks/reviewer/case/README.md": "# a case\n",
    ".claude/agents/evals/builder.json": "{}\n",
    "plugins/demo/agents/notes.txt": "text\n",
    "plugins/demo/skills/alpha/SKILL.md": "---\nname: alpha\n---\n",
    "plugins/demo/skills/alpha/agents/inner.md": "# nested\n",
    "docs/agents/guide.md": "# docs\n",
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
    # Path.glob's `*` never crosses a slash, so this is a second opinion on the exact
    # depth-one rule, not a copy of the script's regex.
    expected = set()
    for pattern in (
        "plugins/*/agents/*.md",
        "plugins/*/commands/*.md",
        ".claude/agents/*.md",
        ".claude/commands/*.md",
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
        "plugins/demo/agents/helper.json",
        "agents/helper.md",
    ],
)
def test_a_path_outside_the_four_locations_is_refused(path):
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


def test_a_tracked_symlink_is_refused(repo, tmp_path):
    os.symlink("helper.md", repo.path / "plugins/demo/agents/alias.md")
    repo.commit()
    with pytest.raises(shims.DefinitionError, match="symbolic link"):
        shims.list_definitions(repo.path)
    assert run(repo, tmp_path / "out", "--all") == 1
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").iterdir())


def test_a_definition_that_is_not_a_regular_file_on_disk_is_refused(repo, tmp_path):
    # Tracked as a regular file, replaced by a link in the working tree after checkout.
    target = repo.path / "plugins/demo/agents/helper.md"
    target.unlink()
    os.symlink("/etc/hostname", target)
    assert run(repo, tmp_path / "out", "--all") == 1


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
        "agent--claude--builder\t.claude/agents/builder.md",
        "agent--demo--helper\tplugins/demo/agents/helper.md",
        "command--claude--ship-it\t.claude/commands/ship-it.md",
        "command--demo--run-it\tplugins/demo/commands/run-it.md",
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
        "agent--demo--helper\tplugins/demo/agents/helper.md",
        "command--demo--new-one\tplugins/demo/commands/new-one.md",
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
    assert lines == ["agent--demo--helper\tplugins/demo/agents/helper.md"]
    assert fork != tip


def test_changed_lists_a_renamed_definition_at_its_new_path(repo, tmp_path):
    base = repo.commit("base again")
    repo.git("mv", "plugins/demo/agents/helper.md", "plugins/demo/agents/renamed.md")
    repo.commit()
    out = tmp_path / "out"
    assert run(repo, out, "--changed", base) == 0
    lines = (out / "map.tsv").read_text(encoding="utf-8").splitlines()
    assert lines == ["agent--demo--renamed\tplugins/demo/agents/renamed.md"]


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


def test_changed_with_an_unknown_commit_fails(repo, tmp_path):
    assert run(repo, tmp_path / "out", "--changed", "0" * 40) == 1


def test_a_mode_is_required():
    with pytest.raises(SystemExit):
        shims.main(["--out", "x"])


def test_the_summary_line_counts_what_was_written(repo, tmp_path, capsys):
    assert run(repo, tmp_path / "out", "--all") == 0
    assert capsys.readouterr().out.strip() == "4 definition(s) wrapped as shims"
