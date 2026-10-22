# Toolchain profiles

## Contents

- Rust
- TypeScript
- C and C++
- Gradle
- Ninja and Make
- Reading a profile for fan-out

## Rust

`cargo build --timings` writes an HTML report under `target/cargo-timings/`. The chart shows each crate as a bar against time, with the number of concurrently running units beneath. Two readings matter: a long bar that others wait on (the critical path; making that crate smaller or splitting it frees everything behind it), and a stretch with few running units (parallelism is lost, so more cores will not help there).

For why a crate rebuilds, `CARGO_LOG=cargo::core::compiler::fingerprint=trace cargo build` prints the fingerprint comparison that marked it dirty. Frequent culprits: a `build.rs` without `cargo:rerun-if-changed` lines (so it reruns on any change), environment variables read by the compiler, and alternating invocations that select different packages or features (a single-package build and a `--workspace` build can resolve features differently and so rebuild each other's dependencies).

## TypeScript

```bash
npx tsc --extendedDiagnostics --noEmit
npx tsc --generateTrace trace-dir --noEmit
```

`--extendedDiagnostics` reports file count, lines, memory, and time per phase (parse, bind, check, emit). Many files with a short check phase points at module graph size; a long check phase points at expensive types. The trace directory holds `trace.json` and `types.json`: open the trace in a Chromium-based trace viewer and look at the longest `checkSourceFile` and type-instantiation spans. `tsc --listFiles` shows what is in the program, which exposes accidental inclusion of `node_modules` types or build output.

Structural fixes: project references (`composite`, `references`, built with `tsc -b`) so unchanged projects are skipped, `incremental` with a `tsBuildInfoFile`, narrower `include` globs, and `skipLibCheck` when declaration checking of dependencies is the cost (a trade-off; say that you made it).

## C and C++

Compile with `-ftime-trace` (clang). Each object gets a JSON next to it. Aggregate across the build with ClangBuildAnalyzer:

```bash
ClangBuildAnalyzer --start build/
# run the build
ClangBuildAnalyzer --stop build/ capture.bin
ClangBuildAnalyzer --analyze capture.bin
```

The report lists the files that took longest to parse and to optimise, the headers with the highest cumulative include cost (the fan-out ranking), and the most expensive template instantiations. Act on the include ranking first: forward declarations, splitting a header that mixes cheap and heavy declarations, precompiled headers for a stable heavy set. Unity builds trade incremental speed for clean speed; measure both numbers before adopting.

## Gradle

`gradle build --profile` writes an HTML report under `build/reports/profile/` splitting configuration, task execution and dependency resolution. `--scan` gives the same in a build scan with the timeline. A long configuration phase on every invocation, with fast tasks, points at build logic doing work at configuration time (reading files, running commands, resolving configurations eagerly); the fix is lazy task configuration and moving that work into task actions. The configuration cache removes repeated configuration when build logic is compatible with it.

## Ninja and Make

`ninja -d explain` states why each edge is dirty. `ninja -n -d explain` does it without building. `.ninja_log` in the build directory records the start and end time in milliseconds of each edge (its columns are tab-separated); `ninja -d stats` does not, as it prints only internal counters. `ninjatracing` converts the log into a trace for a viewer such as Perfetto. Sorting by duration gives the slowest steps, and the longest chain of dependent edges is the critical path. For Make, `make --debug=b` shows which prerequisite triggered each rebuild, and `make -n` previews without running.

## Reading a profile for fan-out

For each candidate (header, module, barrel file), compute:

- cost per use, from the profile,
- number of units that include or import it, from the include graph or the tool's report,
- product of the two (build cost), and the number of units rebuilt when it changes (incremental cost).

Sort by the product and by incremental cost separately; they often name different targets. A file high on both is the first change to make.
