# Policyfiles and staged rollout

Read when moving a node group from roles and environments to Policyfiles, writing or
updating a Policyfile, reading a lock diff, or promoting a change across policy groups.
Subcommands and flags change between Chef Workstation releases; run `chef --help` and
check the official docs for the pinned version before using any of them.

## Contents

- Shape of a Policyfile
- The commands and what each one changes
- Reading a lock diff
- Promotion across policy groups
- Moving off roles and environments
- Rollback and its limits

## Shape of a Policyfile

```ruby
# Policyfile.rb
name 'web'
default_source :supermarket          # or an internal source; see the pinning note below
run_list 'base::default', 'nginx_site::default'
cookbook 'base', path: '../cookbooks/base'
cookbook 'nginx_site', '~> 2.4'
default['nginx_site']['worker_processes'] = 4
```

A Policyfile names one policy: a run list, the cookbooks that satisfy it with
constraints, and optional attributes. `chef install` solves the constraints and writes
`Policyfile.lock.json`, recording each resolved cookbook with a version and an
identifier. Commit both files.

Prefer an internal or reviewed source over a public one for production cookbooks, and
set the source explicitly so a missing cookbook fails instead of resolving from
somewhere unexpected. Which source types exist depends on the Workstation version.

## The commands and what each one changes

| Command | Effect | Changes the server |
| --- | --- | --- |
| `chef install` | Solves constraints and writes the lock, reusing locked versions when it exists | No |
| `chef update` | Re-solves, taking newer versions the constraints allow | No |
| `chef diff` | Compares two locks, groups or revisions | No |
| `chef push <group> Policyfile.lock.json` | Uploads the cookbooks and assigns that lock to the policy group | Yes |

The pair to keep apart is `install` and `update`: the first keeps what you have, the
second changes it. Run `update` in its own commit so the lock diff is the whole change.

## Reading a lock diff

Review three things, in order:

1. Which cookbooks changed version, including ones you never named (transitive
   dependencies). Each is a changelog to read.
2. Whether any cookbook's source changed (a path or a different source), which is a
   change of code owner rather than of version.
3. The attributes carried in the lock, since a default changed there applies to every
   node in the group.

A diff that touches more cookbooks than the change description mentions is the reason
the diff exists. Stop and explain it before pushing.

## Promotion across policy groups

A policy group is a named set of nodes following one lock for a policy. A typical order is
a dev group, a canary group in production, then the rest in one or more batches.

1. Push to the first group and wait for its nodes to converge; confirm from run results,
   not from the push succeeding. Check the failed-run count, the time to converge and the
   service-level signals the change could affect.
2. Push the same lock file, byte for byte, to the next group. Verify with `chef diff`
   between groups that only the intended differences exist.
3. Hold between groups for at least one full converge interval of the fleet, and longer
   for a change that acts on a schedule (a cron-driven job, a log rotation).

Do not regenerate the lock between groups, and do not let CI run `chef update` as part
of a deploy. Record the lock's digest and the groups it reached in the change record.

## Moving off roles and environments

1. Inventory what the role and environment set today: run list, attribute overrides and
   cookbook version pins. The effective node attributes (`knife node show` or the
   equivalent) are the ground truth, since precedence hides overrides.
2. Write the Policyfile to reproduce that, then compare the converged result on a test
   instance against a node following the old model.
3. Move one group of nodes, bootstrapped or switched to the policy, and let it run for
   a few converge cycles before the next.
4. Leave the old roles and environments in place until the last node has moved, then
   remove them in a separate change.

## Rollback and its limits

Rollback is pushing the previous lock to the group. It restores the cookbook set and
attributes, not the changes the new code made: removed packages return only if the old
code installs them, migrated files stay migrated, a deleted user stays deleted. Write the
way back for each one-way action before the first push, and test it on an instance that
has already run the new version.
