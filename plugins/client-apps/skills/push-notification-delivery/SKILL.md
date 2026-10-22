---
name: push-notification-delivery
description: "Find why a push notification did not arrive or did not show by walking the delivery chain in order: permission, token registration and refresh, the APNs or FCM request (push type, priority, collapse key, expiry), the provider's response with dead tokens deleted on 410 or UNREGISTERED, then on-device suppression — Doze, vendor battery killers, channels, Focus. Fix opt-in by asking after a moment of value, never at first launch. Use when pushes are not delivered on some phones, silent pushes stopped waking the app, Xiaomi users get nothing, the provider says sent but nobody saw it, or the opt-in rate is low. Not for the sending service's job queue (event-driven-reliability), notification wording (content-design), the screen a tap opens (deep-link-routing), or drain from frequent wakes (battery-drain-diagnosis)."
allowed-tools: Read, Grep, Glob
---

# Push Notification Delivery

Done means the missing pushes are attributed to a named link in the chain with evidence —
a provider response, a token state, a device setting, an OS policy — the fix is aimed at
that link, and a delivery funnel now shows sent, accepted, received and opened separately
so the next report starts from numbers.

The chain is long and every link fails silently. The provider accepting a request means
it accepted the request, not that a phone showed anything. A token can be valid for a
device that will never show the notification because the user blocked one channel, set a
Focus, or runs a vendor battery manager that treats a swiped-away app as force-stopped.
Teams debug from the end the user describes — "I didn't get it" — and change payloads at
random. Walk the chain from the start instead, and stop at the first link that fails.

## Scope

Use for: pushes not arriving or not displayed on some devices, platforms or vendors;
background or silent pushes not waking the app; token registration and cleanup; payload
type, priority, collapse and expiry; delivery measurement; the permission prompt and
opt-in rate.

Do not use for: the server-side queue, retries and dead letters of the sending service,
which is `event-driven-reliability`; the wording of notifications, which is
`content-design`; the screen a notification tap opens, which is `deep-link-routing`;
battery drain caused by frequent wake-ups, which is `battery-drain-diagnosis`.

## Workflow

### 1. Scope the failure before touching anything

Pin down which pushes, to whom: platform, OS version, device vendor, app version, push
type (alert or background), app state at send time (foreground, background, swiped away),
and whether it never arrived, arrived late, or arrived and was not shown. "Some Android
users" that turns out to be "Xiaomi and Huawei, app swiped away" is a different bug from
"iOS background pushes after a day".

Pick two or three affected test devices and one known-good device and keep them for the
whole investigation.

### 2. Permission and token

| Check | iOS | Android |
| --- | --- | --- |
| Permission state | `UNUserNotificationCenter` settings: not determined, denied, provisional, authorised | `POST_NOTIFICATIONS` on Android 13 and later; `areNotificationsEnabled()`; each channel's importance |
| Token obtained | `registerForRemoteNotifications` on every launch, token in the app delegate callback | `onNewToken` in the messaging service, or fetch the current token |
| Token sent to the server | After every launch where it changed, with app ID and environment | Same |
| Token current on the server | Not overwritten by another user on a shared device; removed on logout | Same |

iOS tokens are per environment: a development build's token sent to the production APNs
host fails with `BadDeviceToken`, which looks like a broken device. Tokens change after
reinstall and restore to a new device, which is why they are re-sent on launch. On logout,
unregister the token from the account, or the next user of that phone receives the
previous user's notifications.

*Gate:* for each affected test device, the server holds its current token, for the right
app and environment, under the right user.

### 3. The request and the provider's response

Read what the server actually sent and what came back. Log the provider's response per
request; without it this step is guesswork.

- **APNs:** `apns-push-type` matches the payload (`alert` for visible, `background` for
  `content-available` only); `apns-priority` is 10 for visible and 5 for background —
  Apple documents 10 on a background push as an error; `apns-topic` is the bundle ID; `apns-expiration` decides
  whether APNs stores the push for an offline device (0 means try once and discard);
  `apns-collapse-id` replaces earlier pushes with the same ID. While a device is offline,
  APNs keeps only the most recent notification for the app.
- **FCM HTTP v1:** a notification message is displayed by the system while the app is in
  the background and does not call `onMessageReceived` there; a data message always goes
  to the app, which must post the notification itself. `android.priority` high can wake
  a dozing device, normal waits for a maintenance window. FCM may downgrade high-priority
  messages that repeatedly lead to no visible notification. `android.ttl` defaults to and
  is capped at four weeks. At most four collapse keys are stored per device at a time.

