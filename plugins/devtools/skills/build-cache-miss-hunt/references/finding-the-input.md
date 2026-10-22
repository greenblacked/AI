# Finding the input that differs

## Contents

- The comparison procedure
- Turborepo
- Gradle
- Bazel
- Reading the difference
- Common fixes by symptom

## The comparison procedure

1. Pick one commit and one task. Choose the cheapest task that misses.
2. Produce the input description on machine A and on machine B, from a clean checkout, with the same command.
3. Normalise nothing before the first diff. A path that differs is the finding.
4. Change one thing, rerun on both, and repeat until the descriptions match.

## Turborepo

```bash
turbo run build --filter=<package> --dry=json > a.json     # on each machine
jq '.tasks[] | select(.taskId=="<package>#build")' a.json > a.task.json
diff a.task.json b.task.json
```

Fields worth reading in the task object: `hash`, `inputs` (file hashes the task reads), `environmentVariables` (what was hashed from the environment), `hashOfExternalDependencies` and `dependencies`. A difference in `hashOfExternalDependencies` means the lockfile or resolved dependency set differs between machines, often a different install of the same lockfile. A difference in a dependency task's hash cascades into the task you are reading; follow the chain to the first task whose own inputs differ.

`turbo run build --summarize` records the same material for a real run in `.turbo/runs/`. Check that `.turbo/` itself is in the ignore list for inputs.

## Gradle

```bash
./gradlew build --build-cache -Dorg.gradle.caching.debug=true
./gradlew build --build-cache --scan
```

The debug flag logs, for each cacheable task, the hash of every input property and the combined cache key. Diff the logs from the two machines and look for the property whose hash differs. A build scan shows the same under the task's inputs and states why it was or was not served from cache. Typical culprits: a task input annotated as an absolute path where a relative or classpath-normalised input was meant, a non-reproducible archive (file order or timestamps; archive tasks can be told to use reproducible file order and fixed timestamps), and a build script reading `System.getenv`.

Remote cache write policy lives in the settings `buildCache` block: `remote(HttpBuildCache)` with `push` set from a condition such as running on a trusted branch.

## Bazel

```bash
bazel build //pkg:target --execution_log_json_file=/tmp/exec.json
```

Compare the spawn entry for one target between machines: the `commandArgs`, `environmentVariables` and each input's digest. An argument containing the output base or workspace path, or a differing environment variable, is the cause. `--incompatible_strict_action_env` fixes the shell environment seen by actions. Workspace status stamping (`--stamp`) writes volatile keys such as build time; only stamp the release target, not every target. Different toolchains between machines show up as different tool input digests.

## Reading the difference

| What differs | Likely cause |
| --- | --- |
| A path prefix in an argument or input | Checkout directory or home directory leaking in |
| One environment variable name | The task or a script reads it; declare it or stop reading it |
| A file digest with identical contents shown elsewhere | Line endings or file mode differing between platforms |
| A generated file's digest | Timestamp, SHA or ordering inside it |
| A tool or toolchain digest | Version drift between laptop and CI |
| Only dependency task hashes | The root is upstream; follow the chain |

## Common fixes by symptom

- Hits on one developer's machine only: the cache key includes something per-user (home path, username). Check the environment list first.
- Misses on every CI run, hits locally: CI sets variables the build hashes, or checks out to a different directory each run.
- Misses only for packages that generate code: the generator stamps time or SHA, or writes entries in map order.
- Hit rate decays over days: a growing log or output directory is inside a glob.
