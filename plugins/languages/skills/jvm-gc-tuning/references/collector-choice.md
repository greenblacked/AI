# Collector choice

Read this at step 5, after sizing and allocation work are done and the goal still is not met.

## G1

The default on machines with two or more processors and enough memory. It works in regions and aims for a pause target.

- `-XX:MaxGCPauseMillis=<n>`: a target the collector adapts to by changing how much it collects per pause. Setting it very low raises the number of collections and cuts throughput.
- Leave the young generation sizes alone; they are derived from the pause target.
- `-XX:InitiatingHeapOccupancyPercent` controls when concurrent marking starts; lower it only when logs show marking starting too late (to-space exhausted or full collections after marking).
- `-XX:G1HeapRegionSize` matters when humongous allocations dominate; the value is a power of two.

## ZGC

Concurrent collector aimed at pauses that do not grow with heap size.

- Needs headroom: it trades memory and CPU for short pauses. A heap sized at the live set plus a little will stall allocations.
- Enable generational mode on JDK 21 with `-XX:+UseZGC -XX:+ZGenerational`; from JDK 23 it is the default mode, and releases after that remove the non-generational one. Generational mode copes much better with high allocation rates than the original.
- Watch for allocation stalls in the log: they mean the heap is too small for the allocation rate.

## Parallel and Serial

Parallel maximises throughput with stop-the-world pauses proportional to the live set; fine for batch jobs. Serial suits tiny containers (one CPU, small heap) where the JVM chooses it automatically.

## Choosing

1. Is a pause goal stated? If pauses of a second or more are acceptable, stay on G1 or Parallel.
2. Does the heap exceed a few gigabytes with a goal under about 10 ms? Consider ZGC and budget extra memory and CPU.
3. Is the container limited to one CPU? Concurrent collectors compete with the application for it; measure.

Whichever you pick, record the version, the flags and the replayed-load results next to the decision.
