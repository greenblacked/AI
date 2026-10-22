# Probe configuration and triage

## Contents

- Blackbox exporter module
- Scrape configuration with locations
- Quorum alert
- Prober-health alert
- Triage worksheet

## Blackbox exporter module

A module that checks status, content and the identifying header:

```yaml
modules:
  http_login_page:
    prober: http
    timeout: 10s
    http:
      method: GET
      valid_status_codes: [200]
      headers:
        User-Agent: "acme-synthetic/1.0"
        X-Synthetic-Check: "login-page"
      fail_if_body_not_matches_regexp:
        - "Sign in to your account"
      preferred_ip_protocol: ip4
```

The exporter answers `/probe?target=https://example.com/login&module=http_login_page`. Metrics include `probe_success`, `probe_duration_seconds`, `probe_http_status_code` and, for TLS, `probe_ssl_earliest_cert_expiry`. It does not run a multi-step journey; use a scripted browser or API check for flows that need state across steps.

## Scrape configuration with locations

Run one exporter per location and scrape each with a `location` label:

```yaml
scrape_configs:
  - job_name: synthetic-login-eu
    metrics_path: /probe
    params:
      module: [http_login_page]
    static_configs:
      - targets: ["https://example.com/login"]
        labels:
          check: login
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: probe-eu.example.net:9115
      - target_label: location
        replacement: eu
```

Repeat the job once per location with a different `replacement` address and `location`. Prometheus rejects duplicate `job_name` values, so name them `synthetic-login-eu`, `synthetic-login-us` and so on; the shared `check: login` label is what the alerts below group and match on. Keep each location on separate infrastructure, and ideally more than one hosting provider.

## Quorum alert

Page when at least two of three locations fail for several minutes:

```yaml
- alert: SyntheticLoginDown
  expr: count by (check) (probe_success{check="login"} == 0) >= 2
  for: 3m
  labels:
    severity: page
- alert: SyntheticLoginSingleLocation
  expr: probe_success{check="login"} == 0
  for: 10m
  labels:
    severity: ticket
```

Adjust the quorum to the number of locations: majority of the count, not a fixed 2. The `for:` duration covers the retry; a retry from a different location is what the other locations' results already supply. A hosted checker offers the same through its own alert settings; set it to require failures in more than one location.

## Prober-health alert

```yaml
- alert: SyntheticProberSilent
  expr: absent_over_time(probe_success{check="login", location="eu"}[15m])
  labels:
    severity: ticket
```

Write one per location, or generate them. Also alert on `up{job="synthetic-login-eu"} == 0` for the exporter itself, and on a location whose failure rate over a day is several times the median of the others.

## Triage worksheet

For each failed run in the last 30 days, record: time, location, failing step, status code or error, and cause from the table in the skill. Then group:

- by location: a location with most of the failures is a location problem
- by hour of day: a fixed hour points to a batch job, a backup, a rate limit or a time-zone bug in the check
- by failing step: one step failing in most runs is a brittle step or a third-party dependency
- by status code: 403 and challenge pages are bot rules; 429 is rate limiting of the probe; 5xx at the same time as real-user errors is a real outage

Compute false pages per month as pages with no matching real-user degradation. If the count is above one, start with the largest cause group.
