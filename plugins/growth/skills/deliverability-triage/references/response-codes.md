# Reading bounce and deferral responses

Read this at step 3 of the triage, once the platform's SMTP responses are exported.

## Contents

- Grouping table
- What to do with each group

## Grouping table

Group by the three-part enhanced status code (class.subject.detail) and the provider, then count per day.

| Group | Typical codes | Reading |
| --- | --- | --- |
| Throttling | 4.x.x with rate or volume wording, such as the basic reply code 421 | Receiver slowing you; ramp too fast or standing is falling |
| Reputation or policy block | 5.7.x with text naming reputation, policy or a blocklist | Sender or IP standing |
| Authentication failure | 5.7.x naming SPF, DKIM or DMARC | Records or alignment broken |
| Unknown user | 5.1.1 | Address does not exist; list quality |
| Mailbox full or disabled | 4.2.2, 5.2.1 | Dormant addresses; sunset candidates |
| Content rejection | 5.7.x or 5.6.x naming content or URLs | Message or link domain flagged |

The exact text varies by receiver, so read the human-readable part of the response and quote it; the code alone is ambiguous.

## What to do with each group

- Throttling: slow the send rate, spread over more hours, prefer the engaged segment, and check complaints.
- Reputation or policy: stop sending to that provider from that IP or domain, read the receiver's postmaster page named in the response, and find the segment that drove complaints.
- Authentication failure: hand to `email-authentication-rollout` with the failing stream.
- Unknown user: suppress permanently; trace which source produced the addresses.
- Mailbox full or disabled: suppress after repeated soft bounces, per the sunset rule.
- Content rejection: diff the last good and first bad message for new link domains, shorteners and attachments.

A group that is a small share of a provider's volume but growing is worth more attention than a large flat one.
