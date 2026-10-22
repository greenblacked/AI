# Bus checklists

## Contents

- Capture settings
- UART symptoms
- I2C symptoms
- SPI symptoms
- Worked calculations

## Capture settings

| Bus | Lines to probe | Sample rate | Decoder settings |
| --- | --- | --- | --- |
| UART | TX, RX, optional RTS and CTS | at least 8 samples per bit | baud, data bits, parity, stop bits, inversion |
| I2C | SCL, SDA | at least 4x the bus clock, 10x for edges | 7-bit address display |
| SPI | SCLK, MOSI, MISO, CS | at least 4x SCLK | CPOL, CPHA, bit order, CS polarity |

Probe ground close to the signal, with short leads. A long ground lead rings and invents edges that the part never sees.

## UART symptoms

- Every character wrong but a repeated pattern: baud mismatch; compute the real divider.
- First character right, later ones drift: baud error accumulating over the frame.
- Some characters right, some not, at a high rate: error near the tolerance limit or a noisy line.
- Nothing seen at the receiver, line idles low: inverted polarity or an RS-232 level where TTL is expected.
- Output works until a burst of data, then loses bytes: no flow control or an overrun with no receive buffer.

## I2C symptoms

- Address phase NACKed: wrong address, no power, or the bus is held.
- Data NACKed: wrong register or length, or the part is busy.
- SDA low at idle: a part was reset mid-byte; clock out up to nine SCL pulses, then STOP.
- Both lines high but rising slowly in a curve: pull-ups too weak or capacitance too high.
- Works at 100 kHz, fails at 400 kHz: rise time fails the faster mode.
- Read returns the previous value: missing repeated start, or the controller does not wait for clock stretching.

## SPI symptoms

- All 0xFF: part not selected, not powered or not responding; MISO floats high.
- All 0x00: MISO held low or the part held in reset.
- Data shifted by one bit: wrong CPHA.
- Data inverted or every bit wrong in a pattern: wrong CPOL or bit order.
- Works slowly, fails fast: wiring or part timing limit.

## Worked calculations

Baud error. A peripheral clock of 16 MHz, 16x oversampling and a target of 115200 baud gives a divider of 16 000 000 / (16 x 115200) = 8.68. If the divider is stored as the integer 9, the actual rate is 16 000 000 / (16 x 9) = 111 111 baud, an error of (111 111 - 115 200) / 115 200 = about -3.5 percent. That is over the budget before the other end contributes; use a fractional divider or a different clock.

Pull-up. A fast-mode bus (tr allowed 300 ns) with 100 pF of capacitance: `Rp(max) = 300e-9 / (0.8473 x 100e-12)` = about 3.5 kohm. The minimum is set by the low-level current: with a 3.3 V supply and 3 mA sink, `Rp(min) = (3.3 - 0.4) / 0.003` = about 970 ohm. Choose a value between them, nearer the lower end if the capacitance is uncertain.
