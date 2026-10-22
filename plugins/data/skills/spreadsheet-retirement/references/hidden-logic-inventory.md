# Hidden logic inventory

## Contents

- Where logic hides
- Finding it in Excel
- Finding it in Google Sheets
- Watching a cycle
- The inventory template

## Where logic hides

| Kind | Why it matters | Typical symptom in the parallel run |
| --- | --- | --- |
| Value typed over a formula | The formula's result was replaced once and never restored | One line differs by a fixed amount every cycle |
| Constants in cells | Rates, headcounts, targets updated by hand at unknown times | Differences that change at period boundaries |
| External links to other workbooks | Logic and data live in a file nobody named | Values that match only when the other file is open |
| Pivot tables | Filters, hidden items and a cache that may not be refreshed | Missing categories; totals that match last month's data |
| Macros (VBA) or Apps Script | Steps run on a button, often deleting or reshaping rows | Rows present in the pipeline and absent in the sheet |
| Power Query steps | Filters, merges and type changes applied on refresh | Joins and exclusions nobody mentioned |
| Hidden rows, columns and sheets | Excluded data, helper calculations, old overrides | Unexplained exclusions |
| Named ranges | Formulas refer to a range whose extent was set by hand | New rows silently outside the range |
| Manual calculation mode | Displayed values are stale | The sheet does not match its own inputs |
| Display precision | A cell shows two decimals and stores more, or "Set precision as displayed" truncated stored values | Differences of a cent or less, summing to more |
| Iterative calculation | Circular references resolved by iteration | Results that depend on the iteration settings |
| Volatile or online functions | `TODAY()`, `NOW()`, and in Google Sheets `GOOGLEFINANCE`, `IMPORTRANGE`, `IMPORTDATA` | Results that change depending on when the sheet was opened |
| Manual steps outside the file | Rows deleted before pasting, filters applied by habit, adjustments after a call | Differences nobody can find in the file |

## Finding it in Excel

Work on a copy, with macros left disabled. You can read VBA source in the editor without enabling macros, or extract it without opening Office using a static tool such as `olevba` from oletools.

- **Formulas and constants:** Formulas > Show Formulas (Ctrl+`) to see every formula. Home > Find & Select > Go To Special > Constants selects every typed value; inside a column of formulas, a selected constant is an override.
- **Precedents:** Formulas > Trace Precedents and Trace Dependents from each consumer-facing figure, sheet by sheet. The Inquire add-in's workbook and cell relationship views help where your Office edition includes it.
- **External links:** Data > Edit Links, or the Workbook Links pane in current Microsoft 365 versions. Do not update links while inventorying; record the target paths.
- **Names:** Formulas > Name Manager. Record each name's range and whether it is fixed or dynamic.
- **Queries:** Data > Queries & Connections. Open each query in the Power Query editor and record every applied step, including filters and removed columns.
- **Pivots:** for each pivot table, record the source range, the filters, hidden items, and when it was last refreshed.
- **Hidden content:** unhide all sheets, rows and columns in the copy. Sheets set to very hidden appear only in the VBA editor's project view and properties.
- **Macros:** Alt+F11 opens the editor. Read every module and record what each procedure does to the data, especially deletes, sorts, copies between sheets and hard-coded ranges.
- **Settings:** Formulas > Calculation Options (manual or automatic); File > Options > Formulas for iterative calculation; File > Options > Advanced for "Set precision as displayed".

## Finding it in Google Sheets

- **Formulas:** View > Show > Formulas (Ctrl+`).
- **Scripts:** Extensions > Apps Script. Read every function, including triggers that run on open, on edit or on a timer.
- **History:** File > Version history shows who changed which cells and when; use it to find overrides and to recover past inputs for the oracle.
- **Imports and online data:** search formulas for `IMPORTRANGE`, `IMPORTDATA`, `IMPORTXML`, `GOOGLEFINANCE` and `QUERY`; each is a dependency or a hidden filter.
- **Names and protection:** Data > Named ranges and Data > Protect sheets and ranges. A protected range often marks the inputs someone considered important.
- **Filter views:** Data > Filter views; a saved view can be what the owner actually reads.

## Watching a cycle

Sit with the owner while they produce one real cycle from scratch, and write down every action in order without interrupting. Afterwards, ask about each one: why it is done, since when, who decided, and what happens if it is skipped. Common findings: test or internal accounts removed by hand, one customer's figures adjusted after a phone call, a rate copied from an email, a late file waited for, a total checked against a figure in another system before sending. Each becomes an inventory row.

## The inventory template

| # | Location (sheet, cell or step) | Kind | What it does | Since when, who decided | Fate | Owner of the rule |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Summary!F14` | Value over formula | Fixes March commission for one rep | Finance lead, March | Adjustment table row with reason and period | Finance lead |
| 2 | Manual step before paste | Exclusion | Removes accounts with "TEST" in the name | Long-standing | Exclusion table | Sales operations |
| 3 | `Rates!B2` | Constant | EUR to GBP rate, typed monthly | Finance | Rate table sourced from the treasury feed at month-end close | Treasury |
| 4 | Macro `CleanUp` | Macro | Deletes rows with zero amount | Unknown | Dropped with owner's written agreement; zero rows retained and filtered in the report | Finance lead |

The fates are: a rule in the pipeline, a row in an owned table, or dropped with written agreement. Nothing stays as "we will keep doing that by hand" unless it is listed as a manual step in the runbook with an owner, because an unlisted manual step is how the next spreadsheet starts.
