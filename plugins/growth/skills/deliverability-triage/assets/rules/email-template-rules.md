---
paths:
  - "**/emails/**/*.html"
  - "**/emails/**/*.mjml"
  - "**/email-templates/**"
  - "**/templates/email/**"
---

# Working on email templates

- Keep an unsubscribe reference and a plain-text alternative in every marketing template,
  because bulk-sender rules and complaint rates both depend on them.
- Tag external links with the parameters the campaign tagging standard sets, and leave
  internal links untagged so they do not overwrite the real source in analytics.
- Never paste a recipient list or an address into a template; lists belong in the sending
  platform.
- Do not send a template until `campaign-preflight` has passed for it.
