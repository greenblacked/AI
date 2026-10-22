# Registry and reconciliation

## Contents

- Registry schema
- Signing service work-order check
- Weekly reconciliation
- Compromise query
- Station checklist

## Registry schema

Names are illustrative; keep the fields.

```sql
CREATE TABLE unit (
  serial            TEXT PRIMARY KEY,
  product           TEXT NOT NULL,
  hw_revision       TEXT NOT NULL,
  bootloader_hash   TEXT NOT NULL,
  firmware_hash     TEXT NOT NULL,
  firmware_version  TEXT NOT NULL,
  test_result       TEXT NOT NULL,
  test_sw_version   TEXT NOT NULL,
  station_id        TEXT NOT NULL,
  work_order        TEXT NOT NULL,
  provisioned_at    TIMESTAMP NOT NULL
);

-- no foreign key to unit: a certificate is issued (step 4 of the flow) before the
-- unit row is written (step 7), and a unit that fails test never gets a row
CREATE TABLE unit_cert (
  serial       TEXT NOT NULL,
  fingerprint  TEXT NOT NULL UNIQUE,
  issued_at    TIMESTAMP NOT NULL,
  revoked_at   TIMESTAMP,
  work_order   TEXT NOT NULL,
  station_id   TEXT NOT NULL   -- the station that issued it, so exposure needs no unit row
);

CREATE TABLE failed_unit (
  serial           TEXT NOT NULL,
  station_id       TEXT NOT NULL,
  test_sw_version  TEXT NOT NULL,
  reason           TEXT,
  failed_at        TIMESTAMP NOT NULL
);

CREATE TABLE unit_event (
  serial      TEXT NOT NULL REFERENCES unit(serial),
  event       TEXT NOT NULL,  -- shipped, claimed, unclaimed, returned, revoked
  actor       TEXT NOT NULL,
  at          TIMESTAMP NOT NULL,
  detail      TEXT
);
```

Issuance has its own table so an RMA or a retried attempt adds a row and sets `revoked_at` on the earlier one; the `unit` row is never rewritten. State is derived from the latest event, so history is never overwritten. Failed units go in the separate `failed_unit` table with the same station and time fields, so scrap is counted, and writing that row sets `revoked_at` on the unit's certificate in the same transaction: a scrapped board must not leave the line with a live identity.

## Signing service work-order check

A CSR is signed only when every line holds.

1. The station presents a credential bound to a known fixture, and the fixture is enabled for this product.
2. The work order is open and `issued_count` is below `quantity`.
3. The serial is inside the order's range and not already in `unit`.
4. The CSR key type and size are on the allow list, and its signature verifies.
5. Subject and extensions come from the service, not the CSR.
6. The issuance, the work order and the fingerprint are logged before the certificate is returned.

A failed provisioning attempt on a serial must be reusable only by an explicit, logged re-issue that revokes the earlier certificate.

## Weekly reconciliation

Four counts per product and week, from four independent sources.

| Source | Count |
| --- | --- |
| Signing service log | certificates issued |
| Registry | rows with a passing test |
| Manufacturer shipment report | units shipped to you or to customers |
| Your receiving or shipping records | units received |

```sql
-- live certificates with no passing registry row; failed shows whether the
-- unit was recorded as scrap (true) or is unaccounted for (false)
SELECT c.serial, c.fingerprint,
       EXISTS (SELECT 1 FROM failed_unit f WHERE f.serial = c.serial) AS failed
FROM unit_cert c
LEFT JOIN unit u ON u.serial = c.serial AND u.test_result = 'pass'
WHERE u.serial IS NULL AND c.revoked_at IS NULL;

-- registry rows beyond the work order quantity
SELECT work_order, COUNT(*) AS built, MAX(w.quantity) AS ordered
FROM unit u JOIN work_order w ON w.id = u.work_order
GROUP BY work_order HAVING COUNT(*) > MAX(w.quantity);
```

Anything non-zero is investigated by serial before the next order is opened. Overbuild shows up as the manufacturer's shipped count exceeding the registry's passing count; compare by serial range, not totals, and look for ranges that have been shipped but never provisioned.

## Compromise query

If an intermediate or a station credential is suspected, list the exposure first and revoke second.

```sql
SELECT c.serial, c.fingerprint, c.station_id, c.issued_at, c.revoked_at
FROM unit_cert c
WHERE c.station_id = :station AND c.issued_at BETWEEN :from AND :to;
```

Feed the fingerprints to the revocation list or service deny entry. Units in the field then need a path to a fresh identity; plan that before it is needed.

## Station checklist

- Programming files are checked by hash before use; the station cannot run a modified image.
- The readout protection step is verified by attempting a read, and failure fails the unit.
- The station has no copy of any private key and no standing network path beyond the signing service and the registry.
- Fixture serial numbers are in the registry so a faulty fixture can be traced to every unit it handled.
- The test software version is recorded per unit.
