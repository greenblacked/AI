# GitLab merge request contract

Verify the following against the documentation for the organisation's GitLab version
before implementation; API availability and limits differ across releases and hosting
tiers.

## Event acceptance

Verify the webhook secret token before accepting event content. Enforce an event-age
window and deduplicate deliveries with trusted event and object identifiers. Resolve the
project and merge request again through authenticated API state. An event is a trigger,
not the authoritative snapshot.

Reject events outside the configured GitLab instance, project or target-branch policy.
Coalesce bursts for the same merge request, but retain the version identity that each run
actually reviewed.

## Immutable review identity

Fetch [merge request versions](https://docs.gitlab.com/api/merge_requests/) and select
the current version according to the documented ordering or explicit current-version
indication. Record the version identifier and its
`base_commit_sha`, `start_commit_sha` and `head_commit_sha` diff refs. Treat that tuple as
the run identity; do not rely only on branch names, merge request IID or a mutable “latest”
URL.

Prefer the documented version-specific diff response for the recorded version. If an
implementation instead uses the current merge request `/diffs` endpoint, bracket the
entire paginated fetch with version reads and accept it only when both reads identify the
same version identifier and base, start and head SHA tuple; `/diffs` is mutable latest
state, not a version selector. The merge
request `/changes` endpoint is deprecated. Follow [GitLab REST
pagination](https://docs.gitlab.com/api/rest/#pagination) through the server-provided
`Link` relation until no next page remains; do not infer completion from a short page or
depend on total-count headers, which may be absent. The default page size is 20 and the
documented maximum is 100. Record expected and observed file counts where available;
`changes_count` is a string and may be reported as `1000+`, so it is not proof of
completeness.

For the version-specific response, require the expected SHA tuple and examine its state,
`overflow`, `without_files` and per-file coverage indicators. A version identifier does
not make an incomplete payload complete.

For every file, preserve old path, new path, rename/deletion flags and the platform's
coverage indicators. GitLab can mark a file diff `collapsed` (excluded initially but
potentially retrievable) or `too_large` (unretrievable through that endpoint), and
instance limits can omit content. Do not reconstruct missing hunks from an unchecked mutable
branch. Either retrieve content by the pinned commit through an approved API and state
that it lacks diff context, or mark the file unreviewed.

## Inline positions

Build line positions only from validated diff data and the pinned diff refs. The
[Discussions API](https://docs.gitlab.com/api/discussions/#create-a-new-thread-in-the-merge-request-diff)
requires the version's base, start and head SHAs for a diff position. Distinguish
old-side and new-side lines, renamed paths, deletions and unchanged context according to
the selected Discussions API version. Confirm that each proposed anchor is represented
by the supplied hunk before publication.

When an anchor is unsupported or no longer valid, prefer a merge-request-level finding
that names the path and evidence over guessing a nearby line. Refetch the current MR
version immediately before publishing; any identity change makes the run stale.

## Forks and pipeline state

Do not solve fork review by exposing protected variables or a project write token to a
pipeline that checks out or executes the fork revision. Whether a particular GitLab
pipeline source can access protected variables depends on project settings, ref
protection, runner trust and GitLab version. Verify those controls separately, but keep
this reviewer independent of contributor-controlled pipeline execution.

The integration must remain advisory. It does not approve the merge request, set merge
status, merge, push a fix, or impersonate a human reviewer. A human and the repository's
normal required checks retain authority.

## Implementation evidence

Before coding, capture links and version dates for the exact GitLab documentation used:

- merge request versions and version-specific diffs;
- Discussions API diff positions;
- REST pagination and relevant diff limits;
- webhook authentication and event schema;
- fork merge request pipelines, protected resources and token permissions.

A [CI job token](https://docs.gitlab.com/ci/jobs/ci_job_token/#job-token-access) has a
limited API surface: it can read selected merge request and note resources but cannot
create discussions or notes. Do not assume it can be the publisher credential. Select a
separate narrowly scoped integration identity only after the authentication mechanism is
chosen, and keep it in the publisher rather than the model runtime.

Write contract tests from recorded, redacted fixtures for multiple pages, collapsed and
oversized diffs, renamed and deleted files, stale versions, and fork-origin events.
