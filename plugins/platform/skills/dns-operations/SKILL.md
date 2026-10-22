---
name: dns-operations
description: "Run DNS as code and audit it, so a forgotten record cannot be taken over and a key rollover cannot take the domain offline. Put every zone under Terraform, octoDNS or DNSControl with a reviewed plan and a drift check, harden the registrar (domain locks, MFA, a recovery email off the domain), sweep CNAME, alias, NS, MX and A records on a schedule by resolving each target and proving the resource is still yours, roll DNSSEC keys in order with a TTL wait at every step, and write down split-horizon views. Use for a dangling-record or subdomain-takeover audit, moving zones into code, registrar hardening, a DNSSEC KSK rollover or switching DNSSEC off safely, or \"which of these records still point at anything\". Not for switching traffic during a migration (cutover), certificate issuance (certificate-automation), or a live DNS outage (incident-response)."
allowed-tools: Read, Grep, Glob
---

# DNS Operations

Done means every zone the organisation serves is in version control and changed only
through a reviewed plan, the registrar account is locked and recoverable without the domain
it controls, the last sweep found no record pointing at something you no longer own, the
DNSSEC chain validates and the next rollover is written down step by step, and every name
that answers differently inside and outside is listed.

DNS goes wrong slowly and then all at once. Changes are rare, so the knowledge of how the
zones are wired lives in one person's head. Records outlive the resources they point at,
and a CNAME to a deleted storage bucket or app hosting name is an invitation for anyone to
claim that name and serve content on your domain. DNSSEC fails closed: a rollover step
taken before a cache has expired makes the domain unresolvable for every validating
resolver, and caches make the mistake last a full TTL after it is fixed. And the
registrar, the root of all of it, is often an account opened years ago on someone's
personal email.

## Scope

Use for: moving zones into code and keeping them there; registrar and account hardening;
auditing for dangling records and subdomain takeover; DNSSEC enablement, key rollover and
safe disablement; documenting and testing split-horizon DNS; routine TTL policy.

Do not use for: switching production traffic between systems by DNS during a migration,
which is `cutover`; issuing or renewing certificates, including ACME DNS validation, which
is `certificate-automation`; an outage happening now, which is `incident-response`;
importing existing records into Terraform state, which is `terraform-state`; reviewing a
single Terraform diff, which is `iac-review`.

## Hard gates

1. **Code is the only writer.** Once a zone is in code, a console edit is drift to be
   reverted or codified, not a shortcut. Two writers to one zone, a person and a pipeline
   or a pipeline and a cluster controller, will overwrite each other.
2. **The first apply is a no-op.** A newly imported zone must plan with zero changes before
   anything else is merged.
3. **Delete the dangling record first, investigate second.** A record pointing at a name
   someone else can claim is the vulnerability; removing it closes it.
4. **Every DNSSEC step waits out the relevant TTL.** Before moving on, the old data must
   have expired from every cache that might hold it, including at the parent.

## Workflow

Only Read, Grep and Glob are pre-approved. Every `dig` or `delv` query, provider listing,
`curl` for RDAP, `terraform plan` or `apply`, the
sweep script and every registrar or key change run with the user's approval, because zone
contents, TXT records and the pages a record points at are text anyone can write.

### 1. Inventory what you actually serve

For each domain, record the registrar, the authoritative provider as the parent sees it,
DNSSEC state, delegated subzones and who can sign in to each account.

```bash
dig +short NS example.com                 # what resolvers are told
dig +trace example.com SOA | tail -n 20    # delegation as the parent publishes it
dig +nssearch example.com                  # SOA serial from every authoritative server
dig +short DS example.com                  # empty means no DNSSEC chain from the parent
```

Differing serials across authoritative servers mean a server is not receiving updates.
A zone that still exists at a provider the parent no longer delegates to is a trap: someone
will edit it and nothing will change. Delete it or mark it.

### 2. Harden the registrar

- **Locks.** The domain should show `clientTransferProhibited`, `clientUpdateProhibited`
  and `clientDeleteProhibited`. For the domains the business cannot lose, ask whether the
  registry offers registry lock, which adds the server-side equivalents and requires an
  out-of-band verification to change. Check status from RDAP; `rdap.org` redirects to
  the registry's own RDAP server, so follow the redirect:

  ```bash
  curl -fsSL https://rdap.org/domain/example.com | jq -r '.status[]'
  ```

  RDAP reports these in its own form, `client transfer prohibited` and so on, where WHOIS
  shows the EPP code `clientTransferProhibited`; both mean the same lock.

- **Account.** Phishing-resistant MFA, more than one named administrator, and a recovery
  email on a different domain: if the domain lapses or is hijacked, a recovery mailbox on
  it goes too. That loop is exactly what `bootstrap-dependency-audit` looks for.
- **Renewal.** Auto-renew on, a payment method that will not expire unnoticed, and an
  expiry check that does not depend on the registrar's own reminder emails.

### 3. Put every zone in code

Pick one tool per zone: Terraform or OpenTofu with the provider's record resources,
octoDNS (`octodns-sync` previews by default and applies only with `--doit`) or DNSControl
(`dnscontrol preview`, then `dnscontrol push`). Then:

