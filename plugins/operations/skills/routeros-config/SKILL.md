---
name: routeros-config
description: Change, upgrade or recover a MikroTik RouterOS device without locking yourself out of it. Establish the version and a second way in, export the config as text, make the change in safe mode so a dropped session reverts it, verify over a path you did not touch, then release. Covers the changes that actually strand people — firewall input rules, bridge VLAN filtering, addresses, routes, users and services — the package and RouterBOOT upgrade order, and the recovery ladder. Use whenever someone configures, upgrades, backs up or is locked out of a MikroTik router or switch, or mentions RouterOS, WinBox, hEX, CRS, CCR, /export or safe mode. Not for reviewing a written Ansible or Terraform diff (iac-review), rotating a credential (secret-rotation), an access review (access-review), or another vendor's router or firewall, which nothing here covers.
allowed-tools: Read, Grep, Glob, Bash(ssh:*), Bash(diff:*)
---

# RouterOS configuration and recovery

A change lands on the device, you can still reach the device, and you can prove what
changed by diffing two text exports.

On a network device the thing you are changing and the path you are changing it over are
the same object. That is the whole difficulty. A firewall rule, a VLAN setting or an
address change can be perfectly correct and still end the session that issued it, and
once the session is gone the device is doing exactly what you told it to — forever, or
until someone drives to it. Ordinary config discipline does not cover this, because on a
server a bad change leaves you logged in to fix it.

Two more things make RouterOS specific. The syntax moved between version 6 and version 7,
so a procedure copied from a forum post is as likely to be for the other major version as
for yours. And the bootloader is upgraded separately from the operating system, so a
device can run a current RouterOS on firmware years behind it.

## Scope

Use for: configuring, hardening, upgrading, backing up or recovering a MikroTik router or
switch; any change to firewall, VLANs, addressing, routing, users or management services;
planning a change you suspect could strand you.

Do not use for: reviewing an Ansible or Terraform diff that someone has already written,
which is `iac-review`; rotating or containing a leaked credential, which is
`secret-rotation`; an estate-wide least-privilege review, which is `access-review`; a
live service incident whose cause is not yet known to be the network, which is
`k8s-triage`; or a network device from another vendor, because the commands, the gates and
the recovery ladder here are RouterOS-specific and following them elsewhere produces
confident nonsense.

## Hard gates

Each of these exists because skipping it is how a routine change becomes a site visit.

- **No change over the network without an automatic undo.** Safe mode is the built-in
  one: what you do in it is reverted if the session dies. Where a step cannot run in safe
  mode, arrange the undo before the change, not after.
- **A text export before you touch anything, and another after.** The binary backup
  cannot be read or diffed, so it cannot tell you what changed or be partially reused.
- **Verify over a path you did not just change.** The session that made the change is the
  one witness that cannot tell you it still works, because it was already open.
- **Confirm the command on the device, not from a procedure.** Tab-completion and `?` at
  a menu level cost seconds and settle the version question that a copied command does
  not.
- **Know your second way in before you need it.** If the only path to the device is the
  one you are about to reconfigure, establishing a second one is the first change, made
  on its own.

## Workflow

### 1. Establish what you are on, and how you get back in

Before the first change, record the version, the board, and the identity — a device you
believe is the spare is the one people reconfigure by mistake.

```bash
ssh admin@192.0.2.1 '/system resource print; /system routerboard print; /system identity print'
```

The space-separated form above is accepted by both major versions. The slash-separated
path form is not, which matters in the one step whose job is to find out which version you
are on.

Then establish the second path, and prove it works now rather than assuming it. Candidates,
roughly in order of how much they survive: a serial console; layer-2 MAC access from a
directly attached segment, which works when IP configuration is broken because it does not
use it; a second administrative account reachable from a different subnet. Restrict
layer-2 management to the interfaces where it is meant to be available — it bypasses
routing, which is what makes it useful in recovery and dangerous the rest of the time.

`references/lockout-recovery.md` is the ladder to climb when this step was skipped and
you are already locked out. Read it before pressing any button on the device.

### 2. Export as text, and read what comes back

```bash
ssh admin@192.0.2.1 '/export' > before.rsc
```

Whether secrets appear in that file depends on the version and on the flag you passed, so
check the output for them rather than assuming either way — the answer decides whether the
file can go in version control as it stands.

Take the binary backup as well. The two are not alternatives: the binary one restores this
device to this state, and the text one is the one you can read, diff, review and replay
onto a replacement board.

### 3. Decide whether the change is one of the ones that strand people

