#!/usr/bin/env python3
"""Score whether a skill's description actually triggers.

A description is the only thing loaded before a skill fires, and the usual failure is
silent: it reads well, it never triggers, and nobody finds out. This runs the committed
eval set through a model and reports the rate.

What it measures is discrimination, not just recall. Every query is judged against the
*whole* catalogue of skill descriptions in this repository, so a description that fires
on everything scores badly on the negatives even though it passes the positives. That is
the failure a single-skill test cannot see.

Requires the `claude` CLI on PATH and working credentials. It is deliberately not part of
the required CI gate: it costs money, it is sampled rather than deterministic, and a gate
that is occasionally wrong is a gate people learn to override.

    python scripts/run_trigger_eval.py --skill skills/engineering/ci-triage
    python scripts/run_trigger_eval.py --all --runs 3 --threshold 0.8
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
from skillcheck.rules import find_skills  # noqa: E402

PROMPT = """You are deciding which skill, if any, to consult for a user's message.

Available skills:
{catalogue}

User message:
{query}

Reply with exactly one line: the name of the single skill you would consult, or NONE if
none of them applies. No explanation, no punctuation, no other text."""


def catalogue(root: Path) -> dict[str, str]:
    entries = {}
    for directory in find_skills(root / "skills"):
        values = parse((directory / "SKILL.md").read_text(encoding="utf-8")).values
        entries[values["name"]] = " ".join(values["description"].split())
    return entries


def ask(prompt: str, model: str | None, timeout: int) -> str:
    command = ["claude", "-p", prompt]
    if model:
        command += ["--model", model]
    try:
        result = subprocess.run(  # noqa: S603
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"__error__ {error}"
    return result.stdout.strip().splitlines()[-1].strip() if result.stdout.strip() else "__empty__"


def score_skill(directory: Path, root: Path, args) -> dict:
    name = directory.name
    entries = catalogue(root)
    listing = "\n".join(f"- {n}: {d}" for n, d in sorted(entries.items()))
    cases = json.loads((directory / "evals" / "trigger-eval.json").read_text(encoding="utf-8"))

    results = []
    for case in cases:
        votes = Counter(
            ask(PROMPT.format(catalogue=listing, query=case["query"]), args.model, args.timeout)
            for _ in range(args.runs)
        )
        chosen = votes.most_common(1)[0][0]
        fired = chosen == name
        results.append(
            {
                "query": case["query"],
                "should_trigger": case["should_trigger"],
                "chose": chosen,
                "passed": fired == case["should_trigger"],
            }
        )
        if args.verbose:
            mark = "pass" if results[-1]["passed"] else "FAIL"
            print(f"  {mark}  chose={chosen:18} {case['query'][:70]}", file=sys.stderr)

    passed = sum(r["passed"] for r in results)
    positives = [r for r in results if r["should_trigger"]]
    negatives = [r for r in results if not r["should_trigger"]]
    return {
        "skill": name,
        "total": len(results),
        "passed": passed,
        "rate": passed / len(results) if results else 0.0,
        "recall": (sum(r["passed"] for r in positives) / len(positives) if positives else 0.0),
        "specificity": (sum(r["passed"] for r in negatives) / len(negatives) if negatives else 0.0),
        "failures": [r for r in results if not r["passed"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--skill", type=Path, help="path to one skill directory")
    target.add_argument("--all", action="store_true", help="every skill with an eval set")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--runs", type=int, default=1, help="samples per query (majority wins)")
    parser.add_argument("--threshold", type=float, default=0.8, help="minimum pass rate")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", type=Path, default=None, help="write full results here")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.all:
        targets = [d for d in find_skills(root / "skills") if (d / "evals").is_dir()]
    else:
        targets = [args.skill.resolve()]
    if not targets:
        print("no skill has an eval set", file=sys.stderr)
        return 2

    reports = []
    for directory in targets:
        print(f"scoring {directory.name}", file=sys.stderr)
        reports.append(score_skill(directory, root, args))

    print(f"\n{'skill':22} {'rate':>6} {'recall':>7} {'specificity':>12}")
    for report in reports:
        print(
            f"{report['skill']:22} {report['rate']:>6.0%} {report['recall']:>7.0%} "
            f"{report['specificity']:>12.0%}"
        )

    if args.json:
        args.json.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")

    failing = [r for r in reports if r["rate"] < args.threshold]
    for report in failing:
        print(f"\n{report['skill']} below threshold — misses:", file=sys.stderr)
        for failure in report["failures"]:
            want = report["skill"] if failure["should_trigger"] else "not " + report["skill"]
            print(f"  wanted {want}, chose {failure['chose']}: {failure['query']}", file=sys.stderr)
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
