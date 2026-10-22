# Rule record and review checklist

Read this when creating a rule's record or running the periodic review.

## Contents

- Rule record
- Backtest record
- Review-period checklist
- Coverage inventory

## Rule record

Keep it in the repository beside the rule file.

| Field | Entry |
| --- | --- |
| Rule ID and path | |
| Hypothesis | one sentence on attacker behaviour |
| Log source and field | with the date the field was verified populated and the population covered |
| Known blind spots | accounts, hosts or regions with no data |
| Technique tags | ATT&CK IDs, as an inventory label only |
| Emulation | exact steps or sample file, and the date of the last passing run |
| Owner | person or team |
| Severity and route | page or ticket, with the reason |
| Triage note | three first queries; expected benign causes |
| Exclusions | each with reason, owner and expiry date |
| Created, last reviewed | dates |

## Backtest record

Window start and end, event volume scanned, alert count, false positives and their causes, true positives if any, and the decision (ship, tune, split, reject).

## Review-period checklist

For each rule:

- Did it alert in the period, and what was the disposition of each alert?
- Did the emulation test pass on its last scheduled run?
- Have exclusions expired, and are they still needed?
- Is the field still populated, or did the source change its schema?
- Precision this period, and median time from alert to triage decision.
- Retire if no true positive and no passing test across two review periods; fold into a higher-fidelity rule if another already catches the same behaviour with less noise.

## Coverage inventory

List ATT&CK techniques in three columns: tested rule, untested rule, no rule. Review the third column against the threat model for the environment and decide which gaps matter. Report counts for information, not as a goal.
