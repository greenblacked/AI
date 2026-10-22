# Context propagation by transport

Read the row for the transport you are on. Each states what must carry the context, who
injects, who extracts, and the usual way it is lost.

| Transport | Carrier | Usual loss |
| --- | --- | --- |
| HTTP between services | `traceparent` and `tracestate` request headers | Proxy or gateway allow-list; client built from a raw socket library that bypasses the instrumented client |
| gRPC | Metadata keys of the same names | Interceptor not registered on the channel, or on only one side |
| Message queue | Message headers or attributes | Publisher does not inject; consumer framework creates a fresh context per message; broker or bridge copies the body but drops headers |
| Thread pool, executor, async callback | In-process context object | Task submitted without wrapping the current context, so the worker runs with an empty one |
| Scheduled or batch job | Stored with the job record | Job row has no field for context; the job starts a new trace, which is acceptable if it links back |
| Serverless front door | Integration-specific | Platform regenerates its own trace id and passes yours only if configured to |
| Browser to backend | Header on fetch calls | Cross-origin requests need the header allowed in the CORS preflight response |

## Checks per boundary

- Send a request with a known `traceparent` and read it on the far side of the boundary.
- For a queue, publish one message by hand with a known header and see whether the
  consumer span carries that trace id.
- For a pool, log the current trace id before submitting and inside the task.
- For fan-in consumers, expect span links rather than a single parent.
