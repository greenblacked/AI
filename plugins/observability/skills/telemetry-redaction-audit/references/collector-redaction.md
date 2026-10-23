# Collector redaction

## Contents

- Allow-list with the redaction processor
- Pattern masking with transform
- Placement in the pipeline
- Verifying

## Allow-list with the redaction processor

The `redaction` processor (collector contrib) removes attributes whose keys are not allowed and masks values that match blocked patterns.

```yaml
processors:
  redaction:
    allow_all_keys: false
    allowed_keys:
      - http.request.method
      - http.response.status_code
      - http.route
      - url.path
      - server.address
      - service.name
      - service.version
      - rpc.method
    blocked_values:
      - "eyJ[A-Za-z0-9_-]{8,}\\.eyJ[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]*"
      - "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
    summary: info
```

`summary: info` adds counts of the redacted and masked values as attributes; `summary: debug` also adds the key names, which is how you find the next leaking source. Keys not listed are dropped, so run with `summary: debug` in staging to build the list from real traffic, then use `info` in production, where key names are not worth the extra attributes. Check the processor's README for your collector version, since option names have changed between releases.

## Pattern masking with transform

For logs, where the body is free text, use OTTL:

```yaml
processors:
  transform/mask:
    log_statements:
      - context: log
        statements:
          - replace_pattern(body, "eyJ[A-Za-z0-9_-]{8,}\\.eyJ[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]*", "[jwt]")
          - replace_pattern(attributes["http.url"], "([?&](token|key|sig)=)[^&]+", "$$1[removed]")
```

`$$` escapes the dollar sign in collector configuration so the capture group reference reaches the regular expression. `replace_pattern` only works on string values; a body that is a map needs its string fields addressed individually.

## Placement in the pipeline

Put redaction first after `memory_limiter` and before `batch`, tail sampling, any exporter with a persistent queue, and any connector that derives metrics, so unmasked values are not written to disk or turned into labels. Run it at the node or agent tier as well as the gateway when data leaves a trust boundary between them.

## Verifying

- Unit check: feed the collector a test span with a canary in each attribute class and read the exported output from a `debug` exporter in staging.
- Self-metrics: watch the exporter and processor counters for drops after enabling the allow-list; a sudden fall in attributes is expected, a fall in spans is not.
- Re-run the canary suite from the audit after each change.
