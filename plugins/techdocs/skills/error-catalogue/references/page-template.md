# Error page template

Read this when writing or reviewing the page for an error code. The reader arrives holding
the error, usually from a link in the message, and wants to know whether this is their
case and what to do. The page is ordered for that reader, not for the team that owns the
code.

## Contents

- [Template](#template)
- [Worked example](#worked-example)
- [Writing the confirm step](#writing-the-confirm-step)
- [Answering retryable](#answering-retryable)
- [Retired codes](#retired-codes)
- [Review checklist](#review-checklist)

## Template

```markdown
# <CODE>: <summary from the registry>

**Retryable:** <Yes | No> · **Since:** <version> · **Owner:** <team>

## What happened
<The condition that produces this code, in the reader's terms. One short paragraph.>

## How to confirm this is your case
<What the reader can check, with the exact place to look, and how to tell this code
apart from the lookalikes listed below.>

## How to fix it
1. <What the caller can do, in order.>
2. <...>

If that does not resolve it: <what an operator or support needs, and which identifiers
to send them, such as the request ID.>

## Related codes
- <CODE>: <one line on how it differs>
```

Keep the retryable answer in the header line. Client authors scan for it, and it is the
fact most often wrongly assumed.

## Worked example

```markdown
# BIL-1042: The card issuer declined the payment

**Retryable:** No · **Since:** 4.2.0 · **Owner:** billing-team

## What happened
The customer's bank refused the charge. The request reached the payment processor and was
valid; the decision was the issuer's.

## How to confirm this is your case
The error response carries `"code": "BIL-1042"` and a `decline_reason` field. If the
response instead carries BIL-1050, the processor was unreachable and the card was never
checked.

## How to fix it
1. Show the customer that their bank declined the payment and ask them to use another
   card or contact their bank. Do not retry the same card automatically.
2. If `decline_reason` is `insufficient_funds`, a retry can succeed later, once the
   customer confirms the funds are available.

If many cards are declined at once, contact support with the request IDs; a pattern can
indicate a processor-side problem rather than individual issuers.

## Related codes
- BIL-1050: the processor did not answer; retryable with backoff.
- BIL-1007: retired in 4.2.0; older releases reported all declines under this code.
```

## Writing the confirm step

The confirm step is what separates a catalogue from a list. Without it, a reader with a
lookalike error follows the wrong fix with full confidence.

- Name a concrete place to look: a response field, a log line with its key, a command and
  its output. "Check your configuration" is not a confirm step.
- Name the lookalikes and the observation that tells them apart. Two codes that share a
  symptom are the ones readers confuse.
- Ask for the identifier that support will need, such as a request or trace ID, here
  rather than at the end, so the reader collects it while they have it.

## Answering retryable

| Answer | Means | Example |
| --- | --- | --- |
| Yes | The same request can succeed later; back off before retrying | Upstream timeout, rate limit, temporary unavailability |
| No | The same request will fail again until something changes | Validation failure, permission denied, resource not found |

For a no, say in the fix what must change for a retry to succeed: the input, a permission,
a later point in time the reader controls. For a yes, say whether the response tells the
client how long to wait, such as a `Retry-After` header, and what to do when retries run
out. SDK authors implement exactly what this line says, so a wrong answer becomes
behaviour across every client.

## Retired codes

A retired code keeps its page, because old releases still emit it and old messages still
link to it. Replace the body with:

- the release it was retired in;
- the code or codes that replaced it, and how to tell which applies;
- what to do on a release that still emits it.

Never delete the page and never redirect it to the replacement silently: a reader on an
old release needs to see that the code they hold is real and what it meant.

## Review checklist

- [ ] Title is the code and the registry summary, unchanged
- [ ] Retryable answer matches the registry and the client behaviour
- [ ] Confirm step names a concrete place to look and the lookalike codes
- [ ] Fix steps are in order, one action each, caller before operator
- [ ] Every command, field name and header on the page exists in the current release
- [ ] The runtime message or response for this code links here
