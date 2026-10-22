# The pull request check and the doc-touch rate

Read this when wiring the drift map into CI. The examples use GitHub Actions; the logic is
the same on any CI that can see the merge result of a pull request.

## Contents

- [What the job computes](#what-the-job-computes)
- [Job outline](#job-outline)
- [Permissions and fork pull requests](#permissions-and-fork-pull-requests)
- [The override](#the-override)
- [Doc-touch rate](#doc-touch-rate)

## What the job computes

On a `pull_request` event the checkout is the merge commit, so its first parent is the base
branch tip and `HEAD^1..HEAD` is exactly what the pull request changes.

1. **Changed files**: `git diff --name-only HEAD^1 HEAD`.
2. **Identifiers before and after**: run the same extractors that build the map against
   the base tree and the head tree. Removed identifiers are the set difference, base
   minus head. A rename shows up as one removed and one added. Before using a removed
   identifier's forms, drop any form that is also a form of an identifier still present at
   head: with `storage.retention_days` removed and `cache.retention_days` kept, the leaf
   `retention_days` is still true on the cache pages and must not produce a hit.
3. **Advisory pages**: pages mapped to an identifier whose form appears in a changed line
   of source (`git diff -U0 HEAD^1 HEAD` restricted to source paths), plus pages mapped to a
   path glob matching a changed file, minus pages the pull request already changes.
4. **Blocking hits**: for each removed identifier, every line on a non-historical page under
   the docs root that still contains one of its forms, as `file:line`.
5. **Output**: a Markdown block listing advisory pages with the identifier that matched,
   and blocking hits, written to the step summary and, where the token allows, to one
   pull request comment. Exit 3 when there are blocking hits and let any internal
   failure exit with its own code (not 3); the job, not the script, decides whether an override applies.

Keep the extraction and the set arithmetic in a script in the repository, with tests over
a small fixture tree: a removed flag still documented, the same flag only in the
changelog, a renamed config key, and a change touching nothing mapped.

## Job outline

```yaml
name: docs-drift
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
permissions:
  contents: read
  pull-requests: write
jobs:
  drift:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 2
          persist-credentials: false
      - name: Compute affected pages
        env:
          OVERRIDE: ${{ contains(github.event.pull_request.labels.*.name, 'docs-drift-override') }}
        run: |
          set -Eeuo pipefail
          status=0
          ./scripts/docs_drift.sh HEAD^1 HEAD > drift.md || status=$?
          cat drift.md >> "$GITHUB_STEP_SUMMARY"
          [ "$status" -eq 0 ] && exit 0
          # Exit 3 means blocking hits, the only status a label may waive. Any other
          # non-zero status, including the 1 an unhandled error gives, is the script
          # failing, and an override must not hide that.
          if [ "$status" -eq 3 ] && [ "$OVERRIDE" = "true" ]; then exit 0; fi
          exit "$status"
```

`fetch-depth: 2` is enough for the merge commit and its first parent. The script path is
illustrative: it is the script described above, in your repository.

The `labeled` and `unlabeled` types matter: without them, adding the override label does
not re-run the check, and the pull request stays red until the next push.

Post the comment in a separate step after the summary, from the same `drift.md`. To keep one
comment per pull request, put a hidden marker line in the body, find the earlier comment
carrying it, and edit that comment through the REST API
(`PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}`) rather than posting a new one
on every push. Post nothing when there are no advisory pages and no blocking hits.

## Permissions and fork pull requests

The comment needs `pull-requests: write`; nothing else in the job needs more than
`contents: read`. On a pull request from a fork, the token is read-only and the comment
step fails, so skip it there with
`if: github.event.pull_request.head.repo.full_name == github.repository` and rely on the
step summary and the check result.

Do not switch to `pull_request_target` to get a write token for forks. That event runs with
the base repository's credentials, and this job runs the pull request's own extractor
scripts; checking out the fork's head under it hands those credentials to code from
outside the project.

## The override

The override is for one situation: an identifier removed from the source of truth but
still accepted, with a deprecation warning, and documented that way on purpose. Restrict
who can apply the label to the map's owners where the platform allows it, and require the
pull request description to say why. Review the overridden pull requests each time the
rate is measured; most should have been a historical-page entry or a doc fix.

## Doc-touch rate

Count changes from the default branch's history, so the code and docs halves do not
depend on a hosting API. With `--first-parent`, current git shows each merge commit's
changes against the base, and a squash merge is already one commit per pull request:

```bash
git log origin/main --first-parent --since='90 days ago' --format='@@%H' --name-only
```

Split the output on the `@@` lines and, for each commit, classify its file list with the
same script the job uses: did it touch mapped code, and did it touch a mapped page? Check
on the first run that merge commits list their files; if they come out empty, the git in
use needs `--diff-merges=first-parent` added.

Overrides live on the pull request, not in git. Count them with a search over merged pull
requests in the same window, for example
`is:pr is:merged label:docs-drift-override merged:>=2026-01-01`, adjusted to the window's
start date.

Report, for commits that touched mapped code: the share that also touched a mapped page,
the share overridden, and the share that did neither. Keep the window length fixed between
measurements so the trend means something.
