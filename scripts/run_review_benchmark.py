#!/usr/bin/env python3
"""Measure the output quality of the `reviewer` subagent, not just whether it is picked.

A trigger eval (`run_trigger_eval.py`) only asks whether a description gets `reviewer`
chosen. It says nothing about what comes back once it is: whether a seeded defect from
`docs/review-lessons.md` is actually caught, or whether a clean, honest change is waved
through rather than stalled on an invented objection. This measures that instead, the
same way the trigger harness measures routing: against a committed set of cases, through
the real CLI, reported as a rate.

Each case under `.claude/agents/benchmarks/reviewer/<case>/` is a small unified diff
(`change.patch`) and a `case.json` describing it — `"kind": "defect"` seeds one class
from the lessons file as a plausible, small patch against today's tree; `"kind":
"clean"` is an honest change that should ship. A defect case passes when `reviewer`
returns `FIX` or `STOP` and every `must_mention` regex matches its report; a clean case
passes on `SHIP`. The two rates that come back — catch rate over the defects, false-alarm
rate over the clean cases — are what this measures, and they cost real money per run: the
harness runs the actual `reviewer` subagent through the `claude` CLI, once per case per
`--runs`.

Each case runs in an isolated `git worktree`, detached from `HEAD`, with its patch
applied there and nowhere else — the repository's own tree is never touched. The
worktree is always removed afterwards, whether the case passed, failed or errored.

    python scripts/run_review_benchmark.py
    python scripts/run_review_benchmark.py --case stale-count-in-prose
    python scripts/run_review_benchmark.py --json /tmp/reviewer-benchmark.json
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCHMARK_DIR = "benchmarks/reviewer"
# Line-anchored, so "no verdict: FIX yet" buried in a sentence never matches — the
# line has to *lead* with "Verdict:", optionally behind Markdown decoration a model
# reaches for on its own: a heading (#), a blockquote (>), a bullet (- or *), bold or
# italic (** or _) or an inline-code backtick, in any combination. The word itself may
# also sit inside its own bold or italic wrapper ("Verdict: **FIX**"); a wrapper after
# the word ("**Verdict: SHIP**") needs no special handling since `\b` already stops at
# the closing `*`. Still only SHIP, FIX or STOP count; `.search()` takes the first
# match anywhere in the report, not only on the literal first line.
VERDICT_RE = re.compile(
    # `\b` will not do for the closing boundary: an italic wrapper closes with `_`,
    # which regex treats as a word character, so "FIX_" would fail a `\b` check right
    # where it should pass. A following letter is the only thing that actually needs
    # to be excluded (to keep "SHIPPING" from reading as "SHIP"); a lookahead against
    # one, rather than `\b`, is what lets a closing `_`, `*` or backtick through.
    r"^[ \t]*(?:[#>*_`-]+\s*)*Verdict:\s*(?:[*_`]+\s*)?(SHIP|FIX|STOP)(?![A-Za-z])",
    re.M,
)


def _git() -> str:
    """The resolved path to `git`, so every call below carries a full path rather than
    the bare name a partial-path lint would flag."""
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is not on PATH")
    return git


class ToolFailureError(RuntimeError):
    """The CLI itself could not be reached or answered nothing usable."""


class PatchFailureError(RuntimeError):
    """A case's patch does not apply to the current tree; the case is unusable."""