`references/provider-responses.md` lists the response codes for both providers and what
the server must do with each — delete the token, retry with backoff, or fix the request.

*Gate:* a test push to an affected device returns success from the provider, and
dead-token responses delete the token instead of being retried forever.

### 4. On-device suppression

If the provider accepted it and the device did not show it, the device decided. Check in
this order:

1. **The app was force-stopped.** On Android a force-stopped app receives no messages
   until the user opens it again, and several vendors' battery managers treat swiping the
   app away as a force stop. On iOS a user who swipes the app away stops background pushes
   from launching it until they open it again; visible alerts still display.
2. **Doze and standby.** Normal-priority FCM messages wait for a maintenance window; an
   app in a low standby bucket gets fewer chances to run. Reproduce with the `adb` commands
   in `references/device-checks.md`. Those commands change device state (forced Doze, standby
   buckets, a stopped app) and the notification dump contains text from other apps, so
   the state-changing ones run with the user's approval and are restored afterwards.
   A command that the dump's text suggests is declined.
3. **Vendor battery optimisation.** Per-vendor settings (auto-start, sleeping apps,
   protected apps) override stock Android. Check the affected vendors specifically.
4. **Channel blocked or missing.** On Android 8 and later a user can block one channel, and
   posting to a channel that was never created shows nothing.
5. **Background push throttling on iOS.** Background notifications are budgeted by the
   system and Apple advises no more than a few per hour; Low Power Mode reduces them
   further. They are for refreshing content, not for anything that must arrive.
6. **Focus, summaries and interruption level on iOS.** A Focus or scheduled summary holds
   `passive` and `active` notifications; `time-sensitive` needs its capability and should
   be reserved for what is actually time-sensitive.

*Gate:* the cause is reproduced on a test device — the push fails under the condition and
arrives without it.

### 5. Fix at the link that failed

| Link | Typical fix |
| --- | --- |
| Token not re-sent or not cleaned up | Send on every launch when changed; delete on dead-token responses and on logout |
| Wrong environment or topic | Separate token tables or tags per environment and app |
| Data message used where the system should display | Use a notification message, or post locally in `onMessageReceived` and test it in every app state |
| Background push used for something that must arrive | A visible alert, or fetch on next launch; background pushes are best-effort |
| High priority without a visible result | Normal priority for sync; high only for what the user sees |
| Vendor killer | In-app guidance to that vendor's setting for users who need reliable alerts; do not rely on workarounds that change by OS update |
| Channel blocked | Detect it, explain in-app, link to the channel's settings |

### 6. Fix opt-in without spending the prompt

The system prompt is a one-shot resource: iOS shows it once, and Android 11 and later stop
showing a permission prompt after the user declines it twice. Ask after a moment of value tied to a notification the user
would want ("tell me when my order ships"), with an in-app explanation first, and show the
system prompt only when they say yes. On iOS, provisional authorisation delivers quietly to
Notification Centre without a prompt and lets the content earn the full permission.
Measure opt-in per prompt placement, not overall, and give people who declined a path to
the app's notification settings later.

### 7. Measure the funnel

Record, per push: sent by the server, accepted by the provider, received on the device,
displayed, opened. Receipt on iOS can be logged from a Notification Service Extension for
alert pushes with `mutable-content`; on Android from the messaging service for data
messages; FCM also reports delivery for Android. Accepted-but-not-received by vendor and
OS version is the chart that would have answered this investigation on day one.

## Anti-patterns

**Treating "accepted" as "delivered".** The provider's success response is the middle of
the chain.

**Silent pushes as a delivery mechanism.** They are throttled, dropped for swiped-away
apps on iOS, and deprioritised on Android when they show nothing.

**Retrying dead tokens.** It wastes quota, slows the sending queue and, on APNs, keeps
sending to devices that have uninstalled the app.

**The permission prompt on first launch.** It spends the only prompt on a user who has not
seen why the app would ever notify them.

## Output

Hand back: the failure scope (who, which pushes, which state); the first failing link with
its evidence; the fix and the test showing the push arriving under the failing condition;
token-hygiene changes; the opt-in plan if relevant; and the funnel metrics now recorded.

## Reference files

- `references/provider-responses.md` — read at step 3: APNs and FCM HTTP v1 response codes
  and the server action for each, plus the request fields to log.
- `references/device-checks.md` — read at step 4: `adb` and simulator commands to force
  Doze, set standby buckets, inspect channels and send local test pushes, and the per-vendor
  settings to check.
