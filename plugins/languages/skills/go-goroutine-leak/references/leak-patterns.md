# Recurring leak patterns

Read this once the leaking group is identified and the cause is not obvious from its wait reason.

## Contents

- Unbuffered send after a timeout
- Select without a cancellation case
- Response body not closed
- Timers and tickers in loops
- Worker pools and errgroup
- Reading debug=2 output

## Unbuffered send after a timeout

Wrong: the caller stops waiting, the goroutine blocks forever on the send.

```go
ch := make(chan result)
go func() { ch <- fetch() }()
select {
case r := <-ch:
    use(r)
case <-time.After(time.Second):
    return errTimeout
}
```

Fix: `ch := make(chan result, 1)` so the send always completes. The wait reason in the dump is `chan send`.

## Select without a cancellation case

Wrong: the loop waits on an input that may never arrive again.

```go
for {
    select {
    case job := <-jobs:
        handle(job)
    }
}
```

Fix: add `case <-ctx.Done(): return`, and ensure the context is cancelled when the owner finishes. Wait reason: `select` or `chan receive`.

## Response body not closed

An `http.Response` body that is neither closed nor read to the end keeps the connection and its reader goroutines alive. In the dump these appear as `IO wait` under `net/http.(*persistConn).readLoop` and `writeLoop`, in pairs, growing with outbound request volume. Fix: `defer resp.Body.Close()` immediately after the error check, and drain with `io.Copy(io.Discard, resp.Body)` when you do not read it all. Set `Client.Timeout` or per-request contexts.

## Timers and tickers in loops

`time.NewTicker` without `Stop` leaks the ticker and usually the goroutine ranging over it. `time.After` inside a `for` loop allocates a timer per iteration that is not released until it fires on toolchains before Go 1.23. Use one timer you `Reset`, or a context deadline.

## Worker pools and errgroup

A pool that ranges over an input channel never exits unless the channel is closed; the owner that sends must be the one that closes. With `errgroup`, use `g, ctx := errgroup.WithContext(parent)` and have every goroutine select on `ctx.Done()` around sends, otherwise one failed worker leaves the others blocked on a full channel.

## Reading debug=2 output

Each goroutine begins with a header such as `goroutine 123 [chan send, 14 minutes]:`. The bracket holds the wait reason and, once over a minute, how long it has waited. A group whose waits keep lengthening between two dumps never completes. The `created by` line at the bottom of each stack names the function that started the goroutine, which is usually the owner that needs the fix.
