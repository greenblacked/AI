# Device checks

Commands and settings for reproducing on-device suppression. Run each with a known-good
push from the server or provider console, and compare with the same push under normal
conditions.

## Contents

- Android: stopped state, Doze and standby
- Android: notifications and channels
- Android: vendors
- iOS

## Android: stopped state, Doze and standby

```bash
# Stopped state: nothing is delivered until the user opens the app again
adb shell am force-stop com.example.app

# Doze: put the device into deep idle, send normal and high priority, then restore
adb shell dumpsys battery unplug
adb shell dumpsys deviceidle force-idle
# ... send the normal and high priority test pushes now ...
adb shell dumpsys deviceidle unforce
adb shell dumpsys battery reset

# App standby buckets
adb shell am get-standby-bucket com.example.app
adb shell am set-standby-bucket com.example.app rare

# The user's background restriction from battery settings
adb shell cmd appops set com.example.app RUN_ANY_IN_BACKGROUND ignore
# ... send a test push, then restore ...
adb shell cmd appops set com.example.app RUN_ANY_IN_BACKGROUND allow
```

Expected: under forced idle a normal-priority message waits; a high-priority one arrives.
After `force-stop`, nothing arrives until the app is launched. If a vendor device behaves
like `force-stop` after a swipe from recents, that is the vendor battery manager.

## Android: notifications and channels

```bash
adb shell dumpsys notification
```

Look for the package's channels and their importance; a channel at importance none is
blocked by the user. In code, check `NotificationManagerCompat.areNotificationsEnabled()`
and the channel's importance before concluding a push was lost. On Android 13 and later,
check the `POST_NOTIFICATIONS` grant. To send someone to fix it, open
`Settings.ACTION_APP_NOTIFICATION_SETTINGS` with the package in `EXTRA_APP_PACKAGE`, or
the channel settings for one channel.

## Android: vendors

Vendor battery managers act before stock Android does. Check, on the vendor's own device:

| Vendor | Settings to look at |
| --- | --- |
| Xiaomi | Autostart, and the app's battery saver set to no restrictions |
| Huawei, Honor | App launch set to manage manually with background activity allowed; devices without Google Play services cannot receive FCM at all and need the vendor's own push service |
| Samsung | Sleeping apps and deep sleeping apps lists; never-sleeping apps |
| Oppo, OnePlus, Vivo | Battery optimisation and background activity per app |

Settings names move between OS versions; community-maintained per-vendor guides such as
dontkillmyapp.com track them. Use them to write in-app guidance for users who need
reliable alerts, and record vendor and OS version in delivery telemetry so the effect is
measured rather than assumed.

## iOS

- **Simulator:** `xcrun simctl push booted com.example.app payload.json` delivers a local
  test payload; it exercises the app's handling, not APNs.
- **Device, through APNs:** Apple's Push Notifications Console sends a test push to a
  device token and shows delivery logs for it; use it to separate "APNs never reached the
  device" from "the device did not show it".
- **Device logs:** with the device connected to a Mac, Console.app filtered to the `apsd`
  process shows push receipt.
- **Settings on the affected device:** the app's notification settings (alerts, banners,
  Notification Centre), any active Focus and whether the app is allowed through it,
  Scheduled Summary, Low Power Mode, and Background App Refresh for the app — with it off,
  background pushes do not launch the app.
- **Swiped away:** after the user swipes the app away in the app switcher, background
  pushes stop launching it until the user opens it again; test that state explicitly.
