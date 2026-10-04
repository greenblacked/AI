# Security

## Reporting

Report a suspected vulnerability or a leaked credential privately through GitHub's
[security advisory form](https://github.com/greenblacked/AI/security/advisories/new) for this repository, rather than opening an issue. If the finding
is a credential visible in this repository or its history, say so in the first line so it
can be revoked before anything else is discussed.

## What this repository contains

Markdown instructions for AI coding agents, and a standard-library Python validator. It
holds no secrets, no production configuration, and no dependencies at runtime.

That does not make it inert. Skills are instructions an agent follows, sometimes with
tool access, so a malicious change here is a supply-chain change. The controls are:

- **Secret scanning** over both the working tree and the full history on every pull
  request. A secret that was committed and later removed is still leaked.
- **Workflow auditing** with zizmor, which looks for the ways CI itself gets
  compromised: template injection into shell steps, over-broad token permissions,
  unpinned actions, and untrusted code checked out under a privileged trigger.
- **Least-privilege tokens.** Every workflow declares a top-level `permissions:` block
  and every job narrows it further. Checkouts set `persist-credentials: false`; nothing
  here pushes from CI.
- **Pinned actions.** Every third-party action is referenced by full commit SHA. A shell
  check in `security.yml` fails the build if one is not.
- **Static analysis** with CodeQL, run from `security.yml` with the `security-extended`
  query suite, and with ruff's flake8-bandit rules.
- **GitHub's own controls**, alongside the checks above rather than in place of them:
  private vulnerability reporting, which is what the form under Reporting depends on;
  secret scanning with push protection, which stops a credential as it is pushed rather
  than one CI run later; and Dependabot alerts and security updates. Those last two
  cover less than their names suggest: GitHub raises an alert for an action only when it
  is referenced by a semantic version, never by a commit SHA, and every action here is
  pinned by SHA. `pyproject.toml` declares no runtime dependencies; its one third-party
  package is the unpinned `hatchling` build backend, fetched only when the validator is
  built or installed as a package, which CI never does, and no update covers it. The
  tools CI installs are pinned in workflow variables, which GitHub does not read as
  dependencies. Today the defence for actions is the weekly version updates in
  `.github/dependabot.yml`, which do follow a SHA pin through its version comment. Which
  of these are confirmed on, and how to read each back, is recorded in
  [`docs/ci.md`](docs/ci.md#recorded-state).

## What skills may and may not contain

Skills may describe security tooling, defensive procedure, threat models and hardening
work — several of them do, in detail.

They may not contain working exploit code, credentials of any kind, or instructions whose
plain purpose is unauthorised access or evading detection. A skill should not surprise
someone who has read its description.