`references/risky-changes.md` ranks the change classes by how they take the device away
from you, each with the check that catches it beforehand. Read the entry for what you are
about to do. The short version: a firewall `input` rule, enabling bridge VLAN filtering, a
change to the address or interface you are connected over, the default route, and anything
touching users or management services.

For those, the pre-checks matter more than the change. A dropped management path is
usually not a subtle mistake — it is a correct rule applied in an order that catches your
own traffic, or a VLAN table that does not contain the port you are sitting on.

### 4. Make the change in safe mode

In an interactive terminal, safe mode is a toggle — Ctrl-X — and the prompt shows the mode
while it is on. The prompt is the confirmation: if it does not change, the chord did not
take, which is a harmless way to find that out.

Everything done while it is on is undone if the session drops — which is exactly the
failure you are protecting against, because the change that strands you also kills the
session that made it.

Releasing it means pressing the same toggle again, deliberately, once the change is
verified. Leaving the session by another route is not the same act — at least one of the
other ways out discards the changes rather than keeping them — so end it on purpose rather
than by closing a window.

Two limits decide whether the protection is real. It holds a bounded number of actions, and
a window that runs past the bound can leave the mode and keep the changes rather than
refusing the action, so keep the window to the change itself rather than a whole evening's
work, and treat the prompt as the only signal that you are still protected. And it protects
the session, not the device: a reboot or a power cut is a different problem, and the export
from step 2 is what covers that.

### 5. Verify over a path you did not touch

Test from the second path, and test the thing the change was for as well as the thing you
were afraid of breaking. A rule that blocks your management traffic and a rule that blocks
the traffic it was written for fail in opposite directions and look identical from a
session that is still open.

### 6. Release, export again, and diff

Release safe mode with the toggle, once verification passed. Then export again and diff:

```bash
ssh admin@192.0.2.1 '/export' > after.rsc && diff -u before.rsc after.rsc
```

The export begins with a header carrying the date and the version, so the diff is never
empty; read past that line. What remains is the record of what actually changed, which is
routinely not what you thought you were changing. Store `after.rsc` where the next person
will find it, with the date and the reason, and keep it in version control if the device
matters.

## Upgrades

The package upgrade and the bootloader upgrade are two operations, and doing only the
first is the common outcome because it is the one that reports success.

1. Export first. An upgrade is the case where you most want a readable config, and the
   binary backup is the least portable across versions.
2. Upgrade the packages and reboot. Confirm the version afterwards rather than assuming
   the reboot did what the changelog said.
3. Upgrade the bootloader, which needs its own reboot to take effect.
4. Check the things a version change silently alters — the wireless stack, routing table
   syntax, and defaults for services you rely on. This is where a working config becomes
   a half-working one.

Across a major version, upgrade a spare board or a lab device first and diff its export
before and after. Reading what the upgrade rewrote is cheaper than discovering it on the
device that carries traffic. Plan the order and the rollback the way you would any
hard-to-reverse switchover; `cutover` covers that shape if the upgrade is large enough to
need a runbook of its own.

## Output format

When this skill produces a change plan, say plainly:

- **What changes** — the commands, in the order they will run.
- **How you get back in** — the second path, proven working, named specifically.
- **What reverts it** — safe mode, a scheduled undo, or the export to restore from.
- **What proves it worked** — the test, and the path it runs over.
- **What to watch after** — what would show up later rather than immediately.

## Anti-patterns

**Pasting a procedure without checking which major version it was written for.** The
commands often still parse. Silent acceptance of something that means something slightly
different is worse than an error, which is why step 1 records the version first.

**Treating the binary backup as the backup.** It restores this device to this state and
tells you nothing else — you cannot read it, diff it, review it, or lift one section out
of it onto a replacement board.

**Enabling bridge VLAN filtering before the management path is in the VLAN table.** The
setting is correct, the table is incomplete, and the port you are sitting on stops
carrying your traffic the instant it takes effect.

**Adding a drop rule to the input chain above the rule that lets you in.** Rules are
evaluated in order, so a rule that is right at the bottom of the list is a lockout at the
top.

**Leaving the default administrative account in place because the password was changed.**
The account name is the half of the credential an attacker does not have to guess.

**Enabling every management service so that one of them will work.** Each is another way
in for everyone else; decide which one you use and restrict the rest to the addresses that
should reach them.

## Reference files

- `references/lockout-recovery.md` — the ordered ladder from "the session hung" to
  reinstalling the device, with what each rung costs and what it destroys. Read it at
  step 1 when planning, and before touching hardware when recovering.
- `references/risky-changes.md` — the change classes that strand people, each with the
  check that catches it first. Read the relevant entry at step 3, before making the change.
