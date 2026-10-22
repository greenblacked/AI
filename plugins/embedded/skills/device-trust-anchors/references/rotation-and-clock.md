# Rotation and clock

## Contents

- Anchor layout
- Inspecting expiry
- Clock test matrix
- Rotation rehearsal

## Anchor layout

| Item | Held where | In the device | Lifetime |
| --- | --- | --- | --- |
| Anchor A, current | offline, separate access control | public certificate | field life plus shelf life plus margin |
| Anchor B, spare | offline, separate access control | public certificate only | same or longer |
| Private intermediate | online signing service, the only key that signs routinely | pinned or chained to A and B | shorter than the anchors, renewable |
| Device certificate | the unit | its own | renewed from half its lifetime |

The spare's private key must exist from day one. A spare created after the problem cannot be in units already shipped.

## Inspecting expiry

Dates of a certificate: `openssl x509 -in cert.pem -noout -dates`. Subject and issuer: `openssl x509 -in cert.pem -noout -subject -issuer`. Verify a chain at a chosen time: `openssl verify -attime <epoch-seconds> -CAfile anchors.pem -untrusted intermediate.pem leaf.pem`. Use `-attime` to test the ten-year case without changing the machine clock.

## Clock test matrix

| Unit clock | Expected result |
| --- | --- |
| Correct | connects |
| Build date | connects after time bootstrap, or waits and retries |
| 1970 | same as build date |
| Ten years after build | validates against anchors that are still valid; fails clearly when they are not |
| Ahead of the server by a day | connects within tolerance, or reports skew |

Record what the unit logs in each case, and confirm it never disables certificate checks to proceed.

## Rotation rehearsal

1. Pick lab units: newest firmware, oldest firmware, one stored for a year, one with a dead clock.
2. Publish the new chain under the spare anchor on a test service.
3. Push the configuration that switches the units to it.
4. Count units that reconnect, and read the logs of those that do not.
5. Repeat after expiring the old chain in the test.
6. Write down the time taken and the units that needed manual work; any such unit is a production risk of its own kind.
