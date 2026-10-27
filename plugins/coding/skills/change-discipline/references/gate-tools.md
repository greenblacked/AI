# Gate tools

The three gates in `SKILL.md` all work the same way: measure only what the diff touched, compare against a bar, and fail on a regression rather than on the whole repository's history. This file lists a tool for each gate per ecosystem and shows how to join the complexity and coverage halves of the CRAP score.

A flag is written here only when it was read from the tool's own `--help` output. Where a flag is not stated, the recipe says what to look for and ends with "check the tool's docs": tools rename options between releases, and a remembered flag that no longer exists fails silently in a script more often than it fails loudly. Run `<tool> --help` once before wiring any of these into a script.

## Contents

- Choosing the diff
- Complexity and coverage, per ecosystem
- Computing CRAP per changed function
- Duplication
- Mutation, scoped to the diff
- When a tool is missing

## Choosing the diff

Every gate needs the same answer to "which lines did this change touch". Fix it once and reuse it:

```bash
set -Eeuo pipefail
BASE=origin/main   # the branch this change will merge into
git -c core.quotePath=false diff --unified=0 --src-prefix=a/ --dst-prefix=b/ "$BASE" -- 'src/*.py'   # changed hunks under the source root; swap the root and pathspec per language
```

`--unified=0` makes each hunk header carry exactly the changed line range, which is what the script below reads. The prefix flags pin the `a/` and `b/` path prefixes the script parses, which a `diff.noprefix` or `diff.mnemonicPrefix` setting would otherwise change. `git diff` does not see a file git does not track yet, and a new module is usually still untracked when the gates run. Run `git add -N <file>` on each new file first, which records the intent to add it without staging its content, so the diff shows it whole. `core.quotePath=false` keeps non-ASCII file names unquoted. Use the merge base when the branch is long-lived, so that work already merged on the base is not counted as yours.

## Complexity and coverage, per ecosystem

Complexity says how many paths a function has; coverage says how many of its lines a test ran. CRAP needs both for the same function.

| Ecosystem | Complexity per function | Coverage | Notes |
| --- | --- | --- | --- |
| Python | `radon cc -j <paths>` prints JSON with each function's name, `lineno`, `endline` and `complexity`; its `endline` stops at the start of the last statement, so the script takes the real last line from `ast`. It also emits an entry of type `class` that spans the whole class and reports one combined score for it, plus the methods again on their own, and lists nested functions under `closures`; score the methods and closures, never the class entry. `lizard` also covers Python. | `coverage run` records, `coverage json` writes per-file executed and missing line lists. `--branch` adds branch data and `--include` limits the files. | The script below joins exactly these two outputs. |
| JavaScript and TypeScript | ESLint's built-in `complexity` rule reports each function over a threshold; set the threshold in config and check the tool's docs for the option. `lizard` reports every function with `--csv`. | `c8` collects V8 coverage and has `--include` and `--reporter`; Istanbul's `nyc` is the older route. Check the tool's docs for the reporter that writes per-line data. | Prefer `lizard --csv` for the join: it lists all functions, not only the ones over a limit. |
| JVM | PMD has a cyclomatic complexity rule, and `lizard` covers Java and Kotlin. | JaCoCo's XML report holds counters per method, including a complexity counter and instruction or line counters. Check the report's DTD for the exact counter names. | Coverage per method is `covered / (covered + missed)` of one counter; use the same counter every run. |
| Go | `gocyclo` prints a score per function with its file and line. Check the tool's docs for output options. | `go test -coverprofile=cover.out ./...` writes a profile, and `go tool cover -func=cover.out` prints a coverage percentage per function. | Both outputs name file and line, so the join key already exists. |
| Rust | `rust-code-analysis-cli` reports metrics per function, including cyclomatic complexity. Check the tool's docs for its output flags. | `cargo llvm-cov` reports coverage from LLVM instrumentation. Check the tool's docs for its report formats. | Coverage regions are finer than lines; pick one unit and keep it. |
| C and C++ | `lizard` with `--csv`, which handles both languages without a build. | `gcov` for GCC builds, `llvm-cov` for Clang builds. Both read data written by an instrumented test run. | Measure the source files the diff touched, not generated or vendored ones. |
| C# | `lizard` covers C#. | Check the test runner's docs for a coverage collector and its output format. | |

`lizard` takes `-l` to choose languages, `-C` to set the complexity warning threshold, `-x` to exclude paths and `-f` to read the file list from a file, which is the simplest way to hand it only the files in the diff.

## Computing CRAP per changed function

