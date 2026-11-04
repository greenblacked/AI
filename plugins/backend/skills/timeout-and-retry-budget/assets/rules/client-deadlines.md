---
paths:
  - "**/*client*.go"
  - "**/*client*.py"
  - "**/*client*.ts"
  - "**/*client*.java"
  - "**/*client*.cs"
  - "**/*Client*.py"
  - "**/*Client*.ts"
  - "**/*Client*.java"
  - "**/*Client*.cs"
  - "**/*retr*.go"
  - "**/*retr*.py"
  - "**/*retr*.ts"
---

# Outbound client calls

- Set every outbound call's timeout from the caller's remaining deadline, not a library default, because a default the caller did not choose outlives the caller's own deadline.
- Retry at exactly one layer, because attempts multiply across layers (three layers of three is 27x on the deepest dependency).
- Retry only idempotent or keyed operations, because retrying a timed-out write otherwise turns uncertainty into a duplicate.
- Use capped full-jitter backoff, because uncapped or unjittered retries arrive in synchronised waves.
- Draw retries from a budget near 10 percent of first attempts, because a per-request limit still permits a retry on every request.
- Write the chain into `call-chain-budget.md` before adding a retry, because the product of attempts is only visible across the whole chain.
