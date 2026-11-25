# Resources, failures and tests

Read when a resource is not idempotent, notifications misbehave, a run fails and the
phase or cause is unclear, or Test Kitchen, InSpec and Cookstyle need setting up. Resource
names, properties and defaults change between client releases; check the docs for the
pinned Chef Infra Client.

## Contents

- Idempotence patterns
- Notifications and ordering
- Custom resources
- Reading a failed run
- Test Kitchen, InSpec and Cookstyle
- Review checklist

## Idempotence patterns

| Symptom on the second converge | Usual cause | Fix |
| --- | --- | --- |
| `execute` reports an update every run | No guard | `creates`, or `not_if` testing the real state |
| `template` or `file` updates every run | Content includes a timestamp, a random value or unordered hash output | Sort keys, remove the volatile value |
| `package` reinstalls | Version property compared with a different format than the platform reports | Use the platform's version string, or drop the pin and manage the repository |
| `service` restarts every run | A `notifies :restart` from a resource that always updates | Fix the upstream resource, then keep the notification |
| `ruby_block` runs every run | No guard, and it has no way to report no change | Add `only_if`, or replace with a resource |

Guards are commands: `not_if 'test -f /etc/app/.initialised'` runs on each converge, so
keep it cheap and make it test the effect rather than the cause. A `guard_interpreter`
changes how a string guard is run; check the docs before relying on it.

## Notifications and ordering

`notifies` defaults to running at the end of the converge, collapsing repeated
notifications into one. `:immediately` runs the target at once and can run it several
times. Use `action :nothing` on the target so it runs only when notified, and use
`subscribes` when the target should own the dependency. Order of resources in the
collection is the order of the run lists and recipes, so a resource that needs another
must come after it, or be included through `include_recipe` earlier.

## Custom resources

Move a pattern into a custom resource when it appears in more than one recipe or needs
real conditionals. Define `property`s with types and defaults, write one `action` per
verb, and use `converge_if_changed` or the built-in current-versus-desired comparison so
the resource reports a change only when it made one. Prefer this over a definition or a
library helper with side effects. Test each action on its own in Test Kitchen.

## Reading a failed run

Read the log from the first error, not the last line.

| Message shape | Phase | What to check |
| --- | --- | --- |
| Syntax error or `NoMethodError` with no resource named | Compile | Cookbook code, or an attribute that is `nil` |
| Cookbook or dependency not found, solve failure | Compile or sync | Lock content, source availability, metadata dependencies |
| `Chef::Exceptions::...` naming a resource and action | Converge | The resource's inputs, and the node's state |
| `undefined method` on a node attribute path | Compile | The attribute is absent on this node; check precedence and the policy group |
| A command resource exits non-zero | Converge | Run the same command by hand as the same user, with the same environment |
| Authentication or 401/403 against the server | Before either | Node key, clock skew, client name, server reachability |
| Licence acceptance error on a fresh client | Before either | The distribution's licence setting; check the vendor's docs |

When only some nodes fail, diff what differs: platform version, node attributes
(`knife node show`-style output), policy group and lock, and leftover state from earlier
runs. Do not edit a failing node by hand to make a run pass; fix the cookbook or the
inputs and converge again.

## Test Kitchen, InSpec and Cookstyle

```yaml
# kitchen.yml (driver and platform names depend on your tooling and versions)
driver:
  name: dokken                 # or vagrant, a cloud driver
transport:
  name: dokken                 # kitchen-dokken needs its own transport
provisioner:
  name: dokken
  # or chef_zero with a policyfile (named_run_list, policyfile_path); check docs
verifier:
  name: inspec
platforms:
  - name: ubuntu-22.04
  - name: rockylinux-9
suites:
  - name: default
    verifier:
      inspec_tests: [test/integration/default]
```

Steps for each change:

1. `cookstyle` for lint; fix deprecations rather than silencing them.
2. `kitchen converge`, then `kitchen converge` again: the second run must report zero
   updated resources. Fail the suite when it does not.
3. `kitchen verify`: InSpec controls assert outcomes (`package`, `service`, `file`,
   `port`), not the recipe's text.
4. `kitchen destroy` in CI always, so a failed suite does not leave instances running.

Run the suite for every platform the fleet runs, and add the failing case first when
fixing a defect. Containers are fast but do not exercise init systems or kernel settings
the same way; keep at least one VM-based suite for cookbooks that touch them.

## Review checklist

- Every `execute` or `bash` has a guard or is justified in a comment.
- Nothing reads converge-produced state at compile time without `lazy` or `ruby_block`.
- No secret in an attribute, template default or test fixture; secret-handling
  resources set `sensitive true`.
- `metadata.rb` declares `chef_version` (enforced) and `supports` (documentation only; use a guard or a raise to refuse a platform).
- Two consecutive converges in Test Kitchen report no updates.
- The lock diff has been read, and the rollback is written down.