The formula is complexity squared times (1 minus coverage) cubed, plus complexity. At full coverage the score equals the complexity; at zero coverage it grows with the square, so a function of complexity 10 with no tests scores 110.

The recipe has four steps whatever the ecosystem:

1. Write the changed line ranges per file from `git diff --unified=0`.
2. Write each function's file, first line, last line and complexity from the complexity tool.
3. Write each function's covered and uncovered line counts from the coverage data, counting only lines inside its range.
4. Keep the functions whose range overlaps a changed range, compute the score, and fail when one exceeds the bar.

A Python version of all four steps, standard library only. Run it from the repository root as `python3 crap.py <base> <source-root> [limit]`. A changed file that radon lists no functions for, such as a constants module or an `__init__.py` that only re-exports, counts as having no functions and scores nothing. It expects `complexity.json` from `radon cc -j <source-root>` and `coverage.json` from `coverage json`, taken from a run with `--source=<source-root>`, in the current directory. It scores only changed files under the source root and leaves test files out of the diff, so the tools never need to measure the tests; it exits 2 when a scored file has no coverage data, when an untracked `.py` file sits under the source root (run `git add -N` on it and rerun), when a never-imported file sits in a directory with no `__init__.py` (coverage finds unrun files only inside packages, so add the `__init__.py` or set `include_namespace_packages = true` in coverage's `[run]` settings) and when git quotes a path because it holds a backslash or similar, and 1 when a changed function is over the bar:

```python
import ast
import json
import os
import re
import subprocess
import sys

base = sys.argv[1]  # e.g. origin/main
root = os.path.relpath(sys.argv[2])  # the measured source root, e.g. src
limit = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0

# Only files under the source root are scored, and test files are left out of
# the diff: the complexity and coverage runs are scoped to the source root, so a
# changed test would have no data and could only trip the guard below.
pathspec = [
    f"{root}/*.py",
    ":(exclude,glob)**/test_*.py",
    ":(exclude,glob)**/*_test.py",
    ":(exclude,glob)**/conftest.py",
    ":(exclude,glob)**/tests/**",
]
# git does not diff a file it does not track, so a new module would pass unscored.
untracked = subprocess.run(
    [
        "git",
        "-c",
        "core.quotePath=false",
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        *pathspec,
    ],
    check=True,
    capture_output=True,
    text=True,
).stdout.split("\n")
untracked = [u for u in untracked if u]
if untracked:
    print("untracked files would go unscored; run git add -N on them:")
    print("\n".join(untracked))
    sys.exit(2)
diff = subprocess.run(
    [
        "git",
        "-c",
        "core.quotePath=false",
        "diff",
        "--unified=0",
        "--diff-filter=ACMR",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        base,
        "--",
        *pathspec,
    ],
    check=True,
    capture_output=True,
    text=True,
).stdout
changed, path = {}, None
for line in diff.splitlines():
    if line.startswith('+++ "'):
        print(f"git quoted a path, which this script does not parse: {line[4:]}")
        sys.exit(2)
    if line.startswith("+++ b/"):
        path = line[6:]
    elif line.startswith("@@") and path:
        m = re.search(r"\+(\d+)(?:,(\d+))?", line)
        start, count = int(m[1]), int(m[2] or 1)
        changed.setdefault(path, set()).update(range(start, start + count))


def scorable(entries):
    # A class entry spans every method in it, so scoring it would charge a
    # covered changed method for untested code beside it. Methods are listed
    # on their own; closures nest inside the function that defines them.
    for e in entries:
        if e["type"] != "class":
            yield e
        yield from scorable(e.get("closures", []))


def last_lines(path):
    # radon's endline stops at the start of the function's last statement, so a
    # trailing assert or nested def would be left out. The ast knows the real end.
    # A decorator belongs to the function it decorates, so the span starts there.
    tree = ast.parse(open(path).read())
    return {
        n.lineno: (min([d.lineno for d in n.decorator_list] + [n.lineno]), n.end_lineno)
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


cx = json.load(open("complexity.json"))
cov = json.load(open("coverage.json"))["files"]

failed, scored = False, 0
for path, lines in changed.items():
    # With --source, coverage lists every file under the root, so a path it does
    # not name was spelled differently (an absolute path, a subdirectory prefix)
    # and would pass silently; refuse it. radon leaves out a file with no
    # functions, so a path missing there simply has nothing to score.
    if path not in cov:
        print(f"no coverage data under the path {path}")
        sys.exit(2)
    ends = last_lines(path)
    for fn in scorable(cx.get(path, [])):
        first, last = ends.get(fn["lineno"], (fn["lineno"], fn["endline"]))
        span = range(first, last + 1)
        if not lines.intersection(span):
            continue
        data = cov[path]
        hit = [n for n in data.get("executed_lines", []) if n in span]
        miss = [n for n in data.get("missing_lines", []) if n in span]
        total = len(hit) + len(miss)
        c = fn["complexity"]
        crap = c**2 * (1 - (len(hit) / total if total else 1.0)) ** 3 + c
        scored += 1
        failed |= crap > limit
        print(f"{crap:7.1f}  {path}:{fn['lineno']} {fn['name']} (complexity {c})")
print(f"scored {scored} function(s) in {len(changed)} changed file(s)")
sys.exit(1 if failed else 0)
```

For another language, keep steps 1, 3 and 4 and replace the two input readers. For Go, the `-func` output already gives coverage per function, so step 3 collapses into a lookup by file and line.

Three cautions. A change to module-level code or a deleted file touches no function in the diff, so it scores nothing and the script still exits 0, and so does a changed file with no functions in it; read the "scored" line rather than the exit code alone. A hunk that only deletes lines has an empty added range, so a function that only lost lines is never scored; if the deletion changed its behaviour, name that function and score it by hand. And a function with no executable lines in its range (an abstract method, an empty body) has nothing to cover; the script treats it as fully covered, which is correct for CRAP but worth a glance.

## Duplication

`jscpd` detects clones across most languages and, in current releases, can scope itself to the diff. Its `--help` lists these options:

| Option | What it does |
| --- | --- |
| `--min-tokens` (`-k`) | The smallest clone to report. Set it to the project's threshold; 50 is the default this skill uses. |
| `--changed` | Report only clones involving files git lists as changed, staged, unstaged or untracked. Every file is still scanned, so a changed file's clone of unchanged code is found. |
| `--changed-only` | Scan only the changed files, so they are compared with one another and not with the rest. Cheaper, and blind to a copy of existing code. |
| `--baseline-from-ref <ref>` | Build a baseline from a git ref's tree and report only clones absent from it. This is the ratchet form. |
| `--fail-on-new-clones` | Exit 1 when more than N new clones appear (default N is 0). Needs a baseline or `--changed`. |
| `--reporters` | Choose output such as `console` or `json`. |

The ratchet form is the one to prefer: `jscpd` with `--baseline-from-ref` set to the merge base and `--fail-on-new-clones` fails only on clones this diff introduced, so old duplication never blocks a new change. If the installed version lacks these options, run it over the base and the head separately and compare the clone lists by hand; check the tool's docs for the output format.

For JVM sources, PMD's copy-paste detector (CPD) is the alternative. Check the tool's docs for its minimum-token option and its output formats.

## Mutation, scoped to the diff

A mutation tool changes the code in small ways and reruns the tests. A mutant the tests ran and did not catch is a survivor; a mutant on a line no test ran is reported separately as no coverage. Both count as failures on a changed line. Running it on a whole repository takes hours, so scope it to the changed lines.

| Ecosystem | Tool | Scoping |
| --- | --- | --- |
| Python | `mutmut` | `mutmut run` accepts mutant names, so run the tool, then rerun naming only the mutants inside changed functions; `mutmut results` lists them and `mutmut show` prints one. Check the tool's docs for the name format in the installed version. `cosmic-ray` is the alternative; check the tool's docs for how it selects modules. |
| JavaScript, TypeScript, C# | Stryker | In the JavaScript runner `--mutate` takes files and accepts a line range after the file name, in the form `file:startLine-endLine`, and `--incremental` reuses earlier results so only changed code is retested. For C#, check the tool's docs for its diff option. |
| JVM | PIT | Check the tool's docs for a way to limit mutation to the classes or files changed since a git ref. |
| Rust | `cargo-mutants` | Check the tool's docs for restricting mutation to a diff or to a list of files. |
| Go | `go-mutesting` | Check the tool's docs; it takes file or package arguments, so pass only the changed files. |

A survivor or no-coverage mutant is resolved in one of three ways (for no coverage, the first way is a test that reaches the line and kills the mutant): a test that kills it, a reason it cannot matter (an equivalent mutant), or the discovery that the mutated line was dead and should be deleted. Judging equivalence is the work of `mutation-testing`. If the tool reports a survivor or no-coverage mutant in a line the change did not touch, leave it and note it as pre-existing in the ledger.

## When a tool is missing

A gate that cannot run is a stop condition in `SKILL.md`, not a pass. Report which gate and which tool, offer the cheapest install route in the project's own ecosystem, and wait. If the owner accepts skipping the gate, write that acceptance in the ledger with the date. Do not substitute a different measure under the same name: a line count is not a complexity score, and a manual look is not a mutation run.
