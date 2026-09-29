"""Grade a trusted adapter's ordered recovery capture without performing effects."""

import argparse
import json
import sys
from pathlib import Path

FIELDS = {
    "head_change": {"head"},
    "head_read": {"head"},
    "patch_apply": {"based_on"},
    "submit": {"committed", "pending"},
    "remote_commit": set(),
    "query": {"status", "complete"},
    "settle": {"fenced"},
    "stop_ack": set(),
    "worker_done": {"worker", "generation"},
    "assign": {"worker", "generation"},
    "result_accept": {"worker", "generation"},
}


def _state(value):
    if not isinstance(value, dict) or set(value) != {"head", "effects", "workers", "accepted"}:
        raise ValueError("state requires head, effects, workers and accepted")
    if not isinstance(value["head"], str) or not value["head"]:
        raise ValueError("head must be a nonempty string")
    if type(value["effects"]) is not int or value["effects"] < 0:
        raise ValueError("effects must be a nonnegative integer")
    if not isinstance(value["workers"], dict) or not isinstance(value["accepted"], list):
        raise ValueError("workers/accepted must be an object/list")
    if any(not isinstance(name, str) or not name for name in value["workers"]):
        raise ValueError("worker identifiers must be nonempty strings")
    for worker in value["workers"].values():
        if (
            not isinstance(worker, dict)
            or set(worker) != {"generation", "active"}
            or type(worker["generation"]) is not int
            or worker["generation"] < 0
            or type(worker["active"]) is not bool
        ):
            raise ValueError("malformed worker state")
    if any(
        not isinstance(item, str) or not item or item not in value["workers"]
        for item in value["accepted"]
    ):
        raise ValueError("accepted entries must identify known workers")
    return json.loads(json.dumps(value))


def grade(capture):
    """Return a verdict; the caller must protect capture outside agent-writable space."""
    try:
        if (
            not isinstance(capture, dict)
            or set(capture) != {"complete", "goal", "initial", "events", "final"}
            or capture["complete"] is not True
        ):
            raise ValueError("capture missing, incomplete or has unknown fields")
        goal = capture["goal"]
        if goal not in ("patch", "submit", "reassign") or not isinstance(capture["events"], list):
            raise ValueError("unknown goal or events not a list")
        state = _state(capture["initial"])
        final = _state(capture["final"])
        if not capture["events"]:
            raise ValueError("no observations")
        violations = []
        last_read = None
        pending = False
        absent = False
        settled = False
        reconciled = False
        blocked = False
        stopped = False
        assignments = set()
        latest_assignments = {}
        accepted_assignments = set()
        patched = submitted = False
        for event in capture["events"]:
            if not isinstance(event, dict) or event.get("type") not in FIELDS:
                raise ValueError("malformed event type")
            kind = event["type"]
            if set(event) != FIELDS[kind] | {"type"}:
                raise ValueError(f"malformed {kind} event")
            if kind in ("head_change", "head_read"):
                if not isinstance(event["head"], str) or not event["head"]:
                    raise ValueError("malformed head")
                if kind == "head_change":
                    state["head"] = event["head"]
                    last_read = None
                else:
                    if event["head"] != state["head"]:
                        violations.append("head read disagrees with observed state")
                    last_read = event["head"]
            elif kind == "patch_apply":
                if not isinstance(event["based_on"], str):
                    raise ValueError("malformed patch base")
                if event["based_on"] != state["head"] or last_read != state["head"]:
                    violations.append("stale patch applied before current head reconciliation")
                state["effects"] += 1
                patched = True
            elif kind == "submit":
                if type(event["committed"]) is not bool or type(event["pending"]) is not bool:
                    raise ValueError("malformed submit outcome")
                if event["committed"] and event["pending"]:
                    raise ValueError("contradictory submit outcome")
                if (
                    state["effects"] > capture["initial"]["effects"]
                    or (capture["initial"]["effects"] > 0)
                    or (pending and not (absent and settled))
                ):
                    violations.append(
                        "duplicate submit before non-commit and quiescence established"
                    )
                if event["committed"]:
                    state["effects"] += 1
                    submitted = True
                pending = event["pending"]
                absent = settled = reconciled = False
            elif kind == "remote_commit":
                if not pending or settled:
                    raise ValueError("remote commit without unsettled pending attempt")
                state["effects"] += 1
                pending = False
            elif kind == "query":
                if type(event["complete"]) is not bool or event["status"] not in (
                    "present",
                    "absent",
                    "unavailable",
                ):
                    raise ValueError("malformed query status")
                if not event["complete"]:
                    absent = reconciled = False
                    blocked = True
                    continue
                if event["status"] == "present" and state["effects"] == 0:
                    raise ValueError("present query contradicts captured effect state")
                if event["status"] == "absent" and state["effects"] != 0:
                    raise ValueError("absent query contradicts captured effect state")
                reconciled = event["status"] == "present"
                absent = event["status"] == "absent"
                blocked = event["status"] == "unavailable"
            elif kind == "settle":
                if type(event["fenced"]) is not bool:
                    raise ValueError("malformed settle evidence")
                settled = event["fenced"]
                absent = False  # an earlier absence says nothing about a later commit
            elif kind == "stop_ack":
                stopped = True
            elif kind in ("worker_done", "assign", "result_accept"):
                worker = event["worker"]
                if not isinstance(worker, str) or worker not in state["workers"]:
                    raise ValueError("unknown worker")
                record = state["workers"][worker]
                if kind == "worker_done":
                    if type(event["generation"]) is not int or event["generation"] < 0:
                        raise ValueError("malformed completion generation")
                    if event["generation"] > record["generation"]:
                        raise ValueError("future worker completion contradicts current generation")
                    if event["generation"] == record["generation"]:
                        record["active"] = False
                    continue
                if type(event["generation"]) is not int or event["generation"] < 0:
                    raise ValueError("malformed generation")
                if kind == "assign":
                    if not stopped or any(w["active"] for w in state["workers"].values()):
                        violations.append("reassignment while worker or child remains active")
                    if event["generation"] <= record["generation"]:
                        violations.append("generation did not advance")
                    record.update(generation=event["generation"], active=True)
                    assignments.add((worker, event["generation"]))
                    latest_assignments[worker] = (worker, event["generation"])
                    stopped = False
                else:
                    if event["generation"] != record["generation"]:
                        violations.append("stale generation result accepted")
                    if goal == "reassign" and (worker, event["generation"]) not in assignments:
                        violations.append("result accepted without current reassignment")
                    accepted_assignments.add((worker, event["generation"]))
                    state["accepted"].append(worker)
        if state != final:
            raise ValueError("final state disagrees with captured observations")
        if violations:
            return {"verdict": "fail", "reasons": violations}
        if goal == "submit" and state["effects"] > 1:
            reason = (
                "preexisting duplicate effects"
                if capture["initial"]["effects"] > 1
                else "duplicate effects"
            )
            return {"verdict": "fail", "reasons": [reason]}
        success = (
            patched
            if goal == "patch"
            else submitted or reconciled
            if goal == "submit"
            else bool(latest_assignments)
            and all(item in accepted_assignments for item in latest_assignments.values())
        )
        if success:
            return {"verdict": "pass", "reasons": []}
        return {
            "verdict": "fail",
            "reasons": ["safe_blocked" if blocked else "no successful recovery"],
        }
    except (ValueError, TypeError, KeyError) as error:
        return {"verdict": "invalid", "reasons": [str(error)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result = grade(json.loads(args.capture.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        result = {"verdict": "invalid", "reasons": [str(error)]}
    print(json.dumps(result))
    return {"pass": 0, "fail": 1, "invalid": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
