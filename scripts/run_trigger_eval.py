#!/usr/bin/env python3
"""Score whether a skill's or subagent's description actually triggers.

A description is the only thing loaded before a skill fires, and the usual failure is
silent: it reads well, it never triggers, and nobody finds out. This runs the committed
eval set through a model and reports the rate.

What it measures is discrimination, not just recall. Every query is judged against the
*whole* catalogue — every skill description and every subagent description in this
repository — so a description that fires on everything scores badly on the negatives
even though it passes the positives. That is the failure a single-skill test cannot see.

Three things it measures that a pass/fail line cannot:

- Routing. A negative that names the sibling which *should* win (`"expected"`) only
  passes when that sibling is chosen. Without it, a negative passes whenever anything
  other than this skill is chosen, including a completely wrong neighbour, and the
  theft the negatives exist to catch is invisible.
- Regression. `--baseline` compares every rate against a committed earlier run and
  prints the delta, because with forty descriptions competing for the same queries the
  expected consequence of editing one is a change in a neighbour's score, and a fixed
  threshold cannot see a skill slide from 100% to 85%.
- The listing budget. Claude Code shows the model a listing capped at a fraction of the
  context window, and drops the descriptions of the least-used skills when it overflows.
  `--budget` reproduces that so a description is scored the way the runtime shows it
  rather than the way it is written.

Requires the `claude` CLI on PATH and working credentials. It is deliberately not part of
the required CI gate: it costs money, it is sampled rather than deterministic, and a gate
that is occasionally wrong is a gate people learn to override.

    python scripts/run_trigger_eval.py --skill plugins/engineering/skills/ci-triage
    python scripts/run_trigger_eval.py --agent plugins/engineering/agents/ci-log-reader.md
    python scripts/run_trigger_eval.py --all --baseline evals/baseline.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import parse  # noqa: E402
from skillcheck.rules import find_agents, find_plugins, find_skills  # noqa: E402

PROMPT = """You are deciding which skill or subagent, if any, to consult for a user's message.

Available:
{catalogue}

User message:
{query}

