# Tools by ecosystem

For each: how to see the chain, where the constraint goes, where the override goes.

## npm

- See: the error prints `Found:` (what is installed) and `Could not resolve dependency` with a `peer` line. `npm explain <pkg>` prints every path that pulls the package, with the range at each step; `npm ls <pkg>` shows the installed tree.
- Constrain: edit the manifest of the package you own to a version that satisfies both, or upgrade the requester.
- Override: `"overrides": { "<pkg>": "<version>" }` in the root `package.json`; scoped form nests under the requester (`"requester": { "<pkg>": "<version>" }`) so only that edge is forced.
- Bypass: `--legacy-peer-deps` (ignores peer ranges, the npm 6 behaviour) or `--force`. Both belong on a command line, not in committed `.npmrc` or CI.

## pnpm

- See: `pnpm why <pkg>`; peer issues print under `pnpm install` as unmet peer warnings with the tree.
- Override: `pnpm.overrides` in the root `package.json` (or `overrides` in `pnpm-workspace.yaml` in newer releases). `pnpm.peerDependencyRules.allowedVersions` relaxes one peer range without overriding the package itself, which is narrower.

## Yarn

- See: `yarn why <pkg>`.
- Override: `resolutions` in the root `package.json`.

## pip

- See: `pip install` prints `ResolutionImpossible` with the conflict causes; `pipdeptree --reverse --packages <pkg>` lists dependents; `pip check` reports broken requirements in an installed environment.
- Constrain: a constraints file passed with `-c constraints.txt` limits versions without adding packages.
- Override: pip has no override; relax by installing the requester with `--no-deps` and its other requirements separately, which is the bypass class and needs the record in step 6.

## uv

- See: the resolution error lists the incompatible requirements; read all of it.
- Constrain: `constraint-dependencies` under `[tool.uv]`.
- Override: `override-dependencies` under `[tool.uv]`, which replaces the requirement the requester declared.

## Maven

- See: `mvn dependency:tree -Dverbose -Dincludes=<groupId>:<artifactId>` shows omitted-for-conflict entries. The enforcer plugin's `dependencyConvergence` rule fails when one artifact resolves through paths with different versions and prints each path.
- Constrain: `dependencyManagement` in the parent POM pins the version for every path; exclude a transitive with `<exclusions>` only when the artifact is genuinely unused.

## Gradle

- See: `gradle dependencyInsight --dependency <name> --configuration <config>` explains why a version was chosen.
- Constrain: `dependencies { constraints { implementation("g:a:ver") { because("...") } } }`; the `because` text is the record.
- Override: `resolutionStrategy.force` or `eachDependency` in the configuration, which bypass the resolver's choice.

## Go

- See: `go mod why -m <module>` and `go mod graph | grep <module>`.
- Constrain: `require` the version you need; minimal version selection takes the highest required.
- Override: a `replace` directive in `go.mod`, which affects only the main module.

## Rust

- See: `cargo tree -i <crate>` (inverted tree) and the error naming the incompatible semver requirements.
- Override: `[patch]` or a `cargo update -p <crate> --precise <version>`; a duplicate major version in the tree is often legitimate and not an error.
