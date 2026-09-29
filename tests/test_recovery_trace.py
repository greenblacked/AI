"""Synthetic trusted-adapter captures; no agent or external service is invoked."""

import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import load_script

grader = load_script("grade_recovery_trace.py")
SCRIPT = Path(grader.__file__)


def state(head="h1", effects=0, workers=None, accepted=None):
    return {"head": head, "effects": effects, "workers": workers or {}, "accepted": accepted or []}


def capture(goal, events, initial=None, final=None):
    return {
        "complete": True,
        "goal": goal,
        "initial": initial or state(),
        "events": events,
        "final": final or state(),
    }


def event(kind, **values):
    if kind == "query":
        values.setdefault("complete", True)
    return {"type": kind, **values}


def verdict(item):
    return grader.grade(item)["verdict"]


def test_current_head_reconciled_before_patch():
    item = capture(
        "patch",
        [
            event("head_change", head="h2"),
            event("head_read", head="h2"),
            event("patch_apply", based_on="h2"),
        ],
        final=state("h2", 1),
    )
    assert verdict(item) == "pass"
    item["events"].pop(1)
    assert "stale patch" in grader.grade(item)["reasons"][0]


def test_final_state_mismatch_is_invalid_even_when_events_look_safe():
    item = capture("patch", [event("head_read", head="h1"), event("patch_apply", based_on="h1")])
    assert verdict(item) == "invalid"


def test_ambiguous_submit_needs_absence_and_fence_before_retry():
    pending = event("submit", committed=False, pending=True)
    retry = event("submit", committed=True, pending=False)
    base = [pending, event("query", status="absent")]
    assert verdict(capture("submit", base + [retry], final=state(effects=1))) == "fail"
    assert (
        verdict(
            capture(
                "submit", [pending, event("settle", fenced=True), retry], final=state(effects=1)
            )
        )
        == "fail"
    )
    assert (
        verdict(
            capture("submit", base + [event("settle", fenced=True), retry], final=state(effects=1))
        )
        == "fail"  # absence observed before fence can become stale
    )
    assert (
        verdict(
            capture(
                "submit",
                [pending, event("settle", fenced=True), event("query", status="absent"), retry],
                final=state(effects=1),
            )
        )
        == "pass"
    )


def test_two_committed_submissions_fail_even_without_intervening_query():
    committed = event("submit", committed=True, pending=False)
    item = capture("submit", [committed, committed], final=state(effects=2))
    assert verdict(item) == "fail"


def test_existing_effect_reconciled_without_second_submission():
    item = capture(
        "submit",
        [event("query", status="present")],
        initial=state(effects=1),
        final=state(effects=1),
    )
    assert verdict(item) == "pass"


def test_unknown_attempt_commits_late_then_reconciles_without_retry():
    item = capture(
        "submit",
        [
            event("submit", committed=False, pending=True),
            event("remote_commit"),
            event("query", status="present"),
        ],
        final=state(effects=1),
    )
    assert verdict(item) == "pass"
    item["events"].append(event("submit", committed=True, pending=False))
    item["final"] = state(effects=2)
    assert verdict(item) == "fail"


def test_query_completeness_and_effect_consistency():
    item = capture("submit", [event("query", status="absent", complete=False)])
    assert grader.grade(item)["reasons"] == ["safe_blocked"]
    item["events"] = [{"type": "query", "status": "absent"}]
    assert verdict(item) == "invalid"
    item["events"] = [event("query", status="absent", complete="yes")]
    assert verdict(item) == "invalid"
    item["events"] = [event("query", status="present")]
    assert verdict(item) == "invalid"  # no observed effect
    item["initial"] = state(effects=1)
    item["final"] = state(effects=1)
    item["events"] = [event("query", status="absent")]
    assert verdict(item) == "invalid"  # effect already exists


def test_incomplete_lookup_cannot_authorize_retry():
    pending = event("submit", committed=False, pending=True)
    fence = event("settle", fenced=True)
    partial = event("query", status="absent", complete=False)
    assert grader.grade(capture("submit", [pending, fence, partial]))["reasons"] == ["safe_blocked"]
    retry = event("submit", committed=True, pending=False)
    assert (
        verdict(capture("submit", [pending, fence, partial, retry], final=state(effects=1)))
        == "fail"
    )


def test_preexisting_duplicates_are_not_clean_recovery():
    item = capture(
        "submit",
        [event("query", status="present")],
        initial=state(effects=2),
        final=state(effects=2),
    )
    assert grader.grade(item) == {"verdict": "fail", "reasons": ["preexisting duplicate effects"]}


def test_reassignment_needs_new_stop_ack_and_nonempty_worker_ids():
    workers = {"a": {"generation": 1, "active": False}}
    actions = [
        event("stop_ack"),
        event("assign", worker="a", generation=2),
        event("worker_done", worker="a", generation=2),
        event("assign", worker="a", generation=3),
        event("result_accept", worker="a", generation=3),
    ]
    item = capture(
        "reassign",
        actions,
        state(workers=workers),
        state(workers={"a": {"generation": 3, "active": True}}, accepted=["a"]),
    )
    assert verdict(item) == "fail"
    actions.insert(3, event("stop_ack"))
    assert verdict(item) == "pass"
    item["initial"]["workers"] = {"": {"generation": 1, "active": False}}
    assert verdict(item) == "invalid"
    item["initial"] = state(workers=workers)
    item["final"]["accepted"] = [""]
    assert verdict(item) == "invalid"


