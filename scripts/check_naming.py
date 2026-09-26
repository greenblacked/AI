#!/usr/bin/env python3
"""Fail on a naming-convention violation this repository has decided to enforce.

Four families, one job, so a contributor has one place to look rather than four:

- **File and folder names.** Every tracked file (`git ls-files`, not only what a pull
  request touched) is checked against the convention for its category: a skill
  directory, an agent or command file, a `references/*.md` or `evals/*.json` name, a
  Python module under `scripts/`, `src/` or `tests/`, a workflow file, a shell script, a
  doc under `docs/`. A named, commented allowlist covers the conventional exceptions —
  `README.md`, `Makefile`, dotfiles and the rest — rather than one more special case
  invented per file.
- **Branch names.** Moved here from `check_attribution.py`, which now owns only
  authorship and tool attribution rather than two scripts enforcing one shape. The
  `<type>/<short-kebab-description>` rule and its constants are unchanged; only the
  file that owns them moved.
- **Commit subjects and the pull request title**, checked against ordinary git commit
  message practice adapted to what this repository's own history already does: plain
  imperative subjects with no Conventional Commits type prefix. A merge commit and
  anything from Dependabot — by author or by a `dependabot/` branch — are exempt, since
  neither is a subject a person chose by hand.
- **Code identifiers** are ruff's job, not this script's: `pep8-naming` (`N`) runs in
  the existing `python security lint` job because it only ever sees Python, and this
  script would just be reimplementing it worse.

Body-line wrapping is deliberately not checked. This repository's own history has commit
bodies well past 72 characters — prose explaining a decision, wrapped by the author's
own judgement rather than a column — so gating on it would fail the history it is meant
to describe as compliant. `docs/ci.md` covers where each check actually runs.

Standard library only, like the checks it sits beside. It shells out to `git log` and
`git ls-files`, resolved to an absolute path exactly as `check_attribution.py` resolves
`git`.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# --- kebab-case and snake_case, the two shapes every category below is judged against ---

KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SNAKE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

# Conventional exceptions, by exact basename. Each is a name imposed by something other
# than this repository's own taste: a GitHub or npm convention that inspects the file by
# name, a Python convention pytest and the interpreter both read specially, or a name
# `AGENTS.md` itself fixes. Extending this list is how a real exception is recorded;
# editing a check to stop looking at a file is not the same thing and is not done here.
_ALLOWED_BASENAMES = {
    "README.md",  # GitHub renders this name specially
    "AGENTS.md",  # the name Codex and Gemini CLI read; AGENTS.md fixes it
    "CLAUDE.md",  # the name Claude Code reads instead of AGENTS.md
    "CHANGELOG.md",  # Keep a Changelog convention
    "CONTRIBUTING.md",  # GitHub renders this name specially
    "CODE_OF_CONDUCT.md",  # GitHub renders this name specially
    "SECURITY.md",  # GitHub renders this name specially
    "LICENSE",  # GitHub and packaging tools look for this exact name
    "NOTICE",  # paired with LICENSE by the same convention
    "SKILL.md",  # the filename the Skills runtime loads
    "Makefile",  # make's own convention
    "pull_request_template.md",  # GitHub's own template discovery path
    "__init__.py",  # Python's package-marker filename
    "__main__.py",  # Python's module-as-script entry point
    "conftest.py",  # pytest's own fixture-discovery filename
}


def is_dotfile(path: str) -> bool:
    """Whether the file itself is a dotfile — `.editorconfig`, `.yamllint.yaml`. This is
    the file's own basename only: `.github/workflows/ci.yml` and `.claude/agents/x.md`
    both sit inside a dot-directory and are still judged by their own category below,
    because this repository chose the spelling of what is inside each, unlike the
    top-level tool-config dotfiles this exists to skip."""
    return Path(path).name.startswith(".")


# --- file and folder categories ------------------------------------------------------
#
# Each pattern captures the one segment that is actually judged. A skill's directory
# name already has to equal its `name` field — the validator checks that — so this does
# not duplicate it; it only checks the directory is kebab-case, which `name` alone does
# not guarantee (the validator accepts any `name` that is a valid frontmatter string).

_SKILL_DIR_RE = re.compile(r"^plugins/[^/]+/skills/([^/]+)/")
_AGENT_FILE_RE = re.compile(r"^(?:plugins/[^/]+/agents|\.claude/agents)/([^/]+)\.md$")
_COMMAND_FILE_RE = re.compile(r"^(?:plugins/[^/]+/commands|\.claude/commands)/([^/]+)\.md$")
_REFERENCES_RE = re.compile(r"(?:^|/)references/([^/]+)\.md$")
_EVALS_JSON_RE = re.compile(r"(?:^|/)evals/([^/]+)\.json$")
_DOCS_RE = re.compile(r"^docs/([^/]+)\.md$")
_WORKFLOW_RE = re.compile(r"^\.github/workflows/([^/]+)\.(ya?ml)$")
_PYTHON_RE = re.compile(r"^(scripts|src|tests)/(?:.*/)?([^/]+)\.py$")
_SHELL_RE = re.compile(r"(?:^|/)([^/]+)\.sh$")


def file_naming_problems(paths: list[str]) -> list[str]:
    """Every tracked path judged against the category its location puts it in. A path
    matching none of the patterns below carries no rule here — this is a checklist of
    decided conventions, not a claim that every file in the tree has one."""
    problems: list[str] = []
    seen_skill_dirs: set[str] = set()

    for path in paths:
        # An allowed basename only excuses the checks that judge the basename itself —
        # `SKILL.md` is exempt from being kebab-case, but a `SKILL.md` under a skill
        # directory still has that directory's name checked, so this does not `continue`
        # the whole path the way an early return would.
        allowed = is_dotfile(path) or Path(path).name in _ALLOWED_BASENAMES

        skill_dir = _SKILL_DIR_RE.match(path)
        if skill_dir and skill_dir.group(1) not in seen_skill_dirs:
            seen_skill_dirs.add(skill_dir.group(1))
            if not KEBAB_RE.match(skill_dir.group(1)):
                problems.append(f"{path}: skill directory `{skill_dir.group(1)}` is not kebab-case")

        agent = _AGENT_FILE_RE.match(path)
        if agent and not allowed and not KEBAB_RE.match(agent.group(1)):
            problems.append(f"{path}: agent file `{agent.group(1)}` is not kebab-case")

        command = _COMMAND_FILE_RE.match(path)
        if command and not allowed and not KEBAB_RE.match(command.group(1)):
            problems.append(f"{path}: command file `{command.group(1)}` is not kebab-case")

        reference = _REFERENCES_RE.search(path)
        if reference and not allowed and not KEBAB_RE.match(reference.group(1)):
            problems.append(f"{path}: reference `{reference.group(1)}` is not kebab-case")

        evals_json = _EVALS_JSON_RE.search(path)
        if evals_json and not allowed and not KEBAB_RE.match(evals_json.group(1)):
            problems.append(f"{path}: eval set `{evals_json.group(1)}` is not kebab-case")

        doc = _DOCS_RE.match(path)
        if doc and not allowed and not KEBAB_RE.match(doc.group(1)):
            problems.append(f"{path}: doc `{doc.group(1)}` is not kebab-case")

        workflow = _WORKFLOW_RE.match(path)
        if workflow and not allowed:
            name, extension = workflow.group(1), workflow.group(2)
            if extension == "yaml":
                problems.append(f"{path}: workflow uses `.yaml`; every workflow here uses `.yml`")
            if not KEBAB_RE.match(name):
                problems.append(f"{path}: workflow `{name}` is not kebab-case")

        python = _PYTHON_RE.match(path)
        if python and not allowed:
            top, name = python.group(1), python.group(2)
            if not SNAKE_RE.match(name):
                problems.append(f"{path}: Python module `{name}` is not snake_case")
            # Only a direct child of tests/ is a test module in the sense the convention
            # means; a helper under tests/fixtures/ is judged on snake_case alone, the
            # same as any other script, because it is not itself a test pytest collects.
            if top == "tests" and path.count("/") == 1 and not name.startswith("test_"):
                problems.append(f"{path}: test module does not start with `test_`")

        shell = _SHELL_RE.search(path)
        if (
            shell
            and not allowed
            and not (KEBAB_RE.match(shell.group(1)) or SNAKE_RE.match(shell.group(1)))
        ):
            problems.append(
                f"{path}: shell script `{shell.group(1)}` is neither kebab-case nor snake_case"
            )

    return problems


# --- branch names, moved here from check_attribution.py -------------------------------
#
# Unchanged from where they lived before: `check_attribution.py` now enforces only
# authorship and tool attribution, and a branch's shape is a naming convention like any
# other, so one script owns it rather than two agreeing by coincidence.

_ALLOWED_BRANCH_PREFIX = "dependabot/"
_BRANCH_TYPES = ("feat", "fix", "chore", "docs", "ci", "test")
_BRANCH_NAME_RE = re.compile(r"^(?:" + "|".join(_BRANCH_TYPES) + r")/[a-z0-9]+(?:-[a-z0-9]+)*$")
_EXEMPT_BRANCH_NAMES = {"main", "master", "HEAD"}

# A tool-named branch is still attribution's concern — it is naming the tool that wrote
# the change, not merely a shape violation — so `check_attribution.py` keeps that one
# message and this file does not repeat the tool-name list. `branch_problem` here only
# judges the `<type>/<short-kebab-description>` shape.


def branch_problem(branch: str | None) -> str | None:
    """None, or why a branch name does not match `<type>/<short-kebab-description>`."""
    if not branch:
        return None
    if branch in _EXEMPT_BRANCH_NAMES:
        return None
    if branch.startswith(_ALLOWED_BRANCH_PREFIX):
        return None
    if not _BRANCH_NAME_RE.match(branch):
        allowed = ", ".join(f"{t}/" for t in _BRANCH_TYPES)
        return (
            f"branch `{branch}` does not match `<type>/<short-kebab-description>` "
            f"(allowed types: {allowed}) — see CONTRIBUTING.md#naming-a-branch"
        )
    return None


# --- commit subjects and the pull request title ----------------------------------------

_TRAILING_PR_NUMBER_RE = re.compile(r"\s\(#\d+\)$")
_WIP_MARKERS = ("WIP", "fixup!", "squash!", "amend!")
_FIRST_WORD_RE = re.compile(r"^([A-Za-z]+)")
# Conventional Commits types this repository has never used and does not start; a match
# here is checked before the imperative-mood list below, since a lowercase type prefix
# would otherwise just as easily fail the "starts with a capital letter" rule with a less
# specific message.
_TYPE_PREFIX_RE = re.compile(
    r"^(feat|fix|chore|docs|ci|test|build|perf|refactor|style|revert)(\([^)]*\))?!?:\s*",
    re.IGNORECASE,
)
# Past-tense and third-person forms of the verbs a commit subject here reaches for most,
# assembled by hand from `git log --format=%s` rather than a suffix heuristic — a suffix
# rule would also catch "Address" and "Process", which end in the same letter and are
# themselves imperative.
_BANNED_FIRST_WORDS = frozenset(
    {
        "added", "adds",
        "fixed", "fixes",
        "updated", "updates",
        "removed", "removes",
        "changed", "changes",
        "improved", "improves",
        "refactored", "refactors",
        "implemented", "implements",
        "created", "creates",
        "moved", "moves",
        "renamed", "renames",
        "deleted", "deletes",
        "introduced", "introduces",
        "corrected", "corrects",
        "dropped", "drops",
        "documented", "documents",
        "reverted", "reverts",
        "replaced", "replaces",
        "bumped", "bumps",
        "enabled", "enables",
        "merged", "merges",
        "cleaned", "cleans",
        "extracted", "extracts",
        "wrote", "writes",
        "made", "makes",
    }
)  # fmt: skip


def subject_problems(raw: str) -> list[str]:
    """Every naming problem in one commit subject or pull request title."""
    subject = raw.strip()
    if not subject:
        return []

    problems = []
    for marker in _WIP_MARKERS:
        if marker in subject:
            problems.append(f"subject carries the work-in-progress marker `{marker}` — {subject!r}")

    stripped = _TRAILING_PR_NUMBER_RE.sub("", subject)
    if len(stripped) > 72:
        problems.append(f"subject is {len(stripped)} characters, over 72 — {subject!r}")
    if not stripped[:1].isupper():
        problems.append(f"subject does not start with a capital letter — {subject!r}")
    if stripped.endswith("."):
        problems.append(f"subject ends with a trailing period — {subject!r}")

    if _TYPE_PREFIX_RE.match(stripped):
        problems.append(f"subject carries a Conventional Commits type prefix — {subject!r}")
    else:
        first_word = _FIRST_WORD_RE.match(stripped)
        if first_word and first_word.group(1).lower() in _BANNED_FIRST_WORDS:
            problems.append(
                f"subject opens with `{first_word.group(1)}`, not the imperative mood — {subject!r}"
            )

    return problems


# --- git plumbing ----------------------------------------------------------------------

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"
LOG_FORMAT = FIELD_SEP.join(["%H", "%P", "%an", "%s"]) + RECORD_SEP


def git_binary() -> str | None:
    """The absolute path to git, or None. Never a bare name, the way `check_shell.py`
    resolves `bash`: a partial path is resolved against whatever PATH holds right now,
    and an absolute one is not."""
    return shutil.which("git")


def tracked_files(root: Path, git: str) -> list[str]:
    """Every path git tracks, exactly as `git ls-files` names it — forward-slashed and
    relative to `root` — so the file-naming checks run over the real tree rather than
    only what a pull request happens to touch."""
    result = subprocess.run(  # noqa: S603 - absolute path, fixed argv
        [git, "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git ls-files failed")
    return [line for line in result.stdout.splitlines() if line]


CommitRecord = tuple[str, str, str, str]


def commits_in(root: Path, commit_range: str, git: str) -> list[CommitRecord]:
    """Every commit in the range, as (hash, space-separated parent hashes, author name,
    subject)."""
    result = subprocess.run(  # noqa: S603 - absolute path, fixed argv, range is the only variable
        [git, "log", commit_range, f"--format={LOG_FORMAT}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"git log {commit_range} failed")
    records = [r for r in result.stdout.split(RECORD_SEP) if r.strip("\n")]
    commits = []
    for record in records:
        fields = record.lstrip("\n").split(FIELD_SEP, 3)
        if len(fields) != 4:
            continue
        commits.append(tuple(fields))
    return commits


_ALLOWED_IDENTITY_NAMES = {"dependabot[bot]"}


def check(
    root: Path,
    commit_range: str | None = None,
    *,
    branch: str | None = None,
    pr_title: str | None = None,
) -> int:
    git = git_binary()
    if git is None:
        print("git is not on PATH, so nothing was checked", file=sys.stderr)
        return 2

    try:
        paths = tracked_files(root, git)
    except ValueError as error:
        print(f"::error::could not list tracked files — {error}")
        return 2

    problems: list[str] = file_naming_problems(paths)

    commits_checked = 0
    if commit_range is not None:
        try:
            commits = commits_in(root, commit_range, git)
        except ValueError as error:
            print(f"::error::could not read commits in range {commit_range} — {error}")
            return 2

        # Dependabot's own branch exempts every commit on it, the same allowance
        # `check_attribution.py` gives the branch-shape check — Dependabot writes these
        # subjects itself, not a person choosing a naming convention.
        dependabot_branch = bool(branch) and branch.startswith(_ALLOWED_BRANCH_PREFIX)

        for commit_hash, parents, author_name, subject in commits:
            is_merge = len(parents.split()) > 1
            is_dependabot = author_name in _ALLOWED_IDENTITY_NAMES
            if is_merge or is_dependabot or dependabot_branch:
                continue
            commits_checked += 1
            for problem in subject_problems(subject):
                problems.append(f"commit {commit_hash[:12]}: {problem}")

        branch_bad = branch_problem(branch)
        if branch_bad:
            problems.append(branch_bad)

        if pr_title and not dependabot_branch:
            for problem in subject_problems(pr_title):
                problems.append(f"pull request title: {problem}")

    for problem in problems:
        print(f"::error title=naming::{problem}")

    if problems:
        print(f"\n{len(problems)} naming problem(s)", file=sys.stderr)
        return 1
    print(
        f"{len(paths)} tracked file(s), {commits_checked} commit(s) checked, "
        "carry no naming problems"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_naming", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    parser.add_argument(
        "--range",
        dest="commit_range",
        default=None,
        help=(
            "git log range to check commit subjects and the branch name over. Omitted "
            "on a push to main or a merge group, where there is no pull request title "
            "or range to check, so only file names are judged."
        ),
    )
    args = parser.parse_args(argv)
    return check(
        args.root.resolve(),
        args.commit_range,
        branch=os.environ.get("GITHUB_HEAD_REF"),
        pr_title=os.environ.get("PR_TITLE"),
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
