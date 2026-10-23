# Reading a thread dump

Read this when a dump is large, locks are not plain `synchronized`, or the pattern is not in the table.

## Contents

- Anatomy of one entry
- Walking a lock to its owner
- ReentrantLock and other ownable synchronizers
- Grouping a large dump
- Common misreads

## Anatomy of one entry

```text
"http-nio-8080-exec-17" #42 daemon prio=5 os_prio=0 tid=0x... nid=0x1a2b waiting for monitor entry
   java.lang.Thread.State: BLOCKED (on object monitor)
    at com.example.Cache.get(Cache.java:58)
    - waiting to lock <0x00000007c0a1b2c8> (a com.example.Cache)
    at com.example.Service.lookup(Service.java:31)
```

The name usually identifies the pool. `nid` is the operating system thread id in hexadecimal, which joins the dump to `top -H`. The state line and the `- waiting to lock` or `- locked` lines carry the lock address.

## Walking a lock to its owner

1. Take the address from a `waiting to lock <0x...>` line.
2. Search the dump for `locked <0x...>` with the same address. The thread that has it is the owner.
3. Read the owner's stack. It is either doing slow work inside the lock (I/O, a remote call), itself waiting on something else, or waiting on a lock held by a thread in the first group, which is a cycle.
4. Repeat until the chain ends at a thread that is running or waiting on I/O. That thread is the root.

## ReentrantLock and other ownable synchronizers

Threads parked on a `ReentrantLock` appear as `WAITING (parking)` with `- parking to wait for <0x...> (a java.util.concurrent.locks.ReentrantLock$NonfairSync)`. The owner is listed under `Locked ownable synchronizers` in its own entry, which `-l` prints; match the address there. Without `-l` the owner is not shown.

## Grouping a large dump

Strip addresses and thread numbers from the stack lines, then count identical stacks. A shell pipeline over the saved file is enough: extract the first five frames of each entry, sort and count. Work from the largest group down, and ignore idle pool workers parked in `LinkedBlockingQueue.take` or `ThreadPoolExecutor.getTask`; those are healthy and waiting for work.

## Common misreads

| Appearance | Reality |
| --- | --- |
| `RUNNABLE` in `socketRead0` | Blocked on the network, not computing |
| Many `TIMED_WAITING` in `sleep` | Often a retry loop or a scheduler, check the caller |
| Threads `WAITING` in `Unsafe.park` | Could be idle workers or a real wait; read the frames above |
| A deadlock section missing | No Java-level cycle; the stall may be I/O or a lock held across I/O |
