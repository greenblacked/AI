#!/usr/bin/env python3
"""Check a branching dialogue or quest graph exported as plain JSON.

Standard library only. Usage:

    check_graph.py GRAPH.json [--strings STRINGS.json] [--max-chars N]

GRAPH.json:
    {"defaults": {"flag": value, ...},
     "nodes": [{"id": "a", "start": true, "ending": false,
                "line_key": "a.line", "sets": {"flag": value}}, ...],
     "edges": [{"from": "a", "to": "b",
                "when": [{"flag": "f", "op": "==", "value": true}]}, ...]}

STRINGS.json maps a line key to {locale: text}.

Prints one "node-id: code: reason" line per finding and exits 1 if there are any.
"""

import argparse
import json
import sys

OPS = ("==", "!=", ">", ">=", "<", "<=")


def reachable(starts, out):
    seen, stack = set(starts), list(starts)
    while stack:
        for nxt in out.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def sccs(ids, out):
    """Tarjan's algorithm, iterative so a long quest chain cannot hit the recursion limit."""
    index, low, on, stack, result, counter = {}, {}, set(), [], [], [0]
    for root in ids:
        if root in index:
            continue
        work = [(root, iter(out.get(root, ())))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on.add(nxt)
                    work.append((nxt, iter(out.get(nxt, ()))))
                    advanced = True
                    break
                if nxt in on:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    top = stack.pop()
                    on.discard(top)
                    comp.append(top)
                    if top == node:
                        break
                result.append(comp)
    return result


def check_graph(graph):
    findings = []
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    defaults = graph.get("defaults", {})
    out = {i: [] for i in nodes}
    for e in edges:
        for end in (e["from"], e["to"]):
            if end not in nodes:
                findings.append(
                    (
                        end,
                        "unknown-node",
                        f"edge {e['from']} -> {e['to']} names a node that is not defined",
                    )
                )
        if e["from"] in nodes and e["to"] in nodes:
            out[e["from"]].append(e["to"])

    starts = [i for i, n in nodes.items() if n.get("start")]
    if not starts:
        findings.append(("(graph)", "no-start", "no node is marked start"))
    seen = reachable(starts, out)
    for i in nodes:
        if i not in seen:
            findings.append((i, "unreachable", "no path from any start node"))
        if not out[i] and not nodes[i].get("ending"):
            findings.append((i, "dead-end", "no outgoing edge and not marked ending"))

    for comp in sccs(list(nodes), out):
        members = set(comp)
        cyclic = len(comp) > 1 or comp[0] in out[comp[0]]
        if not cyclic:
            continue
        leaves = any(t not in members for m in comp for t in out[m])
        ends = any(nodes[m].get("ending") for m in comp)
        if not leaves and not ends:
            findings.append(
                (
                    sorted(comp)[0],
                    "cycle-no-exit",
                    "cycle of " + ", ".join(sorted(comp)) + " has no edge out and no ending",
                )
            )

    # Flags that may hold a value at a node: forward union over every path.
    # Over-approximate on purpose: an error here means no path can supply it.
    values = {f: {v} for f, v in defaults.items()}
    for n in nodes.values():
        for f, v in n.get("sets", {}).items():
            values.setdefault(f, set()).add(v)
    may_set = {i: set(defaults) for i in nodes}
    for s in starts:
        may_set[s] |= set(nodes[s].get("sets", {}))
    changed = True
    while changed:
        changed = False
        for a in nodes:
            if a not in seen:
                continue
            for b in out[a]:
                new = may_set[a] | set(nodes[b].get("sets", {}))
                if not new <= may_set[b]:
                    may_set[b] |= new
                    changed = True

    for e in edges:
        a = e["from"]
        if a not in nodes:
            continue
        pinned = {}
        for c in e.get("when", []):
            flag, op, val = c["flag"], c.get("op", "=="), c.get("value")
            where = f"{a} -> {e['to']}"
            if op not in OPS:
                findings.append((a, "bad-condition", f"{where}: unknown operator {op!r}"))
                continue
            if flag not in may_set[a] and a in seen:
                findings.append(
                    (
                        a,
                        "read-before-set",
                        f"{where}: reads {flag!r}, which no path to {a} sets and has no default",
                    )
                )
                continue
            known = values.get(flag, set())
            if op == "==" and known and val not in known:
                findings.append(
                    (
                        a,
                        "never-true",
                        f"{where}: {flag} == {val!r} but only "
                        f"{sorted(map(repr, known))} are ever set",
                    )
                )
            if op == "==":
                if flag in pinned and pinned[flag] != val:
                    findings.append(
                        (
                            a,
                            "never-true",
                            f"{where}: {flag} cannot equal both {pinned[flag]!r} and {val!r}",
                        )
                    )
                pinned[flag] = val
    return findings, nodes


def check_strings(nodes, strings, max_chars):
    findings = []
    locales = sorted({loc for row in strings.values() for loc in row})
    for i, n in nodes.items():
        key = n.get("line_key")
        if key is None:
            continue
        row = strings.get(key)
        if row is None:
            findings.append((i, "missing-key", f"line key {key!r} is not in the string table"))
            continue
        for loc in locales:
            text = row.get(loc)
            if not text:
                findings.append((i, "missing-locale", f"{key!r} has no text for {loc}"))
            elif max_chars and len(text) > max_chars:
                findings.append(
                    (
                        i,
                        "too-long",
                        f"{key!r} in {loc} is {len(text)} characters, box holds {max_chars}",
                    )
                )
    return findings


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("graph")
    p.add_argument("--strings")
    p.add_argument(
        "--max-chars", type=int, default=0, help="text box capacity at the longest locale"
    )
    args = p.parse_args(argv)
    with open(args.graph, encoding="utf-8") as fh:
        graph = json.load(fh)
    findings, nodes = check_graph(graph)
    if args.strings:
        with open(args.strings, encoding="utf-8") as fh:
            findings += check_strings(nodes, json.load(fh), args.max_chars)
    for node, code, reason in findings:
        print(f"{node}: {code}: {reason}")
    print(f"{len(findings)} finding(s) in {len(nodes)} node(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
