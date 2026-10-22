# Shared-state catalogue

Each class of state that travels from a polluter to a victim, the symptom the victim
shows, how to observe the state directly, and the fix that isolates it. Read it at step 5,
once the polluter is known: match the victim's failure message against the symptom
column first, because it narrows the class faster than reading the polluter line by line.

## Contents

- [The table](#the-table)
- [Accumulating leaks](#accumulating-leaks)
- [A state guard for pytest](#a-state-guard-for-pytest)
- [When the leak is in production code](#when-the-leak-is-in-production-code)

## The table

| Leaked state | What the victim shows | How to see it | Isolating fix |
| --- | --- | --- | --- |
| A module-level global, singleton or class attribute changed by a test | A value or configuration it never set; behaviour of a mode another test switched on | Grep the polluter for assignments to module or class attributes; print the value at the start of the victim | Build the object per test and inject it; where the global must stay, reset it in a fixture teardown |
| A memoised cache (`functools.lru_cache`, a static map, a Go package-level map) | A stale result computed from another test's inputs | Call the cache's own introspection (`cache_info()` in Python) before and after the polluter | Clear it in teardown (`cache_clear()`), or inject the cache so each test gets its own |
| A patch or spy never restored (`mock.patch` started without `stop`, `jest.spyOn` without restore, an attribute set by hand) | A collaborator returning a canned value, or a call count that includes calls from another test | Check whether the patched attribute is still a mock object at the start of the victim | Patch through a scoped mechanism: a `with` block, the `monkeypatch` fixture, `restoreMocks: true` in Jest |
| Environment variables | A feature on or off, a different endpoint, a credential path that points nowhere | Diff `os.environ` (or the process environment) before and after the polluter | `monkeypatch.setenv`, `t.Setenv`, or a fixture that restores the snapshot |
| Working directory | Relative paths resolving somewhere else; "file not found" for a file that exists | Print the working directory at the start of the victim | `monkeypatch.chdir`, `t.Chdir` (Go 1.24 and later), or absolute paths built from the test file's location |
| Files at a fixed path (`/tmp/out.json`, a fixture file rewritten in place) | Unexpected contents, or a file that should not yet exist already existing | List the path before and after the polluter; `git status` shows a modified checked-in fixture | A per-test directory: `tmp_path`, `t.TempDir()`, or a directory named for the test |
| A fixed network port, or a server left running | "Address already in use", or the victim talking to the polluter's server and getting its answers | List listening sockets during the victim's setup | Bind to port 0 and read back the assigned port; stop the server in teardown |
| Database rows, sequences or schema | A count that is too high, a unique-constraint violation, an id that is not the one expected | Row counts per table before and after the polluter | A transaction per test rolled back in teardown, or data unique to each test; set up the rows a test needs rather than deleting afterwards |
| The clock, time zone or locale (a time freezer not stopped, `TZ` changed, a locale set, fake timers left on) | Dates off by hours or a day, timestamps that never advance, formatted numbers in another locale | Print the current time, `TZ` and locale at the start of the victim | Scope the freeze to the test with a context manager or decorator; restore `TZ` and call `time.tzset()` after changing it |
| The global random state (`random.seed` called in a test) | A "random" choice that is identical every time, or a sequence that changes when an unrelated test is added | Note whether the failure follows the seed; disable any plugin that reseeds per test | Inject a seeded generator instead of seeding the global one |
| Background threads, goroutines or timers still running | A failure in a later, unrelated test, sometimes in teardown; writes arriving after the polluter has finished | `threading.enumerate()` before and after; `goleak.VerifyNone(t)` from `go.uber.org/goleak` in Go | Stop and join everything the test started, in teardown |
| Logging handlers, warning filters, `logging.disable` | Captured logs empty; an expected warning not raised | Inspect the root logger's handlers and level, and `warnings.filters` | Restore in teardown; use `caplog` and `pytest.warns` instead of changing global configuration |
| Import-time side effects, `sys.modules` or `sys.path` edits, framework settings overrides, feature-flag clients, activated translations | Behaviour that depends on which test imported a module first | Diff `sys.modules` keys and `sys.path` before and after | Move the side effect out of import time; use the framework's scoped override (for Django, `override_settings`) |

PostgreSQL sequences are not rolled back with the transaction that called `nextval`, so a
test asserting a specific generated id can fail after any test that inserted into the same
table, even when every transaction was rolled back. Assert on the id the insert returned,
never on a literal.

## Accumulating leaks

When no single half of the candidate list breaks the victim but any long enough prefix
does, every test is leaking a little of something finite. Measure it rather than bisect it:

- File descriptors: count the entries under `/proc/self/fd` on Linux at the start of each
  test and watch it climb. In pytest, `-W error::ResourceWarning` turns an unclosed file or
  socket into an error at the test that leaked it.
- Connections: read the pool's own statistics, or the server's count of open connections,
  per test.
- Threads and goroutines: the counts above, per test.
- Memory: the process's resident size per test, when the victim fails with an allocation
  error.

The test where the count steps up is the polluter. Fix it the same way: release the
resource in teardown.

## A state guard for pytest

An autouse fixture that fails any test leaving the environment or working directory
changed. pytest sets up autouse fixtures before the fixtures a test requests, so this one is
torn down after `monkeypatch` has restored its changes, and only a leak that nothing restored
trips it.

```python
# conftest.py
import os

import pytest


def _env():
    # pytest rewrites PYTEST_CURRENT_TEST at setup and again at teardown, so it
    # always differs between the two snapshots and would fail every test.
    return {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}


@pytest.fixture(autouse=True)
def _no_leaked_process_state():
    env_before = _env()
    cwd_before = os.getcwd()
    yield
    assert _env() == env_before, "test changed os.environ without restoring it"
    assert os.getcwd() == cwd_before, "test changed the working directory without restoring it"
```

Extend it with whichever class the bisection found, so the guard grows from real incidents
rather than from a list nobody maintains. Keep each check cheap: it runs around every test.

## When the leak is in production code

A global the suite leaks between tests is often a global the service leaks between
requests, users or tenants: a per-request value cached at module level, a client configured
by the first caller, a mutable default argument. Before fixing the test, ask what happens
when two requests with different inputs hit the same process in sequence. If the answer is
the same thing that happened to the victim, the fix belongs in the code under test and the
finding belongs in the hand-back as a product defect, not a test-hygiene note.
