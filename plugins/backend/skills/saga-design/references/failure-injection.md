# Failure injection for sagas

Contents: kill points, fault types, assertions.

## Kill points

For a saga with n steps there are about 3n+1 places to die: before the first state write, between the state write and the remote call, after the remote call and before the result is recorded, and after recording. Enumerate them from the code, give each a named hook (`crash_after("reserve.call")`), and run the saga once per hook with a process kill, not an exception, so no cleanup runs.

After restart the recovery path must pick the saga up with no manual action. A recovery that needs a person to re-run it is the stuck-saga query working, not the saga recovering.

## Fault types per step

| Fault | What it checks |
| --- | --- |
| Immediate error | The compensation chain runs in reverse order |
| Timeout where the request later succeeds | Cancellation intent refuses the late request, or reconciliation finds it |
| Timeout where the request never arrived | Compensation treats "not found" as success |
| Duplicate delivery of the same command | Idempotency key makes it a no-op |
| Compensation itself fails | Retried with backoff, then `failed_needs_human` |

## Assertions

After every run, query each participant directly: reservations held for this saga id, charges and authorisations, messages sent. The expected set is either every forward effect present or none present net of compensations. Also assert the saga row is terminal and that no non-terminal saga is older than its deadline.
