# Correctness checklist

The question lists behind step 3 of the review, plus the cases the four passes do not
cover cleanly. Work a pass top to bottom against the lines in front of you and write the
answer down, including when the answer is "cannot fail here".

## Contents

- [Pass 1: does it do what it claims](#pass-1-does-it-do-what-it-claims)
- [Pass 2: the error path](#pass-2-the-error-path)
- [Pass 3: concurrency and ordering](#pass-3-concurrency-and-ordering)
- [Pass 4: hostile or absent input](#pass-4-hostile-or-absent-input)
- [Resources and lifetimes](#resources-and-lifetimes)
- [State machines and enums](#state-machines-and-enums)
- [Data and schema changes](#data-and-schema-changes)
- [Interface and compatibility changes](#interface-and-compatibility-changes)

## Pass 1: does it do what it claims

| Question | The shape it catches |
| --- | --- |
| Is every comparison the one the description implies — `<` where it says "up to and including"? | Off-by-one on pagination, quotas, retry counts and date ranges. Ask what happens at exactly the boundary value. |
| Does an early return skip work that the later path performs? | A guard clause added for one case that also short-circuits cleanup, auditing or a metric. |
| Is the condition inverted anywhere a negation was introduced? | `!isExpired` refactored into `isValid` where the two are not complements because of a third state. |
| Does the default value of a new parameter preserve existing behaviour at every existing call site? | A default that is correct for the new caller and wrong for the five old ones. |
| If a value is computed twice, are both computations the same? | A total recomputed in the view and the mailer, divergent after one is changed. |
| Does the change do anything the description does not mention? | Two changes in one diff, or a debug flag left flipped. |

Read the tests as the specification and check the implementation against it. Where the
tests say one thing and the code another, the defect is real and you found it without
running anything.

## Pass 2: the error path

For every call that crosses a boundary — network, disk, database, subprocess, another
service — answer all four:

1. What is the failure returned or thrown, and is it handled distinctly from success?
2. Is the state after the failure still valid, or is it partially applied? Name the
   variables and rows that are now inconsistent.
3. Is anything retried that is not idempotent? A retried charge is a double charge, a
   retried publish is a duplicate message, a retried migration is a corrupt schema.
4. Does the caller learn that it failed, or does the error become a logged line and a
   returned zero?

Specific shapes worth naming as findings:

- **Swallowed exception.** `except Exception: pass`, or a `catch` whose body only logs
  while the function returns its success value. The system now reports success for work
  it did not do.
- **Partial write with no compensation.** Two writes to different stores with no
  transaction, no outbox and no reconciliation. Ask what a crash between them leaves.
- **Error thrown inside cleanup.** A failure in a `finally`, `defer` or destructor that
  replaces the original error, which is the one that explained the problem.
- **A timeout that is absent or infinite.** An unbounded call holds a connection, a
  thread and eventually the pool. Ask what the timeout is; "the client default" is an
  answer only if someone has read it.
- **Retry with no cap and no backoff.** Converts a downstream blip into a self-inflicted
  denial of service, and converts a hard error into a timeout that is harder to diagnose.
- **An error path with no test.** The most common untested code in any codebase, and the
  code that runs when things are already going badly.

## Pass 3: concurrency and ordering

Ask these even in code that looks single-threaded — a web handler is concurrent by
construction, and a queue consumer with more than one worker is too.

| Question | The shape it catches |
| --- | --- |
| Is there a read, then a decision, then a write, on shared state? | Check-then-act. Two requests both read a balance of 100, both approve an 80 spend. Fix is a conditional update, a row lock or a unique constraint, not a re-read. |
| Does a counter or a set get updated by read-modify-write? | Lost update. Needs an atomic increment or a compare-and-set. |
| Can the same message be delivered twice? | At-least-once delivery meeting a non-idempotent handler. Ask for the idempotency key and where it is stored. |
| Can messages arrive out of order? | An update applied before the create it depends on, or a stale value overwriting a newer one because it arrived late. |
| Is a cache written before or after the source of truth, and what happens between? | A cache populated on the failure path, or a window in which readers see the new cache and the old row. |
| Are two locks taken in different orders in two places? | Deadlock, which will appear under load and never in test. |
| Does anything hold a lock across a network call? | Latency in a dependency becomes contention in your service. |
| Is shared mutable state captured by a closure, a goroutine, a thread or an async task? | The classic loop-variable capture, and state mutated by a background task nobody joined. |

## Pass 4: hostile or absent input

Run the value set — empty, one, many, huge, negative, zero, null, duplicate, unicode,
attacker-chosen — against each input the change introduces or newly trusts.

- **Injection.** Any string reaching SQL, a shell, a template, an LDAP filter, a header
  or a file path. Ask whether it is parameterised or escaped by the library rather than
  by hand. Concatenation is the finding, regardless of how safe the current callers are.
- **Path traversal.** User-controlled path segments joined onto a base directory. Ask
  what `../` does.
- **Authorisation after the fetch.** The object is loaded, then the check runs. The
  finding is real when an error message or a timing difference reveals the object's
  existence, and it is worse when the check is missing on one of several routes.
- **Missing object-level check.** Endpoints that verify the caller is logged in but not
  that this record is theirs. Check every route that takes an id from the request.
- **Caller-controlled limits.** A page size, a batch size or a timeout that comes from
  the request with no upper bound is a memory exhaustion primitive.
- **Regex over user input.** Nested quantifiers backtrack exponentially. A regex built
  from user input at all is a finding.
- **Deserialisation of untrusted data** into rich objects, and any parser given a size
  it did not choose — zip bombs, deeply nested JSON, oversized uploads.
- **Secrets and personal data in logs.** Tokens, keys, full request bodies and email
  addresses added to a log line or an error message that goes to a third party.

For a dedicated threat model of a whole surface rather than the input handling in one
diff, hand off to `security-review`.

## Resources and lifetimes

- Every acquired handle — file, connection, lock, transaction, temporary file, subscription — has a
  release on every path out of the function, including the error paths and the early returns.
- A connection pool has a bound, and the change does not hold connections across
  user-controlled waits.
- Unbounded growth: a list, map or channel that accumulates per request with nothing
  removing entries is a leak with a slow fuse.
- A background task started by a request has a lifetime tied to something; one tied to
  nothing survives shutdown and loses its work silently.

## State machines and enums

- A new enum variant or status value: find every `switch`, `match` or `if` chain over
  that type and check whether the new value falls into a default branch that now does
  the wrong thing silently.
- A new state in a workflow: enumerate the transitions into and out of it, and check
  that the terminal states are still terminal.
- A boolean that has become three-valued in practice (`true`, `false`, "not yet known")
  is worth raising as a should-fix — the third case is where the defect lives.

## Data and schema changes

- Is the migration reversible, and if not, is that stated and accepted?
- Does the new column have a default, and does adding it lock the table at your row
  count? Ask for the row count if the diff does not say.
- Does the code deploy before, after or with the migration, and does each ordering work?
  Code that reads a column the migration has not added yet fails on the old replica.
- Is there a backfill, is it batched, and is it restartable from where it stopped?
- Does anything read the old shape — a replica, a report, an export, another service?

Deeper mechanics belong to `db-migration`; in review, the job is to confirm the ordering
was considered and the rollback exists.

## Interface and compatibility changes

- A removed or renamed field in a response breaks every consumer that reads it. Ask who
  the consumers are; "nobody uses it" needs a search, not a belief.
- A widened accepted input is usually safe; a narrowed one is a breaking change even
  when the type is unchanged — a newly enforced maximum length rejects existing traffic.
- An error code or status changing is a contract change that no type checker sees.
- A change to serialised or persisted format has to be readable by the currently running
  version, because both will run at once during the deploy.
