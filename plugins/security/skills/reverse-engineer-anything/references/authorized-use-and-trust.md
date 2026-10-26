# Authorized use and trust boundaries

Condensed from upstream [DISCLAIMER.md](https://github.com/morluto/rea/blob/main/DISCLAIMER.md)
and [SECURITY.md](https://github.com/morluto/rea/blob/main/SECURITY.md).

## Lawful use

Appropriate: security research, malware and incident analysis, vulnerability
research and coordinated disclosure, CTFs and education, interoperability,
software preservation, and debugging or auditing software you own or are
authorized to examine.

Not supported: DRM / license / anti-cheat circumvention; game cheats or online
service tampering; bypassing authentication or access controls without
authorization; copying proprietary software or protected assets; evading provider
policies; reselling or sharing provider accounts.

You are responsible for authorization, applicable law, contracts, IP, privacy,
and third-party tool licenses. Possession of a file does not by itself authorize
every operation.

## Runtime and device operations

Some workflows execute or observe programs, browsers, network captures, or
attached devices. Authorization to inspect an artifact does not necessarily
authorize execution, interception, or device changes. Prefer static inspection
first; use disposable environments for dynamic work.

## Trust and distribution

- Official sources only: `github.com/morluto/rea`, `rea.tools`, npm `rea-agents`.
- Pin exact package versions in durable MCP config.
- REA analyzes locally; the host session may still send tool results to a cloud
  provider — use a local/offline host for sensitive targets when required.
- Bridges authenticate with per-session tokens over private IPC. That is not a
  sandbox against same-user malware.
- Opening an untrusted binary delegates parsing to Ghidra/Hopper/IDA/JADX with
  the current user's permissions.
- Obtain commercial engines lawfully; REA provides no license keys.

## Results

Decompilation and reconstruction may be incomplete or wrong. Review evidence
before consequential decisions. Obtaining source-like output does not grant
rights to the original program or to redistribute generated material.
