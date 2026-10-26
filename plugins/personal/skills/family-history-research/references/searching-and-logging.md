# Searching and logging

Read this at phase 4 when planning and again at phase 5 before the first search.

## Contents

- Plan from the end of the chain
- The coverage list
- The stop rule
- The research log
- Citations
- Negative results
- Browser mode
- No-browser mode
- The CAPTCHA and sign-in hand-off
- Pace

## Plan from the end of the chain

Start at the most recent event that is already well documented, and work back one link at a
time. Each link tells you the name, place and age to look for next, which a search from the
distant end cannot. For each gap write down, before searching:

- the record type that would have been made (a baptism entry, a marriage entry, a household
  list, a military enlistment record, a probate file);
- the kind of institution that would hold it now (a regional archive, a church office, a
  national service, a local museum, a family-history society);
- the search keys: names with variants, an age or year range, the place and its neighbours,
  relatives and witnesses;
- what result would support the hypothesis and what would undermine it.

The last line is the one that matters. If a missing entry would not change your mind, the
search is decoration.

## The coverage list

One row per record type and place that could plausibly hold the answer. Put the rows in
`assets/research-log.csv` with `row_type` set to `coverage`. Each row ends in exactly one of:

- **searched-found:** looked at, and a relevant entry exists.
- **searched-not-found:** looked at over a stated scope, and nothing relevant.
- **inaccessible:** could not be reached, with the reason (not digitised, restricted, closed
  route after a challenge, user chose not to pay).
- **out-of-scope:** (out of scope in prose) deliberately left out, with the reason (a minor, something the user asked
  not to be searched, a different question).

A row with no final state is an unfinished search. `scripts/audit_registers.py` rejects it.

## The stop rule

A search is reasonably exhaustive when every coverage item that could plausibly hold the
answer is closed, and the conclusion would survive the next likely record. Test the second
part by asking what record you would find next and what it would have to say to overturn the
conclusion. If you can name one that you have not looked for, the search is not done. If the
only remaining items are inaccessible, say so, and cap the proof level accordingly.

Stopping because the first hit looks right is the usual failure, and it is invisible: the
unlooked-for record is never found.

## The research log

One row per search, in `assets/research-log.csv` with `row_type` set to `search`:

| Column | What goes in it |
| --- | --- |
| date | The day the search was run |
| repository_kind | The kind of holder (a regional archive, a church office), not a brand |
| terms | The exact terms typed, including each variant tried |
| scope_covered | The years and places actually covered, which may be less than the repository holds |
| result | What came back, including nothing |
| follow_up | What to do next, or none |

Log a search before reading the next. A log written afterwards from memory leaves out the
dead ends, and the dead ends are what show the search was thorough.

## Citations

Every item found needs a full citation in `assets/sources.csv`: what the item is, who created
it and when, where it is held, the collection or book and page or entry, how you obtained it
and on what date, and a stable locator (a persistent link where one exists, otherwise the
shelf mark, volume and folio). A citation that says "found online" is not a citation.

Write the statement the item makes in `assets/statements.csv` exactly as written, with the
date and place as written. The reading goes in the conclusion, not in the statement.

## Negative results

Record a negative result with the scope it covers: which register, which years, which
spellings. "No entry for the name or its three variants in the baptism register, 1850-1860"
is a result someone can extend. "Not found" is not.

A negative result is meaningful only when the record would have been made and survives for
that scope. A gap in a register, a lost volume or a parish that did not register at the time
makes the search uninformative, and the row says so.

## Browser mode

When a browser is available the user drives it for anything behind a sign-in, a challenge or
terms. Search one query at a time and read the result before the next. Save pages as the
user's own copies for their research, not in bulk.

## No-browser mode

When there is no browser, do not search and do not describe what a search "would find". Write
a query plan: for each coverage item, the kind of repository, the exact terms and variants to
type, the scope to select, and what each outcome would mean. Say in the first line that no
search was run. The plan is a set of instructions for the user, never a result.

## The CAPTCHA and sign-in hand-off

The user solves every CAPTCHA, signs in and accepts terms personally. This is not a courtesy:
terms are a contract only the user can enter, and a challenge exists to stop automation.

After a hand-off the user runs the rest of that site's searches, unless the site's terms
explicitly allow assisted browsing. A repeated challenge means the site has judged the
traffic automated; close the route as inaccessible and record why. Do not wait and retry in
a loop, do not change the way the requests look, and do not look for a way around a
paywall, geo-block or rate limit. Nothing here crawls, bulk-exports, reassembles image tiles
or runs scripts in the page to fetch images a site serves only for display.

## Pace

One search at a time, with a pause long enough that a person could have typed it. A fast pace
risks the user's account and the site's goodwill for every researcher after them.
