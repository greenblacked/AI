"""The narrative graph checker: its fixture, each finding code, and how it exits."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/gamedev/skills/game-narrative-graph-check"

spec = importlib.util.spec_from_file_location("check_graph", SKILL / "scripts/check_graph.py")
assert spec is not None
assert spec.loader is not None
graph_check = importlib.util.module_from_spec(spec)
sys.modules["check_graph"] = graph_check
spec.loader.exec_module(graph_check)


def codes(graph: dict) -> set[tuple[str, str]]:
    findings, _ = graph_check.check_graph(graph)
    return {(node, code) for node, code, _ in findings}


def test_fixture_reports_exactly_the_expected_findings(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [
        str(SKILL / "fixtures/graph.json"),
        "--strings",
        str(SKILL / "fixtures/strings.json"),
        "--max-chars",
        "40",
    ]
    assert graph_check.main(argv) == 1
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "finding" not in ln]
    got = sorted(":".join(ln.split(":")[:2]) for ln in lines)
    expected = (SKILL / "fixtures/expected.txt").read_text(encoding="utf-8").splitlines()
    assert got == sorted(expected)


def test_clean_graph_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    graph = {
        "nodes": [{"id": "a", "start": True}, {"id": "b", "ending": True}],
        "edges": [{"from": "a", "to": "b"}],
    }
    path = tmp_path / "g.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    assert graph_check.main([str(path)]) == 0
    assert "0 finding(s) in 2 node(s)" in capsys.readouterr().out


def test_missing_start_is_reported() -> None:
    graph = {"nodes": [{"id": "a", "ending": True}], "edges": []}
    assert ("(graph)", "no-start") in codes(graph)


def test_edge_to_undefined_node_is_reported() -> None:
    graph = {
        "nodes": [{"id": "a", "start": True, "ending": True}],
        "edges": [{"from": "a", "to": "ghost"}],
    }
    assert ("ghost", "unknown-node") in codes(graph)


def test_self_loop_without_exit_is_a_cycle() -> None:
    graph = {
        "nodes": [{"id": "a", "start": True}],
        "edges": [{"from": "a", "to": "a"}],
    }
    assert ("a", "cycle-no-exit") in codes(graph)


def test_cycle_with_an_exit_is_allowed() -> None:
    graph = {
        "nodes": [{"id": "a", "start": True}, {"id": "b"}, {"id": "end", "ending": True}],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
            {"from": "b", "to": "end"},
        ],
    }
    assert not {c for c in codes(graph) if c[1] == "cycle-no-exit"}


def test_long_chain_does_not_hit_the_recursion_limit() -> None:
    size = 3000
    nodes = [{"id": f"n{i}", "start": i == 0, "ending": i == size - 1} for i in range(size)]
    edges = [{"from": f"n{i}", "to": f"n{i + 1}"} for i in range(size - 1)]
    assert codes({"nodes": nodes, "edges": edges}) == set()


def test_unknown_operator_is_reported() -> None:
    graph = {
        "defaults": {"f": 1},
        "nodes": [{"id": "a", "start": True}, {"id": "b", "ending": True}],
        "edges": [{"from": "a", "to": "b", "when": [{"flag": "f", "op": "~=", "value": 1}]}],
    }
    assert ("a", "bad-condition") in codes(graph)


def test_contradictory_conditions_on_one_edge_never_hold() -> None:
    cond = [
        {"flag": "f", "op": "==", "value": 1},
        {"flag": "f", "op": "==", "value": 2},
    ]
    graph = {
        "defaults": {"f": 1},
        "nodes": [
            {"id": "a", "start": True, "sets": {"f": 2}},
            {"id": "b", "ending": True},
        ],
        "edges": [{"from": "a", "to": "b", "when": cond}],
    }
    assert ("a", "never-true") in codes(graph)


def test_flag_set_on_the_path_is_not_read_before_set() -> None:
    graph = {
        "nodes": [
            {"id": "a", "start": True, "sets": {"seen": True}},
            {"id": "b"},
            {"id": "c", "ending": True},
        ],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "c", "when": [{"flag": "seen", "op": "==", "value": True}]},
        ],
    }
    assert not {c for c in codes(graph) if c[1] == "read-before-set"}


def test_string_table_findings() -> None:
    nodes = {"a": {"line_key": "a.line"}, "b": {"line_key": "b.line"}, "c": {}}
    strings = {"a.line": {"en": "short", "de": "this one is far too long"}, "x": {"en": "y"}}
    got = {(n, c) for n, c, _ in graph_check.check_strings(nodes, strings, 10)}
    assert got == {("a", "too-long"), ("b", "missing-key")}


def test_max_chars_zero_disables_the_length_check() -> None:
    nodes = {"a": {"line_key": "a.line"}}
    strings = {"a.line": {"en": "x" * 500}}
    assert graph_check.check_strings(nodes, strings, 0) == []


def test_duplicate_node_id_is_reported_and_first_occurrence_is_judged() -> None:
    graph = {
        "nodes": [
            {"id": "a", "start": True},
            {"id": "b", "ending": True},
            {"id": "b"},
        ],
        "edges": [{"from": "a", "to": "b"}],
    }
    findings, nodes = graph_check.check_graph(graph)
    assert ("b", "duplicate-node") in {(n, c) for n, c, _ in findings}
    # The later, non-ending "b" must not overwrite the first one and cause a dead-end.
    assert ("b", "dead-end") not in {(n, c) for n, c, _ in findings}
    assert nodes["b"].get("ending") is True
