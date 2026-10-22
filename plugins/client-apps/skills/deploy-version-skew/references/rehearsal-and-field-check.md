# Rehearsal and field check

Contents: the staging rehearsal with two builds, the field numbers to read after a real
release, and how to derive the retention period.

## Staging rehearsal

Build A and build B must differ in at least one lazily loaded route, so the chunk hashes
change. Open every tab on A before deploying B.

| Case | Setup | Expected |
| --- | --- | --- |
| Retained | Deploy B without pruning A's assets; in an A tab, open a route not yet visited | The route loads A's chunk, no reload, no error |
| Pruned, clean form | Deploy B, delete A's assets; open an unvisited route | One reload, the tab is on B, the route works |
| Pruned twice | As above, but B's chunk for that route is also deleted | One reload, then the error screen; no second reload |
| Pruned, dirty form | Type into a form, then open an unvisited route | No reload; the "new version" screen offers to reload after saving |
| Stale flag | Deploy B; in an A tab, wait for the build id mismatch, then click a link | A full page load to B at the click, not before |
| Long-lived page | Leave an A dashboard open across the deploy | Banner appears; nothing reloads on its own |
| Mixed API | New client against old server, old client against new server | Both work; unknown fields ignored, missing optional fields tolerated |
| Storage blocked | Repeat "pruned, clean form" with storage disabled | No reload; error screen with a reload button |

A rehearsal that only tests the happy path proves nothing: the loop guard and the
dirty-form check are the parts that fail in production.

## Field check after the next release

Read these per deploy, aligned on deploy time, for the day after each release:

- Chunk-load errors per thousand sessions, split by client build, before and after the
  change. The target is close to zero for builds inside the retention window.
- How often the loop guard tripped. A non-zero count means chunks are missing for
  current builds, or a tab outlived retention.
- Reloads triggered by the stale flag, against sessions that ended on a stale build.
- The distribution of `X-Client-Build` (or your header) in API request logs, by age of
  the build.

## Deriving retention

From the request logs, find the age of the oldest build that still accounts for a
meaningful share of traffic over a week, choose the share you are willing to send to the
error screen, and keep assets for that age plus a margin. Re-derive it when usage
changes: a product people leave open all week (a dashboard, an admin console) needs far
longer retention than one opened per task.
