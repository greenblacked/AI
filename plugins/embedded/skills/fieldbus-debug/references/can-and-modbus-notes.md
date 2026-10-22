# CAN and Modbus notes

## Contents

- Resistance readings
- Worked bus-off case
- Modbus frame walkthrough
- Silent interval at common baud rates
- Register addressing and word-order tests

## Resistance readings

Measure between CANH and CANL with all nodes unpowered.

| Reading | Meaning |
| --- | --- |
| About 60 ohms | Two terminators, one at each end |
| About 120 ohms | One terminator only, or one has an open connection |
| About 40 ohms | Three terminators |
| Over 1 kilohm | No termination, or an open conductor |
| Near zero | A short between the pair |

Then measure each conductor to ground and to the shield; a low reading is a fault. With the bus powered and idle, CANH and CANL both sit near half the supply (about 2.5 V on a 5 V transceiver); a stuck dominant level shows a large difference.

## Worked bus-off case

A machine reports one drive dropping off the network every few hours.

1. The error counters on the drive's controller climbed over minutes before the drop; the others stayed near zero. So the fault is local to that drive.
2. The drive's cable is the longest stub on the line, and an extra terminator was fitted at the drive end of that stub.
3. The resistance reading with power off was about 40 ohms: three terminators.
4. The extra terminator was removed and the stub shortened. The reading became 60 ohms, and the counter stayed under 20 for a week.

The fix came from the measurement, not from the firmware. Recovery logic was still changed to wait and back off, since the original restarted immediately and raised bus load during the fault.

## Modbus frame walkthrough

Request to device 17 for two holding registers starting at wire address 107:

```text
11 03 00 6B 00 02 B7 47
```

Fields: device address, function 3, start address high and low (0x006B is 107), quantity (2), then the CRC low byte first. The documented register number in a 4xxxx table would be 40108. A response begins with the same address and function, a byte count (4), the data, then its CRC. An exception reply replaces the function with 0x83 and carries one exception code byte.

The CRC is the 16-bit Modbus CRC with initial value 0xFFFF and reflected polynomial 0xA001, transmitted low byte first. Verify your implementation against a known frame like the one above before trusting it on the bus.

## Silent interval at common baud rates

A character on the wire is 11 bits (start, 8 data, parity, stop) in the default Modbus framing.

| Baud | Character time | 3.5 characters | 1.5 characters |
| --- | --- | --- | --- |
| 9600 | 1.15 ms | 4.0 ms | 1.7 ms |
| 19200 | 0.57 ms | 2.0 ms | 0.86 ms |
| above 19200 | fixed | 1.75 ms | 0.75 ms |

Check that the platform timer can resolve these. A tick of 1 ms makes the 1.75 ms interval unreliable.

## Register addressing and word-order tests

Read a value you can confirm from the device's display, such as a setpoint of 100.0, and compare.

| Observed decode | Conclusion |
| --- | --- |
| The value of the neighbouring register | Off-by-one: documented number versus wire address |
| Correct integer, wrong float | Word order: swap the two registers |
| Garbage float with correct word order | Byte order inside words: swap bytes |
| Exception: illegal data address | Register not implemented, or a block read crosses one |
| No reply | Wrong device address, baud, parity or stop bits; or a driver-enable timing fault |

Record the working combination in the integration notes so the next engineer does not rediscover it.
