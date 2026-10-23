# Seed, replay and bisect commands by runner

Where each runner prints the seed of a randomised run, how to replay it, how to run a
chosen subset in a chosen order, and what isolation boundary it puts between tests. Read
the section for your runner before step 2 of the procedure, and confirm a flag against
the installed version's `--help` when the suite pins an older release.

## Contents

- [pytest](#pytest)
- [Go](#go)
- [Jest](#jest)
- [RSpec and Minitest](#rspec-and-minitest)
- [JUnit 5 and Maven Surefire](#junit-5-and-maven-surefire)
- [PHPUnit](#phpunit)
- [A runner with no bisector](#a-runner-with-no-bisector)

## pytest

pytest runs in file and definition order unless a plugin randomises it.

- **pytest-randomly** is active as soon as it is installed. The header prints
  `Using --randomly-seed=NNNN`; replay with `pytest --randomly-seed=NNNN`, or
  `--randomly-seed=last` to reuse the previous run's seed. Disable it for a hand-ordered
  run with `-p no:randomly`. It also reseeds `random` at the start of every test, which
  hides leaks of the global random state — if you suspect one, bisect with it disabled.
- **pytest-random-order** is off until asked: `--random-order`, replay with
  `--random-order-seed=NNNN`, and `--random-order-bucket=module` (or `class`, `package`,
  `global`) to choose how far tests may move.
- **Run serially.** With pytest-xdist installed, add `-p no:xdist` (or `-n 0`) to every
  bisection run. To recover a failed parallel run's order, rerun it with `-v` and keep the
  lines tagged with the failing worker, such as `[gw2]`, in the order they appear.
- **Bisector.** `detect-test-pollution --failing-test tests/test_b.py::test_victim --tests tests/`
  collects the candidates, confirms the victim passes alone and fails after them, then
  halves until it prints the polluter. It runs serially and handles lists too long for a
  command line.
- **Hand-ordered run.** Pass node IDs on the command line in the order you want them run,
  with randomisation disabled: `pytest -p no:randomly -p no:xdist tests/test_a.py::test_polluter tests/test_b.py::test_victim`.

## Go

- `go test -shuffle=on ./...` randomises test and benchmark order within each package and
  prints `-test.shuffle NNNN` before the results. Replay with `go test -shuffle=NNNN`.
- Add `-count=1` to every bisection run so a cached result is not reported as a pass.
- Each package is its own test binary and process, so in-memory polluters are always in
  the victim's package. Tests in other packages can only leak through files, ports, the
  database or other external state.
- `-run` selects tests by regular expression but does not order them: selected tests run in
  source order (files by name, then declaration order) or in shuffle order. To bisect, select
  subsets with `-run '^(TestA|TestB|TestVictim)$'` and `-shuffle=off`, keeping the polluter
  earlier in source order than the victim, or replay the seed against the subset and
  confirm the victim still runs last.
- `t.Parallel()` tests pause until the sequential tests in the package have finished, so a
  parallel test's position in the printed order is not when it ran.

## Jest

- `jest --randomize` shuffles tests within each file; `--seed=NNNN` replays; `--showSeed`
  prints the seed even without randomisation. `--randomize` is available from Jest 29.5;
  `--seed` and `--showSeed` from 29.2.
- Every test file gets its own module registry and global environment, so an in-memory
  polluter is in the victim's file. Across files, only external state leaks: a database,
  files on disk, a port, or a server started once in `globalSetup`.
- `--runInBand` (`-i`) runs files serially in one process for bisection.
- `restoreMocks: true` in the Jest config restores every `jest.spyOn` after each test, which
  removes the most common in-file polluter class at once.

## RSpec and Minitest

- **RSpec.** `rspec --order random` prints `Randomized with seed NNNN`. Replay with
  `rspec --seed NNNN`, and bisect with `rspec --seed NNNN --bisect`, which ends by printing
  the minimal reproduction command naming the polluter and victim.
- **Minitest** randomises by default and prints `Run options: --seed NNNN`. Replay by passing
  `--seed NNNN` to the test command. The `minitest-bisect` gem's `minitest_bisect` command
  takes the same seed and searches for the polluter.

## JUnit 5 and Maven Surefire

- Randomise method order with
  `junit.jupiter.testmethod.order.default=org.junit.jupiter.api.MethodOrderer$Random` and
  class order with
  `junit.jupiter.testclass.order.default=org.junit.jupiter.api.ClassOrderer$Random` in
  `junit-platform.properties`.
- Set `junit.jupiter.execution.order.random.seed` explicitly in CI — from the build number,
  for example — and print it, because the default seed is logged only at a verbose log
  level most builds do not show.
- Surefire forks decide the process boundary: with forks reused, static state in one class
  can leak into later classes in the same JVM. Bisect with a single fork so the order you
  set is the order that runs.

## PHPUnit

- `phpunit --order-by=random` prints `Random Seed: NNNN`; replay with
  `--random-order-seed=NNNN`.
- `--process-isolation` exists and is the fix to avoid, for the reason the procedure gives:
  it hides the leak rather than removing it.

## A runner with no bisector

Write the candidate list to a file, one test ID per line, in the order they ran. Generate
each half as a new file, keep the victim as the last line, and feed the file to whatever
form of "run these tests in this order" the runner supports. Record each run as a line in a
log — subset size, first and last test ID, pass or fail — so the bisection can be resumed or
checked without repeating it.
