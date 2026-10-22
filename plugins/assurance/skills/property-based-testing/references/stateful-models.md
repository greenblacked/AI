# Stateful models

Read this at step 6, before writing the first model-based test. A stateful property generates a sequence of operations, applies each to the real system and to a model, and checks after every step that the two agree. When it fails, the library shrinks the sequence to the shortest one that still fails.

## Contents

- [Choosing the model](#choosing-the-model)
- [Hypothesis RuleBasedStateMachine](#hypothesis-rulebasedstatemachine)
- [fast-check commands](#fast-check-commands)
- [Other libraries](#other-libraries)
- [Making failures shrink well](#making-failures-shrink-well)

## Choosing the model

The model is the simplest thing that is obviously correct for the behaviour you are checking, and it ignores everything you are not checking.

| System under test | Model | What the model leaves out |
| --- | --- | --- |
| A key-value store, cache or repository | A dictionary | Persistence, eviction order unless eviction is under test, performance |
| A queue or log | A list | Partitioning, durability, delivery timing |
| An LRU cache with capacity n | A list of keys in recency order, truncated to n, plus a dictionary of values | Memory layout, concurrency |
| A bank account or ledger | A balance per account and a list of applied transfers | Storage, idempotency keys unless they are under test |
| A connection pool | A count of free and checked-out connections | The connections themselves |
| A file system wrapper | A dictionary from path to bytes | Permissions and timestamps, unless they are the point |

If the model starts to grow its own bugs, it is too detailed. Split the test: one model for the data, a separate property for the part you left out.

## Hypothesis RuleBasedStateMachine

```python
import shutil
import tempfile

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    consumes,
    invariant,
    precondition,
    rule,
)

from mystore import Store


class StoreMachine(RuleBasedStateMachine):
    keys = Bundle("keys")

    def __init__(self):
        super().__init__()
        self.path = tempfile.mkdtemp()  # fresh state for every sequence
        self.store = Store.open(self.path)
        self.model = {}

    @rule(target=keys, key=st.text(alphabet="abcd", min_size=1, max_size=3))
    def new_key(self, key):
        return key  # small alphabet so keys collide

    @rule(key=keys, value=st.binary(max_size=32))
    def put(self, key, value):
        self.store.put(key, value)
        self.model[key] = value

    @rule(key=keys)
    def get(self, key):
        assert self.store.get(key) == self.model.get(key)

    @rule(key=consumes(keys))
    def delete(self, key):
        self.store.delete(key)
        self.model.pop(key, None)

    @rule()
    def reopen(self):
        self.store.close()
        self.store = Store.open(self.path)  # persistence bugs live here

    @precondition(lambda self: len(self.model) > 0)
    @rule()
    def clear(self):
        self.store.clear()
        self.model.clear()

    @invariant()
    def sizes_agree(self):
        assert len(self.store) == len(self.model)

    def teardown(self):
        self.store.close()
        shutil.rmtree(self.path, ignore_errors=True)


StoreMachine.TestCase.settings = settings(max_examples=200, stateful_step_count=50, deadline=None)
TestStore = StoreMachine.TestCase
```

- `Bundle` holds values produced by earlier rules, so later rules operate on keys that exist. `consumes` removes the value from the bundle when the rule uses it.
- `@invariant()` runs after every step. Put cheap global checks there and specific checks in the rules.
- `@precondition` keeps a rule from being chosen when the state does not allow it; prefer it to an early `return` inside the rule, which wastes a step and confuses shrinking.
- `stateful_step_count` bounds the length of each sequence. Most bugs need fewer than ten steps; the bound exists for speed.
- The pull-request and nightly profiles from step 5 apply here too; the per-class settings above override them, so leave `max_examples` out of the class if you want the nightly profile to raise it.

## fast-check commands

```ts
import fc from 'fast-check';
import { Store } from './store';

type Model = { entries: Map<string, string> };

class PutCommand implements fc.Command<Model, Store> {
  constructor(readonly key: string, readonly value: string) {}
  check(_m: Readonly<Model>) { return true; }
  run(m: Model, r: Store) {
    r.put(this.key, this.value);
    m.entries.set(this.key, this.value);
  }
  toString() { return `put(${JSON.stringify(this.key)}, ${JSON.stringify(this.value)})`; }
}

class GetCommand implements fc.Command<Model, Store> {
  constructor(readonly key: string) {}
  check(_m: Readonly<Model>) { return true; }
  run(m: Model, r: Store) {
    expect(r.get(this.key)).toEqual(m.entries.get(this.key));
  }
  toString() { return `get(${JSON.stringify(this.key)})`; }
}

class DeleteCommand implements fc.Command<Model, Store> {
  constructor(readonly key: string) {}
  check(m: Readonly<Model>) { return m.entries.has(this.key); }   // precondition
  run(m: Model, r: Store) {
    r.delete(this.key);
    m.entries.delete(this.key);
    expect(r.size()).toBe(m.entries.size);
  }
  toString() { return `delete(${JSON.stringify(this.key)})`; }
}

const key = fc.constantFrom('a', 'b', 'c', 'd');          // small pool so operations collide
const allCommands = [
  fc.tuple(key, fc.string({ maxLength: 16 })).map(([k, v]) => new PutCommand(k, v)),
  key.map((k) => new GetCommand(k)),
  key.map((k) => new DeleteCommand(k)),
];

test('store behaves like a map', () => {
  fc.assert(
    fc.property(fc.commands(allCommands, { maxCommands: 50 }), (cmds) => {
      const setup = () => ({ model: { entries: new Map<string, string>() }, real: new Store() });
      fc.modelRun(setup, cmds);
    }),
  );
});
```

- `check` is the precondition; commands whose `check` returns false are skipped in that state.
- `toString` is what appears in the shrunk failure report, so make it a readable call.
- The `setup` function runs once per generated sequence and must return fresh state each time.
- Use `fc.asyncModelRun` when commands are asynchronous, and `fc.scheduledModelRun` with `fc.scheduler()` when the bug is about the order in which promises settle.

## Other libraries

- **proptest**: the `proptest-state-machine` crate provides a reference state machine (the model) and a system under test, with transitions generated from strategies.
- **jqwik**: offers stateful testing through action chains; see its user guide for the current API, which has changed between major versions.
- **rapid**: `t.Repeat` takes a map of named actions and runs them in a generated order, with a check function called after each.

## Making failures shrink well

- **Fresh state per sequence.** A real system shared across sequences turns one failure into an order-dependent one that shrinks to nonsense.
- **A controllable clock.** Expiry, retries and timeouts need a clock the test advances as an operation (`advance_clock(seconds)`), never real sleeps, or the sequence is slow and its result depends on the runner.
- **No concurrency in the first model.** Get the sequential model passing first. Concurrency bugs need a separate test that controls interleaving (`fc.scheduler`, or a linearisability checker), and mixing the two makes neither readable.
- **Readable operation names.** The shrunk sequence is the bug report. `put("a", b"")`, `reopen()`, `get("a")` tells the reader the defect; an opaque object dump does not.
- **Pin the shrunk sequence.** Write it out as an ordinary example test that performs those operations in order. The stateful property found it; the example keeps it found.
