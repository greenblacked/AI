# Controller health checklist

Read when hardening, upgrading, migrating or diagnosing the Jenkins controller. Menu
names, defaults and the plugin set change between versions; check the official docs
for the pinned core before acting, and record the version each claim was checked on.

## Contents

- Settings that decide blast radius
- Configuration as Code
- Plugin pinning and upgrades
- Symptoms and where to look
- Backup and restore

## Settings that decide blast radius

| Setting | Target | Why |
| --- | --- | --- |
| Built-in node executors | 0 | Builds there can read `JENKINS_HOME` |
| Authorization | Matrix or role based, no anonymous read | Job configuration and logs leak internal names and sometimes secrets |
| Agent to controller access | Left enabled in the default way | Disabling the protection lets a compromised agent read controller files |
| CSRF protection | On | Blocks cross-site form posts; API-token requests do not need a crumb |
| Script Security sandbox | On for every job | A job outside it runs arbitrary Groovy as Jenkins |
| Markup formatter | Plain text or the safe default | Job descriptions render HTML otherwise |
| Credentials scope | Folder-level for team secrets, system scope only for controller use | A global credential is bindable by every job |

Review the Manage Jenkins security warnings page after each upgrade; it lists plugin
advisories and configuration problems for the pinned version.

## Configuration as Code

- Keep the YAML in a repository with review; load it through the documented environment
  variable or path for the plugin, and use the plugin's validation or dry-run option in
  CI before applying to the controller.
- Reference secrets as `${NAME}` resolved from environment, mounted files or an external
  secret store, never as literal values. Check how the pinned plugin resolves a missing
  variable; some versions fail the load, some leave the placeholder.
- Export the live configuration once to bootstrap, then diff and prune; an export
  contains defaults and runtime state that do not belong in version control, and it can
  also contain credential values (encrypted with the controller's key), so replace each
  one with a `${NAME}` reference before committing.
- Treat a reload of configuration as a change to production: it can reset hand-made
  settings, which is the point, so announce it.

## Plugin pinning and upgrades

1. Keep a plugins list with explicit versions and install it with the project's plugin
   installer CLI at image build time.
2. Pin the controller image tag; upgrade core and plugins together on a staging
   controller built from the same configuration.
3. Read each changed plugin's changelog for removed or renamed steps and for required
   core versions. Dependencies pull in other plugins: diff the resolved list, not only
   the top-level one.
4. Run a multibranch scan and a build of one representative pipeline per job type, plus
   one that uses each shared library.
5. Promote by replacing the image; roll back by restoring the previous image and, only if
   the data format changed, the backup.

Do not use the update centre's "install and restart" on the production controller as the
upgrade process; it leaves no record of what changed.

## Symptoms and where to look

| Symptom | First checks |
| --- | --- |
| Builds queue with "waiting for next available executor" | Queue reason text, node labels, offline agents, executor count on the node, cloud agent provisioning limits |
| Controller slow, UI hangs | Thread dump and heap (`jvm-thread-dump-triage`, `jvm-oom-triage`), number of jobs and builds retained, a plugin doing synchronous work on the UI thread |
| `JENKINS_HOME` disk full | Builds with no discarder, large archived artifacts, workspaces on the controller, log size (`disk-full-triage`) |
| Every job fails after a restart | Plugin dependency resolution errors in the startup log, a plugin pinned to an incompatible core |
| Multibranch scan not triggering | Webhook delivery and the branch source plugin's event handling, then scan log for the repository |
| Agent disconnects | Agent log, network idle timeouts between agent and controller, resource limits on the agent host |
| Approved scripts keep reappearing | The signature differs by argument type, or the library is sandboxed and its approval list differs from the global one |

## Backup and restore

Back up `JENKINS_HOME` without workspaces and caches, plus the configuration repository
and the image tag. Restore into a scratch controller on a schedule and confirm that jobs
load, credentials decrypt (the secret key files must travel with the credential store)
and a build runs. A backup that was never restored is a hope, not a recovery plan.
Encrypt the backup and restrict access to it like the credential store, since it
includes the secret key files, and isolate the scratch controller from production
targets and destroy it after the test.