Reply with exactly one line: the name of the single entry you would consult, or NONE if
none of them applies. No explanation, no punctuation, no other text."""

# Claude Code caps each listing entry's description at this many characters regardless
# of the overall budget (the `skillListingMaxDescChars` setting).
ENTRY_CAP = 1536


class Target:
    """One thing with a description and an eval set: a skill directory or an agent file."""

    def __init__(self, name: str, kind: str, eval_set: Path, source: Path):
        self.name = name
        self.kind = kind
        self.eval_set = eval_set
        self.source = source

    @classmethod
    def skill(cls, directory: Path) -> Target:
        return cls(directory.name, "skill", directory / "evals" / "trigger-eval.json", directory)

    @classmethod
    def agent(cls, path: Path) -> Target:
        return cls(path.stem, "subagent", path.parent / "evals" / f"{path.stem}.json", path)


def all_targets(root: Path) -> list[Target]:
    targets = [Target.skill(d) for d in find_skills(root)]
    for plugin in find_plugins(root):
        targets += [Target.agent(a) for a in find_agents(plugin / "agents")]
    return targets


def catalogue(root: Path) -> dict[str, tuple[str, str]]:
    """name -> (kind, description) for every skill and subagent."""
    entries: dict[str, tuple[str, str]] = {}
    for directory in find_skills(root):
        values = parse((directory / "SKILL.md").read_text(encoding="utf-8")).values
        entries[values["name"]] = ("skill", " ".join(values["description"].split()))
    for plugin in find_plugins(root):
        for path in find_agents(plugin / "agents"):
            values = parse(path.read_text(encoding="utf-8")).values
            entries[values["name"]] = ("subagent", " ".join(values["description"].split()))
    return entries


def render(entries: dict[str, tuple[str, str]], budget: int | None, target: str) -> str:
    """Render the listing the way the runtime would.

    Every name is always present. Each description is cut at ENTRY_CAP. When a budget
    is set and the total still exceeds it, descriptions are dropped until it fits — and
    the target's own description goes first. That is the worst case, and it is also the
    realistic one for a newly installed skill: the runtime drops the least-used entries
    first, and a skill nobody has invoked yet is by definition the least used.
    """
    described = {n: d[:ENTRY_CAP] for n, (_, d) in entries.items()}
    if budget is not None:
        order = [target] + sorted(n for n in described if n != target)
        for name in order:
            if sum(len(d) for d in described.values()) <= budget:
                break
            described[name] = ""
    lines = []
    for name in sorted(entries):
        kind = entries[name][0]
        label = f"{name} ({kind})" if kind == "subagent" else name
        lines.append(f"- {label}: {described[name]}" if described[name] else f"- {label}")
    return "\n".join(lines)


class ToolFailure(RuntimeError):
    """The model could not be reached, so no answer exists to score."""


def ask(prompt: str, model: str | None, timeout: int) -> str:
    """Return the model's choice, or raise if the tool itself failed.

    Folding a failure into the return value is the dangerous thing here. A dead CLI
    would return the same sentinel for every query, which never equals the skill name,
    which scores as a correct rejection on all ten negatives: 0% recall and 100%
    specificity. That is a plausible-looking result meaning "descriptions never fire"
    rather than "the tool is broken", and it is exactly the number the report is read
    for. Better to stop.
    """
    command = ["claude", "-p", prompt]
    if model:
        command += ["--model", model]
    try:
        result = subprocess.run(  # noqa: S603
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as error:
        raise ToolFailure("the `claude` CLI is not on PATH") from error
    except OSError as error:
        raise ToolFailure(f"could not run the `claude` CLI: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise ToolFailure(f"the `claude` CLI timed out after {timeout}s") from error

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ToolFailure(
            f"the `claude` CLI exited {result.returncode}: {detail[-1] if detail else 'no output'}"
        )
    if not result.stdout.strip():
        raise ToolFailure("the `claude` CLI returned nothing")
    return result.stdout.strip().splitlines()[-1].strip()


def judge(case: dict, chosen: str, name: str) -> tuple[bool, str]:
    """Return (passed, reason)."""
    fired = chosen == name
    if case["should_trigger"]:
        return fired, "" if fired else f"wanted {name}"
    if fired:
        return False, f"wanted not {name}"
    expected = case.get("expected")
    if expected and chosen != expected:
        # Not firing was right; where the query went instead was not. This is the
        # theft between neighbours that a plain negative cannot see.
        return False, f"routed to {chosen}, expected {expected}"
    return True, ""


def score(target: Target, entries: dict, args) -> dict:
    if not target.eval_set.is_file():
        raise SystemExit(f"{target.source} has no eval set at {target.eval_set}")
    cases = json.loads(target.eval_set.read_text(encoding="utf-8"))
    listing = render(entries, args.budget, target.name)

    results = []
    for case in cases:
        votes = Counter(
            ask(PROMPT.format(catalogue=listing, query=case["query"]), args.model, args.timeout)
            for _ in range(args.runs)
        )
        (chosen, count), *rest = votes.most_common()
        # With an odd number of runs a tie is impossible, so the margin is a real signal
        # about whether the description sits on the model's decision boundary.
        margin = count - (rest[0][1] if rest else 0)
        passed, reason = judge(case, chosen, target.name)
        results.append(
            {
                "query": case["query"],
                "should_trigger": case["should_trigger"],
                "expected": case.get("expected"),
                "chose": chosen,
                "margin": margin,
                "passed": passed,
                "reason": reason,
            }
        )
        if args.verbose:
            mark = "pass" if passed else "FAIL"
            split = f" ({count}-{count - margin} split)" if margin < args.runs else ""
            print(f"  {mark}  chose={chosen:22} {case['query'][:60]}{split}", file=sys.stderr)

    positives = [r for r in results if r["should_trigger"]]
    negatives = [r for r in results if not r["should_trigger"]]
    routed = [r for r in negatives if r["expected"]]
    rate = lambda items: sum(r["passed"] for r in items) / len(items) if items else None  # noqa: E731
    return {
        "target": target.name,
        "kind": target.kind,
        "total": len(results),
        "passed": sum(r["passed"] for r in results),
        "rate": rate(results) or 0.0,
        "recall": rate(positives) or 0.0,
        "specificity": rate(negatives) or 0.0,
        "routing": rate(routed),
        "narrow": sum(1 for r in results if r["margin"] < args.runs),
        "failures": [r for r in results if not r["passed"]],
    }


def _write(path: Path | None, reports: list[dict]) -> None:
    if path:
        path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")


def _load_baseline(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    if not path.is_file():
        raise SystemExit(f"no baseline at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r.get("target", r.get("skill")): r["rate"] for r in data}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--skill", type=Path, help="path to one skill directory")
    which.add_argument("--agent", type=Path, help="path to one subagent .md file")
    which.add_argument(
        "--all", action="store_true", help="every skill and subagent with an eval set"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="samples per query, majority wins; must be odd so a tie cannot be broken by luck",
    )
    parser.add_argument("--threshold", type=float, default=0.8, help="minimum pass rate")
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="listing budget in characters; the runtime's default is about 1%% of the "
        "context window, roughly 8000 for a 200k model",
    )
    parser.add_argument(
        "--baseline", type=Path, default=None, help="an earlier --json output to diff against"
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", type=Path, default=None, help="write full results here")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.runs < 1 or args.runs % 2 == 0:
        parser.error("--runs must be a positive odd number, so that a vote cannot tie")

    root = args.root.resolve()
    if args.all:
        targets = [t for t in all_targets(root) if t.eval_set.is_file()]
    elif args.skill:
        targets = [Target.skill(args.skill.resolve())]
    else:
        targets = [Target.agent(args.agent.resolve())]
    if not targets:
        print("nothing has an eval set", file=sys.stderr)
        return 2

    baseline = _load_baseline(args.baseline)
    entries = catalogue(root)

    reports = []
    for target in targets:
        print(f"scoring {target.name}", file=sys.stderr)
        try:
            reports.append(score(target, entries, args))
        except ToolFailure as error:
            print(f"\naborting: {error}", file=sys.stderr)
            print(
                "Scores so far are written out; nothing is reported for the rest, "
                "because a run that cannot reach the model has no result to report.",
                file=sys.stderr,
            )
            _write(args.json, reports)
            return 2
        # Written after every target rather than at the end, so a timeout or an
        # interruption does not discard scores that have already been paid for.
        _write(args.json, reports)

    header = (
        f"{'target':22} {'rate':>6} {'recall':>7} {'specificity':>12} {'routing':>8} {'narrow':>7}"
    )
    if baseline:
        header += f" {'delta':>7}"
    print(f"\n{header}")
    for report in reports:
        routing = f"{report['routing']:>8.0%}" if report["routing"] is not None else f"{'-':>8}"
        line = (
            f"{report['target']:22} {report['rate']:>6.0%} {report['recall']:>7.0%} "
            f"{report['specificity']:>12.0%} {routing} {report['narrow']:>7}"
        )
        if baseline:
            before = baseline.get(report["target"])
            line += f" {report['rate'] - before:>+7.0%}" if before is not None else f" {'new':>7}"
        print(line)

    failing = [r for r in reports if r["rate"] < args.threshold]
    for report in failing:
        print(f"\n{report['target']} below threshold — misses:", file=sys.stderr)
        for failure in report["failures"]:
            print(
                f"  {failure['reason']}, chose {failure['chose']}: {failure['query']}",
                file=sys.stderr,
            )
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
