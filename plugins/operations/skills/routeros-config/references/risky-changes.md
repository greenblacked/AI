# The changes that strand people

Ranked by how often they end the session that made them. Each entry is the mechanism,
the check that catches it beforehand, and the recovery that is cheapest if it happens
anyway. None of these is an exotic mistake; they are correct changes applied in an order
or a scope that includes your own traffic.

## Firewall input chain

**Mechanism.** Rules are evaluated in order and the first match wins, so a drop rule
placed above the rule that permits your management access ends your session the moment it
is accepted — and not only on the next connection, unless a rule accepting established and
related traffic sits above the drop as well. Where such a rule does sit above it, the open
session survives and the lockout appears the next time anyone connects, which is the worse
case: the change looks fine from the session that made it.

**Check first.** Know where in the list the rule will land rather than where you intended
it to land, and place it explicitly relative to a known neighbour instead of appending and
hoping. Confirm the rule that admits your own access exists and sits above it. A rule
matching established and related traffic near the top is what keeps an open session alive
while you work; if the change moves or removes it, that is the change to be careful about,
not the new rule.

**Cheapest recovery.** Safe mode. This is the class safe mode was made for.

## Bridge VLAN filtering

**Mechanism.** Turning VLAN filtering on makes the bridge start enforcing a table that was
previously ignored. Every port that is not correctly described in that table — tagged
where it should be tagged, untagged with the right default VLAN where it should be
untagged — stops carrying the traffic it used to carry. If the port you are managing the
device over is one of them, the device is gone the instant the setting takes effect.

**Check first.** Walk the table and find the entry that covers your own port and the VLAN
your management traffic is in, including the case where that traffic is untagged. Decide
deliberately where the device's own management address lives once filtering is on. Make
this change from a path that does not cross the bridge you are changing, or from the
console, if you have one.

**Cheapest recovery.** Safe mode. Layer-2 access is the fallback, but it is a weaker one
here than elsewhere: that traffic still crosses the bridge you have just told to enforce a
table, so a port missing from the table can take the recovery path with it.

## The address or interface you are connected over

**Mechanism.** Changing, disabling or renaming the interface or address carrying your
session ends it, and the device may now be reachable only at an address nobody has yet
written down.

**Check first.** Establish which interface and address your session is actually using
rather than the one you believe it is, and make the change from a different one. Where the
change must happen on the live path, add the new address before removing the old one, so
both work for a moment and you can move across.

**Cheapest recovery.** Layer-2 access, which does not depend on addressing.

## Default route and routing changes

**Mechanism.** A management session crossing a router loses its return path when the
default route changes, even though nothing about the device's own interfaces moved. This
one is easy to mis-attribute, because the device is fine and the path is not.

**Check first.** Work out whether your traffic reaches the device symmetrically. If the
return path depends on the route you are editing, arrange the undo before the edit.

**Cheapest recovery.** Safe mode, then a session from inside the segment the device is on.

## Users, groups and management services

**Mechanism.** Disabling, renaming or restricting the account you are logged in as, or the
service you are logged in over, can end access for everyone including you. Address
restrictions on a service are the sharp edge: correct in intent, and wrong by one subnet
is indistinguishable from off.

**Check first.** Have a second working account before you change the first, and prove it
by logging in with it rather than by reading the configuration. When restricting a service
by address, include the address you are connected from, and check what that address is
after any network address translation between you and the device.

**Cheapest recovery.** The second account. If there is no second account this class has no
cheap recovery, which is the argument for making one first.

## Wireless and interface-level changes on a remote device

**Mechanism.** Changing a radio, a bonding or bridge membership, or an interface's
parameters can take down the link carrying the session, and in the wireless case may
require the far end to agree to the new settings before it comes back.

**Check first.** For a link with two ends, change the end you are not connected through
first, and confirm it before changing the other. Where both ends must change together,
schedule an undo on the far end before you begin.

**Cheapest recovery.** A scheduled undo on the far end, which has to be arranged before
the change rather than after.
