"""ci_scope.py decides how much of CI a run skips, so every way it can say "skip" is a case
here, and so is every way the proof behind it can fail and fall back to a full run.

The API is a table and git is a table, the way the triage and pin-freshness tests stand
in for the network: nothing here reaches GitHub.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import REPO, load_script

scope = load_script("ci_scope.py")

REPO_NAME = "owner/repo"
HEAD = "a" * 40
BASE = "b" * 40
STAGE = "c" * 40
STAGE_HEAD = "d" * 40
TREE = "e" * 40
MERGE = "f" * 40
PR_HEAD = "1" * 40


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
        return table[args]

    return git


def runs_path(head):
    return (
        f"/repos/{REPO_NAME}/actions/workflows/ci.yml/runs"
        f"?head_sha={head}&event=pull_request&per_page=30"
    )


def jobs_path(run_id):
    return f"/repos/{REPO_NAME}/actions/runs/{run_id}/jobs?per_page=100"


def run(run_id, base=BASE, status="completed"):
    return {"id": run_id, "status": status, "pull_requests": [{"base": {"sha": base}}]}


CODE_GREEN = [
    {"name": "test (3.13)", "conclusion": "success"},
    {"name": "validate skills", "conclusion": "success"},
]
TEXT_ONLY = [
    {"name": "test (3.13)", "conclusion": "skipped"},
    {"name": "validate skills", "conclusion": "skipped"},
    {"name": "attribution", "conclusion": "success"},
]


def env(**values):
    return {"REPOSITORY": REPO_NAME, "RUN_ID": "999", **values}


def edited(**values):
    return env(
        **{
            "EVENT_NAME": "pull_request",
            "EVENT_ACTION": "edited",
            "HEAD_SHA": HEAD,
            "BASE_SHA": BASE,
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
    assert set(scope.TEXT_JOBS).isdisjoint(scope.skippable("text"))


# --- text -----------------------------------------------------------------------------


def test_an_edit_after_a_green_run_rechecks_only_the_description():
    get = table_get(
        {
            runs_path(HEAD): {"workflow_runs": [run(999, status="in_progress"), run(7)]},
            jobs_path(7): {"jobs": CODE_GREEN + [{"name": "attribution", "conclusion": "failure"}]},
        }
    )
    mode, reason = scope.decide(edited(), get, table_git({}))
    # The current run is passed over, and an earlier failure of a description check
    # (the footer a new pull request briefly carries) does not force a full run.
    assert mode == "text" and "run 7" in reason


def test_an_edit_reaches_past_earlier_text_runs_to_the_run_that_checked_the_code():
    get = table_get(
        {
            runs_path(HEAD): {"workflow_runs": [run(9), run(8)]},
            jobs_path(9): {"jobs": TEXT_ONLY},
            jobs_path(8): {"jobs": CODE_GREEN},
        }
    )
    assert scope.decide(edited(), get, table_git({}))[0] == "text"


@pytest.mark.parametrize(
    ("runs", "jobs", "why"),
    [
        ([run(7)], {7: [{"name": "test (3.10)", "conclusion": "failure"}]}, "did not pass"),
        ([run(7)], {7: [{"name": "test (3.10)", "conclusion": "cancelled"}]}, "did not pass"),
        ([run(7, status="in_progress")], {}, "not finished"),
        ([run(7, base="0" * 40)], {}, "no earlier run"),
        ([{"id": 7, "status": "completed", "pull_requests": []}], {}, "no earlier run"),
        ([], {}, "no earlier run"),
        ([run(7)], {7: []}, "did not pass"),
    ],
)
def test_an_edit_runs_everything_unless_the_code_already_passed_against_this_base(runs, jobs, why):
    # A failed or cancelled code check, a run still going, a base that has moved since,
    # a fork's run (which carries no pull request), and no run at all are each a full run.
    table = {runs_path(HEAD): {"workflow_runs": runs}}
    table.update({jobs_path(run_id): {"jobs": listed} for run_id, listed in jobs.items()})
    mode, reason = scope.decide(edited(), table_get(table), table_git({}))
    assert mode == "full" and why in reason, reason


def test_an_edit_with_a_malformed_sha_runs_everything():
    mode, reason = scope.decide(edited(HEAD_SHA="not-a-sha"), table_get({}), table_git({}))
    assert mode == "full" and "not proven" in reason


# --- promotion from stage ----------------------------------------------------------------


def stage_world(diff="CHANGELOG.md\n", head_tree=TREE, run_jobs=CODE_GREEN, pulls=None):
    git = table_git(
        {
            ("rev-parse", "origin/stage"): STAGE + "\n",
            ("diff", "--name-only", STAGE, "HEAD"): diff,
            ("rev-parse", f"{STAGE}^{{tree}}"): TREE + "\n",
        }
    )
    if pulls is None:
        pulls = [
            {
                "number": 152,
                "merge_commit_sha": STAGE,
                "merged_at": "2026-10-06T09:04:45Z",
                "base": {"ref": "stage"},
                "head": {"sha": STAGE_HEAD},
            }
        ]
    get = table_get(
        {
            f"/repos/{REPO_NAME}/commits/{STAGE}/pulls": pulls,
            f"/repos/{REPO_NAME}/commits/{STAGE_HEAD}": {"commit": {"tree": {"sha": head_tree}}},
            runs_path(STAGE_HEAD): {"workflow_runs": [run(5)]},
            jobs_path(5): {"jobs": run_jobs},
        }
    )
    return get, git


def into_main():
    return env(EVENT_NAME="pull_request", EVENT_ACTION="synchronize", BASE_REF="main")


@pytest.mark.parametrize(
    "diff",
    [
        "",
        "CHANGELOG.md\n",
        "CHANGELOG.md\n.claude/agents/benchmarks/reviewer/unpublished-release-links/change.patch\n",
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
        (
            {
                "pulls": [
                    {
                        "number": 9,
                        "merge_commit_sha": STAGE,
                        "merged_at": "2026-10-06T09:04:45Z",
                        "base": {"ref": "dev"},
                        "head": {"sha": STAGE_HEAD},
                    }
                ]
            },
            "into stage",
        ),
    ],
)
def test_a_promotion_runs_everything_unless_stage_proves_the_tree(world, why):
    # Any change outside the release files, a stage pull request whose head is not the
    # tree stage holds, a red stage run, or a stage tip no pull request produced.
    get, git = stage_world(**world)
    mode, reason = scope.decide(into_main(), get, git)
    assert mode == "full" and why in reason, reason


def test_an_api_failure_during_a_proof_runs_everything():
    get, git = stage_world()
    broken = table_get({f"/repos/{REPO_NAME}/commits/{STAGE}/pulls": OSError("reset")})
    mode, reason = scope.decide(into_main(), broken, git)
    assert mode == "full" and reason == "not proven: OSError"


# --- promotion from the push to main -----------------------------------------------------


def push_world(pushed_tree=TREE, run_jobs=CODE_GREEN):
    git = table_git({("rev-parse", "HEAD^{tree}"): pushed_tree + "\n"})
    get = table_get(
        {
            f"/repos/{REPO_NAME}/commits/{MERGE}/pulls": [
                {
                    "number": 155,
                    "merge_commit_sha": MERGE,
                    "merged_at": "2026-10-06T11:34:00Z",
                    "base": {"ref": "main"},
                    "head": {"sha": PR_HEAD},
                }
            ],
            f"/repos/{REPO_NAME}/commits/{PR_HEAD}": {"commit": {"tree": {"sha": TREE}}},
            runs_path(PR_HEAD): {"workflow_runs": [run(6)]},
            jobs_path(6): {"jobs": run_jobs},
        }
    )
    return get, git


def on_main():
    return env(EVENT_NAME="push", REF="refs/heads/main", SHA=MERGE)


def test_the_push_after_a_proven_merge_is_a_promotion():
    get, git = push_world()
    mode, reason = scope.decide(on_main(), get, git)
    assert mode == "promotion" and "#155" in reason


@pytest.mark.parametrize(
    ("world", "why"),
    [
        ({"pushed_tree": "0" * 40}, "changed the tree"),
        ({"run_jobs": [{"name": "test (3.10)", "conclusion": "failure"}]}, "did not pass"),
    ],
)
def test_the_push_runs_everything_when_the_merge_is_not_what_passed(world, why):
    get, git = push_world(**world)
    mode, reason = scope.decide(on_main(), get, git)
    assert mode == "full" and why in reason, reason


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


def test_every_listed_job_exists_in_ci_and_every_code_job_is_listed():
    # The lists are written by hand and the workflow is not; a renamed or added job
    # either breaks a skip silently or stays unskippable forever, so they are checked
    # against each other here.
    text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    jobs = set(re.findall(r"^  ([a-z][a-z0-9-]*):\n", text.split("\njobs:\n", 1)[1], re.M))
    listed = set(scope.TEXT_SKIPS) | set(scope.PROMOTION_SKIPS)
    assert listed <= jobs, listed - jobs
    assert jobs - set(scope.TEXT_SKIPS) == set(scope.TEXT_JOBS) | set(scope.ALWAYS)
    assert set(scope.PROMOTION_SKIPS) <= set(scope.TEXT_SKIPS)
