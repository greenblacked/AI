# Smart TV and streaming platforms

Read this when the target is a smart TV's or streaming device's own operating system and app
platform rather than a native binary, a JVM class file or a web bundle. Gate 1 still applies
first: write down the authorisation and scope before the first command. Owning the set gives
you physical access and puts it in scope, but it gives you no rights over the vendor's software
or the third-party apps on it. Under gate 1, write down which permission covers the software
itself: the set's own settings, which you are entitled to use; an app you built and loaded
through the platform's developer mode; or an interoperability right you actually hold.

## Contents

- [Identify the platform before picking a tool](#identify-the-platform-before-picking-a-tool)
- [Where ad injection and tracking actually live](#where-ad-injection-and-tracking-actually-live)
- [What is, and is not, in scope here](#what-is-and-is-not-in-scope-here)
- [Building a replacement UI is a different skill](#building-a-replacement-ui-is-a-different-skill)

## Identify the platform before picking a tool

The app package format decides the tool, so identify the format before anything else.

- **A TV platform whose apps ship as `.apk`** uses the same package format that
  [packaged and mobile artifacts](packaged-and-mobile-artifacts.md) covers. Read it there;
  nothing new is needed.
- **A platform whose web apps ship as `.wgt`** uses the W3C Widget Packaging and XML
  Configuration specification, which builds on an ordinary zip archive with a `config.xml`
  manifest (confirmed against the specification and the platform's developer documentation).
  The same `unzip -l` and `python3 -m zipfile -l` approach applies; the manifest is
  `config.xml` rather than `AndroidManifest.xml`.
- **A platform whose apps ship as `.ipk`** is not zip-backed. The general IPK and opkg
  convention is an `ar` archive holding a `debian-binary` marker plus `control.tar.gz` and
  `data.tar.gz`, the same family as a `.deb`. Run `file` on it first (gate 2) and branch on
  what it prints, never on the extension. On small test packages built for this skill,
  `file` 5.45 reported `Debian binary package (format 2.0), with control.tar.gz/, data
  compression gz` when `debian-binary` was the first member and `current ar archive` when it
  was not; either way `ar t` lists the members and `ar x` extracts them. Some packaging
  tools wrap the same three files in a gzipped `tar` instead, which `file` reports as `gzip
  compressed data`; list that one with `tar -tzf`. Neither form is ever read with `unzip`.
  These outputs come from test packages, not a real TV package, so confirm the layout
  against a sample before relying on it.
- **A platform whose developer mode sideloads a plain zip** of script, markup and media
  through the device's own web interface can be listed with `unzip -l`. A signed store
  package is built and signed through the vendor's own publishing process, and this reference
  does not cover reading one.

## Where ad injection and tracking actually live

Many ad-supported smart TV platforms run some form of automatic content recognition (ACR): a
component that samples what is on screen or in the audio, matches it against a reference
database, and reports back what is being watched. ACR is a data-collection step, not the ad
overlay itself. A separate component uses what it reports to target or measure ads, and the
two can be controlled separately in the OS, if either is exposed at all; this was not
independently verified for this skill.

The regulatory history is documented. The FTC's announcement of 6 February 2017 describes a
settlement, with the New Jersey Division of Consumer Affairs, with a TV manufacturer for $2.2
million over ACR software, on by default and later pushed to previously sold sets, that tracked
viewing second by second and shared it with third parties without adequate disclosure or
consent. The order required prominent disclosure and affirmative opt-in consent going forward.
Read that announcement on the FTC's site rather than rely on this summary.

Many ACR-capable sets now expose an ACR or interest-based-advertising opt-out in their own
settings, but the menu path and the feature's name both change across vendors and firmware
versions. Read the vendor's own current support documentation rather than follow a path quoted
here: a path that is correct for one firmware version is exactly the kind of detail that goes
stale silently, so none is given.

To observe what the set actually does, watch it from the network side at a point you
control: the lookups it sends to a DNS resolver you run, or traffic captured on your own
router or a mirror port. The set may ignore the resolver your network hands it, using a
fixed public resolver or encrypted DNS instead, so an empty resolver log proves nothing; the
router or mirror-port capture, which shows destination addresses and timing either way, is
the view to trust. Most of the traffic is encrypted, so this shows which addresses the set
contacts and when (for example right after the picture changes), and usually which host
names from the part of the TLS handshake that is not encrypted, unless the connection uses
Encrypted Client Hello, which hides that too; it never shows what was sent. That pattern is
the dynamic confirmation gate 4 asks for. This was not independently verified against a real
set for this skill. Nothing here involves intercepting or decrypting the traffic, and this
file does not describe how. For gate 3, the set is not run on your machine: it is an
appliance already on your network, so the isolation that matters is the network's. Put it on
its own segment or guest network, so the capture sees only its traffic and it cannot reach
your other devices.

## What is, and is not, in scope here

The set's own settings menu, and a platform's own documented developer mode used the way its
SDK describes, are the vendor's supported mechanisms. Owning the set does not by itself cover
anything beyond them: under gate 1, name the permission that covers the software you are
touching, as set out at the top of this file.

Unlocking a bootloader with no official unlock path, breaking secure boot, or circumventing DRM
to reach a component with no supported access is a different posture. It is not covered by this
reference, and it runs into this skill's own no-bypass gate (gate 5) the same as any other
target. This file does not describe how to do it.

## Building a replacement UI is a different skill

Wanting your set's home screen to feel like another platform's — a grid of large app tiles with
remote-driven focus navigation, for instance — stops being a reverse-engineering question once
you have observed how it behaves. Building an original version from a behavioural spec, not by
copying the other platform's code, icons or assets, is `feature-recreation`'s job; this file is
for reading the shipped artifact itself.

Another platform's name, logo, icons and look-alike branding are trademark and trade-dress
questions. Route them to `feature-recreation`'s gate 5 rather than resolving them here:
"Patent and trademark risk is named, not decided here. A feature can be free of copyright
concerns and still covered by a patent, or its name and look protected as trade dress. This
skill does not clear either; flag the risk for legal review when the feature is a core
differentiator or the reference is a direct competitor."
