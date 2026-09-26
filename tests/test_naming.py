"""The check that files, branches, commit subjects and pull request titles follow this
repository's naming conventions.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import load_script

naming = load_script("check_naming.py")


def git(repo, *args, env=None):
    result = subprocess.run(  # noqa: S603 - fixed argv, test fixture only
        ["git", *args],  # noqa: S607 - resolved against PATH like every other git call here
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result


@pytest.fixture
def repo(tmp_path):
    directory = tmp_path / "repo"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    git(directory, "config", "user.name", "Test User")
    git(directory, "config", "user.email", "test@example.com")
    (directory / "README.md").write_text("# repo\n", encoding="utf-8")
    git(directory, "add", "README.md")
    git(directory, "commit", "-q", "-m", "Initial commit")
    git(directory, "tag", "base")
    return directory


def commit(repo, message, *, author=None, parents=None):
    """One commit carrying `message`, written through -F so nothing about the message
    ever appears as a literal argument on a command line. `parents` merges the named
    refs in as extra parents, for building a merge commit to exempt."""
    path = repo / "message.txt"
    path.write_text(message, encoding="utf-8")
    env = os.environ.copy()
    if author:
        env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = author
    if parents:
        git(repo, "merge", "-q", "--no-ff", "-F", str(path), *parents, env=env)
    else:
        git(repo, "commit", "-q", "--allow-empty", "-F", str(path), env=env)
    path.unlink(missing_ok=True)


# --- a clean range ------------------------------------------------------------------


def test_a_clean_range_passes(repo, capsys):
    commit(repo, "Add a feature")
    assert naming.check(repo, "base..HEAD") == 0
    assert "carry no naming problems" in capsys.readouterr().out


def test_an_empty_range_passes(repo, capsys):
    assert naming.check(repo, "base..HEAD") == 0
    assert "0 commit(s) checked" in capsys.readouterr().out


def test_no_range_skips_commit_and_branch_checks(repo, capsys):
    # A push to main or a merge group has no base ref or PR title to check against, so
    # `commit_range=None` only runs the file-naming checks.
    commit(repo, "fixed a typo")  # would fail the imperative-mood check, if checked
    assert naming.check(repo) == 0
    assert "carry no naming problems" in capsys.readouterr().out


# --- commit subject rules -------------------------------------------------------------


def test_subject_problems_finds_nothing_wrong_with_an_ordinary_subject():
    assert naming.subject_problems("Add a feature") == []


def test_subject_problems_ignores_an_empty_subject():
    assert naming.subject_problems("") == []
    assert naming.subject_problems("   ") == []


@pytest.mark.parametrize("marker", ["WIP", "fixup!", "squash!", "amend!"])
def test_a_work_in_progress_marker_fails(marker):
    problems = naming.subject_problems(f"{marker} add a feature")
    assert any("work-in-progress marker" in p for p in problems)


def test_wip_only_matches_on_a_word_boundary():
    # "WIP" is checked as a word, not a substring, so a subject that merely contains
    # those three letters inside a longer word is not a work-in-progress marker.
    problems = naming.subject_problems("Add WIPE support")
    assert not any("work-in-progress marker" in p for p in problems)


def test_wip_as_its_own_word_still_fails():
    problems = naming.subject_problems("WIP: thing")
    assert any("work-in-progress marker" in p for p in problems)


def test_a_subject_over_72_characters_fails():
    subject = "A" + "x" * 80
    problems = naming.subject_problems(subject)
    assert any("over 72" in p for p in problems)


def test_a_trailing_pr_number_is_excluded_from_the_length():
    # 72 characters of subject plus a squash-merge-appended " (#1234)" still passes,
    # because the suffix is not something the author chose to fit inside the column.
    subject = "A" * 72 + " (#1234)"
    assert naming.subject_problems(subject) == []


def test_a_subject_just_over_72_after_stripping_the_suffix_fails():
    subject = "A" * 73 + " (#1234)"
    problems = naming.subject_problems(subject)
    assert any("over 72" in p for p in problems)


def test_a_lowercase_subject_fails():
    problems = naming.subject_problems("add a feature")
    assert any("capital letter" in p for p in problems)


def test_a_trailing_period_fails():
    problems = naming.subject_problems("Add a feature.")
    assert any("trailing period" in p for p in problems)


@pytest.mark.parametrize(
    "subject",
    [
        "Added a feature",
        "Adds a feature",
        "Fixed a bug",
        "Fixes a bug",
        "Updated the docs",
        "Updates the docs",
        "Removed the file",
        "Renamed the module",
        "Implemented the check",
    ],
)
def test_a_past_or_third_person_opening_verb_fails(subject):
    problems = naming.subject_problems(subject)
    assert any("not the imperative mood" in p for p in problems)


@pytest.mark.parametrize(
    "subject",
    [
        "Add a feature",
        "Make the build faster",
        "Split the plugin in two",  # "Split" is not on the banned list — ambiguous tense
        "Document the API",
        "Enable the flag",
    ],
)
def test_an_imperative_subject_passes(subject):
    assert naming.subject_problems(subject) == []


@pytest.mark.parametrize(
    "subject",
    [
        "feat: add a feature",
        "fix(scope): correct the count",
        "docs: update the guide",
        "ci!: bump the pin",
    ],
)
def test_a_conventional_commits_prefix_fails(subject):
    problems = naming.subject_problems(subject)
    assert any("Conventional Commits type prefix" in p for p in problems)


def test_a_type_prefix_is_not_also_reported_as_an_imperative_mood_failure():
    # "fix:" would also read as a lowercase-first-word violation of the capital-letter
    # rule, and "fix" is not itself in the banned-verb list — the type-prefix message is
    # the specific one, so it should not additionally claim a banned opening verb.
    problems = naming.subject_problems("fix: correct the count")
    assert not any("not the imperative mood" in p for p in problems)


# --- exemptions: merges and Dependabot -------------------------------------------------


def test_a_merge_commit_is_exempt(repo, capsys):
    git(repo, "checkout", "-q", "-b", "topic")
    commit(repo, "Add a feature on the topic branch")
    git(repo, "checkout", "-q", "main")
    commit(repo, "unrelated main commit")
    commit(repo, "merged topic into main", parents=["topic"])
    # The merge commit's own subject ("merged topic into main") would fail the
    # imperative-mood check if it were not exempt for having two parents.
    assert naming.check(repo, "base..HEAD") == 1  # the non-merge "unrelated main commit"
    out = capsys.readouterr().out
    assert "merged topic into main" not in out


def test_a_dependabot_author_is_exempt(repo, capsys):
    commit(repo, "bumped a dependency", author=("dependabot[bot]", "support@github.com"))
    assert naming.check(repo, "base..HEAD") == 0
    assert "carry no naming problems" in capsys.readouterr().out


def test_a_dependabot_branch_exempts_every_commit_on_it(repo, capsys):
    commit(repo, "bumped a dependency")  # would fail on its own
    assert naming.check(repo, "base..HEAD", branch="dependabot/pip/foo-1.2.3") == 0
    assert "carry no naming problems" in capsys.readouterr().out


def test_a_dependabot_branch_also_exempts_the_pull_request_title(repo, capsys):
    assert (
        naming.check(
            repo,
            "base..HEAD",
            branch="dependabot/pip/foo-1.2.3",
            pr_title="bump foo from 1 to 2",
        )
        == 0
    )


# --- the pull request title -----------------------------------------------------------


def test_a_bad_pull_request_title_fails(repo, capsys):
    assert naming.check(repo, "base..HEAD", pr_title="fixed the thing") == 1
    out = capsys.readouterr().out
    assert "pull request title" in out


def test_a_good_pull_request_title_passes(repo, capsys):
    assert naming.check(repo, "base..HEAD", pr_title="Fix the thing") == 0


# --- branch names: the `<type>/<short-kebab-description>` shape ----------------------


@pytest.mark.parametrize(
    "branch",
    [
        "feat/subagent-handoff-lines",
        "fix/dead-gcp-snapshot-link",
        "chore/project-hygiene",
        "docs/code-of-conduct",
        "ci/dependabot-auto-merge-and-attribution",
        "test/attribution-branch-shape",
    ],
)
def test_each_allowed_prefix_passes(branch):
    assert naming.branch_problem(branch) is None


@pytest.mark.parametrize(
    "branch",
    [
        "ci/bump-codeql-action-4.37.9",
        "fix/py3.13-compat",
        "chore/release-1.2.0",
    ],
)
def test_a_dot_between_digits_passes(branch):
    # A version number reads as one rather than as a second kind of separator, so long
    # as the dot sits between two digits.
    assert naming.branch_problem(branch) is None


@pytest.mark.parametrize(
    "branch",
    [
        "feat/foo.bar",  # a dot between letters, not digits
        "feat/a..b",  # a bare double dot
    ],
)
def test_a_dot_not_between_digits_fails(branch):
    problem = naming.branch_problem(branch)
    assert problem is not None
    assert "CONTRIBUTING.md#naming-a-branch" in problem


@pytest.mark.parametrize(
    "branch",
    [
        "feat/Add-Thing",  # uppercase
        "feat/add_thing",  # underscore
        "feat/add/thing",  # nested slash
        "feat/",  # empty description
    ],
)
def test_a_malformed_description_fails(branch):
    problem = naming.branch_problem(branch)
    assert problem is not None
    assert "CONTRIBUTING.md#naming-a-branch" in problem


def test_a_missing_prefix_fails():
    problem = naming.branch_problem("add-a-thing")
    assert problem is not None
    assert "CONTRIBUTING.md#naming-a-branch" in problem


def test_a_dependabot_branch_passes():
    assert naming.branch_problem("dependabot/pip/foo-1.2.3") is None


def test_main_and_detached_head_pass():
    assert naming.branch_problem("main") is None
    assert naming.branch_problem("HEAD") is None


def test_no_branch_is_not_a_finding():
    assert naming.branch_problem(None) is None
    assert naming.branch_problem("") is None


def test_contributing_lists_exactly_the_allowed_prefixes():
    # Moved from tests/test_attribution.py along with the shape check itself: one script
    # owns the `<type>/` convention now, so this is the one place the CONTRIBUTING table
    # is checked against the constant it must not drift from.
    contributing = (Path(__file__).resolve().parent.parent / "CONTRIBUTING.md").read_text(
        encoding="utf-8"
    )
    table = contributing.split("## Naming a branch", 1)[1].split("## Commits", 1)[0]
    documented = set(re.findall(r"^\| `([a-z]+)/`", table, re.MULTILINE))
    assert documented == set(naming._BRANCH_TYPES)


def test_contributing_prints_the_same_description_pattern_check_naming_enforces():
    # CONTRIBUTING.md prints the shape as a literal string for a reader; this ties that
    # string to the constant the check actually runs, so a change to one cannot silently
    # stop matching the other.
    contributing = (Path(__file__).resolve().parent.parent / "CONTRIBUTING.md").read_text(
        encoding="utf-8"
    )
    table = contributing.split("## Naming a branch", 1)[1].split("## Commits", 1)[0]
    printed = re.search(r"`\[a-z0-9\]\+\(\?:[^`]+\)\*`", table)
    assert printed is not None
    assert printed.group(0).strip("`") == naming._BRANCH_DESCRIPTION_RE_TEXT


# --- file and folder names -------------------------------------------------------------


def test_a_kebab_case_skill_directory_passes():
    assert naming.file_naming_problems(["plugins/coding/skills/code-review/SKILL.md"]) == []


def test_an_underscore_skill_directory_fails():
    problems = naming.file_naming_problems(["plugins/coding/skills/code_review/SKILL.md"])
    assert any("skill directory" in p for p in problems)


def test_a_skill_directory_is_only_reported_once_across_its_files():
    paths = [
        "plugins/coding/skills/code_review/SKILL.md",
        "plugins/coding/skills/code_review/references/checklist.md",
    ]
    problems = naming.file_naming_problems(paths)
    assert sum("skill directory" in p for p in problems) == 1


@pytest.mark.parametrize(
    "path",
    [
        "plugins/coding/agents/skill_reviewer.md",
        ".claude/agents/skill_reviewer.md",
    ],
)
def test_an_underscore_agent_file_fails(path):
    problems = naming.file_naming_problems([path])
    assert any("agent file" in p for p in problems)


def test_a_kebab_case_agent_file_passes():
    assert naming.file_naming_problems(["plugins/coding/agents/skill-reviewer.md"]) == []


@pytest.mark.parametrize(
    "path",
    [
        "plugins/security/commands/blast_radius.md",
        ".claude/commands/skill_gap.md",
    ],
)
def test_an_underscore_command_file_fails(path):
    problems = naming.file_naming_problems([path])
    assert any("command file" in p for p in problems)


def test_an_underscore_reference_fails():
    problems = naming.file_naming_problems(
        ["plugins/coding/skills/code-review/references/review_templates.md"]
    )
    assert any("reference" in p for p in problems)


def test_an_underscore_evals_json_fails():
    problems = naming.file_naming_problems(
        ["plugins/coding/skills/code-review/evals/trigger_eval.json"]
    )
    assert any("eval set" in p for p in problems)


def test_an_underscore_doc_fails():
    problems = naming.file_naming_problems(["docs/writing_skills.md"])
    assert any("doc" in p for p in problems)


def test_a_kebab_case_doc_passes():
    assert naming.file_naming_problems(["docs/writing-skills.md"]) == []


def test_a_camel_case_workflow_fails():
    problems = naming.file_naming_problems([".github/workflows/ciWorkflow.yml"])
    assert any("workflow" in p and "kebab-case" in p for p in problems)


def test_a_yaml_extension_workflow_fails():
    problems = naming.file_naming_problems([".github/workflows/ci.yaml"])
    assert any(".yaml" in p for p in problems)


def test_a_yml_extension_workflow_passes():
    assert naming.file_naming_problems([".github/workflows/ci.yml"]) == []


@pytest.mark.parametrize(
    "path",
    [
        "scripts/checkNaming.py",
        "src/skillcheck/badName.py",
        "tests/testNaming.py",
    ],
)
def test_a_non_snake_case_python_module_fails(path):
    problems = naming.file_naming_problems([path])
    assert any("snake_case" in p for p in problems)


def test_a_snake_case_python_module_passes():
    assert naming.file_naming_problems(["scripts/check_naming.py"]) == []


def test_a_test_module_without_the_test_prefix_fails():
    problems = naming.file_naming_problems(["tests/naming_helpers.py"])
    assert any("does not start with `test_`" in p for p in problems)


def test_conftest_is_not_required_to_start_with_test():
    assert naming.file_naming_problems(["tests/conftest.py"]) == []


def test_a_nested_test_helper_is_not_required_to_start_with_test():
    # tests/fixtures/generate_block_scalars.py: snake_case is enough for a file that
    # pytest never collects as a test module in its own right.
    assert naming.file_naming_problems(["tests/fixtures/generate_block_scalars.py"]) == []


def test_dunder_python_files_are_exempt():
    assert naming.file_naming_problems(["src/skillcheck/__init__.py"]) == []
    assert naming.file_naming_problems(["src/skillcheck/__main__.py"]) == []


def test_a_snake_case_shell_script_passes():
    assert naming.file_naming_problems(["scripts/bisect_probe.sh"]) == []


def test_a_kebab_case_shell_script_passes():
    assert naming.file_naming_problems(["scripts/bisect-probe.sh"]) == []


def test_a_mixed_case_shell_script_fails():
    problems = naming.file_naming_problems(["scripts/Bisect-Probe.sh"])
    assert any("shell script" in p for p in problems)


def test_allowed_basenames_are_never_flagged():
    paths = [
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "LICENSE",
        "NOTICE",
        "template/SKILL.md",
        "Makefile",
        ".github/pull_request_template.md",
        "src/skillcheck/__init__.py",
        "src/skillcheck/__main__.py",
        "tests/conftest.py",
    ]
    assert naming.file_naming_problems(paths) == []


def test_dotfiles_and_dot_directories_are_never_flagged():
    assert naming.file_naming_problems([".editorconfig", ".yamllint.yaml"]) == []
    assert naming.file_naming_problems([".github/ISSUE_TEMPLATE/bug.yml"]) == []


def test_a_path_matching_no_category_is_not_a_finding():
    assert naming.file_naming_problems(["listing-budget.json", "providers.json"]) == []


# --- git plumbing and error handling ---------------------------------------------------


def test_git_binary_resolves_to_an_absolute_path():
    path = naming.git_binary()
    assert path is not None
    assert os.path.isabs(path)


def test_git_binary_is_none_when_git_is_not_on_path(monkeypatch):
    monkeypatch.setattr(naming.shutil, "which", lambda name: None)
    assert naming.git_binary() is None


def test_check_reports_rather_than_raises_when_git_is_missing(repo, monkeypatch, capsys):
    monkeypatch.setattr(naming, "git_binary", lambda: None)
    assert naming.check(repo) == 2
    assert "git is not on PATH" in capsys.readouterr().err


def test_check_reports_an_unreadable_range_rather_than_raising(repo, capsys):
    assert naming.check(repo, "not-a-real-ref..HEAD") == 2
    assert "could not read commits in range" in capsys.readouterr().out


def test_commits_in_skips_a_record_with_the_wrong_field_count(repo, monkeypatch):
    git_path = naming.git_binary()

    class FakeResult:
        returncode = 0
        stdout = "only-one-field\x1e\n"
        stderr = ""

    monkeypatch.setattr(
        naming.subprocess,
        "run",
        lambda *a, **k: FakeResult(),  # noqa: ARG005
    )
    assert naming.commits_in(repo, "base..HEAD", git_path) == []


def test_tracked_files_reports_rather_than_raises_on_a_bad_repo(tmp_path):
    git_path = naming.git_binary()
    with pytest.raises(ValueError, match="failed|not a git repository"):
        naming.tracked_files(tmp_path, git_path)


def test_check_reports_rather_than_raises_when_tracked_files_cannot_be_listed(tmp_path, capsys):
    # Not a git repository at all, so `git ls-files` fails before any commit range is
    # ever read.
    assert naming.check(tmp_path) == 2
    assert "could not list tracked files" in capsys.readouterr().out


# --- main() and its environment ------------------------------------------------------


def test_main_defaults_to_files_only_with_no_range_flag(repo, monkeypatch):
    captured = {}

    def fake_check(root, commit_range, **kwargs):
        captured["range"] = commit_range
        return 0

    monkeypatch.setattr(naming, "check", fake_check)
    assert naming.main([str(repo)]) == 0
    assert captured["range"] is None


def test_main_reads_the_range_flag(repo):
    assert naming.main([str(repo), "--range", "base..HEAD"]) == 0


def test_main_reads_pull_request_and_branch_context_from_the_environment(repo, monkeypatch):
    monkeypatch.setenv("GITHUB_HEAD_REF", "add-a-thing")
    monkeypatch.setenv("PR_TITLE", "fixed the thing")
    assert naming.main([str(repo), "--range", "base..HEAD"]) == 1


def test_main_with_clean_environment_passes(repo, monkeypatch):
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.delenv("PR_TITLE", raising=False)
    assert naming.main([str(repo), "--range", "base..HEAD"]) == 0