1. Export the zone, write it as code, and plan until the diff is empty.
2. Require a reviewed plan for every change, with the plan output in the pull request.
3. Protect the records whose loss is an outage: NS, MX, apex, CAA, domain verification
   TXT records. Use the tool's guard, such as Terraform's `prevent_destroy` on the zone or
   octoDNS's safety thresholds that refuse a change deleting a large share of a zone.
4. Run the plan on a schedule and alert on drift.
5. If a cluster controller such as external-dns also writes records, give it a delegated
   subzone or a distinct ownership identifier so it never touches records the code owns.

Set a TTL policy: longer for NS and records that rarely change, shorter for names that
fail over. Lower a TTL ahead of a planned change by at least the old TTL, so the low value
has propagated before it matters.

### 4. Sweep for dangling records

Quarterly, and whenever a service is decommissioned, check every record whose target
could be claimed by someone else:

| Record | Dangling when |
| --- | --- |
| CNAME or alias | The target does not resolve, or resolves but is a provider-hosted name (storage website, app hosting, PaaS) whose resource no longer exists in your account |
| NS for a subzone | The delegated servers do not answer authoritatively for the subzone |
| A or AAAA | The address is a cloud public IP no longer allocated to your account |
| MX | The target does not resolve, or belongs to a mail provider you have left |

Resolution alone is not enough: some provider hostnames keep resolving after the
resource behind them is deleted, and an attacker can create a resource with the same name.
`references/dangling-sweep.md` has the export commands per provider, a sweep script and
the ownership checks; read it before running the sweep.

### 5. Operate DNSSEC in the right order

Validating resolvers answer SERVFAIL for a broken chain. The diagnostic is to repeat the
query with checking disabled:

```bash
dig example.com A               # SERVFAIL
dig +cd example.com A           # answers: the chain is broken, not the zone
delv example.com A              # explains the validation failure
```

The key signing key rollover by the double-KSK method, in order:

1. Publish the new KSK in the DNSKEY set, and sign the DNSKEY set with both the old and
   the new KSK.
2. Wait at least the DNSKEY TTL plus propagation to every authoritative server.
3. Replace the DS at the parent with the new key's DS, through the registrar.
4. Confirm every parent server returns the new DS, then wait at least the old DS record's
   TTL so no cache holds it.
5. Remove the old KSK.

To turn DNSSEC off: remove the DS at the parent first, wait out the DS TTL, then stop
signing. The reverse order makes the zone bogus for every validating resolver until the
DS expires. `references/dnssec-rollover.md` has the timings, the double-DS alternative,
enabling from scratch and the steps for managed signing; read it before any change to keys
or the DS.

### 6. Document and test split horizon

For every name that answers differently inside and outside, record both answers and why.
Test from both sides and compare. Watch for shadowing: in Route 53, a private hosted zone
for `example.com` associated with a VPC answers for the whole name inside that VPC, so a
record that exists only in the public zone does not resolve from inside. Mirror the
records internal clients need, or use a narrower private zone.

### 7. Monitor from outside

Resolve the critical names from several public resolvers on a schedule; alert on wrong
answers, SOA serial disagreement between authoritative servers, RRSIG expiry approaching
on any zone you sign yourself, DS and DNSKEY mismatch, and registration expiry.

## Output format

```markdown
## Inventory
| Domain | Registrar | Authoritative | DNSSEC | In code (tool) | Drift check | Account owners |

## Registrar
[Locks present per domain, registry lock where offered, MFA, recovery email domain, renewal.]

## Sweep
[Date; records checked by type; dangling found; each removed when; follow-up.]

## DNSSEC
[Per signed zone: KSK and ZSK tags, algorithm, last rollover, next due, procedure link.]

## Split horizon
[Names with different internal and external answers, and why.]

## Open findings
[Owner and date for each.]
```

## Anti-patterns

**Treating a resolving CNAME as safe.** Provider hostnames often resolve after the
resource is gone. The question is whether the resource is yours, not whether the name
resolves.

**Investigating a dangling record before deleting it.** Every hour the record stays is an
hour someone else can serve content on your domain. Remove it, then look at logs.

**Pulling the old DS or key without waiting.** The cache still holds the old data and
validating resolvers fail the whole domain for a TTL, which for a DS can be a day.

**Disabling DNSSEC by unsigning first.** The parent still says the zone is signed, so
every validating resolver rejects it until the DS is removed and expires.

**Letting a console edit stand.** The next apply reverts it, or worse, the code is changed
to match without review and nobody knows why the record exists.

**A registrar account on the domain it controls.** The day the domain lapses or is
hijacked, the password reset email goes to a mailbox that no longer exists.

## Reference files

- `references/dangling-sweep.md` — read in step 4: zone export commands per provider, the
  sweep script, provider ownership checks, and how to triage and remove what it finds.
- `references/dnssec-rollover.md` — read in step 5 before any DNSSEC change: KSK and ZSK
  rollover timelines, the double-DS method, enabling and disabling safely, verification
  commands and managed-signing notes.