def build_prompt(intent: str, head_sha: str) -> str:
    """The brief `reviewer` is handed, following reviewer.md's "What the caller passes".

    The base is resolved by the runner itself and stated as a commit, not left for
    `reviewer` to compute with a shell variable: `--allowedTools` matches each
    subcommand of a compound line independently, and does not match past a variable
    assignment or a command substitution such as ``base=$(...)``, so a command built
    that way is denied outright under `--permission-mode dontAsk` however read-only it
    is. Naming the commit and asking for `git diff HEAD` and `git status` run on their
    own is what keeps every command `reviewer` needs a plain, individually-allowable
    one. This covers how to run the commands, not what to look for: the intent is the
    caller's, verbatim, and what to look hardest at is deliberately omitted, because
    telling the harness what the defect is would be scoring whether it can read a hint
    rather than whether it finds the thing itself.
    """
    return (
        f"The change is the uncommitted working tree against HEAD, commit {head_sha}. "
        "The base is HEAD; diff with `git diff HEAD` and `git status`. Run each command "
        "on its own, without shell variables or command substitution. This is the loop "
        "it is in: /ship, meaning a finished change built by implementer.\n\n"
        "User message:\n" + intent.strip() + "\n\n"
        "Reply exactly as your system prompt specifies: Verdict first, then Findings, "
        "Evidence, Not assessed and Handoff."
    )


# Least-privilege at the command-prefix level, not a read-only guarantee. Passed with
# `--allowedTools` under `--permission-mode dontAsk`: that mode denies anything not
# listed here rather than prompting for it, so a step reviewer.md actually calls for
# has to be named explicitly or the run starves on denials instead of reviewing
# anything. It narrows what `reviewer` can *reach for*, not what those commands can
# themselves do: `git diff --output=<path>` and `git log --output=<path>` write a file
# anywhere the process can, and `make test` / `python3 -m pytest` execute whatever is
# in the worktree's own `tests/`. Nothing here catches either — the deny list below and
# the throwaway `git worktree` bound the damage a rule this coarse cannot rule out by
# itself, they do not make it impossible.
# `test_allowed_tools_contains_no_obvious_write_or_network_command_name` in
# tests/test_review_benchmark.py holds only the prefixes themselves to that lower bar.
# The space form (`Bash(git diff *)`) is preferred over
# the equivalent colon form per code.claude.com's permissions docs; a compound command
# is split on `&&`, `||`, `;`, `|`, `|&`, `&` and newlines and each piece checked
# against this list on its own, which is also why the brief asks `reviewer` to run each
# command separately rather than chaining them — and an allow rule does not match past
# a shell assignment such as `X=... command`, which is why the PYTHONPATH-prefixed form
# of the skillcheck invocation is not listed below; it would never match and only
# widens the constant without doing anything.
ALLOWED_TOOLS = (
    "Read",
    "Grep",
    "Glob",
    # The reads reviewer.md's "Establish what changed" step runs, plus the commit the
    # runner resolves and states so `reviewer` never needs a shell variable for it.
    "Bash(git diff *)",
    "Bash(git status *)",
    "Bash(git log *)",
    "Bash(git show *)",
    "Bash(git ls-files *)",
    "Bash(git rev-parse *)",
    # The four gates reviewer.md runs itself rather than trusting a claim they passed.
    "Bash(make validate)",
    "Bash(make catalogue)",
    "Bash(make test)",
    "Bash(make coverage)",
    # The same check run directly, the way docs/ci.md's "reproducing a failure"
    # section shows it. Not also listed with a PYTHONPATH= prefix: an allow rule does
    # not match past a shell variable assignment, so that form would never match and
    # would only be dead weight here.
    "Bash(python3 -m skillcheck *)",
    "Bash(python3 -m pytest *)",
)

# Deny rules are evaluated before allow rules and win, including inside a substitution
# or a subshell, so this is the actual backstop rather than the allowlist above: write,
# history-rewriting and network-reaching git subcommands, the plain network and file-
# deletion tools, and the two package installers, plus the three editing tool names
# `disallowedTools` accepts directly. `test_nothing_is_both_allowed_and_denied` holds
# that this list and `ALLOWED_TOOLS` never name the same thing.
DISALLOWED_TOOLS = (
    "Bash(git push *)",
    "Bash(git fetch *)",
    "Bash(git pull *)",
    "Bash(git clone *)",
    "Bash(git remote *)",
    "Bash(git reset *)",
    "Bash(git checkout *)",
    "Bash(git worktree *)",
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(rm *)",
    "Bash(ssh *)",
    "Bash(scp *)",
    "Bash(nc *)",
    "Bash(pip *)",
    "Bash(npm *)",
    "Write",
    "Edit",
    "NotebookEdit",
)


