# Race patterns

Read this when the report does not point to an obvious cause. Each entry shows the wrong shape and the correction.

## Contents

- Shared map
- Loop variable capture
- WaitGroup Add inside the goroutine
- Copied mutex
- Lazy initialisation
- Slice handed off then modified
- Lock-order deadlock
- Reading the wait reason in a dump

## Shared map

Wrong: handlers write a package-level map.

```go
var cache = map[string]int{}
func set(k string, v int) { cache[k] = v }
```

Fix: a struct holding the map and a `sync.Mutex` declared above it, with every access through methods that lock. For a map that is written once per key and read often, `sync.Map` is an option; measure before choosing it, since a plain map with a mutex is usually clearer.

## Loop variable capture

Wrong on a module whose `go.mod` says a version before 1.22:

```go
for _, id := range ids {
    go func() { process(id) }()
}
```

Fix: pass it as an argument, `go func(id string) { process(id) }(id)`, or shadow it with `id := id`. From 1.22 each iteration has its own variable, so check the `go` directive before reporting this.

## WaitGroup Add inside the goroutine

Wrong: `Wait` may run before any `Add`.

```go
go func() { wg.Add(1); defer wg.Done(); work() }()
wg.Wait()
```

Fix: call `wg.Add(1)` before the `go` statement.

## Copied mutex

Wrong: a value receiver copies the struct, and the lock with it.

```go
func (c Counter) Inc() { c.mu.Lock(); c.n++; c.mu.Unlock() }
```

Fix: a pointer receiver. `go vet` reports this as copylocks.

## Lazy initialisation

Wrong: `if x == nil { x = build() }` reached from two goroutines. Fix: `sync.Once`, or initialise before the goroutines start.

## Slice handed off then modified

Wrong: the caller sends `items` to a goroutine and then appends to the same backing array. Fix: copy before handing off, or give up the reference and do not touch it again.

## Lock-order deadlock

Two goroutines take locks A and B in opposite orders. In a dump, each is in `sync.Mutex.Lock` and each holds the lock the other wants. Fix by a written order, or by merging the locks.

## Reading the wait reason in a dump

| State in the header | Meaning |
| --- | --- |
| `semacquire`, `sync.Mutex.Lock` | Waiting for a mutex or wait group |
| `chan receive`, `chan send` | Waiting on a channel counterpart |
| `select` | Waiting on several channels |
| `IO wait` | Waiting on the network poller |

The goroutine that holds a contended lock is rarely the one shown waiting; find the stack that is inside a critical section and blocked on something else.
