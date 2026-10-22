---
name: fleet-provisioning
description: "Give every manufactured device its own factory identity and an auditable record. Generate the key pair inside the secure element or crypto block and export only a CSR; never flash a shared key or keep a private key on the line PC. Run a fixed station flow (firmware, reversible readout protection, key, per-product intermediate CA under an offline root, certificate read back, functional test, record, then any permanent lock), keep a registry row per unit, reconcile against the manufacturer's count weekly to catch overbuild and claim units by proof of possession. Use for \"how do we provision certificates in manufacturing\", \"we flash the same key to every unit\", \"the contract manufacturer built extras\", \"claim a device to a customer account\". Not for rotating live credentials (secret-rotation), server ACME (certificate-automation) or trust-chain lifetime in the field (device-trust-anchors)."
allowed-tools: Read, Glob, Grep
---

# Fleet Provisioning

Provisioning is done when each unit leaves the line with an identity that exists nowhere else, a registry row that proves what was loaded into it, and a count you can reconcile against what the factory says it built.

The usual failure is convenience on the line: one key or one claim certificate baked into the image because it is simple to flash, or a private key generated on a station PC because the chip is slow. Either way a single leaked file, or one extracted unit, impersonates the whole fleet, and nothing in the registry shows which units were affected.

## Scope

Use for: designing or auditing the factory flow that creates device identities, the registry behind it, the contract manufacturer's access, and the step that binds a unit to a customer.

Do not use for: rotating shared secrets that are already live, which is `secret-rotation`; automating server certificates, which is `certificate-automation`; how long device certificates and roots must remain valid in the field, which is `device-trust-anchors`.

This is engineering procedure, not legal or regulatory advice; product security regimes differ by market.

## Workflow

### 1. Fix what the identity is

Decide the unit of identity before the tooling: one key pair and one certificate per unit, bound to a serial that is also printed or encoded on the product. Write down who trusts it (the cloud service, a peer device) and what it may do. A shared key, a shared claim certificate or a derived-from-serial secret is a fleet-wide credential; if one is unavoidable for first contact, it must only allow exchanging for a unique identity, and the exchange must be limited to serials the factory has declared.

### 2. Make the key on the device

Generate the private key inside the secure element or the MCU's crypto block, set it non-exportable, and export only a certificate signing request. The key then never exists on the line PC, in a log or in a programming file. If the part cannot generate a key, say so plainly and treat the line as a high-trust environment with a hardware security module and audited operators; a software-generated key written by a station is the weakest acceptable design and should be recorded as a known risk.

Prefer a part whose secure element supports locking configuration, so the slot policy (non-exportable, signing only) cannot be changed after the line writes it.

### 3. Fix the station flow, and its order

The order matters because each step guards the next. A unit that fails midway must be unable to leave as a half-finished product.

1. Program the bootloader and firmware, and read back their hashes.
2. Enable readout protection at a reversible level only, one that a mass erase or an authenticated regression can undo, so the unit stays recoverable while it is still being tested. Decide the RMA unlock now. Some parts have a level that can be regressed with a mass erase; others have a permanent level with no way back, and a permanent level means a returned unit is scrapped or re-flashed only by replacing the chip, which is a cost to price in. Whatever the choice, document the unlock and require authentication for it, so a field unit cannot be unlocked by anyone holding a debug probe. If the product uses a permanent level, it is applied in step 8, never here.
3. Generate the key on the device and export the CSR.
4. Send the CSR to the signing service (step 4) and receive the certificate.
5. Write the certificate and read it back. Compare the public key in the certificate with the one the device reports, so a certificate for the wrong unit is caught before it ships.
6. Run the functional test, including a handshake or a signed challenge using the new identity.
7. Only then write the registry row and mark the unit as passed. A row written before the test records units that never worked.
8. If the product uses a permanent or irreversible readout-protection level, set it now, as the very last step, after the functional test has passed and the registry row is written. A permanent level applied earlier turns every unit that fails test or needs rework into scrap. Read the level back and record it in the registry as an appended event.

### 4. Signing hierarchy

Keep an offline root that signs only intermediates, in a controlled ceremony. Use one online intermediate per product (or per product and factory) so compromise of one line does not touch another. The intermediate's private key lives in an HSM or a managed key service, not on the signing service's disk. The signing service signs a CSR only when it matches a work order: a known serial range, a quantity not yet used up, an authenticated station, and a key type and extensions it allows. It sets certificate lifetime and extensions itself and ignores whatever the CSR requests. For lifetimes and trust-root planning, follow `device-trust-anchors`.

### 5. The registry

One row per unit, written once and amended only by appended events:

- serial number and hardware revision
- key identifier or certificate fingerprint
- bootloader and firmware hashes and versions
- test results and the test software version
- station, operator or fixture, and time
- state: provisioned, shipped, claimed, returned, revoked

Treat it as an audit record: access-controlled, backed up, and not editable in place. Template and queries are in `references/registry-and-reconciliation.md`.

### 6. Reconcile against the contract manufacturer

A manufacturer can build more units than ordered and sell them; those units carry valid firmware and, if the factory can issue identities freely, valid certificates. Defences:

- Issue identities only against a purchase order's quantity, as in step 4.
- Reconcile weekly: units the signing service issued, units in the registry as passed, units the manufacturer reports shipped, and units received. Any difference is investigated by serial.
- Keep scrapped and failed units in the registry too; a high scrap count with low reported waste is a signal.
- Give the manufacturer's stations access to the signing service and nothing else: no root, no registry write beyond their own rows, no download of firmware sources.

### 7. Claiming a unit for a customer

Binding a unit to an account must prove the person has the physical unit, not merely the serial number, which is often printed on a box or guessable. Have the device sign a fresh challenge from the service with its provisioned key (proof of possession), accept the claim only for a unit in the registry and not already claimed, and pair it with something the owner has, such as a code shown on the device or a button press. Log claims. Transfer of ownership is an explicit unclaim followed by a new claim.

### 8. Returns and compromise

An RMA revokes the old identity and issues a new one through the same station flow, never by copying a key onto a replacement. Know how to revoke: a revocation list or a deny entry at the service, keyed by the fingerprint in the registry. Rehearse the bad day: given a leaked intermediate or one extracted key, the registry should list exactly the affected units within minutes.

### 9. Hand back

Give the station flow as an ordered list with the gate at each step, where each key and credential lives, the registry fields, the reconciliation query and its first result, the RMA unlock decision, and the residual risks accepted, such as parts that cannot generate keys on-chip.

## Anti-patterns

**One claim certificate in every image.** A single unit extracted from the field exposes it, and it grants whatever the exchange allows.

**Writing the registry row first.** It records intent, so units that failed test look provisioned.

**Letting the signing service accept any CSR.** The factory then mints identities for anyone who can reach it.

**Locking the debug port with no RMA plan.** Returned units become unanalysable, and the temptation is to reopen the lock with an unauthenticated procedure.

## Reference files

- `references/registry-and-reconciliation.md` — read at steps 5 and 6: a registry schema, the weekly reconciliation queries, a work-order check for the signing service and an incident query for a leaked key.
