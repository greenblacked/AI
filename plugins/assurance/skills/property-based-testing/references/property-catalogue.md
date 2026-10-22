# Property catalogue

Read this at step 1 when the one-sentence property will not come. Each entry gives the property, the generator it needs, and the trap that makes it pass when it should not.

## Contents

- [Serialisation and encoding](#serialisation-and-encoding)
- [Text processing](#text-processing)
- [Money and arithmetic](#money-and-arithmetic)
- [Collections and ordering](#collections-and-ordering)
- [Search, filtering and queries](#search-filtering-and-queries)
- [Time and scheduling](#time-and-scheduling)
- [Access rules and configuration](#access-rules-and-configuration)
- [Choosing an oracle](#choosing-an-oracle)

## Serialisation and encoding

| Property | Generator | Trap |
| --- | --- | --- |
| `decode(encode(x)) == x` for every valid value | The domain object, built from its fields, including optional fields absent and present | Equality that ignores the field that is lost. Compare with a full structural equality, not the object's own `__eq__` if that skips fields. |
| `encode(decode(b)) == b` | Only for a canonical format, where each value has exactly one encoding | Non-canonical formats (JSON with whitespace, maps with unordered keys) fail this legitimately. Assert it only where the specification promises canonical output. |
| Old reader accepts new writer's output, minus new fields | Objects from the current schema, encoded and read with the previous version's decoder | Running both versions in one process is awkward; a fixture of encoded bytes from the old version, read by the new decoder, covers the other direction. |
| Floats survive the round trip | Include `NaN`, both infinities, `-0.0`, subnormals and the largest finite value | `NaN != NaN`, so compare with an equality that treats two `NaN`s as equal, or exclude them and say so. |

## Text processing

| Property | Generator | Trap |
| --- | --- | --- |
| A slug, escape or sanitiser is idempotent | Arbitrary Unicode text, including combining marks, right-to-left text and characters outside the Basic Multilingual Plane | ASCII-only generators hide every normalisation bug. Let the library generate full Unicode. |
| `unescape(escape(s)) == s` | Text containing every character the escaper treats specially | Weight the generator toward the special characters, or they appear too rarely to matter. |
| Truncation never exceeds the limit and never splits a character | Strings longer and shorter than the limit, with multi-byte characters near the cut | Asserting the length in code units when the limit is in bytes, or the reverse. |
| Case-insensitive comparison is symmetric and consistent with lowercasing | Pairs drawn from a small alphabet with case variants | Locale-sensitive lowercasing (the Turkish dotless i) makes this fail on some machines only. Pin the locale. |

## Money and arithmetic

| Property | Generator | Trap |
| --- | --- | --- |
| Allocating an amount across n parts sums back to the amount exactly | Amounts in minor units and part counts from one to a modest bound | Floating-point currency. Generate integers in minor units, and treat any float in the code as the finding. |
| A discount never makes a price negative and never increases it | Prices, discount kinds and stacking orders | Applying discounts in a different order changing the result may be correct; state which order the business specifies. |
| Converting currency there and back loses at most the rounding of two conversions | Amounts and rates with realistic precision | Asserting exact equality where the specification allows one minor unit of rounding per step. |
| Scaling every line by k scales the total by k | Line items and small integer factors | Rounding per line versus on the total. Decide which the code promises before asserting. |

## Collections and ordering

| Property | Generator | Trap |
| --- | --- | --- |
| Sorting gives an ordered permutation of the input | Lists with duplicates drawn from a small pool | Checking only that the output is ordered; a function that returns an empty list passes. Check it is a permutation too. |
| A stable sort preserves the order of equal keys | Records with keys from a pool of three or four values and a unique tag | Unique keys make stability untestable; force collisions. |
| Merge of two sorted lists equals sorting their concatenation | Two lists, each sorted after generation | This is an oracle property; the sort is the oracle. |
| Paging through results returns every item exactly once | A dataset and page sizes from one to larger than the dataset | Items inserted between page requests. Hold the dataset fixed for the property, and write a separate stateful test for concurrent inserts. |
| Deduplication is idempotent and the output is a subset of the input | Lists with deliberate duplicates | Asserting idempotence alone; a function returning nothing is idempotent. |

## Search, filtering and queries

These are metamorphic relations: the exact output is unknown, but how it must change is known.

| Relation | Generator | Trap |
| --- | --- | --- |
| Adding a filter never increases the result count | A dataset and a base query, plus one extra predicate | Filters that widen by design, such as an OR clause. Restrict the extra predicate to AND. |
| Results are the same whatever order the rows were inserted in | A dataset and a permutation of it | Result ordering without an explicit sort key legitimately differs. Compare as sets, or sort first. |
| A query for an item just inserted finds it | A dataset, a new item, and a query built from the item's own fields | Search indexes with eventual consistency. Wait on the index's own refresh mechanism, not a sleep. |
| Pagination limit k returns the first k of the unlimited query | A dataset and limits around its size | Ties in the sort key make the first k ambiguous. Add a unique tie-breaker to the sort. |

## Time and scheduling

| Property | Generator | Trap |
| --- | --- | --- |
| Adding a duration and subtracting it returns the original instant | Instants across years and durations including negative | Calendar arithmetic (add one month) is not invertible: 31 January plus one month minus one month is not 31 January. Use fixed durations for this property. |
| The next run time is after now and satisfies the schedule | Schedules, and instants including daylight-saving transitions in several zones | Generating instants only in UTC hides every transition bug. Generate zone and local time together. |
| Converting between zones and back preserves the instant | Instants and zone names from the zone database | Local times in a spring-forward gap do not exist; test conversion of instants, not of local wall-clock times, for this property. |

## Access rules and configuration

| Property | Generator | Trap |
| --- | --- | --- |
| Granting an extra permission never removes access | A user, a resource, a permission set and one extra permission | Explicit deny rules break monotonicity by design. Exclude them from the generator or state the exception. |
| Merging configuration with an empty overlay is the identity | Configuration trees with nested maps and lists | List merge semantics (replace or append) differ by key. Assert per key class. |
| Merging is associative where the specification says so | Three configuration trees | Many merge functions are not associative; find out before asserting, and record which. |

## Choosing an oracle

An oracle comparison is only as good as the oracle. A good one is:

- **Simpler than the code under test**: a linear scan instead of an index, a list instead of a tree, an exact rational instead of a float, a brute-force search over small inputs.
- **Independently written**: the previous implementation during a rewrite, a different library, a reference implementation from the specification. A copy of the new code's logic is not an oracle.
- **Fast enough on small inputs**: bound the generator so the oracle's worst case stays cheap. Brute force over inputs of size eight finds most of what it would find at size eight thousand.

During a rewrite, keep the old implementation behind a test-only import until the property has run at nightly volume for long enough to be trusted, then delete it and keep the pinned examples it produced.
