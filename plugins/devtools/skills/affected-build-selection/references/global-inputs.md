# Global inputs

A global input is a file whose change can alter any project's result although no project imports it. Declare each so that changing it selects every project.

## Usual suspects

| File or group | Why it is global |
| --- | --- |
| Root lockfile (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`) | Resolves every dependency of every project. Some tools diff the lockfile per package; confirm yours does before relying on it, otherwise treat it as global |
| Toolchain version (`.nvmrc`, `.node-version`, `.tool-versions`, `rust-toolchain.toml`, `go.mod`'s go line) | A compiler or runtime change affects all output |
| Root configs (`tsconfig.base.json`, `.eslintrc*`, `babel.config.*`, `jest.preset.*`, `pyproject.toml` at the root) | Inherited by every project |
| Build tool config (`turbo.json`, `nx.json`, workspace files) | Changes what a target means |
| CI workflow and shared scripts (`.github/workflows/*`, `scripts/ci/*`) | Changes how things are built and tested |
| Container and environment definitions (`Dockerfile`, `docker-compose.yml`, `.env.example`) | Changes the environment tests run in |
| Code generation inputs (schemas, protobuf, OpenAPI documents) | Outputs feed projects the graph does not link |

## Finding undeclared ones

1. List every file in the repository outside any project directory: `git ls-files | grep -v -E '^(apps|packages|libs)/'` (adjust to your layout). Read the list once and mark each as global or irrelevant.
2. Replay the last year of commits that touched only those files: `git log --since='1 year ago' --name-only --pretty=format: -- . ':!apps' ':!packages' ':!libs' | sort | uniq -c | sort -rn | head -30`. For each frequently changed file, ask what broke when it changed.
3. For each commit that changed only non-project files, run the full suite at that commit and at its parent and note any difference. A difference is an undeclared global input.

## Where each tool takes the declaration

| Tool | Setting |
| --- | --- |
| Turborepo | `globalDependencies` (files) and `globalEnv` (environment variables) in `turbo.json`; per-task `inputs` narrows what counts for one task |
| Nx | `namedInputs` in `nx.json` with a shared set (conventionally `sharedGlobals`) referenced by each target's `inputs` |
| Bazel and Pants | The build graph already owns file inputs; the gap is files outside any target, so check them with `bazel query` or the tool's equivalent |
| Custom scripts | A path-prefix rule that bypasses the filter and selects all |
