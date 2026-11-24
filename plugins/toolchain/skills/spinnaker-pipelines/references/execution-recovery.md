# Stuck executions and stale views

Read this when an execution shows RUNNING with no progress, a stage will not finish, or
the UI shows clusters that disagree with the cluster itself. The services involved are
Orca (runs executions), Clouddriver (reads and writes the cloud and caches it), Echo
(triggers), Gate (API) and Fiat (permissions). Config keys, queue behaviour and storage
options differ by release and backend; confirm them in the official docs for the pinned
version before acting on anything below.

## Classify the stall first

| Symptom | Likely cause | First check |
| --- | --- | --- |
| Stage RUNNING, task list shows a task repeating | Waiting on a real condition: manifest not stable, wait stage, canary running | The stage's task details and message; what is true on the cluster |
| Stage RUNNING at a Manual Judgment | Waiting for a person; no timeout set | The stage config for a timeout; who is allowed to judge |
| Execution RUNNING, no stage has updated for a long time, no task repeating | Orca lost the message that advances it | Orca logs for that execution id; queue and storage backend health |
| Stage done on the cluster, UI shows old state | Clouddriver cache has not refreshed | The cluster via `kubectl` or the cloud console, then the cache age |
| Pipeline did not start at all | Trigger not delivered or filtered out | Echo log and the source's delivery log; trigger regex; run-as permissions |
| Stage failed with a permission error only on trigger | Run-as user or service account lacks access | The pipeline's run-as setting and the account's permissions |

Look at the stage's own message before anything else; a task that retries on "manifest not
stable" is telling you which object to look at.

## Verify against the cluster, not the UI

Clouddriver caches what it reads from the provider and serves the UI and some stages from
that cache. Kubernetes caching agents poll on an interval and refresh on demand after a
Spinnaker write; a change made outside Spinnaker, or a cluster with many namespaces and
kinds, can leave the cache behind for longer than expected. Use the provider's own CLI to
establish what is deployed. If the cluster is right and the UI is wrong, the cause is the
cache, and a stage that waits on the cache (stability checks, find-artifact) can wait on
stale data. Narrowing the kinds and namespaces an account caches, where the account
config allows it, shortens the cycle; check the provider docs for the options. Stages
that force a cache refresh exist in some provider types; check the pinned release.

## What cancel does

Cancelling an execution stops Orca from advancing it. It does not undo what the cloud
already did, and it does not delete a manifest that a stage applied. After a cancel,
inspect the cluster and decide whether to roll forward (re-run with the same artifact)
or roll back (Undo Rollout or the previous artifact). Re-running a pipeline with
concurrency disabled while the stuck one is still RUNNING queues or drops the new run;
cancel the stuck one first.

If a cancel has no effect, the execution is probably not being processed. Read Orca's logs
for that execution id and the health of its queue backend (Redis or SQL, depending on the
installation) before restarting anything. A restart makes Orca re-read queued messages,
which can resume the stalled execution, fail it, or resume it twice when a message was
delivered but not acknowledged; the outcome depends on the queue implementation and its
zombie or orphan handling, so read that part of the docs first and do the restart with a
person watching, not as a first move.

## Do not

- Edit execution rows in Redis or SQL by hand. Executions are written by several tasks
  and a hand edit can leave stages that reference each other inconsistently.
- Delete and recreate a pipeline to clear a stuck run. That discards the execution
  history and the trigger bindings and does not clear the cause.
- Raise stage timeouts to make a stuck stage pass. A stage that needs longer needs the
  reason found; a longer timeout hides a probe that never turns ready.
- Re-run a deploy before reading what the first one applied. Two partial applies are
  harder to reason about than one.

## After recovery

Record the execution id, which of the three causes it was, what was cancelled, and what
the cluster held afterwards. If the cause was a missing timeout, a loose artifact match
or an unready probe, fix that in the pipeline, not only the instance.
