# Owned-device boundaries

Read before planning any change.

## In bounds

- Devices the operator owns outright, or administers with written authorisation (a managed
  fleet, a lab unit, a client device under contract).
- Disabling or uninstalling (for user 0) preinstalled apps, ad and telemetry packages, and
  launchers on that device.
- Switching the default launcher; changing the privacy, ad-personalisation and diagnostics
  settings the vendor provides.
- Blocking ad or telemetry endpoints at the owner's own DNS resolver or router.
- Pulling APKs from the owned device for analysis.
- Factory reset; reflashing an official vendor image through the vendor's documented
  procedure when the owner authorises it, with a backup.
- Security research on the owned device, with findings sent to the vendor through its
  disclosure process.

## Out of bounds

- DRM (any scheme) or HDCP bypass, spoofing or key extraction.
- Enabling piracy, unlicensed streams, stream ripping or region-lock evasion.
- Defeating anti-theft, activation, parental or account locks.
- Account takeover, or using credentials or tokens found on the device.
- Exploits, rooting or bootloader unlocking used to gain access the owner was not given, or on
  devices the operator does not own.
- Any device belonging to someone else without their authorisation — neighbours, landlords,
  venues, employers, shared housing.
- Redistributing modified vendor images or proprietary packages.

## When unsure

Stop and ask for the ownership or authorisation basis in writing. If a goal can only be met by
an out-of-bounds step, say so and do not provide it.