def build_command(
    command_template: str | None,
    model: str | None,
    max_turns: int,
    max_budget_usd: float,
) -> list[str]:
    """Return the argv to run per case, with `{prompt}` still to be substituted.

    Not `--bare`: that skips loading `.claude/agents/`, and `reviewer` lives there.
    """
    if command_template:
        argv = shlex.split(command_template)
        if not any("{prompt}" in part for part in argv):
            raise ValueError("--command must contain {prompt}, or the model is never asked")
        return argv
    # `--allowedTools, --allowed-tools <tools...>` (per `claude -p --help`) is
    # variadic: it consumes every following argv element until the next token that
    # looks like a flag. A single comma-joined string was one such element and safe
    # either way, but a rule with a literal space in it — every `Bash(git diff *)`
    # entry here — reads as several arguments if this ever changes to pass the list
    # unquoted, so each rule is its own argv element rather than one joined string.
    # The prompt goes right after `-p`, before either variadic flag starts, so it is
    # never swallowed into the tools list that follows it.
    argv = [
        "claude",
        "-p",
        "{prompt}",
        "--agent",
        "reviewer",
        "--output-format",
        "json",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        *ALLOWED_TOOLS,
        "--disallowedTools",
        *DISALLOWED_TOOLS,
        "--max-turns",
        str(max_turns),
        "--max-budget-usd",
        str(max_budget_usd),
    ]
    if model:
        argv += ["--model", model]
    return argv


def load_cases(root: Path, name: str | None) -> list[Path]:
    base = root / ".claude" / "agents" / BENCHMARK_DIR
    if name:
        case_dir = base / name
        if not (case_dir / "case.json").is_file():
            raise SystemExit(f"no case named {name!r} under {base}")
        return [case_dir]
    if not base.is_dir():
        return []
    return sorted(p.parent for p in base.glob("*/case.json"))


