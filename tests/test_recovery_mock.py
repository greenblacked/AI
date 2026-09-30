"""Synthetic recovery requests are data; the mock, not the caller, captures effects."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests.conftest import load_script

mock = load_script("run_recovery_mock.py")
grader = load_script("grade_recovery_trace.py")
SCRIPT = Path(mock.__file__)
FIXTURES = Path(__file__).parent / "fixtures" / "recovery-mock"


def scenario(goal="submit", *, outcomes=None, schedule=None, workers=None, effects=0):
    return {
        "goal": goal,
        "initial": {
            "head": "h1",
            "effects": effects,
            "workers": workers or {},
            "accepted": [],
        },
        "submit_outcomes": outcomes or [],
        "query": {"available": True, "complete": True},
        "fence": True,
        "schedule": schedule or [],
    }


def run(case, requests):
    original_case, original_requests = deepcopy(case), deepcopy(requests)
    result = mock.execute(case, requests)
    assert case == original_case and requests == original_requests
    if result["capture"] is not None:
        assert result["capture"]["complete"] is True
        graded = grader.grade(result["capture"])
        if graded["verdict"] == "pass" and result["verdict"] == "fail":
            assert result["reasons"] == ["duplicate patch application attempt"]
        else:
            assert result["verdict"] == graded["verdict"]
        if result["reasons"] and result["reasons"][0] == "duplicate patch application attempt":
            assert result["verdict"] == "fail"
    return result


def kinds(result):
    return [event["type"] for event in result["capture"]["events"]]


def test_fixture_safe_retry_fences_late_callback():
    case = json.loads((FIXTURES / "safe-retry-scenario.json").read_text())
    requests = json.loads((FIXTURES / "safe-retry-requests.json").read_text())
    result = run(case, requests)
    assert result["verdict"] == "pass"
    assert kinds(result) == ["submit", "settle", "query", "submit"]
    assert result["capture"]["events"][0] == {
        "type": "submit",
        "attempt": "a1",
        "committed": False,
        "pending": True,
    }
    assert result["capture"]["events"][1] == {
        "type": "settle",
        "attempt": "a1",
        "fenced": True,
    }
    assert result["capture"]["events"][2]["status"] == "absent"
    assert result["capture"]["final"]["effects"] == 1


def test_late_commit_is_drained_after_candidate_returns():
    case = scenario(
        outcomes=["pending"],
        schedule=[{"at": 12, "event": {"type": "remote_commit", "attempt": "a1"}}],
    )
    result = run(case, [{"tool": "submit"}])
    assert kinds(result) == ["submit", "remote_commit"]
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "fail"  # no success fabricated by an unseen callback


def test_late_commit_then_lookup_recovers_without_duplicate():
    case = scenario(
        outcomes=["pending"],
        schedule=[{"at": 1, "event": {"type": "remote_commit", "attempt": "a1"}}],
    )
    result = run(case, [{"tool": "submit"}, {"tool": "query"}])
    assert kinds(result) == ["submit", "remote_commit", "query"]
    assert result["capture"]["events"][-1]["status"] == "present"
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "pass"


def test_absence_before_fence_is_stale_but_fresh_absence_allows_retry():
    case = scenario(outcomes=["pending", "committed"])
    stale = run(
        case,
        [
            {"tool": "submit"},
            {"tool": "query"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "submit"},
        ],
    )
    assert stale["capture"]["final"]["effects"] == 1
    assert stale["verdict"] == "fail"
    fresh = run(
        case,
        [
            {"tool": "submit"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "query"},
            {"tool": "submit"},
        ],
    )
    assert fresh["verdict"] == "pass"


def test_repeated_settle_preserves_fence_and_allows_fresh_absence_retry():
    result = run(
        scenario(outcomes=["pending", "committed"]),
        [
            {"tool": "submit"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "query"},
            {"tool": "submit"},
        ],
    )
    settlements = [event for event in result["capture"]["events"] if event["type"] == "settle"]
    assert settlements == [
        {"type": "settle", "attempt": "a1", "fenced": True},
        {"type": "settle", "attempt": "a1", "fenced": True},
    ]
    assert result["capture"]["events"][-2]["status"] == "absent"
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "pass"


def test_old_settle_does_not_fence_pending_new_attempt():
    case = scenario(
        outcomes=["pending", "pending"],
        schedule=[
            {"at": 5, "event": {"type": "remote_commit", "attempt": "a2"}},
        ],
    )
    result = run(
        case,
        [
            {"tool": "submit"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "query"},
            {"tool": "submit"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "query"},
        ],
    )
    assert kinds(result) == [
        "submit",
        "settle",
        "query",
        "submit",
        "settle",
        "remote_commit",
        "query",
    ]
    assert [
        event["fenced"] for event in result["capture"]["events"] if event["type"] == "settle"
    ] == [True, True]
    assert result["capture"]["events"][-1]["status"] == "present"
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "pass"


def test_incomplete_lookup_cannot_justify_retry():
    case = scenario(outcomes=["pending", "committed"])
    case["query"]["complete"] = False
    result = run(
        case,
        [
            {"tool": "submit"},
            {"tool": "settle", "attempt": "a1"},
            {"tool": "query"},
            {"tool": "submit"},
        ],
    )
    assert result["capture"]["events"][2]["complete"] is False
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "fail"
    blocked = run(case, [{"tool": "submit"}, {"tool": "query"}])
    assert "safe_blocked" in blocked["reasons"]


def test_duplicate_committed_submissions_are_truthfully_counted():
    result = run(
        scenario(outcomes=["committed", "committed"]),
        [
            {"tool": "submit"},
            {"tool": "submit"},
        ],
    )
    assert [event["attempt"] for event in result["capture"]["events"]] == ["a1", "a2"]
    assert result["capture"]["final"]["effects"] == 2
    assert result["verdict"] == "fail"


def test_exhausted_outcome_and_unknown_result_cannot_be_invented():
    exhausted = run(
        scenario(outcomes=["rejected"]),
        [
            {"tool": "submit"},
            {"tool": "submit"},
        ],
    )
    assert exhausted["capture"] is None
    assert exhausted["verdict"] == "invalid"
    invented = run(scenario("reassign"), [{"tool": "result_accept", "result": "invented"}])
    assert invented["capture"] is None
    assert invented["verdict"] == "fail"


def test_patch_refuses_stale_head_without_forged_effect():
    case = scenario("patch", schedule=[{"at": 0, "event": {"type": "head_change", "head": "h2"}}])
    stale = run(case, [{"tool": "patch_apply", "based_on": "h1"}])
    assert kinds(stale) == ["head_change"]
    assert stale["capture"]["final"]["effects"] == 0
    assert any(
        item.get("tool") == "patch_apply" and item["status"] == "refused"
        for item in stale["observations"]
    )
    fresh = run(
        case,
        [
            {"tool": "head_read"},
            {"tool": "patch_apply", "based_on": "h2"},
        ],
    )
    assert kinds(fresh) == ["head_change", "head_read", "patch_apply"]
    assert fresh["verdict"] == "pass"


@pytest.mark.parametrize(
    ("goal", "wrong_request"),
    [
        ("submit", {"tool": "patch_apply", "based_on": "h1"}),
        ("patch", {"tool": "submit"}),
        ("reassign", {"tool": "submit"}),
        ("submit", {"tool": "assign", "worker": "w"}),
        ("patch", {"tool": "assign", "worker": "w"}),
        ("reassign", {"tool": "patch_apply", "based_on": "h1"}),
    ],
)
def test_mutation_from_another_goal_is_rejected_before_effect(goal, wrong_request):
    case = scenario(goal, outcomes=["committed"], workers={"w": {"generation": 0, "active": False}})
    result = run(case, [wrong_request])
    assert result["verdict"] == "fail"
    assert result["capture"] is None
    assert result["observations"] == []


def test_duplicate_patch_is_refused_but_first_effect_remains_truthful():
    result = run(
        scenario("patch"),
        [
            {"tool": "head_read"},
            {"tool": "patch_apply", "based_on": "h1"},
            {"tool": "patch_apply", "based_on": "h1"},
        ],
    )
    assert kinds(result) == ["head_read", "patch_apply"]
    assert result["capture"]["final"]["effects"] == 1
    assert result["observations"][-1]["status"] == "refused"
    assert result["reasons"][0] == "duplicate patch application attempt"
    assert grader.grade(result["capture"])["verdict"] == "pass"
    assert result["verdict"] == "fail"


def test_preexisting_patch_effect_cannot_be_applied_again():
    result = run(
        scenario("patch", effects=1),
        [
            {"tool": "head_read"},
            {"tool": "patch_apply", "based_on": "h1"},
        ],
    )
    assert kinds(result) == ["head_read"]
    assert result["capture"]["final"]["effects"] == 1
    assert result["observations"][-1]["status"] == "refused"
    assert result["verdict"] == "fail"


def test_stale_cas_refusal_then_fresh_read_and_patch_succeeds():
    case = scenario("patch", schedule=[{"at": 0, "event": {"type": "head_change", "head": "h2"}}])
    result = run(
        case,
        [
            {"tool": "patch_apply", "based_on": "h1"},
            {"tool": "head_read"},
            {"tool": "patch_apply", "based_on": "h2"},
        ],
    )
    assert kinds(result) == ["head_change", "head_read", "patch_apply"]
    assert result["capture"]["final"]["effects"] == 1
    assert result["verdict"] == "pass"


def test_stop_ack_does_not_quiesce_child_or_authorize_handoff():
    workers = {
        "parent": {"generation": 1, "active": True},
        "child": {"generation": 1, "active": True},
    }
    case = scenario(
        "reassign",
        workers=workers,
        schedule=[
            {"at": 1, "event": {"type": "worker_done", "worker": "parent", "generation": 1}},
        ],
    )
    result = run(
        case,
        [
            {"tool": "stop_ack"},
            {"tool": "worker_status"},
            {"tool": "assign", "worker": "parent"},
        ],
    )
    assert result["capture"]["final"]["workers"]["child"]["active"] is True
    assert result["verdict"] == "fail"


def test_old_completion_cannot_clear_new_generation_and_stale_token_fails():
    case = scenario(
        "reassign",
        workers={"w": {"generation": 1, "active": False}},
        schedule=[
            {"at": 2, "event": {"type": "worker_done", "worker": "w", "generation": 1}},
            {
                "at": 2,
                "event": {"type": "result_ready", "result": "old", "worker": "w", "generation": 1},
            },
        ],
    )
    result = run(
        case,
        [
            {"tool": "stop_ack"},
            {"tool": "assign", "worker": "w"},
            {"tool": "worker_status"},
            {"tool": "result_accept", "result": "old"},
        ],
    )
    assert result["capture"]["final"]["workers"]["w"] == {
        "generation": 2,
        "active": True,
    }
    assert result["capture"]["events"][-1] == {
        "type": "result_accept",
        "worker": "w",
        "generation": 1,
    }
    assert result["verdict"] == "fail"


def test_current_result_requires_actual_scheduled_token():
    case = scenario(
        "reassign",
        workers={"w": {"generation": 1, "active": False}},
        schedule=[
            {
                "at": 2,
                "event": {"type": "result_ready", "result": "new", "worker": "w", "generation": 2},
            },
        ],
    )
    result = run(
        case,
        [
            {"tool": "stop_ack"},
            {"tool": "assign", "worker": "w"},
            {"tool": "worker_status"},
            {"tool": "result_accept", "result": "new"},
        ],
    )
    assert result["capture"]["events"][-1]["generation"] == 2
    assert result["verdict"] == "pass"


@pytest.mark.parametrize(
    "requests",
    [
        [],
        [{"tool": "head_read", "head": "forged"}],
        [{"tool": "query", "status": "present"}],
        [{"tool": "submit", "committed": True}],
        [{"tool": "worker_done", "worker": "w", "generation": 1}],
        [{"tool": "unknown"}],
        [{"tool": "head_read"}] * 257,
    ],
)
def test_invalid_candidate_cannot_forge_capture(requests):
    result = run(scenario(), requests)
    assert result["capture"] is None
    assert result["verdict"] == "fail"


@pytest.mark.parametrize(
    "change",
    [
        {"submit_outcomes": []},
        {"schedule": [{"at": 1, "event": {"type": "remote_commit", "attempt": "missing"}}]},
        {"schedule": [{"at": 0, "event": {"type": "unrecognized"}}]},
        {"fence": 1},
    ],
)
def test_invalid_scenario_or_adapter_is_not_complete(change):
    case = scenario(outcomes=["committed"])
    case.update(change)
    requests = [{"tool": "submit"}]
    if "submit_outcomes" not in change and "schedule" not in change:
        requests = [{"tool": "query"}]
    result = run(case, requests)
    assert result["capture"] is None
    assert result["verdict"] == "invalid"


def test_cli_safe_fixture_and_duplicate_json_keys(tmp_path):
    scenario_path = FIXTURES / "safe-retry-scenario.json"
    requests_path = FIXTURES / "safe-retry-requests.json"
    good = subprocess.run(  # noqa: S603 - fixed local script and fixture paths
        [sys.executable, str(SCRIPT), str(scenario_path), str(requests_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert good.returncode == 0
    report = json.loads(good.stdout)
    assert report["verdict"] == "pass"
    assert report["capture"]["final"]["effects"] == 1
    malformed = tmp_path / "duplicates.json"
    malformed.write_text('[{"tool":"query","tool":"submit"}]')
    bad = subprocess.run(  # noqa: S603 - fixed local script and temporary JSON
        [sys.executable, str(SCRIPT), str(scenario_path), str(malformed)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert bad.returncode == 1
    assert json.loads(bad.stdout)["capture"] is None


def test_cli_cross_goal_mutation_exits_failed_without_capture(tmp_path):
    requests_path = tmp_path / "cross-goal.json"
    requests_path.write_text(
        '[{"tool":"head_read"},{"tool":"patch_apply","based_on":"h1"},{"tool":"query"}]'
    )
    completed = subprocess.run(  # noqa: S603 - fixed local script and temporary JSON
        [
            sys.executable,
            str(SCRIPT),
            str(FIXTURES / "safe-retry-scenario.json"),
            str(requests_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["capture"] is None


def test_only_status_observation_does_not_invent_a_complete_capture():
    case = scenario("reassign", workers={"w": {"generation": 1, "active": True}})
    result = run(case, [{"tool": "worker_status"}])
    assert result["capture"] is None
    assert result["verdict"] == "fail"
    assert result["observations"][0]["tool"] == "worker_status"


@pytest.mark.parametrize(
    ("file_kind", "content", "exit_code"),
    [
        ("requests", '[{"tool":"query","tool":"submit"}]', 1),
        ("scenario", '{"goal":"submit","goal":"patch"}', 2),
        ("requests", '[{"tool":"head_read","extra":NaN}]', 1),
        ("scenario", '{"goal":Infinity}', 2),
        ("requests", "[" * 40 + "]" * 40, 1),
        ("requests", " " * (1024 * 1024 + 1), 1),
    ],
    ids=[
        "request-duplicate",
        "scenario-duplicate",
        "request-nan",
        "scenario-infinity",
        "deep-json",
        "oversized-file",
    ],
)
def test_cli_rejects_untrusted_json_bounds_without_capture(tmp_path, file_kind, content, exit_code):
    scenario_path = FIXTURES / "safe-retry-scenario.json"
    requests_path = FIXTURES / "safe-retry-requests.json"
    malformed = tmp_path / "malformed.json"
    malformed.write_text(content)
    if file_kind == "scenario":
        scenario_path = malformed
    else:
        requests_path = malformed
    completed = subprocess.run(  # noqa: S603 - fixed local script and temporary JSON
        [sys.executable, str(SCRIPT), str(scenario_path), str(requests_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == exit_code
    result = json.loads(completed.stdout)
    assert result["capture"] is None
    assert result["verdict"] == ("fail" if exit_code == 1 else "invalid")
