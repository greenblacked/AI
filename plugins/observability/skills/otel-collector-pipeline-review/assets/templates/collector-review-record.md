# Collector review record

One collector configuration and its deployment. Fill in every field; delete the guidance in
brackets.

## Subject

- Configuration files: [paths]
- Distribution and version: [core, contrib, vendor or custom build, and version]
- Tier: [node agent, gateway or single tier, and why]
- Container memory limit and replica count: [values]
- GOMEMLIMIT: [value, or unset]

## Pipelines

One row per pipeline.

| Pipeline | Processors in order | memory_limiter first | batch last | Exporters |
| --- | --- | --- | --- | --- |
| [traces, metrics or logs, with any name suffix] | [list] | [yes or no] | [yes or no] | [list] |

## Exporters

| Exporter | sending_queue and size unit | Must survive restart | Storage | Retry bound | TLS |
| --- | --- | --- | --- | --- | --- |
| [name] | [enabled, size] | [yes or no] | [file_storage path or none] | [max_elapsed_time] | [yes or no] |

## Findings

Ordered by consequence: what loses data, what causes a kill, what is only untidy.

| Finding | File and setting | Why it matters | Smallest change |
| --- | --- | --- | --- |
| [text] | [file:line, key] | [consequence] | [change] |

## Validation and load run

- `otelcol validate` result: [pass or the error]
- Memory under the limit at the container limit: [peak value]
- Refusals before an OOM kill: [yes or no, counts]
- Queue fills when the backend is stopped, process survives: [yes or no]

## Not verified

[Anything not checked, and why.]