def make_worktree(repo_root: Path) -> Path:
    holding = Path(tempfile.mkdtemp(prefix="reviewer-bench-"))
    target = holding / "wt"
    try:
        subprocess.run(  # noqa: S603
            [_git(), "worktree", "add", "--detach", str(target), "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        # `mkdtemp` above already created `holding` before `git worktree add` had a
        # chance to fail; nothing removes it unless this does.
        shutil.rmtree(holding, ignore_errors=True)
        raise
    return target


def head_sha(worktree: Path) -> str:
    """The commit the worktree is detached at, stated in the brief so `reviewer` never
    has to compute it itself with a shell variable `--allowedTools` cannot see past."""
    result = subprocess.run(  # noqa: S603
        [_git(), "rev-parse", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def remove_worktree(repo_root: Path, worktree: Path) -> None:
    subprocess.run(  # noqa: S603
        [_git(), "worktree", "remove", "--force", str(worktree)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    shutil.rmtree(worktree.parent, ignore_errors=True)


def apply_patch(worktree: Path, patch_path: Path, case_name: str) -> None:
    result = subprocess.run(  # noqa: S603
        [_git(), "apply", str(patch_path)],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise PatchFailureError(f"{case_name}: patch did not apply: {detail}")


def parse_json_result(stdout: str) -> dict:
    """Return the CLI's JSON object, tolerating a preamble line before or after it.

    Real `--output-format json` output is one JSON object, sometimes pretty-printed
    across lines; a stand-in CLI used for testing may print a line of chatter first.
    Try the whole thing, then fall back to the last line that parses as an object.
    """
    stripped = stdout.strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise ToolFailureError("no JSON object found in the CLI's output")


def model_costs(data: dict) -> list[tuple[str, float | None]]:
    """Every model `modelUsage` names, with its own cost — not just the first key.

    A run can show cost split across more than one model in the same result — a cheap
    model for a small step alongside the one `--agent reviewer` actually reviews with —
    and reporting only the first key hides exactly the question this is for: whether
    the frontmatter's `model:` is the one that did the review, or something else spent
    most of the budget instead.
    """
    usage = data.get("modelUsage")
    if not isinstance(usage, dict):
        return []
    costs = []
    for name, info in usage.items():
        if not isinstance(name, str) or not name:
            continue
        cost = info.get("costUSD") if isinstance(info, dict) else None
        costs.append((name, cost if isinstance(cost, (int, float)) else None))
    return costs


def no_verdict_detail(data: dict, report: str) -> tuple[str, dict]:
    """A short reason plus the evidence for a run that reached neither a verdict nor a
    known diagnostic (a denial, a budget or a turn limit): what the model actually
    said, so the case does not have to be re-run just to read it, and how it stopped.

    The head and tail of `report` are kept separately rather than truncating the
    middle out of one string, because the two ends are where a verdict line and a
    closing `Handoff` most often sit — a single 300-character truncation from the
    front would usually show neither.
    """
    num_turns = data.get("num_turns")
    subtype = data.get("subtype")
    stop_reason = data.get("stop_reason") or data.get("terminal_reason")
    bits = []
    if num_turns is not None:
        bits.append(f"{num_turns} turns")
    if stop_reason:
        bits.append(f"stop_reason={stop_reason}")
    if subtype:
        bits.append(f"subtype={subtype}")
    reason = "no verdict" + (f" ({', '.join(bits)})" if bits else "")
    detail = {
        "result_head": report[:300],
        "result_tail": report[-300:] if len(report) > 300 else "",
        "num_turns": num_turns,
        "subtype": subtype,
        "stop_reason": stop_reason,
    }
    return reason, detail


def command_line(argv: list[str]) -> str:
    """The argv the harness will run, shell-quoted, with the prompt elided.

    Printed before every invocation so the exact command — every allow and deny rule,
    every flag — can be checked without the report text crowding it out.
    """
    display = ["<prompt elided>" if part == "{prompt}" else part for part in argv]
    return shlex.join(display)


def ask(argv: list[str], prompt: str, cwd: Path, timeout: int) -> dict:
    """Run the CLI once and return its parsed JSON result, or raise ToolFailureError."""
    print(f"$ {command_line(argv)}", file=sys.stderr)
    resolved = [part.replace("{prompt}", prompt) for part in argv]
    tool = f"the `{resolved[0]}` CLI"
    try:
        result = subprocess.run(  # noqa: S603
            resolved,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as error:
        raise ToolFailureError(f"{tool} is not on PATH") from error
    except OSError as error:
        raise ToolFailureError(f"could not run {tool}: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise ToolFailureError(f"{tool} timed out after {timeout}s") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ToolFailureError(
            f"{tool} exited {result.returncode}: {detail[-1] if detail else 'no output'}"
        )
    return parse_json_result(result.stdout)


def denial_texts(data: dict) -> list[str]:
    """One "<tool>: <what it tried>" line per denial, so a missing allow rule can be
    read off the result rather than re-run for.

    `tool_input` almost always carries a `command` for `Bash`; a denied non-`Bash` tool
    (`Write`, `Edit`) has no such key, so the whole `tool_input` is shown instead of
    nothing. Truncated at 200 characters — enough to identify the command, not so much
    that one long denial buries the rest of the report.
    """
    texts = []
    for denial in data.get("permission_denials") or []:
        if not isinstance(denial, dict):
            continue
        tool_name = denial.get("tool_name", "?")
        tool_input = denial.get("tool_input") or {}
        detail = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(detail, str):
            detail = json.dumps(tool_input, sort_keys=True) if tool_input else ""
        if len(detail) > 200:
            detail = detail[:200] + "…"
        texts.append(f"{tool_name}: {detail}" if detail else tool_name)
    return texts


def diagnose_failure(data: dict) -> str | None:
    """A harness-level reason a run produced no usable verdict, distinct from
    `reviewer`'s own judgement.

    A denied tool call, an exhausted budget or a hit turn limit each mean the run never
    got far enough to reach a verdict; reporting them as "no verdict" would read as a
    failure of judgement rather than of the run's own headroom or allowlist, which is
    the gap this exists to make visible instead.
    """
    texts = denial_texts(data)
    if texts:
        return "permission denied: " + "; ".join(texts)
    subtype = data.get("subtype")
    if subtype == "error_max_budget_usd":
        return "budget exhausted"
    if subtype == "error_max_turns":
        return "turn limit"
    return None


def judge(case: dict, verdict: str | None, report: str) -> tuple[bool, str]:
    """Return (passed, reason) for one case given its majority verdict and report."""
    if verdict is None:
        return False, "no verdict"
    if case["kind"] == "defect":
        if verdict not in ("FIX", "STOP"):
            return False, f"verdict {verdict}, wanted FIX or STOP"
        for pattern in case.get("must_mention", []):
            if not re.search(pattern, report, re.I):
                return False, f"missing {pattern!r} in the report"
        return True, ""
    if verdict != "SHIP":
        return False, f"false alarm: verdict {verdict}, wanted SHIP"
    return True, ""


def run_case(case_dir: Path, repo_root: Path, argv: list[str], args) -> dict:
    name = case_dir.name
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    patch_path = case_dir / "change.patch"

    worktree = None
    try:
        # Inside the try rather than before it: a failed `git worktree add` still
        # leaves `make_worktree`'s `mkdtemp` directory on disk, and only `finally`
        # below cleans anything up.
        worktree = make_worktree(repo_root)
        apply_patch(worktree, patch_path, name)
        prompt = build_prompt(case["intent"], head_sha(worktree))
        runs = []
        for _ in range(args.runs):
            data = ask(argv, prompt, worktree, args.timeout)
            report = data.get("result", "")
            match = VERDICT_RE.search(report)
            runs.append(
                {
                    "verdict": match.group(1) if match else None,
                    "report": report,
                    "cost": data.get("total_cost_usd"),
                    "diagnostic": diagnose_failure(data),
                    "denials": denial_texts(data),
                    "data": data,
                }
            )
    finally:
        if worktree is not None:
            remove_worktree(repo_root, worktree)

    votes = Counter(r["verdict"] for r in runs)
    majority_verdict, _ = votes.most_common(1)[0]
    chosen = next((r for r in runs if r["verdict"] == majority_verdict), runs[0])
    passed, reason = judge(case, majority_verdict, chosen["report"])
    result_head = result_tail = ""
    num_turns = subtype = stop_reason = None
    if majority_verdict is None and chosen["diagnostic"]:
        passed, reason = False, chosen["diagnostic"]
    elif majority_verdict is None:
        reason, detail = no_verdict_detail(chosen["data"], chosen["report"])
        passed = False
        result_head = detail["result_head"]
        result_tail = detail["result_tail"]
        num_turns = detail["num_turns"]
        subtype = detail["subtype"]
        stop_reason = detail["stop_reason"]
    total_cost = sum(r["cost"] for r in runs if isinstance(r["cost"], (int, float)))
    denials = sorted({tool for r in runs for tool in r["denials"]})

    # Every model modelUsage named across every run, with its own summed cost — not
    # only the first key an earlier version reported, so a run split across a cheap
    # model and the one `reviewer`'s frontmatter actually names is visible as both.
    totals: dict[str, float | None] = {}
    for r in runs:
        for model_name, cost in model_costs(r["data"]):
            if model_name not in totals:
                totals[model_name] = cost
            elif cost is not None:
                totals[model_name] = (totals[model_name] or 0.0) + cost
    models = [
        f"{model_name} (${cost:.4f})" if cost is not None else model_name
        for model_name, cost in sorted(totals.items())
    ]

    return {
        "case": name,
        "kind": case["kind"],
        "lesson": case.get("lesson"),
        "verdict": majority_verdict,
        "passed": passed,
        "reason": reason,
        "cost_usd": total_cost,
        "models": models,
        "denials": denials,
        "runs": len(runs),
        "result_head": result_head,
        "result_tail": result_tail,
        "num_turns": num_turns,
        "subtype": subtype,
        "stop_reason": stop_reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--case", default=None, help="run a single named case")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="samples per case, majority of verdicts wins; a tie goes to whichever "
        "verdict was reached first, since nothing here breaks a tie by re-running",
    )
    parser.add_argument("--jobs", type=int, default=1, help="cases in flight at once")
    parser.add_argument("--max-turns", type=int, default=40)
    parser.add_argument("--max-budget-usd", type=float, default=2.00)
    parser.add_argument("--model", default=None, help="passed to the CLI as --model")
    parser.add_argument(
        "--command",
        default=None,
        metavar="TEMPLATE",
        help="override the CLI invocation; a shell-style template containing {prompt}",
    )
    parser.add_argument("--threshold-catch", type=float, default=0.85)
    parser.add_argument("--threshold-false-alarm", type=float, default=0.34)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--json", type=Path, default=None, help="write full results here")
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    try:
        argv = build_command(args.command, args.model, args.max_turns, args.max_budget_usd)
    except ValueError as error:
        parser.error(str(error))

    root = args.root.resolve()
    try:
        case_dirs = load_cases(root, args.case)
    except SystemExit as error:
        print(str(error), file=sys.stderr)
        return 2
    if not case_dirs:
        print("no benchmark cases found", file=sys.stderr)
        return 2

    results = []
    hard_error = False

    def one(case_dir: Path) -> dict:
        try:
            return run_case(case_dir, root, argv, args)
        except (ToolFailureError, PatchFailureError) as error:
            return {
                "case": case_dir.name,
                "kind": json.loads((case_dir / "case.json").read_text(encoding="utf-8")).get(
                    "kind"
                ),
                "verdict": None,
                "passed": False,
                "reason": str(error),
                "cost_usd": 0.0,
                "models": [],
                "denials": [],
                "runs": 0,
                "result_head": "",
                "result_tail": "",
                "num_turns": None,
                "subtype": None,
                "stop_reason": None,
                "error": True,
            }

    if args.jobs == 1:
        for case_dir in case_dirs:
            results.append(one(case_dir))
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(one, case_dirs))

    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    for r in results:
        if r.get("error"):
            hard_error = True

    defects = [r for r in results if r["kind"] == "defect"]
    clean = [r for r in results if r["kind"] == "clean"]
    catch_rate = (sum(r["passed"] for r in defects) / len(defects)) if defects else None
    false_alarm_rate = (sum(not r["passed"] for r in clean) / len(clean)) if clean else None
    total_cost = sum(r["cost_usd"] for r in results)

    print(f"{'case':32} {'kind':7} {'verdict':7} {'result':6} {'cost':>8}  reason")
    for r in results:
        verdict = r["verdict"] or "-"
        mark = "pass" if r["passed"] else "FAIL"
        cost = f"${r['cost_usd']:.2f}" if r.get("cost_usd") else "-"
        models = f" [{', '.join(r['models'])}]" if r.get("models") else ""
        print(f"{r['case']:32} {r['kind']:7} {verdict:7} {mark:6} {cost:>8}  {r['reason']}{models}")

    if catch_rate is not None:
        print(
            f"\ncatch rate: {catch_rate:.0%} ({sum(r['passed'] for r in defects)}/{len(defects)})"
        )
    if false_alarm_rate is not None:
        print(
            f"false-alarm rate: {false_alarm_rate:.0%} "
            f"({sum(not r['passed'] for r in clean)}/{len(clean)})"
        )
    print(f"total cost: ${total_cost:.2f}")

    if hard_error:
        return 2
    below = (catch_rate is not None and catch_rate < args.threshold_catch) or (
        false_alarm_rate is not None and false_alarm_rate > args.threshold_false_alarm
    )
    return 1 if below else 0


if __name__ == "__main__":
    raise SystemExit(main())
