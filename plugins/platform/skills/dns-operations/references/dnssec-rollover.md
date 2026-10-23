# DNSSEC rollover and state changes

Read this before any change to DNSSEC keys or to the DS record at the parent. Every
procedure here is a sequence of publish, wait, switch, wait, retire. The waits are the
procedure; skipping one is how a domain disappears for validating resolvers.

## Contents

- The values to read first
- KSK rollover: double-KSK
- KSK rollover: double-DS
- ZSK rollover: pre-publish
- Enabling DNSSEC
- Disabling DNSSEC
- Verification commands
- Managed signing
- Algorithm changes

## The values to read first

| Value | How to read it | Why |
| --- | --- | --- |
| DNSKEY TTL | `dig +noall +answer DNSKEY example.com` from an authoritative server | How long a resolver may cache the old key set |
| DS TTL at the parent | `dig +norecurse +noall +answer DS example.com @PARENT-NS` | How long a resolver may cache the old DS; often a day at large TLDs |
| Maximum zone TTL | The largest TTL of any signed record | How long old signatures may be cached |
| Propagation delay | Time for a change to reach every authoritative server, checked with `dig +nssearch` | Added to every wait |

Find a parent server with `dig +short NS com.` (or the relevant TLD). Write every wait as
"TTL plus propagation plus a margin", and record the earliest time the next step may run.

## KSK rollover: double-KSK

1. Generate the new KSK and publish it in the DNSKEY set. Sign the DNSKEY set with both the
   old and the new KSK. The ZSK keeps signing everything else.
2. Confirm every authoritative server serves the new DNSKEY set.
3. Wait the DNSKEY TTL plus propagation, so every cache that holds the DNSKEY set holds the
   one containing both keys.
4. Submit the new DS to the parent through the registrar, replacing the old DS.
5. Confirm every parent server returns only the new DS.
6. Wait the parent's DS TTL plus propagation, so no cache still holds the old DS.
7. Remove the old KSK from the DNSKEY set and stop signing with it.
8. Verify validation from several validating resolvers.

The failure modes: removing the old KSK before step 6 completes leaves resolvers holding
the old DS with no matching key; changing the DS before step 3 completes leaves resolvers
holding the new DS with a cached key set that lacks the new key.

## KSK rollover: double-DS

Useful when changing the DNSKEY set is easy but registrar changes are slow:

1. Add the new key's DS at the parent alongside the old DS.
2. Confirm at every parent server, then wait the DS TTL plus propagation.
3. Replace the old KSK with the new KSK in the DNSKEY set.
4. Wait the DNSKEY TTL plus propagation.
5. Remove the old DS from the parent.

Where the parent registry reads CDS or CDNSKEY records from the child zone, the DS changes
can be automated. Confirm the registry supports it before depending on it.

## ZSK rollover: pre-publish

1. Publish the new ZSK in the DNSKEY set without signing with it.
2. Wait the DNSKEY TTL plus propagation.
3. Sign the zone with the new ZSK instead of the old.
4. Wait the maximum zone TTL plus propagation, so no cached signature from the old ZSK
   remains.
5. Remove the old ZSK.

No parent change is involved. Most signing tools and managed providers do this
automatically; confirm the schedule rather than assuming.

## Enabling DNSSEC

1. Sign the zone and confirm every authoritative server serves DNSKEY and RRSIG records.
2. Validate the signed zone before the parent knows about it: `delv` with the new key as a
   trust anchor, or an online analyser.
3. Wait the DNSKEY TTL.
4. Add the DS at the parent through the registrar.
5. Confirm from several validating resolvers.

Nothing is enforced until the DS exists at the parent, which is what makes the steps before
it safe.

## Disabling DNSSEC

1. Remove the DS at the parent through the registrar.
2. Confirm every parent server has dropped it.
3. Wait the DS TTL plus propagation.
4. Stop signing and remove the DNSKEY records.

Doing it in the other order makes the zone bogus for every validating resolver until the
old DS expires from caches. This is also the order to follow before moving a signed zone to
a provider that cannot import the existing keys.

## Verification commands

```bash
dig +dnssec +multi +noall +answer DNSKEY example.com   # key tags; flags 257 is a KSK, 256 a ZSK
dig +norecurse +noall +answer DS example.com @a.gtld-servers.net
dig example.com A                                      # SERVFAIL here...
dig +cd example.com A                                  # ...but an answer here: validation failure
delv example.com A                                     # reports why validation failed, or that it succeeded
dig +dnssec +noall +answer example.com SOA             # RRSIG expiration time for signed data
```

Match the key tag in the DS record to a KSK in the DNSKEY set. A DS whose key tag matches no
published KSK is a broken chain.

## Managed signing

**Route 53.** The KSK is backed by a customer managed KMS key, which Route 53 requires to be
asymmetric, ECC_NIST_P256, and in US East (N. Virginia); Route 53 manages the ZSK. The
relevant commands are `create-key-signing-key`, `get-dnssec` (which shows each KSK's status
and its DS record), `deactivate-key-signing-key`, `delete-key-signing-key`,
`enable-hosted-zone-dnssec` and `disable-hosted-zone-dnssec`. Alarm on the
`DNSSECInternalFailure` and `DNSSECKeySigningKeysNeedingAction` metrics. Disabling or
scheduling deletion of the KMS key behind an active KSK stops signing, and the zone fails
validation once existing signatures expire; protect that key accordingly.

**Other managed providers.** Read the provider's documented KSK procedure. Whatever it
automates for the ZSK, a KSK change still needs a DS change at the parent unless the
registry consumes CDS records, and that DS change is yours.

## Algorithm changes

Changing the signing algorithm is not a key rollover: the zone must be signed with both
algorithms while both are published, and the order differs from the procedures above.
Follow the algorithm rollover guidance in RFC 6781 and RFC 7583 and the signer's own
documentation, and treat it as a planned change with its own runbook.