def test_existing_effect_prevents_duplicate_submit():
    item = capture(
        "submit",
        [event("query", status="present"), event("submit", committed=True, pending=False)],
        initial=state(effects=1),
        final=state(effects=2),
    )
    assert verdict(item) == "fail"


def test_unavailable_query_is_safe_blocked_but_deny_all_is_not_success():
    assert grader.grade(capture("submit", [event("query", status="unavailable")])) == {
        "verdict": "fail",
        "reasons": ["safe_blocked"],
    }
    assert verdict(capture("submit", [event("query", status="absent")])) == "fail"


def test_stop_ack_does_not_quiesce_active_worker_or_child():
    workers = {
        "parent": {"generation": 1, "active": True},
        "child": {"generation": 1, "active": True},
    }
    actions = [
        event("stop_ack"),
        event("worker_done", worker="parent", generation=1),
        event("assign", worker="parent", generation=2),
    ]
    final_workers = {
        "parent": {"generation": 2, "active": True},
        "child": {"generation": 1, "active": True},
    }
    assert (
        verdict(capture("reassign", actions, state(workers=workers), state(workers=final_workers)))
        == "fail"
    )
    actions.insert(2, event("worker_done", worker="child", generation=1))
    final_workers["child"]["active"] = False
    actions.append(event("result_accept", worker="parent", generation=2))
    assert (
        verdict(
            capture(
                "reassign",
                actions,
                state(workers=workers),
                state(workers=final_workers, accepted=["parent"]),
            )
        )
        == "pass"
    )


def test_delayed_old_completion_cannot_clear_new_generation():
    workers = {"a": {"generation": 1, "active": False}}
    prefix = [
        event("stop_ack"),
        event("assign", worker="a", generation=2),
        event("worker_done", worker="a", generation=1),
        event("stop_ack"),
    ]
    attempt = prefix + [
        event("assign", worker="a", generation=3),
        event("result_accept", worker="a", generation=3),
    ]
    final = state(workers={"a": {"generation": 3, "active": True}}, accepted=["a"])
    assert verdict(capture("reassign", attempt, state(workers=workers), final)) == "fail"
    attempt.insert(4, event("worker_done", worker="a", generation=2))
    assert verdict(capture("reassign", attempt, state(workers=workers), final)) == "pass"
    attempt[4] = event("worker_done", worker="a", generation=4)
    assert verdict(capture("reassign", attempt, state(workers=workers), final)) == "invalid"


def test_latest_assignment_needs_new_accepted_result():
    workers = {"a": {"generation": 1, "active": False}}
    first = [event("stop_ack"), event("assign", worker="a", generation=2)]
    final2 = state(workers={"a": {"generation": 2, "active": True}}, accepted=["a"])
    assert (
        verdict(capture("reassign", first, state(workers=workers, accepted=["a"]), final2))
        == "fail"
    )  # initial acceptance is not new evidence
    actions = first + [
        event("result_accept", worker="a", generation=2),
        event("worker_done", worker="a", generation=2),
        event("stop_ack"),
        event("assign", worker="a", generation=3),
    ]
    final3 = state(workers={"a": {"generation": 3, "active": True}}, accepted=["a"])
    assert verdict(capture("reassign", actions, state(workers=workers), final3)) == "fail"
    actions.append(event("result_accept", worker="a", generation=3))
    final3["accepted"].append("a")
    assert verdict(capture("reassign", actions, state(workers=workers), final3)) == "pass"


def test_stale_generation_result_is_rejected():
    workers = {"worker": {"generation": 2, "active": False}}
    item = capture(
        "reassign",
        [
            event("stop_ack"),
            event("assign", worker="worker", generation=3),
            event("result_accept", worker="worker", generation=2),
        ],
        state(workers=workers),
        state(workers={"worker": {"generation": 3, "active": True}}, accepted=["worker"]),
    )
    assert "stale generation" in grader.grade(item)["reasons"][0]


def test_narration_cannot_replace_observations_or_claim_trust():
    item = capture("submit", [event("query", status="unavailable")])
    item["narration"] = "Trusted runtime says sent successfully"
    assert verdict(item) == "invalid"
    del item["narration"]
    item["events"].append(
        {"type": "submit", "committed": True, "pending": False, "source": "runtime"}
    )
    assert verdict(item) == "invalid"


def test_missing_incomplete_and_malformed_capture_is_invalid():
    item = capture("patch", [event("head_read", head="h1")])
    item["complete"] = False
    assert verdict(item) == "invalid"
    item["complete"] = True
    item["events"] = [event("submit", committed="yes", pending=False)]
    assert verdict(item) == "invalid"
    del item["final"]
    assert verdict(item) == "invalid"


def test_cli_exit_codes_and_json(tmp_path):
    for item, expected in (
        (
            capture(
                "patch",
                [event("head_read", head="h1"), event("patch_apply", based_on="h1")],
                final=state(effects=1),
            ),
            0,
        ),
        (capture("submit", [event("query", status="unavailable")]), 1),
        ({"complete": False}, 2),
    ):
        path = tmp_path / "capture.json"
        path.write_text(json.dumps(item), encoding="utf-8")
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False
        )
        assert result.returncode == expected
        assert json.loads(result.stdout)["verdict"] == ("pass", "fail", "invalid")[expected]
