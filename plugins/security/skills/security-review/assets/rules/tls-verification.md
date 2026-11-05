---
paths:
  - "**/*.yaml"
  - "**/*.yml"
  - "**/*.json"
  - "**/*.toml"
  - "**/*.ini"
  - "**/*.conf"
---

# TLS verification in committed config

Loads when a config file is read or edited. Turning certificate verification off in a file that
is committed turns it off for every environment that reads the file, usually long after the
reason for it has gone.

- Do not set a skip-verification key to true or a verify key to false in a committed file.
  That covers the Kubernetes `insecure-skip-tls-verify`, Go-style `insecure_skip_verify`,
  `skip_tls_verify`, and the Ansible, Python-client and registry equivalents `validate_certs`,
  `verify_ssl` and `ssl_verify`.
- Fix the trust chain instead: add the issuing CA to the client's CA bundle, or name it with
  the client's CA-file setting. Verification stays on and the failure goes away.
- A genuine exception (a lab appliance with a self-signed certificate, a migration window)
  needs a record in `tls-verification-exception.md` before the setting lands: one client, one
  exact host, why the bundle cannot be fixed, a compensating control, an owner, an expiry and
  the revert step. Never a wildcard host, never a production default.
- Put the key in an overlay or environment-specific file that is never the default, and carry
  the marker `tls-exception` on the same line, with the record's id, so the reviewer and the
  hook can see it is recorded.
- The check reads these file types only. A skip written in code (a client option, a curl flag,
  an environment variable) or in an extensionless client config file is not seen, so look for those in
  review, with the `security-review` skill.
