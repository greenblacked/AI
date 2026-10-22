# Reproduction setup

Contents: inspecting a physical device, the iOS Simulator, Playwright's WebKit build,
and what to capture when the bug will not reproduce.

## Physical device

1. On the iPhone or iPad, turn on Web Inspector in Safari's Advanced settings.
2. On the Mac, show the Develop menu (Safari settings, Advanced, "Show features for web
   developers" in recent versions).
3. Connect the device by cable (or pair it for network inspection), open the page in
   Safari on the device, and choose the device and the page from the Develop menu.
4. Use the Console, Network, Storage and Elements tabs exactly as on desktop. Storage
   shows local storage, IndexedDB and cookies, which is where ITP problems show up.

Inspecting an installed Home Screen app or an app's web view works the same way when the
app allows inspection; the page appears under the device in the Develop menu.

## iOS Simulator

The Simulator ships with Xcode and runs mobile Safari. Older iOS runtimes can be added
from Xcode's settings, under Platforms, which is how to test the oldest version the
product supports.

```bash
xcrun simctl list devices booted                       # which simulator is running
xcrun simctl openurl booted https://staging.example.com/checkout
```

Inspect it from the Mac's Develop menu, where it appears like a connected device. The
Simulator reproduces layout, viewport units, the safe area and most JavaScript
behaviour; it is weaker for performance, touch nuances and anything tied to real
hardware.

## Playwright WebKit

```bash
npx playwright install webkit
npx playwright open --browser webkit https://staging.example.com/checkout
npx playwright test --project=webkit                   # when playwright.config defines it
```

It runs on Linux, macOS and Windows, which makes it the practical choice for a
regression test in CI. It is a WebKit build, not Safari: it shares the JavaScript engine
and layout code, but device emulation only sets the viewport, user agent and touch
flags. It does not reproduce the iOS toolbars, keyboard, input zoom or ITP.

## When it will not reproduce

Ask the reporter for the iOS version and display mode, and add these fields to client
error reports so the next occurrence carries them:

- the user agent string, for reporting only, never for branching;
- whether the page runs as an installed app (`matchMedia('(display-mode: standalone)')`);
- the results of the feature checks the suspected cause depends on, such as
  `CSS.supports('height', '100dvh')`;
- whether storage the app expects to exist is present at start-up.

A report that says "Safari 16 on iPhone, standalone, local storage empty at start-up" is
usually enough to place the bug on the known list without a device in hand.
