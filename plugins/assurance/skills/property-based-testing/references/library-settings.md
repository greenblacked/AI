# Library settings

Read this at steps 4 and 5: how each library pins a counterexample, what its default run count is, how to reproduce a failure, and how to give pull requests and the nightly job different budgets. Defaults change between releases; confirm against the installed version's documentation before quoting a number to someone else.

## Contents

- [At a glance](#at-a-glance)
- [Hypothesis (Python)](#hypothesis-python)
- [fast-check (JavaScript and TypeScript)](#fast-check-javascript-and-typescript)
- [proptest (Rust)](#proptest-rust)
- [jqwik (Java and the JVM)](#jqwik-java-and-the-jvm)
- [rapid (Go)](#rapid-go)
- [Scheduled job checklist](#scheduled-job-checklist)

## At a glance

| Library | Default examples | Pin a counterexample | Reproduce a CI failure | Change the count per job |
| --- | --- | --- | --- | --- |
| Hypothesis | 100 (`max_examples`) | `@example(...)` | `--hypothesis-seed`, or the printed `@reproduce_failure` blob | Settings profiles, chosen with `--hypothesis-profile` or loaded in `conftest.py` |
| fast-check | 100 (`numRuns`) | `examples` option to `fc.assert` | The printed `seed` and `path` passed back to `fc.assert` | `fc.configureGlobal({ numRuns })` read from your own environment variable |
| proptest | 256 (`cases`) | Commit `proptest-regressions/` | The regression file replays it | `PROPTEST_CASES`, when the code does not set `cases` itself |
| jqwik | 1000 (`tries`) | An `@Example` test, or `@Property(seed = "...")` while debugging | The seed in the failure report | jqwik's configuration file, or `tries` on the annotation |
| rapid | 100 (`-rapid.checks`) | A table-driven example test | `-rapid.seed` with the printed seed | `-rapid.checks` on the command line |

## Hypothesis (Python)

```python
# conftest.py
import os
from hypothesis import settings

settings.register_profile("pr", max_examples=200, derandomize=True, deadline=None, print_blob=True)
settings.register_profile("nightly", max_examples=5000, deadline=None, print_blob=True)
settings.register_profile("dev", max_examples=50)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
```

```python
from hypothesis import example, given, note, strategies as st


@given(st.builds(Invoice, lines=st.lists(line_items(), max_size=20)))
@example(Invoice(lines=[]))  # empty invoice, issue 4127
@example(Invoice(lines=[LineItem(qty=1, unit_minor=-1)]))  # negative price, issue 4188
def test_invoice_round_trips(invoice):
    encoded = encode(invoice)
    note(f"encoded={encoded!r}")
    assert decode(encoded) == invoice
```

- Choose a profile per job with `HYPOTHESIS_PROFILE=nightly pytest` or `pytest --hypothesis-profile=nightly`. Register the profiles explicitly so the behaviour of each job is written in the repository rather than inferred from the environment.
- `derandomize=True` makes the pull-request run use the same examples every time for a given test and library version, so a red build is caused by the diff. The nightly profile leaves it off so each run explores new inputs.
- `deadline=None` removes the per-example time limit (200 ms by default), which on a shared runner produces failures that are about load, not correctness.
- `print_blob=True` puts a `@reproduce_failure(...)` line in the failure output. It is tied to the exact Hypothesis version and is for reproducing the failure locally while fixing it; replace it with `@example` before merging.
- `pytest --hypothesis-show-statistics` prints per-test timing and the `event()` labels you recorded, which is how you check the generator's distribution.
- Health checks such as `filter_too_much` and `too_slow` are findings about the generator. Suppress one only with a comment saying why the generator cannot be improved.
- The example database in `.hypothesis/` replays local failures first on the next local run. It is not shared with CI and not a substitute for `@example`. Keep it out of version control.

## fast-check (JavaScript and TypeScript)

```ts
import fc from 'fast-check';

const numRuns = Number(process.env.PROPERTY_RUNS ?? 100);
const seed = process.env.PROPERTY_SEED ? Number(process.env.PROPERTY_SEED) : undefined;
fc.configureGlobal({ numRuns, ...(seed !== undefined ? { seed } : {}) });

test('invoice round-trips', () => {
  fc.assert(
    fc.property(invoiceArb, (invoice) => {
      expect(decode(encode(invoice))).toEqual(invoice);
    }),
    { examples: [[{ lines: [] }]] }, // empty invoice, issue 4127
  );
});
```

- `PROPERTY_RUNS` and `PROPERTY_SEED` above are your own variable names, not fast-check's. Set a fixed seed in the pull-request job and leave it unset at night.
- On failure fast-check prints a `seed` and a `path`. Passing both back to `fc.assert` replays the exact failing case, and `endOnFailure: true` stops it there; use that locally while fixing, then pin the shrunk value in `examples` or a plain test.
- `fc.statistics(arbitrary, classify)` prints how often each class you name appears.
- For asynchronous code use `fc.asyncProperty` and `await fc.assert(...)`; for ordering bugs between promises, `fc.scheduler()` lets the library choose the interleaving and shrink it.

## proptest (Rust)

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn invoice_round_trips(invoice in invoice_strategy()) {
        let bytes = encode(&invoice);
        prop_assert_eq!(decode(&bytes).unwrap(), invoice);
    }
}
```

- When a property fails, proptest writes its seed to a file under `proptest-regressions/`, in a tree that mirrors the source directory, and replays it first on every later run. Commit those files; they are the pinned counterexamples. Add an ordinary `#[test]` for any case worth a name.
- Leave `cases` unset in the code and set `PROPTEST_CASES` per job (`PROPTEST_CASES=5000 cargo test` at night). A `ProptestConfig::with_cases(n)` in the code fixes the count and the variable no longer changes it.
- Use `prop_compose!` to build domain strategies from parts, and `prop_assume!` sparingly for the same reason as `assume` elsewhere.
- Model-based testing is in the separate `proptest-state-machine` crate.

## jqwik (Java and the JVM)

```java
class InvoiceProperties {
    @Property
    void roundTrips(@ForAll("invoices") Invoice invoice) {
        assertThat(Codec.decode(Codec.encode(invoice))).isEqualTo(invoice);
    }

    @Provide
    Arbitrary<Invoice> invoices() {
        return lineItems().list().ofMaxSize(20).map(Invoice::new);
    }

    @Example // empty invoice, issue 4127
    void emptyInvoiceRoundTrips() {
        Invoice empty = new Invoice(List.of());
        assertThat(Codec.decode(Codec.encode(empty))).isEqualTo(empty);
    }
}
```

- The default is 1000 tries per property, which is high for a pull request when properties are slow. Set the default in jqwik's configuration file rather than on each annotation, so the nightly job can raise it in one place; the user guide names the key for your version.
- jqwik keeps a local database of failures and by default replays the previous failing seed first. Like Hypothesis's, it is local; pin the case as an `@Example`.

## rapid (Go)

```go
func TestInvoiceRoundTrip(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        inv := invoiceGen().Draw(t, "invoice")
        got, err := Decode(Encode(inv))
        if err != nil {
            t.Fatalf("decode: %v", err)
        }
        if !reflect.DeepEqual(got, inv) {
            t.Fatalf("round trip changed the invoice: got %+v", got)
        }
    })
}
```

- Raise the count with `go test ./internal/invoice -rapid.checks=10000`. Pass the flag only to packages that import rapid: a test binary that does not define the flag rejects it.
- Reproduce with `-rapid.seed` and the seed from the failure output, then pin the shrunk value in a table-driven test.
- The standard library's `testing/quick` is frozen and does not shrink; prefer rapid for new properties. Go's native fuzzing (`go test -fuzz`) is coverage-guided and belongs to the `fuzz-harness` skill, though a fuzz target can assert a property too.

## Scheduled job checklist

- Runs every property at the nightly count with fresh seeds, on the default branch.
- Has no wall-clock deadline per example and a job timeout long enough for the count.
- Prints the seed for every failure and keeps the full log as an artefact.
- Files or updates one ticket per failing property, with the seed, the shrunk case and the commit, rather than relying on someone reading a red scheduled run.
- Is owned: a named team reads the tickets, pins the case and fixes the bug, or the job is noise within a month.
