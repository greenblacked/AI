# TLS alerts and verify codes

## Contents

- TLS alerts
- OpenSSL verify codes
- curl exit codes that mean TLS
- Server-side log phrases
- Quick comparisons that locate the fault

## TLS alerts

An alert is the peer saying why it closed. The alert is named from the point of view of the side that sent it, so `unknown ca` received by the client means the server did not trust the client's certificate, and the same text printed on the server means the client did not trust the server's.

| Alert (number) | Typical cause | First check |
| --- | --- | --- |
| `handshake_failure` (40) | No shared cipher suite, signature algorithm or group; sometimes a missing certificate for the requested name | `nmap --script ssl-enum-ciphers`, `s_client` with `-tls1_2` and `-tls1_3` |
| `bad_certificate` (42) | Certificate unreadable, corrupt or invalid in a way not covered by a finer alert | Parse it with `openssl x509 -noout -text` |
| `certificate_expired` (45) | A certificate in the chain is outside its dates, or the peer's clock is wrong | Dates and `date -u` on both sides |
| `certificate_unknown` (46) | Unspecified certificate problem | Server log of the rejecting side |
| `unknown_ca` (48) | The chain does not lead to a CA the peer trusts | Chain completeness, the peer's trust store |
| `access_denied` (49) | Valid client certificate, but policy refuses it | Server authorisation rules for that identity |
| `decrypt_error` (51) | A signature or Finished message failed to verify | Key and certificate mismatch; proxy mangling |
| `protocol_version` (70) | No common protocol version | Which versions each side enables |
| `insufficient_security` (71) | Offered parameters too weak for the peer's policy | Cipher and key-size policy |
| `internal_error` (80) | Fault on the sender | Sender's error log |
| `unrecognized_name` (112) | SNI names a host the server does not serve | The `-servername` value, virtual host configuration |
| `certificate_required` (116) | Server requires a client certificate and none was sent (TLS 1.3) | mTLS step; client certificate configuration |
| `no_application_protocol` (120) | No ALPN protocol in common | Offered `-alpn` list versus the server's |

## OpenSSL verify codes

| Code | Message | Meaning |
| --- | --- | --- |
| 0 | ok | Verified against the trust store used |
| 2 | unable to get issuer certificate | Issuer not found in the chain or store |
| 10 | certificate has expired | A certificate in the chain is past `notAfter` |
| 9 | certificate is not yet valid | Before `notBefore`; often a client clock behind |
| 18 | self-signed certificate | The leaf is its own issuer and not trusted |
| 19 | self-signed certificate in chain | A root in the chain is not in the trust store |
| 20 | unable to get local issuer certificate | The issuer is not available locally: missing intermediate or untrusted root |
| 21 | unable to verify the first certificate | Only the leaf is available and its issuer is unknown |
| 62 | hostname mismatch | The name checked is not in the SAN list |

The default trust store differs by tool. Pass `-CAfile` or `-CApath` to `s_client` to be explicit, and `--cacert` to curl; otherwise the result describes only that tool's default.

## curl exit codes that mean TLS

| Exit code | Meaning |
| --- | --- |
| 35 | TLS connect error, handshake failed (read the alert in `-v`) |
| 51 | Peer certificate or fingerprint not OK (older libraries; hostname) |
| 58 | Problem with the local client certificate |
| 59 | Could not use the specified cipher |
| 60 | Peer certificate cannot be authenticated with known CA certificates |
| 77 | Problem reading the CA certificate file |
| 83 | Issuer check failed |

## Server-side log phrases

| Phrase | Source | Reading |
| --- | --- | --- |
| `no shared cipher` | nginx, OpenSSL | The client's offer and server's list do not intersect |
| `SSL_do_handshake() failed ... wrong version number` | nginx | Plain HTTP sent to a TLS port, or a proxy protocol mismatch |
| `peer did not return a certificate` | nginx | mTLS client sent none |
| `unsupported protocol` | OpenSSL | The client's minimum version exceeds the server's maximum or the reverse |
| `certificate verify failed` | OpenSSL, many | Match the verify code beside it |
| `PKIX path building failed` | Java | Missing issuer in the Java trust store |
| `unable to find valid certification path` | Java | The same |

## Quick comparisons that locate the fault

- **Same host, with and without `-servername`.** Different certificates mean SNI-dependent virtual hosts.
- **Same host, `--resolve` to each backend address.** A single backend failing is a stale node or a mismatched certificate on one member of a pool.
- **A clean machine versus the failing one.** Different results point at trust store, proxy, clock or outbound inspection on the failing one.
- **TLS 1.2 forced versus TLS 1.3 forced.** One failing isolates a version-specific configuration.
- **Direct to the origin versus through the CDN or load balancer.** The failure moving with the hop names the hop that terminates TLS.
