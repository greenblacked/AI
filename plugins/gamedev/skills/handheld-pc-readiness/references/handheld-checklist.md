# Handheld checklist

Read this at steps 2 to 5 of `SKILL.md`.

## Contents

- [Clean-install procedure](#clean-install-procedure)
- [Per-category checklist](#per-category-checklist)
- [Session log](#session-log)

## Clean-install procedure

1. Uninstall the game and delete its compatibility data and saved settings so the next launch is a first launch.
2. Reinstall from the store build under test, not a developer copy.
3. Launch with no mouse or keyboard attached, as a player does.
4. Record the OS version, the Proton version (or Windows build) and the game build id.

## Per-category checklist

Input

- [ ] Every launcher, EULA, age-gate and login screen works with the controller.
- [ ] Anti-cheat and DRM prompts need no pointer.
- [ ] Glyphs match the controller in use and change when the controller changes.
- [ ] Text fields open the on-screen keyboard.
- [ ] Each menu has a controller route in and out; no mini-game traps the player.

Display

- [ ] Renders at 1280x800 natively or in an exact scaling mode.
- [ ] Smallest text (tooltips, subtitles, numbers) readable on the device.
- [ ] Nothing clipped at the edges of the panel.

Seamlessness

- [ ] First run reaches gameplay with controller only.
- [ ] Suspend and resume return to a working game.
- [ ] No prompt appears that needs a keyboard.

System support

- [ ] Runs under Proton or natively from a clean install.
- [ ] Video, audio and middleware work; workarounds listed and tested clean.

## Session log

```text
build: ____   device: ____   os/proton: ____   preset: ____   power: battery
minute   fps_avg   fps_low   battery_pct   watts   notes
0
10
20
30
floor from current criteria: ____ (page and date: ____)
result: pass / fail
```

The values are measured, never estimated. If the overlay does not show a figure, note that and use an external meter instead of guessing.
