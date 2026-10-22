# Reading DMARC aggregate reports

Read this at step 3 of the rollout, when the first reports arrive.

## Contents

- What a report row contains
- Grouping table
- Classifying a row
- Forwarders and mailing lists

## What a report row contains

Each aggregate report is XML from one receiving organisation covering a time window. A row holds the source IP, the message count, the disposition the receiver applied, the SPF and DKIM results as evaluated for DMARC (aligned or not), and under the auth results the actual domains tested (the SPF envelope domain, the DKIM `d=` and selector). Use a processing service or a small script to turn the XML into a table; reading raw files does not scale beyond a day.

## Grouping table

Group rows by sending organisation, not by IP, because large platforms use many addresses.

| Column | Source |
| --- | --- |
| Organisation | reverse DNS of the IP, the DKIM `d=` domain, the SPF domain |
| Volume | sum of message counts over the window |
| DKIM aligned pass | `dkim` result in policy evaluated, with `d=` matching the From domain |
| SPF aligned pass | `spf` result in policy evaluated, envelope domain matching the From domain |
| Receivers seen | which reporters sent a row for it |

## Classifying a row

1. Aligned pass on DKIM or SPF: working. Note the platform and move on.
2. Known platform, failing: a fix is needed. Typical causes are no custom DKIM domain configured, a bounce domain left on the platform's default, or a signing selector never published.
3. Unknown IP, high volume, consistent: ask the teams. A forgotten script is common; abuse is possible. Do not guess.
4. Unknown IP, low volume, scattered across many receivers: likely spoofing, which enforcement is meant to block.
5. Passing at one receiver, failing at another for the same source: look for a forwarder or a rewriting gateway between them.

## Forwarders and mailing lists

Forwarding keeps the original envelope but changes the sending IP, so SPF fails; DKIM survives unless the forwarder edits the body or subject. Lists that rewrite subjects or add footers break DKIM too. Those rows are expected noise: do not try to fix them, and do not hold enforcement waiting for them to reach zero. Judge by whether your own streams are clean.
