# Normalise and bucket

How to turn two piles of responses into a short list of findings: normalise only what the
old-against-old run proved nondeterministic, compare structurally, sign each difference, and
close each bucket.

## Contents

- [Normaliser rules as jq filters](#normaliser-rules-as-jq-filters)
- [Flattening a response into comparable paths](#flattening-a-response-into-comparable-paths)
- [The bucket signature](#the-bucket-signature)
- [Ranking and reading buckets](#ranking-and-reading-buckets)
- [Classification and sign-off](#classification-and-sign-off)

## Normaliser rules as jq filters

Keep the rules in one file under version control, one rule per field, each with a comment
naming the old-against-old evidence (bucket signature and count). Apply the same file to both
sides; a rule applied to one side only manufactures differences.

Sort object keys on every document. Key order is not meaningful in JSON and serialisers differ:

```bash
jq -S . response.json
```

Replace a nondeterministic value with a shape check rather than deleting it. A timestamp that
is present and well formed becomes a fixed token; one that is missing or malformed stays as it
is and shows up in the diff:

```jq
walk(
  if type == "object" and has("createdAt")
     and (.createdAt | type) == "string"
     and (.createdAt | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T"))
  then .createdAt = "TIMESTAMP"
  else . end
)
```

The same pattern for generated identifiers, matching the format the old system emits:

```jq
walk(
  if type == "object" and has("requestId")
     and (.requestId | type) == "string"
     and (.requestId | test("^[0-9a-f-]{36}$"))
  then .requestId = "UUID"
  else . end
)
```

Sort arrays only where the contract says order is not meaningful, and sort by a stable key
rather than by the whole element:

```jq
if type == "object" and (.items | type) == "array"
then .items |= sort_by(.id)
else . end
```

Any other body (an error body, a 404, an empty object, or a string or array at the top level)
is left alone, so it reaches the diff instead of failing normalisation and dropping the pair.
The outer `type == "object"` test matters: `.items` on a string or an array is a jq error
(exit 5), and on an object without the key an `|=` update would add `"items": null` to a body
that never had one.

Sorting every array (`walk(if type == "array" then sort else . end)`) is tempting and wrong: it
hides the regression where a list that must be ordered by date comes back in insertion order.

Numbers: compare by value, not by serialised text. `1.10` from the old system and `1.1` from
the new one are the same number, and recent `jq` versions keep a literal's original text on
output, so a text diff of flattened output reports them as different. Compare numeric values
with `==` in the comparison step instead. A real precision difference (`0.30000000000000004`
against `0.3`) is a finding about rounding, not noise; bucket it and decide.

Headers: compare a fixed allow-list (`Content-Type`, `Cache-Control`, `Location`,
`Content-Encoding`, any custom header clients read). `Date`, `Server`, trace headers and
`ETag` values derived from generated content are excluded by listing what is compared, not by
listing what is ignored.

## Flattening a response into comparable paths

Flatten each normalised body into one line per leaf. Keep the full indexed path for the
comparison and derive the collapsed path (indices replaced by `[]`) only for the signature.
Collapsing before comparing would make a reordered list or a swapped pair of elements flatten
to identical lines and pass. A leaf is a scalar or an empty array or object, so that `[]`
against a missing key, or `[]` against `{}`, still shows up. Enumerate with `path(..)`, not
`paths(...)`: `paths` never returns the root, so a body that is a bare scalar or an empty
container (`"ok"` against `"error"`, `{}` against `[]`) would flatten to no lines on either
side and count as identical. The comparison key is the path as JSON (`tojson`), not a
dot-joined string, so the key `"a.b"` and the nested `a` then `b` stay distinct:

```bash
jq -c 'path(.. | select((type != "array" and type != "object") or length == 0)) as $p
  | {path: ($p | tojson),
     shape: ($p | map(if type == "number" then "[]" else tostring end) | join(".")),
     value: getpath($p)}' normalised.json
```

Compare the flattened old and new output per request on `path`. A path present on one side only is
`missing` or `added`; a path on both sides with values of different JSON types is
`type-changed`; same type, different value is `value-changed`. Status code and allow-listed
headers are compared as two more synthetic paths, `status` and `header.<name>` written with the
header name lowercased.

## The bucket signature

```text
signature = route_template | old_status -> new_status | path | kind
example:    GET /orders/{id} | 200 -> 200 | items.[].price.currency | missing
```

Route templates come from the router or the API schema, not from the raw path; `/orders/812`
and `/orders/9133` must land in one bucket. Where no template is available, replace path
segments that are all digits or match the id format with `{id}`.

Record per bucket: distinct requests affected, raw diff count, share of that route's replayed
requests, first and last capture timestamp, and two or three example request ids. Keep the
examples' full normalised old and new responses next to the report; the person closing the
bucket reads those, not the signature.

## Ranking and reading buckets

Rank by distinct requests affected, weighted by how central the route is, so a bucket
touching 0.2% of a checkout route can outrank one touching 40% of an internal health detail
endpoint.

Read buckets that share a request together. One root cause (a missing join, a changed default
locale) often surfaces as several paths on the same requests; fixing it closes all of them, and
treating them as separate findings wastes the review.

A bucket whose share of its route is near 100% is usually a systematic change: a renamed field,
a default that moved, a serialiser setting. A bucket at a small, stable share usually tracks a
data shape: null fields, empty collections, a legacy record type, an unusual tenant
configuration. Pull the examples' underlying records before guessing.

## Classification and sign-off

| State | Who can close it | What must exist |
| --- | --- | --- |
| Bug in new | Service owner | The fix, and the bucket absent on re-replay of the same capture |
| Bug in old, fixed | Service owner plus an owner of each affected consumer | Written approval, list of consumers checked |
| Bug in old, preserved | Service owner | Decision to reproduce the defect, ticket to remove it later |
| Intentional change | The approver named in the step 1 change list | Entry on that list, or a new dated sign-off |
| Noise | Whoever owns the normaliser file | Old-against-old evidence, rule added with that evidence cited |

Re-replay the same capture after each round of fixes. A bucket is closed only when the replay
that should no longer produce it does not, and the next fresh capture is replayed as well,
because a fix can open a bucket elsewhere.
