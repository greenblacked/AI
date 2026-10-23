# Phantom dependency audit by ecosystem

## Contents

- JavaScript and TypeScript
- Python
- Go
- Rust
- Monorepos
- Deciding a flagged candidate

## JavaScript and TypeScript

Strict install: `pnpm install --frozen-lockfile` with the default isolated linker. If the repository sets `node-linker=hoisted` or `shamefully-hoist=true` in `.npmrc`, the phantoms are being hidden on purpose; remove the setting on a branch for the audit and put it back only if a specific tool needs it.

Common false positives from `knip` and `depcheck`:

- Packages named only in config: Babel presets and plugins, ESLint `extends` and `plugins`, PostCSS plugins, Jest `transform`. Both tools have plugins that read these configs; check the tool recognised the config file before trusting the result, and add the config path to its entry list if not.
- Binaries used only from `scripts` in `package.json` or from CI. Check with a search for the binary name across the repository, workflows included.
- `@types/*` packages for a library that ships none. They are used by the compiler, not an import.
- Peer dependencies another package requires. Declaring them is correct even when nothing imports them.

Phantom shapes worth knowing: importing a transitive package directly (`lodash` reached through another library), a workspace package importing a sibling's dependency instead of declaring it, and a deep import into `some-lib/node_modules/other`. The last is a path hack and fails under every non-hoisted layout.

## Python

Strict environment: a fresh `python -m venv` with `pip install -r` of the declared set only. Installing the project in editable mode puts the repository root on the path, which makes local modules importable from anywhere and hides packaging mistakes; install a built wheel for the audit when the packaging itself is in question.

`deptry` codes: DEP001 missing (imported, not declared), DEP002 unused, DEP003 transitive (imported, declared only through another package), DEP004 misplaced dev dependency. Import names differ from distribution names (`yaml` is `PyYAML`, `PIL` is `Pillow`); `deptry` carries a mapping, and its per-project mapping setting covers the rest.

False positives: pytest plugins and Sphinx extensions loaded by name, `entry_points` targets, packages imported only inside a function behind a try, and optional extras.

## Go

`go mod tidy -diff` prints what tidy would change and exits non-zero when it would change anything; it needs a Go release that supports the flag. Without it, run `go mod tidy` on a clean tree and read `git diff go.mod go.sum`. A `// indirect` comment marks a module required only through another; a module the code imports directly but marked indirect is the Go phantom, and tidy corrects it.

## Rust

`cargo machete` is a fast textual check and can miss a crate used only through a macro or renamed in `Cargo.toml`; it supports an ignore list in the manifest metadata for those. `cargo udeps` is slower, needs a nightly toolchain, and works from the compiler's view rather than the text, so it has fewer false positives. A crate declared only under `[dev-dependencies]` but used in `src/` fails a normal build, so the compiler already catches that direction.

## Monorepos

Audit each package against its own manifest, never the root. A root-level dependency that satisfies every package's imports is the monorepo version of hoisting: it works until a package is published or built alone. Run the strict install for the whole workspace, then build one package in isolation (`pnpm --filter <name>... build`) to confirm it stands without its neighbours' declarations.

## Deciding a flagged candidate

1. Search the whole repository, config and CI included, for the package name and for any binary it provides.
2. Check whether another declared package lists it as a peer.
3. Remove it on a branch and run the build and the suite; a plugin loaded by name fails at start, not at compile.
4. If still unsure, keep it and write the reason beside it. An unused dependency costs install time; a wrongly removed one costs an outage.
