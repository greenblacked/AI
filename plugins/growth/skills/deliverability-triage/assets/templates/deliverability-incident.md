# Deliverability incident: [short name]

<!-- One record per placement or bounce drop. Fill every bracket from a dated reading; leave
a bracket as it is when the figure is not yet known. Never estimate one. -->

## Window and split

- Window: [start date] to [end date]
- Split by mailbox provider: [provider, rate before, rate now]
- Split by stream: [stream, rate before, rate now]
- Split by sending domain or IP: [domain or IP, rate before, rate now]
- Date the slice first moved: [date]

## Provider-side readings

| Source | Reading | Date |
| --- | --- | --- |
| Postmaster spam rate | [value] | [date] |
| SNDS | [value] | [date] |
| Complaint feedback loop | [value] | [date] |

## Bounce and deferral classes

| Class (code or text) | Count | Provider |
| --- | --- | --- |
| [class] | [count] | [provider] |

## Authentication check

SPF, DKIM and DMARC result for the affected stream: [pass or fail, aligned or not, date checked]

## The single change

- Change made: [one change]
- Expected effect: [what should move, by how much]
- Measure on: [date]

## Result

Provider-side reading after the change: [value] on [date]

## Standing suppression rule added

[rule, threshold and owner]
