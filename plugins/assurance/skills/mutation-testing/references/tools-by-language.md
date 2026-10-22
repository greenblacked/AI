# Mutation tools: diff-scoped runs, gates and suppression

The invocation that limits each tool to a change, where it writes results, how to make it
fail a build, and how to suppress a mutant proven equivalent. Read the section for your
stack before the first run, and confirm option names against the installed version's help
output: these tools move quickly and an old pinned release may predate an option.

## Contents

- [Turning a diff into a scope](#turning-a-diff-into-a-scope)
- [JavaScript and TypeScript: Stryker](#javascript-and-typescript-stryker)
- [C#: Stryker.NET](#c-strykernet)
- [Java and Kotlin: PIT](#java-and-kotlin-pit)
- [Python: mutmut](#python-mutmut)
- [Rust: cargo-mutants](#rust-cargo-mutants)
- [PHP: Infection](#php-infection)
- [Ruby and Go](#ruby-and-go)

## Turning a diff into a scope

Every tool below starts from the same diff, taken against the merge base so that commits
landing on `main` since the branch was cut are not counted as the change:

```bash
git fetch origin main
git diff --unified=0 origin/main...HEAD -- src/ > changed.diff
git diff --name-only --diff-filter=AMR origin/main...HEAD -- src/ > changed-files.txt
```

`AMR` rather than `AM` keeps a renamed file that was also edited, which `AM` drops from the list.

Tools that take line ranges need them out of the hunk headers. A hunk header reads
`@@ -a,b +c,d @@`; the new lines are `c` to `c + d - 1`, a missing `,d` means one line, and
`d` of zero is a pure deletion with nothing to mutate:

```python
# changed_ranges.py: print path:start-end for each added or changed hunk
import re
import sys

current = None
with open(sys.argv[1], encoding="utf-8") as diff:
    for line in diff:
        if line.startswith("+++ b/"):
            current = line[6:].strip()
        elif line.startswith("@@") and current:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, count = int(match.group(1)), int(match.group(2) or "1")
            if count:
                print(f"{current}:{start}-{start + count - 1}")
```

Filter the output to source extensions the tool understands before passing it on; a diff
under `src/` can include stylesheets and JSON.

## JavaScript and TypeScript: Stryker

- **Scope.** `--mutate` takes comma-separated globs, and each entry may carry a line range:
  `npx stryker run --mutate "src/pricing.ts:40-72,src/discount.ts:12-19"`. Build the list
  from `changed_ranges.py`. Alternatively, `--incremental` reuses the previous run's results
  from `reports/stryker-incremental.json` and re-tests only mutants whose code or covering
  tests changed; keep that file between CI runs as a cache.
- **Speed.** `"coverageAnalysis": "perTest"` in the config runs each mutant against only the
  tests that cover it.
- **Gate.** `"thresholds": { "high": 90, "low": 80, "break": 80 }` makes the run exit
  non-zero when the score falls below `break`. On a diff-scoped run that is a gate on changed
  code.
- **Results.** Statuses are Killed, Survived, NoCoverage, Timeout, CompileError,
  RuntimeError and Ignored. The HTML report under `reports/mutation/` shows each survivor in
  place.
- **Suppress.** A comment on the line before:
  `// Stryker disable next-line EqualityOperator: index starts at 0 and steps by 1, so != and < agree`.
  Name the mutator rather than `all`, so a different, real mutant on the same line still runs.

## C#: Stryker.NET

- **Scope.** The `--since` option, given the base branch, mutates only files changed since
  that commit.
- **Gate.** `--break-at` with a percentage fails the run below that score.
- **Suppress.** The same `Stryker disable` comment family as the JavaScript tool, with the
  mutator named and a reason after the colon.

## Java and Kotlin: PIT

- **Scope.** Turn `changed-files.txt` into class patterns and pass them as `targetClasses`:

  ```bash
  mvn test-compile org.pitest:pitest-maven:mutationCoverage \
    -DtargetClasses='com.example.billing.Invoice*,com.example.billing.Discount*' \
    -DwithHistory
  ```

  `withHistory` stores results between runs so unchanged classes with unchanged tests are
  not re-analysed. The plugin also offers an `scmMutationCoverage` goal that selects classes
  from version-control changes; check its options in the plugin's documentation for the
  version you use.
- **Gradle.** The `info.solidsoft.pitest` plugin exposes the same settings in a `pitest`
  block.
- **Gate.** `mutationThreshold` fails the build below a mutation score; `coverageThreshold`
  does the same for line coverage.
- **Results.** Statuses are KILLED, SURVIVED, NO_COVERAGE, TIMED_OUT, MEMORY_ERROR,
  RUN_ERROR and NON_VIABLE. Reports land under `target/pit-reports/`.
- **Mutators.** The default group is `DEFAULTS`; `STRONGER` adds more conditional mutations
  at the price of more mutants. Start with the default on a gate.
- **Suppress.** Open-source PIT has no inline suppression comment. Exclude a proven
  equivalent by method with `excludedMethods`, and write the reason beside the
  configuration. By default PIT already avoids mutating calls to the common logging
  libraries through `avoidCallsTo`.

## Python: mutmut

- **Scope.** mutmut scopes by path, not by line. Set `paths_to_mutate` in the
  `[tool.mutmut]` table of `pyproject.toml` (or the `[mutmut]` section of `setup.cfg`) to the
  changed modules from `changed-files.txt`, then discard survivors that fall outside the
  changed line ranges when triaging.
- **Run and read.** `mutmut run`, then `mutmut results` to list mutants by status,
  `mutmut show <mutant-name>` for the diff of one mutant, and `mutmut browse` for an
  interactive view.
- **Suppress.** `# pragma: no mutate` at the end of the line, with the reason in a comment
  on the line above.
- **Gate.** mutmut has no built-in threshold; fail the CI step when `mutmut results` lists a
  survivor in the changed lines.

## Rust: cargo-mutants

- **Scope.** `cargo mutants --in-diff changed.diff` generates mutants only in code the diff
  touches.
- **Results.** Written under `mutants.out/`, with `caught.txt`, `missed.txt`,
  `timeout.txt` and `unviable.txt` listing each outcome. The process exits non-zero when any
  mutant is missed, which is the gate.
- **Speed.** cargo-mutants runs the package's tests for each mutant rather than selecting
  per test, so scope matters more here than anywhere; `--jobs` runs several mutants in
  parallel in separate build directories.
- **Suppress.** `#[mutants::skip]` on the function, which needs the small `mutants` crate as
  a dependency, with the reason in a comment above it. `exclude_re` in
  `.cargo/mutants.toml` excludes by name pattern.

## PHP: Infection

- **Scope and gate in one command:**

  ```bash
  vendor/bin/infection --git-diff-lines --git-diff-base=origin/main --min-covered-msi=100 --threads=4
  ```

  `--git-diff-lines` restricts mutation to changed lines; `--git-diff-filter=AM` instead
  restricts it to added and modified files. `--min-msi` gates on the score over all mutants,
  `--min-covered-msi` on the score over covered code only, which is the one to use when
  survivors and no-coverage are being handled separately.
- **Suppress.** An `@infection-ignore-all` annotation in the class or method docblock, or a
  per-mutator `ignore` list in `infection.json5` naming the method, with the reason beside it.

## Ruby and Go

- **Ruby: mutant.** Its `--since` option restricts mutation to subjects changed since a
  given revision, which is the diff-scoped run.
- **Go.** gremlins (`gremlins unleash`) and go-mutesting both mutate by package. Scope the run
  to the packages in `changed-files.txt` and triage only survivors inside the changed line
  ranges.
