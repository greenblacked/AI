# Tracing a path through code that does not read statically

Read this when step 3 of the workflow loses the thread: the call goes into an interface,
a container, a queue or an event name, and the editor's "go to definition" lands on
something abstract or on nothing at all.

## Contents

- [The three places a static trace breaks](#the-three-places-a-static-trace-breaks)
- [Crossing dependency injection](#crossing-dependency-injection)
- [Crossing an event bus or a queue](#crossing-an-event-bus-or-a-queue)
- [Crossing dynamic dispatch and string-keyed registries](#crossing-dynamic-dispatch-and-string-keyed-registries)
- [Using the runtime instead of guessing](#using-the-runtime-instead-of-guessing)
- [Reading a stack trace as a free map](#reading-a-stack-trace-as-a-free-map)
- [Recording the trace](#recording-the-trace)

## The three places a static trace breaks

Every lost trace is one of three shapes, and each has a different cheapest answer.

| Shape | What you see | Cheapest way across |
| --- | --- | --- |
| Indirection by type | The call site names an interface with four implementations | Find the wiring, not the implementations: whatever constructs the object decides which one runs. |
| Indirection by message | The code publishes `order.created` and returns | Search the event name as a literal string across the whole organisation's repositories, not just this one. |
| Indirection by key | A registry, a plugin table, `getattr`, a handler map keyed by a string | Find the registration sites, which are usually all in one file or one decorator. |

Deciding which shape you are in takes seconds and saves the twenty minutes people spend
reading all four implementations of an interface, three of which are a test double, a
deprecated version and a variant used by one customer.

## Crossing dependency injection

The wiring is the answer, and it is in one of a small number of places: a module or
provider file, a container configuration, a `main` function that constructs the object
graph, or an annotation that binds an interface to a class.

```bash
rg -n "bind\(|provide|register|singleton|AddScoped|@Provides|@Component|useClass" -g '!**/test*/**'
```

Read the binding for the interface you are stuck on, then go to that single
implementation. If the binding is conditional on an environment variable or a profile,
note which value production uses — orienting against the wiring used in tests is a
common and expensive mistake, because the test wiring is often a stub that does nothing.

## Crossing an event bus or a queue

The publisher and the consumer may not be in the same repository, which is why searching
locally returns one hit and a dead end.

1. Take the event or topic name as a literal string.
2. Search every repository you have access to for it, not just this one.
3. If the name is constructed (`f"order.{action}"`), search for the prefix instead.
4. Failing that, read the broker: a topic's consumer groups name the services that
   subscribe, and that list is authoritative in a way that code search is not.

Record the hop in the trace as a boundary rather than a call. The two sides can be
deployed separately, which means the contract between them is a real contract even when
nobody wrote it down, and it is exactly the kind of coupling that makes a first change go
wrong.

## Crossing dynamic dispatch and string-keyed registries

Handler maps, plugin loaders, decorators that register on import, and reflection over
class names all hide the call graph from search. Find the registration mechanism once and
the whole family becomes readable.

```bash
rg -n "register\(|@register|HANDLERS\[|importlib|getattr\(|Class\.forName|reflect\."
```

The important consequence for orientation is in step 8 of the workflow: code reached only
through one of these mechanisms has no inbound reference that grep can see, so it looks
dead and is not. Anything found here belongs on the "live despite appearances" list in
the orientation note.

## Using the runtime instead of guessing

Static reading has a point of diminishing returns, usually reached after the second lost
hop. Past it, running the code is cheaper than reasoning about it.

- **A breakpoint at the entry point, stepped forward.** The debugger answers in one run
  the question a morning of reading answers unreliably: which implementation, which
  branch, which config value.
- **A temporary log line at each candidate hop.** When a debugger is impractical — a
  distributed path, a production-only code path, a language with an awkward local setup —
  logging the function name and one identifying field at four candidate sites tells you
  which of them the request actually visits.
- **Existing tracing.** If the service emits spans, one real trace in the tracing UI is
  the path, with timings, already drawn. Check for that before instrumenting anything.
- **The test suite as a harness.** Running the integration test for the path under a
  debugger gives you a reproducible entry with fixtures already in place.

Remove temporary logging before the first change lands; a log line added during
orientation and forgotten becomes noise in someone else's incident.

## Reading a stack trace as a free map

An existing exception in the logs or the error tracker is the path already traced, by the
runtime, through the exact wiring production uses. It is the single highest-value artefact
for orientation and it is usually sitting unread in the error tracker.

Read it from the bottom up: the bottom frames are the entry point and the framework, the
middle frames are the application's own path, and the top frame is where it broke. The
middle section is the trace you were trying to build by hand. Strip the framework frames,
keep the ones in the repository's own package, and that list is step 3 of the workflow
with no work.

That order holds for Java, JavaScript, Go and Rust. Python prints its traceback the other
way round — it says so at the top, "most recent call last" — so a Python traceback is read
downwards: the entry point is at the top and the last line is where it broke.

## Recording the trace

One line per hop, in the order the request visits them, each carrying file, function and
what changes:

```text
1. routes/checkout.ts:42  POST /checkout        validates the body, resolves the tenant
2. services/cart.ts:118   priceCart()           applies discounts, reads the price table
3. services/payment.ts:67 authorise()           calls the payment provider, 8s timeout
4. repo/orders.ts:203     insertOrder()         single transaction, writes orders + items
5. events.ts:31           publish order.created consumed elsewhere; boundary, not a call
```

Mark each hop you confirmed at runtime rather than by reading, because the two have
different reliability and the next reader deserves to know which is which.
