---
name: affected-build-selection
description: "Makes a monorepo build and test only what a change can affect, without missing a regression. Affected means the change set against the merge-base mapped through the dependency graph in reverse; each step has a failure: a shallow checkout that degrades to everything or nothing, files outside the graph (lockfile, toolchain, CI config) not declared as global inputs, and a selection never proved sound. Uses the tool's query (turbo --filter with a git ref, nx affected --base), replays the last 50 merged PRs against a full run for zero false negatives, and keeps a full run on main and nightly. Use whenever someone says \"CI runs everything on every PR\", \"set up nx affected\", \"turbo missed a break\", \"which projects depend on this library\". Not for pipeline structure (ci-pipeline-design), a task re-running with unchanged inputs (build-cache-miss-hunt), or dependency cycles (refactoring)."
allowed-tools: Bash(git:*), Bash(turbo:*), Bash(nx:*), Bash(gh pr list:*), Read, Grep, Glob
---

# Affected Build Selection

Done means a pull request builds and tests exactly the projects its change can reach, the selection has been replayed against real history with no missed regression, and a full run still happens somewhere that would catch what the selection cannot.

Selecting by change is a promise that nothing outside the selection could have broken. Every gap in that promise fails silently: the build is green, the regression ships, and the cause is a selection that never ran the test. So the work is proving soundness, not turning the feature on.

## Scope

Use for: introducing or repairing affected-only builds in a monorepo, a selection that missed a break, finding which projects depend on a library.

Do not use for: shaping the whole pipeline or its required checks (`ci-pipeline-design`), or a task that re-runs although nothing changed (`build-cache-miss-hunt`).

## Workflow

### 1. Gate one: CI must hold the real merge-base

Affected is a diff against a base commit. A shallow checkout cannot find it, and the tools degrade quietly: some treat the base as missing and run everything, others see no diff and run nothing. The second is the dangerous one.

- GitHub Actions: `actions/checkout` with `fetch-depth: 0`, or fetch the base explicitly (`git fetch origin main --depth=...` deep enough to reach the merge-base; deepen until `git merge-base origin/main HEAD` succeeds).
- For a pull request, compare against the merge-base with the target branch, not the tip of the target, so unrelated landed changes are not counted. For a push to main, compare against the previous successful commit, not `HEAD~1`, so a multi-commit push and a rerun after a red build are covered.
- Add an assertion step that fails the job if `git merge-base origin/<base> HEAD` returns nothing, rather than letting the tool guess. Nx ships an `nx-set-shas` action that computes the last successful base for you.

### 2. Gate two: declare what lives outside the graph

The dependency graph knows imports between projects. It does not know that a root lockfile, a toolchain version file, a shared lint or compiler config, a Dockerfile or the CI workflow changed behaviour for everything. A change to any of them must select every project.

- Turborepo: list them in `globalDependencies` in `turbo.json` (and `globalEnv` for environment variables that change output).
- Nx: put them in a `sharedGlobals` named input in `nx.json` and include it in the inputs of every target; `namedInputs` also scopes which files inside a project count, so test-only files do not invalidate a build.
- Other tools: add a rule that these paths trigger the full set.

`references/global-inputs.md` lists the files that usually belong and how to find the ones that do not look like it.

### 3. Use the tool's own query

Do not hand-roll the diff-to-project mapping in shell; the tool's graph is the source of truth and a hand version drifts.

```bash
# Turborepo: the ... prefix includes dependents of changed packages
turbo run test --filter='...[origin/main]'
# Nx: affected projects against a base
nx affected -t build test lint --base=origin/main --head=HEAD
```

Newer Turborepo releases also offer `turbo run test --affected`, which defaults the comparison to the pull request's base in CI; confirm the installed version supports it before relying on it. To answer "which projects depend on this library": `nx graph --affected` or `nx show projects --affected --base=origin/main` for Nx, and `turbo run build --filter='...<package>' --dry=json` for Turborepo, which lists the tasks it would run without running them.

### 4. Prove soundness before trusting it

A selection is sound when it never omits a project whose result a full run would change. Measure that, do not assume it.

1. Take the last 50 merged pull requests (`gh pr list --state merged --limit 50 --json number,mergeCommit,baseRefName`).
2. For each, compute the affected set from its merge-base, run the full suite at both the first parent `P` and the merge commit `M`, and record which projects failed in each. Rerun any project whose result changed to rule out a flaky test.
3. A false negative is a project whose result changed between `P` and `M` (passing at `P`, failing at `M`) and is absent from the affected set. A project already failing at `P` is not a miss. The requirement is zero. A single one means a missing edge or an undeclared global input; find it, fix the config, rerun the replay.

`references/soundness-replay.md` has a script outline and a results table to fill in. If history has few failures, seed the replay with deliberate breaks: change a shared library's exported behaviour and check every dependent is selected.

### 5. Keep a net underneath

Run the full suite on main after every merge and on a nightly schedule, regardless of selection. This catches what the replay could not (dynamic imports, code generation, runtime configuration, a graph edge the tool cannot see) and gives a record against which the selection's miss rate can be measured over time. A full-run failure that the selection would have skipped is a soundness bug: treat it as one, with the same replay.

### 6. Roll out

Run selection in report-only mode first: compute the affected set on every pull request, log it beside the full run, and compare. Switch the gate to the selection only after the comparison is clean for a sprint. Keep an escape hatch, a label or commit trailer that forces a full run.

## Hand back

The base and head used, the global inputs declared, the command and tool version, the replay result with its count of pull requests and false negatives, the full-run cadence on main, and the remaining blind spots named (generated code, runtime config, cross-repo dependencies).

## Anti-patterns

**Trusting a shallow clone.** The failure mode is a green build that tested nothing.

**Comparing against `HEAD~1` on main.** A multi-commit merge or a rerun after a failure hides changes from earlier commits.

**Treating the cache as the selection.** A cache hit skips work already done; it does not decide what a change can reach. They fix different problems.

**Turning it on without a net.** With no full run on main, an unsound selection is never discovered.

## Reference files

- `references/global-inputs.md` — read in step 2: files that usually must invalidate everything, and how to find undeclared ones.
- `references/soundness-replay.md` — read in step 4: how to run the replay and record false negatives.
