---
name: campaign-preflight
description: "Run the pre-send gate on a bulk email so the wrong segment, broken link or missing unsubscribe never goes out. In order: audience count against the last send of the same segment (off by more than 10% blocks until explained), suppression lists applied, seed send to real Gmail, Outlook and Apple Mail inboxes in light and dark mode, every tagged link clicked, plain-text part, List-Unsubscribe plus one-click List-Unsubscribe-Post (RFC 8058), monitored From and reply-to, send time and timezone. Large sends go in waves with a named kill-switch holder for the first 20 minutes. Use for \"ready to send the newsletter\", \"final check before we blast this\" or \"checklist before the campaign goes live\". Not for placement problems after sending (deliverability-triage), URL tagging (campaign-tagging-standard), changelogs (release-notes) or automated flows (lifecycle-sequence-design)."
allowed-tools: Read, Glob, Grep
---

# Campaign Preflight

Done means a named person has passed every gate below in order, the result is recorded in the campaign ticket, and someone holds the kill switch while the first wave goes out.

The usual failure is a gate checked by looking at the draft. The error is almost never in the copy: it is the segment that silently doubled, the link that still points at staging, the suppression list that was not attached to this send. An email cannot be recalled, so every check has to happen before the button.

## Scope

Use for: a one-off or recurring bulk send, such as a newsletter, announcement or promotion, about to go out.

Do not use for: mail already sent that is landing badly (`deliverability-triage`), how links are tagged (`campaign-tagging-standard`), product changelogs (`release-notes`) or automated multi-step flows (`lifecycle-sequence-design`).

## Hard gates

1. The gates run in the order below. The audience check comes first because everything after it is wasted on the wrong list.
2. A failed gate stops the send. It is cleared by fixing the cause or by a named person writing down why it is acceptable.
3. The seed send uses the final content and final tagged URLs, not an earlier draft.

## Workflow

### 1. Audience count against the last comparable send

Find the recipient count for the last send to the same segment and compare. A difference of more than 10% blocks the send until someone explains it: a list import, a changed filter, a deleted suppression, a segment that now includes a new field. An unexplained drop is as suspect as a rise. Record both numbers and the explanation. For a segment's first send there is no previous count: rebuild the count independently (for example, run the segment's query again in the CRM) and compare the two, and require a named waiver to proceed if they differ by more than 10%.

### 2. Suppression and unsubscribe

Confirm the global unsubscribe list, hard bounces, complaints and any customer-specific suppressions (open support escalations, legal holds, contacts in a live sales conversation) are applied to this send. Spot-check by searching for three known suppressed addresses in the final audience; none should appear.

### 3. Seed send to real inboxes

Send the final message to seed addresses at, at minimum, Gmail, Outlook and Apple Mail, and look at each in light and dark mode on desktop and phone. Check that images have alt text and the layout holds with images blocked, that dark mode does not make logos or text unreadable, and that the preheader reads well. A rendering tool helps, but one real inbox per provider is the check that cannot be skipped. See `references/preflight-checklist.md` for the table to fill in.

### 4. Click every link

From the seed message, click each link once and confirm the destination, the tags on the URL (parameters as set by the standard), and that the landing page works on a phone. Include the logo, footer, preference centre and unsubscribe links. A personalised link should resolve for the seed contact.

### 5. Plain-text part

Confirm a plain-text alternative exists and is readable, not a pasted "view in browser" line. Messages without one score worse with some filters and are unreadable in some clients.

### 6. Unsubscribe headers

Confirm the message carries `List-Unsubscribe` and, for one-click, `List-Unsubscribe-Post: List-Unsubscribe=One-Click` as defined in RFC 8058, and that the one-click request actually unsubscribes the seed contact. The one-click header is what Google and Yahoo require of bulk senders. Open the raw message in the seed inbox (show original in Gmail) to read the headers and check the visible footer unsubscribe link works too. Test the unsubscribe on a seed address and confirm it lands on the suppression list before the real send.

### 7. Sender identity

Confirm the From address is on the authenticated sending domain and that From and reply-to are mailboxes someone reads on send day. Replies to an unmonitored address are lost customer questions and unsubscribe requests in disguise.

### 8. Send time and timezone

Confirm the send time, the timezone it is expressed in, and whether the platform sends in the sender's or the recipient's zone. Check the date against holidays and other sends to the same people that day.

### 9. Send in waves with a kill switch

For a large list, send a first wave to a small slice (a few percent) and watch for the first 20 minutes: bounces, complaint signals, unsubscribe rate, link errors reported by replies, and any rendering complaint. Name a person who holds the stop control for that window and say how to reach them. Release the remaining waves only when the first looks normal against the previous send.

### 10. Record

Write in the campaign ticket: audience counts and explanation, who ran each gate, seed results, link check, header check, send time, wave plan, kill-switch holder and the outcome of the first wave.

## Hand back

The completed checklist with pass or fail per gate, any waived gate with the name and reason, the wave plan and kill-switch holder, and the ticket link. If a gate could not be run (no Outlook seed, say), mark it unverified rather than passed.

## Anti-patterns

**Reviewing the draft instead of the seed.** What the platform sends differs from what the editor shows.

**Sending to a fresh segment with no comparison.** A count that has never been compared with anything cannot be wrong, which is why it is wrong.

**Everyone owns the stop button.** Then nobody does; name one person.

**Testing unsubscribe by reading the footer.** The link must be clicked and the suppression confirmed.
