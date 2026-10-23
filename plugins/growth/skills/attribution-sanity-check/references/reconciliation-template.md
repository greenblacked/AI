# Reconciliation template

Read this at step 1 when building the first table.

## Contents

- The table
- Matching the definitions
- Reading the result

## The table

| Source | Conversion definition | Window and view-through | Claimed count | Notes |
| --- | --- | --- | --- | --- |
| Backend | paid order, deduplicated by order id | n/a | the count of record | exclude refunds and test orders as the business does |
| Search ads platform | purchase event | click window, view setting | | |
| Social ads platform | purchase event | click and view windows | | |
| Email platform | revenue attributed | click window | | |
| Web analytics | purchase event | session or model based | | |
| Self-reported field | answer category | n/a | | share of respondents |

Total the claimed counts for the paid and owned platforms and divide by the backend conversions in the claiming channels' scope: leave out orders whose analytics or self-reported source is organic, direct, referral or word of mouth, and record that unclaimed share next to the factor.

## Matching the definitions

- Use one period in one time zone. Platform reports often default to different ones.
- Use the same conversion: a lead is not a purchase. If platforms count a micro-event, say so.
- Net out refunds and test orders on the backend side before comparing.
- Note conversion-delay: recent days are incomplete for platforms with long windows. Reconcile a period that closed at least a window ago.

## Reading the result

These bands apply to the scoped factor. Under 1.0 means tracking loss: consent, blockers or missing tags. Around 1.0 to 1.3 is common for a single dominant channel. Above 1.5 means heavy overlap between platforms or duplicated events; the larger the factor, the less any single platform's cost per acquisition can be believed. Record the factor with the date so the next check has a baseline.
