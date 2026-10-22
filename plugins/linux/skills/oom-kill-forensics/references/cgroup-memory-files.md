# cgroup v2 memory files

## Contents

- Limit files
- Event counters
- memory.stat keys
- Mapping to unit settings

## Limit files

| File | Meaning |
| --- | --- |
| memory.max | Hard limit; exceeding it triggers reclaim, then a cgroup OOM kill. `max` means unlimited |
| memory.high | Throttle threshold; the group is slowed and reclaimed hard above it but not killed |
| memory.low, memory.min | Protection from reclaim |
| memory.swap.max | Swap limit for the group |
| memory.current | Current usage, including cache |
| memory.peak | Highest usage seen (kernel 5.19 and later) |

## Event counters

`memory.events` holds `low`, `high`, `max`, `oom`, `oom_kill`, and on newer kernels `oom_group_kill`. A `max` count rising while `oom_kill` is zero means the group is hitting its limit and reclaiming successfully: it is under pressure but not yet dying. `memory.events.local` counts only the group itself.

## memory.stat keys

| Key | Meaning |
| --- | --- |
| anon | Anonymous memory (heap, stack); cannot be dropped without swap |
| file | Page cache; reclaimable unless dirty or locked |
| shmem | tmpfs and shared memory; counted in file but not droppable |
| slab_reclaimable, slab_unreclaimable | Kernel objects charged to the group |
| kernel_stack, pagetables | Per-process kernel memory |
| file_dirty, file_writeback | Cache awaiting disk; stalls reclaim |

## Mapping to unit settings

| Unit setting | File |
| --- | --- |
| MemoryMax= | memory.max |
| MemoryHigh= | memory.high |
| MemoryLow=, MemoryMin= | memory.low, memory.min |
| MemorySwapMax= | memory.swap.max |

`MemoryHigh=` set a little below `MemoryMax=` makes a service slow down under pressure instead of being killed, which gives monitoring a chance to notice.
