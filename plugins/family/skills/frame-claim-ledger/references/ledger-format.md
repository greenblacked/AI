# The ledger format

## Contents

- The table
- Three kinds of claim
- Restating a claim so it can fail
- Weighing

## The table

One row per claim, kept with the frame until the decision is recorded.

```text
| # | Claim (restated)          | Kind      | Weight | Verdict      | Label     | Rests on it            |
| 1 | <subject, version, scope> | behaviour | high   | HOLDS        | primary   | the choice of queue    |
| 2 | <subject, date, scope>    | figure    | high   | UNVERIFIED   | consensus | the sizing in the note |
| 3 | <subject>                 | need      | low    | not assessed | -         | the second user story  |
```

Weight is how much of the hard-to-reverse decision falls if the claim is false: high, medium or low, with the sentence that shows it. Verdict and label stay empty until a finding returns. A row left at "not assessed" is copied into the decision record's Not assessed section as it stands.

## Three kinds of claim

- **Behaviour.** What a flag, an endpoint, a library or a platform does. The source is the implementation or the reference for the version in use, not a tutorial.
- **Figure.** A statistic, price, quota, latency or adoption number. The source is the report that first published it. A figure with no origin is a finding: unsourced.
- **Need.** That a user has the problem, how many, how often. The source is what users did or said, not what the requester believes they will do. When none was measured, the claim is unverified and the frame says so.

## Restating a claim so it can fail

"The API is rate limited" cannot fail. "The v2 search endpoint limits each API key to 60 requests a minute on the free plan, as of this month" can. Include the subject, the version or date, and the scope. A behaviour claim with no version is two claims; say which one is on the ledger.

A sentence that bundles two facts becomes two rows. A claim that is really a preference ("customers prefer fewer options") is restated as the observation it stands on, or dropped.

## Weighing

Ask of each row: if this were false, would the hard-to-reverse decision change, or only a detail beneath it? Rank on that, settle the top two, and write the rest down with their weight. A tie goes to the claim whose failure would be found latest, because a late discovery costs the most. If every row is low, the decision is probably reversible and the ledger can stay a list.
