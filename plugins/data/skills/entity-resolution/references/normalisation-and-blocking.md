# Normalisation and blocking

## Contents

- Junk values
- Per-field normalisation
- Blocking keys
- Block size
- Pair completeness

The SQL below is ANSI-flavoured; adjust function names (`LOWER`, `REGEXP_REPLACE`, `SOUNDEX`) to your warehouse, and check each exists there before relying on it.

## Junk values

Run this per identifying field and per source before normalising. Any value carried by far more records than a real identifier could be is a placeholder, a shared mailbox or a default.

```sql
SELECT email, COUNT(*) AS records
FROM crm_contacts
WHERE email IS NOT NULL
GROUP BY email
HAVING COUNT(*) > 5
ORDER BY records DESC
LIMIT 100;
```

Typical findings: `test@`, `noreply@`, `info@`, `accounts@` on a shared domain; phone numbers of all one digit; the company's own head-office address entered for every walk-in customer; names such as `Unknown`, `Cash Sale`, `.`. Keep a reviewed list per field, set those values to null in the normalised column, and keep the raw value.

## Per-field normalisation

| Field | Rule | Why |
| --- | --- | --- |
| Personal name | Unicode NFKC, case fold, strip punctuation, then collapse whitespace; split into given and family where the source has them | Punctuation removed after collapsing leaves double spaces that break equality |
| Company name | As above, then move legal-form tokens (Ltd, Limited, LLC, Inc, GmbH, SA, BV, plc) into a separate `legal_form` field; keep "The" handling consistent | "Acme Ltd" and "Acme Limited" should block together, but the legal form is still evidence |
| Email | Trim, lower-case; apply provider rules such as ignoring dots or `+tag` only for providers that document that behaviour | Stripping dots from every domain merges distinct mailboxes on providers that treat them as significant |
| Phone | Parse to E.164 with a library such as libphonenumber, using the record's country as the default region | `020 7946 0000`, `+44 20 7946 0000` and `0044...` are one number |
| Address | Parse into components (house number, street, locality, postcode, country) with a parser such as libpostal or a national postal reference file; upper-case postcode without spaces for keys | Free-text address equality almost never holds across systems |
| Date of birth, incorporation date | ISO 8601; flag `1900-01-01` and similar defaults as junk | Default dates create false hard-match evidence |
| Tax or registration number | Strip spaces and separators, upper-case, validate the check digit where the scheme has one | An invalid number is a typing error, not an identifier |
| Web domain | Lower-case host, drop `www.`, drop path; null free-mail domains | Every Gmail user shares `gmail.com` |

Write the rules as code with tests, one case per row above, and version them. The link table records which version matched each pair.

## Blocking keys

Use several passes and take the union of their candidate pairs. Each pass should be cheap to compute and should put true matches together even when other fields disagree.

| Pass | Key | Catches | Watch for |
| --- | --- | --- | --- |
| 1 | Normalised email | Same person, same mailbox | Shared mailboxes; junk list must be applied first |
| 2 | E.164 phone | Same person, typo in name | Switchboard numbers for companies |
| 3 | Postcode + first three letters of family name | Same person at same address, email changed | Large buildings, student halls |
| 4 | Web domain (companies) | Subsidiaries and trading names | Free-mail domains; resellers using a client's domain |
| 5 | Phonetic code of name + region | Spelling variants | Common surnames produce huge blocks |

## Block size

Pairs grow with the square of block size, so a single block of 50,000 records holds about 1.25 x 10^9 pairs.

```sql
SELECT block_key,
       COUNT(*) AS records,
       COUNT(*) * (COUNT(*) - 1) / 2 AS pairs
FROM candidate_keys
WHERE pass = 3
GROUP BY block_key
ORDER BY pairs DESC
LIMIT 50;
```

Set a cap on records per block from the scoring budget. Inspect every block over the cap: if its key is a junk value, add it to the junk list; if it is legitimate (a common surname in a large city), refine that pass with a second key component rather than dropping the block silently.

## Pair completeness

Pair completeness is the share of true matches that appear in the candidate set. Measure it against matches you know independently of the blocking keys: records sharing a verified tax number, or the pairs labelled "match" in the hand-labelled sample.

```sql
-- known_matches(left_id, right_id): matches established without using blocking keys
SELECT COUNT(*)                                  AS known,
       COUNT(c.left_id)                          AS in_candidates,
       1.0 * COUNT(c.left_id) / COUNT(*)         AS pair_completeness
FROM known_matches k
LEFT JOIN candidate_pairs c
  ON (c.left_id = k.left_id AND c.right_id = k.right_id)
  OR (c.left_id = k.right_id AND c.right_id = k.left_id);
```

Store candidate pairs with `left_id < right_id` and the join simplifies to one direction. A pair completeness below the recall you need means a missing blocking pass, not a scoring problem; look at the known matches that were not blocked together and ask which cheap key they did share.
