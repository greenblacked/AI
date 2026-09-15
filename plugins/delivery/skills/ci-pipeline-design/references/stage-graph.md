# Stage graphs by repository shape

## Contents

- [How to read these](#how-to-read-these)
- [Library](#library)
- [Service deployed as a container](#service-deployed-as-a-container)
- [Container image or base image repository](#container-image-or-base-image-repository)
- [Monorepo](#monorepo)
- [Decomposing into reusable workflows](#decomposing-into-reusable-workflows)
- [Entry points: pull request, default branch, tag, schedule](#entry-points-pull-request-default-branch-tag-schedule)

## How to read these

Each graph shows jobs as nodes and dependencies as edges. An edge exists only where the
downstream job consumes an output of the upstream one, or where running the downstream
job has a cost worth avoiding when the upstream failed. Everything without an edge runs
in parallel. The **critical path** is the longest chain, and it is the number a developer
experiences; adding parallel breadth never goes below it.

The `[required]` marker is the blocking set from step 1 of the skill. Notice in every
shape that it is a subset, and that the long jobs are mostly outside it.

## Library

A package consumed by other code: no deployment, a publish step on tags, and a
compatibility surface that is the whole point of the matrix.

```text
setup ─┬─ lint [required]
       ├─ type check [required]
       ├─ unit tests (matrix: versions x os) ──┬─ matrix aggregate [required]
       ├─ build distributables [required] ─────┴─ publish (tag only)
       └─ docs build (advisory)
```

Points specific to this shape:

- The matrix is the product's claim about what it supports, so its breadth is a product
  decision rather than a cost decision. If the breadth is unaffordable per pull request,
  run the narrow set on pull requests and the full set on a schedule, and say in the
  support policy that the wide axes are verified daily rather than per change.
- `publish` depends on `build` and runs only on a tag. It is the only job with a
  credential.
- Installing the built distributable in a clean environment and importing it catches the
  packaging defect — a missing file in the manifest — that no test running from the
  source tree can see. It is cheap and it belongs on the critical path before publish.

## Service deployed as a container

```text
setup ─┬─ lint [required]
       ├─ unit tests [required]
       ├─ build image [required] ─┬─ image scan [required]
       │                          ├─ integration tests (compose) [required]
       │                          └─ deploy staging ─ smoke ─ deploy production
       └─ migration check (advisory)
```

- The image is built once here and every downstream job refers to it by digest. That is
  the build-once rule expressed as graph structure: there is exactly one node that
  produces the artefact.
- Integration tests depend on the image rather than the source, because testing the
  source and shipping the image tests the wrong thing.
- Deployment jobs hang off the same node and are the only ones with credentials.
- Schema work belongs to `db-migration`, not here; what the pipeline owns is the check
  that the migration applies cleanly against a copy of the schema.

## Container image or base image repository

```text
setup ─ build (matrix: platforms) ─ aggregate ─┬─ scan [required]
                                               ├─ structure tests [required]
                                               └─ push by digest ─ tag manifest
```

- Multi-platform builds fan out per platform and fan in to a manifest list. Push the
  per-platform images by digest and tag the manifest, so a tag never points at a
  partially pushed set.
- The scan blocks the push rather than the merge if the base image is outside your
  control and new findings appear without a code change. Otherwise the pipeline goes red
  for reasons nobody in the repository can fix, which is the fastest way to teach people
  to ignore it.

## Monorepo

The defining problem is that running everything on every change does not scale and
running only what changed is hard to get right.

```text
setup ─ detect changed projects ─┬─ per-project lint/test (dynamic matrix) ─ aggregate [required]
                                 ├─ affected integration tests [required]
                                 └─ per-project build ─ per-project publish
```

- The change-detection step is now load-bearing: a false negative means a broken project
  merges green. Derive the affected set from the build tool's own dependency graph where
  one exists rather than from path globs, because globs miss the dependency edges that
  matter — a shared library changing affects consumers whose paths did not change.
- Run the full set on the default branch, on a schedule, or both. That is what bounds
  the damage from a change-detection miss.
- The aggregate job is what branch protection requires, because the dynamic matrix's
  cell names change per run and cannot be named in a rule.

## Decomposing into reusable workflows

Once there is more than one entry point, the same jobs need to be callable from each.
Two mechanisms, and they are not interchangeable:

| Mechanism | What it is | When it fits |
| --- | --- | --- |
| Reusable workflow | A whole workflow called with inputs, running as its own jobs | A stage with several jobs, or one needing its own permissions and secrets |
| Composite action | A bundle of steps inlined into a calling job | A repeated sequence of steps inside one job, such as language setup |

Rules that keep the indirection readable:

- One level of nesting. A reusable workflow calling a reusable workflow puts the thing
  that actually ran two hops from the thing that failed.
- Pass what varies as explicit inputs rather than reading repository variables inside the
  called workflow. A called workflow that reads ambient state behaves differently
  depending on who called it, which is not visible at the call site.
- Pin what you call to a commit, including your own organisation's workflows. A moving
  reference means the pipeline changes without a commit in this repository.
- Keep the required-check name in the calling repository, not inside the callee, so the
  branch protection rule survives refactoring of the callee.

## Entry points: pull request, default branch, tag, schedule

| Entry point | Runs | Why |
| --- | --- | --- |
| Pull request | The blocking set, plus fast advisory checks | This is the number people wait for |
| Default branch after merge | The blocking set plus long end-to-end suites, and the deploy path | The place where expensive confirmation is affordable |
| Tag or release | Build, publish, promote | The only entry point with publishing credentials |
| Schedule | Full matrix breadth, dependency freshness, slow scans | Catches drift that no commit triggers |

The failure this table prevents is one workflow doing all four with conditionals on every
job. Those files become unreadable at about the third condition, and the usual symptom is
a job that quietly stops running on the branch that needed it, which nobody notices
because a job that does not run reports nothing at all.
