# Approval contract

Use this contract for consequential agent actions such as sending, purchasing, deleting,
deploying or publishing. Approval records express human intent; they do not replace the
tool's authorization decision.

## Canonical request

Construct the preview and approval record from one canonical representation after schema
validation, default expansion and trusted identifier resolution. Include every field that
can change the effect:

- action and tool version;
- principal plus target tenant or account;
- recipient or destination;
- amount, currency, quantity or other bounded value;
- canonical resource identifiers and expected versions;
- enumerated batch members in stable order;
- irreversible impact, expiry and a unique approval identifier.

Reject unknown fields and ambiguous identifiers before preview. Store a digest or opaque
record over the canonical request. Any field change, batch membership change or resolver
result change invalidates approval and requires a new preview.

## Execution protocol

1. Authenticate the current principal from trusted session state.
2. Load the approval by its unique identifier and verify principal, scope and expiry.
3. Rebuild the canonical request and compare it exactly with the approved request.
4. Resolve mutable references and verify their expected versions.
5. Authorize the current principal for the final action, tenant and resolved resources.
6. In the same transaction or conditional write as the effect, enforce authorization and
   expected resource versions where the backend supports it.
7. Mark the approval consumed and record the decision and result atomically with the
   effect where possible.

If the backend cannot couple the checks and effect atomically, recheck immediately before
execution, use conditional writes where available, minimize the interval, and document
the residual race. Do not claim that a preflight check eliminates time-of-check to
time-of-use risk.

## Replay, retries and idempotency

Make approval single-use unless the preview explicitly describes a bounded repeatable
operation. Reject reuse for a different canonical request, principal, tenant or tool
version.

Give every approved effect an idempotency key derived from the approval identifier and
operation slot. Persist the result against that key. A retry after a timeout returns the
recorded result or resumes the same operation; it does not create a second payment,
message, deployment or deletion. For a batch, allocate one stable slot per member so a
partial retry cannot repeat completed members or silently add new ones.

Distinguish these states in the audit record: approved but unused, executing, succeeded,
failed without effect, outcome unknown, and consumed. An unknown outcome requires
reconciliation against authoritative state before retry, not a fresh blind execution.

## Evidence to retain

Retain the approval identifier, canonical request digest, safe preview, principal,
tenant, resource versions, authorization decision, idempotency key, timestamps and final
effect identifier. Redact secrets and sensitive content while preserving correlation.
