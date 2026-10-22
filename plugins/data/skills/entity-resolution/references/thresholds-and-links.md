# Thresholds and links

## Contents

- Labelling protocol
- Weighted precision and recall
- Choosing the two thresholds
- Link, override and golden record tables
- Survivorship rules
- Unmerging
- Stable entity ids

## Labelling protocol

1. Split all scored candidate pairs into score bands, for example ten bands of equal width or deciles of score. Record the population count `N_b` of each band.
2. Sample about 20 pairs per band for roughly 200 in total. Oversample the bands where you expect the threshold to fall; never sample in proportion to population, or almost every labelled pair is an obvious non-match.
3. Show the labeller the raw and normalised values of both records side by side, plus the per-field comparison vector. Hide the overall score so it does not anchor the judgement.
4. Labels are `match`, `non-match` or `cannot tell`. Write the rule for the entity definition at the top of the sheet so labellers apply the same meaning of "same".
5. Have a second person label a subset of at least 50 pairs. Report the agreement rate. Settle each disagreement in writing and add the settled rule to the sheet's instructions.
6. Keep the labelled set versioned. Pairs labelled by reviewers later are added to it, which is how the sample grows with use.

Labelling sheets contain personal data. Show only the fields the decision needs, keep the sheet where the source data's access controls apply, and delete working copies when the round ends; `data-privacy` covers the obligations.

## Weighted precision and recall

Because the sample is stratified, the raw share of matches among labelled pairs is not the population figure. Weight each band by its population.

For band `b`: `n_b` labelled pairs (excluding `cannot tell`), `m_b` labelled matches, `N_b` candidate pairs in the population. Estimated true matches in the band: `M_b = N_b * m_b / n_b`.

At threshold `t`, over bands whose lower edge is at or above `t`:

- Precision(t) = sum of `M_b` / sum of `N_b`
- Recall among candidates(t) = sum of `M_b` above `t` / sum of `M_b` over all bands
- Overall recall(t) = recall among candidates(t) x pair completeness from blocking

Report the threshold table:

| Threshold | Pairs above | Est. precision | Est. recall (overall) | Labelled pairs above | Labelled false merges above |
| --- | --- | --- | --- | --- | --- |
| 0.95 | | | | | |
| 0.90 | | | | | |
| 0.85 | | | | | |
| 0.80 | | | | | |

The last column matters as much as the estimate: precision estimated from 12 labelled pairs with no errors is not evidence of 100%. If the band you would auto-match has few labelled pairs, label more there before deciding.

## Choosing the two thresholds

- **Upper (auto-match):** the lowest threshold whose estimated precision meets the target from the error-cost step, with enough labelled pairs above it to make the estimate meaningful.
- **Lower (non-match):** the threshold below which labelled matches are rare enough that the recall lost is acceptable to the consumer.
- **Review band:** everything between. Multiply its pair count by the expected weekly arrival rate to get review volume, and check it against the hours someone has actually agreed to spend. If it does not fit, raise the lower threshold and accept the lost recall explicitly, rather than lowering the upper one and accepting false merges silently.

## Link, override and golden record tables

```sql
CREATE TABLE entity_link (
  source_system   TEXT        NOT NULL,
  source_id       TEXT        NOT NULL,
  entity_id       TEXT        NOT NULL,
  match_method    TEXT        NOT NULL,  -- rule code, 'score', 'review', 'singleton'
  match_score     NUMERIC,
  matcher_version TEXT        NOT NULL,
  linked_at       TIMESTAMP   NOT NULL,
  valid_to        TIMESTAMP,             -- set when the link is withdrawn
  PRIMARY KEY (source_system, source_id, linked_at)
);

CREATE TABLE entity_override (
  left_system     TEXT NOT NULL,
  left_id         TEXT NOT NULL,
  right_system    TEXT NOT NULL,
  right_id        TEXT NOT NULL,
  decision        TEXT NOT NULL,          -- 'match' or 'non-match'
  decided_by      TEXT NOT NULL,
  decided_at      TIMESTAMP NOT NULL,
  reason          TEXT
);
```

Adjust types to the warehouse. The current link for a record is the row with `valid_to IS NULL`, and there must be exactly one. The primary key cannot enforce that, because a rerun's new row has a different `linked_at`: close the old link and insert the new one in one transaction, and run this check after every run, expecting no rows:

```sql
SELECT source_system, source_id, COUNT(*) AS current_links
FROM entity_link
WHERE valid_to IS NULL
GROUP BY source_system, source_id
HAVING COUNT(*) > 1;
```

On PostgreSQL a partial unique index (`CREATE UNIQUE INDEX ... ON entity_link (source_system, source_id) WHERE valid_to IS NULL`) enforces the same rule; warehouses that do not enforce constraints need the check. Every run applies `entity_override` before scoring: a `non-match` override acts as a hard non-match rule, a `match` override as a deterministic rule.

The golden record is a derived table or view built from current links and the source rows. It is never the place a correction is made; corrections go into links, overrides or the source system.

## Survivorship rules

Write one rule per golden field and keep the source and timestamp of the value chosen.

| Field | Typical rule |
| --- | --- |
| Legal name | Registry or billing source over CRM |
| Email | Most recently verified; otherwise most recent |
| Postal address | Billing source for invoices, most recent for marketing; keep both if both are used |
| Phone | Most recent non-junk |
| Tax number | Only from a source that validates it; conflict means the cluster is wrong, not that one value wins |

A conflict on a field that should be unique per entity (tax number, date of birth) is a signal to send the cluster to review, not a survivorship decision.

## Unmerging

1. Identify the wrong links: the records that do not belong to the entity.
2. Set `valid_to` on those link rows and insert new links to a new or correct entity id, with `match_method = 'review'`.
3. Insert a `non-match` override between the separated records so the next run does not rejoin them.
4. Rebuild the golden records for every entity id touched.
5. Tell downstream consumers which entity ids changed, with the old and new ids, so cached joins and exports can be corrected. Writing those corrections into production tables is a backfill; run it with `safe-backfill`.

## Stable entity ids

A rerun recomputes clusters from scratch, so ids must be reassigned deliberately:

- For each new cluster, find the previous entity id held by the largest share of its members. Only a majority share makes the cluster a candidate for that id.
- Each previous id goes to at most one new cluster. When a split leaves several candidates for the same id (two successors can each be made entirely of members that carried it, and so both show a 100% share), pick one winner by the number of overlapping members, then by a deterministic tie-break such as the lowest member record key.
- Every other new cluster mints a new id, and the old-to-new mapping is recorded for consumers. Never let two clusters keep the same id: the link and golden-record tables would join them back into one entity.

Report the share of entity ids that changed on each run. A large change on a run with no matcher change means the source data shifted or a junk value slipped through.
