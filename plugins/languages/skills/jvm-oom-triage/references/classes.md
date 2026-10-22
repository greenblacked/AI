# The OOM classes

Contents: the table, per-class checks, and what to read in a kernel kill.

## Table

| Message or evidence | Region | Usual owner | Check |
| --- | --- | --- | --- |
| `Java heap space` | Heap | Unbounded collection, large result set, request-scoped data held too long | Heap dump, MAT dominator tree |
| `GC overhead limit exceeded` | Heap | The same, seen late: the collector spends nearly all its time reclaiming almost nothing | GC log shows live set near max after each collection |
| `Metaspace` | Class metadata | Class loader leak, per-call class generation | `jcmd <pid> VM.metaspace`, loaded class count over time |
| `Compressed class space` | Class metadata | The same, a separate limit (`-XX:CompressedClassSpaceSize`) | As above |
| `Direct buffer memory` | Off-heap | Pooled or leaked `ByteBuffer.allocateDirect` in a network or compression library | NMT, buffer pool MXBeans |
| `unable to create native thread` | Threads | Unbounded pool, thread per request, low `ulimit -u` or cgroup pids limit | Thread count against limits |
| `Requested array size exceeds VM limit` | One allocation | A size computed wrongly or read from untrusted input | The stack trace, not a dump |
| None, exit 137 | Process past its cgroup limit | Heap plus non-heap together over the limit, or native growth | Platform kill reason, NMT |

## Metaspace

Count loaded classes over time with `jcmd <pid> VM.classloader_stats` and `jcmd <pid> VM.metaspace`. A count that rises with every redeploy or request means classes are generated and their loader stays reachable. In a heap dump, find class loader instances with many instances of `java.lang.Class` retained, and take the path to GC roots of the loader. Raising `-XX:MaxMetaspaceSize` only changes when it fails; leaving it unset lets the region grow to the container limit, which turns this error into a kill.

## Direct buffers

The JVM exposes buffer pool usage through the platform MXBeans (`java.nio:type=BufferPool,name=direct`); log its `MemoryUsed` and `Count` over time. Memory is released only when the owning `ByteBuffer` object is collected or explicitly freed, so a quiet heap can delay the release of a large amount of native memory. The default cap is the maximum heap size; set `-XX:MaxDirectMemorySize` only after you know the owner.

## Native threads

```bash
jcmd <pid> Thread.print | grep -c '^"'
grep Threads /proc/<pid>/status
ulimit -u
cat /sys/fs/cgroup/pids.max 2>/dev/null
```

Each thread reserves a stack (`-Xss`) and native bookkeeping. Group the thread names from the dump by prefix; the pool with thousands of members is the owner. The cgroup path above is for cgroup v2; on v1 look under the pids controller.

## Reading a kernel kill

On the node, `dmesg` reports the killed process and the cgroup's memory usage and limit at that moment. On Kubernetes, the container's last state shows reason `OOMKilled` and exit code 137; the pod's events and node pressure are the `k8s-triage` skill's. A kill at a steady heap size with RSS climbing is native growth; a kill during a heap rise is both together.

## Heap dump etiquette

`jcmd <pid> GC.heap_dump /dumps/app.hprof` writes only live objects after a full collection and pauses the process while writing. Size the free space first. Compress before moving, delete after analysis, and never attach a dump to a ticket.
