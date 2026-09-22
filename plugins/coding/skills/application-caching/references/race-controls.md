# Race controls

Use this reference after drawing the miss and mutation interleaving. Choose the mechanism supported by the source and cache rather than translating the names mechanically between products.

## Versioned keys

Every authoritative mutation must advance a shared monotonic version or generation reliably tied to its source commit. Readers discover that current generation, then address the cached value by both resource identity and generation. A late loader can populate only its old namespace; readers that have advanced will not consume it. Store the generation independently of the evictable value, define how readers learn it, and reclaim old value generations without reclaiming the ordering state.

## Compare-and-set

Publish only if the persistent shared generation still equals the source generation loaded. The comparison and write must be one atomic provider operation or transaction. Reading a generation and later issuing an unconditional write is not CAS. Define restore, reset, and failover behavior so the generation cannot move backward.

## Leases and fencing

A lease reduces simultaneous work. Its expiry does not stop the old holder. Monotonic fencing tokens can reject an expired holder, but they order lease owners rather than source mutations: a newer holder may still have loaded an old snapshot. When a late old result is unsafe, require both a valid ownership token and a loaded source generation equal to the current persistent generation. Specify what component atomically enforces both comparisons.

Provider primitives differ. Confirm atomicity, expiry, ownership, and retry behavior in the documentation for the deployed version. Redis documents conditional `SET` options and its cautions for lock patterns in [SET](https://redis.io/docs/latest/commands/set/) and [distributed locks](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/). These are concrete primitives, not a universal instruction to use a distributed lock.

## Review questions

- What monotonic value distinguishes old from new?
- Which source mutations advance it, and how is that tied to commit?
- Where is it stored so value eviction or deletion cannot remove it?
- Which operation atomically checks it before publication?
- What can a paused or retried loader do after ownership expires?
- Can an old entry be addressed after readers advance?
- How are wraparound, reset, restore, and region failover handled?
