# Snapshot capture and reading

Contents: a safe capture routine, flags, reading the views, native and external memory, and when the snapshot tools do not apply.

## Safe capture routine

1. Take one instance out of the load balancer, or run a replica under replayed traffic at a steady rate.
2. Confirm free memory in the container is at least the current heap size; check `process.memoryUsage().heapTotal` and the limit.
3. Write snapshots to a volume with room for several files, each about the size of the heap.
4. Take snapshot 1, then snapshot 2 and 3 after the same fixed number of requests each, forcing a full GC beforehand.
5. Copy the files out, delete them from the instance, and handle them as secrets.

## Ways to take a snapshot

| Method | Notes |
| --- | --- |
| `--heapsnapshot-signal=SIGUSR2`, then `kill -USR2 <pid>` | Needs the flag at start; works without a debugger |
| `v8.writeHeapSnapshot([filename])` | Returns the file name; call from a protected route or a REPL |
| `--heapsnapshot-near-heap-limit=<n>` | Writes up to n snapshots as the heap nears its limit; the process is already in trouble when it runs |
| Inspector (`node --inspect`, then the Memory tab) | Convenient locally; do not expose the inspector port beyond localhost |

## Views

- **Summary**: constructors with count, shallow size and retained size. Filter to objects allocated between two snapshots.
- **Comparison**: delta in count and size between two snapshots, by constructor.
- **Containment**: the object graph from the roots.
- **Statistics**: memory split by category (code, strings, JS arrays, system objects).

Shallow size is the object itself; retained size is everything only it keeps alive. A small shallow object with a large retained size is the owner.

## Retainer chains

Read upward from the instance. Typical terminal owners: `(Module)` or a module-scope variable, `EventEmitter._events`, `Timeout` in the timers list, `(closure)` context with the captured variable named, `Promise` reaction lists for a promise that never settles.

## External and native memory

If `external` or `arrayBuffers` climbs, snapshots show the owning objects but not the buffers' contents. Look for streams not ended, compression objects not closed, `Buffer.allocUnsafe` kept in a pool, and native addons with their own cache. If RSS climbs while heap, external and array buffers are flat, the memory is outside V8's accounting: allocator fragmentation or a native module. Try running with a different allocator or limiting glibc arenas (`MALLOC_ARENA_MAX`) as an experiment, measured by the RSS trend, not by assumption.

## Reading `--trace-gc`

Each mark-compact line reports the heap size before and after, and the pause. A healthy process returns to roughly the same size after full collections. A rising floor is a leak; a rising peak with a flat floor is a larger working set. Frequent full collections that reclaim little precede the out-of-memory abort.
