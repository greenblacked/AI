# Cache keys, hit rates and trust boundaries

## Contents

- [The claim a cache key makes](#the-claim-a-cache-key-makes)
- [Keys per ecosystem](#keys-per-ecosystem)
- [Restore keys](#restore-keys)
- [Measuring whether the cache is worth its cost](#measuring-whether-the-cache-is-worth-its-cost)
- [Trust boundaries](#trust-boundaries)
- [What not to cache](#what-not-to-cache)

## The claim a cache key makes

A key says: any two runs producing this key may share these bytes. Everything that
changes the contents belongs in the key, and nothing else does. Both failure directions
are common and they look nothing alike.

| Failure | Symptom | Cause |
| --- | --- | --- |
| Key too specific | Hit rate near zero, runs slightly slower than with no cache at all | Commit SHA, run number, branch name or a timestamp in the key |
| Key too loose | Failures that do not reproduce locally, a toolchain nobody installed, a dependency version nobody requested | An input that changes the contents is missing from the key |

The second is worse and harder to see, because the restored bytes are plausible. Any
time a build fails in a way that makes no sense, clearing the cache is a valid first
experiment and a fast one.

## Keys per ecosystem

The general form is `{os}-{language version}-{tool}-{hash of lockfile}`, with anything
else the install step reads appended.

| Ecosystem | Cache path | Hash these | Also in the key |
| --- | --- | --- | --- |
| npm, pnpm, yarn | The package manager's store, not `node_modules` | `package-lock.json`, `pnpm-lock.yaml` or `yarn.lock` | OS, architecture, Node major version |
| pip | `~/.cache/pip`, or the wheel cache | `requirements*.txt` or `uv.lock` or `poetry.lock` | OS, architecture, exact Python version |
| Go | `~/.cache/go-build` and `~/go/pkg/mod` separately | `go.sum` | OS, architecture, Go version |
| Maven, Gradle | `~/.m2/repository`, `~/.gradle/caches` | `pom.xml`, `*.gradle*`, `gradle-wrapper.properties` | OS, JDK major version |
| Cargo | `~/.cargo/registry`, `~/.cargo/git`, `target/` | `Cargo.lock` | OS, target triple, toolchain version |
| Docker | The builder's own cache backend, not a tarball you manage | Not applicable, the builder is content-addressed | Builder version |

Two frequent mistakes in that table:

- **Architecture belongs in the key wherever native code compiles.** A cache restored
  onto a different runner architecture produces binaries that do not run, and the error
  message names a dynamic loader rather than your key.
- **The exact language version, not the major.** A cache built under one patch release
  of an interpreter can contain compiled artefacts the next one rejects. Where the
  setup step reports the resolved version, use it rather than the value you requested.

Most ecosystems now have first-party caching built into the setup step, which gets these
inputs right without you restating them. Prefer it, and hand-roll only what it does not
cover.

## Restore keys

A restore key is a prefix tried when the exact key misses, letting a run start from a
near-match instead of nothing. The prefix ladder drops one component at a time, most
specific first.

Where it is right: download and package caches, where a near-match saves most of the
work and the install step still reconciles against the lockfile. The worst case is a
slightly stale set of packages that the install step corrects.

Where it is wrong: anything the build treats as an output — a compiled tree, a generated
directory, a test fixture database. A near-match there is not corrected by anything, and
the build proceeds on bytes produced by a different input set. Use an exact key with no
prefixes and accept the miss.

## Measuring whether the cache is worth its cost

Saving a cache costs time too, and a cache that misses pays that cost on every run for no
return. Get the numbers rather than assuming:

```bash
set -Eeuo pipefail

# Cache hit or miss per run, read out of the setup job's log.
gh run list --workflow ci.yml --branch main --limit 50 --json databaseId \
  --jq '.[].databaseId' \
  | while read -r run_id; do
      # --job takes a numeric job id, not a name, so resolve it first. Grepping the
      # whole run log would also work and is simpler when only one job caches.
      job_id=$(gh run view "$run_id" --json jobs \
        --jq '.jobs[] | select(.name=="setup") | .databaseId')
      if [ -n "$job_id" ] \
         && gh run view "$run_id" --log --job "$job_id" | grep -qi 'cache restored from key'; then
        echo hit
      else
        echo miss
      fi
    done \
  | sort | uniq -c
```

Compare the saved time against the install time it replaces. A cache restoring a large
tree over a slow link can be slower than installing from a nearby registry mirror, and a
dependency step of a few seconds does not need a cache at all.

Then check the eviction window. Providers evict by age and by total size per repository,
so a rarely built branch can miss every time while the repository is nominally at its
cache limit. When total size is the constraint, cache fewer things rather than more:
several small unused caches evict the one that was working.

## Trust boundaries

A cache is shared mutable state written by one run and read by another, so it is worth
one deliberate paragraph in any pipeline design.

- **A fork's pull request run is untrusted code.** If it can write to a cache scope that
  a trusted run later restores, it can place bytes into a trusted build. Providers scope
  caches per branch with a fallback to the default branch, which usually means untrusted
  runs restore from trusted scopes but cannot write into them. Confirm that is your
  provider's behaviour rather than assuming it.
- **Do not cache anything a credential produced.** A registry login writes an
  authentication token into a config file inside the home directory; caching that
  directory publishes it to every later run.
- **Do not cache across repositories** unless the cache is content-addressed and its
  contents verified on restore, because the trust boundary then follows whoever can
  write to the least protected of the repositories.
- Where a cache is suspected of being poisoned rather than merely stale, rotate the key
  prefix. Deleting entries races with runs that are still writing them.

## What not to cache

- Build outputs that the pipeline is supposed to produce from scratch. If the artefact
  is restored rather than built, the build step is proving nothing.
- Test databases with schema in them, unless the schema hash is in the key. The stale
  case is a test suite passing against a schema that no longer exists.
- Anything with secrets in it.
- Anything larger than the time it saves, which you can only know from the measurement
  above.
