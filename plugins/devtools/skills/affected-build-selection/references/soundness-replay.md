# Soundness replay

Goal: show that over real history the affected set never omitted a project that a full run would have failed.

## Procedure

1. List the sample.

   ```bash
   gh pr list --state merged --limit 50 --json number,mergeCommit,baseRefName,title > replay/prs.json
   ```

2. For each pull request, at its merge commit `M` and first parent `P`:

   ```bash
   git checkout --detach "$M"
   # affected set against the first parent
   turbo run test --filter="...[$P]" --dry=json > replay/$n.affected.json
   # or: nx show projects --affected --base="$P" --head="$M"
   # full run at M, recording failing projects
   turbo run test --continue > replay/$n.full.log
   # the same full run at the first parent
   git checkout --detach "$P"
   turbo run test --continue > replay/$n.base.log
   ```

   Run both in a clean checkout so the full run does not reuse results from the affected one; disable the cache for the replay or use a separate cache directory.
3. Extract the projects that fail at `M` but passed at `P`, and rerun each to rule out flakiness. The check is set containment: those changed results are a subset of the affected set. A project failing at both `P` and `M` is not a miss.
4. Record each pull request in a table.

| PR | Affected count | Newly failing at M (passed at P) | Missed (newly failing and not affected) |
| --- | --- | --- | --- |
| 1234 | 7 | 0 | none |

## Reading the result

- Zero misses across fifty merged pull requests, most of which passed, proves little about the failure case. Add seeded breaks: pick five shared libraries, introduce a deliberate failing change in each and confirm every dependent test is selected.
- A miss has one of three causes: a global input not declared, an edge the graph cannot see (dynamic import, a script that reads another package's files, generated code), or a base computed wrongly. Fix the cause, not the case, and rerun the whole replay.
- Keep the replay script in the repository and rerun it when the build tool is upgraded or the workspace layout changes.
