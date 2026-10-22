# Event schema

## Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Unique per entry; a time-ordered identifier helps range queries |
| `occurred_at` | timestamp | yes | Server time, UTC, from a synchronised clock |
| `action` | string | yes | Stable verb from the catalogue, `noun.verb` (`role.grant`, `export.create`, `session.revoke`) |
| `outcome` | enum | yes | `allowed`, `denied`, `failed` |
| `reason` | string | when denied or failed | Machine reason code (`policy.not_member`, `mfa.required`) |
| `policy` | string | when an authorisation decision | The rule or policy id that decided, and its version |
| `actor.id` | string | yes | Stable pseudonymous user or service id, never an email |
| `actor.type` | enum | yes | `user`, `admin`, `support`, `service`, `job` |
| `actor.on_behalf_of` | string | when impersonating or delegating | The subject the actor is acting as; `actor.id` stays the real actor |
| `actor.session_id` | string | for interactive actors | Lets an investigator group one session's actions; store an id, never the session token |
| `actor.auth_method` | string | for sign-in and sensitive actions | `sso`, `password+totp`, `api_key:<key id>`, `workload_identity` |
| `target.type` | string | yes | Resource type |
| `target.id` | string | yes | Resource id; indexed |
| `tenant_id` | string | in multi-tenant systems | Indexed; scopes customer-facing views |
| `source.ip` | string | for network-originated actions | |
| `source.user_agent` | string | for interactive actors | Truncate to a fixed length |
| `request_id` | string | yes | Joins the entry to operational traces without copying their content |
| `changes` | array | for updates | Field names changed; values only for fields classed safe to keep |
| `prev_hash`, `hash` | string | if hash-chained | See the tamper-evidence reference |

Index at least `target.id`, `actor.id`, `tenant_id`, `action` and `occurred_at`. Those are the query keys the investigation questions name; an unindexed key turns a two-minute question into a day's export.

## Example

```json
{
  "id": "01J9Z3K7Q4W8M2T6R0C5N1B7XD",
  "occurred_at": "2026-10-14T09:31:07.412Z",
  "action": "user.update",
  "outcome": "allowed",
  "policy": "support-impersonation@v3",
  "actor": {
    "id": "usr_7f3a91",
    "type": "support",
    "on_behalf_of": "usr_c02e44",
    "session_id": "ses_51d0aa",
    "auth_method": "sso"
  },
  "target": { "type": "user", "id": "usr_c02e44" },
  "tenant_id": "ten_0193",
  "source": { "ip": "203.0.113.24", "user_agent": "Mozilla/5.0 (truncated)" },
  "request_id": "req_8c41f7e2",
  "changes": [
    { "field": "email", "changed": true },
    { "field": "plan", "before": "starter", "after": "team" }
  ]
}
```

The email change records that it happened, not the addresses. The plan change keeps its values because a plan name is not personal data and the investigation question ("who upgraded this account") needs them.

## Action naming

- `noun.verb`, lower case, from a fixed catalogue kept in code; a new action is a reviewed change to the catalogue.
- Past-tense meaning, present-tense form: `role.grant` records that a grant was attempted, and `outcome` says whether it happened.
- One action per user intent. A bulk operation records one entry for the request with a count and a reference to the affected set, plus per-record entries only where a question needs them.

## Content rules

Never write into an entry:

- Passwords, password hashes, one-time codes, recovery codes.
- Access tokens, refresh tokens, session cookies, API keys, signing keys or private keys. An API key is referenced by its key id.
- Full payment card numbers or security codes.
- Request or response bodies copied wholesale.

Minimise:

- People appear by pseudonymous id. Names and emails are resolved at read time from the identity system, for readers allowed to see them.
- Changed fields holding personal or sensitive data record the field name and `changed: true`.
- Free-text fields entered by users (comments, notes) are not copied into entries.

Enforce the rules in the emitting library, not in reviewers' memory: an allowlist of fields per action that may carry values, and a test that fails when an action emits a field outside it.
