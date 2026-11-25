"""ci_scope.py decides how much of CI a run skips, so every way it can say "skip" is a case
here, and so is every way the proof behind it can fail and fall back to a full run.

The API is a table and git is a table, the way the triage and pin-freshness tests stand
in for the network: nothing here reaches GitHub.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from tests.conftest import REPO, load_script

scope = load_script("ci_scope.py")

REPO_NAME = "owner/repo"
STAGE = "c" * 40
STAGE_HEAD = "d" * 40
TREE = "e" * 40
STAGE_REF = "feat/promote-to-stage"
PATCH = ".claude/agents/benchmarks/reviewer/unpublished-release-links/change.patch"


def table_get(table):
    def get(path):
        if path not in table:
            raise KeyError(path)
        value = table[path]
        if isinstance(value, Exception):
            raise value
        return value

    return get


def table_git(table):
    def git(*args):
        if args not in table:
            raise KeyError(args)
        value = table[args]
        if isinstance(value, Exception):
            raise value
        return value

    return git


def branch_pulls_path():
    owner = REPO_NAME.split("/")[0]
    return f"/repos/{REPO_NAME}/pulls?head={owner}:feat%2Fpromote-to-stage&state=all&per_page=100"


def runs_path(head):
    return (
        f"/repos/{REPO_NAME}/actions/workflows/ci.yml/runs"
        f"?head_sha={head}&event=pull_request&per_page=30"
    )


def jobs_path(run_id):
    return f"/repos/{REPO_NAME}/actions/runs/{run_id}/jobs?per_page=100"


def run(run_id, status="completed", branch=STAGE_REF, repo=REPO_NAME):
    return {
        "id": run_id,
        "status": status,
        "head_branch": branch,
        "head_repository": {"full_name": repo},
    }


CODE_GREEN = [
    {"name": "test (3.13)", "conclusion": "success"},
    {"name": "validate skills", "conclusion": "success"},
]


def env(**values):
    return {"REPOSITORY": REPO_NAME, **values}


def edited(**values):
    return env(
        **{
            "EVENT_NAME": "pull_request",
            "EVENT_ACTION": "edited",
            **values,
        }
    )


# --- full ---------------------------------------------------------------------------


@pytest.mark.parametrize("base", ["dev", "stage"])
def test_a_pull_request_into_dev_or_stage_runs_everything(base):
    mode, reason = scope.decide(
        env(EVENT_NAME="pull_request", EVENT_ACTION="synchronize", BASE_REF=base),
        table_get({}),
        table_git({}),
    )
    assert mode == "full" and base in reason


@pytest.mark.parametrize("event", ["workflow_dispatch", "merge_group", "push"])
def test_other_events_run_everything(event):
    mode, _ = scope.decide(
        env(EVENT_NAME=event, REF="refs/heads/dev"), table_get({}), table_git({})
    )
    assert mode == "full"


def test_skippable_lists_are_fixed_and_full_skips_nothing():
    assert scope.skippable("full") == ()
    assert scope.skippable("anything else") == ()
    assert "test" in scope.skippable("promotion") and "package" not in scope.skippable("promotion")


# --- edits ----------------------------------------------------------------------------


def test_an_edit_into_dev_runs_everything_without_reusing_a_historical_run():
    def unexpected_get(path):
        raise AssertionError(f"edited runs must not query historical CI: {path}")

    mode, reason = scope.decide(edited(BASE_REF="dev"), unexpected_get, table_git({}))
    assert mode == "full" and "into dev" in reason, reason


# --- promotion from stage ----------------------------------------------------------------


def stage_world(
    diff="CHANGELOG.md\n",
    head_tree=TREE,
    run_jobs=CODE_GREEN,
    pulls=None,
    runs=None,
    applies="",
    branch_pulls=None,
):
    git = table_git(
        {
            ("rev-parse", "origin/stage"): STAGE + "\n",
            ("diff", "--no-renames", "--name-only", STAGE, "HEAD"): diff,
            ("rev-parse", f"{STAGE}^{{tree}}"): TREE + "\n",
            ("apply", "--check", PATCH): applies,
        }
    )
    if pulls is None:
        pulls = [
            {
                "number": 152,
                "merge_commit_sha": STAGE,
                "merged_at": "2026-10-06T09:04:45Z",
                "base": {"ref": "stage"},
                "head": {"sha": STAGE_HEAD, "ref": STAGE_REF},
            }
        ]
    table = {
        f"/repos/{REPO_NAME}/commits/{STAGE}/pulls": pulls,
        f"/repos/{REPO_NAME}/commits/{STAGE_HEAD}": {"commit": {"tree": {"sha": head_tree}}},
        runs_path(STAGE_HEAD): {"workflow_runs": [run(5)] if runs is None else runs},
        jobs_path(5): {"jobs": run_jobs},
        branch_pulls_path(): [{"number": 152}] if branch_pulls is None else branch_pulls,
        jobs_path(4): {"jobs": [{"name": "site-browser", "conclusion": "failure"}]},
    }
    return table_get(table), git


def into_main():
    return env(EVENT_NAME="pull_request", EVENT_ACTION="synchronize", BASE_REF="main")


@pytest.mark.parametrize(
    "diff",
    [
        "",
        "CHANGELOG.md\n",
        f"CHANGELOG.md\n{PATCH}\n",
    ],
)
def test_a_promotion_of_the_tree_stage_passed_skips_the_test_matrix(diff):
    get, git = stage_world(diff=diff)
    mode, reason = scope.decide(into_main(), get, git)
    assert mode == "promotion", reason
    assert "#152" in reason and "run 5" in reason


@pytest.mark.parametrize(
    ("world", "why"),
    [
        ({"diff": "CHANGELOG.md\nscripts/site_style.py\n"}, "differs from stage in 1 file"),
        ({"head_tree": "0" * 40}, "not the tree stage holds"),
        ({"run_jobs": [{"name": "test (3.13)", "conclusion": "failure"}]}, "did not pass"),
        ({"pulls": []}, "is not the merge of a pull request into stage"),
        ({"runs": [run(5), run(4)]}, "run 4"),
        ({"runs": [run(5, branch="feat/another-pull-request")]}, "no earlier run"),
        ({"runs": [run(5, repo="someone/fork")]}, "no earlier run"),
        ({"branch_pulls": [{"number": 152}, {"number": 160}]}, "also heads pull request #160"),
        (
            {
                "pulls": [
                    {
                        "number": 152,
                        "merge_commit_sha": STAGE,
                        "merged_at": "2026-10-06T09:04:45Z",
                        "base": {"ref": "stage"},
                        "head": {"sha": STAGE_HEAD},
                    }
                ]
            },
            "names no head branch",
        ),
        (
            {
                "diff": f"{PATCH}\n",
                "applies": subprocess.CalledProcessError(1, ["git", "apply"]),
            },
            "CalledProcessError",
        ),
        (
            {
                "pulls": [
                    {
                        "number": 9,
                        "merge_commit_sha": STAGE,
                        "merged_at": "2026-10-06T09:04:45Z",
                        "base": {"ref": "dev"},
                        "head": {"sha": STAGE_HEAD, "ref": STAGE_REF},
                    }
                ]
            },
            "into stage",
        ),
    ],
)
def test_a_promotion_runs_everything_unless_stage_proves_the_tree(world, why):
    # Any change outside the release files, a stage pull request whose head is not the
    # tree stage holds, a red stage run (even behind a green one), a stage tip no pull
    # request produced, a repointed benchmark patch that no longer applies, or a green
    # run that belongs to another pull request or a fork with the same head commit, or a
    # stage branch that also headed another pull request, whose runs share its branch.
    get, git = stage_world(**world)
    mode, reason = scope.decide(into_main(), get, git)
    assert mode == "full" and why in reason, reason


def test_an_api_failure_during_a_proof_runs_everything():
    get, git = stage_world()
    broken = table_get({f"/repos/{REPO_NAME}/commits/{STAGE}/pulls": OSError("reset")})
    mode, reason = scope.decide(into_main(), broken, git)
    assert mode == "full" and reason == "not proven: OSError"


# --- promotion from the push to main, and edits to a promotion -------------------------


def on_main():
    return env(EVENT_NAME="push", REF="refs/heads/main", SHA="f" * 40)


def test_the_push_to_main_is_proven_by_stage_like_the_pull_request_was():
    # The merged pull request ran as a promotion, with the matrix skipped, so it cannot
    # vouch for the push; stage's pull request ran everything.
    get, git = stage_world()
    mode, reason = scope.decide(on_main(), get, git)
    assert mode == "promotion" and "#152" in reason, reason


def test_the_push_to_main_runs_everything_when_main_is_not_stage():
    get, git = stage_world(diff="CHANGELOG.md\nscripts/site_style.py\n")
    mode, reason = scope.decide(on_main(), get, git)
    assert mode == "full" and "differs from stage" in reason, reason


def test_an_edit_to_a_promotion_is_proven_by_stage():
    get, git = stage_world()
    mode, reason = scope.decide(edited(BASE_REF="main"), get, git)
    assert mode == "promotion" and "#152" in reason, reason


# --- plumbing ----------------------------------------------------------------------------


def test_only_the_github_api_is_ever_called():
    assert scope.resolve_url("/repos/x/y") == "https://api.github.com/repos/x/y"
    with pytest.raises(ValueError):
        scope.resolve_url("https://example.com/repos/x/y")
    with pytest.raises(ValueError):
        scope.resolve_url("https://api.github.com.example.com/x")


def test_run_git_returns_git_output():
    assert re.fullmatch(r"[0-9a-f]{40}\n", scope.run_git("-C", str(REPO), "rev-parse", "HEAD"))


def test_main_writes_mode_and_the_jobs_it_may_skip(tmp_path, monkeypatch):
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(scope, "decide", lambda env, get, git: ("promotion", "a reason"))
    assert scope.main() == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "mode=promotion"
    assert lines[1] == "skippable=" + " ".join(scope.PROMOTION_SKIPS)
    assert "`promotion`" in summary.read_text(encoding="utf-8")


def test_every_promotion_skip_names_a_workflow_job():
    # The skip list is written by hand and the workflow is not; a renamed job would make
    # the aggregate reject an otherwise valid promotion.
    text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    jobs = set(re.findall(r"^  ([a-z][a-z0-9-]*):\n", text.split("\njobs:\n", 1)[1], re.M))
    assert set(scope.PROMOTION_SKIPS) <= jobs


def test_non_code_check_names_match_the_workflow_display_names():
    # The runs API reports a job by its `name:`, not its id. A renamed code check must not
    # become ignored by the historical promotion proof.
    text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    names = {
        job: re.search(rf"^  {job}:\n(?:    #.*\n)*    name: (.+)$", text, re.M).group(1)
        for job in ("attribution", "naming", "ci", "scope")
    }
    assert set(names.values()) == set(scope.NON_CODE_CHECK_NAMES), names
