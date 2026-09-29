"""Run data-only recovery requests against a bounded trusted mock adapter."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


class InputError(ValueError):
    pass


class AdapterError(ValueError):
    pass


def _limits(value, depth=0):
    if depth > 16:
        raise InputError("JSON nesting limit exceeded")
    if isinstance(value, str):
        if len(value) > 256:
            raise InputError("string limit exceeded")
    elif isinstance(value, (dict, list)):
        if len(value) > 256:
            raise InputError("item limit exceeded")
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise InputError("object key must be a string")
                _limits(key, depth + 1)
                _limits(item, depth + 1)
        else:
            for item in value:
                _limits(item, depth + 1)
    elif value is not None and type(value) not in (bool, int, float):
        raise InputError("unsupported JSON value")
    if type(value) is float:
        raise InputError("floating-point values are unsupported")
    if type(value) is int and abs(value) > 2**63 - 1:
        raise InputError("integer limit exceeded")


def _keys(value, fields, error=InputError):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise error("unexpected or missing fields")


def _name(value, error=InputError):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise error("identifier must be a nonempty bounded string")


def _state(value):
    _keys(value, ("head", "effects", "workers", "accepted"), AdapterError)
    _name(value["head"], AdapterError)
    if type(value["effects"]) is not int or value["effects"] < 0:
        raise AdapterError("invalid initial effect count")
    if not isinstance(value["workers"], dict) or not isinstance(value["accepted"], list):
        raise AdapterError("invalid initial worker state")
    for name, record in value["workers"].items():
        _name(name, AdapterError)
        _keys(record, ("generation", "active"), AdapterError)
        if (
            type(record["generation"]) is not int
            or record["generation"] < 0
            or type(record["active"]) is not bool
        ):
            raise AdapterError("invalid initial worker generation")
    if any(not isinstance(name, str) or name not in value["workers"] for name in value["accepted"]):
        raise AdapterError("invalid initial accepted worker")


SCHEDULE = {
    "head_change": {"type", "head"},
    "remote_commit": {"type", "attempt"},
    "worker_done": {"type", "worker", "generation"},
    "result_ready": {"type", "result", "worker", "generation"},
}
REQUESTS = {
    "head_read": {"tool"},
    "patch_apply": {"tool", "based_on"},
    "submit": {"tool"},
    "query": {"tool"},
    "settle": {"tool", "attempt"},
    "stop_ack": {"tool"},
    "worker_status": {"tool"},
    "assign": {"tool", "worker"},
    "result_accept": {"tool", "result"},
}


def _scenario(value):
    _limits(value)
    _keys(value, ("goal", "initial", "submit_outcomes", "query", "fence", "schedule"), AdapterError)
    if value["goal"] not in ("patch", "submit", "reassign"):
        raise AdapterError("invalid scenario goal")
    _state(value["initial"])
    outcomes = value["submit_outcomes"]
    if not isinstance(outcomes, list) or any(
        outcome not in ("committed", "pending", "rejected") for outcome in outcomes
    ):
        raise AdapterError("invalid submit outcomes")
    _keys(value["query"], ("available", "complete"), AdapterError)
    if any(type(flag) is not bool for flag in (*value["query"].values(), value["fence"])):
        raise AdapterError("invalid query or fence capability")
    if not isinstance(value["schedule"], list):
        raise AdapterError("invalid schedule")
    previous = -1
    results = set()
    for item in value["schedule"]:
        _keys(item, ("at", "event"), AdapterError)
        if type(item["at"]) is not int or item["at"] < previous or item["at"] < 0:
            raise AdapterError("schedule must have ascending nonnegative barriers")
        previous = item["at"]
        event = item["event"]
        if not isinstance(event, dict) or event.get("type") not in SCHEDULE:
            raise AdapterError("unknown scheduled event")
        _keys(event, SCHEDULE[event["type"]], AdapterError)
        if event["type"] == "head_change":
            _name(event["head"], AdapterError)
        elif event["type"] == "remote_commit":
            _name(event["attempt"], AdapterError)
        else:
            _name(event["worker"], AdapterError)
            if type(event["generation"]) is not int or event["generation"] < 0:
                raise AdapterError("invalid scheduled generation")
            if event["type"] == "result_ready":
                _name(event["result"], AdapterError)
                if event["result"] in results:
                    raise AdapterError("duplicate result token")
                results.add(event["result"])


def _requests(value):
    _limits(value)
    if not isinstance(value, list):
        raise InputError("requests must be an array")
    for item in value:
        if not isinstance(item, dict) or item.get("tool") not in REQUESTS:
            raise InputError("unknown candidate tool")
        _keys(item, REQUESTS[item["tool"]])
        for key in REQUESTS[item["tool"]] - {"tool"}:
            _name(item[key])


def _grader():
    path = Path(__file__).with_name("grade_recovery_trace.py")
    spec = importlib.util.spec_from_file_location("_bundled_recovery_grader", path)
    if spec is None or spec.loader is None:
        raise AdapterError("bundled grader unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.grade


def _error(verdict, reason):
    return {"capture": None, "observations": [], "verdict": verdict, "reasons": [reason]}


def execute(scenario, requests):
    """Execute validated data requests; scenario and schedule are trusted adapter input."""
    try:
        _scenario(scenario)
    except (InputError, AdapterError, TypeError, ValueError):
        return _error("invalid", "invalid trusted scenario")
    try:
        _requests(requests)
    except (InputError, TypeError, ValueError):
        return _error("fail", "invalid candidate requests")
    result_tokens = {
        item["event"]["result"]
        for item in scenario["schedule"]
        if item["event"]["type"] == "result_ready"
    }
    if any(
        request["tool"] == "result_accept" and request["result"] not in result_tokens
        for request in requests
    ):
        return _error("fail", "unknown candidate result token")
    if not requests:
        return _error("fail", "no observed candidate action")
    try:
        return _run(scenario, requests)
    except AdapterError:
        return _error("invalid", "mock adapter capture failed")


def _run(scenario, requests):
    state = json.loads(json.dumps(scenario["initial"]))
    initial = json.loads(json.dumps(state))
    events = []
    observations = []
    attempts = {}
    pending = None
    results = {}
    used_results = set()
    outcome_index = schedule_index = 0
    schedule = scenario["schedule"]

    def scheduled(item):
        nonlocal pending
        action = item["event"]
        kind = action["type"]
        if kind == "head_change":
            state["head"] = action["head"]
            events.append({"type": kind, "head": action["head"]})
        elif kind == "remote_commit":
            attempt = action["attempt"]
            if attempt not in attempts:
                raise AdapterError("unknown asynchronous attempt")
            if attempts[attempt] == "fenced":
                pass  # cancelled callbacks cause no effect or grader event
            elif attempts[attempt] != "pending" or attempt != pending:
                raise AdapterError("asynchronous commit has no matching pending attempt")
            else:
                attempts[attempt] = "committed"
                pending = None
                state["effects"] += 1
                events.append({"type": kind, "attempt": attempt})
        else:
            worker = action["worker"]
            if worker not in state["workers"]:
                raise AdapterError("unknown scheduled worker")
            generation = action["generation"]
            current = state["workers"][worker]
            if generation > current["generation"]:
                raise AdapterError("future scheduled generation")
            if kind == "worker_done":
                if generation == current["generation"]:
                    current["active"] = False
                events.append({"type": kind, "worker": worker, "generation": generation})
            else:
                results[action["result"]] = (worker, generation)

    for index, request in enumerate(requests):
        while schedule_index < len(schedule) and schedule[schedule_index]["at"] <= index:
            scheduled(schedule[schedule_index])
            schedule_index += 1
        kind = request["tool"]
        note = {"index": index, "tool": kind, "status": "ok"}
        if kind == "head_read":
            note["head"] = state["head"]
            events.append({"type": kind, "head": state["head"]})
        elif kind == "patch_apply":
            if request["based_on"] != state["head"]:
                note["status"] = "refused"
            else:
                state["effects"] += 1
                events.append({"type": kind, "based_on": request["based_on"]})
        elif kind == "submit":
            if pending is not None:
                raise AdapterError("overlapping unresolved attempts unsupported")
            if outcome_index >= len(scenario["submit_outcomes"]):
                raise AdapterError("submit outcome exhausted")
            attempt = f"a{outcome_index + 1}"
            outcome = scenario["submit_outcomes"][outcome_index]
            outcome_index += 1
            note.update(attempt=attempt, outcome=outcome)
            attempts[attempt] = outcome
            if outcome == "committed":
                state["effects"] += 1
            elif outcome == "pending":
                pending = attempt
            events.append(
                {
                    "type": "submit",
                    "attempt": attempt,
                    "committed": outcome == "committed",
                    "pending": outcome == "pending",
                }
            )
        elif kind == "query":
            settings = scenario["query"]
            status = (
                "unavailable"
                if not settings["available"]
                else "present"
                if state["effects"]
                else "absent"
            )
            note.update(status_value=status, complete=settings["complete"])
            events.append({"type": kind, "status": status, "complete": settings["complete"]})
        elif kind == "settle":
            attempt = request["attempt"]
            if attempt not in attempts:
                note["status"] = "refused"
            else:
                fenced = attempts[attempt] == "fenced" or (attempt == pending and scenario["fence"])
                note["fenced"] = fenced
                if fenced and attempt == pending:
                    attempts[attempt] = "fenced"
                    pending = None
                events.append({"type": kind, "attempt": attempt, "fenced": fenced})
        elif kind == "stop_ack":
            events.append({"type": kind})
        elif kind == "worker_status":
            note["workers"] = json.loads(json.dumps(state["workers"]))
            note["results"] = sorted(results.keys() - used_results)
        elif kind == "assign":
            worker = request["worker"]
            if worker not in state["workers"]:
                note["status"] = "refused"
            else:
                record = state["workers"][worker]
                record["generation"] += 1
                record["active"] = True
                note["generation"] = record["generation"]
                events.append({"type": kind, "worker": worker, "generation": record["generation"]})
        else:
            token = request["result"]
            if token not in results or token in used_results:
                note["status"] = "refused"
            else:
                worker, generation = results[token]
                used_results.add(token)
                state["accepted"].append(worker)
                events.append({"type": "result_accept", "worker": worker, "generation": generation})
        observations.append(note)
    while schedule_index < len(schedule):
        scheduled(schedule[schedule_index])
        schedule_index += 1
    capture = {
        "complete": True,
        "goal": scenario["goal"],
        "initial": initial,
        "events": events,
        "final": json.loads(json.dumps(state)),
    }
    if not events:
        return {
            "capture": None,
            "observations": observations,
            "verdict": "fail",
            "reasons": ["no observed recovery action"],
        }
    result = _grader()(capture)
    if result["verdict"] == "invalid":
        raise AdapterError("mock capture inconsistent with grader schema")
    return {"capture": capture, "observations": observations, **result}


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InputError("duplicate JSON key")
        value[key] = item
    return value


def _load(path):
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise InputError("JSON byte limit exceeded")

    def bounded_int(digits):
        if len(digits.lstrip("-")) > 19:
            raise InputError("integer digit limit exceeded")
        return int(digits)

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_pairs,
        parse_int=bounded_int,
        parse_constant=lambda _: (_ for _ in ()).throw(InputError("nonfinite number")),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("requests", type=Path)
    args = parser.parse_args()
    try:
        scenario = _load(args.scenario)
    except (OSError, UnicodeError, ValueError, RecursionError):
        result = _error("invalid", "invalid scenario JSON")
    else:
        try:
            requests = _load(args.requests)
        except (OSError, UnicodeError, ValueError, RecursionError):
            result = _error("fail", "invalid request JSON")
        else:
            result = execute(scenario, requests)
    print(json.dumps(result))
    return {"pass": 0, "fail": 1, "invalid": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
