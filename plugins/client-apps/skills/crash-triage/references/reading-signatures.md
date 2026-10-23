# Reading crash signatures

Common exception types mapped to their usual causes and the first thing to check. Read
this at step 6, when the exception type is unfamiliar or the top frame is inside the
system. A usual cause is a starting hypothesis, not a diagnosis — confirm it against the
split from step 5.

## Contents

- [iOS exception types](#ios-exception-types)
- [Android exceptions](#android-exceptions)
- [Reports that are not crashes](#reports-that-are-not-crashes)
- [When the top frame is in the system](#when-the-top-frame-is-in-the-system)

## iOS exception types

| Exception type (signal) | Usual cause | First check |
| --- | --- | --- |
| `EXC_BREAKPOINT` (`SIGTRAP`) | A Swift runtime trap: force-unwrapping `nil`, index out of range, arithmetic overflow, a failed `as!` cast, `fatalError` or `preconditionFailure` | The line of the first frame in your code; the operation on it that can trap |
| `EXC_BAD_ACCESS` (`SIGSEGV` or `SIGBUS`) | Use after free, an `unowned` or unsafe pointer to a released object, a data race on a reference, or a stack overflow from deep recursion | Address Sanitizer and Thread Sanitizer on the reproducing path; a crashing address near the stack limit points at recursion |
| `EXC_CRASH` (`SIGABRT`) | An uncaught Objective-C exception, or a library calling `abort()` | The Last Exception Backtrace and the exception name: `NSInvalidArgumentException` (often an unrecognised selector), `NSRangeException`, `NSInternalInconsistencyException` (often table or collection view batch updates whose counts do not add up) |
| `EXC_CRASH` (`SIGKILL`) with a Termination Reason | The system killed the process; not a code fault | Route to `anr-watchdog-triage` |
| `EXC_GUARD` | Misuse of a guarded system resource, such as closing a file descriptor the system owns | The guard type named in the report |
| `EXC_RESOURCE` | A resource limit: CPU, wakeups or memory. CPU and wakeup reports are usually diagnostics rather than fatal | Memory to `anr-watchdog-triage`; CPU and wakeups to `battery-drain-diagnosis` |

A crash in UIKit or SwiftUI internals on a thread other than the main thread is almost
always UI work done off the main thread. The Main Thread Checker in a debug build
catches it before release.

## Android exceptions

| Exception | Usual cause | First check |
| --- | --- | --- |
| `NullPointerException`, Kotlin `!!`, `UninitializedPropertyAccessException` | A value read after its owner's lifecycle ended — a view after `onDestroyView`, a `lateinit` before it was set | Whether the read sits in a callback that can outlive the screen; scope it to `viewLifecycleOwner` |
| `IllegalStateException: Can not perform this action after onSaveInstanceState` | A fragment transaction after state was saved, often from an async result | Run the transaction from a lifecycle-aware scope; `commitAllowingStateLoss` only where losing it is acceptable |
| `IllegalStateException: Fragment ... not attached to a context` | An async callback after the fragment detached | Cancel the work with the lifecycle rather than checking `isAdded` everywhere |
| `WindowManager$BadTokenException` | Showing a dialog or popup for an activity that is finishing or gone | The lifecycle state at the call site |
| `OutOfMemoryError` | Java heap exhausted; the allocating frame is the last straw, not necessarily the cause — bitmaps decoded at full size are the classic | A heap dump on a low-RAM device; bitmap sizes against the views showing them |
| `TransactionTooLargeException` | A binder transaction over the per-process buffer, usually a large saved-instance-state bundle or intent extra | What is put in `onSaveInstanceState` and intent extras |
| `DeadObjectException`, `DeadSystemException` | The remote process or system server died mid-call | Usually a symptom; check whether it clusters on one OEM or OS version |
| `ForegroundServiceStartNotAllowedException` | Starting a foreground service from the background on Android 12 or later | Whether the start qualifies for an exemption, or should be a WorkManager job |
| `ForegroundServiceDidNotStartInTimeException` | `startForeground()` not called promptly after `startForegroundService()` | Blocking work before `startForeground()` in the service's start path |
| `IllegalArgumentException` naming `FLAG_IMMUTABLE` or `FLAG_MUTABLE` | A `PendingIntent` created without a mutability flag when targeting Android 12 or later, often inside an old SDK | Which library created it, and its fixed version |
| `SecurityException` | A missing runtime permission, or a permission revoked while the app ran | The permission check before the call |
| Native `SIGSEGV`, `SIGABRT` | A native bug in your code or a third-party SDK's library | Which `.so` the top frame is in, its Build ID, and whether it is yours |

## Reports that are not crashes

- iOS `EXC_CRASH (SIGKILL)` with `0x8badf00d`, `0xdead10cc` or another termination code,
  and any jetsam event: `anr-watchdog-triage`.
- Android ANRs and low-memory kills appear in vitals and in `ApplicationExitInfo`, not as
  exceptions: `anr-watchdog-triage`.
- A crash on the first launch after an update whose stack sits in Core Data, Room, SQLite
  or a migration class: `on-device-migration-safety`.

## When the top frame is in the system

1. Find the first frame in your own code below it; that is where the bad input or call
   came from.
2. Check whether the signature concentrates on one OS version or manufacturer. A system
   bug usually does, and the fix is a workaround guarded by version, plus a report to the
   vendor.
3. If no frame of yours appears at all, check the other threads and the breadcrumbs for
   what the app was doing, and whether a third-party SDK owns the thread.
