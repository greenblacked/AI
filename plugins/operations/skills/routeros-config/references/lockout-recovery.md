# Lockout recovery

Climb this ladder in order. Each rung costs more and destroys more than the one above it,
and the common mistake is jumping to the bottom because it is the rung everyone
remembers. Before you take any rung, be clear about which of two situations you are in:
the device is unreachable, or the device is reachable and doing the wrong thing. They look
identical from a dead session and they need opposite responses.

## 1. Wait for safe mode to do its job

If the change was made in safe mode and the session has dropped, the device reverts it
without you. Waiting is the whole procedure. Reconnecting too eagerly through a half-open
session, or forcing the old session to close in the wrong way, is how people lose a revert
that was already happening.

The revert does not fire the moment your side of the connection dies. It fires when the
device gives up on a session it can no longer see, which is minutes rather than seconds.
Impatience here is what sends people to the bottom of this ladder to destroy a
configuration that was about to come back on its own, so give it that long before moving
down.

Establish from the other end whether the session is really gone. A session that is hung
rather than closed has not triggered anything yet.

## 2. Reach it over layer 2 from an attached segment

MikroTik devices can be managed over layer 2 from a directly connected segment, which does
not depend on IP addressing, routing or the firewall's input chain being sane. This is the
rung that recovers most self-inflicted lockouts, and it only works if the service was left
enabled on an interface you can physically reach — which is why step 1 of the skill asks
you to prove it before you need it.

You need to be on the same broadcast domain. In practice that means a laptop plugged into
the device, or into a switch that reaches it without crossing the router you just broke.

## 3. Serial console

A serial console does not care about the network stack at all, so it survives everything
above and most things below. It needs physical access and the right cable, and on some
boards the port is present but not fitted with a connector. Find out which case you are in
before an outage rather than during one.

## 4. The other administrator, from the other side

If a second account exists that is reachable from a different subnet — a management
network, a VPN that terminates elsewhere, a jump host inside the perimeter — it may still
be able to get in when your path cannot. This only helps if the change did not affect that
path too, which is why the second path should not share a firewall rule or an interface
with the first.

## 5. The reset button

The reset button does several different things depending on how long it is held, and both
the intervals and what they mean differ by board. One of them destroys the running
configuration and the others do not, and you cannot tell which one you are performing by
feel. Read the documentation for the board in front of you before pressing it, rather than
working from what the last board did.

This rung destroys the running configuration. It is recoverable only to the extent that
you took a text export beforehand, which is the argument for step 2 of the skill.

## 6. Reinstall over the network

The last rung reloads the operating system from a machine on the same segment, and by default returns
the device to a clean state with no configuration at all. It needs physical access, a
direct connection and a prepared host, so it is a planned operation rather than something
you improvise at the end of a bad evening.

Treat reaching this rung as a finding rather than a fix: a device that had to be
reinstalled to recover from a config change is a device with no out-of-band path, and
building one is the follow-up.

## What to fix afterwards

Every lockout is evidence about the gap that allowed it. The useful questions are whether
a second path existed, whether it was proven working, whether the change ran with an
automatic undo, and whether a readable export existed from before the change. A lockout
that cost a site visit and changed none of those four answers will happen again.
