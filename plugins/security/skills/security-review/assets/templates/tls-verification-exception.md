# TLS verification exception

One record per exception. Fill in every field; a field you cannot fill in is a reason to fix the
CA bundle instead. Keep the record next to the config it covers and put its id in the
`tls-exception` marker on the line that turns verification off.

- **Id:**
- **Client** (tool or library, and the config file that sets it):
- **Host** (one exact name and port, no wildcard):
- **Why the CA bundle cannot be fixed** (what was tried, who owns the certificate):
- **Compensating control** (network path, pinned fingerprint, mutual authentication, read-only
  data):
- **Environment** (never the default; name the overlay or file):
- **Owner** (a person or team that answers for it):
- **Granted on / Expires** (a date, at most 90 days out):
- **Revert step** (the exact change that turns verification back on):
- **Verification command** (shows the host now validates, or that the exception is gone):
- **Reviewed by:**

## Closing

When the date passes, either revert and record the verification output here, or renew with a new
date and a reason. An expired record with the setting still in place is a finding.
