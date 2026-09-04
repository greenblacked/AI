# Ecosystem playbooks

The exact commands per ecosystem for the four steps that are otherwise guesswork:
escalating deprecation warnings, diffing what a lockfile really moved, scanning for
advisories with reachability, and pinning a transitive version with an expiry.

## Contents

- npm, pnpm and yarn
- Python: pip, uv, Poetry
- Go
- Java: Maven and Gradle
- Rust: Cargo
- Overrides with an expiry date
- Runtime and language upgrade checklist

## npm, pnpm and yarn

```bash
# What is out of date, and by how many majors
npm outdated --long
npm view react versions --json | jq -r '.[-20:][]'

# Bump exactly one thing
npm install react@19 --save-exact
npm ls react                      # who else asked for it, and what they got

# Deprecation warnings escalated to failures
node --throw-deprecation --pending-deprecation ./node_modules/.bin/jest
NODE_OPTIONS='--throw-deprecation' npm test

# Advisories, with the dependency path that explains why you have the package
npm audit --json | jq '.vulnerabilities | to_entries[] | {name:.key, severity:.value.severity, via:.value.via}'
osv-scanner --lockfile=package-lock.json      # broader database, reachability for some ecosystems

# What the lockfile actually moved
git diff --stat package-lock.json
git diff package-lock.json | rg '^\+.*"version"' | wc -l
```

`npm ci` in CI, never `npm install` — `install` rewrites the lockfile, which turns the
build into a moving target and makes the "did the lockfile change" question unanswerable.

pnpm and yarn differ mainly in the override syntax below and in `pnpm why` /
`yarn why` as the equivalent of `npm ls`. pnpm's strict node-modules layout surfaces
missing peer dependencies that npm's flat layout hides, which is a reason to prefer it
during an upgrade even if you do not keep it.

## Python: pip, uv, Poetry

```bash
pip list --outdated --format=columns
pip install 'django==5.1.*'
pip-compile --upgrade-package django requirements.in    # move one pin, hold the rest

uv lock --upgrade-package django
uv pip compile --upgrade-package django requirements.in

poetry update django              # one package
poetry show --outdated
poetry show --tree django         # who depends on it

# Deprecation warnings escalated
python -W error::DeprecationWarning -m pytest
PYTHONWARNINGS=error::DeprecationWarning python -m pytest
pytest -W error::DeprecationWarning -W ignore::DeprecationWarning:third_party.*
```

The third form is the one to reach for in a real codebase: fail on your own deprecations,
ignore the ones coming out of a dependency you do not control yet. Filtering by module
keeps the signal without the noise that makes people disable the flag entirely.

```bash
pip-audit                                    # advisories against installed versions
pip-audit --requirement requirements.txt --fix --dry-run
```

## Go

```bash
go list -m -u all                      # available upgrades
go get example.com/pkg@v2.0.0          # note the /v2 import path for v2+ modules
go mod tidy && git diff go.sum

go vet ./...                           # deprecations surface via staticcheck's SA1019
staticcheck -checks SA1019 ./...

govulncheck ./...                      # reachability: reports only vulnerabilities whose
                                       # affected symbol your code can actually reach
```

`govulncheck` is the strongest reachability signal available in any mainstream ecosystem;
where it says a vulnerability is unreachable, that is a defensible reason to schedule the
upgrade rather than expedite it. Record the run in the pull request, since the claim is
only as current as the scan.

For a Go language upgrade, note that the `go` directive in `go.mod` and the toolchain
line control language semantics per module; bumping the toolchain does not by itself
change the language version your module compiles under.

## Java: Maven and Gradle

```bash
mvn versions:display-dependency-updates
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core
mvn -Dmaven.compiler.showDeprecation=true -Dmaven.compiler.failOnWarning=true test
mvn org.owasp:dependency-check-maven:check

./gradlew dependencies --configuration runtimeClasspath
./gradlew dependencyInsight --dependency jackson-databind
./gradlew --warning-mode all build
```

Maven's nearest-definition resolution means a transitive version can be decided by depth
in the tree rather than by the highest requirement, so `dependency:tree` is not optional
reading — the version you get is frequently not the version anything asked for. Use
`dependencyManagement` (Maven) or a platform / BOM (Gradle) to state the version once
rather than pinning it at each site.

OpenRewrite recipes do a substantial share of Java framework migrations mechanically;
run them as their own commit, as with any codemod.

## Rust: Cargo

```bash
cargo outdated
cargo update -p serde --precise 1.0.210     # move exactly one crate
cargo tree -i serde                          # inverse tree: who pulls it in
cargo tree -d                                # duplicate versions of the same crate
cargo audit
cargo fix --edition                          # edition migration, mechanical part
```

`cargo tree -d` is the fastest way to see that you are compiling two majors of the same
crate. That is legal and often fine, and it is also how types from "the same" crate stop
being the same type — worth checking when an error message says a type does not match
itself.

## Overrides with an expiry date

An override forces a transitive version past what its parent asked for. It is a
legitimate way to clear an advisory before upstream ships a fix, and a bad way to live.

```json
// package.json — npm and pnpm
"overrides": { "semver": "7.5.4" }
// yarn
"resolutions": { "**/semver": "7.5.4" }
```

```toml
# Cargo.toml
[patch.crates-io]
semver = { git = "https://github.com/org/semver", rev = "…" }
```

Whatever the syntax, the entry needs four things next to it, in a comment or an adjacent
file the build reads: who added it, why, the upstream issue it waits on, and the date it
must be gone. Something has to act on the date — a scheduled job that opens a ticket, or
a test that fails once the date passes:

```python
# tests/test_overrides.py — fails the build when a pin outlives its date
def test_no_expired_overrides():
    for pin in load_overrides():
        assert pin.expires > date.today(), f"{pin.name} expired {pin.expires}: {pin.reason}"
```

Without that, the pin is permanent, and its cost is paid later by whoever cannot work out
why resolution produces a version nothing requested.

## Runtime and language upgrade checklist

A runtime bump is not a dependency bump; it moves the floor under everything.

- [ ] Support window: the target version's end-of-life date, and whether it is far enough
      out to be worth the move.
- [ ] Standard library: removals, changed defaults, modules that left the standard library
      and are now a package you must add.
- [ ] Toolchain: linter, formatter, type checker, coverage, build plugins, and the test
      runner all support the target. The slowest of these sets the date.
- [ ] Base image rebuilt on the new runtime, rescanned, digest re-pinned. Cross-reference
      `image-hardening` for the ladder and the scan gate.
- [ ] System libraries underneath: libc flavour, OpenSSL major, ICU version. A TLS or
      certificate default change breaks exactly one integration, only in production.
- [ ] Native extensions and compiled wheels rebuilt for the new ABI.
- [ ] Performance re-measured: garbage collection, allocator, JIT behaviour and startup
      time all move. Capacity assumptions tied to the old runtime are now unverified.
- [ ] Locale, timezone data and date parsing, which change with the base image as often as
      with the runtime.
- [ ] CI matrix runs old and new together for at least one release, so a revert has a
      tested target rather than a hopeful one.
