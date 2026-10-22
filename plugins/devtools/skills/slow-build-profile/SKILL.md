---
name: slow-build-profile
description: "Profiles a slow compile or bundle and attacks the biggest cost first. Takes three numbers before any change (clean build, incremental build after a one-line edit, no-op build), treats a no-op that does real work as a broken up-to-date check, then uses the toolchain's own profile (cargo build --timings, tsc --extendedDiagnostics, clang -ftime-trace with ClangBuildAnalyzer, Gradle --profile, ninja -d explain) and ranks by total time times fan-out. Fixes generated-file rewrites first, then the widest fan-out, then parallelism, and reports before and after. Use when someone says \"incremental builds take 90 seconds\", \"cargo build is slow\", \"tsc takes forever\", \"touching one header recompiles everything\" or \"gradle configuration is slow\". Not for runtime speed of the program (profiling), cache keys and hit rate (build-cache-miss-hunt), or pipeline structure (ci-pipeline-design)."
allowed-tools: "Read, Grep, Glob, Edit, Bash(cargo:*), Bash(npx tsc:*), Bash(tsc:*), Bash(clang:*), Bash(clang++:*), Bash(ninja:*), Bash(make:*), Bash(gradle:*), Bash(git:*)"
---

# Slow Build Profile

Done means you have three timings before and three after on the same machine and commit state, the change that moved them is named, and the remaining cost is attributed to something specific.

Slow builds attract tuning by folklore: more cores, a faster disk, a bigger cache. Most of those help a little and leave the cause untouched, because the large costs are structural. A header included by four thousand files, a generated file rewritten on every run so everything downstream rebuilds, a barrel file that drags the whole module graph into each import. Measuring first finds those; hardware hides them.

## Scope

Use for: slow clean, incremental or no-op builds of compiled or bundled projects (Rust, C and C++, TypeScript, JVM, bundlers), slow Gradle configuration, and a one-line edit that rebuilds far more than it should.

Do not use for: the speed of the program once built (`profiling`), cache keys and low hit rates on a remote cache (`build-cache-miss-hunt`), or how the CI pipeline is staged and parallelised (`ci-pipeline-design`).

## Workflow

### 1. Take three numbers

Measure on the machine where the pain is, with the editor and other builds idle, and repeat each at least three times, keeping the median.

1. **Clean build.** From an empty build directory, with dependency caches warm so you are not timing downloads.
2. **Incremental build.** After a one-line edit in a file of typical depth, not a leaf nobody imports.
3. **No-op build.** Immediately after a successful build, with nothing changed.

Write them down. The pain is almost always in the second or third, and a team that only ever times the clean build optimises the wrong one.

### 2. Check the no-op first

A no-op build should take a second or two: the tool decides everything is up to date and stops. If it does real work, the up-to-date check is broken, and that is the cheapest and largest win available because it taxes every incremental build too.

Ask the tool why it rebuilt:

```bash
ninja -d explain                      # prints the reason each edge is rebuilt
CARGO_LOG=cargo::core::compiler::fingerprint=trace cargo build   # why a crate is considered dirty
make --debug=b                        # which prerequisite was newer
gradle build --info                   # task up-to-date reasons are logged
```

Usual causes: a code generator that rewrites its output on each run even when the content is identical (the timestamp changes and everything downstream rebuilds), a build script that touches a file, a source file whose modification time is in the future, and an input glob that includes the build output directory. Fix the generator to write only when content changes, or compare before replacing.

### 3. Use the toolchain's own profile

Do not guess which step is slow. Each toolchain can say.

| Toolchain | Command | What it shows |
| --- | --- | --- |
| Rust | `cargo build --timings` | HTML timeline per crate: build time, parallelism, which crate blocks others |
| TypeScript | `tsc --extendedDiagnostics`, `tsc --generateTrace outdir` | Phase times, file counts, and a trace viewable in a trace viewer for the slowest type checks |
| C and C++ | compile with `-ftime-trace`, aggregate with ClangBuildAnalyzer | Time per header, template instantiation and file across the whole build |
| Gradle | `--profile`, or `--scan` | Configuration time against execution time, slowest tasks and plugins |
| Ninja | `ninja -d stats`, and the `.ninja_log` | Per-edge timings and the critical path |

`references/toolchain-profiles.md` gives the invocation and how to read the output for each, including the ClangBuildAnalyzer steps.

### 4. Rank by total time times fan-out

The slowest single file is rarely the best target. A header costing 400 ms to parse and included by 3,000 translation units is 20 minutes of CPU; a file costing 20 seconds once is 20 seconds. In JavaScript and TypeScript the same shape is a barrel file re-exporting an entire package so each import pulls in everything. Rank candidates by the time they cost across the whole build, and for the incremental number by how many units rebuild when they change.

### 5. Fix in order

1. Stop rewriting unchanged generated files, and fix anything broken in the no-op.
2. Cut the widest fan-out: split the large header, forward-declare instead of including, replace a barrel import with a direct one, introduce project references in TypeScript (`tsc -b` with `composite`) or split a crate along a stable interface.
3. Remove expensive repeated work: a heavy template instantiated in every unit, a procedural macro or code generator that runs every build.
4. Only then parallelism and hardware: more cores help when the profile shows idle cores on the timeline, and do nothing when one crate or one step is the critical path.

One change at a time, rerunning the relevant number after each, so you know which change paid.

### 6. Re-measure and report

Run the same three measurements the same way. Report before and after for each, the variance you saw, and what the profile now shows as the largest remaining cost. If the clean build is unchanged and the incremental improved, say so; that is usually the right trade.

## Hand back

The three baseline numbers and the three final ones, the profile evidence for each change made (the command and what it showed), the changes in order, and the largest remaining cost with a recommendation.

## Anti-patterns

**Buying hardware first.** It scales the symptom and leaves the fan-out that made every edit expensive.

**Timing only the clean build.** Developers live in the incremental loop; a clean-build win can leave their day unchanged.

**Optimising the slowest file.** Total time across the build is what counts, which fan-out decides.

**Reading a single run.** Build times vary with disk cache and thermal state; repeat and take the median.

## Reference files

- `references/toolchain-profiles.md` — read when you need the exact invocation and reading guide for a toolchain's own profiler.
