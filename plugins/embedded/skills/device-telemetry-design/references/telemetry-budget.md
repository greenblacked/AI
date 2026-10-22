# Telemetry budget and schema

## Contents

- Budget arithmetic
- Worked example
- Field registry template
- Message layout
- Schema evolution rules
- Three-day test sheet

## Budget arithmetic

1. Monthly data allowance per device, from the plan price and the share you will spend on telemetry: `bytes_per_day = monthly_bytes / 30`.
2. Subtract protocol overhead per connection. Handshakes, headers and acknowledgements can dwarf a small payload, so count the cost of each connection, not only the payload.
3. Energy: multiply the connections per day by the energy of one connection (radio-on time times current, including the connected-state tail) and check against the battery's share for communications.
4. Choose the smaller of the byte and energy limits, then divide: connections per day times payload per connection.

## Worked example

A plan that allows 3 MB per month for telemetry gives about 100 KB per day. If each connection costs about 4 KB of overhead and 1 KB of payload, five connections a day cost 25 KB, leaving room for a larger payload on the daily summary. If the energy limit allows only four connections a day, the energy limit is the binding one. Replace these figures with measurements from your own link; the point is the method.

## Field registry template

| Id | Name | Type | Unit | Cadence | Diagnosis it enables | Since version |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | reset_reason | enum | n/a | each boot | brownout versus watchdog versus fault | 1 |
| 2 | reset_count | counter | resets | each report | reset loops | 1 |
| 3 | uptime | counter | seconds | each report | fresh reset versus long-lived | 1 |

Keep one row per field, and a row for each retired field marked retired, so its id is never reused.

## Message layout

A message contains:

- Schema version.
- Device id and a per-device sequence number, incremented per message.
- Build id.
- A counters block (aggregated since the last report, or running totals; choose one and state which).
- An events block, each with a code and arguments.
- An optional crash block: fault registers and the ring log, sent once after an abnormal boot.

Send running totals where a lost message would otherwise lose information: the receiver subtracts, and the gap does not lose counts.

## Schema evolution rules

- Add fields with new ids; never repurpose an id.
- A receiver ignores ids it does not know; a sender omits fields the receiver does not need.
- Do not change a unit or scale without a new id.
- Keep decoders for every schema version still in the field.
- Test an old-firmware message against the new backend and a new-firmware message against the old backend before each release.

## Three-day test sheet

| Step | Expected |
| --- | --- |
| Disconnect for 72 hours | Device keeps running; buffer does not overflow silently |
| Force a reset, a fault and a low-battery event | Each recorded locally |
| Reconnect | Sequence gap visible; ring log and fault record delivered |
| Check volume after reconnect | Within the daily budget or spread across days by policy |
| Check drop policy | Faults kept, routine samples dropped first |
